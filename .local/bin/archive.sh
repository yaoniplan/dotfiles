#!/usr/bin/env bash

set -euo pipefail

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

# Helper: extracts JSON fields using jq if available, grep/cut as fallback
extract_json_field() {
  local json="$1"
  local field="$2"

  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r ".${field} // empty" 2>/dev/null || true
  else
    echo "$json" | grep -o "\"${field}\":[[:space:]]*\"[^\"]*\"" | head -n1 | cut -d'"' -f4 || true
  fi
}

# -------------------------------------------------------------------
# Phase 1: Availability Check (Instant ~100-200ms)
# -------------------------------------------------------------------
if [[ $FORCE_CRAWL -eq 0 ]]; then
  AVAIL_RESP=$(curl -s -L -A "$USER_AGENT" "https://archive.org/wayback/available?url=$TARGET_URL")

  if command -v jq >/dev/null 2>&1; then
    EXISTING_URL=$(echo "$AVAIL_RESP" | jq -r '.archived_snapshots.closest.url // empty' 2>/dev/null || true)
  else
    EXISTING_URL=$(echo "$AVAIL_RESP" | grep -o '"url":[[:space:]]*"[^"]*"' | head -n1 | cut -d'"' -f4 || true)
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
  SAVE_RESP=$(curl -s -L -X POST "https://web.archive.org/save/" \
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
  # Fallback Path: Synchronous Public Crawl with Header Parsing (5-15s)
  echo "No API keys found. Crawling page in real time..."

  RESPONSE_HEADERS=$(curl -s -L -i -A "$USER_AGENT" "https://web.archive.org/save/$TARGET_URL")
  REL_PATH=$(echo "$RESPONSE_HEADERS" | grep -iE '^(content-location|location):' | head -n1 | tr -d '\r' | awk '{print $2}' || true)

  if [[ -n "$REL_PATH" ]]; then
    if [[ "$REL_PATH" == http* ]]; then
      SNAPSHOT_URL="$REL_PATH"
    else
      SNAPSHOT_URL="https://web.archive.org${REL_PATH}"
    fi
    echo "Successfully archived!"
    echo "Snapshot URL: $SNAPSHOT_URL"
  else
    echo "Archive request submitted!"
    echo "Snapshot URL: https://web.archive.org/web/$TARGET_URL"
  fi
fi
