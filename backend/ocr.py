# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import re
import os
import json
import httpx
from datetime import datetime
try:
    from learning import get_learned_patterns_for_company, learn_from_feedback
except ImportError:
    from backend.learning import get_learned_patterns_for_company, learn_from_feedback

_llm_instance = None

def get_llm():
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    try:
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        model_dir = os.path.join(os.path.dirname(__file__), "models_data")
        if not os.path.exists(model_dir):
            model_dir = os.path.join(os.path.dirname(__file__), "models")
        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "qwen2.5-1.5b-instruct-q4_k_m.gguf")

        if not os.path.exists(model_path):
            print("[Mini-AI] Model not found locally. Auto-downloading Qwen2.5-1.5B-Instruct GGUF (~980 MB)...")
            downloaded = hf_hub_download(
                repo_id="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                filename="qwen2.5-1.5b-instruct-q4_k_m.gguf",
                local_dir=model_dir
            )
            print(f"[Mini-AI] Model successfully downloaded to: {downloaded}")

        print("[Mini-AI] Initializing embedded Llama-cpp engine (4 CPU threads)...")
        _llm_instance = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            verbose=False
        )
        return _llm_instance
    except Exception as e:
        print(f"[Mini-AI] Notice: Could not initialize embedded Llama model ({e}). Using regex fallback.")
        return None

def extract_text_from_file(filepath: str) -> str:
    text = ""
    try:
        if filepath.lower().endswith('.pdf'):
            try:
                from pypdf import PdfReader
                reader = PdfReader(filepath)
                num_pages = len(reader.pages)
                
                # For long multi-page documents (> 5 pages), prioritize first 3 and last 2 pages for metadata
                pages_to_read = range(num_pages)
                if num_pages > 5:
                    pages_to_read = list(range(0, min(5, num_pages))) + list(range(max(0, num_pages - 3), num_pages))
                    
                for idx in pages_to_read:
                    extracted = reader.pages[idx].extract_text()
                    if extracted:
                        text += f"--- Page {idx+1} ---\n" + extracted + "\n"
            except Exception as pe:
                print(f"pypdf extraction notice: {pe}")

            if not text.strip():
                images = convert_from_path(filepath, first_page=1, last_page=5)
                for img in images:
                    text += pytesseract.image_to_string(img, lang='deu') + "\n"
        else:
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img, lang='deu')
    except Exception as e:
        print(f"Error during OCR/text extraction: {e}")
    return text

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

