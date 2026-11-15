"""
End-to-end answer quality through the gateway, per provider.
Usage:  python eval/eval_answers.py --providers ollama,groq
Keys:   set env vars STUDYRAG_KEY_GROQ, STUDYRAG_KEY_GEMINI ... (sent as X-Api-Key, never saved)
"""
import argparse, csv, json, os, re, statistics, time
import httpx
from common import norm, is_match

REFUSAL = ["pas trouve", "n'ai pas trouve", "ne trouve pas", "did not find", "not find", "no relevant passage",
           "aucun passage", "not in the documents", "pas dans les documents", "aucune information"]

ap = argparse.ArgumentParser()
ap.add_argument("--questions", default="eval/questions.json")
ap.add_argument("--base", default="http://localhost:8000")
ap.add_argument("--providers", default="ollama")
ap.add_argument("--top-k", type=int, default=4)
ap.add_argument("--delay", type=float, default=2.0, help="seconds between calls (free-tier rate limits)")
ap.add_argument("--label", default="answers")
a = ap.parse_args()

def ask(q, provider):
    headers = {}
    key = os.getenv("STUDYRAG_KEY_" + provider.upper())
    if key:
        headers["X-Api-Key"] = key
    body = {"question": q["question"], "course": q.get("course"), "provider": provider,
            "top_k": a.top_k, "history": []}
    text, sources, done, err = "", [], {}, ""
    t0 = time.perf_counter(); first = None
    with httpx.stream("POST", f"{a.base}/api/ask", json=body, headers=headers, timeout=300) as r:
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            ev = json.loads(line[6:])
            if ev["type"] == "sources":
                sources = ev["sources"]
            elif ev["type"] == "token":
                if first is None:
                    first = time.perf_counter() - t0
                text += ev["text"]
            elif ev["type"] == "done":
                done = ev
            elif ev["type"] == "error":
                err = ev.get("code", "error")
    return text, sources, done, err, first, time.perf_counter() - t0

rows = []
qs = json.load(open(a.questions, encoding="utf-8"))
for provider in a.providers.split(","):
    for q in qs:
        try:
            text, sources, done, err, first, total = ask(q, provider)
        except Exception as e:
            text, sources, done, err, first, total = "", [], {}, f"client:{type(e).__name__}", None, 0
        nt = norm(text)
        if q["source_type"] == "no_answer":
            cov = None; src_ok = None; cited = None
            refused = any(p in nt for p in REFUSAL)
        else:
            kws = q["keywords"]
            cov = sum(1 for k in kws if norm(k) in nt) / len(kws) if kws else None
            src_ok = any(is_match(s["file"], s.get("page"), q) for s in sources)
            cited = bool(re.search(r"\[\d+\]", text))
            refused = None
        rows.append({"provider": provider, "id": q["id"], "type": q["source_type"], "coverage": cov,
                     "source_ok": src_ok, "cited": cited, "refused": refused, "error": err,
                     "fallback": done.get("fallback"), "provider_used": done.get("provider_used"),
                     "ttft_ms": round(first * 1000) if first else None, "total_ms": round(total * 1000),
                     "answer": text.replace("\n", " ")[:600]})
        print(f"{provider:<10} q{q['id']:>2} cov={cov} src={src_ok} cited={cited} refused={refused} err={err} {rows[-1]['total_ms']}ms")
        time.sleep(a.delay)

def avg(v):
    v = [x for x in v if x is not None]
    return round(sum(v) / len(v), 2) if v else None
print("\n=== SUMMARY per provider")
for p in sorted({r["provider"] for r in rows}):
    R = [r for r in rows if r["provider"] == p]
    real = [r for r in R if r["type"] != "no_answer"]
    na = [r for r in R if r["type"] == "no_answer"]
    print(f"{p}: keyword coverage={avg([r['coverage'] for r in real])}  "
          f"source found={avg([int(r['source_ok']) for r in real])}  cited={avg([int(r['cited']) for r in real])}  "
          f"refusal on no-answer={avg([int(r['refused']) for r in na])}  errors={sum(1 for r in R if r['error'])}  "
          f"median ttft={statistics.median([r['ttft_ms'] for r in R if r['ttft_ms']] or [0])}ms  "
          f"median total={statistics.median([r['total_ms'] for r in R])}ms")
os.makedirs("eval/results", exist_ok=True)
out = f"eval/results/{a.label}.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("saved", out)
