# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Straightening of page images before OCR, and policy numbers as scans deliver them."""

import random

import pytest
from PIL import Image, ImageDraw

import image_prep
import ocr


def page_with_text_lines(width=1100, height=1500, seed=3):
    """A white page with rows of dark 'words' - what the tilt estimation looks at."""
    rnd = random.Random(seed)
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    for y in range(120, height - 120, 34):
        x = 100
        while x < width - 160:
            w = rnd.randint(30, 140)
            draw.rectangle([x, y, x + w, y + 16], fill=20)
            x += w + 18
    return img


@pytest.mark.parametrize("angle", [-6.0, -2.5, -0.8, 0.8, 1.8, 3.5, 6.0])
def test_the_tilt_of_a_page_is_found(angle):
    tilted = page_with_text_lines().rotate(angle, resample=Image.BICUBIC, fillcolor=255)
    # rotating by the estimate must undo the tilt
    assert image_prep.estimate_tilt(tilted) == pytest.approx(-angle, abs=0.3)


def test_a_straight_page_is_left_alone():
    assert image_prep.estimate_tilt(page_with_text_lines()) == 0.0


def test_a_blank_page_has_no_tilt():
    assert image_prep.estimate_tilt(Image.new("L", (800, 1000), 255)) == 0.0


def test_prepared_pages_keep_their_size_and_are_grey():
    tilted = page_with_text_lines().rotate(2.0, resample=Image.BICUBIC, fillcolor=255).convert("RGB")
    prepared = image_prep.prepare_for_ocr(tilted)
    assert prepared.mode == "L" and prepared.size == tilted.size


def test_the_original_image_is_read_when_the_preparation_fails(monkeypatch):
    seen = []
    monkeypatch.setattr(ocr, "prepare_for_ocr", lambda img: (_ for _ in ()).throw(RuntimeError("kaputt")))
    monkeypatch.setattr(ocr.pytesseract, "image_to_string", lambda img, **kw: seen.append(img) or "Text")
    original = Image.new("RGB", (10, 10))
    assert ocr.read_page_image(original) == "Text"
    assert seen == [original]


@pytest.mark.parametrize("text,expected", [
    ("zur Kraftfahrtversicherung LJ-23375 102-001", "LJ-23375102-001"),   # space inside, as OCR delivers it
    ("zur Kraftfahrtversicherung LJ-23375102-001", "LJ-23375102-001"),
])
def test_policy_numbers_with_an_ocr_space(text, expected):
    assert ocr.extract_policy_number_fallback(text) == expected


def test_a_phone_number_is_not_taken_for_a_policy_number():
    assert ocr.extract_policy_number_fallback("Tel AB-040 411 12-3") is None
