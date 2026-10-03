# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

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
    monkeypatch.setattr(ocr, "_ocr_page", lambda img: seen.append(img) or ("Text", 90.0))
    original = Image.new("RGB", (10, 10))
    assert ocr.read_page_image(original) == "Text"
    assert seen == [original]


# ----- pages that were scanned turned -----------------------------------------------------------

def _readings(monkeypatch, results):
    """Stand in for Tesseract: the n-th reading of a page returns results[n]."""
    calls = []
    def fake(img):
        calls.append(img.size)
        return results[len(calls) - 1]
    monkeypatch.setattr(ocr, "_ocr_page", fake)
    return calls


def test_an_upright_page_is_read_once(monkeypatch):
    calls = _readings(monkeypatch, [("Guter Text", 91.0)])
    assert ocr.read_page_image(Image.new("RGB", (60, 100), "white")) == "Guter Text"
    assert len(calls) == 1


def test_a_blank_page_is_read_once(monkeypatch):
    calls = _readings(monkeypatch, [("", None)])
    assert ocr.read_page_image(Image.new("RGB", (60, 100), "white")) == ""
    assert len(calls) == 1


def test_a_turned_page_is_read_in_all_orientations_and_the_best_one_wins(monkeypatch):
    # readings: as scanned (nonsense), 90 (nonsense), 180 (clear), 270 (nonsense)
    calls = _readings(monkeypatch, [("Kauderwelsch", 28.0), ("Wirres", 31.0), ("Brief an Herrn", 90.0), ("Noch Wirres", 27.0)])
    assert ocr.read_page_image(Image.new("RGB", (60, 100), "white")) == "Brief an Herrn"
    assert len(calls) == 4
    assert calls[1] == (100, 60) and calls[3] == (100, 60)     # the quarter turns swap width and height


def test_a_poor_scan_is_not_replaced_by_a_reading_that_is_barely_better(monkeypatch):
    _readings(monkeypatch, [("Verblasster Text", 42.0), ("a", 45.0), ("b", 50.0), ("c", 40.0)])
    assert ocr.read_page_image(Image.new("RGB", (60, 100), "white")) == "Verblasster Text"


def _tsv(rows):
    header = "level page_num block_num par_num line_num word_num left top width height conf text".split()
    return chr(10).join(chr(9).join(row) for row in [header] + rows)


def _word(block, par, line, word, conf, text):
    return ["5", "1", str(block), str(par), str(line), str(word), "0", "0", "10", "10", str(conf), text]


def test_text_and_confidence_are_built_from_the_word_table():
    tsv = _tsv([
        ["4", "1", "1", "1", "1", "0", "0", "0", "10", "10", "-1", ""],           # a line, no word
        _word(1, 1, 1, 1, 90.5, "Hallo"), _word(1, 1, 1, 2, 70.5, "Welt"),
        _word(1, 1, 2, 1, 80.0, "zweite"), _word(1, 1, 2, 2, 80.0, "Zeile"),
        _word(1, 2, 1, 1, 60.0, "Absatz"),
        _word(2, 1, 1, 1, 50.0, "Block"),
        ["5", "1", "2", "1", "1", "2", "0", "0", "10", "10", "-1", " "],            # a gap, not a word
    ])
    text, confidence = ocr._text_and_confidence(tsv)
    assert text == "Hallo Welt\nzweite Zeile\n\nAbsatz\n\nBlock\n"
    assert confidence == pytest.approx((90.5 + 70.5 + 80 + 80 + 60 + 50) / 6)


def test_a_page_without_words_has_no_confidence():
    assert ocr._text_and_confidence(_tsv([])) == ("\n", None)


@pytest.mark.parametrize("text,expected", [
    ("zur Kraftfahrtversicherung LJ-23375 102-001", "LJ-23375102-001"),   # space inside, as OCR delivers it
    ("zur Kraftfahrtversicherung LJ-23375102-001", "LJ-23375102-001"),
])
def test_policy_numbers_with_an_ocr_space(text, expected):
    assert ocr.extract_policy_number_fallback(text) == expected


def test_a_phone_number_is_not_taken_for_a_policy_number():
    assert ocr.extract_policy_number_fallback("Tel AB-040 411 12-3") is None
