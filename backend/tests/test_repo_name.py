# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""The pattern sync must find the project's repository under its new and its old name."""

import pytest

import learning

NEW, OLD = learning.GITHUB_REPO_CANDIDATES


class Answer:
    def __init__(self, status, full_name=None):
        self.status_code = status
        self._full_name = full_name

    def json(self):
        return {"full_name": self._full_name}


@pytest.fixture(autouse=True)
def forget_the_resolved_name():
    learning._resolved_repo = None
    yield
    learning._resolved_repo = None


def fake_github(monkeypatch, answers):
    asked = []

    def get(url, **kwargs):
        name = url.split("/repos/")[1]
        asked.append(name)
        answer = answers.get(name)
        if isinstance(answer, Exception):
            raise answer
        return answer or Answer(404)

    monkeypatch.setattr(learning.httpx, "get", get)
    return asked


def test_the_new_name_is_used_once_the_repository_was_renamed(monkeypatch):
    # the old name now only redirects (301), only the new one answers 200
    asked = fake_github(monkeypatch, {NEW: Answer(200, NEW), OLD: Answer(301)})
    assert learning.github_repo() == NEW
    assert asked == [NEW]


def test_the_old_name_is_used_before_the_rename(monkeypatch):
    fake_github(monkeypatch, {NEW: Answer(404), OLD: Answer(200, OLD)})
    assert learning.github_repo() == OLD


def test_a_redirect_is_not_mistaken_for_the_repository(monkeypatch):
    fake_github(monkeypatch, {NEW: Answer(404), OLD: Answer(301)})
    assert learning.github_repo() == OLD          # the last candidate, because nothing answered 200
    assert learning._resolved_repo is None        # and it is not remembered


def test_the_canonical_name_from_the_answer_wins(monkeypatch):
    fake_github(monkeypatch, {NEW: Answer(404), OLD: Answer(200, "KaelanTesseract/Zettelfrieden")})
    assert learning.github_repo() == "KaelanTesseract/Zettelfrieden"


def test_offline_returns_a_name_without_remembering_it(monkeypatch):
    fake_github(monkeypatch, {NEW: OSError("offline"), OLD: OSError("offline")})
    assert learning.github_repo() == OLD
    assert learning._resolved_repo is None


def test_the_answer_is_remembered(monkeypatch):
    asked = fake_github(monkeypatch, {NEW: Answer(200, NEW)})
    learning.github_repo()
    learning.github_repo()
    assert asked == [NEW]
