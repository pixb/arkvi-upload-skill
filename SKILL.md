---
name: arkiv-upload
description: Upload media files into an arkiv library over HTTP and trigger ingest. Use when a user wants to add video/audio clips to arkiv, push local media files into arkiv, or when an agent needs to ingest media into arkiv without manually copying files into a directory. Documents the arkiv POST /api/ingest/upload endpoint, Bearer-token auth, file/extension/size constraints, the concurrency limit, and how the background ingest picks the file up.
---

# Arkiv Upload Skill

This skill lets a skills-compatible agent push media (video / audio) into an
**arkiv** library and have it auto-ingested (transcribed + indexed) so it
becomes searchable. arkiv's MCP tools are **read-only** — uploading goes through
this HTTP endpoint, not through MCP.

## When to use
- The user says "upload / 上传 / 加入 / ingest this clip into arkiv".
- You have a local media file and need to push it into arkiv.
- You want to add new source material to the arkiv library programmatically.

## Endpoint

```
POST {ARKIV_BASE_URL}/api/ingest/upload
```

- `ARKIV_BASE_URL` — arkiv API base. Defaults to `http://localhost:8501` for a
  local deployment; for a LAN/remote arkiv use its host:port (e.g.
  `http://192.168.x.x:8501`).
- Field name: `files` (multipart/form-data). One or many files per request.
- Auth: `Authorization: Bearer {ARKIV_TOKEN}` where `ARKIV_TOKEN` is any arkiv
  access token that has the `ingest_write` scope (e.g. the `ui-test` token).
  Loopback connections may be trusted as admin automatically; for LAN use the
  token.

### Request example

```bash
curl -Ss -X POST \
  -H "Authorization: Bearer $ARKIV_TOKEN" \
  -F "files=@/path/to/clip.mp4" \
  "$ARKIV_BASE_URL/api/ingest/upload"
```

Multiple files in one call:

```bash
curl -Ss -X POST \
  -H "Authorization: Bearer $ARKIV_TOKEN" \
  -F "files=@a.mp4" -F "files=@b.mov" \
  "$ARKIV_BASE_URL/api/ingest/upload"
```

### Success response (202 Accepted)

```json
{
  "ok": true,
  "saved": ["clip.mp4"],
  "upload_dir": "/app/media-in",
  "ingest": "triggered"
}
```

Upload returns immediately after the file is written; ingest (whisper
transcription + vision + embedding) runs in the background and may take a while
for long clips. Poll `GET {ARKIV_BASE_URL}/api/stats` (`total` count) to see the
new row appear.

## Constraints (enforced by the server)

| Rule | Detail | Failure |
|------|--------|---------|
| Scope | token needs `ingest_write` | 401 / 403 |
| Filename | only the basename is used — `../` and absolute paths are stripped, no traversal | 400 `非法檔名` |
| Extension | only known media extensions (video/audio) are accepted | 400 `不支援的檔案類型` |
| Per-file size | `ARKIV_UPLOAD_MAX_MB` (default **4096 MB**) | 413 if exceeded |
| Concurrency | at most `ARKIV_UPLOAD_MAX_CONCURRENT` (default **3**) uploads run at once; extras queue up to `ARKIV_UPLOAD_MAX_QUEUE_SEC` (default **300 s**) | 429 `上傳並發已達上限` |

If you get `429`, back off and retry the upload after a short delay — another
upload is currently being received.

## What happens after upload

1. The file is written into the ingest source directory (default
   `/app/media-in`, i.e. the host's `./media-in` bind mount).
2. A background ingest is triggered over that directory. arkiv's ingest is
   **single-flight** (one ingest at a time, to avoid concurrent whisper OOM), so
   if an ingest is already running the new file is picked up when the slot frees.
3. The clip is transcribed, thumbnailed, vision-tagged and embedded, then shows
   up in `search_media` / `library_stats`.

## Alternative: server-side path ingest

If the file is **already on the arkiv server's filesystem** (not on the agent's
machine), you can skip the upload and tell arkiv to ingest a directory it can
already see:

```bash
curl -Ss -X POST \
  -H "Authorization: Bearer $ARKIV_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":"/app/media-in"}' \
  "$ARKIV_BASE_URL/api/ingest"
```

This only works for paths under arkiv's approved ingest roots (the media-in
directory is one of them). Use the multipart upload above when the file lives
on the agent/client side.

## Notes
- This is an HTTP API, independent of arkiv's MCP server. To let an agent
  "upload through MCP" you would need an `upload_media` MCP tool — that is a
  separate addition, not covered here.
- The upload directory default (`/app/media-in`) is shared with manual ingest;
  each upload triggers a whole-directory ingest, but already-processed files are
  de-duplicated, so repeated uploads are cheap.
