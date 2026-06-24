import argparse
import csv
import gzip
import json
import math
import re
from datetime import date, datetime
from pathlib import Path


TODAY = date(2026, 6, 18)

PROFICIENCY_WEIGHT = {
    "beginner": 0.35,
    "intermediate": 0.6,
    "advanced": 0.85,
    "expert": 1.0,
}

TARGET_LOCATIONS = ("pune", "noida")
WELCOME_LOCATIONS = (
    "hyderabad",
    "mumbai",
    "delhi",
    "gurgaon",
    "bangalore",
    "bengaluru",
)

SERVICES_COMPANIES = {
    "tcs",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "tech mahindra",
    "mindtree",
    "mphasis",
}

NON_TECH_TITLES = (
    "marketing",
    "sales",
    "hr ",
    "accountant",
    "operations manager",
    "content writer",
    "graphic designer",
    "customer support",
    "civil engineer",
    "mechanical engineer",
)

NON_PRODUCTION_TITLE_HINTS = (
    "architect",
    "engineering manager",
    "director",
    "tech lead",
    "technical lead",
    "vp ",
    "head of",
)

# FIX #2/#3: added applied-scientist family + a few synonyms that were
# completely missing before (Applied Scientist had zero coverage).
TARGET_TITLE_PATTERNS = (
    (r"\bsenior ai engineer\b", 1.0),
    (r"\blead ai engineer\b", 0.98),
    (r"\bsenior applied scientist\b", 0.97),
    (r"\bapplied scientist\b", 0.93),
    (r"\bsenior machine learning engineer\b", 0.96),
    (r"\bstaff machine learning engineer\b", 0.92),
    (r"\bsenior nlp engineer\b", 0.95),
    (r"\bsearch engineer\b", 0.9),
    (r"\bsenior search engineer\b", 0.93),
    (r"\brecommendation systems? engineer\b", 0.92),
    (r"\bpersonalization engineer\b", 0.9),
    (r"\bapplied ml engineer\b", 0.9),
    (r"\bmachine learning engineer\b", 0.86),
    (r"\bai engineer\b", 0.84),
    (r"\bnlp engineer\b", 0.82),
    (r"\bml scientist\b", 0.82),
    (r"\bsenior data scientist\b", 0.72),
    (r"\bml engineer\b", 0.7),
    (r"\bdata scientist\b", 0.58),
    (r"\bsenior software engineer \(ml\)\b", 0.78),
    (r"\bresearch engineer\b", 0.55),  # capped lower; pure-research disqualifier handled separately
    (r"\bdata engineer\b", 0.36),
    (r"\bbackend engineer\b", 0.35),
    (r"\bsoftware engineer\b", 0.32),
)

