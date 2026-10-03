# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import pytesseract
from pattern_safety import apply_patterns
from document_naming import detect_kind, suggest_title
from image_prep import prepare_for_ocr
from page_select import MAX_OCR_PAGES, FIRST_OCR_PAGES, OCR_BATCH_PAGES, choose_text_pages, has_premium, split_pdftotext
from field_checks import assess_fields
from document_types import CONTRACT_FIELDS, DEFAULT_DOC_TYPE, DOC_TYPE_FOR_KIND, document_type_for, is_informational
from PIL import Image, ImageOps
from pdf2image import convert_from_path
import re
import os
import shutil
import subprocess
from datetime import datetime
try:
    from learning import get_learned_patterns_for_company, learn_from_feedback
except ImportError:
    from backend.learning import get_learned_patterns_for_company, learn_from_feedback

# Bounds for untrusted uploads: a PDF page or image can declare absurd dimensions
# (a few KB that expand to gigabytes of pixels) and Tesseract can be made to churn
# on adversarial images, so rendering, decoding and recognition are all capped.
OCR_MAX_PAGE_SIDE_PX = 3300          # longest side a PDF page is rendered at (~280 dpi on A4; at 2400 a policy number on a green card and a class digit were lost)
OCR_MAX_IMAGE_SIDE_PX = 3600
OCR_MAX_IMAGE_PIXELS = 50_000_000    # decoded pixels above this are refused outright
OCR_PDF_RENDER_TIMEOUT_S = 60
OCR_TESSERACT_TIMEOUT_S = 60
MAX_EXTRACTED_TEXT_CHARS = 200_000   # what the (regex-heavy) extractors ever get to see

Image.MAX_IMAGE_PIXELS = OCR_MAX_IMAGE_PIXELS

ORIENTATION_RETRY_BELOW = 50    # mean word confidence (0-100) below which other orientations are tried
ORIENTATION_MIN_GAIN = 20       # ... and the other reading must be this much more confident


def _text_and_confidence(tsv: str):
    """(text, mean confidence) from the word table (TSV) of a Tesseract run: lines in reading
    order, a blank line between paragraphs and blocks like the plain text output has. The
    confidence is None when no word was found (a blank page)."""
    lines, confidences = [], []
    current, last_paragraph = [], None
    for row in tsv.splitlines()[1:]:
        cells = row.split("\t")
        if len(cells) < 12 or cells[0] != "5" or not cells[11].strip():
            continue
        try:
            value = float(cells[10])
        except ValueError:
            continue
        if value >= 0:
            confidences.append(value)
        line_key, paragraph = tuple(cells[2:5]), tuple(cells[2:4])
        if current and line_key != current[0]:
            lines.append(" ".join(current[1:]))
            current = []
            if paragraph != last_paragraph:
                lines.append("")
        if not current:
            current = [line_key]
        current.append(cells[11].strip())
        last_paragraph = paragraph
    if current:
        lines.append(" ".join(current[1:]))
    return "\n".join(lines) + "\n", (sum(confidences) / len(confidences) if confidences else None)


def _ocr_page(img):
    """(text, mean confidence of the words) of one page from a single Tesseract run."""
    tsv = pytesseract.image_to_data(img, lang="deu", timeout=OCR_TESSERACT_TIMEOUT_S)
    return _text_and_confidence(tsv)


def read_page_image(img) -> str:
    """Text of one page image. The page is straightened first (phone photos and hurried
    scans are tilted; see image_prep.py) - if that fails for any reason the original
    image is read instead.

    A page that was scanned or photographed turned by a quarter or half turn reads as
    nonsense, and Tesseract says so itself: upright pages have a mean word confidence around 90,
    turned ones 23-35 (measured on 14 real letters). Only such a page is read again in the other
    three orientations, and a clearly more confident reading wins. (Tesseract's own orientation
    detection was tried first and rejected: it took 5 of 14 upright letters for upside down and
    turned sans-serif pages the wrong way.)"""
    try:
        img = ImageOps.exif_transpose(img)  # a phone photo knows how it was held
    except Exception:
        pass

    def prepared(image):
        try:
            return prepare_for_ocr(image)
        except Exception as e:
            print(f"Image preparation notice: {e}")
            return image

    text, confidence = _ocr_page(prepared(img))
    if confidence is None or confidence >= ORIENTATION_RETRY_BELOW:
        return text
    best_text, best_confidence = text, confidence
    for turn in (90, 180, 270):
        turned_text, turned_confidence = _ocr_page(prepared(img.rotate(turn, expand=True)))
        if turned_confidence is not None and turned_confidence > best_confidence:
            best_text, best_confidence = turned_text, turned_confidence
    return best_text if best_confidence - confidence >= ORIENTATION_MIN_GAIN else text


PDFTOTEXT_TIMEOUT_S = 30
MAX_LAYER_PAGES = 150               # pages of a text-layer PDF that are ever read (the rest is terms and conditions)
USE_PDFTOTEXT = True                # layout-preserving text from Poppler's pdftotext, see read_text_layer