def extract_with_mini_ai(text: str) -> dict:
    """Uses embedded Mini-AI (Llama-cpp Qwen2.5-1.5B) to extract structured insurance data."""
    if not text or len(text.strip()) < 10:
        return None

    llm = get_llm()
    if not llm:
        return None

    truncated_text = text[:3000]

    prompt = (
        "<|im_start|>system\n"
        "Du bist ein präziser deutscher Versicherungs-Experte. "
        "Analysiere den folgenden Vertragstext und extrahiere alle Informationen. "
        "WICHTIG für 'coverage_details': Extrahiere NUR TATSÄCHLICH VERSICHERTE LEISTUNGEN (ignoriere 'Was ist nicht versichert'!). "
        "Formatiere JEDE Leistung streng in grammatikalisch perfektem Deutsch nach dem Schema: 'Name der Leistung (Prägnante Nomen-Stichpunkte zur Abdeckung in Klammern)'. "
        "Kopiere NIEMALS lange Rohsätze wie 'Leistet, wenn...' oder 'Ersetzt berechtigte...'. Nutze stattdessen grammatikalisch saubere Substantivierungen!\n"
        "Beispiele für perfektes Deutsch:\n"
        "- 'Kfz-Haftpflichtversicherung (Personen- & Sachschäden an Dritten, Erstattung berechtigter Ansprüche & Abwehr unberechtigter Forderungen)'\n"
        "- 'Schutzbrief (Organisatorische & finanzielle Hilfe bei Panne oder Unfall, Pannenhilfe vor Ort & Abschleppen)'\n"
        "- 'Teilkasko (Schutz bei Glasbruch, Diebstahl, Hagel, Sturm & Wildunfällen)'\n"
        "- 'Vollkasko (Abdeckung von Unfallschäden am eigenen Fahrzeug & Vandalismus)'\n"
        "- 'Fahrerschutz (Übernahme von Personenschäden & Genesungskosten des Fahrers bei Unfall)'\n"
        "- 'Ausland-Schadenschutz (Schadenregulierung bei Unfällen im Ausland nach deutschem Standard)'\n"
        "- 'Kfz-Umweltschadenversicherung (Schutz vor öffentlich-rechtlichen Ansprüchen nach dem Umweltschadensgesetz)'\n"
        "Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt ohne Erklärungen oder Markdown.\n"
        "JSON-Format:\n"
        "{\n"
        '  "company": "Name des Versicherers (z.B. HUK-COBURG, HUK24, Allianz, AXA)",\n'
        '  "insurance_type": "Art der Versicherung (z.B. Kfz-Versicherung, Privathaftpflicht)",\n'
        '  "policy_number": "Versicherungsscheinnummer",\n'
        '  "contact_info": "Vollständige Firmenadresse mit PLZ und Ort (z.B. Bahnhofsplatz, 96444 Coburg)",\n'
        '  "start_date": "YYYY-MM-DD",\n'
        '  "end_date": "YYYY-MM-DD",\n'
        '  "cost": 123.45,\n'
        '  "payment_cycle": "monatlich", "vierteljährlich", "halbjährlich" oder "jährlich",\n'
        '  "category": "Kfz", "Haftpflicht", "Hausrat", "Leben", "Gesundheit", "Rechtsschutz" oder "Sonstige",\n'
        '  "sf_class": "Schadenfreiheitsklasse (z.B. SF 15, SF 1/2 oder SF 3)",\n'
        '  "regional_class": "Regionalklasse (z.B. R4 oder 04)",\n'
        '  "type_class": "Typklasse (z.B. 18 oder TK18)",\n'
        '  "is_price_change": true oder false (wenn das Dokument eine Beitragsanpassung/Beitragserhöhung ist),\n'
        '  "previous_cost": 100.00,\n'
        '  "new_cost": 120.00,\n'
        '  "coverage_details": ["Kfz-Haftpflichtversicherung (Personen- & Sachschäden an Dritten, Erstattung berechtigter Ansprüche)", "Schutzbrief (Organisatorische & finanzielle Hilfe bei Panne oder Unfall)"]\n'
        "}<|im_end|>\n"
        f"<|im_start|>user\nVERTRAGSTEXT:\n{truncated_text}<|im_end|>\n"
        "<|im_start|>assistant\n{"
    )

    try:
        response = llm(
            prompt,
            max_tokens=450,
            temperature=0.1,
            stop=["<|im_end|>"]
        )

        raw_json_str = "{" + response["choices"][0]["text"]
        
        if "}" in raw_json_str:
            raw_json_str = raw_json_str[:raw_json_str.rfind("}") + 1]

        parsed = json.loads(raw_json_str)

        company = str(parsed.get("company", "")).strip() or None
        ins_num = str(parsed.get("policy_number", "")).strip() or None
        ins_type = str(parsed.get("insurance_type", "")).strip() or "Versicherung"
        category = str(parsed.get("category", "")).strip() or "Sonstige"

        cost = None
        try:
            if parsed.get("cost") is not None:
                cost = float(parsed.get("cost"))
        except:
            pass

        payment_cycle = str(parsed.get("payment_cycle", "jährlich")).lower().strip()
        if payment_cycle not in ["monatlich", "vierteljährlich", "halbjährlich", "jährlich"]:
            payment_cycle = "jährlich"

        s_date = parse_date(str(parsed.get("start_date", "")))
        e_date = parse_date(str(parsed.get("end_date", "")))

        cov_details = parsed.get("coverage_details", [])
        if not isinstance(cov_details, list):
            cov_details = []

        cov_details = sanitize_coverage_details(cov_details)

        raw_s = str(parsed.get("start_date", ""))
        raw_e = str(parsed.get("end_date", ""))
        raw_c = str(parsed.get("cancellation_date", ""))
        s_date, e_date, c_date = calculate_insurance_dates(raw_s, raw_e, raw_c, text)
        ins_num = extract_policy_number_fallback(text, ins_num)

        exact_cost = extract_cost_fallback(text)
        final_cost = new_cost or cost
        if exact_cost and (not final_cost or final_cost == 150.0 or final_cost == 150 or re.search(r'150[^\n]*selbstbeteiligung', text, re.I)):
            final_cost = exact_cost

        sf_class = str(parsed.get("sf_class", "")).strip() or None
        regional_class = str(parsed.get("regional_class", "")).strip() or None
        regional_class = extract_regionalklasse_fallback(text, regional_class)
        type_class = str(parsed.get("type_class", "")).strip() or None
        is_price_change = bool(parsed.get("is_price_change", False))
        prev_cost = None
        try:
            if parsed.get("previous_cost") is not None: prev_cost = float(parsed.get("previous_cost"))
        except: pass
        new_cost = None
        try:
            if parsed.get("new_cost") is not None: new_cost = float(parsed.get("new_cost"))
        except: pass

        subject = str(parsed.get("subject", "") or parsed.get("document_title", "")).strip() or None
        if not subject:
            subject = extract_subject_fallback(text)

        print(f"[Mini-AI] Successfully extracted data with Qwen2.5-1.5B: Company='{company}', Policy='{ins_num}', Subject='{subject}', Start='{s_date}', End='{e_date}'")
        return {
            "company": company,
            "insurance_number": ins_num,
            "category": category,
            "doc_type": ins_type,
            "subject": subject,
            "document_title": subject,
            "suggested_title": subject or (f"{company or ins_type} - {ins_num or 'Polizze'}"),
            "cost": final_cost,
            "payment_cycle": payment_cycle,
            "start_date": s_date,
            "end_date": e_date,
            "cancellation_date": c_date,
            "coverage_details": cov_details,
            "sf_class": sf_class,
            "regional_class": regional_class,
            "type_class": type_class,
            "is_price_change": is_price_change,
            "previous_cost": prev_cost,
            "new_cost": final_cost,
            "ai_used": True,
            "ai_model": "Qwen2.5-1.5B (Embedded)"
        }
    except Exception as e:
        print(f"[Mini-AI] Exception during AI execution ({e}). Using regex fallback.")

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

