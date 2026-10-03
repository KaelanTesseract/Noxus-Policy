# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Every source file carries the licence header, so the licence stays unambiguous.

Own files carry "Copyright (c) <year> Dennis Guse" and "SPDX-License-Identifier: MIT". The files in
``frontend/src/components/ui`` are derived from shadcn/ui and keep that project's notice instead
(see THIRD_PARTY_NOTICES.md). A new file without a header fails here.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".sh", ".css", ".yml"}
GENERATED = {"next-env.d.ts"}
SKIPPED_DIRS = {"node_modules", ".next", ".git", "__pycache__", "venv", ".venv", "documents", "data", "eval", "models"}
HEADER_LINES = 12

OWN = re.compile(r"Copyright \(c\) 20\d\d Dennis Guse(?!\. All rights reserved)")
SHADCN = re.compile(r"Based on shadcn/ui .*Copyright \(c\) 2023 shadcn")


def _source_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and path.name not in GENERATED and not SKIPPED_DIRS & set(path.relative_to(ROOT).parts):
            yield path


FILES = sorted(_source_files()) if (ROOT / "frontend").is_dir() else []


@pytest.mark.skipif(not FILES, reason="the repository root is not available")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_source_file_has_licence_header(path):
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:HEADER_LINES])
    relative = path.relative_to(ROOT).as_posix()
    expected = SHADCN if relative.startswith("frontend/src/components/ui/") else OWN
    assert expected.search(head), f"{relative}: licence header missing or outdated"
    assert "SPDX-License-Identifier: MIT" in head, f"{relative}: SPDX line missing"
    assert "All rights reserved" not in head


def test_licence_file_names_the_copyright_holder():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.startswith("MIT License") and "Copyright (c) 2026 Dennis Guse" in text
