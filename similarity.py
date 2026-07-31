"""
similarity.py
---------------
Scoring logic for the AI Career Accelerator.

- compute_ats_score: heuristic 0-100 score based on resume structure/content
  quality (sections present, contact info, length, skills found), independent
  of any job description.
- score_breakdown: the same heuristic broken into named categories, used to
  render the ATS radar/bar chart in the UI.
- compute_match_score: TF-IDF + cosine similarity between the resume text and
  a job description, expressed as a 0-100 percentage.
- find_missing_skills: skills that appear in the job description but not the
  resume (also used by the roadmap + interview modules).
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from resume_parser import extract_skills


# ---------------------------------------------------------------------------
# ATS Score (resume quality, no JD required)
# ---------------------------------------------------------------------------

def _structure_score(parsed_resume):
    sections = parsed_resume["sections"]
    weight = 40 / max(len(sections), 1)
    return sum(weight for present in sections.values() if present)


def _contact_score(parsed_resume):
    contact = parsed_resume["contact_info"]
    score = 0
    if contact.get("email"):
        score += 10
    if contact.get("phone"):
        score += 5
    if contact.get("linkedin") or contact.get("github"):
        score += 5
    return score


def _skills_score(parsed_resume):
    skill_count = len(parsed_resume["skills"])
    return min(skill_count, 12) / 12 * 25


def _length_score(parsed_resume):
    word_count = parsed_resume["word_count"]
    if word_count >= 800:
        return 15
    if word_count >= 400:
        return 12
    if word_count >= 200:
        return 8
    if word_count >= 80:
        return 4
    return 0


def compute_ats_score(parsed_resume):
    """parsed_resume is the dict returned by resume_parser.parse_resume()."""
    score = (
        _structure_score(parsed_resume)
        + _contact_score(parsed_resume)
        + _skills_score(parsed_resume)
        + _length_score(parsed_resume)
    )
    return round(min(score, 100))


def score_breakdown(parsed_resume):
    """Category breakdown (each 0-100) for the ATS score radar/bars in the UI."""
    return {
        "structure": round(min(_structure_score(parsed_resume) / 40 * 100, 100)),
        "contact_info": round(min(_contact_score(parsed_resume) / 20 * 100, 100)),
        "skills_coverage": round(min(_skills_score(parsed_resume) / 25 * 100, 100)),
        "content_depth": round(min(_length_score(parsed_resume) / 15 * 100, 100)),
    }


# ---------------------------------------------------------------------------
# Resume <-> Job Description match score
# ---------------------------------------------------------------------------

def _clean(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s+#./-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_match_score(resume_text, jd_text):
    """Cosine similarity between resume and job description via TF-IDF,
    returned as a percentage 0-100."""
    resume_clean = _clean(resume_text)
    jd_clean = _clean(jd_text)

    if not resume_clean or not jd_clean:
        return 0

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform([resume_clean, jd_clean])
    except ValueError:
        # Happens if vocabulary is empty after stop-word removal
        return 0

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(float(similarity) * 100, 1)


# ---------------------------------------------------------------------------
# Missing skills
# ---------------------------------------------------------------------------

def find_missing_skills(resume_text, jd_text, skills_list):
    resume_skills = set(extract_skills(resume_text, skills_list))
    jd_skills = set(extract_skills(jd_text, skills_list))

    missing = sorted(jd_skills - resume_skills)
    matched = sorted(jd_skills & resume_skills)

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "jd_skills": sorted(jd_skills),
    }
