# Evaluation pack

## Layout (unzip at the root of the repository)
    eval/    questions.json  questions_sample.json  common.py  eval_retrieval.py  eval_answers.py  results/
    tools/   make_manifest.py
    data/    sample/sample1.pdf  sample/sample2.pdf      (data/raw/ is NOT committed)

## 1. Course files (data/raw/<Course>/<file>)
Use these course names: `Machine_Learning` (semester S6) and `Java_POO`.
Rename files to ASCII before indexing. `expected_file` in questions.json uses these names:

    1_Introduction_au_ML.pdf                  5_K_plus_proche_voisin.pdf
    2_Regression_Lineaire.pdf                 6_Decision_Tree.pdf
    3_Regression_Multiple_et_Polynomiale.pdf  7_K_means.pdf
    4_Regression_Logistique.pdf               Introduction_a_Java_et_a_la_POO.pdf
                                              cours_Java_et_POO.pdf

Matching ignores case, accents, spaces, underscores and extension, so "2 - Regression Linéaire.pdf" also matches.
Page numbers = position in the PDF file (what the parser stores), NOT the number printed on the slide.
They drift in cours_Java_et_POO.pdf (printed 72 = PDF page 71).

## 2. Questions
- questions.json: 25 questions with known answers (17 Machine Learning, 8 Java) + 2 "no answer" questions
  (the answer is not in the documents: the system must say so).
- source_type = `ocr` means the answer is inside an image, so it tests the OCR path (5 questions).
- `alt_pages` = other pages accepted as correct. `note` = known pitfalls.
- questions_sample.json: 12 questions for data/sample (course `Demo`), for Member 2's tests.

## 3. Run (system up, data indexed)
    python eval/eval_retrieval.py --label baseline
    python eval/eval_retrieval.py --questions eval/questions_sample.json --label sample
    set STUDYRAG_KEY_GROQ=...            (Windows)   export STUDYRAG_KEY_GROQ=...   (Linux/Mac)
    python eval/eval_answers.py --providers ollama,groq --label answers
Requirements: `pip install httpx`. Change one thing per run (chunk size, OCR on/off, top-k) and
use a different --label each time; compare the CSV files in eval/results/.

## 4. Known pitfalls to discuss in the report
- Image-only PDFs: 6_Decision_Tree.pdf has no text layer (51 of 53 pages), and several pages of other files
  contain tables/code as images. Without OCR these questions cannot be answered.
- OCR can lose decimal points (question 13: the slide says 1.4, OCR may read 14).
- Footer text ("Centre d'Excellence IT - FSA ... 12 / 43") appears on every slide: filter it or it pollutes chunks.