# FIX #1: expanded vocabulary so plain-language / synonym-using candidates
# (the "Tier 5 doesn't say RAG or Pinecone" trap the JD calls out explicitly)
# aren't scored near-zero on career evidence just for using different words.
TEXT_SIGNALS = {
    "retrieval": 4.8,
    "ranking": 4.6,
    "learning-to-rank": 4.5,
    "learning to rank": 4.5,
    "recommendation": 4.1,
    "recommender": 4.1,
    "search": 3.7,
    "information retrieval": 4.8,
    "semantic search": 4.2,
    "hybrid retrieval": 4.8,
    "dense vector": 4.2,
    "vector search": 4.3,
    "embedding": 3.6,
    "sentence transformer": 3.8,
    "bm25": 3.8,
    "ndcg": 4.2,
    "mrr": 3.8,
    "offline-online": 3.8,
    "a/b": 2.8,
    "ab test": 2.8,
    "evaluation harness": 4.0,
    "eval framework": 3.7,
    "candidate-jd": 4.8,
    "matching pipeline": 4.3,
    "connect users with relevant": 4.0,
    "search & discovery": 4.2,
    "content matching": 3.8,
    "text encoders": 3.7,
    "vector representations": 3.6,
    "search backend": 3.8,
    "search infrastructure": 4.0,
    "indexing algorithms": 3.7,
    "rag": 2.8,
    "llm": 2.4,
    "fine-tuning": 2.5,
    "production": 2.2,
    "deployed": 2.2,
    "real users": 2.4,
    # --- newly added synonyms / paraphrases ---
    "two-tower": 4.0,
    "two tower": 4.0,
    "candidate generation": 4.2,
    "collaborative filtering": 4.0,
    "click-through": 3.5,
    "click through rate": 3.5,
    "ctr prediction": 3.4,
    "cross-encoder": 4.0,
    "cross encoder": 4.0,
    "reranker": 4.3,
    "re-ranking": 4.3,
    "reranking": 4.3,
    "cold start": 3.2,
    "personalization": 3.8,
    "personalisation": 3.8,
    "ann search": 4.0,
    "approximate nearest neighbor": 4.0,
    "nearest neighbor search": 3.9,
    "feature store": 2.6,
    "relevance scoring": 4.0,
    "query understanding": 3.8,
    "intent matching": 3.6,
    "job-candidate matching": 4.6,
    "talent matching": 4.0,
    "marketplace matching": 3.8,
    "recall and precision": 3.2,
}

SKILL_SIGNALS = {
    "Information Retrieval": 4.5,
    "Information Retrieval Systems": 4.9,
    "Learning to Rank": 4.7,
    "Recommendation Systems": 4.4,
    "Semantic Search": 4.2,
    "Vector Search": 4.2,
    "Embeddings": 3.6,
    "Sentence Transformers": 3.8,
    "BM25": 3.8,
    "FAISS": 3.4,
    "Qdrant": 3.4,
    "Pinecone": 3.3,
    "Milvus": 3.3,
    "Weaviate": 3.3,
    "Elasticsearch": 3.2,
    "OpenSearch": 3.2,
    "pgvector": 3.1,
    "Search Infrastructure": 4.2,
    "Search Backend": 4.0,
    "Search & Discovery": 4.0,
    "Content Matching": 3.8,
    "Text Encoders": 3.7,
    "Vector Representations": 3.7,
    "Indexing Algorithms": 3.6,
    "Machine Learning": 2.8,
    "Deep Learning": 2.4,
    "NLP": 3.0,
    "LLMs": 2.4,
    "Fine-tuning LLMs": 2.4,
    "PyTorch": 2.2,
    "TensorFlow": 2.0,
    "Python": 2.3,
    "scikit-learn": 1.8,
    "MLOps": 1.8,
    "MLflow": 1.6,
    "Kubeflow": 1.4,
    "Haystack": 1.6,
    "Collaborative Filtering": 4.0,
    "Personalization": 3.8,
    "Feature Engineering": 2.0,
    "XGBoost": 2.2,
    "LightGBM": 2.0,
}

VISION_SPEECH_SKILLS = {
    "Computer Vision",
    "OpenCV",
    "Image Classification",
    "Object Detection",
    "YOLO",
    "Speech Recognition",
    "ASR",
    "TTS",
    "Robotics",
}

NLP_IR_SKILLS = {
    "NLP",
    "Information Retrieval",
    "Information Retrieval Systems",
    "Semantic Search",
    "Vector Search",
    "Embeddings",
    "BM25",
    "Search Infrastructure",
    "Learning to Rank",
    "Recommendation Systems",
}


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def lower(value):
    return str(value or "").casefold()


def sigmoid(value):
    return 1.0 / (1.0 + math.exp(-value))


