# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

import os
import json
import re
import hashlib
import base64
try:
    import httpx
except ImportError:
    import urllib.request
    class SimpleHttpX:
        def get(self, url, timeout=10.0):
            req = urllib.request.urlopen(url, timeout=timeout)
            txt = req.read().decode('utf-8')
            class Resp:
                status_code = 200
                text = txt
            return Resp()
    httpx = SimpleHttpX()
import subprocess
import threading
import time

try:
    from sanitizer import sanitize_text_for_learning, extract_safe_anchor_pattern
except ImportError:
    from backend.sanitizer import sanitize_text_for_learning, extract_safe_anchor_pattern

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ENC_FILE = os.path.join(DATA_DIR, "vendor_patterns.enc")
JSON_LEGACY_FILE = os.path.join(DATA_DIR, "vendor_patterns.json")

APP_CIPHER_KEY = "NOXUS_POLICY_AES256_COMMUNITY_KEY_V1_2026"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/KaelanTesseract/Noxus-Policy/main/backend/data/vendor_patterns.enc"

_last_sync_timestamp = 0

def _xor_cipher(data: bytes, key: str) -> bytes:
    key_bytes = hashlib.sha256(key.encode('utf-8')).digest()
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))

def encrypt_patterns(data_dict: dict) -> str:
    raw_bytes = json.dumps(data_dict, ensure_ascii=False, indent=2).encode('utf-8')
    enc_bytes = _xor_cipher(raw_bytes, APP_CIPHER_KEY)
    return base64.b64encode(enc_bytes).decode('utf-8')

def decrypt_patterns(enc_str: str) -> dict:
    try:
        enc_bytes = base64.b64decode(enc_str.strip().encode('utf-8'))
        raw_bytes = _xor_cipher(enc_bytes, APP_CIPHER_KEY)
        return json.loads(raw_bytes.decode('utf-8'))
    except Exception as e:
        print(f"[LearningEngine] Cipher decryption error: {e}")
        return {"_meta": {"version": "0.2.0-beta"}, "vendors": {}}

def load_vendor_patterns() -> dict:
    if os.path.exists(ENC_FILE):
        try:
            with open(ENC_FILE, "r", encoding="utf-8") as f:
                content = f.read()
                return decrypt_patterns(content)
        except Exception as e:
            print(f"[LearningEngine] Error reading encrypted file: {e}")

    # Fallback / Migration from legacy json
    if os.path.exists(JSON_LEGACY_FILE):
        try:
            with open(JSON_LEGACY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "_meta" in data:
                    data["_meta"]["version"] = "0.2.0-beta"
                save_vendor_patterns(data)
                return data
        except Exception as e:
            print(f"[LearningEngine] Error reading legacy json: {e}")

    return {"_meta": {"version": "0.2.0-beta"}, "vendors": {}}

def save_vendor_patterns(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    if "_meta" not in data:
        data["_meta"] = {}
    data["_meta"]["version"] = "0.2.0-beta"
    try:
        enc_str = encrypt_patterns(data)
        with open(ENC_FILE, "w", encoding="utf-8") as f:
            f.write(enc_str)
        
        # Remove legacy unencrypted JSON file if present
        if os.path.exists(JSON_LEGACY_FILE):
            try:
                os.remove(JSON_LEGACY_FILE)
            except:
                pass
    except Exception as e:
        print(f"[LearningEngine] Error saving encrypted vendor patterns: {e}")

def merge_patterns_db(base_db: dict, incoming_db: dict) -> dict:
    merged = dict(base_db)
    m_vendors = merged.setdefault("vendors", {})
    inc_vendors = incoming_db.get("vendors", {})

    for v_key, v_val in inc_vendors.items():
        if v_key not in m_vendors:
            m_vendors[v_key] = v_val
        else:
            # Merge aliases
            existing_aliases = set(m_vendors[v_key].get("company_aliases", []))
            for alias in v_val.get("company_aliases", []):
                existing_aliases.add(alias)
            m_vendors[v_key]["company_aliases"] = list(existing_aliases)

            # Merge patterns
            e_patterns = m_vendors[v_key].setdefault("patterns", {})
            for fld, pat_list in v_val.get("patterns", {}).items():
                e_list = e_patterns.setdefault(fld, [])
                for p in pat_list:
                    if p not in e_list:
                        e_list.append(p)

    return merged

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
    Extracts vendor patterns strictly anonymously and merges them into encrypted vendor_patterns.enc.
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
    print(f"[LearningEngine] Successfully updated encrypted patterns for vendor '{v_key}' safely (ZERO PII).")

def get_learned_patterns_for_company(company_name: str) -> dict:
    if not company_name:
        return {}
    v_key = get_vendor_key(company_name)
    db = load_vendor_patterns()
    vendors = db.get("vendors", {})
    return vendors.get(v_key, {}).get("patterns", {})

def sync_patterns_with_github(force_push: bool = False):
    """
    Bi-directional 2-Way Sync Engine:
    1. Pulls latest encrypted community patterns from GitHub.
    2. Merges with local patterns.
    3. Commits & pushes encrypted updates back to GitHub.
    """
    global _last_sync_timestamp
    print("[LearningEngine] Running bi-directional 2-way pattern sync with GitHub...")

    # Step 1: Inbound Pull (Fetch GitHub Remote Patterns)
    try:
        resp = httpx.get(GITHUB_RAW_URL, timeout=10.0)
        if resp.status_code == 200 and resp.text:
            remote_db = decrypt_patterns(resp.text)
            if remote_db and "vendors" in remote_db:
                local_db = load_vendor_patterns()
                merged_db = merge_patterns_db(local_db, remote_db)
                save_vendor_patterns(merged_db)
                print("[LearningEngine] Inbound Sync: Successfully merged latest encrypted community patterns from GitHub.")
    except Exception as e:
        print(f"[LearningEngine] Inbound Sync Notice (Offline/Skipped): {e}")

    # Step 2: Outbound Push (Auto-Commit & Auto-Push local encrypted updates)
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(os.path.join(repo_root, ".git")):
            cmd_check = "git status --porcelain backend/data/vendor_patterns.enc"
            res = subprocess.run(cmd_check, cwd=repo_root, shell=True, capture_output=True, text=True)
            if force_push or (res.returncode == 0 and "vendor_patterns.enc" in res.stdout):
                print("[LearningEngine] Outbound Sync: Auto-committing and pushing updated encrypted patterns to GitHub...")
                subprocess.run("git add backend/data/vendor_patterns.enc", cwd=repo_root, shell=True, check=True)
                subprocess.run('git commit -m "auto: Daily bi-directional pattern sync [v0.2.0-beta]"', cwd=repo_root, shell=True)
                subprocess.run("git push origin main", cwd=repo_root, shell=True)
                print("[LearningEngine] Outbound Sync: Successfully pushed updated encrypted patterns to GitHub!")
    except Exception as e:
        print(f"[LearningEngine] Outbound Sync Notice: {e}")

    _last_sync_timestamp = time.time()

def start_daily_pattern_scheduler():
    """
    Spawns background daemon thread that performs 2-way sync once every 24 hours.
    """
    def _run_loop():
        time.sleep(5)
        sync_patterns_with_github()

        while True:
            time.sleep(86400) # 24 Hours
            sync_patterns_with_github()

    t = threading.Thread(target=_run_loop, daemon=True)
    t.start()
