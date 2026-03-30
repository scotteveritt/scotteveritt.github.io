#!/usr/bin/env bash
#
# Cross-post a Jekyll markdown post to Dev.to and Hashnode.
# On first publish, writes platform IDs back to frontmatter and commits.
# On subsequent pushes, updates Dev.to (PUT), skips Hashnode (no update API).
#
# Usage: cross-post.sh <path-to-post.md>
#
# Expects env vars:
#   DEVTO_API_KEY
#   HASHNODE_API_KEY
#   HASHNODE_PUBLICATION_ID
#   SITE_URL  (e.g. https://scotteveritt.github.io)

set -euo pipefail

POST_FILE="$1"
UPDATED_FRONTMATTER=false

if [ ! -f "$POST_FILE" ]; then
  echo "File not found: $POST_FILE"
  exit 1
fi

# ── Parse front matter ──────────────────────────────────────────

fm_value() {
  sed -n '/^---$/,/^---$/p' "$POST_FILE" | grep "^$1:" | head -1 | sed "s/^$1: *//; s/^\"//; s/\"$//"
}

# Insert or update a frontmatter field
fm_set() {
  local key="$1" value="$2"
  if grep -q "^${key}:" "$POST_FILE"; then
    sed -i "s|^${key}:.*|${key}: ${value}|" "$POST_FILE"
  else
    # Insert before closing ---
    sed -i "/^---$/,/^---$/{
      /^---$/{
        x
        s/.*//
        x
        b
      }
    }" "$POST_FILE"
    # Simpler: insert on line 2 (after first ---)
    sed -i "2a\\
${key}: ${value}" "$POST_FILE"
  fi
}

TITLE=$(fm_value title)
DESCRIPTION=$(fm_value description)
DATE=$(fm_value date)
DEVTO_ID=$(fm_value devto_id)
HASHNODE_ID=$(fm_value hashnode_id)
KEYWORDS=$(fm_value keywords)

# Build slug from filename
SLUG=$(basename "$POST_FILE" .md | sed 's/^[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-//')
CANONICAL_URL="${SITE_URL}/blog/${SLUG}/"

echo "Title:      $TITLE"
echo "Slug:       $SLUG"
echo "Canonical:  $CANONICAL_URL"
echo "Dev.to ID:  ${DEVTO_ID:-<none>}"
echo "Hashnode ID:${HASHNODE_ID:-<none>}"

# ── Extract body (strip front matter) ───────────────────────────

BODY=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$POST_FILE")

# Convert relative image/video paths to absolute
BODY=$(echo "$BODY" | sed "s|](/assets/|](${SITE_URL}/assets/|g")
BODY=$(echo "$BODY" | sed "s|src=\"/assets/|src=\"${SITE_URL}/assets/|g")

# Strip hero image (first line if it's an image)
BODY=$(echo "$BODY" | sed '1{/^!\[/d;}')

# Convert <video> tags to animated GIF embeds (platforms can't play hosted mp4s)
# Matches: <video ...><source src="URL.mp4" ...></video>
# Replaces with: ![animation](URL.gif)
BODY=$(echo "$BODY" | sed 's|<video[^>]*><source src="\([^"]*\)\.mp4"[^>]*></video>|![animation](\1.gif)|g')

# ── Dev.to ──────────────────────────────────────────────────────