def read_text_layer(filepath: str) -> list:
    """Text of every page of a PDF with a text layer, as a list (index = page - 1); empty
    pages stay in the list. With Poppler's pdftotext (-layout) tables and columns keep their
    shape; without it, or if it fails, pypdf reads the pages. A scan has no text layer: the
    pages come back empty."""
    if USE_PDFTOTEXT:
        exe = shutil.which("pdftotext")
        if exe:
            try:
                done = subprocess.run(
                    [exe, "-layout", "-enc", "UTF-8", "-l", str(MAX_LAYER_PAGES), os.path.abspath(filepath), "-"],
                    capture_output=True, timeout=PDFTOTEXT_TIMEOUT_S, check=True,
                )
                return split_pdftotext(done.stdout.decode("utf-8", errors="replace"))
            except (subprocess.SubprocessError, OSError) as e:
                print(f"pdftotext notice: {e}")
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        return [(page.extract_text() or "") for page in reader.pages[:MAX_LAYER_PAGES]]
    except Exception as pe:
        print(f"pypdf extraction notice: {pe}")
        return []


def _pdf_page_count(filepath: str):
    try:
        from pypdf import PdfReader
        return len(PdfReader(filepath).pages)
    except Exception:
        return None


def ocr_pdf_pages(filepath: str) -> str:
    """A scanned PDF, recognised page by page: the first pages, then more in small batches until
    a premium has been found - a long scan whose premium table stands on page 7 is still read,
    an information leaflet of 60 pages is not read to the end."""
    total = _pdf_page_count(filepath)
    text = ""
    first, last = 1, FIRST_OCR_PAGES
    while True:
        images = convert_from_path(
            filepath, first_page=first, last_page=last,
            size=OCR_MAX_PAGE_SIDE_PX, timeout=OCR_PDF_RENDER_TIMEOUT_S,
        )
        for number, img in enumerate(images, start=first):
            text += f"--- Page {number} ---\n" + read_page_image(img) + "\n"
        reached_end = not images or len(images) < (last - first + 1) or (total is not None and last >= total)
        if reached_end or last >= MAX_OCR_PAGES or has_premium(text) or is_informational(document_type_for(detect_kind(text))):
            return text
        first, last = last + 1, min(last + OCR_BATCH_PAGES, MAX_OCR_PAGES)


def extract_text_from_file(filepath: str) -> str:
    text = ""
    try:
        if filepath.lower().endswith('.pdf'):
            layer = read_text_layer(filepath)
            if any(page.strip() for page in layer):
                for idx in choose_text_pages(layer):
                    if layer[idx].strip():
                        text += f"--- Page {idx+1} ---\n" + layer[idx] + "\n"
            else:
                text = ocr_pdf_pages(filepath)
        else:
            with Image.open(filepath) as img:
                img.draft("RGB", (OCR_MAX_IMAGE_SIDE_PX, OCR_MAX_IMAGE_SIDE_PX))  # cheap JPEG downscale while decoding
                img.thumbnail((OCR_MAX_IMAGE_SIDE_PX, OCR_MAX_IMAGE_SIDE_PX))
                text = read_page_image(img)
    except Exception as e:
        print(f"Error during OCR/text extraction: {e}")
    return text[:MAX_EXTRACTED_TEXT_CHARS]

def parse_date(date_str: str):
    if not date_str:
        return None
    date_str = date_str.strip().strip('.').strip(':')
    formats = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None

def is_invalid_policy_num(candidate: str) -> bool:
    if not candidate:
        return True
    s = candidate.strip().lower()
    if len(s) < 4:
        return True
    # A valid policy number MUST contain at least one digit!
    if not re.search(r'\d', s):
        return True
    if s.startswith(('ist', 'der', 'des', 'von', 'und', 'null', 'seite', 'bitte', 'satz', 'tarif', 'abgang', 'kraftfahrt', 'versicherung', 'nachtrag')):
        return True
    if re.search(r'vers\.st|ust|iban|bic|hrb|amtsgericht|kraftfahrtversicherung|haftpflichtversicherung|rechtschutz', s):
        return True
    return False

def extract_subject_fallback(text: str) -> str:
    if not text:
        return None

    # 1. Direct regex match for "Betreff: ..." or "Betr.: ..."
    match = re.search(r'(?i)(?:betreff|betr\.)\s*[:\s]*([^\n]{4,90})', text)
    if match:
        subj = match.group(1).strip()
        if len(subj) >= 4 and not subj.lower().startswith(('sehr geehrte', 'hallo', 'dame', 'herr', 'ihre', 'unsere')):
            return subj

    # 2. Prominent document header lines in top 20 lines
    for line in text.split('\n')[:20]:
        clean_line = line.strip()
        if re.search(r'(?i)^(beitragsanpassung|beitragserhöhung|versicherungsschein|polizze|nachtrag\s+zur|nachtrag|kündigungsbestätigung|jahresabrechnung|schadensmeldung|versicherungsinformation|rechnung)\b', clean_line):
            if 4 <= len(clean_line) <= 90:
                return clean_line

    return None

_NUMBER_LABEL = re.compile(
    r'(?i)\b(?:versicherungsschein-?(?:nummer|nr)|versicherungs-?nummer|policen-?(?:nummer|nr)|police(?:n)?-?nr|police'
    r'|vertrags-?(?:nummer|nr)|schein-?(?:nummer|nr)|vsnr)\b\.?[ \t]*:?[ \t]*')


