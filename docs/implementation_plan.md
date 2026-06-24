# Implementation Plan: Redrob Candidate Ranking System

**Project**: Intelligent Candidate Discovery & Ranking Challenge  
**Target Role**: Senior AI Engineer — Founding Team (Redrob AI)  
**Created**: 2026-06-18

---

## 1. Overview

Build a candidate ranking system that matches job seekers from the Redrob platform to a specific open role: **Senior AI Engineer at Redrob AI (Series A)**.

The system must:
- Ingest candidate profiles conforming to the schema in `docs/plan.md`
- Extract relevant signals from candidate data (experience, skills, location, engagement)
- Score and rank candidates for fit against the Senior AI Engineer JD
- Output top 100 candidates with explanatory reasoning

---

## 2. Candidate Profile Schema Analysis

From `docs/plan.md`, each candidate has:

### Core Profile
- `candidate_id` (CAND_XXXXXXX format)
- `profile`: Name, headline, summary, location, country, years of experience, title, company, industry
- `career_history[]`: Roles with dates, company size, descriptions (up to 10 entries)
- `education[]`: Institutions, degrees, field of study, tier ranking (up to 5 entries)
- `skills[]`: Skill name, proficiency level (beginner/intermediate/advanced/expert), endorsements count
- `redrob_signals`: Platform activity metrics

### Redrob Signals (Engagement)
- Profile completeness score
- Signup and last-active dates
- Open to work flag
- Profile views, applications, recruiter engagement
- Skill assessment scores
- Expected salary, work preferences, willingness to relocate
- GitHub activity score
- Interview and offer acceptance rates
- Verification status (email, phone, LinkedIn)

---

## 3. Target Role Profile: Senior AI Engineer

**From JD in `docs/plan.md`:**

**Required Competencies:**
- 5–9 years ML/AI engineering experience
- Deep technical depth: embeddings, retrieval, ranking, LLMs, fine-tuning
- Scrappy product-engineering mindset (balance between shipper and researcher)
- Ownership of ranking, retrieval, and matching systems
- Comfortable with early-stage ambiguity and rapid iteration

**Location & Logistics:**
- Pune/Noida, India (Hybrid — flexible cadence)
- Open to relocation from Tier-1 Indian cities

**Implicit Requirements:**
- AI/ML background (Computer Science or equivalent)
- Experience with AI systems design (not just research)
- Evidence of shipping products or features

---

## 4. Scoring Strategy

Rank candidates using a multi-factor scoring approach:

### 4.1. Experience Fit (40% weight)
- Years of experience: target 5–9 years (peak score at 7)
- Career history contains AI/ML roles
- Progression from IC to senior/leadership signals
- Relevance of past roles to ranking/retrieval/LLM work

### 4.2. Technical Skills (30% weight)
- Presence of key skills: `machine-learning`, `deep-learning`, `NLP`, `LLMs`, `embeddings`, `retrieval`, `ranking`, `Python`, `PyTorch`/`TensorFlow`
- Skill proficiency levels (expert > advanced > intermediate)
- Total endorsements as confidence signal
- GitHub activity score (evidence of hands-on coding)

### 4.3. Product Mindset (15% weight)
- Company size trajectory: startup → larger companies → back to startup (suggests exposure to scaling)
- Current company size (Series A startups preferred)
- Interview completion rate (commitment to process)
- Offer acceptance rate (follows through)

### 4.4. Engagement & Availability (15% weight)
- Open to work flag
- Profile completeness score (high = serious candidate)
- Willingness to relocate or already in target location (India)
- Expected salary reasonable for the market
- Recruiter response rate (engaged on platform)
- Last active date (recent activity)

---

## 5. Ranking Algorithm

1. **Load candidates** from `data/candidates.jsonl` (or `candidates.jsonl.gz`)
2. **For each candidate**:
   - Extract experience years, skills, company history, education, signals
   - Compute sub-scores for each factor (experience, skills, mindset, engagement)
   - Normalize each to [0, 1]
   - Weighted sum: `score = 0.40*exp + 0.30*skills + 0.15*mindset + 0.15*engagement`
3. **Sort** by score descending
4. **Select** top 100 and write CSV with fields: `candidate_id`, `rank`, `score`, `reasoning`

