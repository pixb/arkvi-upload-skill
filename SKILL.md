---
name: arkiv-upload-skill
description: >-
  Add video/audio clips to an arkiv library and trigger ingest without manual
  file copying. Use when a user wants to push local media into arkiv, or an
  agent needs to ingest media into arkiv over HTTP. Activates on phrases like
  upload to arkiv, 上传到 arkiv, ingest this clip, add media to arkiv, push file
  into arkiv.
license: MIT
activation: /arkiv-upload-skill
metadata:
  author: pix
  version: 1.0.0
  created: 2026-08-27
  last_reviewed: 2026-08-27
  review_interval_days: 180
  dependencies:
    - name: arkiv API
      url: http://192.168.1.3:8501
      type: service
provenance:
  maintainer: pix
  version: 1.0.0
  created: 2026-08-27
  source_references:
    - https://github.com/pixb/arkiv
compatibility: >-
  Works on all platforms supporting the Agent Skills Open Standard (SKILL.md):
  Claude Code, GitHub Copilot CLI, VS Code Copilot, Cursor, Windsurf, Cline,
  OpenAI Codex CLI, Gemini CLI, OpenCode, and more.
---

# /arkiv-upload-skill

Push media (video / audio) into an **arkiv** library and have it auto-ingested
(transcribed + indexed) so it becomes searchable. arkiv's MCP tools are
**read-only** — uploading goes through this HTTP endpoint, not through MCP.

## When to use

- The user says "upload / 上传 / 加入 / ingest this clip into arkiv".
- You have a local media file and need to push it into arkiv.
- You want to add new source material to the arkiv library programmatically.

## Endpoint

```
POST {ARKIV_BASE_URL}/api/ingest/upload
```

- `ARKIV_BASE_URL` — arkiv API base. Defaults to `http://192.168.1.3:8501` for a
  local deployment; for a LAN / remote arkiv use its host:port.
- Field name: `files` (multipart/form-data). One or many files per request.
- Auth: a header `Authorization: Bearer {ARKIV_TOKEN}` where `ARKIV_TOKEN` is any
  arkiv access token that has the `ingest_write` scope (e.g. the `ui-test`
  token). Loopback connections may be trusted as admin automatically; for LAN
  use the token.

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

A ready-made, cross-platform helper ships with this skill — read
`scripts/upload.py` (pure standard library, runs on Linux / macOS / Windows /
\*BSD) and run it:

```bash
ARKIV_BASE_URL=http://192.168.1.3:8501 ARKIV_TOKEN=xxx \
  python3 scripts/upload.py clip.mp4 another.mov
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

The call returns immediately after the file is written; ingest (whisper
transcription + vision + embedding) runs in the background and may take a while
for long clips. Poll `GET {ARKIV_BASE_URL}/api/stats` (the `total` count) to see
the new row appear.

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

If the file is **already on the arkiv server's filesystem** (not on the
agent's machine), you can skip the upload and tell arkiv to ingest a directory it
can already see:

```bash
curl -Ss -X POST \
  -H "Authorization: Bearer $ARKIV_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":"/app/media-in"}' \
  "$ARKIV_BASE_URL/api/ingest"
```

This only works for paths under arkiv's approved ingest roots (the media-in
directory is one of them). Use the multipart upload above when the file lives
on the agent / client side.

## Gotchas

- arkiv's MCP tools are read-only; uploading requires this HTTP endpoint, not MCP.
- A filename like `a/b.mp4` is reduced to its basename `b.mp4` server-side
  (path components are dropped, not rejected) — you cannot control where the
  file lands; it always goes to the media-in directory.
- Only media extensions are accepted; other files get `400`, not a silent skip.
- The `202` response means "received + ingest scheduled", not "ingested". The
  new row appears in `/api/stats` only after the background ingest finishes,
  which for long clips can take minutes.
- Background ingest is single-flight: if an ingest is already running, your
  uploaded file waits in the queue (it is not lost).
- The media-in mount must be `rw` for upload to write (the arkiv compose deploy
  sets `./media-in:/app/media-in:rw`).
- From `localhost` the request may be trusted as admin without a token; from any
  other host the request requires a token that has the `ingest_write` scope.

## Notes

- This is an HTTP API, independent of arkiv's MCP server. To let an agent
  "upload through MCP" you would need an `upload_media` MCP tool — that is a
  separate addition, not covered here.
- The upload directory default (`/app/media-in`) is shared with manual ingest;
  each upload triggers a whole-directory ingest, but already-processed files are
  de-duplicated, so repeated uploads are cheap.
