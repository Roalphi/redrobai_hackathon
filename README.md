# Redrob Candidate Ranker

This repository contains a deterministic, CPU-only ranker for the Redrob Intelligent Candidate Discovery & Ranking Challenge.

## Reproduce

```powershell
python rank.py --candidates data/candidates.jsonl --out submission.csv
```

The ranker uses only the Python standard library and makes no network calls. It also accepts gzipped input:

```powershell
python rank.py --candidates candidates.jsonl.gz --out submission.csv
```

## Sandbox

Run the Streamlit demo locally:

```powershell
streamlit run app.py
```

The app has three input modes:
- bundled sample for quick checks
- local path for large files such as `data/candidates.jsonl.gz`
- browser upload for smaller samples

For a 500 MB-style dataset, use the local path mode so the file is read from disk instead of pushed through the browser upload widget.

## Method

The scoring model is a transparent rule-based ranker for the Senior AI Engineer JD. It emphasizes production evidence in titles and career history for retrieval, ranking, search, recommendations, embeddings, vector search, and evaluation systems. Skills are treated as supporting evidence, weighted by proficiency, endorsements, duration, and Redrob assessment scores.

The final score combines career fit, target skills, 5-9 year experience fit, product-company exposure, education, behavioral availability, location, and salary reasonableness. It applies penalties for keyword-stuffing patterns, inconsistent years of experience, expert skills with zero duration, non-technical titles with many AI keywords, and low availability signals.

The output is validated locally for the required `candidate_id,rank,score,reasoning` format, exactly 100 rows, unique sequential ranks, known candidate IDs, monotonic scores, and non-empty reasoning.