def extract_policy_number_fallback(text: str, current_num: str = None) -> str:
    # 1. Direct pattern like LJ-12345678-001 or 123/456789-A or VSN-999999 (High precision)
    direct_match = re.search(r'\b([A-Z]{1,4}-\d{6,12}-\d{1,3}|\d{3}/\d{6}-[A-Za-z0-9])\b', text)
    if direct_match:
        val = direct_match.group(1).strip()
        if not is_invalid_policy_num(val):
            return val

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
        m = re.search(pat, text)
        if m:
            raw = m.group(1).upper().replace(" ", "").replace("-", "").replace("O", "0")
            if not raw.startswith("R"):
                raw = f"R{raw}"
            if re.match(r'^R\d{1,2}$', raw):
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

def extract_cost_fallback(text: str) -> float:
    if not text:
        return None

    # Priority 1: Direct Guthaben / Erstattung / Gutschrift / Abrechnung total match
    # e.g. "Das Guthaben wird Ihrem Beitragskonto gutgeschrieben: 40,33- €" or "Erstattungsbeitrag ... 40,33- €"
    m_guthaben = re.search(r'(?i)(?:guthaben|erstattungsbeitrag|erstattung|gutschrift|abrechnung|rückerstattung)[^\n]*?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*-?)\s*(?:€|EUR)', text)
    if m_guthaben:
        val = parse_german_amount(m_guthaben.group(1))
        if val is not None:
            return val

    # Priority 2: Total line match (e.g. "Gesamtbeitrag inkl. 19 % ... 49,53 €" or "Zwischensumme 40,33- €")
    for line in text.split('\n'):
        if re.search(r'(?i)gesamtbeitrag|zahlbeitrag|gesamt|bruttobeitrag|zwischensumme|erstattungsbeitrag', line):
            amounts = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*-?)\s*(?:€|EUR)', line)
            if amounts:
                val = parse_german_amount(amounts[-1])
                if val is not None:
                    return val

    # Priority 3: Explicit total premium line with tax
    m1 = re.search(r'(?i)beitrag\s*\([^)]*inklusive[^)]*\)\s*[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*-?)\s*(?:€|EUR)', text)
    if m1:
        val = parse_german_amount(m1.group(1))
        if val is not None:
            return val

    m2 = re.search(r'(?i)(?:gesamtbeitrag|zahlbeitrag|beitrag\s*inkl\.?\s*steuer)\s*[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*-?)\s*(?:€|EUR)', text)
    if m2:
        val = parse_german_amount(m2.group(1))
        if val is not None:
            return val

    # Priority 4: Single line scan for premium or credit
    for line in text.split('\n'):
        if re.search(r'(?i)selbstbeteiligung|selbstbehalt|ohne versicherungsteuer|kfz\-haftpflicht|teilkasko|vollkasko', line):
            continue
        m = re.search(r'(?i)(?:beitrag|prämie|erstattung|guthaben|gutschrift)\s*[:\s]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*-?)\s*(?:€|EUR)', line)
        if m:
            val = parse_german_amount(m.group(1))
            if val is not None:
                return val

    # Priority 5: Fallback scan lines for any valid amount
    valid_costs = []
    for line in text.split('\n'):
        if re.search(r'(?i)(selbstbeteiligung|selbstbehalt|pauschal|deckungssumme|umweltschadensgesetz|personenschäden|ohne versicherungsteuer)', line):
            continue
        m = re.search(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*-?)\s*(?:€|EUR|Euro)', line)
        if m:
            val = parse_german_amount(m.group(1))
            if val is not None and abs(val) >= 0.01:
                valid_costs.append(val)

    if valid_costs:
        return valid_costs[0]

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
    match_start = re.search(r'(?i)(?:beginn der änderung|versicherungsbeginn|vertragsbeginn|beginn|gültig ab|fällig am|zeitraum|am)\.?:?\s*(\d{2}\.\d{2}\.\d{4})', text)
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
            month = e_date.month - 1
            year = e_date.year
            if month == 0:
                month = 12
                year -= 1
            day = min(e_date.day, 28)
            c_date = datetime.date(year, month, day)
        except Exception:
            pass

    return s_date, e_date, c_date

