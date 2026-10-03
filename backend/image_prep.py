# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Straightens a page image before Tesseract reads it.

A phone photo or a hurriedly scanned page is rarely straight, and Tesseract loses
a lot of words on tilted lines (measured on degraded copies of a real letter:
32-83 % of the words found at a 2-4 degree tilt, 90-94 % once straightened).
Straight scans come out the same as before.

Pillow only, so nothing is added to the Docker image. The tilt is estimated on a
small copy (projection profile: at the right angle the text lines are the most
"striped"), which keeps the cost the same for any page size.
"""

from PIL import Image, ImageOps

PROFILE_SIDE_PX = 700     # the tilt is estimated on a copy this big
MAX_TILT_DEG = 8.0        # beyond this a page is more likely turned than tilted
MIN_TILT_DEG = 0.25       # smaller tilts are left alone
MIN_GAIN = 1.03           # the best angle must be this much "more striped" than no rotation


def _row_score(img: Image.Image, angle: float) -> float:
    rotated = img.rotate(angle, resample=Image.BILINEAR, fillcolor=0) if angle else img
    rows = list(rotated.resize((1, rotated.height), Image.BOX).tobytes())
    mean = sum(rows) / len(rows)
    return sum((r - mean) ** 2 for r in rows)


def estimate_tilt(img: Image.Image) -> float:
    """Tilt of the text lines in degrees (positive = the lines rise to the left; rotate
    the image by this angle to straighten it). 0.0 when the page has no clear lines."""
    profile = ImageOps.invert(ImageOps.autocontrast(img.convert("L"), cutoff=2))
    profile.thumbnail((PROFILE_SIDE_PX, PROFILE_SIDE_PX))

    base = _row_score(profile, 0.0)
    if base <= 0:
        return 0.0
    # coarse search over the whole range, then a fine search around the best angle. The peak
    # is narrow (a tilt of 1 degree moves the line ends by more than a line height), so the
    # coarse step must be small.
    steps = int(MAX_TILT_DEG * 2)
    coarse = {k / 2: _row_score(profile, k / 2) for k in range(-steps, steps + 1)}
    centre = max(coarse, key=coarse.get)
    fine = {centre + k * 0.125: None for k in range(-4, 5)}
    for angle in fine:
        fine[angle] = _row_score(profile, angle)
    best = max(fine, key=fine.get)
    if abs(best) < MIN_TILT_DEG or fine[best] < base * MIN_GAIN:
        return 0.0
    return best


def prepare_for_ocr(img: Image.Image) -> Image.Image:
    """Upright (EXIF), grey, stretched contrast, straightened."""
    img = ImageOps.exif_transpose(img)
    grey = ImageOps.autocontrast(img.convert("L"), cutoff=2)
    angle = estimate_tilt(grey)
    if angle:
        grey = grey.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=255)
    return grey
