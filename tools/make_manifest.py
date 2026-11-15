"""
List the course files in data/raw/<Course>/<file> and warn about problems.
Usage: python tools/make_manifest.py
"""
import csv, pathlib, re
root = pathlib.Path("data/raw")
rows, warns = [], []
for p in sorted(root.rglob("*")):
    if not (p.is_file() and p.suffix.lower() in {".pdf", ".pptx", ".docx"}):
        continue
    parts = p.relative_to(root).parts
    if len(parts) < 2:
        warns.append(f"{p}: expected data/raw/<Course>/<file>")
        continue
    course = parts[0]
    pages, text_layer = "", ""
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            r = PdfReader(str(p)); pages = len(r.pages)
            sample = [r.pages[i].extract_text() or "" for i in range(0, pages, max(1, pages // 8))]
            empty = sum(1 for t in sample if len(t.strip()) < 90)
            text_layer = "mostly-images" if empty > len(sample) / 2 else "text"
        except Exception:
            pass
        if re.search(r"[ÃÂ�]", p.name):
          warns.append(f"{p.name}: broken accents in the file name. Rename it.")
    rows.append([course, p.name, p.suffix, p.stat().st_size, pages, text_layer])
with open("data/manifest.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["course", "file", "type", "bytes", "pages", "text_layer"]); w.writerows(rows)
print(len(rows), "files ->", "data/manifest.csv")
for w_ in warns:
    print("WARNING:", w_)
mi = [r for r in rows if r[5] == "mostly-images"]
if mi:
    print("These PDFs are mostly images (OCR needed):", ", ".join(r[1] for r in mi))