def sanitize_coverage_details(coverage_list: list) -> list:
    cleaned = []
    for item in coverage_list:
        if not isinstance(item, str) or not item.strip():
            continue
        s = item.strip()

        # Filter out negative statements or non-covered items
        if re.search(r'(?i)(:\s*nein|ist nicht vertragsinhalt|nicht versichert|erloschen|ausgeschlossen)', s):
            continue

        # Convert raw copied sentences to grammatically perfect German
        if "Leistet, wenn mit dem versicherten Fahrzeug" in s or "berechtigte Ansprüche" in s:
            cleaned.append("Kfz-Haftpflichtversicherung (Personen- & Sachschäden an Dritten, Erstattung berechtigter Ansprüche & Abwehr unberechtigter Forderungen)")
        elif "Bietet organisatorische und finanzielle Hilfe" in s:
            cleaned.append("Schutzbrief (Organisatorische & finanzielle Hilfe bei Panne oder Unfall, Pannenhilfe vor Ort & Abschleppen)")
        elif "Ersetzt Schäden an Ihrem Fahrzeug durch Vandalismus" in s or "Vollkasko" in s and "(" not in s:
            cleaned.append("Vollkasko (Abdeckung von Unfallschäden am eigenen Fahrzeug & Vandalismus)")
        elif "Ersetzt den Personenschaden des Fahrers" in s or "Fahrerschutz" in s and "(" not in s:
            cleaned.append("Fahrerschutz (Übernahme von Personenschäden & Genesungskosten des Fahrers bei Unfall)")
        elif "Ersetzt Ihren Personen- und Sachschaden bei einem Unfall im Ausland" in s or "Ausland-Schadenschutz" in s and "(" not in s:
            cleaned.append("Ausland-Schadenschutz (Schadenregulierung bei Unfällen im Ausland nach deutschem Standard)")
        elif "Schützt Sie vor öffentlich-rechtlichen Ansprüchen nach dem Umweltschadensgesetz" in s or "Umweltschaden" in s and "(" not in s:
            cleaned.append("Kfz-Umweltschadenversicherung (Schutz vor öffentlich-rechtlichen Ansprüchen nach dem Umweltschadensgesetz)")
        elif "Versichert sind z. B. Diebstahl, Hagel, Sturm" in s or "Teilkasko" in s and "(" not in s:
            cleaned.append("Teilkasko (Schutz bei Glasbruch, Diebstahl, Hagel, Sturm & Wildunfällen)")
        elif "Ersetzt Schäden an Ihrem Fahrzeug durch Verschleiß" in s:
            continue
        else:
            cleaned.append(s)

    return list(dict.fromkeys(cleaned))

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

    if not data["company"]:
        comp_match = re.search(r'([A-ZÄÖÜa-zäöü0-9\-\s]{3,30}\s+(?:Versicherung(?:en)?|AG|SE|VVaG|Krankenkasse))', text)
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
    
    # Kfz
    if re.search(r'(?i)(kfz\-haftpflicht|kraftfahrt-haftpflicht)', text):
        coverage_details.append("Kfz-Haftpflichtversicherung (Schäden an Drittfahrzeugen, Personenschäden & Abwehr unberechtigter Ansprüche)")
    if re.search(r'(?i)(schutzbrief)', text) and not re.search(r'(?i)schutzbrief[^\n]*ist nicht vertragsinhalt', text):
        coverage_details.append("Schutzbrief (Organisatorische & finanzielle Hilfe bei Panne oder Unfall, Abschleppen & Mietwagen)")
    if re.search(r'(?i)(teilkasko)', text):
        coverage_details.append("Teilkasko (Schutz bei Glasbruch, Diebstahl, Hagel, Sturm & Wildunfällen)")
    if re.search(r'(?i)(vollkasko)', text) and not re.search(r'(?i)vollkasko[^\n]*ist nicht vertragsinhalt', text):
        coverage_details.append("Vollkasko (Abdeckung von Unfallschäden am eigenen Fahrzeug & Vandalismus)")
    if re.search(r'(?i)(fahrerschutz)', text) and not re.search(r'(?i)fahrerschutz[^\n]*ist nicht vertragsinhalt', text):
        coverage_details.append("Fahrerschutz (Übernahme von Personenschäden & Genesungskosten des Fahrers bei Unfall)")
    if re.search(r'(?i)(ausland\-schadenschutz)', text) and not re.search(r'(?i)ausland\-schadenschutz[^\n]*ist nicht vertragsinhalt', text):
        coverage_details.append("Ausland-Schadenschutz (Schadenregulierung bei Unfällen im Ausland nach deutschem Standard)")
    if re.search(r'(?i)(umweltschaden|umweltschadensgesetz)', text):
        coverage_details.append("Kfz-Umweltschadenversicherung (Schutz vor öffentlich-rechtlichen Ansprüchen nach dem Umweltschadensgesetz)")

    # Exclude false positives like "Wohngebäude bei der Itzehoer versichert: Nein"
    if re.search(r'(?i)(wohngebäude|gebäudeversicherung)', text) and not re.search(r'(?i)wohngebäude[^\n]*:\s*nein', text) and not re.search(r'(?i)wohngebäude[^\n]*ist nicht', text):
        coverage_details.append("Wohngebäudeversicherung (Absicherung gegen Feuer, Sturm, Hagel, Leitungswasser & Elementarschäden)")

    # Haftpflicht
    if re.search(r'(?i)(privathaftpflicht)', text):
        coverage_details.append("Privathaftpflicht (Schäden an Dritten, Mietsachschäden, Gefälligkeitshandlungen & Schlüsselverlust)")
    if re.search(r'(?i)(hundehaftpflicht|tierhalterhaftpflicht)', text):
        coverage_details.append("Tierhalterhaftpflicht (Personen- & Sachschäden durch Haustiere/Hunde an Dritten)")
    if re.search(r'(?i)(bauherrenhaftpflicht|haus-? und grundbesitzer)', text):
        coverage_details.append("Haus- & Grundbesitzerhaftpflicht (Absicherung von Verkehrssicherungspflichten & Bauherrenschäden)")

    # Hausrat
    if re.search(r'(?i)(hausrat)', text):
        coverage_details.append("Hausratversicherung (Schutz bei Einbruchdiebstahl, Vandalismus, Leitungswasser, Sturm & Hagel)")

    # Rechtsschutz
    if re.search(r'(?i)(rechtsschutz)', text):
        if re.search(r'(?i)(verkehrsrechtsschutz)', text):
            coverage_details.append("Verkehrsrechtsschutz (Kostendeckung bei Streitigkeiten im Straßenverkehr & Anwaltskosten)")
        if re.search(r'(?i)(berufsrechtsschutz)', text):
            coverage_details.append("Berufsrechtsschutz (Rechtlicher Schutz bei Arbeitsplatz- & Arbeitsvertragsstreitigkeiten)")
        if re.search(r'(?i)(mietrechtsschutz|immobilienrechtsschutz)', text):
            coverage_details.append("Miet- & Immobilienrechtsschutz (Rechtsschutz bei Konflikten zwischen Mieter und Vermieter)")
        if not any("rechtsschutz" in c.lower() for c in coverage_details):
            coverage_details.append("Rechtsschutz (Übernahme von Anwalts- & Gerichtskosten sowie Freie Anwaltswahl)")

    # Gesundheit & Zahn
    if re.search(r'(?i)(zahnzusatz|zahnersatz|zahnbehandlung)', text):
        coverage_details.append("Zahnzusatzversicherung (Kostenerstattung für professionelle Zahnreinigung, Inlays & Zahnersatz)")
    if re.search(r'(?i)(krankentagegeld|krankengeld)', text):
        coverage_details.append("Krankentagegeld (Einkommenssicherung bei längerer Krankheitsdauer)")

    # Leben & Vorsorge
    if re.search(r'(?i)(berufsunfähigkeit|bu\-rente)', text):
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

    # Price Adjustment / Price Change Regex Extraction
    if re.search(r'(?i)(beitragsanpassung|beitragserhöhung|neuer beitrag|beitragsänderung|jahresrechnung)', text):
        data["is_price_change"] = True
        data["doc_type"] = "Beitragsanpassung"

    data["coverage_details"] = coverage_details
    return data

