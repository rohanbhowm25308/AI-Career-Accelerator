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
    weight = 35 / max(len(sections), 1)
    return sum(weight for present in sections.values() if present)


def _contact_score(parsed_resume):
    contact = parsed_resume["contact_info"]
    score = 0
    if contact.get("email"):
        score += 7
    if contact.get("phone"):
        score += 4
    if contact.get("linkedin") or contact.get("github"):
        score += 4
    return score


def _skills_score(parsed_resume):
    skill_count = len(parsed_resume["skills"])
    return min(skill_count, 12) / 12 * 20


_BULLET_LINE_RE = re.compile(
    r"^[\u2022\u25CF\u25AA\u25CB\u25E6\u2023\u2043*•\-\uf000-\uf0ff]\s*"
)
# \uf000-\uf0ff is the Private Use Area range PDF extractors commonly map
# Wingdings/Symbol bullet glyphs into (e.g. U+F0D8, the arrow bullet this
# resume's template uses). The old regex only recognized one specific PUA
# codepoint (\uf0b7), so any other glyph in that range was invisible to the
# bullet check below and fell through to the much weaker sentence-shaped
# fallback heuristic - which, for a *run* of consecutive glyph-prefixed
# bullets, merges the first missed one into whatever line came right
# before it (often the job-title header) and then silently drops the rest,
# undercounting real bullets and tanking the quantified-impact score even
# when the bullets do contain metrics.
# A number only counts as a quantified metric if it's not glued to letters on
# either side - this excludes digits embedded in proper nouns/names like
# "Tech4Hack" or "Web3" while still matching real metrics like "20%",
# "1,000+", "4-member", "35%".
_METRIC_RE = re.compile(r"(?<![a-zA-Z])\d[\d,.]*\+?%?(?![a-zA-Z])")
_DATE_RANGE_HINT_RE = re.compile(
    r"(19|20)\d{2}\s*[-–—to]+\s*((19|20)\d{2}|present|current)"
    r"|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(19|20)\d{2}",
    re.IGNORECASE,
)
_ALL_CAPS_HEADER_RE = re.compile(r"^[A-Z0-9 &/,()]{4,}$")


def _looks_like_header_line(line):
    """Job titles, company/date lines, and section headers aren't
    achievement bullets even though they're capitalized sentence-shaped
    text - filter them out so the fallback heuristic below doesn't treat
    them as bullets."""
    if _DATE_RANGE_HINT_RE.search(line):
        return True
    if _ALL_CAPS_HEADER_RE.match(line.strip()):
        return True
    if line.count(",") >= 6 and not line.rstrip().endswith((".", "!", "?")):
        return True  # long comma-separated skill/tool list, not a sentence
    if line.count("|") >= 1 and not line.rstrip().endswith((".", "!", "?")):
        return True  # "Role | Company | Program"-style header, not a bullet
    return False


from resume_parser import SECTION_KEYWORDS

_ACHIEVEMENT_SECTIONS = {"experience", "projects", "certifications"}


_URL_ONLY_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _extract_bullet_lines(raw_text):
    """Pulls out lines that look like resume bullet points, scoped to the
    Experience/Projects/Certifications sections only (so education records,
    summary text, and skill lists can't be miscounted as "achievements").
    Prefers literal bullet-glyph-prefixed lines (handles the different
    glyphs various PDF exporters use). Many modern resume templates skip
    bullet glyphs entirely and rely on indentation alone, so this also
    falls back to sentence-shaped content lines within those sections.
    PDF text extraction often wraps one bullet across multiple raw lines -
    continuation lines (typically starting lowercase, mid-sentence) are
    merged back into the bullet they belong to, rather than dropped or
    scored as a separate fragment."""
    bullets = []
    pending = None  # bullet currently being assembled across wrapped lines
    current_section = None

    def flush():
        nonlocal pending
        if pending:
            bullets.append(pending.strip())
        pending = None

    for line in (raw_text or "").split("\n"):
        stripped = line.strip()
        if not stripped or _URL_ONLY_RE.match(stripped):
            continue

        lowered = stripped.lower()
        if len(stripped) <= 40:
            matched_section = next(
                (section for section, keywords in SECTION_KEYWORDS.items() if any(kw in lowered for kw in keywords)),
                None,
            )
            if matched_section:
                flush()
                current_section = matched_section
                continue

        if current_section not in _ACHIEVEMENT_SECTIONS:
            continue

        if _BULLET_LINE_RE.match(stripped):
            flush()
            content = _BULLET_LINE_RE.sub("", stripped).strip()
            if content:
                pending = content
            continue

        is_header = _looks_like_header_line(stripped)

        # A continuation line: no bullet glyph, starts lowercase (mid-
        # sentence) or the prior line didn't end with terminal punctuation,
        # and isn't itself a header - append it to the bullet in progress.
        if pending and not is_header and (stripped[:1].islower() or not pending.rstrip().endswith((".", "!", "?"))):
            pending += " " + stripped
            continue

        flush()
        if 30 <= len(stripped) <= 260 and stripped[:1].isupper() and stripped.count(" ") >= 4 and not is_header:
            pending = stripped

    flush()
    return bullets