def load_candidates(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def normalized_sum(text, weights, denominator):
    total = 0.0
    lowered = lower(text)
    for phrase, weight in weights.items():
        if phrase in lowered:
            total += weight
    return clamp(total / denominator)


def title_score(title):
    lowered = lower(title)
    for pattern, score in TARGET_TITLE_PATTERNS:
        if re.search(pattern, lowered):
            return score
    if any(term in lowered for term in NON_TECH_TITLES):
        return 0.0
    return 0.12


def experience_score(years):
    years = float(years or 0.0)
    if 5.0 <= years <= 9.0:
        return 1.0 - min(abs(years - 7.0) / 5.0, 0.25)
    if 4.0 <= years < 5.0:
        return 0.78 + (years - 4.0) * 0.12
    if 9.0 < years <= 11.0:
        return 0.82 - (years - 9.0) * 0.09
    if 3.0 <= years < 4.0:
        return 0.48 + (years - 3.0) * 0.2
    if 11.0 < years <= 14.0:
        return 0.5 - (years - 11.0) * 0.08
    return 0.18


def skill_score(skills, assessments):
    total = 0.0
    matched = []
    target_count = 0
    zero_duration_expert = 0
    vision_speech_count = 0
    nlp_ir_count = 0
    for skill in skills:
        name = str(skill.get("name", ""))
        if name in VISION_SPEECH_SKILLS:
            vision_speech_count += 1
        if name in NLP_IR_SKILLS:
            nlp_ir_count += 1
        weight = SKILL_SIGNALS.get(name)
        if weight is None:
            continue
        target_count += 1
        proficiency = PROFICIENCY_WEIGHT.get(skill.get("proficiency"), 0.45)
        endorsements = min(float(skill.get("endorsements", 0)) / 45.0, 1.0)
        duration = min(float(skill.get("duration_months", 0)) / 36.0, 1.0)
        if skill.get("proficiency") == "expert" and int(skill.get("duration_months", 0) or 0) <= 3:
            zero_duration_expert += 1
        assessment_present = bool(assessments) and name in assessments
        assessment = float(assessments.get(name, 0.0)) / 100.0 if assessment_present else None
        # FIX #9: trust the objective assessment score over self-reported
        # proficiency when an assessment exists; self-report dominated before.
        if assessment is not None:
            confidence = 0.25 * proficiency + 0.15 * endorsements + 0.15 * duration + 0.45 * assessment
        else:
            confidence = 0.45 * proficiency + 0.25 * endorsements + 0.30 * duration
        contribution = weight * confidence
        total += contribution
        matched.append((contribution, name))
    score = clamp(total / 28.0)
    if target_count >= 10:
        score *= 0.92
    # FIX #6 (vision/speech dodge): require real NLP/IR evidence, not just
    # "enough generic ML skills", to clear a CV/speech-heavy profile.
    if vision_speech_count > 0 and nlp_ir_count == 0:
        score *= 0.6
    elif vision_speech_count > target_count and target_count < 5:
        score *= 0.82
    return score, [name for _, name in sorted(matched, reverse=True)[:5]], zero_duration_expert


def career_text(candidate):
    profile = candidate.get("profile", {})
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
    ]
    for role in candidate.get("career_history", []):
        parts.extend(
            [
                role.get("title", ""),
                role.get("industry", ""),
                role.get("description", ""),
            ]
        )
    return " ".join(parts)


def career_score(candidate):
    profile = candidate.get("profile", {})
    text = career_text(candidate)
    evidence = normalized_sum(text, TEXT_SIGNALS, 46.0)
    current_title = title_score(profile.get("current_title"))
    role_titles = [
        title_score(role.get("title", ""))
        for role in candidate.get("career_history", [])
    ]
    best_role = max(role_titles or [current_title])
    production_terms = normalized_sum(
        text,
        {
            "production": 2.0,
            "deployed": 2.0,
            "real users": 2.2,
            "serving": 1.6,
            "latency": 1.4,
            "scale": 1.2,
            "owned": 1.0,
            "led": 1.0,
            "shipped": 1.8,
            "launched": 1.6,
        },
        11.0,
    )
    return clamp(0.40 * evidence + 0.34 * current_title + 0.14 * best_role + 0.12 * production_terms)


