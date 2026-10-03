# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Compares language models on the one job the app gives them: reading the insurer and the
policy number from a letter when the rules found none (see ai_merge.py).

Two sets of letters, 25 in all:
* the real evaluation documents that are no information leaflets (``backend/eval/``, outside git),
* invented letters of other insurers and layouts (``synthetic_letters.py``).
The rules' results are switched off, the model is asked, and its answer goes through the same
checks as in the app (it must stand in the text and look like an insurer / a policy number).
For each model it prints speed, memory and how often the answer was right, wrongly accepted
or rejected. ``--baseline`` does the same for the rules alone, without a model.

    python tools/eval_models.py --baseline
    python tools/eval_models.py models/qwen2.5-1.5b-instruct-q4_k_m.gguf --name qwen1.5b --cpus 4
"""

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eval_extraction as ee  # noqa: E402  (paths, SECRET_KEY, Windows tool lookup)

ee.prepare_windows_tools()
sys.path.insert(0, ee.BACKEND)

import ai_merge  # noqa: E402
import ocr  # noqa: E402
from document_naming import detect_kind  # noqa: E402
from document_types import document_type_for, is_informational  # noqa: E402
from synthetic_letters import LETTERS  # noqa: E402

RESULTS = os.path.join(ee.EVAL_DIR, "model_results.jsonl")


def norm(value) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def matches_company(got, want) -> bool:
    g, w = norm(got), norm(want)
    return bool(g) and bool(w) and (w in g or g in w)


def matches_number(got, want) -> bool:
    return bool(norm(got)) and norm(got) == norm(want)


def cases():
    """[{set, name, text, company, number}] - letters the app would ask the model about."""
    out, seen = [], set()
    with open(ee.EXPECTED_PATH, encoding="utf-8") as f:
        expected = json.load(f)
    for name, want in sorted(expected.items()):
        text = ee.load_text(os.path.join(ee.DOCS_DIR, name), ocr)
        if is_informational(document_type_for(detect_kind(text))):
            continue                      # the app never asks the model about these
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest in seen:
            continue                      # the same letter twice
        seen.add(digest)
        out.append({"set": "echt", "name": name[:8], "text": text, "company": want["company"], "number": want["insurance_number"]})
    for i, letter in enumerate(LETTERS):
        out.append({"set": letter.get("group", "synthetisch"), "name": f"S{i + 1:02d} {letter['company'][:14]}", "text": letter["text"],
                    "company": letter["company"], "number": letter["insurance_number"]})
    return out


def classify(got, right: bool) -> str:
    if not got:
        return "abgelehnt"
    return "richtig" if right else "falsch angenommen"


def summarise(rows, fields=("company", "number")):
    stats = {}
    for field in fields:
        counts = {"richtig": 0, "falsch angenommen": 0, "abgelehnt": 0}
        raw_right = 0
        for r in rows:
            counts[r[field]["class"]] += 1
            raw_right += r[field]["raw_right"]
        stats[field] = {**counts, "roh_richtig": raw_right}
    return stats


def save_answers(name, answers):
    path = os.path.join(ee.EVAL_DIR, "model_answers.json")
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    data[name] = answers
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def run_baseline(cs):
    rows = []
    for c in cs:
        r = ocr.extract_insurance_data_regex(c["text"])
        row = {"set": c["set"], "name": c["name"]}
        row["company"] = {"value": r["company"], "raw_right": matches_company(r["company"], c["company"])}
        row["company"]["class"] = classify(r["company"], row["company"]["raw_right"])
        row["number"] = {"value": r["insurance_number"], "raw_right": matches_number(r["insurance_number"], c["number"])}
        row["number"]["class"] = classify(r["insurance_number"], row["number"]["raw_right"])
        row["fcompany"], row["fnumber"] = dict(row["company"]), dict(row["number"])
        rows.append(row)
    return rows


def run_model(path, name, threads, cpus, cs):
    import psutil
    from llama_cpp import Llama

    process = psutil.Process()
    if cpus:
        process.cpu_affinity(list(range(0, cpus * 2, 2)))   # every second logical core: separate physical cores
    rss_before = process.memory_info().rss / 1e6
    started = time.perf_counter()
    llm = Llama(model_path=path, n_ctx=ocr.LLM_CONTEXT_TOKENS, n_threads=threads, verbose=False)
    load_s = time.perf_counter() - started
    rss_after_load = process.memory_info().rss / 1e6
    grammar = ocr._get_answer_grammar()

    def ask(text):
        snippet = ocr.select_relevant_text(text, ocr.LLM_TEXT_CHARS)
        t = time.perf_counter()
        response = llm.create_chat_completion(messages=ocr.ai_messages(snippet), max_tokens=ocr.LLM_MAX_TOKENS,
                                              temperature=0.0, grammar=grammar)
        return response, time.perf_counter() - t

    ask(cs[0]["text"])                    # warm-up, not counted
    rows, times, prompt_tokens, answer_tokens, peak, answers = [], [], [], [], rss_after_load, []
    for c in cs:
        response, secs = ask(c["text"])
        peak = max(peak, process.memory_info().rss / 1e6)
        times.append(secs)
        prompt_tokens.append(response["usage"]["prompt_tokens"])
        answer_tokens.append(response["usage"]["completion_tokens"])
        try:
            parsed = json.loads(response["choices"][0]["message"]["content"])
        except Exception:
            parsed = {}
        company, number = (parsed.get("company") or None), (parsed.get("policy_number") or None)
        merged = ai_merge.merge_ai_into_rules({"company": None, "insurance_number": None},
                                              {"company": company, "insurance_number": number, "ai_model": name}, c["text"])
        row = {"set": c["set"], "name": c["name"], "answer": [company, number]}
        row["company"] = {"value": merged["company"], "raw_right": matches_company(company, c["company"])}
        row["company"]["class"] = classify(merged["company"], matches_company(merged["company"], c["company"]))
        row["number"] = {"value": merged["insurance_number"], "raw_right": matches_number(number, c["number"])}
        row["number"]["class"] = classify(merged["insurance_number"], matches_number(merged["insurance_number"], c["number"]))
        # the app: the rules lead, the model is asked only for what they left empty
        rules = ocr.extract_insurance_data_regex(c["text"])
        for key, value, check in (("fcompany", rules["company"] or merged["company"], matches_company),
                                  ("fnumber", rules["insurance_number"] or merged["insurance_number"], matches_number)):
            row[key] = {"value": value, "raw_right": 0, "class": classify(value, check(value, c["company"] if key == "fcompany" else c["number"]))}
        answers.append([c["name"], company, number])
        rows.append(row)

    ordered = sorted(times)
    size = sum(os.path.getsize(os.path.join(os.path.dirname(path), f)) for f in os.listdir(os.path.dirname(path))
               if f.startswith(os.path.basename(path)[:-len("-00001-of-00002.gguf")]) and f.endswith(".gguf")) \
        if "-00001-of-" in path else os.path.getsize(path)
    save_answers(name, answers)
    return rows, {
        "size_gb": round(size / 1e9, 2), "load_s": round(load_s, 1), "rss_after_load_mb": round(rss_after_load),
        "rss_peak_mb": round(peak), "rss_before_mb": round(rss_before),
        "time_median_s": round(statistics.median(times), 1), "time_mean_s": round(statistics.mean(times), 1),
        "time_p90_s": round(ordered[int(len(ordered) * 0.9) - 1], 1), "time_max_s": round(max(times), 1),
        "prompt_tokens_mean": round(statistics.mean(prompt_tokens)), "answer_tokens_mean": round(statistics.mean(answer_tokens)),
        "threads": threads, "cpus": cpus or os.cpu_count(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", nargs="?", help="path of a .gguf file")
    parser.add_argument("--name", default="")
    parser.add_argument("--baseline", action="store_true", help="the rules alone, no model")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--cpus", type=int, default=4, help="pin the process to this many physical cores (the server has 4)")
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()

    cs = cases()
    if args.baseline:
        rows, meta, name = run_baseline(cs), {}, "Regeln"
    else:
        name = args.name or os.path.basename(args.model)
        rows, meta = run_model(args.model, name, args.threads, args.cpus, cs)

    result = {"model": name, **meta}
    for label in ("echt", "synthetisch", "schwierig"):
        result[label] = summarise([r for r in rows if r["set"] == label])
        result[label]["kombiniert"] = summarise([r for r in rows if r["set"] == label], ("fcompany", "fnumber"))
        result[label]["n"] = sum(1 for r in rows if r["set"] == label)
    os.makedirs(ee.EVAL_DIR, exist_ok=True)
    with open(RESULTS, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    if args.details:
        for r in rows:
            print(f"{r['set'][:5]} {r['name']:20} Gesellschaft {r['company']['class']:18} {r['company']['value']!s:35} Nummer {r['number']['class']:18} {r['number']['value']}")


if __name__ == "__main__":
    main()
