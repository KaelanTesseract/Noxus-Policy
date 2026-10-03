# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Measures how well the document extraction works on real documents.

The documents and the expected values are personal data and live outside git, in
``backend/eval/`` (``docs/`` for the files, ``expected.json`` for the correct
values, ``cache/`` for extracted texts). Nothing in this script uploads anything.

    python tools/eval_extraction.py                 # extract with the rules, print the results
    python tools/eval_extraction.py --ai            # also run the embedded AI model
    python tools/eval_extraction.py --draft         # write eval/expected.json from the current results

With an ``expected.json`` present, every field is compared and a score per method
is printed, so a change to the extraction can be judged by numbers.
"""

import argparse
import json
import os
import sys
import time

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(BACKEND, "eval")
DOCS_DIR = os.path.join(EVAL_DIR, "docs")
CACHE_DIR = os.path.join(EVAL_DIR, "cache")
EXPECTED_PATH = os.path.join(EVAL_DIR, "expected.json")

os.environ.setdefault("SECRET_KEY", "evaluation-run-only-not-a-real-secret-0123456789")
sys.path.insert(0, BACKEND)

def prepare_windows_tools() -> None:
    """On a Windows development machine Tesseract and Poppler are not on the PATH after a
    plain install; find them, and use a local German language file if there is one
    (eval/tessdata/deu.traineddata). On the server none of this is needed."""
    if os.name != "nt":
        return
    candidates = [r"C:\Program Files\Tesseract-OCR"]
    packages = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    if os.path.isdir(packages):
        for root, _dirs, files in os.walk(packages):
            if "pdftoppm.exe" in files:
                candidates.append(root)
                break
    os.environ["PATH"] = os.pathsep.join([c for c in candidates if os.path.isdir(c)] + [os.environ.get("PATH", "")])
    local_langs = os.path.join(EVAL_DIR, "tessdata")
    if os.path.isdir(local_langs):
        os.environ["TESSDATA_PREFIX"] = local_langs


FIELDS = ["company", "insurance_number", "category", "doc_type", "cost", "refund_amount", "payment_cycle",
          "start_date", "end_date", "cancellation_date", "sf_class", "regional_class", "type_class"]
EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")


def load_text(path: str, ocr, fresh: bool = False) -> str:
    """Document text, cached because OCR is slow and the same file is read many times."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, os.path.basename(path) + ".txt")
    if not fresh and os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        with open(cache, encoding="utf-8") as f:
            return f.read()
    text = ocr.extract_text_from_file(path)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def normalise(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 2)
    text = str(value).strip().lower()
    try:  # expected.json keeps numbers as text ("62.48"), the extractor returns floats
        return round(float(text), 2) if text.replace(".", "", 1).replace("-", "", 1).isdigit() and "." in text else text
    except ValueError:
        return text


def pick(result: dict) -> dict:
    return {f: normalise(result.get(f)) for f in FIELDS} if result else {f: None for f in FIELDS}


def show(value) -> str:
    return "-" if value is None else str(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ai", action="store_true", help="also run the embedded AI model")
    parser.add_argument("--draft", action="store_true", help="write eval/expected.json from the rule results")
    parser.add_argument("--fresh", action="store_true", help="read the documents again instead of using cached texts")
    parser.add_argument("--only", help="only documents whose file name contains this text")
    parser.add_argument("--side", type=int, help="longest side in pixels a PDF page is rendered at (implies --fresh)")
    parser.add_argument("--tesseract", default="", help="extra Tesseract options, e.g. \"--psm 6\" (implies --fresh)")
    args = parser.parse_args()

    prepare_windows_tools()
    import ocr
    import document_naming
    ocr.OCR_TESSERACT_CONFIG = args.tesseract
    if args.side:
        ocr.OCR_MAX_PAGE_SIDE_PX = args.side
    args.fresh = args.fresh or bool(args.tesseract) or bool(args.side)

    files = sorted(f for f in os.listdir(DOCS_DIR) if f.lower().endswith(EXTENSIONS))
    if args.only:
        files = [f for f in files if args.only in f]
    if not files:
        sys.exit(f"No documents in {DOCS_DIR}")

    expected = {}
    if os.path.exists(EXPECTED_PATH):
        with open(EXPECTED_PATH, encoding="utf-8") as f:
            expected = json.load(f)

    # The same last step the app runs after either method (document type, amounts, what an
    # informational letter may not deliver). extract_insurance_data() itself is not called:
    # it would write the learned-pattern store and fetch the model.
    def finished(result, text):
        if not result:
            return result
        ocr.finalize_extraction(result, text)
        result["field_checks"] = ocr.assess_fields(result, text)
        return result

    methods = {"regex": lambda text: finished(ocr.extract_insurance_data_regex(text), text)}
    if args.ai:
        methods["ai"] = lambda text: finished(ocr.extract_with_mini_ai(text), text)

    scores = {m: {f: [0, 0] for f in FIELDS} for m in methods}
    drafts = {}
    for name in files:
        path = os.path.join(DOCS_DIR, name)
        started = time.time()
        text = load_text(path, ocr, args.fresh)
        print(f"\n=== {name}  ({len(text)} Zeichen Text, {time.time() - started:.1f}s)")
        if len(text.strip()) < 40:
            print("    kaum Text erkannt (gescanntes Bild? Tesseract nötig)")
        for method, run in methods.items():
            try:
                result = run(text)
            except Exception as e:  # keep going: one broken document must not hide the others
                print(f"    [{method}] FEHLER: {type(e).__name__}: {e}")
                continue
            got = pick(result)
            # a value the extractor only computed (cancellation date, end date without a date in the
            # letter) is not a reading of the document: it counts as "not read"
            for f, check in ((result or {}).get("field_checks") or {}).items():
                if f in got and check["status"] == "berechnet":
                    got[f] = None
            want = expected.get(name)
            if method == "regex":
                drafts[name] = {k: (str(v) if v is not None else None) for k, v in (result or {}).items() if k in FIELDS}
                drafts[name]["suggested_title"] = (result or {}).get("suggested_title")
            new_title = document_naming.suggest_title((result or {}).get("company"), (result or {}).get("category"), text)
            print(f"    [{method}] Titel alt: {show((result or {}).get('suggested_title'))}")
            print(f"    [{method}] Titel neu: {new_title}")
            checks = (result or {}).get("field_checks") or {}
            for f in FIELDS:
                line = f"      {f:18} {show(got[f])}"
                if f in checks and checks[f]["status"] != "gefunden":
                    line += f"   [{checks[f]['status']}]"
                elif f in checks:
                    line += f"   (S.{checks[f].get('seite')})"
                if want is not None and f in want:
                    ok = normalise(want[f]) == got[f]
                    scores[method][f][0] += ok
                    scores[method][f][1] += 1
                    line += "   OK" if ok else f"   FALSCH (erwartet: {show(want[f])})"
                print(line)

    if args.draft:
        os.makedirs(EVAL_DIR, exist_ok=True)
        with open(EXPECTED_PATH, "w", encoding="utf-8") as f:
            json.dump(drafts, f, ensure_ascii=False, indent=2)
        print(f"\nEntwurf geschrieben: {EXPECTED_PATH} (jetzt prüfen und korrigieren)")

    if expected:
        print("\n=== Trefferquote je Feld")
        header = f"{'Feld':20}" + "".join(f"{m:>12}" for m in methods)
        print(header)
        for f in FIELDS:
            row = f"{f:20}"
            for m in methods:
                ok, total = scores[m][f]
                row += f"{(f'{ok}/{total}' if total else '-'):>12}"
            print(row)


if __name__ == "__main__":
    main()