def _number_from_tokens(candidate: str):
    """The policy number at the start of ``candidate``: groups as letters print them ("WG 5544-3321",
    "7 123 456 789 0", "30.120.456-7", "K 4455 6677 88"). It ends at the first word, a date or any
    character a number does not contain."""
    tokens = []
    for token in candidate.split()[:6]:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9./\-]*', token) or re.fullmatch(r'\d{2}\.\d{2}\.\d{2,4}', token):
            break
        if not re.search(r'\d', token) and not (len(token) <= 3 and token.isupper()):
            break
        tokens.append(token)
    while tokens and not re.search(r'\d', tokens[-1]):   # a trailing "WG" belongs to what follows, not to the number
        tokens.pop()
    value = " ".join(tokens)
    if len(re.findall(r'\d', value)) >= 5 and not is_invalid_policy_num(value):
        return value
    return None


def number_after_label(text: str):
    """The number written behind a label like "Versicherungsschein-Nr.", "Vertragsnummer:" or
    "Police", on the same line or - when the line ends with the label - on the next one."""
    lines = (text or "").split("\n")
    for i, line in enumerate(lines):
        for label in _NUMBER_LABEL.finditer(line):
            rest = line[label.end():].strip()
            if not rest and i + 1 < len(lines):
                rest = lines[i + 1].strip()
            value = _number_from_tokens(rest)
            if value:
                return value
    return None


def extract_policy_number_fallback(text: str, current_num: str = None) -> str:
    # 1. Direct pattern like LJ-12345678-001 or 123/456789-A or VSN-999999 (High precision)
    direct_match = re.search(r'\b([A-Z]{1,4}-\d{6,12}-\d{1,3}|\d{3}/\d{6}-[A-Za-z0-9])\b', text)
    if direct_match:
        val = direct_match.group(1).strip()
        if not is_invalid_policy_num(val):
            return val

    # 1b. The same number with a space inside, as scans often come out: "LJ-23375 102-001"
    spaced = re.search(r'\b([A-Z]{1,4}-\d{3,8}) (\d{2,8}-\d{1,3})\b', text)
    if spaced:
        val = spaced.group(1) + spaced.group(2)
        if 6 <= len(re.findall(r'\d', val.split('-', 1)[1].rsplit('-', 1)[0])) <= 12 and not is_invalid_policy_num(val):
            return val

    # 1c. A number behind a label, whatever its layout ("WG 5544-3321", "Police: 12-3456789-0")
    labelled = number_after_label(text)
    if labelled:
        return labelled

    # 2. Multi-line label search: e.g. "Versicherungsschein-Nummer\nLJ-12345678-001"
    multiline_patterns = [
        r'(?i)(?:versicherungsschein-?nummer|policennummer|vertragsnummer|schein-?nummer|vsnr)\b.*?\n+\s*(?:[a-z0-9\s]*?\s+)?([A-Za-z0-9\-/]{5,30})',
        r'(?i)(?:versicherungsschein-?nr|policen-?nr|schein-?nr|vertrags-?nr|vsnr)\.?:?\s*([A-Za-z0-9\-/]{5,30})',
        r'(?i)versicherungs-?schein-?nummer\s*([A-Za-z0-9\-/]{5,30})'
    ]
    for pat in multiline_patterns:
        for match in re.finditer(pat, text):
            val = match.group(1).strip()
            if not is_invalid_policy_num(val):
                return val

    # 3. Hashes pattern like #4#12345678## or ##12345678##
    hash_match = re.search(r'#\d*#?([A-Za-z0-9\-/]{6,25})##', text)
    if hash_match:
        val = hash_match.group(1).strip()
        if not is_invalid_policy_num(val):
            return val

    if current_num and not is_invalid_policy_num(current_num):
        return str(current_num).strip()

    return current_num