def _quantification_score(parsed_resume):
    """Rewards resumes whose achievement bullets include a measurable
    outcome (a number, %, or scale) instead of only listing duties -
    this is one of the most consistently-cited resume-quality signals
    (recruiters and ATS-style checkers alike weigh it heavily)."""
    bullets = _extract_bullet_lines(parsed_resume["raw_text"])
    if not bullets:
        return 9.0  # no bullet-style content to judge - neutral, not punitive

    quantified = sum(1 for b in bullets if _METRIC_RE.search(b))
    ratio = quantified / len(bullets)
    return round(ratio * 18, 1)


def _length_score(parsed_resume):
    word_count = parsed_resume["word_count"]
    # Career-guidance consensus targets roughly 400-600 words for a
    # focused, well-written single-page resume (800+ implies a two-pager).
    # Scaling smoothly toward that target - instead of hard step
    # thresholds - also avoids arbitrary cliffs where one extra word could
    # jump the score a full bracket for no real reason.
    target_words = 450
    return round(min(word_count / target_words, 1.0) * 12, 1)


def _parse_cleanliness_penalty(parsed_resume):
    """Detects duplicate/repeated lines in the extracted text - a real
    artifact of icon-heavy hyperlinked headers (LinkedIn/GitHub/portfolio
    icons) that confuse linear PDF text extraction, the same signal
    commercial ATS checkers report separately as a 'parse rate' below
    100%. This only penalizes resumes with genuine extraction friction -
    a clean single-column resume gets zero penalty."""
    raw_text = parsed_resume.get("raw_text", "")
    lines = [l.strip() for l in raw_text.split("\n") if l.strip() and len(l.strip()) > 3]
    if not lines:
        return 0.0

    counts = {}
    for line in lines:
        counts[line] = counts.get(line, 0) + 1
    duplicate_occurrences = sum(c - 1 for c in counts.values() if c > 1)
    ratio = duplicate_occurrences / len(lines)

    # Scaled and capped so this stays a meaningful-but-bounded signal,
    # not something that can tank an otherwise-strong resume.
    return round(min(ratio * 40, 15), 1)


def compute_ats_score(parsed_resume):
    """parsed_resume is the dict returned by resume_parser.parse_resume()."""
    score = (
        _structure_score(parsed_resume)
        + _contact_score(parsed_resume)
        + _skills_score(parsed_resume)
        + _length_score(parsed_resume)
        + _quantification_score(parsed_resume)
        - _parse_cleanliness_penalty(parsed_resume)
    )
    return round(max(0, min(score, 100)))


def score_breakdown(parsed_resume):
    """Category breakdown (each 0-100) for the ATS score radar/bars in the UI."""
    penalty = _parse_cleanliness_penalty(parsed_resume)
    return {
        "structure": round(min(_structure_score(parsed_resume) / 35 * 100, 100)),
        "contact_info": round(min(_contact_score(parsed_resume) / 15 * 100, 100)),
        "skills_coverage": round(min(_skills_score(parsed_resume) / 20 * 100, 100)),
        "content_depth": round(min(_length_score(parsed_resume) / 12 * 100, 100)),
        "quantified_impact": round(min(_quantification_score(parsed_resume) / 18 * 100, 100)),
        "parse_cleanliness": round(max(0, 100 - (penalty / 15 * 100))),
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