# arkiv-upload-skill

Push media (video / audio) into an arkiv library over HTTP and trigger ingest.

## Activation

Invoke with `/arkiv-upload-skill`, or naturally:

- "upload this clip to arkiv"
- "ingest this video into arkiv"
- "add media to arkiv"

## How to use this file

This is the cross-tool companion file (AAIF format). The full contract —
endpoint, auth, constraints, curl examples, and what happens after upload — lives
in [SKILL.md](SKILL.md). Some tools (Codex CLI, Augment, Continue.dev, Zed) read
this file instead of SKILL.md, so it carries the skill's purpose, triggers,
usage, and `## Gotchas` in full.

## Usage

```
POST {ARKIV_BASE_URL}/api/ingest/upload
```

- Field `files` (multipart/form-data), one or many.
- Header `Authorization: Bearer {ARKIV_TOKEN}` with the `ingest_write` scope.
- Returns `202` immediately; background ingest then indexes the clip.

A ready-made, cross-platform helper ships with this skill — run it instead of
hand-writing curl (pure Python standard library, no dependencies):

```bash
# Token is embedded — no env needed:
python3 scripts/upload.py clip.mp4 another.mov
# Or override endpoint / token:
ARKIV_BASE_URL=http://192.168.1.3:8501 ARKIV_TOKEN=xxxx \
  python3 scripts/upload.py clip.mp4 another.mov
```

## Gotchas

- arkiv's MCP tools are read-only; uploading requires this HTTP endpoint, not MCP.
- A filename like `a/b.mp4` is reduced to its basename `b.mp4` server-side — path
  components are dropped, not rejected. You cannot choose the destination; the
  file always lands in the media-in directory.
- Only media extensions are accepted; other files get `400`, not a silent skip.
- `202` means received + ingest scheduled, not ingested. The new row appears in
  `/api/stats` only after the background ingest finishes (minutes for long clips).
- Background ingest is single-flight; a running ingest queues your file (not lost).
- The media-in mount must be `rw` for upload to write.
- `localhost` may be trusted as admin (no token); any other host needs a token
  with `ingest_write`.
