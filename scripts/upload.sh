#!/usr/bin/env bash
# arkiv-upload-skill — upload helper
# Push one or more local media files into an arkiv library via the
# POST /api/ingest/upload endpoint, then it is auto-ingested.
#
# Usage:
#   ARKIV_BASE_URL=http://localhost:8501 ARKIV_TOKEN=xxxx \
#     bash scripts/upload.sh clip.mp4 another.mov
#
# Environment:
#   ARKIV_BASE_URL   arkiv API base (default http://localhost:8501)
#   ARKIV_TOKEN      access token with ingest_write scope (required unless
#                    connecting from arkiv's own loopback, which may be trusted)
set -euo pipefail

BASE_URL="${ARKIV_BASE_URL:-http://localhost:8501}"

if [ "$#" -lt 1 ]; then
  echo "usage: ARKIV_BASE_URL=... ARKIV_TOKEN=... bash scripts/upload.sh FILE [FILE...]" >&2
  exit 2
fi

# Token is only mandatory when talking to a non-loopback host.
case "$BASE_URL" in
  localhost*|127.0.0.1*|[::1]*|http://localhost*|http://127.0.0.1*|http://[::1]*)
    need_token=0 ;;
  *)
    need_token=1 ;;
esac

if [ "$need_token" -eq 1 ] && [ -z "$ARKIV_TOKEN" ]; then
  echo "error: ARKIV_TOKEN is required for non-loopback ARKIV_BASE_URL ($BASE_URL)" >&2
  exit 1
fi

args=(-Ss -X POST)
if [ -n "$ARKIV_TOKEN" ]; then
  args+=(-H "Authorization: Bearer $ARKIV_TOKEN")
fi
for f in "$@"; do
  if [ ! -f "$f" ]; then
    echo "error: file not found: $f" >&2
    exit 1
  fi
  args+=(-F "files=@$f")
done
args+=("$BASE_URL/api/ingest/upload")

echo ">> POST $BASE_URL/api/ingest/upload (${#@} file(s))"
curl "${args[@]}"
echo
