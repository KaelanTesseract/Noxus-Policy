import re
from datetime import datetime

raw_text = """
669246004QHUK24 AG, HUK-COBURG-Platz 1, 96440 Coburg
Herrn
Dennis Guse
Fischbeker Str. 2 A
23869 Elmenhorst 
 
Coburg, 23.07.2026
Versicherungsschein - Kraftfahrtversicherung Nr. 669/246004-Q
bei der HUK24 AG
 
Grund der Ausfertigung
Neuer Vertrag Ausfertigung des Versicherungsscheins
 
Wichtiger Hinweis Wir buchen den fälligen Erstbeitrag in Höhe von 29,26 € von Ihrem Konto 
ab. Bitte sorgen Sie rechtzeitig für ausreichende Kontodeckung.

Vertragsdauer Beginn Ablauf
Kfz-Haftpflichtversicherung 23.07.2026, 0 Uhr 23.07.2027, 0 Uhr
Kaskoversicherung 24.07.2026, 0 Uhr 23.07.2027, 0 Uhr
 
Versichertes Fahrzeug
Fahrzeugart, Hersteller Anhänger, ANSSEMS (NL)
Gefahrgut keine erlaubnispflichtige Gefahrgutbeförderung
Amtliches Kennzeichen OD-DG 2205
Leistung, Erstzulassung 750 kg Gesamtmasse, 07/2026
Fahrzeug-Identifizierungs-Nr. XLJG1070242335086
 
Versicherungsumfang
Kfz-Haftpflichtversicherung 100 Mio. € Versicherungssumme für Personen-, Sach- und Vermögensschäden 17,95 €
Kaskoversicherung Teilkasko 150 € Selbstbeteiligung 11,34 €
Versicherter Fahrzeugwert 1.800,00 €
 
Jahresbeitrag Gültig ab 24.07.2026 29,29 €
Kontoauszug
Zahlungsweise Jährlich
"""

def parse_date(date_str: str):
    date_str = date_str.strip().strip('.').strip(':')
    formats = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None

def extract_data(text):
    data = {
        "company": None,
        "insurance_number": None,
        "category": None,
        "cost": None,
        "payment_cycle": "jährlich",
        "start_date": None,
        "end_date": None,
        "cancellation_date": None,
    }

    # 1. Company
    if "HUK24" in text:
        data["company"] = "HUK24 AG"
    elif "HUK-COBURG" in text or "HUK" in text:
        data["company"] = "HUK-COBURG"

    # 2. Category
    if re.search(r'(?i)(kraftfahrt|kfz|auto|fahrzeug|anhänger|kasko)', text):
        data["category"] = "Kfz-Versicherung"
    elif re.search(r'(?i)(haftpflicht)', text):
        data["category"] = "Haftpflicht"

    # 3. Insurance Number
    # Match "... Nr. 669/246004-Q" or "Versicherungsschein... Nr. 669/246004-Q"
    vsn_match = re.search(r'(?i)(Versicherungsschein|Kraftfahrtversicherung|Vertrag|Polizze|Versicherungs\-?Nr)[\w\s\-]*Nr\.?[\s\:]*([A-Z0-9\/\-]+)', text)
    if vsn_match:
        data["insurance_number"] = vsn_match.group(2).strip()

    # 4. Payment Cycle
    cycle_match = re.search(r'(?i)Zahlungsweise[\s\:\.]*(\w+)', text)
    if cycle_match:
        data["payment_cycle"] = cycle_match.group(1).lower()

    # 5. Cost
    cost_match = re.search(r'(?i)(Jahresbeitrag|Erstbeitrag|Gesamtbeitrag|Zahlbeitrag)[\w\s\:\.]*?([\d]+[\,\.][\d]{2})\s*€?', text)
    if cost_match:
        try:
            data["cost"] = float(cost_match.group(2).replace(',', '.'))
        except:
            pass

    # 6. Start & End Dates
    # Pattern for "Beginn Ablauf \n ... 23.07.2026 ... 23.07.2027" or "23.07.2026 ... 23.07.2027"
    start_match = re.search(r'(?i)(Beginn|Gültig ab|Inkrafttreten)[\s\:\,\w]*?(\d{2}\.\d{2}\.\d{4})', text)
    if start_match:
        data["start_date"] = parse_date(start_match.group(2))

    end_match = re.search(r'(?i)(Ablauf|Vertragsende|Laufzeit bis|Ende)[\s\:\,\w]*?(\d{2}\.\d{2}\.\d{4})', text)
    if not end_match:
        # Fallback: Find date range e.g. 23.07.2026 ... 23.07.2027
        pair_match = re.search(r'(\d{2}\.\d{2}\.\d{4})[\s\,\w\d]*?(\d{2}\.\d{2}\.\d{4})', text)
        if pair_match:
            data["start_date"] = parse_date(pair_match.group(1))
            data["end_date"] = parse_date(pair_match.group(2))
    else:
        data["end_date"] = parse_date(end_match.group(2))

    if data["end_date"]:
        try:
            ed = data["end_date"]
            month = ed.month - 3
            year = ed.year
            if month <= 0:
                month += 12
                year -= 1
            day = ed.day
            if month == 2 and day > 28:
                day = 28
            elif day == 31 and month in [4, 6, 9, 11]:
                day = 30
            data["cancellation_date"] = datetime(year, month, day).date()
        except:
            pass

    return data

print(extract_data(raw_text))
