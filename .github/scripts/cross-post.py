#!/usr/bin/env python3
"""
Cross-post a Jekyll markdown post to Dev.to and Hashnode.
On first publish, writes platform IDs back to frontmatter and commits.
On subsequent pushes, updates Dev.to (PUT), skips Hashnode (no reliable update).

Usage: cross-post.py <path-to-post.md>

Env vars: DEVTO_API_KEY, HASHNODE_API_KEY, HASHNODE_PUBLICATION_ID, SITE_URL
"""

import json
import os
import re
import subprocess
import sys
import urllib.request

POST_FILE = sys.argv[1]
SITE_URL = os.environ.get("SITE_URL", "https://scotteveritt.github.io")
DEVTO_API_KEY = os.environ.get("DEVTO_API_KEY", "")
HASHNODE_API_KEY = os.environ.get("HASHNODE_API_KEY", "")
HASHNODE_PUB_ID = os.environ.get("HASHNODE_PUBLICATION_ID", "")


def read_post(path):
    with open(path) as f:
        content = f.read()
    # Split frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"ERROR: Could not parse frontmatter in {path}")
        sys.exit(1)
    fm_raw = parts[1].strip()
    body = parts[2].strip()
    return fm_raw, body


def parse_frontmatter(fm_raw):
    """Simple single-line YAML parser (no nested structures)."""
    fm = {}
    for line in fm_raw.split("\n"):
        line = line.strip()
        if ":" not in line or line.startswith("-") or line.startswith("#"):
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val and not val.startswith("\n"):
            fm[key] = val
    return fm


def prepare_body(body):
    """Convert body for cross-platform publishing."""
    # Strip hero image (first line if markdown image)
    body = re.sub(r"^\!\[.*?\]\(.*?\)\s*", "", body)
    # Convert <video> tags to GIF markdown
    body = re.sub(
        r'<video[^>]*><source src="(/assets/animations/[^"]+)\.mp4"[^>]*></video>',
        rf"![animation]({SITE_URL}\1.gif)",
        body,
    )
    # Convert relative paths to absolute
    body = body.replace("](/assets/", f"]({SITE_URL}/assets/")
    body = body.replace('src="/assets/', f'src="{SITE_URL}/assets/')
    return body


def update_frontmatter(path, key, value):
    """Insert or update a key in the file's YAML frontmatter."""
    with open(path) as f:
        content = f.read()
    parts = content.split("---", 2)
    fm_lines = parts[1].strip().split("\n")

    # Check if key exists
    found = False
    for i, line in enumerate(fm_lines):
        if line.startswith(f"{key}:"):
            fm_lines[i] = f"{key}: {value}"
            found = True
            break
    if not found:
        fm_lines.append(f"{key}: {value}")

    parts[1] = "\n" + "\n".join(fm_lines) + "\n"
    with open(path, "w") as f:
        f.write("---".join(parts))


def api_request(url, data=None, headers=None, method=None):
    """Simple HTTP request helper."""
    if data is not None:
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.request.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body[:500]}")
        return None


def post_to_devto(fm, body):
    if not DEVTO_API_KEY:
        print("DEVTO_API_KEY not set, skipping Dev.to")
        return None

    # Tags: first 4 keywords, lowercase, no spaces
    tags = []
    if fm.get("keywords"):
        tags = [
            re.sub(r"[^a-z0-9]", "", t.strip().lower())
            for t in fm["keywords"].split(",")
        ][:4]

    article = {
        "title": fm["title"],
        "body_markdown": body,
        "canonical_url": fm.get("canonical_url", ""),
        "published": True,
        "tags": tags,
    }

    # Set cover image (prefer cover, fall back to hero)
    cover = fm.get("cover") or fm.get("hero")
    if cover:
        if cover.startswith("/"):
            cover = SITE_URL + cover
        article["main_image"] = cover

    payload = {"article": article}

    headers = {"Content-Type": "application/json", "api-key": DEVTO_API_KEY}
    devto_id = fm.get("devto_id", "")

    if devto_id:
        print(f"Updating Dev.to article {devto_id}...")
        resp = api_request(
            f"https://dev.to/api/articles/{devto_id}",
            data=payload,
            headers=headers,
            method="PUT",
        )
        if resp:
            print(f"Dev.to updated: {resp.get('url', '?')}")
        return devto_id
    else:
        print("Creating new Dev.to article...")
        resp = api_request(
            "https://dev.to/api/articles",
            data=payload,
            headers=headers,
            method="POST",
        )
        if resp and resp.get("id"):
            print(f"Dev.to created: {resp['url']} (id: {resp['id']})")
            return str(resp["id"])
        else:
            print(f"Dev.to error: {resp}")
            return None