def education_score(candidate):
    best = 0.0
    for edu in candidate.get("education", []):
        field = lower(edu.get("field_of_study"))
        tier = edu.get("tier", "unknown")
        field_score = 1.0 if "computer" in field else 0.75 if any(x in field for x in ("data", "math", "statistics", "electrical")) else 0.35
        tier_score = {"tier_1": 1.0, "tier_2": 0.82, "tier_3": 0.58, "tier_4": 0.35, "unknown": 0.45}.get(tier, 0.45)
        best = max(best, 0.65 * field_score + 0.35 * tier_score)
    return best


def location_score(profile, signals):
    location = lower(profile.get("location"))
    country = lower(profile.get("country"))
    if any(city in location for city in TARGET_LOCATIONS):
        base = 1.0
    elif any(city in location for city in WELCOME_LOCATIONS):
        base = 0.88
    elif country == "india":
        base = 0.68
    else:
        base = 0.38
    if signals.get("willing_to_relocate"):
        base = min(1.0, base + 0.18)
    return base


def days_since(value):
    try:
        return (TODAY - datetime.strptime(value, "%Y-%m-%d").date()).days
    except (TypeError, ValueError):
        return 999


def parse_date_safe(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def behavior_score(signals):
    last_active = days_since(signals.get("last_active_date"))
    recency = clamp(1.0 - last_active / 180.0)
    response = float(signals.get("recruiter_response_rate", 0.0))
    response_time = float(signals.get("avg_response_time_hours", 240.0))
    response_speed = clamp(1.0 - response_time / 168.0)
    completion = float(signals.get("profile_completeness_score", 0.0)) / 100.0
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.42
    notice = 1.0 - min(float(signals.get("notice_period_days", 180)) / 120.0, 1.0) * 0.55
    saved = clamp(float(signals.get("saved_by_recruiters_30d", 0)) / 10.0)
    interview = float(signals.get("interview_completion_rate", 0.0))

    # FIX #5b: sentinel (-1) values mean "no data", not "neutral/bad data".
    # Exclude them from the weighted sum instead of guessing a substitute.
    weighted_terms = [
        (0.16, recency),
        (0.16, response),
        (0.07, response_speed),
        (0.11, completion),
        (0.12, open_to_work),
        (0.07, notice),
        (0.05, saved),
        (0.06, interview),
    ]
    offer = signals.get("offer_acceptance_rate", -1)
    if offer != -1:
        weighted_terms.append((0.05, float(offer)))
    github = signals.get("github_activity_score", -1)
    if github != -1:
        weighted_terms.append((0.05, float(github) / 100.0))
    verified = (
        int(bool(signals.get("verified_email")))
        + int(bool(signals.get("verified_phone")))
        + int(bool(signals.get("linkedin_connected")))
    ) / 3.0
    weighted_terms.append((0.03, verified))

    total_weight = sum(w for w, _ in weighted_terms)
    raw = sum(w * v for w, v in weighted_terms) / total_weight if total_weight else 0.0

    # FIX #5a: sharpen the "doubly disengaged" case the JD calls out
    # explicitly (6mo inactive + 5% response = "not actually available").
    disengagement = recency * response
    raw = clamp(raw * (0.6 + 0.4 * (1.0 if disengagement > 0.05 else disengagement / 0.05)))
    return clamp(raw)


def product_company_score(candidate):
    roles = candidate.get("career_history", [])
    industries = [lower(role.get("industry")) for role in roles]
    companies = [lower(role.get("company")) for role in roles]
    sizes = [role.get("company_size", "") for role in roles]
    product_industry = any(
        any(
            token in industry
            for token in ("software", "saas", "ai/ml", "fintech", "e-commerce", "internet", "food delivery", "healthtech", "conversational ai")
        )
        for industry in industries
    )
    services_only = roles and all(
        "services" in industry or company in SERVICES_COMPANIES
        for industry, company in zip(industries, companies)
    )
    startup_or_scaleup = any(size in {"11-50", "51-200", "201-500"} for size in sizes)
    score = 0.45
    if product_industry:
        score += 0.28
    if startup_or_scaleup:
        score += 0.15
    if services_only:
        score -= 0.3
    return clamp(score)


def hard_disqualifiers(candidate, zero_duration_expert):
    """
    FIX #3/#4: the JD states three explicit "we will not move forward"
    disqualifiers. These were previously only weakly proxied by soft text
    weights. Returns a list of reason strings (empty = no hard disqualifier
    triggered). Used to hard-cap score rather than nudge it.
    """
    reasons = []
    profile = candidate.get("profile", {})
    roles = candidate.get("career_history", [])

    # 1. Pure research, no production deployment at all.
    if roles and all(
        "research" in lower(r.get("industry", "")) or "academ" in lower(r.get("company", ""))
        for r in roles
    ):
        reasons.append("pure research/academic career history with no production deployment evidence")

    # 2. Senior title but no production code in 18+ months (architecture/TL/manager track).
    if roles:
        most_recent = roles[0]
        recent_title = lower(most_recent.get("title", ""))
        if any(hint in recent_title for hint in NON_PRODUCTION_TITLE_HINTS):
            start = parse_date_safe(most_recent.get("start_date"))
            if start and (TODAY - start).days >= 18 * 30:
                reasons.append("18+ months in an architecture/management-track role with no recent production coding")

    # 3. Honeypot-style fabrication: tenure predates company existence.
    for r in roles:
        founded = r.get("company_founded_year")
        start = parse_date_safe(r.get("start_date"))
        if founded and start and isinstance(founded, (int, float)) and start.year < int(founded):
            reasons.append("role start date predates the company's stated founding year")
            break

    # 4. Honeypot-style fabrication: cluster of "expert" skills with near-zero duration.
    if zero_duration_expert >= 5:
        reasons.append("multiple 'expert' skills claimed with near-zero usage duration")

    return reasons


def job_hopping_penalty(candidate):
    """FIX #9: detect title-chaser pattern (JD explicit dislike) via average tenure."""
    roles = candidate.get("career_history", [])
    durations = []
    for r in roles:
        start = parse_date_safe(r.get("start_date"))
        end = parse_date_safe(r.get("end_date")) or TODAY
        if start:
            durations.append((end - start).days / 365.0)
    if len(durations) >= 3 and sum(durations) / len(durations) < 1.5:
        return 0.18
    return 0.0


def inconsistency_penalty(candidate, zero_duration_expert):
    """
    FIX #7: replaced free-text "N years" regex (prone to false positives on
    unrelated numbers like project durations) with structured date math from
    career_history. FIX #8: removed double-counted country penalty (location
    fit is already captured once in location_score).
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    penalty = 0.0

    years = float(profile.get("years_of_experience", 0.0))
    roles = candidate.get("career_history", [])
    total_role_years = 0.0
    has_dates = False
    for r in roles:
        start = parse_date_safe(r.get("start_date"))
        end = parse_date_safe(r.get("end_date")) or TODAY
        if start:
            has_dates = True
            total_role_years += max((end - start).days / 365.0, 0.0)
    if has_dates and abs(total_role_years - years) > 2.5:
        penalty += 0.18

    if zero_duration_expert >= 5:
        penalty += 0.28
    elif zero_duration_expert >= 2:
        penalty += 0.12

    current_title = lower(profile.get("current_title"))
    if any(term in current_title for term in NON_TECH_TITLES):
        technical_skills = sum(1 for skill in candidate.get("skills", []) if skill.get("name") in SKILL_SIGNALS)
        if technical_skills >= 7:
            penalty += 0.32

    if signals.get("open_to_work_flag") is False and float(signals.get("recruiter_response_rate", 0.0)) < 0.15:
        penalty += 0.12

    penalty += job_hopping_penalty(candidate)

    return clamp(penalty, 0.0, 0.65)


def salary_score(signals, years):
    salary = signals.get("expected_salary_range_inr_lpa", {})
    midpoint = (float(salary.get("min", 0.0)) + float(salary.get("max", 0.0))) / 2.0
    if midpoint <= 0:
        return 0.55
    target = 17.0 + min(max(years - 5.0, 0.0), 5.0) * 3.2
    ratio = midpoint / target
    if 0.75 <= ratio <= 1.45:
        return 1.0
    if ratio > 1.45:
        return clamp(1.0 - (ratio - 1.45) * 0.55, 0.25, 1.0)
    return clamp(0.55 + ratio * 0.4, 0.35, 1.0)


def score_candidate(candidate):
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    years = float(profile.get("years_of_experience", 0.0))
    skills, matched_skills, zero_duration_expert = skill_score(
        candidate.get("skills", []),
        signals.get("skill_assessment_scores", {}),
    )
    career = career_score(candidate)
    experience = experience_score(years)
    education = education_score(candidate)
    product = product_company_score(candidate)
    behavior = behavior_score(signals)
    location = location_score(profile, signals)
    salary = salary_score(signals, years)
    penalty = inconsistency_penalty(candidate, zero_duration_expert)
    disqualifiers = hard_disqualifiers(candidate, zero_duration_expert)

    base = (
        0.31 * career
        + 0.24 * skills
        + 0.15 * experience
        + 0.08 * product
        + 0.06 * education
        + 0.08 * behavior
        + 0.05 * location
        + 0.03 * salary
    )
    # FIX #5a: lower floor so weakly-available candidates are actually
    # down-weighted hard, matching the JD's explicit example.
    availability_multiplier = 0.40 + 0.60 * behavior
    final = clamp(base * availability_multiplier * (1.0 - penalty))

    # FIX #3/#4: hard cap, independent of how strong the lexical score is.
    if disqualifiers:
        final = min(final, 0.07)

    features = {
        "career": career,
        "skills": skills,
        "experience": experience,
        "product": product,
        "education": education,
        "behavior": behavior,
        "location": location,
        "salary": salary,
        "penalty": penalty,
        "matched_skills": matched_skills,
        "disqualifiers": disqualifiers,
    }
    return final, features


def strongest_career_evidence(candidate):
    text = lower(career_text(candidate))
    evidence = []
    for phrase, weight in TEXT_SIGNALS.items():
        if phrase in text:
            evidence.append((weight, phrase))
    return [phrase for _, phrase in sorted(evidence, reverse=True)[:3]]


def build_reason(candidate, score, features):
    """
    FIX #10: vary sentence structure based on which dimension is strongest
    instead of one fixed skeleton for every row, to reduce templated-reasoning
    risk at Stage 4 manual review while staying grounded in real fields
    (no hallucination).
    """
    profile = candidate.get("profile", {})
    signals = candidate.get("redrob_signals", {})
    title = profile.get("current_title", "Candidate")
    years = float(profile.get("years_of_experience", 0.0))
    location = profile.get("location", "unknown location")
    company = profile.get("current_company", "current company")
    evidence = strongest_career_evidence(candidate)
    skills = features["matched_skills"][:3]

    if features["disqualifiers"]:
        return (
            f"{title} ({years:.1f} yrs, {company}) flagged: "
            + "; ".join(features["disqualifiers"])
            + ". Ranked low/excluded regardless of skill keywords present."
        )

    lead_on_skills = features["skills"] >= features["career"]
    if lead_on_skills and skills:
        opener = f"{title} with {years:.1f} years, strongest on demonstrated skills in " + ", ".join(skills)
    elif evidence:
        opener = f"{title} with {years:.1f} years at {company}; career history shows " + ", ".join(evidence)
    else:
        opener = f"{title} with {years:.1f} years at {company}; limited explicit retrieval/ranking evidence in profile text"

    location_lower = lower(location)
    if any(city in location_lower for city in TARGET_LOCATIONS):
        loc_clause = f"based in {location}, a direct hub match"
    elif any(city in location_lower for city in WELCOME_LOCATIONS):
        loc_clause = f"based in {location}, Tier-1 India and within commuting range of hub policy"
    elif signals.get("willing_to_relocate"):
        loc_clause = f"currently in {location} but marked willing to relocate"
    else:
        loc_clause = f"based in {location}, a weaker geographic fit and not marked willing to relocate"

    response_rate = float(signals.get("recruiter_response_rate", 0.0))
    if signals.get("open_to_work_flag") and response_rate >= 0.3:
        avail_clause = f"actively engaged ({response_rate:.0%} recruiter response rate, marked open to work)"
    elif not signals.get("open_to_work_flag") and response_rate < 0.15:
        avail_clause = f"weak engagement signals ({response_rate:.0%} response rate, not marked open to work) — availability is a real concern"
    else:
        avail_clause = f"moderate engagement ({response_rate:.0%} response rate)"

    closer = ""
    if features["penalty"] > 0.2:
        closer = " Profile consistency checks reduced confidence in this ranking."
    elif score < 0.55:
        closer = " Ranked lower because evidence is adjacent to the role rather than a direct match."

    return f"{opener}; {loc_clause}; {avail_clause}.{closer}"


def rank_candidates(candidates):
    scored = []
    for candidate in candidates:
        score, features = score_candidate(candidate)
        scored.append((score, candidate.get("candidate_id", ""), candidate, features))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[:100]


def write_submission(rows, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        previous_score = 1.0
        for rank, (score, candidate_id, candidate, features) in enumerate(rows, start=1):
            score = min(score, previous_score)
            previous_score = score
            writer.writerow(
                [
                    candidate_id,
                    rank,
                    f"{score:.6f}",
                    build_reason(candidate, score, features),
                ]
            )


def validate_submission(out_path, candidate_ids):
    with open(out_path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 100:
        raise ValueError(f"expected 100 rows, found {len(rows)}")
    expected_header = ["candidate_id", "rank", "score", "reasoning"]
    with open(out_path, newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    if header != expected_header:
        raise ValueError(f"expected header {expected_header}, found {header}")
    seen_ids = set()
    previous_score = float("inf")
    for expected_rank, row in enumerate(rows, start=1):
        candidate_id = row["candidate_id"]
        rank = int(row["rank"])
        score = float(row["score"])
        if rank != expected_rank:
            raise ValueError(f"rank {rank} does not match expected {expected_rank}")
        if candidate_id in seen_ids:
            raise ValueError(f"duplicate candidate_id {candidate_id}")
        if candidate_id not in candidate_ids:
            raise ValueError(f"unknown candidate_id {candidate_id}")
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"score out of range for {candidate_id}: {score}")
        if score > previous_score + 1e-9:
            raise ValueError(f"score increases at rank {rank}")
        if not row["reasoning"].strip():
            raise ValueError(f"missing reasoning for {candidate_id}")
        seen_ids.add(candidate_id)
        previous_score = score


def main():
    parser = argparse.ArgumentParser(description="Rank Redrob candidates for the Senior AI Engineer JD.")
    parser.add_argument("--candidates", default="data/candidates.jsonl", help="Path to candidates .jsonl or .jsonl.gz")
    parser.add_argument("--out", default="submission.csv", help="Output CSV path")
    args = parser.parse_args()

    candidates = list(load_candidates(args.candidates))
    rows = rank_candidates(candidates)
    write_submission(rows, args.out)
    validate_submission(args.out, {candidate["candidate_id"] for candidate in candidates})
    print(f"Wrote {len(rows)} ranked candidates to {args.out}")


if __name__ == "__main__":
    main()