def extract_insurance_data(text: str, db=None) -> dict:
    use_ai = True
    if db is not None:
        try:
            import models
            setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "use_ai_ocr").first()
            if setting and setting.value is not None:
                use_ai = setting.value.lower() in ["true", "1", "yes"]
        except Exception as se:
            print(f"Notice checking AI setting: {se}")

    if use_ai:
        data = extract_with_mini_ai(text)
        if not data:
            data = extract_insurance_data_regex(text)
            data["ai_used"] = False
    else:
        data = extract_insurance_data_regex(text)
        data["ai_used"] = False

    # Apply learned vendor patterns if company is detected
    company = data.get("company")
    if company:
        l_patterns = get_learned_patterns_for_company(company)
        if l_patterns:
            for field, pat_list in l_patterns.items():
                if not data.get(field):
                    for pat in pat_list:
                        m = re.search(pat, text)
                        if m:
                            val = m.group(1).strip()
                            if field == "regional_class" and not val.upper().startswith("R"):
                                val = f"R{val}"
                            data[field] = val
                            break

    # Trigger automatic learning loop (100% anonymized, ZERO PII)
    if company and (data.get("regional_class") or data.get("type_class") or data.get("sf_class")):
        learn_from_feedback(company, data.get("doc_type", "Versicherung"), text, data)

    return data