def post_to_hashnode(fm, body):
    if not HASHNODE_API_KEY or not HASHNODE_PUB_ID:
        print("Hashnode credentials not set, skipping")
        return None

    hashnode_id = fm.get("hashnode_id", "")
    if hashnode_id:
        print(f"Hashnode already published ({hashnode_id}), skipping.")
        return hashnode_id

    print("Creating new Hashnode article...")

    # Build tags
    tags = []
    if fm.get("keywords"):
        for t in fm["keywords"].split(",")[:4]:
            name = t.strip()
            slug = re.sub(r"[^a-z0-9-]", "", name.lower().replace(" ", "-"))
            tags.append({"name": name, "slug": slug})

    query = """mutation PublishPost($input: PublishPostInput!) {
        publishPost(input: $input) {
            post { id slug url }
        }
    }"""

    input_data = {
        "publicationId": HASHNODE_PUB_ID,
        "title": fm["title"],
        "contentMarkdown": body,
        "originalArticleURL": fm.get("canonical_url", ""),
        "slug": fm.get("slug", ""),
        "tags": tags,
    }

    # Set cover image (prefer cover, fall back to hero)
    cover = fm.get("cover") or fm.get("hero")
    if cover:
        if cover.startswith("/"):
            cover = SITE_URL + cover
        input_data["coverImageOptions"] = {"coverImageURL": cover}

    variables = {"input": input_data}

    headers = {
        "Content-Type": "application/json",
        "Authorization": HASHNODE_API_KEY,
    }

    resp = api_request(
        "https://gql.hashnode.com",
        data={"query": query, "variables": variables},
        headers=headers,
    )

    if resp and resp.get("data", {}).get("publishPost", {}).get("post"):
        post = resp["data"]["publishPost"]["post"]
        print(f"Hashnode created: {post['url']} (id: {post['id']})")
        return post["id"]
    else:
        print(f"Hashnode error: {resp}")
        return None


def git_commit_ids():
    """Commit updated frontmatter back to the repo."""
    subprocess.run(["git", "config", "user.name", "cross-post-bot"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "bot@scotteveritt.github.io"], check=True
    )
    subprocess.run(["git", "add", POST_FILE], check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"chore: add cross-post IDs to {os.path.basename(POST_FILE)}",
        ],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)
    print("Frontmatter updated and pushed.")


def main():
    if not os.path.exists(POST_FILE):
        print(f"File not found: {POST_FILE}")
        sys.exit(1)

    fm_raw, raw_body = read_post(POST_FILE)
    fm = parse_frontmatter(fm_raw)

    # Build slug and canonical URL
    slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", os.path.basename(POST_FILE).replace(".md", ""))
    canonical = f"{SITE_URL}/blog/{slug}/"
    fm["slug"] = slug
    fm["canonical_url"] = canonical

    print(f"Title:       {fm.get('title', '?')}")
    print(f"Slug:        {slug}")
    print(f"Canonical:   {canonical}")
    print(f"Dev.to ID:   {fm.get('devto_id', '<none>')}")
    print(f"Hashnode ID: {fm.get('hashnode_id', '<none>')}")

    body = prepare_body(raw_body)
    updated = False

    # Dev.to
    new_devto_id = post_to_devto(fm, body)
    if new_devto_id and not fm.get("devto_id"):
        update_frontmatter(POST_FILE, "devto_id", new_devto_id)
        updated = True

    # Hashnode
    new_hashnode_id = post_to_hashnode(fm, body)
    if new_hashnode_id and not fm.get("hashnode_id"):
        update_frontmatter(POST_FILE, "hashnode_id", new_hashnode_id)
        updated = True

    # Commit IDs back
    if updated:
        git_commit_ids()

    print("Cross-posting complete.")


if __name__ == "__main__":
    main()
