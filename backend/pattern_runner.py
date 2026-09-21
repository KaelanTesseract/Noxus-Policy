# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Worker for pattern_safety.apply_patterns: matches learned regex patterns against
a document text inside its own process, so the parent can enforce a timeout by
killing it. Reads {"text": str, "jobs": {field: [pattern, ...]}} from stdin and
writes {field: first captured value} to stdout. Deliberately imports nothing but
the standard library."""

import json
import re
import sys

try:
    import resource  # not available on Windows
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
except Exception:
    pass


def main() -> None:
    request = json.load(sys.stdin)
    text = request["text"]
    found = {}
    for field, patterns in request["jobs"].items():
        for pattern in patterns:
            try:
                match = re.search(pattern, text)
            except re.error:
                continue
            if match and match.groups() and match.group(1):
                found[field] = match.group(1)
                break
    json.dump(found, sys.stdout)


if __name__ == "__main__":
    main()
