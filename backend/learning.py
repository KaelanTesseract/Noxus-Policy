# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
import json
import re
try:
    from sanitizer import sanitize_text_for_learning, extract_safe_anchor_pattern
except ImportError:
    from backend.sanitizer import sanitize_text_for_learning, extract_safe_anchor_pattern

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PATTERNS_FILE = os.path.join(DATA_DIR, "vendor_patterns.json")

def load_vendor_patterns() -> dict:
    if not os.path.exists(PATTERNS_FILE):
        return {"_meta": {"version": "1.0.0"}, "vendors": {}}
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[LearningEngine] Error loading vendor patterns: {e}")
        return {"_meta": {"version": "1.0.0"}, "vendors": {}}

def save_vendor_patterns(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[LearningEngine] Error saving vendor patterns: {e}")

def get_vendor_key(company_name: str) -> str:
    if not company_name:
        return "generic"
    clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
    for kw in ["itzehoer", "huk24", "huk", "allianz", "devk", "ergo", "axa", "gothaer", "vvg", "signal"]:
        if kw in clean:
            return kw
    return clean[:15] if clean else "generic"

def learn_from_feedback(company: str, doc_type: str, raw_ocr_text: str, verified_data: dict):
    """
    Main learning entry point.
    Extracts vendor patterns strictly anonymously and merges them into vendor_patterns.json.
    NO PII (names, addresses, policy numbers, IBANs, etc.) IS EVER STORED!
    """
    if not company or not verified_data or not raw_ocr_text:
        return

    v_key = get_vendor_key(company)
    patterns_db = load_vendor_patterns()
    vendors = patterns_db.setdefault("vendors", {})
    v_entry = vendors.setdefault(v_key, {
        "company_aliases": [company.lower().strip()],
        "patterns": {}
    })
    
    # Ensure aliases list exists
    aliases = v_entry.setdefault("company_aliases", [])
    if company.lower().strip() not in aliases:
        aliases.append(company.lower().strip())

    v_patterns = v_entry.setdefault("patterns", {})

    # Learn Regionalklasse pattern
    regio = verified_data.get("regional_class")
    if regio:
        p = extract_safe_anchor_pattern(raw_ocr_text, regio, ["regionalklasse", "regio", "tarifgruppe", "r-klasse"])
        if p and p not in v_patterns.setdefault("regional_class", []):
            v_patterns["regional_class"].append(p)

    # Learn Typklasse pattern
    typ = verified_data.get("type_class")
    if typ:
        p = extract_safe_anchor_pattern(raw_ocr_text, typ, ["typklasse", "tk", "typ-klasse", "typ"])
        if p and p not in v_patterns.setdefault("type_class", []):
            v_patterns["type_class"].append(p)

    # Learn SF-Klasse pattern
    sf = verified_data.get("sf_class")
    if sf:
        sf_clean = sf.replace("SF ", "").replace("sf ", "").strip()
        p = extract_safe_anchor_pattern(raw_ocr_text, sf_clean, ["sf-klasse", "schadenfreiheitsklasse", "sf"])
        if p and p not in v_patterns.setdefault("sf_class", []):
            v_patterns["sf_class"].append(p)

    save_vendor_patterns(patterns_db)
    print(f"[LearningEngine] Successfully updated patterns for vendor '{v_key}' safely (ZERO PII).")

def get_learned_patterns_for_company(company_name: str) -> dict:
    if not company_name:
        return {}
    v_key = get_vendor_key(company_name)
    db = load_vendor_patterns()
    vendors = db.get("vendors", {})
    return vendors.get(v_key, {}).get("patterns", {})
