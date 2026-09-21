# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import re
import urllib.parse


def content_disposition(kind: str, filename: str) -> str:
    """Builds a Content-Disposition value (``kind`` is "inline" or "attachment")
    that is safe for any filename. The name is client-controlled (upload), and
    pasting it between quotes let a quote or line break end the header value early
    (header injection). This follows RFC 6266: a plain ASCII fallback plus the real
    name percent-encoded in ``filename*``."""
    fallback = re.sub(r'[^A-Za-z0-9._ -]', '_', filename or "")[:150].strip() or "download"
    return f'{kind}; filename="{fallback}"; filename*=UTF-8\'\'{urllib.parse.quote(filename or "download", safe="")}'


def ics_text(value) -> str:
    """Escapes a value for an iCalendar TEXT property (RFC 5545 section 3.3.11).
    Contract names and notes come from users and from OCR of uploaded documents;
    an unescaped line break would let them inject extra calendar properties or events."""
    text = str(value if value is not None else "")
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n"))