def extract_regionalklasse_fallback(text: str, current_regio: str = None) -> str:
    if current_regio and re.match(r'^R\s*[-:]?\s*\d{1,2}$', str(current_regio).strip(), re.I):
        val = str(current_regio).strip().upper().replace(" ", "").replace("-", "")
        if not val.startswith("R"):
            val = f"R{val}"
        return val

    patterns = [
        r'(?i)\b(R\s*[-:]?\s*[0-9O]{1,2})\b',
        r'(?i)(?:regionalklasse|regio|r\-klasse|tarifgruppe)[^\n]*?\b(R\s*[-:]?\s*[0-9O]{1,2})\b',
        r'(?i)(?:regional|regio)[^\n]*?\b([0-9O]{1,2})\b'
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            raw = m.group(1).upper().replace(" ", "").replace("-", "").replace("O", "0")
            if not raw.startswith("R"):
                raw = f"R{raw}"
            # Regional classes run from 1 to 12: "R0" is a class whose last digit OCR lost ("RO 18"),
            # not a class. Skip it and take the next mention (the comparison table repeats it).
            if re.match(r'^R\d{1,2}$', raw) and 1 <= int(raw[1:]) <= 12:
                return raw

    return current_regio if current_regio else None

def parse_german_amount(raw_str: str) -> float:
    if not raw_str:
        return None
    s = raw_str.strip()
    is_negative = False
    if s.endswith('-') or s.startswith('-'):
        is_negative = True
        s = s.replace('-', '').strip()

    s = s.replace('.', '').replace(',', '.')
    try:
        val = float(s)
        return -val if is_negative else val
    except Exception:
        return None

# An amount as printed in German letters: "49,74 €", "1.234,56 EUR", and the credit form
# "40,33- €" (minus sign behind the number) or "-40,33 €".
_AMOUNT = r'(-?\s?\d{1,3}(?:\.\d{3})*,\d{2}\s*-?)\s*(?:€|EUR|Euro)'
# Lines about money coming back to the customer: never the contract premium.
_REFUND_WORDS = re.compile(r'(?i)guthaben|erstattung|erstatten|gutschrift|rückerstattung|rückzahlung|zwischensumme')
# Lines whose amounts are limits or deductibles, not premiums.
_NOT_A_PREMIUM = re.compile(r'(?i)selbstbeteiligung|selbstbehalt|pauschal|deckungssumme|versicherungssumme|'
                            r'umweltschadensgesetz|personenschäden|ohne versicherungsteuer|fahrzeugwert|mio\.')


def _positive_amount(raw: str):
    """The amount as a positive number; None for credits ("40,33-") and unreadable values."""
    val = parse_german_amount(raw)
    return val if val is not None and val > 0 else None


def _amount_after(pattern: str, text: str):
    for m in re.finditer(pattern, text):
        val = _positive_amount(m.group(1))
        if val is not None:
            return val
    return None


def extract_cost_with_basis(text: str):
    """The contract premium of a letter. Credits and refunds ("Guthaben 40,33- €",
    "Zwischensumme 10,42- €") are never returned: they are money the insurer pays out,
    and they used to be read as a negative premium.

    Returns (premium, certain). ``certain`` is False when the amount is only the first
    plausible amount on the page (step 5)."""
    if not text:
        return None, False

    # 1. The letter says what is paid from now on:
    #    "Zukünftig wird der monatliche Beitrag von 49,74 €, beginnend mit dem 01.03.2016"
    val = _amount_after(r'(?i)zukünftig\s+wird\s+der\s+(?:\w+\s+)?beitrag\s+von\s+' + _AMOUNT, text)
    if val is not None:
        return val, True

    # 2. The total including insurance tax.
    val = _amount_after(r'(?i)beitrag\s*\([^)]*inklusive[^)]*\)\s*[:\s]*' + _AMOUNT, text)
    if val is not None:
        return val, True
    for line in text.split('\n'):
        if re.search(r'(?i)gesamtbeitrag|zahlbeitrag|bruttobeitrag|beitrag\s*inkl\.?\s*steuer', line):
            amounts = [_positive_amount(a) for a in re.findall(_AMOUNT, line)]
            amounts = [a for a in amounts if a is not None]
            if amounts:
                return amounts[-1], True

    # 3. The premium of the contract period ("Jahresbeitrag Gültig ab 24.07.2026 29,29 €").
    #    Preferred over the first payment ("Erstbeitrag"), which can differ by a few cents.
    val = _amount_after(r'(?i)(?:jahres|halbjahres|vierteljahres|monats)beitrag[^\n\d€]*(?:\d{2}\.\d{2}\.\d{4})?[^\n\d€]*' + _AMOUNT, text)
    if val is not None:
        return val, True

    # 4. Any line that names a premium.
    for line in text.split('\n'):
        if _REFUND_WORDS.search(line) or _NOT_A_PREMIUM.search(line) or re.search(r'(?i)kfz-haftpflicht|teilkasko|vollkasko', line):
            continue
        m = re.search(r'(?i)(?:beitrag|prämie)\s*[:\s]*' + _AMOUNT, line)
        if m:
            val = _positive_amount(m.group(1))
            if val is not None:
                return val, True

    # 5. Last resort: the first plausible amount.
    for line in text.split('\n'):
        if _REFUND_WORDS.search(line) or _NOT_A_PREMIUM.search(line):
            continue
        m = re.search(_AMOUNT, line)
        if m:
            val = _positive_amount(m.group(1))
            if val is not None:
                return val, False

    return None, False


def extract_cost_fallback(text: str) -> float:
    return extract_cost_with_basis(text)[0]


def extract_refund_amount(text: str):
    """What the insurer pays back (termination, premium reduction), as a positive number.
    Kept apart from the cost on purpose. The amount actually paid out ("Wir erstatten
    Ihnen ...") wins over the balance it is calculated from."""
    if not text:
        return None
    # (pattern, a plain amount is already a refund because of the words in front of it)
    for pattern, plain_amount_counts in (
        (r'(?i)wir erstatten ihnen[^\n\d]*' + _AMOUNT, True),
        (r'(?i)zwischensumme\s*' + _AMOUNT, False),
        (r'(?i)guthaben\s+von\s+' + _AMOUNT, True),
        (r'(?i)erstattungsbeitrag[^\n]*?' + _AMOUNT, False),
    ):
        for m in re.finditer(pattern, text):
            val = parse_german_amount(m.group(1))
            if val and (val < 0 or plain_amount_counts):
                return abs(val)
    return None


def calculate_insurance_dates(start_date_str, end_date_str, cancellation_date_str, text: str):
    import datetime

    def to_date_obj(val):
        if not val:
            return None
        if isinstance(val, datetime.date):
            return val
        return parse_date(str(val))

    s_date = to_date_obj(start_date_str)
    e_date = to_date_obj(end_date_str)
    c_date = to_date_obj(cancellation_date_str)

    # 1. Search for explicit date range pairs: e.g. "24.07.2026, 0 Uhr 23.07.2027, 0 Uhr"
    range_matches = re.findall(r'(\d{2}\.\d{2}\.\d{4})\s*(?:,\s*0\s*Uhr)?\s+(\d{2}\.\d{2}\.\d{4})', text)
    if range_matches:
        pair_start = parse_date(range_matches[0][0])
        pair_end = parse_date(range_matches[0][1])
        if pair_start and not s_date:
            s_date = pair_start
        if pair_end:
            e_date = pair_end

    # 2. Search for explicit Ablauf date in text
    match_end = re.search(r'(?i)(?:versicherungsablauf|vertragsablauf|ablauf|gültig bis)\.?:?\s*(\d{2}\.\d{2}\.\d{4})', text)
    if match_end:
        parsed_end = parse_date(match_end.group(1))
        if parsed_end:
            e_date = parsed_end

    # 3. Search for explicit Beginn / Fälligkeitsdatum in text
    # (a bare "am" is not a start: "Ihr Konto war am 30.04.2018 ausgeglichen" is no contract date)
    match_start = re.search(r'(?i)(?:beginn der änderung|versicherungsbeginn|vertragsbeginn|beginn|gültig ab|fällig am|zeitraum)\.?:?\s*(\d{2}\.\d{2}\.\d{4})', text)
    if match_start and not s_date:
        parsed_start = parse_date(match_start.group(1))
        if parsed_start:
            s_date = parsed_start

    # 4. Override false 01.01. tariff revision dates if date range pair exists
    if e_date and e_date.month == 1 and e_date.day == 1 and range_matches:
        better_end = parse_date(range_matches[0][1])
        if better_end and (better_end.month != 1 or better_end.day != 1):
            e_date = better_end

    # 5. If start_date is known but end_date missing, set end_date = start_date + 1 year
    if s_date and not e_date:
        try:
            e_date = datetime.date(s_date.year + 1, s_date.month, s_date.day) - datetime.timedelta(days=1)
        except Exception:
            pass

    # 6. Calculate cancellation_date = end_date - 1 month (standard German Kündigungsfrist)
    if e_date:
        try:
            c_date = one_month_before(e_date)
        except Exception:
            pass

    return s_date, e_date, c_date

def one_month_before(end_date):
    """The last day for a notice with a notice period of one month to the end of the term:
    the same day of the previous month, or its last day when that month is shorter
    (31.12. -> 30.11., 31.03. -> 28.02.). The day used to be cut at 28 - 31.12. gave 28.11."""
    import calendar
    import datetime
    year, month = (end_date.year - 1, 12) if end_date.month == 1 else (end_date.year, end_date.month - 1)
    return datetime.date(year, month, min(end_date.day, calendar.monthrange(year, month)[1]))

_COVERAGE_STOP = re.compile(r'(?im)^\s*(?:besonders zu beachten|kontoauszug|bitte beachten sie folgendes)')


def coverage_scope(text: str) -> str:
    """The part of a letter that says what THIS contract covers. Everything from the first
    general section on ("Besonders zu beachten", the account statement, advice on paying the
    first premium) is boilerplate that mentions Schutzbrief, Fahrerschutz, Vollkasko ... for every
    customer: a trailer policy listed six coverages because of it, two of them not insured."""
    m = _COVERAGE_STOP.search(text or "")
    return text[:m.start()] if m and m.start() > 300 else (text or "")


def extract_insurance_data_regex(text: str) -> dict:
    data = {
        "company": None,
        "insurance_number": None,
        "category": None,
        "doc_type": None,
        "suggested_title": None,
        "cost": None,
        "payment_cycle": "jährlich",
        "start_date": None,
        "end_date": None,
        "cancellation_date": None,
        "document_date": None,
        "coverage_details": []
    }
    
    # 1. Company detection (Expanded for 70+ DACH insurers + Dynamic Fallback)
    companies = [
        "HUK-COBURG", "HUK24", "Allianz", "AXA", "Ergo", "Generali", 
        "Signal Iduna", "DEVK", "LVM", "Debeka", "R+V", "Gothaer", 
        "Barmenia", "CosmosDirekt", "HanseMerkur", "VHV", "NÜRNBERGER",
        "Zurich", "HDI", "ADAC", "ARAG", "WGV", "Sparkassen Direkt",
        "Provinzial", "SV Sparkassenversicherung", "Die Haftpflichtkasse", "Haftpflichtkasse",
        "Helvetia", "WWK", "InterRisk", "VGH", "Concordia", "Volkswohl Bund",
        "Alte Leipziger", "Hallesche", "UKV", "SDK", "Continentale", "Janitos",
        "Baloise", "Grawe", "Wiener Städtische", "UNIQA", "Oberösterreichische",
        "NV-Versicherungen", "GHV", "Itzehoer", "Münchener Verein", "Die Bayerische",
        "Stuttgarter", "Mannheimer", "BavariaDirekt", "Friday", "Neodigital",
        "Getsafe", "Feather", "Hiscox", "Wertgarantie", "Agila", "Uelzener",
        "DFV", "Deutsche Familienversicherung", "Nürnberger", "VVD"
    ]
    
    for comp in companies:
        if re.search(r'\b' + re.escape(comp) + r'\b', text, re.IGNORECASE):
            data["company"] = comp
            break

    # HUK24 is a company of its own; its letters also name HUK-COBURG (address, group). The letterhead decides.
    if data["company"] == "HUK-COBURG" and re.search(r'\bHUK24\b', "\n".join(text.split("\n")[:60])):
        data["company"] = "HUK24"

    if not data["company"]:
        comp_match =re.search(r'([A-ZÄÖÜa-zäöü0-9\-\s]{3,30}\s+(?:Versicherung(?:en)?|AG|SE|VVaG|Krankenkasse))', text)
        if comp_match:
            comp_candidate = comp_match.group(1).strip()
            if len(comp_candidate) < 35 and not comp_candidate.lower().startswith(('die', 'der', 'das', 'ihre', 'fuer', 'vertrag')):
                data["company"] = comp_candidate
            
    # 2. Insurance Number
    data["insurance_number"] = extract_policy_number_fallback(text, None)

    # 3. Category & Doc Type (Expanded for all DACH insurance categories)
    if re.search(r'(?i)(kfz|auto|fahrzeug|kraftfahrt|teilkasko|vollkasko|pkw|moped|motorrad)', text):
        data["category"] = "Kfz"
        data["doc_type"] = "Kfz-Versicherung"
    elif re.search(r'(?i)(haftpflicht|privathaftpflicht|hundehaftpflicht|tierhalterhaftpflicht|bauherrenhaftpflicht|berufshaftpflicht)', text):
        data["category"] = "Haftpflicht"
        data["doc_type"] = "Haftpflichtversicherung"
    elif re.search(r'(?i)(hausrat|wohngebäude|gebäude|glas|photovoltaik|inventar)', text):
        data["category"] = "Hausrat"
        data["doc_type"] = "Hausrat- / Gebäudeversicherung"
    elif re.search(r'(?i)(leben|renten|altersvorsorge|berufsunfähigkeit|bu\-|riester|rürup|todesfall)', text):
        data["category"] = "Leben"
        data["doc_type"] = "Lebens- / Rentenversicherung"
    elif re.search(r'(?i)(kranken|pflege|zahn|gesundheit|sehhilfe|ambulant|stationär)', text):
        data["category"] = "Gesundheit"
        data["doc_type"] = "Krankenversicherung"
    elif re.search(r'(?i)(rechtsschutz|mietrechtsschutz|verkehrsrechtsschutz|berufsrechtsschutz)', text):
        data["category"] = "Rechtsschutz"
        data["doc_type"] = "Rechtsschutzversicherung"
    elif re.search(r'(?i)(reise|auslandskranken|reiserücktritt)', text):
        data["category"] = "Sonstige"
        data["doc_type"] = "Reiseversicherung"
    elif re.search(r'(?i)(tierkranken|tier|op-versicherung)', text):
        data["category"] = "Sonstige"
        data["doc_type"] = "Tierversicherung"
    else:
        data["category"] = "Sonstige"
        data["doc_type"] = "Versicherung"

    # Suggested Title & Subject (Betreff)
    subj = extract_subject_fallback(text)
    data["subject"] = subj
    data["document_title"] = subj
    comp_str = data["company"] or "Unbekannt"
    num_str = f"({data['insurance_number']})" if data["insurance_number"] else ""
    data["suggested_title"] = subj or f"{comp_str} {data['doc_type']} {num_str}".strip()

    # 4. Cost / Premium
    data["cost"] = extract_cost_fallback(text)

    # 5. Payment Cycle
    if re.search(r'(?i)(monatlich|monatlicher)', text):
        data["payment_cycle"] = "monatlich"
    elif re.search(r'(?i)(vierteljährlich)', text):
        data["payment_cycle"] = "vierteljährlich"
    elif re.search(r'(?i)(halbjährlich)', text):
        data["payment_cycle"] = "halbjährlich"
    else:
        data["payment_cycle"] = "jährlich"

    # 6. Dates
    s_date, e_date, c_date = calculate_insurance_dates(None, None, None, text)
    data["start_date"] = s_date
    data["end_date"] = e_date
    data["cancellation_date"] = c_date

    # Coverage Details (Excluding negative matches)
    coverage_details = []
    cov_text = coverage_scope(text)
    
    # Kfz
    if re.search(r'(?i)(kfz\-haftpflicht|kraftfahrt-haftpflicht)', cov_text):
        coverage_details.append("Kfz-Haftpflichtversicherung (Schäden an Drittfahrzeugen, Personenschäden & Abwehr unberechtigter Ansprüche)")
    if re.search(r'(?i)(schutzbrief)', cov_text) and not re.search(r'(?i)schutzbrief[^\n]*ist nicht vertragsinhalt', cov_text):
        coverage_details.append("Schutzbrief (Organisatorische & finanzielle Hilfe bei Panne oder Unfall, Abschleppen & Mietwagen)")
    if re.search(r'(?i)(teilkasko)', cov_text):
        coverage_details.append("Teilkasko (Schutz bei Glasbruch, Diebstahl, Hagel, Sturm & Wildunfällen)")
    if re.search(r'(?i)(vollkasko(?!vertrag))', cov_text) and not re.search(r'(?i)vollkasko[^\n]*ist nicht vertragsinhalt', cov_text):
        coverage_details.append("Vollkasko (Abdeckung von Unfallschäden am eigenen Fahrzeug & Vandalismus)")
    if re.search(r'(?i)(fahrerschutz)', cov_text) and not re.search(r'(?i)fahrerschutz[^\n]*ist nicht vertragsinhalt', cov_text):
        coverage_details.append("Fahrerschutz (Übernahme von Personenschäden & Genesungskosten des Fahrers bei Unfall)")
    if re.search(r'(?i)(ausland\-schadenschutz)', cov_text) and not re.search(r'(?i)ausland\-schadenschutz[^\n]*ist nicht vertragsinhalt', cov_text):
        coverage_details.append("Ausland-Schadenschutz (Schadenregulierung bei Unfällen im Ausland nach deutschem Standard)")
    if re.search(r'(?i)(umweltschaden|umweltschadensgesetz)', cov_text):
        coverage_details.append("Kfz-Umweltschadenversicherung (Schutz vor öffentlich-rechtlichen Ansprüchen nach dem Umweltschadensgesetz)")

    # Exclude false positives like "Wohngebäude bei der Itzehoer versichert: Nein"
    if re.search(r'(?i)(wohngebäude|gebäudeversicherung)', cov_text) and not re.search(r'(?i)wohngebäude[^\n]*:\s*nein', cov_text) and not re.search(r'(?i)wohngebäude[^\n]*ist nicht', cov_text):
        coverage_details.append("Wohngebäudeversicherung (Absicherung gegen Feuer, Sturm, Hagel, Leitungswasser & Elementarschäden)")

    # Haftpflicht
    if re.search(r'(?i)(privathaftpflicht)', cov_text):
        coverage_details.append("Privathaftpflicht (Schäden an Dritten, Mietsachschäden, Gefälligkeitshandlungen & Schlüsselverlust)")
    if re.search(r'(?i)(hundehaftpflicht|tierhalterhaftpflicht)', cov_text):
        coverage_details.append("Tierhalterhaftpflicht (Personen- & Sachschäden durch Haustiere/Hunde an Dritten)")
    if re.search(r'(?i)(bauherrenhaftpflicht|haus-? und grundbesitzer)', cov_text):
        coverage_details.append("Haus- & Grundbesitzerhaftpflicht (Absicherung von Verkehrssicherungspflichten & Bauherrenschäden)")

    # Hausrat
    if re.search(r'(?i)(hausrat)', cov_text):
        coverage_details.append("Hausratversicherung (Schutz bei Einbruchdiebstahl, Vandalismus, Leitungswasser, Sturm & Hagel)")

    # Rechtsschutz
    if re.search(r'(?i)(rechtsschutz)', cov_text):
        if re.search(r'(?i)(verkehrsrechtsschutz)', cov_text):
            coverage_details.append("Verkehrsrechtsschutz (Kostendeckung bei Streitigkeiten im Straßenverkehr & Anwaltskosten)")
        if re.search(r'(?i)(berufsrechtsschutz)', cov_text):
            coverage_details.append("Berufsrechtsschutz (Rechtlicher Schutz bei Arbeitsplatz- & Arbeitsvertragsstreitigkeiten)")
        if re.search(r'(?i)(mietrechtsschutz|immobilienrechtsschutz)', cov_text):
            coverage_details.append("Miet- & Immobilienrechtsschutz (Rechtsschutz bei Konflikten zwischen Mieter und Vermieter)")
        if not any("rechtsschutz" in c.lower() for c in coverage_details):
            coverage_details.append("Rechtsschutz (Übernahme von Anwalts- & Gerichtskosten sowie Freie Anwaltswahl)")

    # Gesundheit & Zahn
    if re.search(r'(?i)(zahnzusatz|zahnersatz|zahnbehandlung)', cov_text):
        coverage_details.append("Zahnzusatzversicherung (Kostenerstattung für professionelle Zahnreinigung, Inlays & Zahnersatz)")
    if re.search(r'(?i)(krankentagegeld|krankengeld)', cov_text):
        coverage_details.append("Krankentagegeld (Einkommenssicherung bei längerer Krankheitsdauer)")

    # Leben & Vorsorge
    if re.search(r'(?i)(berufsunfähigkeit|bu\-rente)', cov_text):
        coverage_details.append("Berufsunfähigkeitsversicherung (Monatliche Rente & Beitragsbefreiung bei Berufs- oder Erwerbsunfähigkeit)")

    # KFZ Specific Regex Extraction
    match_sf = re.search(r'(?i)\b(?:sf|schadenfreiheitsklasse)\s*[-:]?\s*([0-9/]+|(?:1/2))\b', text)
    if match_sf:
        data["sf_class"] = f"SF {match_sf.group(1).upper()}"

    regio_val = extract_regionalklasse_fallback(text, data.get("regional_class"))
    if regio_val:
        data["regional_class"] = regio_val

    match_typ = re.search(r'(?i)\b(?:typ\s*klasse|typ-?klasse|tk)\b[^\n\d]*?(\d{1,2})\b', text)
    if match_typ:
        data["type_class"] = match_typ.group(1)
    else:
        # Beitragsrechnung: a table row "Kfz-Haftpflicht R05 18 SF 3 (65 %) 43,47 €"; the first row
        # is the current one (further rows compare with the previous year)
        # Only the first row counts: if OCR garbled its class, the class stays empty rather than
        # being taken from a comparison row of the previous year.
        first_row = re.search(r'(?im)^\s*kfz-haftpflicht\b[^\n]*\bSF[^\n]*', text)
        row = re.search(r'(?<![\dR])(\d{2})\s+SF', first_row.group(0)) if first_row else None
        if row:
            data["type_class"] = row.group(1)

    # Price Adjustment / Price Change Regex Extraction
    if re.search(r'(?i)(beitragsanpassung|beitragserhöhung|neuer beitrag|beitragsänderung|jahresrechnung)', text):
        data["is_price_change"] = True
        data["doc_type"] = "Beitragsanpassung"

    data["coverage_details"] = coverage_details
    return data

def finalize_extraction(data: dict, text: str) -> dict:
    """Last step, whichever method (rules or AI) produced ``data``: settle the kind of
    letter and make sure it only delivers what it may.

    - ``doc_type`` becomes the entry of the document-type list that fits the letter
      (the insurance kind the old code put there moves to ``insurance_type``).
    - Informational documents (terms, consumer information, green card ...) deliver no
      contract data at all; their text is full of limits, dates and classes of no policy.
    - A terminated contract has no premium any more; what is paid back is ``refund_amount``.
    - A premium is never negative."""
    kind = detect_kind(text)
    data["document_kind"] = kind
    if data.get("doc_type") and data["doc_type"] not in DOC_TYPE_FOR_KIND.values():
        data["insurance_type"] = data["doc_type"]

    doc_type = document_type_for(kind)
    if doc_type is None:
        # a letter we cannot place: fall back on the wording rule of the extractors
        doc_type = "Beitragsanpassung" if data.get("is_price_change") else DEFAULT_DOC_TYPE
    data["doc_type"] = doc_type
    data["is_price_change"] = doc_type == "Beitragsanpassung"

    if is_informational(doc_type):
        for field in CONTRACT_FIELDS:
            data[field] = None
        data["coverage_details"] = []
        data["refund_amount"] = None
        return data

    data["refund_amount"] = extract_refund_amount(text)
    if kind == "Nachtrag zum Vertragsende":
        data["cost"] = None
        data["new_cost"] = None
        # the contract is over: there is nothing left to give notice for (the end date stays)
        data["cancellation_date"] = None
        data["coverage_details"] = []  # nothing is insured any more; the lines are only the refund calculation
        return data

    cost, certain = extract_cost_with_basis(text)
    if cost is None:
        cost = data.get("cost")
    data["cost_certain"] = certain and cost is not None
    if cost is not None and cost <= 0:
        cost = None
    data["cost"] = cost
    if data.get("new_cost") is not None or kind in ("Nachtrag", "Beitragsanpassung"):
        data["new_cost"] = cost
    return data


def extract_insurance_data(text: str) -> dict:
    data = extract_insurance_data_regex(text)

    # Apply learned vendor patterns if company is detected. They are untrusted
    # input (partly community-sourced), so they only run through pattern_safety.
    company = data.get("company")
    if company:
        l_patterns = get_learned_patterns_for_company(company)
        if l_patterns:
            missing = {field: pats for field, pats in l_patterns.items() if not data.get(field)}
            for field, val in apply_patterns(text, missing).items():
                if field == "regional_class" and not val.upper().startswith("R"):
                    val = f"R{val}"
                data[field] = val

    finalize_extraction(data, text)

    # The name offered for the document. Built from insurer, kind of letter and date only
    # (see document_naming.py); the old "subject" guess often picked a footer sentence.
    # subject/document_title carry the same value because clients read either of them.
    title = suggest_title(data.get("company"), data.get("category"), text)
    data["suggested_title"] = title
    data["document_title"] = title
    data["subject"] = title

    # How far each value can be trusted (found in the text / computed / unsure), see field_checks.py
    data["field_checks"] = assess_fields(data, text)

    # Trigger automatic learning loop (100% anonymized, ZERO PII)
    if company and (data.get("regional_class") or data.get("type_class") or data.get("sf_class")):
        learn_from_feedback(company, data.get("doc_type", "Versicherung"), text, data)

    return data
