import csv
import gzip
import io
import json
from time import perf_counter
from pathlib import Path

import streamlit as st

from tank import build_reason, rank_candidates


st.set_page_config(page_title="Redrob Ranker Sandbox", layout="wide")
st.title("Redrob Ranker Sandbox")
st.caption("Load the full candidate file first, then preview or export the top 25, 50, or 100 ranked results.")


def iter_jsonl_candidates(path):
    path = Path(path).expanduser()
    if str(path).lower().endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)
    else:
        with path.open("rt", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)


def read_uploaded_candidates(uploaded_file):
    if uploaded_file is None:
        return []

    name = (uploaded_file.name or "").lower()
    raw = uploaded_file.getvalue()

    if name.endswith(".gz"):
        text = gzip.decompress(raw).decode("utf-8")
    else:
        text = raw.decode("utf-8")

    stripped = text.lstrip()
    if not stripped:
        return []
    if stripped.startswith("["):
        return json.loads(text)

    candidates = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            candidates.append(json.loads(line))
    return candidates


def safe_get(candidate, *path, default="—"):
    """Defensive nested-field access so a malformed/partial uploaded record
    degrades to a placeholder instead of crashing the sandbox demo."""
    current = candidate
    try:
        for key in path:
            current = current[key]
        return current if current not in (None, "") else default
    except (KeyError, TypeError):
        return default


with st.sidebar:
    st.header("Input")
    input_mode = st.radio("Source", ["Bundled sample", "Local path", "Upload file"], index=0)
    limit = st.slider("Top results to show/export", min_value=1, max_value=100, value=25)
    uploaded_file = None
    local_path = ""

    if input_mode == "Local path":
        local_path = st.text_input("Path to JSONL / JSON / GZ", value="data/candidates.jsonl.gz")
    elif input_mode == "Upload file":
        uploaded_file = st.file_uploader(
            "Upload candidates JSON, JSONL, or GZ",
            type=["json", "jsonl", "gz"],
            max_upload_size=600,
        )


if input_mode == "Bundled sample":
    load_started = perf_counter()
    sample_path = Path("data/sample_candidates.json")
    candidates = json.loads(sample_path.read_text(encoding="utf-8"))
    source_label = "bundled sample_candidates.json"
    load_seconds = perf_counter() - load_started
elif input_mode == "Local path":
    try:
        load_started = perf_counter()
        path = Path(local_path).expanduser()
        if not path.exists():
            candidates = []
            source_label = f"missing path: {path}"
        elif str(path).lower().endswith((".jsonl", ".gz")):
            candidates = list(iter_jsonl_candidates(path))
            source_label = str(path)
        else:
            candidates = json.loads(path.read_text(encoding="utf-8"))
            source_label = str(path)
        load_seconds = perf_counter() - load_started
    except Exception as exc:
        candidates = []
        source_label = f"error reading path: {exc}"
        load_seconds = 0.0
else:
    try:
        load_started = perf_counter()
        candidates = read_uploaded_candidates(uploaded_file) if uploaded_file else []
        source_label = uploaded_file.name if uploaded_file else "no file"
        load_seconds = perf_counter() - load_started
    except Exception as exc:
        candidates = []
        source_label = f"error reading upload: {exc}"
        load_seconds = 0.0

st.write(f"Source: `{source_label}`")
st.write(f"Loaded: **{len(candidates)}** candidates")

if candidates:
    try:
        rank_started = perf_counter()
        ranked = rank_candidates(candidates)
        rank_seconds = perf_counter() - rank_started
    except Exception as exc:
        st.error(f"Ranking failed on this input: {exc}")
        st.stop()

    total_seconds = load_seconds + rank_seconds
    preview_rows = ranked[:limit]
    st.subheader(f"Top {limit} Results")
    timing_col_1, timing_col_2, timing_col_3 = st.columns(3)
    timing_col_1.metric("Load time", f"{load_seconds:.2f}s")
    timing_col_2.metric("Ranking time", f"{rank_seconds:.2f}s")
    timing_col_3.metric("Total time", f"{total_seconds:.2f}s")

    disqualified_count = sum(
        1 for _, _, _, features in preview_rows if features.get("disqualifiers")
    )
    if disqualified_count:
        st.warning(f"{disqualified_count} of the previewed rows tripped a hard disqualifier and were score-capped.")

    st.dataframe(
        [
            {
                "rank": rank,
                "candidate_id": candidate_id,
                "score": f"{score:.6f}",
                "title": safe_get(candidate, "profile", "current_title"),
                "location": safe_get(candidate, "profile", "location"),
                "disqualified": bool(features.get("disqualifiers")),
            }
            for rank, (score, candidate_id, candidate, features) in enumerate(preview_rows, start=1)
        ],
        use_container_width=True,
        hide_index=True,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["candidate_id", "rank", "score", "reasoning"])
    export_started = perf_counter()
    for rank, (score, candidate_id, candidate, features) in enumerate(preview_rows, start=1):
        writer.writerow([candidate_id, rank, f"{score:.6f}", build_reason(candidate, score, features)])
    export_seconds = perf_counter() - export_started
    st.caption(f"CSV export generation time: {export_seconds:.2f}s")

    st.download_button(
        "Download ranked CSV",
        data=output.getvalue().encode("utf-8"),
        file_name="submission_preview.csv",
        mime="text/csv",
    )

    st.subheader("Candidate Preview")
    st.json(candidates[0])
else:
    st.info("Upload a file or keep the bundled sample selected to see rankings.")