---

## 6. Implementation Tasks

### Task 1: Implement Multi-Factor Scoring
**Objective**: Build scoring functions for experience, skills, product mindset, and engagement  
**Details**:
- Create function to extract and score experience years (target 5–9 years optimal)
- Create function to score skills against target keywords (embeddings, LLMs, ranking, Python, PyTorch/TensorFlow)
- Create function to evaluate product mindset (company trajectory, startup experience, offer/interview rates)
- Create function to score engagement signals (open_to_work, profile_completeness, location fit, response_rate)
- Combine all factors into weighted scoring: 40% experience + 30% skills + 15% mindset + 15% engagement

### Task 2: Extract Candidate Fields from Schema
**Objective**: Parse candidate JSON/JSONL records to extract all relevant scoring signals  
**Details**:
- Extract years_of_experience from profile object
- Extract skill names, proficiency levels, and endorsement counts from skills array
- Extract company sizes and role progression from career_history array
- Extract education institution tier from education array
- Extract redrob_signals (open_to_work, profile_completeness, recruiter_response_rate, github_activity_score, location, etc.)

### Task 3: Implement Candidate Ranking
**Objective**: Score and rank all candidates, produce top 100 ranked list  
**Details**:
- Load candidates from data source (JSONL/JSON/GZ)
- Apply multi-factor scoring to each candidate
- Sort by score descending
- Return top 100 with candidate_id, rank, score, and reasoning

### Task 4: Generate Submission CSV
**Objective**: Produce submission output in required format  
**Details**:
- Output columns: `candidate_id`, `rank`, `score`, `reasoning`
- Ranks must be sequential integers 1–100
- Scores must be numeric in [0.0, 1.0] range
- Reasoning must be non-empty descriptive text

### Task 5: Validate Submission Format
**Objective**: Ensure output meets all requirements  
**Details**:
- Validate candidate IDs match CAND_XXXXXXX format
- Verify ranks are unique and sequential
- Verify scores are within [0.0, 1.0] bounds
- Ensure reasoning is present for all rows
- Check for no duplicate candidate IDs in output

---

## 8. Execution Checklist

- [ ] Review candidate schema in `docs/plan.md`
- [ ] Analyze Senior AI Engineer JD in `docs/plan.md`
- [ ] Identify and confirm scoring weights (experience, skills, mindset, engagement)
- [ ] Implement multi-factor scoring logic
- [ ] Implement candidate field extraction from schema
- [ ] Implement candidate ranking and top 100 selection
- [ ] Generate submission CSV output
- [ ] Validate output format (IDs, ranks, scores, reasoning)
- [ ] Verify submission passes all validation rules

---

## 9. Scoring Weights Summary

| Factor | Weight | Sub-Factors |
|--------|--------|-------------|
| Experience | 40% | Years (5-9 optimal), ML roles, seniority progression |
| Technical Skills | 30% | Keywords (embeddings, LLMs, ranking, etc.), proficiency, endorsements, GitHub |
| Product Mindset | 15% | Company size trajectory, startup experience, current stage, offer/interview rates |
| Engagement | 15% | Open to work, profile completeness, location fit, salary reasonableness, response rate |

---

## 10. Success Criteria

- ✅ Submission CSV output has exactly 100 candidates with valid candidate IDs in CAND_XXXXXXX format
- ✅ Ranks are sequential integers 1–100 with no duplicates
- ✅ Scores are numeric values in [0.0, 1.0] range
- ✅ Reasoning text is non-empty and informative for each row
- ✅ Top candidates ranked are AI/ML engineers with 5–9 years experience and relevant skills
- ✅ Scoring is deterministic and reproducible on CPU-only environment
- ✅ No external API calls or network access required

---

## 11. Next Steps

1. **Design Phase**:
   - Review and finalize scoring weights based on JD requirements
   - Decide on primary scoring factors and their contribution percentages

2. **Implementation Phase**:
   - Build multi-factor scoring logic
   - Implement candidate field extraction
   - Generate and validate submission

---

## References

- Candidate Schema: [docs/plan.md](docs/plan.md)
- Job Description: [docs/plan.md](docs/plan.md)
