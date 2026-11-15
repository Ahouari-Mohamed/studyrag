"""
Retrieval quality: Hit@1/3/5 and MRR over eval/questions.json.
Usage:  python eval/eval_retrieval.py --label baseline
        python eval/eval_retrieval.py --questions eval/questions_sample.json --label sample
"""
import argparse, csv, json, os, statistics, time
import httpx
from common import is_match

ap = argparse.ArgumentParser()
ap.add_argument("--questions", default="eval/questions.json")
ap.add_argument("--base", default="http://localhost:8003")
ap.add_argument("--top-k", type=int, default=5)
ap.add_argument("--tol", type=int, default=1, help="page tolerance")
ap.add_argument("--label", default="run", help="name of the configuration (chunk size, model...)")
ap.add_argument("--no-course-filter", action="store_true")
a = ap.parse_args()

qs = json.load(open(a.questions, encoding="utf-8"))
rows, noans = [], []
for q in qs:
    body = {"query": q["question"], "top_k": a.top_k,
            "course": None if a.no_course_filter else q.get("course")}
    t0 = time.perf_counter()
    try:
        res = httpx.post(f"{a.base}/search", json=body, timeout=60).json()["results"]
    except Exception as e:
        print(f"q{q['id']}: request failed ({e})")
        res = []
    ms = (time.perf_counter() - t0) * 1000
    if q["source_type"] == "no_answer":
        noans.append((q["id"], res[0]["score"] if res else None))
        continue
    rank = next((i + 1 for i, c in enumerate(res) if is_match(c["file"], c.get("page"), q, a.tol)), None)
    rows.append({"id": q["id"], "type": q["source_type"], "lang": q["lang"], "difficulty": q["difficulty"],
                 "rank": rank, "latency_ms": round(ms), "top_file": res[0]["file"] if res else "",
                 "top_page": res[0].get("page") if res else "", "top_score": round(res[0]["score"], 3) if res else ""})
    print(f"q{q['id']:>2} [{q['source_type']:<4}] rank={rank}  top={rows[-1]['top_file']} p{rows[-1]['top_page']}")

def stats(rs):
    n = len(rs)
    if not n:
        return "n=0"
    h = lambda k: sum(1 for r in rs if r["rank"] and r["rank"] <= k) / n
    mrr = sum(1 / r["rank"] for r in rs if r["rank"]) / n
    return f"n={n}  Hit@1={h(1):.2f}  Hit@3={h(3):.2f}  Hit@5={h(5):.2f}  MRR={mrr:.2f}"

print("\n=== SUMMARY:", a.label)
print("all     :", stats(rows))
for key in ("type", "lang", "difficulty"):
    for v in sorted({r[key] for r in rows}):
        print(f"{key}={v:<7}:", stats([r for r in rows if r[key] == v]))
lat = [r["latency_ms"] for r in rows]
if lat:
    print(f"latency : median={statistics.median(lat):.0f} ms  max={max(lat)} ms")
for qid, sc in noans:
    print(f"no-answer q{qid}: top score = {sc}  (compare with scores of real hits)")

os.makedirs("eval/results", exist_ok=True)
out = f"eval/results/retrieval_{a.label}.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
    w.writeheader(); w.writerows(rows)
print("saved", out)
