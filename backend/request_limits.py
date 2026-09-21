# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Upper bounds for request bodies.

Starlette parses a multipart upload completely (spooling it to disk) before an
endpoint gets to look at it, so a size check inside the endpoint comes too late:
anyone able to reach the API could fill the disk or the memory with a single
oversized request. This ASGI middleware refuses such requests up front, based on
the Content-Length header and - for chunked bodies without one - on the number of
bytes actually received.

The frontend proxy (frontend/src/app/api/[...path]/route.ts) applies the same
limits; keep both in sync when changing them."""

import json

MB = 1024 * 1024

# One document per upload request (see upload_validation.MAX_UPLOAD_BYTES) plus
# room for the multipart framing and form fields.
MAX_UPLOAD_BODY_BYTES = 16 * MB
# Encrypted backup archives (system restore and user import).
MAX_BACKUP_BODY_BYTES = 512 * MB
# Everything else is small JSON.
MAX_DEFAULT_BODY_BYTES = 2 * MB

_UPLOAD_PATHS = ("/api/documents", "/api/documents/extract", "/api/inbox/upload")
_BACKUP_PATHS = ("/api/backup/import", "/api/backup/import-user")


def body_limit_for(method: str, path: str) -> int:
    if method == "POST":
        normalized = path.rstrip("/") or "/"
        if normalized in _BACKUP_PATHS:
            return MAX_BACKUP_BODY_BYTES
        if normalized in _UPLOAD_PATHS:
            return MAX_UPLOAD_BODY_BYTES
    return MAX_DEFAULT_BODY_BYTES


class _BodyTooLarge(Exception):
    pass


_TOO_LARGE_BODY = json.dumps({"detail": "Die Anfrage ist zu groß."}).encode()


class RequestSizeLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = body_limit_for(scope["method"], scope["path"])

        declared = None
        for name, value in scope["headers"]:
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
                break
        if declared is not None and declared > limit:
            await self._reject(send)
            return

        received = 0
        exceeded = False
        replacement_sent = False

        async def limited_receive():
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise _BodyTooLarge()
            return message

        async def guarded_send(message):
            # FastAPI turns an exception raised while reading the body into a
            # generic 400. Once the limit was hit, replace whatever the app
            # answers with a proper 413.
            nonlocal replacement_sent
            if not exceeded:
                await send(message)
                return
            if replacement_sent:
                return
            if message["type"] == "http.response.start":
                await self._reject(send)
                replacement_sent = True

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if not replacement_sent:
                await self._reject(send)

    @staticmethod
    async def _reject(send):
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(_TOO_LARGE_BODY)).encode()),
                (b"connection", b"close"),
            ],
        })
        await send({"type": "http.response.body", "body": _TOO_LARGE_BODY})
