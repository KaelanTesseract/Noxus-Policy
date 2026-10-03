# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Compares ways of reading scanned pages with Tesseract, so the setting used in
``ocr.py`` is chosen by numbers.

Two measurements, both on the documents in ``backend/eval/docs/`` (personal data,
outside git, see ``eval_extraction.py``):

* **Real scans** (PDFs without a text layer): there is no correct text to compare
  with, so the share of recognised words that are real German insurance words is
  used (vocabulary = the text of the PDFs that do have a text layer), plus how many
  such words were found at all. Higher is better in both columns.
* **Degraded copies** of a text-layer PDF (tilted, blurred, noisy, low resolution -
  roughly a phone photo): here the exact text is known, so precision, recall and F1
  of the words are measured.

    python tools/eval_ocr.py
    python tools/eval_ocr.py --pages 1 --only a,b      # fewer variants/pages for a quick run
"""

import argparse
import io
import os
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

os.environ.setdefault("OMP_THREAD_LIMIT", "1")  # one Tesseract per core instead of many fighting over them
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_extraction as ee  # noqa: E402  (sets up paths, SECRET_KEY, Windows tool lookup)

ee.prepare_windows_tools()
sys.path.insert(0, ee.BACKEND)
from image_prep import prepare_for_ocr  # noqa: E402

from PIL import Image, ImageFilter, ImageOps  # noqa: E402
from pdf2image import convert_from_path  # noqa: E402
import pytesseract  # noqa: E402
from pypdf import PdfReader  # noqa: E402

WORD = re.compile(r"[a-zäöüß]{4,}")


def words(text: str, minimum: int = 4):
    return re.findall(r"[a-zäöüß]{%d,}" % minimum, text.lower())


def layer_text(path: str, max_pages=None) -> str:
    reader = PdfReader(path)
    pages = reader.pages if max_pages is None else reader.pages[:max_pages]
    return "\n".join((p.extract_text() or "") for p in pages)


# ----------------------------------------------------------------------------- preprocessing (Pillow only)
def gray(img):
    return img.convert("L")


def contrast(img):
    return ImageOps.autocontrast(gray(img), cutoff=2)


def otsu_threshold(img) -> int:
    hist = img.histogram()[:256]
    total = sum(hist)
    sum_all = sum(i * h for i, h in enumerate(hist))
    best, best_var, w0, sum0 = 127, -1.0, 0, 0
    for t in range(256):
        w0 += hist[t]
        if not w0:
            continue
        w1 = total - w0
        if not w1:
            break
        sum0 += t * hist[t]
        m0, m1 = sum0 / w0, (sum_all - sum0) / w1
        var = w0 * w1 * (m0 - m1) ** 2
        if var > best_var:
            best, best_var = t, var
    return best


def binarize(img):
    g = contrast(img)
    t = otsu_threshold(g)
    return g.point(lambda p: 255 if p > t else 0).convert("L")


def clean(img):
    """What ocr.py does since the straightening was added (image_prep.py)."""
    return prepare_for_ocr(img)


def clean_binary(img):
    return binarize(prepare_for_ocr(img))


# ----------------------------------------------------------------------------- variants
# name: (page height in px, preprocessing, language, tesseract options)
VARIANTS = {
    "aktuell":        (2400, None,         "deu",     ""),                  # what ocr.py did before (psm 3)
    "psm4":           (2400, None,         "deu",     "--psm 4"),
    "psm6":           (2400, None,         "deu",     "--psm 6"),
    "psm11":          (2400, None,         "deu",     "--psm 11"),
    "kontrast":       (2400, contrast,     "deu",     ""),
    "gerade":         (2400, clean,        "deu",     ""),                  # what ocr.py does now
    "gerade+psm4":    (2400, clean,        "deu",     "--psm 4"),
    "gerade+psm6":    (2400, clean,        "deu",     "--psm 6"),
    "gerade+psm11":   (2400, clean,        "deu",     "--psm 11"),
    "gerade+eng":     (2400, clean,        "deu+eng", ""),
    "gerade+300":     (3300, clean,        "deu",     ""),
    "schwarzweiß":    (2400, clean_binary, "deu",     ""),
}


def recognise(img, variant) -> str:
    _height, prep, lang, options = VARIANTS[variant]
    if prep:
        img = prep(img)
    return pytesseract.image_to_string(img, lang=lang, config=options, timeout=120)


_render_cache = {}
TILT = 1.8


def render(path, page, height):
    key = (path, page, height)
    if key not in _render_cache:
        image = convert_from_path(path, first_page=page, last_page=page, size=height)[0]
        image.load()  # decode now: the lazily read file must not be touched by several threads
        _render_cache[key] = image
    return _render_cache[key].copy()


# ----------------------------------------------------------------------------- degraded copies
def degrade(img, seed=7, tilt=1.8):
    """A page photographed with a phone: tilted, a little out of focus, noisy, JPEG-compressed, low resolution."""
    rnd = random.Random(seed)
    small = img.convert("L")
    small.thumbnail((1700, 1700))
    tilted = small.rotate(tilt, resample=Image.BICUBIC, expand=False, fillcolor=235)
    blurred = tilted.filter(ImageFilter.GaussianBlur(0.9))
    pixels = blurred.load()
    for _ in range(blurred.width * blurred.height // 25):
        x, y = rnd.randrange(blurred.width), rnd.randrange(blurred.height)
        pixels[x, y] = max(0, min(255, pixels[x, y] + rnd.randint(-45, 45)))
    buffer = io.BytesIO()
    blurred.save(buffer, "JPEG", quality=35)
    return Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")


def f1(expected: str, got: str):
    want, have = Counter(words(expected, 3)), Counter(words(got, 3))
    hit = sum((want & have).values())
    precision = hit / max(1, sum(have.values()))
    recall = hit / max(1, sum(want.values()))
    return precision, recall, (2 * precision * recall / (precision + recall)) if hit else 0.0


# ----------------------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pages", type=int, default=2, help="pages per document (default 2)")
    parser.add_argument("--only", help="comma separated variant names")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--tilt", type=float, default=1.8, help="tilt of the degraded copies in degrees")
    args = parser.parse_args()
    global TILT
    TILT = args.tilt

    names = [n for n in VARIANTS if not args.only or n in args.only.split(",")]
    files = sorted(os.path.join(ee.DOCS_DIR, f) for f in os.listdir(ee.DOCS_DIR) if f.lower().endswith(".pdf"))

    vocabulary, scans, with_layer = set(), [], []
    for path in files:
        text = layer_text(path)
        if len(text.strip()) < 40:
            scans.append(path)
        else:
            with_layer.append(path)
            vocabulary |= set(words(text))
    print(f"{len(scans)} Scans, {len(with_layer)} PDFs mit Textebene, Wortschatz {len(vocabulary)} Wörter")

    # jobs: (dataset, label, image-maker, variant)
    jobs = []
    for path in scans:
        for page in range(1, args.pages + 1):
            for variant in names:
                jobs.append(("scan", os.path.basename(path)[:8], page, path, variant))
    synthetic_source = next((p for p in with_layer if "2ac3219d" in p), with_layer[0])
    for page in range(1, args.pages + 1):
        for variant in names:
            jobs.append(("foto", "foto-" + os.path.basename(synthetic_source)[:8], page, synthetic_source, variant))

    def run(job):
        dataset, label, page, path, variant = job
        height = VARIANTS[variant][0]
        try:
            img = render(path, page, height)
        except Exception:
            return job, None, 0.0
        if dataset == "foto":
            img = degrade(img, tilt=TILT)
            img.thumbnail((height, height))
        started = time.time()
        text = recognise(img, variant)
        return job, text, time.time() - started

    # render each page once before the workers start (pdf2image is not worth running in parallel)
    for job in jobs:
        try:
            render(job[3], job[2], VARIANTS[job[4]][0])
        except Exception:
            pass

    started = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(run, jobs))
    print(f"{len(jobs)} Läufe in {time.time() - started:.0f}s\n")

    scan_stats = {v: {"valid": 0, "all": 0, "secs": 0.0, "pages": 0} for v in names}
    photo_stats = {v: {"p": 0.0, "r": 0.0, "f": 0.0, "n": 0, "secs": 0.0} for v in names}
    layer = {}
    for job, text, secs in results:
        dataset, label, page, path, variant = job
        if text is None:
            continue
        if dataset == "scan":
            found = words(text)
            s = scan_stats[variant]
            s["all"] += len(found)
            s["valid"] += sum(1 for w in found if w in vocabulary)
            s["secs"] += secs
            s["pages"] += 1
        else:
            if path not in layer:
                layer[path] = {}
            if page not in layer[path]:
                layer[path][page] = PdfReader(path).pages[page - 1].extract_text() or ""
            p, r, f = f1(layer[path][page], text)
            s = photo_stats[variant]
            s["p"] += p
            s["r"] += r
            s["f"] += f
            s["n"] += 1
            s["secs"] += secs

    print(f"{'Variante':16}{'echte Wörter':>14}{'Anteil':>9}{'s/Seite':>9}   |{'Foto P':>8}{'R':>7}{'F1':>7}")
    for v in names:
        s, ph = scan_stats[v], photo_stats[v]
        share = s["valid"] / s["all"] if s["all"] else 0
        per_page = s["secs"] / s["pages"] if s["pages"] else 0
        n = ph["n"] or 1
        print(f"{v:16}{s['valid']:>14}{share:>9.1%}{per_page:>9.1f}   |{ph['p'] / n:>8.1%}{ph['r'] / n:>7.1%}{ph['f'] / n:>7.1%}")


if __name__ == "__main__":
    main()
