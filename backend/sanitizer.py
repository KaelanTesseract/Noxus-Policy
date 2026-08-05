# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import re

def sanitize_text_for_learning(text: str) -> str:
    """
    Strict PII Sanitizer: Replaces all sensitive personal data (names, addresses,
    policy numbers, IBANs, license plates, emails, phone numbers, tax IDs)
    with generic structural tokens so that no private data can ever be stored or committed.
    """
    if not text:
        return ""

    sanitized = text

    # 1. Emails
    sanitized = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', sanitized)

    # 2. IBANs
    sanitized = re.sub(r'\b[A-Z]{2}\d{2}[ \xa0]?\d{4}[ \xa0]?\d{4}[ \xa0]?\d{4}[ \xa0]?\d{4}[ \xa0]?\d{0,2}\b', '[IBAN]', sanitized)

    # 3. Policy numbers (e.g. LJ-23375102-001, 669/246004-Q, #4#12345678##)
    sanitized = re.sub(r'#\d*#?[A-Za-z0-9\-/]{6,25}##', '[POLICY_NUM]', sanitized)
    sanitized = re.sub(r'\b[A-Z]{1,4}-\d{6,12}-\d{1,3}\b', '[POLICY_NUM]', sanitized)
    sanitized = re.sub(r'\b\d{3,6}/\d{5,9}-[A-Z0-9]\b', '[POLICY_NUM]', sanitized)

    # 4. License plates (e.g. HH-AB 1234, PI-DG 88, B-XY 123)
    sanitized = re.sub(r'\b[A-Z]{1,3}-[A-Z]{1,2}\s*\d{1,4}[E]?\b', '[LICENSE_PLATE]', sanitized)

    # 5. Names with honorifics or common labels (e.g. Herrn Dennis Guse, Frau Anna Schmidt, Herr von Nordeck)
    sanitized = re.sub(r'(?i)\b(?:herrn?|frau|dr\.|prof\.|von|mac|de)\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b', '[NAME]', sanitized)
    sanitized = re.sub(r'(?i)\b(?:kundenname|versicherungsnehmer|versicherter|betreut von|name)\s*:\s*[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b', '[NAME]', sanitized)

    # 6. Postal Codes & Cities (German 5-digit PLZ + City e.g., 20095 Hamburg, 23869 Elmenhorst)
    sanitized = re.sub(r'\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?\b', '[ZIP_CITY]', sanitized)

    # 7. Street addresses (e.g., Große Bäckerstraße 9, Fischbeker Str. 2a, Musterstraße 12)
    sanitized = re.sub(r'\b[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*(?:straße|str\.|weg|gasse|allee|platz|damm)\s+\d+[a-z]?\b', '[STREET_ADDRESS]', sanitized, flags=re.I)

    # 8. Phone & Fax numbers
    sanitized = re.sub(r'(?i)(?:tel|telefon|fax|mobil)\.?:?\s*\+?\d[\d\s\-/]{6,18}\d', '[PHONE]', sanitized)

    # 9. Tax IDs / Steuernummer (e.g., 12/345/67890 or DE123456789)
    sanitized = re.sub(r'\bDE\d{9}\b', '[VAT_ID]', sanitized)
    sanitized = re.sub(r'\b\d{2,3}/\d{3}/\d{4,5}\b', '[TAX_ID]', sanitized)

    # Fallback name cleanup for residual 2-word capitalized names
    sanitized = re.sub(r'\b[A-Z][a-z]{2,15}\s+[A-Z][a-z]{2,15}\b(?=,\s*\[STREET_ADDRESS\]|,\s*\[ZIP_CITY\])', '[NAME]', sanitized)

    return sanitized

def extract_safe_anchor_pattern(raw_text: str, target_val: str, label_keywords: list) -> str:
    """
    Extracts a generalized regex pattern relative to a label keyword
    without containing any private data. Returns None if target_val is not found safely.
    """
    if not target_val or not raw_text:
        return None

    str_val = str(target_val).strip()
    if len(str_val) == 0:
        return None

    # Search lines where label and target_val co-exist
    lines = raw_text.split('\n')
    for line in lines:
        if str_val in line:
            for kw in label_keywords:
                if re.search(r'(?i)\b' + re.escape(kw) + r'\b', line):
                    # Sanitize line first to prevent leaks
                    clean_line = sanitize_text_for_learning(line)
                    # Replace target_val with regex capture group token
                    esc_target = re.escape(str_val)
                    pattern_line = re.sub(esc_target, r'([A-Za-z0-9\\-/]+)', clean_line)
                    return pattern_line

    return None
