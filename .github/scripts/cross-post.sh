#!/usr/bin/env bash
#
# Cross-post a Jekyll markdown post to Dev.to and Hashnode.
# Usage: cross-post.sh <path-to-post.md>
#
# Expects env vars:
#   DEVTO_API_KEY
#   HASHNODE_API_KEY
#   HASHNODE_PUBLICATION_ID
#   SITE_URL  (e.g. https://scotteveritt.github.io)

set -euo pipefail

POST_FILE="$1"

if [ ! -f "$POST_FILE" ]; then
  echo "File not found: $POST_FILE"
  exit 1
fi

# ── Parse front matter ──────────────────────────────────────────

# Extract value from YAML front matter (simple single-line values)
fm_value() {
  sed -n '/^---$/,/^---$/p' "$POST_FILE" | grep "^$1:" | head -1 | sed "s/^$1: *//; s/^\"//; s/\"$//"
}

TITLE=$(fm_value title)
DESCRIPTION=$(fm_value description)
DATE=$(fm_value date)
DEVTO_ID=$(fm_value devto_id)
HASHNODE_ID=$(fm_value hashnode_id)

# Extract keywords → tags (first 4, lowercase, no spaces)
KEYWORDS=$(fm_value keywords)

# Build slug from filename
SLUG=$(basename "$POST_FILE" .md | sed 's/^[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-//')
CANONICAL_URL="${SITE_URL}/blog/${SLUG}/"

echo "Title:     $TITLE"
echo "Slug:      $SLUG"
echo "Canonical: $CANONICAL_URL"

# ── Extract body (strip front matter) ───────────────────────────

BODY=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$POST_FILE")

# Convert relative image/video paths to absolute
BODY=$(echo "$BODY" | sed "s|](/assets/|](${SITE_URL}/assets/|g")
BODY=$(echo "$BODY" | sed "s|src=\"/assets/|src=\"${SITE_URL}/assets/|g")

# Strip hero image (first line if it's an image)
BODY=$(echo "$BODY" | sed '1{/^!\[/d;}')

# Strip video tags (Dev.to/Hashnode can't play hosted mp4s)
BODY=$(echo "$BODY" | sed '/<video/d')

# ── Dev.to ──────────────────────────────────────────────────────

if [ -n "${DEVTO_API_KEY:-}" ]; then
  # Build tags array (first 4 keywords, lowercase, alphanumeric only)
  DEVTO_TAGS=$(echo "$KEYWORDS" | tr ',' '\n' | head -4 | \
    sed 's/^ *//;s/ *$//;s/ //g' | tr '[:upper:]' '[:lower:]' | \
    awk '{printf "\"%s\",", $0}' | sed 's/,$//')

  # Build JSON payload
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
  else
    echo "Creating new Dev.to article..."
    DEVTO_RESP=$(curl -s -X POST "https://dev.to/api/articles" \
      -H "Content-Type: application/json" \
      -H "api-key: $DEVTO_API_KEY" \
      -d "$DEVTO_JSON")
  fi

  NEW_DEVTO_ID=$(echo "$DEVTO_RESP" | jq -r '.id // empty')
  DEVTO_URL=$(echo "$DEVTO_RESP" | jq -r '.url // empty')

  if [ -n "$NEW_DEVTO_ID" ]; then
    echo "Dev.to: $DEVTO_URL (id: $NEW_DEVTO_ID)"
    echo "DEVTO_ID=$NEW_DEVTO_ID" >> "$GITHUB_OUTPUT"
  else
    echo "Dev.to error: $DEVTO_RESP"
  fi
fi

# ── Hashnode ────────────────────────────────────────────────────

if [ -n "${HASHNODE_API_KEY:-}" ] && [ -n "${HASHNODE_PUBLICATION_ID:-}" ]; then
  # Build tags (Hashnode wants [{name, slug}])
  HASHNODE_TAGS=$(echo "$KEYWORDS" | tr ',' '\n' | head -4 | \
    sed 's/^ *//;s/ *$//' | \
    awk '{slug=$0; gsub(/ /,"-",slug); slug=tolower(slug); printf "{\"name\":\"%s\",\"slug\":\"%s\"},", $0, slug}' | \
    sed 's/,$//')

  # Escape body for JSON
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

  if [ -n "$HASHNODE_ID" ] && [ "$HASHNODE_ID" != "" ]; then
    echo "Hashnode article already exists ($HASHNODE_ID), skipping (no update API)."
  else
    echo "Creating new Hashnode article..."
    HASHNODE_RESP=$(curl -s -X POST "https://gql.hashnode.com" \
      -H "Content-Type: application/json" \
      -H "Authorization: $HASHNODE_API_KEY" \
      -d "$(jq -n --arg q "$HASHNODE_QUERY" '{query: $q}')")

    NEW_HASHNODE_ID=$(echo "$HASHNODE_RESP" | jq -r '.data.publishPost.post.id // empty')
    HASHNODE_URL=$(echo "$HASHNODE_RESP" | jq -r '.data.publishPost.post.url // empty')

    if [ -n "$NEW_HASHNODE_ID" ]; then
      echo "Hashnode: $HASHNODE_URL (id: $NEW_HASHNODE_ID)"
      echo "HASHNODE_ID=$NEW_HASHNODE_ID" >> "$GITHUB_OUTPUT"
    else
      echo "Hashnode error: $HASHNODE_RESP"
    fi
  fi
fi

echo "Cross-posting complete."
