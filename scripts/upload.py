#!/usr/bin/env python3
"""arkiv-upload-skill - cross-platform upload helper.

Push one or more local media files into an arkiv library via the
POST /api/ingest/upload endpoint, then it is auto-ingested.

Usage:
    # Token is embedded (LAN build) — no env needed:
    python3 scripts/upload.py clip.mp4 another.mov
    # Override endpoint / token if needed:
    ARKIV_BASE_URL=http://192.168.1.3:8501 ARKIV_TOKEN=xxxx \
        python3 scripts/upload.py clip.mp4 another.mov

Environment:
    ARKIV_BASE_URL   arkiv API base (default http://192.168.1.3:8501)
    ARKIV_TOKEN      access token with ingest_write scope. Defaults to the
                     embedded LAN token; override only to rotate / use another.

Pure standard library - no third-party dependencies, so it runs on any
platform that has Python 3 (Linux, macOS, Windows, *BSD, ...).
"""
import mimetypes
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://192.168.1.3:8501"
# Embedded access token (ingest_write scope) so the helper works on a LAN
# without the caller setting ARKIV_TOKEN. Override via the ARKIV_TOKEN env
# var if you need a different / rotated token. LAN-only deployment — the
# operator accepts the plaintext token living in this file.
DEFAULT_TOKEN = "khTrie1s82jyiUwlO4a0GEyJxC3ZXEqYO3A6Uqou17g"
LOOPBACK_TOKENS = ("localhost", "127.0.0.1", "[::1]", "0.0.0.0")


def is_loopback(url: str) -> bool:
    lowered = url.lower()
    return any(token in lowered for token in LOOPBACK_TOKENS)


def main() -> int:
    base = os.environ.get("ARKIV_BASE_URL", DEFAULT_BASE).rstrip("/")
    token = os.environ.get("ARKIV_TOKEN", DEFAULT_TOKEN)
    files = sys.argv[1:]

    if not files:
        sys.stderr.write(
            "usage: ARKIV_BASE_URL=... ARKIV_TOKEN=... "
            "python3 scripts/upload.py FILE [FILE...]\n"
        )
        return 2

    if not is_loopback(base) and not token:
        sys.stderr.write(
            "error: ARKIV_TOKEN is required for non-loopback ARKIV_BASE_URL (%s)\n" % base
        )
        return 1

    url = base + "/api/ingest/upload"
    boundary = "----arkivuploadboundary"
    body = bytearray()
    for path in files:
        if not os.path.isfile(path):
            sys.stderr.write("error: file not found: %s\n" % path)
            return 1
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            data = fh.read()
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="files"; filename="%s"\r\n' % filename).encode()
        body += ("Content-Type: %s\r\n\r\n" % ctype).encode()
        body += data
        body += b"\r\n"
    body += ("--%s--\r\n" % boundary).encode()

    headers = {
        "Content-Type": "multipart/form-data; boundary=%s" % boundary,
        "Content-Length": str(len(body)),
    }
    if token:
        headers["Authorization"] = "Bearer " + token

    req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
    print(">> POST %s (%d file(s))" % (url, len(files)))
    try:
        with urllib.request.urlopen(req) as resp:
            print(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        sys.stderr.write(
            "error: HTTP %s\n%s\n" % (exc.code, exc.read().decode("utf-8", "replace"))
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
