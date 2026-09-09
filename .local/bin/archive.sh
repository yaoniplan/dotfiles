#!/usr/bin/env bash

set -euo pipefail

# Print usage information
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] <URL>

Fast, lightweight CLI tool to archive URLs to the Internet Archive (archive.org).

Options:
  -f, --force    Skip existing snapshot check; force a live crawl.
  -h, --help     Show this help message.

Environment Variables:
  IA_ACCESS_KEY  (Optional) Internet Archive S3 Access Key for fast API queuing.
  IA_SECRET_KEY  (Optional) Internet Archive S3 Secret Key for fast API queuing.
EOF
  exit 1
}

FORCE_CRAWL=0
TARGET_URL=""

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--force)
      FORCE_CRAWL=1
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      if [[ -z "$TARGET_URL" ]]; then
        TARGET_URL="$1"
      else
        echo "Error: Unexpected argument '$1'" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$TARGET_URL" ]]; then
  usage
fi

USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Portable JSON extractor (uses jq if available, grep/cut as fallback)
extract_json_field() {
  local json="$1"
  local field="$2"

  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r ".${field} // empty"
  else
    echo "$json" | grep -o "\"${field}\":[[:space:]]*\"[^\"]*\"" | head -n1 | cut -d'"' -f4
  fi
}

# -------------------------------------------------------------------
# Phase 1: Availability Check (Instant)
# -------------------------------------------------------------------
if [[ $FORCE_CRAWL -eq 0 ]]; then
  AVAIL_RESP=$(curl -s -A "$USER_AGENT" "https://archive.org/wayback/available?url=$TARGET_URL")

  # Check if a snapshot exists
  if command -v jq >/dev/null 2>&1; then
    EXISTING_URL=$(echo "$AVAIL_RESP" | jq -r '.archived_snapshots.closest.url // empty')
  else
    EXISTING_URL=$(echo "$AVAIL_RESP" | grep -o '"url":[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4)
  fi

  if [[ -n "$EXISTING_URL" && "$EXISTING_URL" != "null" ]]; then
    echo "Existing snapshot found:"
    echo "$EXISTING_URL"
    exit 0
  fi
fi

# -------------------------------------------------------------------
# Phase 2: Live Archive Execution
# -------------------------------------------------------------------
ACCESS_KEY="${IA_ACCESS_KEY:-${WAYBACK_ACCESS_KEY:-}}"
SECRET_KEY="${IA_SECRET_KEY:-${WAYBACK_SECRET_KEY:-}}"

if [[ -n "$ACCESS_KEY" && -n "$SECRET_KEY" ]]; then
  # Fast Path: S3 API Queuing (~200ms)
  SAVE_RESP=$(curl -s -X POST "https://web.archive.org/save/" \
    -H "Accept: application/json" \
    -H "Authorization: LOW ${ACCESS_KEY}:${SECRET_KEY}" \
    -A "$USER_AGENT" \
    --data-urlencode "url=$TARGET_URL" \
    --data-urlencode "capture_all=0")

  JOB_ID=$(extract_json_field "$SAVE_RESP" "job_id")
  SNAPSHOT_URL=$(extract_json_field "$SAVE_RESP" "url")

  if [[ -n "$SNAPSHOT_URL" && "$SNAPSHOT_URL" != "null" ]]; then
    echo "Successfully queued/archived!"
    echo "Snapshot URL: https://web.archive.org/web/$SNAPSHOT_URL"
  elif [[ -n "$JOB_ID" ]]; then
    echo "Archive job queued successfully!"
    echo "Job ID: $JOB_ID"
    echo "Estimated URL: https://web.archive.org/web/$TARGET_URL"
  else
    echo "API Submission response: $SAVE_RESP"
  fi

else
  # Fallback Path: Synchronous Public Crawl (5-15 seconds)
  echo "No API keys found. Crawling page in real time..."
  FINAL_URL=$(curl -s -L -o /dev/null -w "%{url_effective}" -A "$USER_AGENT" "https://web.archive.org/save/$TARGET_URL")

  if [[ "$FINAL_URL" == *"web.archive.org/web/"* ]]; then
    echo "Successfully archived!"
    echo "Snapshot URL: $FINAL_URL"
  else
    echo "Archive request submitted. Result URL:"
    echo "$FINAL_URL"
  fi
fi