if [ -n "${DEVTO_API_KEY:-}" ]; then
  # Build tags array (first 4 keywords, lowercase, alphanumeric only)
  DEVTO_TAGS=$(echo "$KEYWORDS" | tr ',' '\n' | head -4 | \
    sed 's/^ *//;s/ *$//;s/ //g' | tr '[:upper:]' '[:lower:]' | \
    awk '{printf "\"%s\",", $0}' | sed 's/,$//')

  DEVTO_JSON=$(jq -n \
    --arg title "$TITLE" \
    --arg body "$BODY" \
    --arg canonical "$CANONICAL_URL" \
    --argjson tags "[$DEVTO_TAGS]" \
    '{article: {title: $title, body_markdown: $body, canonical_url: $canonical, published: true, tags: $tags}}')

  if [ -n "$DEVTO_ID" ] && [ "$DEVTO_ID" != "" ]; then
    echo "Updating Dev.to article $DEVTO_ID..."
    DEVTO_RESP=$(curl -s -X PUT "https://dev.to/api/articles/$DEVTO_ID" \
      -H "Content-Type: application/json" \
      -H "api-key: $DEVTO_API_KEY" \
      -d "$DEVTO_JSON")
    echo "Dev.to updated: $(echo "$DEVTO_RESP" | jq -r '.url // empty')"
  else
    echo "Creating new Dev.to article..."
    DEVTO_RESP=$(curl -s -X POST "https://dev.to/api/articles" \
      -H "Content-Type: application/json" \
      -H "api-key: $DEVTO_API_KEY" \
      -d "$DEVTO_JSON")

    NEW_DEVTO_ID=$(echo "$DEVTO_RESP" | jq -r '.id // empty')
    DEVTO_URL=$(echo "$DEVTO_RESP" | jq -r '.url // empty')

    if [ -n "$NEW_DEVTO_ID" ]; then
      echo "Dev.to created: $DEVTO_URL (id: $NEW_DEVTO_ID)"
      fm_set "devto_id" "$NEW_DEVTO_ID"
      UPDATED_FRONTMATTER=true
    else
      echo "Dev.to error: $DEVTO_RESP"
    fi
  fi
fi

# ── Hashnode ────────────────────────────────────────────────────

if [ -n "${HASHNODE_API_KEY:-}" ] && [ -n "${HASHNODE_PUBLICATION_ID:-}" ]; then
  if [ -n "$HASHNODE_ID" ] && [ "$HASHNODE_ID" != "" ]; then
    echo "Hashnode already published ($HASHNODE_ID), skipping (no update API)."
  else
    echo "Creating new Hashnode article..."

    HASHNODE_TAGS=$(echo "$KEYWORDS" | tr ',' '\n' | head -4 | \
      sed 's/^ *//;s/ *$//' | \
      awk '{slug=$0; gsub(/ /,"-",slug); slug=tolower(slug); printf "{\"name\":\"%s\",\"slug\":\"%s\"},", $0, slug}' | \
      sed 's/,$//')

    ESCAPED_BODY=$(echo "$BODY" | jq -Rs .)

    HASHNODE_QUERY=$(cat <<GRAPHQL
mutation {
  publishPost(input: {
    publicationId: "${HASHNODE_PUBLICATION_ID}"
    title: $(echo "$TITLE" | jq -Rs .)
    contentMarkdown: ${ESCAPED_BODY}
    originalArticleURL: "${CANONICAL_URL}"
    slug: "${SLUG}"
    tags: [${HASHNODE_TAGS}]
  }) {
    post {
      id
      slug
      url
    }
  }
}
GRAPHQL
)

    HASHNODE_RESP=$(curl -s -X POST "https://gql.hashnode.com" \
      -H "Content-Type: application/json" \
      -H "Authorization: $HASHNODE_API_KEY" \
      -d "$(jq -n --arg q "$HASHNODE_QUERY" '{query: $q}')")

    NEW_HASHNODE_ID=$(echo "$HASHNODE_RESP" | jq -r '.data.publishPost.post.id // empty')
    HASHNODE_URL=$(echo "$HASHNODE_RESP" | jq -r '.data.publishPost.post.url // empty')

    if [ -n "$NEW_HASHNODE_ID" ]; then
      echo "Hashnode created: $HASHNODE_URL (id: $NEW_HASHNODE_ID)"
      fm_set "hashnode_id" "$NEW_HASHNODE_ID"
      UPDATED_FRONTMATTER=true
    else
      echo "Hashnode error: $HASHNODE_RESP"
    fi
  fi
fi

# ── Commit updated frontmatter back ────────────────────────────

if [ "$UPDATED_FRONTMATTER" = true ]; then
  echo "Committing platform IDs back to frontmatter..."
  git config user.name "cross-post-bot"
  git config user.email "bot@scotteveritt.github.io"
  git add "$POST_FILE"
  git commit -m "chore: add cross-post IDs to $(basename "$POST_FILE")"
  git push
  echo "Frontmatter updated and pushed."
fi

echo "Cross-posting complete."
