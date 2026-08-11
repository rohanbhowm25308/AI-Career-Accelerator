"""
advanced_features.py
----------------------
The "Ascend AI Suite" - 15 additional AI-powered career modules layered on
top of the core Analyzer / Interview / Roadmap / Internships pipeline.

Every function here follows the same philosophy as the rest of the project:
  - Fully deterministic / offline by default (no API key needed, nothing
    ever silently fails because a network call didn't come back).
  - Where free-text generation genuinely benefits from a language model
    (HR summary, achievement rewriting, portfolio review, career twin
    narrative), an optional Claude call is attempted first and the module
    transparently falls back to the rule-based version on any failure.
  - Nothing here invents facts about the candidate (no fabricated years of
    experience, no fabricated metrics) - only reshapes / scores what the
    candidate actually provided.

Each public function takes plain Python data (skills lists, report dicts,
free text) so app.py's routes stay thin.
"""

import os
import re
import math
import datetime

from roadmap import ROLE_SKILL_MAP, LEARNING_RESOURCES, build_roadmap, missing_skills_for_role
from resume_parser import extract_skills, extract_contact_info, detect_sections, parse_resume
from similarity import compute_ats_score, score_breakdown, compute_match_score


def _llm_enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _call_claude(prompt, max_tokens=500):
    """Shared helper: returns raw text from Claude, or None on any failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if hasattr(b, "text")).strip()
    except Exception:
        return None


# =============================================================================
# Skill taxonomy shared by several modules (radar, risk score, salary, GPS)
# =============================================================================

SKILL_CATEGORIES = {
    "Programming Languages": [
        "python", "java", "javascript", "typescript", "c++", "c#", "c", "go", "rust",
        "ruby", "php", "kotlin", "swift", "r", "scala",
    ],
    "Web & Frontend": [
        "html", "css", "react", "vue", "angular", "tailwind css", "redux", "webpack",
        "vite", "next.js", "sass",
    ],
    "Backend & APIs": [
        "node.js", "django", "flask", "fastapi", "express", "rest api", "graphql",
        "microservices", "system design",
    ],
    "Data, ML & AI": [
        "sql", "nosql", "pandas", "numpy", "machine learning", "deep learning",
        "scikit-learn", "tensorflow", "pytorch", "keras", "opencv", "nltk", "spacy",
        "data science", "data analysis", "data visualization", "artificial intelligence",
        "computer vision", "natural language processing", "tableau", "power bi",
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "ci/cd", "linux", "bash", "git",
    ],
    "Design & Product": [
        "figma", "adobe xd", "sketch", "wireframing", "prototyping", "ui design",
        "ux design", "product management", "agile", "scrum", "jira",
    ],
    "Security": [
        "cybersecurity", "network security", "penetration testing", "cryptography",
    ],
    "Soft & Process Skills": [
        "communication", "presentation skills", "research", "leadership", "teamwork",
        "problem solving", "unit testing",
    ],
}

# Skills flagged as fading in market demand vs. consistently trending, used by
# the Career Risk Score. Deliberately conservative / illustrative, not a
# claim of authoritative labor-market data.
LEGACY_SKILLS = {
    "jquery", "flash", "vb.net", "perl", "cobol", "silverlight", "backbone.js",
    "coffeescript", "grunt",
}
TRENDING_SKILLS = {
    "machine learning", "deep learning", "artificial intelligence", "kubernetes",
    "docker", "aws", "azure", "gcp", "typescript", "react", "next.js", "rust",
    "go", "cybersecurity", "system design", "data science", "graphql", "terraform",
    "computer vision", "natural language processing",
}


def _categorize_skills(skills):
    skills_set = set(s.lower() for s in skills)
    out = {}
    categorized = set()
    for category, members in SKILL_CATEGORIES.items():
        hits = sorted(skills_set & set(members))
        out[category] = hits
        categorized.update(hits)
    leftover = sorted(skills_set - categorized)
    if leftover:
        out["Other / Domain-specific"] = leftover
    return out


# =============================================================================
# 1. AI Recruiter Mode - simulates a recruiter's ~6-second resume scan
# =============================================================================

def recruiter_mode(report):
    """report: the standard report dict produced by app.build_report()."""
    sections = report.get("sections_detected", {})
    contact = report.get("contact_info", {})
    ats = report.get("ats_score", 0)
    match = report.get("match_score")
    skills = report.get("skills_found", [])
    word_count = report.get("word_count", 0)

    notices, red_flags = [], []

    if sections.get("summary"):
        notices.append("A summary up top gives an instant read on who you are.")
    else:
        red_flags.append("No summary/objective - recruiters have to hunt for context in the first few seconds.")

    if contact.get("email") and (contact.get("linkedin") or contact.get("github")):
        notices.append("Contact block is complete and easy to scan.")
    else:
        red_flags.append("Contact info is incomplete - missing email or a LinkedIn/GitHub link.")

    if sections.get("experience"):
        notices.append("Experience section is present and easy to locate.")
    else:
        red_flags.append("No clearly labeled Experience section - recruiters may assume you have none.")

    if len(skills) >= 8:
        notices.append(f"Strong keyword density - {len(skills)} recognizable skills scanned instantly.")
    elif len(skills) < 4:
        red_flags.append("Very few scannable skill keywords - an ATS or human scanner may pass over you.")

    if word_count > 1100:
        red_flags.append("Resume reads long for a 6-second scan - the most important line may get missed.")
    elif word_count < 150:
        red_flags.append("Resume is very sparse - a recruiter has almost nothing to react to.")

    # First-impression score: blended, explainable, weighted toward what a
    # human actually perceives in the first glance (structure + keywords).
    impression_score = round(
        0.45 * ats + 0.25 * (min(len(skills), 12) / 12 * 100)
        + 0.30 * (match if match is not None else ats)
    )
    impression_score = max(0, min(100, impression_score))

    if impression_score >= 78:
        verdict = "Shortlist"
        headline = "This resume clears the 6-second scan with room to spare."
    elif impression_score >= 55:
        verdict = "Maybe pile"
        headline = "This resume survives the scan but doesn't stand out yet."
    else:
        verdict = "Likely passed over"
        headline = "This resume risks being skipped in the first few seconds."

    return {
        "first_impression_score": impression_score,
        "verdict": verdict,
        "headline": headline,
        "positive_signals": notices or ["Nothing stood out immediately - consider adding a summary and more keywords."],
        "red_flags": red_flags or ["No major red flags spotted in the first scan."],
        "scan_order": ["Name & contact block", "Most recent role / summary line", "Skills keywords", "Section headers"],
    }


# =============================================================================
# 2. Resume Timeline Prediction - explainable, formula-based projection
# =============================================================================

def timeline_prediction(report, applications_per_week=10):
    ats = report.get("ats_score", 0)
    match = report.get("match_score")
    strength = round((ats * 0.6) + ((match if match is not None else ats) * 0.4))
    strength = max(5, min(95, strength))

    # Illustrative response-rate curve: stronger profiles convert applications
    # to callbacks faster. Coefficients chosen so a 50-strength profile lands
    # near commonly-cited early-career benchmarks (~1 callback per 10-15 apps).
    callback_rate = round(2 + (strength / 100) * 14, 1)  # % of applications -> callback
    interview_rate = round(callback_rate * 0.55, 1)       # % of applications -> actual interview

    apps_per_callback = round(100 / callback_rate, 1) if callback_rate else None
    weeks_to_first_callback = math.ceil((apps_per_callback or 20) / applications_per_week) if applications_per_week else None

    milestones = [
        {"week": 1, "label": "Applications go out", "detail": f"Send ~{applications_per_week} tailored applications this week."},
        {
            "week": weeks_to_first_callback or 2,
            "label": "First recruiter callback (expected)",
            "detail": f"At your current profile strength, expect roughly 1 callback per {apps_per_callback or '—'} applications.",
        },
        {
            "week": (weeks_to_first_callback or 2) + 1,
            "label": "First real interview (expected)",
            "detail": "Use the Mock Interview module now so you're rehearsed before this happens.",
        },
        {
            "week": (weeks_to_first_callback or 2) + 3,
            "label": "Offer-stage window",
            "detail": "Typical early-career pipelines run 3-5 weeks from first interview to offer.",
        },
    ]

    return {
        "profile_strength": strength,
        "estimated_callback_rate_percent": callback_rate,
        "estimated_interview_rate_percent": interview_rate,
        "applications_per_week_assumed": applications_per_week,
        "estimated_weeks_to_first_callback": weeks_to_first_callback,
        "milestones": milestones,
        "disclaimer": (
            "An explainable projection based on your ATS/match scores, not a "
            "guarantee - real timelines vary by market, role, and referral access."
        ),
    }


# =============================================================================
# 3. AI Career Twin - a forward-projected persona built from the resume
# =============================================================================

def _seniority_from_report(report):
    word_count = report.get("word_count", 0)
    skill_count = len(report.get("skills_found", []))
    sections = report.get("sections_detected", {})
    score = 0
    score += 1 if word_count > 500 else 0
    score += 1 if skill_count > 10 else 0
    score += 1 if sections.get("certifications") else 0
    if score >= 2:
        return "Mid-level"
    if score == 1:
        return "Junior / Early-career"
    return "Entry-level / Student"


def career_twin(report, target_role=None):
    skills = report.get("skills_found", [])
    stage = _seniority_from_report(report)
    role = target_role or _infer_closest_role(skills)

    role_skills = ROLE_SKILL_MAP.get(role, [])
    have = set(skills)
    match_pct = round(len(have & set(role_skills)) / len(role_skills) * 100) if role_skills else 0

    def horizon(years, extra_skills_needed):
        return {
            "years_out": years,
            "title_estimate": f"{'Senior ' if years >= 5 else ''}{role}" if years >= 3 else role,
            "focus": (
                f"Deepen {', '.join(extra_skills_needed[:3])}" if extra_skills_needed
                else "Specialize and start mentoring / owning larger scope"
            ),
        }

    missing = missing_skills_for_role(skills, role) if role in ROLE_SKILL_MAP else []
    twin_path = [
        horizon(1, missing[:4]),
        horizon(3, missing[4:8] or ["system design", "leadership"]),
        horizon(5, ["technical strategy", "mentoring", "architecture ownership"]),
    ]

    llm_text = None
    if _llm_enabled():
        prompt = (
            "In 2-3 warm, specific sentences (no bullet points), describe a career "
            f"'digital twin' narrative for someone currently at the {stage} stage with these "
            f"skills: {', '.join(skills[:15]) or 'few detected skills'}, aiming toward a "
            f"{role} career path. Be encouraging but realistic. Do not invent job titles they "
            "haven't held or specific employers."
        )
        llm_text = _call_claude(prompt, max_tokens=250)

    return {
        "current_stage": stage,
        "closest_role_match": role,
        "role_match_percent": match_pct,
        "narrative": llm_text or (
            f"Right now your twin sits at the {stage} stage, already showing strength in "
            f"{', '.join(skills[:4]) or 'a small but growing skill set'}. Closing the gap toward "
            f"{role} is mostly about the skills listed in the roadmap below, not starting over."
        ),
        "growth_path": twin_path,
        "used_llm": bool(llm_text),
    }


def _infer_closest_role(skills):
    have = set(skills)
    best_role, best_score = None, -1
    for role, role_skills in ROLE_SKILL_MAP.items():
        overlap = len(have & set(role_skills))
        if overlap > best_score:
            best_score, best_role = overlap, role
    return best_role or "Full Stack Developer"


# =============================================================================
# 4. Recruiter Eye Tracking - simulated attention heatmap over resume zones
# =============================================================================

def eye_tracking(report):
    sections = report.get("sections_detected", {})
    contact = report.get("contact_info", {})
    skills = report.get("skills_found", [])

    # Base attention weights drawn from published resume eye-tracking studies
    # (top band + left column dominate; skills lists draw a quick second look).
    base = {
        "Name & Contact (top band)": 20,
        "Summary / Headline": 17,
        "Most recent Experience entry": 24,
        "Skills section": 16,
        "Education": 9,
        "Projects / Certifications": 8,
        "Older / lower entries": 6,
    }

    present_map = {
        "Name & Contact (top band)": bool(contact.get("email")),
        "Summary / Headline": sections.get("summary"),
        "Most recent Experience entry": sections.get("experience"),
        "Skills section": sections.get("skills") or bool(skills),
        "Education": sections.get("education"),
        "Projects / Certifications": sections.get("projects") or sections.get("certifications"),
        "Older / lower entries": True,
    }

    zones = []
    for zone, weight in base.items():
        present = present_map.get(zone, True)
        # Missing zones don't get "skipped attention" - they get zero, and
        # that reclaimed attention redistributes toward what IS visible.
        zones.append({"zone": zone, "raw_weight": weight if present else 0, "present": bool(present)})

    total = sum(z["raw_weight"] for z in zones) or 1
    for z in zones:
        z["attention_percent"] = round(z["raw_weight"] / total * 100, 1)
        del z["raw_weight"]

    zones.sort(key=lambda z: z["attention_percent"], reverse=True)
    dead_zones = [z["zone"] for z in zones if not z["present"]]

    return {
        "pattern": "F-pattern (top band + left column dominate, attention decays downward)",
        "zones": zones,
        "dead_zones": dead_zones or ["None - every standard zone has content to scan."],
        "tip": "The top third of your resume gets roughly half of all recruiter attention - your strongest line belongs there.",
    }


# =============================================================================
# 5. AI Interview Avatar - persona-flavored mock interview wrapper
# =============================================================================

INTERVIEWER_PERSONAS = {
    "friendly_mentor": {
        "name": "Friendly Mentor",
        "tone": "warm and encouraging, focuses on growth",
        "score_leniency": 6,
        "intro": "Take your time - I'm mostly listening for how you think, not a perfect answer.",
    },
    "strict_bar_raiser": {
        "name": "Strict Bar-Raiser",
        "tone": "terse and exacting, presses for specifics",
        "score_leniency": -8,
        "intro": "Be precise. I'll ask follow-ups if I don't hear specifics.",
    },
    "startup_founder": {
        "name": "Fast-Paced Startup Founder",
        "tone": "moves quickly, cares about impact and ownership",
        "score_leniency": -2,
        "intro": "Keep it snappy - what did YOU actually do, and what changed because of it?",
    },
}


def available_personas():
    return [{"id": k, **v} for k, v in INTERVIEWER_PERSONAS.items()]


def apply_persona_feedback(feedback, persona_id):
    """Adjusts a heuristic feedback dict's score/tone to match a persona,
    without ever fabricating strengths/weaknesses that weren't detected."""
    persona = INTERVIEWER_PERSONAS.get(persona_id)
    if not persona:
        return feedback
    adjusted = dict(feedback)
    adjusted["score"] = max(5, min(100, feedback["score"] + persona["score_leniency"]))
    adjusted["persona"] = persona["name"]
    adjusted["persona_tone"] = persona["tone"]
    return adjusted


# =============================================================================
# 6. Live Confidence Meter - text-level confidence analysis
# =============================================================================

HEDGING_WORDS = [
    "i think", "maybe", "sort of", "kind of", "i guess", "probably", "not sure",
    "i suppose", "might", "possibly", "i believe", "hopefully", "just", "a little bit",
]
FILLER_WORDS = ["um", "uh", "like", "you know", "basically", "actually", "literally"]
ASSERTIVE_MARKERS = ["i led", "i built", "i drove", "i owned", "i delivered", "i achieved", "i decided"]


def confidence_meter(text):
    text = text or ""
    lowered = text.lower()
    words = text.split()
    word_count = max(len(words), 1)

    hedges = sum(lowered.count(h) for h in HEDGING_WORDS)
    fillers = sum(lowered.count(f) for f in FILLER_WORDS)
    assertive_hits = sum(1 for m in ASSERTIVE_MARKERS if m in lowered)
    has_metric = bool(re.search(r"\d", text))

    hedge_ratio = hedges / word_count * 100
    filler_ratio = fillers / word_count * 100

    score = 55
    score += assertive_hits * 10
    score += 8 if has_metric else 0
    score -= hedge_ratio * 6
    score -= filler_ratio * 4
    score += min(word_count / 5, 10)  # a little credit for substance, capped
    score = max(5, min(100, round(score)))

    if score >= 75:
        level = "Confident"
    elif score >= 50:
        level = "Moderate"
    else:
        level = "Hesitant"

    tips = []
    if hedges:
        tips.append("Cut hedging phrases like 'I think' or 'sort of' - state what you did directly.")
    if fillers:
        tips.append("Trim filler words ('like', 'basically', 'actually') for a crisper delivery.")
    if not has_metric:
        tips.append("Add a concrete number to anchor the impact of what you're describing.")
    if not assertive_hits:
        tips.append("Lead with a direct 'I did / I built / I owned' statement.")
    if not tips:
        tips.append("Strong, direct delivery - keep this up.")

    return {
        "confidence_score": score,
        "confidence_level": level,
        "hedging_phrases_detected": hedges,
        "filler_words_detected": fillers,
        "assertive_statements_detected": assertive_hits,
        "has_quantified_detail": has_metric,
        "tips": tips[:3],
    }


# =============================================================================
# 7. AI Resume Heatmap - per-section strength heat score
# =============================================================================

def resume_heatmap(report):
    breakdown = report.get("score_breakdown", {})
    sections = report.get("sections_detected", {})
    skills = report.get("skills_found", [])

    section_scores = {
        "Contact Info": breakdown.get("contact_info", 0),
        "Summary": 100 if sections.get("summary") else 15,
        "Experience": 100 if sections.get("experience") else 10,
        "Skills": breakdown.get("skills_coverage", 0),
        "Projects": 100 if sections.get("projects") else 35,
        "Education": 100 if sections.get("education") else 40,
        "Certifications": 100 if sections.get("certifications") else 50,
        "Overall length/depth": breakdown.get("content_depth", 0),
    }

    def band(score):
        if score >= 75:
            return "hot"
        if score >= 45:
            return "warm"
        return "cold"

    heatmap = [
        {"section": name, "score": round(score), "band": band(score)}
        for name, score in section_scores.items()
    ]
    coldest = min(heatmap, key=lambda h: h["score"])

    return {
        "heatmap": heatmap,
        "weakest_zone": coldest["section"],
        "skill_keyword_density": round(min(len(skills), 20) / 20 * 100),
        "legend": {"hot": "Recruiter-ready", "warm": "Needs polish", "cold": "Fix first"},
    }


# =============================================================================
# 8. AI Skill Radar - categorized skill coverage vs an ideal profile
# =============================================================================

def skill_radar(skills, target_role=None):
    categorized = _categorize_skills(skills)

    ideal_counts = {  # rough "well-rounded" benchmark per category, for context
        "Programming Languages": 3, "Web & Frontend": 4, "Backend & APIs": 3,
        "Data, ML & AI": 4, "Cloud & DevOps": 4, "Design & Product": 3,
        "Security": 2, "Soft & Process Skills": 3, "Other / Domain-specific": 2,
    }

    axes = []
    for category, ideal in ideal_counts.items():
        have = categorized.get(category, [])
        pct = round(min(len(have), ideal) / ideal * 100) if ideal else 0
        axes.append({"category": category, "score": pct, "skills": have})

    role_axes = None
    if target_role and target_role in ROLE_SKILL_MAP:
        role_skills = set(ROLE_SKILL_MAP[target_role])
        have_set = set(skills)
        role_axes = round(len(have_set & role_skills) / len(role_skills) * 100)

    strongest = max(axes, key=lambda a: a["score"]) if axes else None
    weakest = min((a for a in axes if a["skills"] or a["score"] < 100), key=lambda a: a["score"], default=None)

    return {
        "axes": axes,
        "strongest_area": strongest["category"] if strongest else None,
        "weakest_area": weakest["category"] if weakest else None,
        "target_role_fit_percent": role_axes,
    }


# =============================================================================
# 9. Personalized Salary Prediction
# =============================================================================

# Illustrative early-career base ranges in INR lakhs/annum (India tech market
# context) for a 0-1 YOE baseline at a metro location. Clearly framed as an
# estimate, not live market data.
BASE_SALARY_INR_LPA = {
    "Frontend Developer": (4.5, 8),
    "Backend Developer": (5, 9),
    "Full Stack Developer": (5.5, 10),
    "Data Analyst": (4, 7),
    "Data Scientist": (6, 12),
    "Machine Learning Engineer": (7, 14),
    "DevOps Engineer": (6, 11),
    "Mobile Developer": (5, 9),
    "UI/UX Designer": (4, 7.5),
    "Product Manager": (7, 13),
    "Cybersecurity Analyst": (5.5, 10),
}

LOCATION_MULTIPLIER = {
    "metro": 1.0, "tier2": 0.8, "remote_global": 1.6,
}


def salary_prediction(skills, target_role=None, experience_years=0, location_tier="metro"):
    role = target_role or _infer_closest_role(skills)
    base_low, base_high = BASE_SALARY_INR_LPA.get(role, (4, 8))

    experience_years = max(0, min(float(experience_years or 0), 20))
    exp_multiplier = 1 + (experience_years * 0.12)

    role_skills = set(ROLE_SKILL_MAP.get(role, []))
    have = set(skills)
    skill_fit = len(have & role_skills) / len(role_skills) if role_skills else 0.5
    skill_multiplier = 0.9 + skill_fit * 0.35

    loc_multiplier = LOCATION_MULTIPLIER.get(location_tier, 1.0)

    low = round(base_low * exp_multiplier * skill_multiplier * loc_multiplier, 1)
    high = round(base_high * exp_multiplier * skill_multiplier * loc_multiplier, 1)
    midpoint = round((low + high) / 2, 1)

    return {
        "target_role": role,
        "estimated_range_lpa": {"low": low, "high": high, "midpoint": midpoint},
        "currency": "INR (lakhs per annum)",
        "factors": {
            "experience_years": experience_years,
            "skill_fit_percent": round(skill_fit * 100),
            "location_tier": location_tier,
        },
        "disclaimer": (
            "A directional estimate based on role, experience and skill overlap - "
            "not live job-market data. Always cross-check with current listings."
        ),
    }


# =============================================================================
# 10. AI Career GPS - turn-by-turn navigation toward a target role
# =============================================================================

def career_gps(skills, target_role, hours_per_week=8):
    role = target_role or _infer_closest_role(skills)
    missing = missing_skills_for_role(skills, role) if role in ROLE_SKILL_MAP else []
    plan = build_roadmap(missing, hours_per_week=hours_per_week)

    role_skills = ROLE_SKILL_MAP.get(role, [])
    current_fit = round(len(set(skills) & set(role_skills)) / len(role_skills) * 100) if role_skills else 0

    directions = []
    week_cursor = 0
    for i, phase in enumerate(plan["phases"], start=1):
        phase_hours = sum(s["estimated_hours"] for s in phase["skills"])
        phase_weeks = max(1, round(phase_hours / max(hours_per_week, 1)))
        week_cursor += phase_weeks
        directions.append({
            "step": i,
            "instruction": f"Continue toward {role} by mastering: {', '.join(s['skill'] for s in phase['skills'])}",
            "phase": phase["name"],
            "eta_week": week_cursor,
        })

    directions.append({
        "step": len(directions) + 1,
        "instruction": f"Arrive at {role}-ready status - start tailoring applications and mock interviews.",
        "phase": "Arrival",
        "eta_week": week_cursor + 1,
    })

    return {
        "current_location_percent": current_fit,
        "destination": role,
        "distance_skills_remaining": len(missing),
        "total_eta_weeks": week_cursor + 1,
        "directions": directions,
    }


# =============================================================================
# 11. Resume Version Comparison
# =============================================================================

def compare_resume_versions(file_path_a, file_path_b, skills_list):
    parsed_a = parse_resume(file_path_a, skills_list)
    parsed_b = parse_resume(file_path_b, skills_list)

    ats_a = compute_ats_score(parsed_a)
    ats_b = compute_ats_score(parsed_b)

    skills_a, skills_b = set(parsed_a["skills"]), set(parsed_b["skills"])
    added = sorted(skills_b - skills_a)
    removed = sorted(skills_a - skills_b)

    sections_a, sections_b = parsed_a["sections"], parsed_b["sections"]
    section_changes = {
        s: {"version_a": sections_a.get(s, False), "version_b": sections_b.get(s, False)}
        for s in sections_a
    }

    if ats_b > ats_a:
        verdict = "Version B is the stronger resume."
    elif ats_a > ats_b:
        verdict = "Version A is the stronger resume."
    else:
        verdict = "Both versions score equally on ATS quality - compare skill coverage below to break the tie."

    return {
        "version_a": {"ats_score": ats_a, "word_count": parsed_a["word_count"], "skill_count": len(skills_a)},
        "version_b": {"ats_score": ats_b, "word_count": parsed_b["word_count"], "skill_count": len(skills_b)},
        "ats_score_delta": ats_b - ats_a,
        "skills_added_in_b": added,
        "skills_removed_in_b": removed,
        "section_changes": section_changes,
        "verdict": verdict,
    }


# =============================================================================
# 12. AI Portfolio Review - reviews pasted project/portfolio text
# =============================================================================

PORTFOLIO_SIGNAL_KEYWORDS = {
    "live_demo": ["live demo", "deployed", "hosted at", "try it", "view live"],
    "source_code": ["github.com", "source code", "repository", "repo"],
    "visuals": ["screenshot", "video", "gif", "walkthrough", "demo video"],
    "impact": ["users", "downloads", "reduced", "improved", "increased", "%", "results"],
    "documentation": ["readme", "documentation", "setup instructions", "how to run"],
}


def portfolio_review(portfolio_text, skills_list):
    text = portfolio_text or ""
    lowered = text.lower()

    detected_skills = extract_skills(text, skills_list)
    categorized = _categorize_skills(detected_skills)
    diversity = sum(1 for v in categorized.values() if v)

    signals = {}
    for key, phrases in PORTFOLIO_SIGNAL_KEYWORDS.items():
        signals[key] = any(p in lowered for p in phrases)

    present_count = sum(1 for v in signals.values() if v)
    completeness = round(present_count / len(signals) * 100)

    suggestions = []
    if not signals["live_demo"]:
        suggestions.append("Add a live/deployed link for at least one project - working demos convert far better than screenshots alone.")
    if not signals["source_code"]:
        suggestions.append("Link the GitHub repo for each project so reviewers can see real code, not just descriptions.")
    if not signals["visuals"]:
        suggestions.append("Add a screenshot or short demo video/GIF - visual proof is scanned faster than text.")
    if not signals["impact"]:
        suggestions.append("Describe outcomes, not just features - what changed because this project existed?")
    if not signals["documentation"]:
        suggestions.append("Add a README with setup instructions - it signals engineering maturity.")
    if diversity < 2:
        suggestions.append("Your projects lean into a single skill category - a second project in a different area broadens your range.")

    llm_text = None
    if _llm_enabled() and text.strip():
        prompt = (
            "You are reviewing a developer's portfolio description. In 2-3 sentences, give "
            "direct, specific feedback on what's strong and what's missing. Do not invent "
            f"details not present in the text.\n\nPORTFOLIO TEXT:\n{text[:3000]}"
        )
        llm_text = _call_claude(prompt, max_tokens=250)

    return {
        "completeness_score": completeness,
        "signals_detected": signals,
        "tech_stack_detected": detected_skills,
        "tech_stack_diversity_categories": diversity,
        "suggestions": suggestions[:5] or ["Strong portfolio coverage - nice work."],
        "ai_review": llm_text,
    }


# =============================================================================
# 13. One-Click HR Summary
# =============================================================================

def hr_summary(report):
    skills = report.get("skills_found", [])
    ats = report.get("ats_score", 0)
    stage = _seniority_from_report(report)
    top_skills = ", ".join(skills[:5]) if skills else "a developing technical skill set"

    template = (
        f"{stage} candidate with hands-on exposure to {top_skills}. "
        f"Resume scores {ats}/100 on structural ATS quality"
        + (f" and a {report['match_score']}% match against the target role's requirements" if report.get("match_score") is not None else "")
        + f". Detected {len(skills)} relevant technical/tool keywords across "
        + f"{sum(1 for v in report.get('sections_detected', {}).values() if v)} standard resume sections. "
        "Recommended for a screening call to validate depth on the listed skills."
    )

    llm_text = None
    if _llm_enabled():
        prompt = (
            "Write a crisp, 3-sentence HR screening summary of this candidate for a recruiter's "
            "notes, based ONLY on these facts (do not invent employers, dates, or achievements): "
            f"seniority stage={stage}; ATS score={ats}/100; skills detected={skills}; "
            f"job-description match score={report.get('match_score')}."
        )
        llm_text = _call_claude(prompt, max_tokens=220)

    return {
        "summary": llm_text or template,
        "used_llm": bool(llm_text),
        "quick_facts": {
            "seniority_stage": stage,
            "ats_score": ats,
            "match_score": report.get("match_score"),
            "skills_detected": len(skills),
        },
    }


# =============================================================================
# 14. AI Career Risk Score - skill-obsolescence / stagnation risk
# =============================================================================

def career_risk_score(skills):
    skills_set = set(s.lower() for s in skills)
    legacy_hits = sorted(skills_set & LEGACY_SKILLS)
    trending_hits = sorted(skills_set & TRENDING_SKILLS)
    categorized = _categorize_skills(skills)
    diversity = sum(1 for v in categorized.values() if v)

    legacy_ratio = len(legacy_hits) / max(len(skills_set), 1)
    trending_ratio = len(trending_hits) / max(len(skills_set), 1)

    risk = 30
    risk += legacy_ratio * 100 * 0.5
    risk -= trending_ratio * 100 * 0.4
    risk -= min(diversity, 5) * 4
    risk = max(5, min(95, round(risk)))

    if risk >= 65:
        level = "High"
    elif risk >= 35:
        level = "Moderate"
    else:
        level = "Low"

    factors = []
    if legacy_hits:
        factors.append(f"Some listed skills are fading in demand: {', '.join(legacy_hits)}.")
    if not trending_hits:
        factors.append("No clearly trending/high-growth skills detected yet.")
    else:
        factors.append(f"Good signal from trending skills: {', '.join(trending_hits)}.")
    if diversity <= 1:
        factors.append("Skill set is concentrated in a single category - low diversification raises risk if that area cools.")
    else:
        factors.append(f"Skills span {diversity} categories, which spreads risk across the market.")

    recommendations = []
    if legacy_hits:
        recommendations.append(f"Plan a migration path off {legacy_hits[0]} toward its modern equivalent.")
    if not trending_hits:
        recommendations.append("Pick one trending skill adjacent to your current stack (see the Roadmap module) to future-proof your profile.")
    if diversity <= 1:
        recommendations.append("Add a skill from a second category (e.g. cloud, data, or product) to diversify.")
    if not recommendations:
        recommendations.append("Your skill portfolio looks well-positioned - keep refreshing it yearly.")

    return {
        "risk_score": risk,
        "risk_level": level,
        "legacy_skills_detected": legacy_hits,
        "trending_skills_detected": trending_hits,
        "category_diversity": diversity,
        "factors": factors,
        "recommendations": recommendations[:3],
    }


# =============================================================================
# 15. AI Achievement Generator - rewrites a weak bullet using the XYZ formula
# =============================================================================

STRONG_VERBS = [
    "Architected", "Engineered", "Spearheaded", "Optimized", "Automated", "Delivered",
    "Launched", "Streamlined", "Accelerated", "Redesigned", "Scaled", "Reduced",
]

WEAK_VERB_MAP = {
    "worked on": "Engineered", "helped with": "Contributed to and delivered",
    "responsible for": "Owned", "did": "Executed", "made": "Built",
    "was involved in": "Drove", "assisted": "Supported and accelerated",
    "handled": "Managed",
}


def _detect_action_verb(text):
    lowered = text.strip().lower()
    return lowered.split()[0] if lowered.split() else ""


def achievement_generator(bullet_text, skill_context=None):
    text = (bullet_text or "").strip()
    if not text:
        return {"error": "bullet_text is required."}

    lowered = text.lower()
    has_metric = bool(re.search(r"\d", text))
    has_weak_phrase = next((wp for wp in WEAK_VERB_MAP if wp in lowered), None)

    # Rule-based rewrite: swap a weak opening phrase for a strong verb and
    # append an explicit placeholder for impact if none was quantified -
    # never invents a number on the user's behalf.
    rewritten = text
    if has_weak_phrase:
        replacement = WEAK_VERB_MAP[has_weak_phrase]
        rewritten = re.sub(re.escape(has_weak_phrase), replacement.lower(), rewritten, count=1, flags=re.IGNORECASE)
        rewritten = rewritten[0].upper() + rewritten[1:]
    else:
        first_verb = _detect_action_verb(text)
        if first_verb and not first_verb[0].isupper():
            suggestion_verb = STRONG_VERBS[hash(first_verb) % len(STRONG_VERBS)]
            rewritten = f"{suggestion_verb} {text}" if not text[0].isupper() else text

    if not has_metric:
        rewritten = rewritten.rstrip(".") + ", resulting in [add a measurable outcome: %, time saved, users, revenue]."

    formula_rewrite = (
        f"{STRONG_VERBS[hash(text) % len(STRONG_VERBS)]} "
        f"{text.strip().rstrip('.')}"
        + (f" using {skill_context}" if skill_context else "")
        + ", resulting in [X measurable outcome]."
    )

    llm_rewrite = None
    if _llm_enabled():
        prompt = (
            "Rewrite this single resume bullet point to start with a strong action verb and "
            "follow the XYZ formula (Accomplished X as measured by Y, by doing Z). "
            "CRITICAL: do not invent any numbers, metrics, or outcomes that are not already "
            "present in the original text - if no metric is present, insert the literal "
            "placeholder '[quantify: e.g. %, time, users]' instead of a made-up figure. "
            f"Return ONLY the rewritten bullet.\n\nORIGINAL: {text}"
        )
        llm_rewrite = _call_claude(prompt, max_tokens=150)

    return {
        "original": text,
        "detected_weak_phrase": has_weak_phrase,
        "has_quantified_outcome": has_metric,
        "rule_based_rewrite": rewritten,
        "xyz_formula_rewrite": formula_rewrite,
        "ai_rewrite": llm_rewrite,
        "tip": "Fill in every bracketed placeholder with a real number before using this on your resume - never fabricate metrics.",
    }


# =============================================================================
# 16. AI Career Time Machine - projects skills/salary/role forward in time,
# entirely by re-running the *existing* skill-gap, salary, and role-fit
# engines above at increasing experience checkpoints. No new data source,
# no invented facts - just the same explainable math, staged over time.
# =============================================================================

_TIME_MACHINE_CHECKPOINTS = [
    {"label": "Now", "months": 0},
    {"label": "6 Months", "months": 6},
    {"label": "1 Year", "months": 12},
    {"label": "2 Years", "months": 24},
    {"label": "5 Years", "months": 60},
]

_SENIORITY_BY_YEARS = [
    (0, "Entry-level"), (1, "Junior"), (3, "Mid-level"), (6, "Senior"), (10, "Staff/Lead"),
]

_EXAMPLE_COMPANIES_BY_ROLE = {
    "Frontend Developer": ["Zomato", "Razorpay", "Freshworks", "a Series-A startup"],
    "Backend Developer": ["Swiggy", "CRED", "Postman", "a fintech scale-up"],
    "Full Stack Developer": ["Flipkart", "Meesho", "Groww", "a Y Combinator startup"],
    "Data Analyst": ["Deloitte", "PhonePe", "Myntra", "a growth-stage D2C company"],
    "Data Scientist": ["Fractal Analytics", "Mu Sigma", "Ola", "a health-tech startup"],
    "Machine Learning Engineer": ["NVIDIA", "Sprinklr", "Innovaccer", "an AI-first startup"],
    "DevOps Engineer": ["Zoho", "Chargebee", "Postman", "a cloud infra startup"],
    "Mobile Developer": ["PhonePe", "Dream11", "Meesho", "an app-first startup"],
    "UI/UX Designer": ["Swiggy Design", "Zoho", "CRED Design", "a product studio"],
    "Product Manager": ["Cred", "Groww", "Razorpay", "an early-stage startup"],
    "Cybersecurity Analyst": ["TCS Cybersecurity", "Wipro", "a fintech security team", "a SOC consultancy"],
}


def _seniority_label(years):
    label = _SENIORITY_BY_YEARS[0][1]
    for threshold, name in _SENIORITY_BY_YEARS:
        if years >= threshold:
            label = name
    return label


def career_time_machine(report, target_role=None):
    """Projects a resume forward through 6mo/1yr/2yr/5yr checkpoints by
    re-running the real skill-gap (career_gps) and salary_prediction
    engines at each point - assuming the candidate follows the roadmap at
    a steady, disclosed pace. This is a projection under stated
    assumptions, not a guarantee, and says so explicitly."""
    skills = report.get("skills_found", [])
    role = target_role or _infer_closest_role(skills)

    gps = career_gps(skills, role, hours_per_week=8)
    # Map each roadmap direction step to the week it completes, so we know
    # which skills are "acquired" by which future checkpoint.
    role_skills = set(ROLE_SKILL_MAP.get(role, []))
    missing_ordered = missing_skills_for_role(skills, role) if role in ROLE_SKILL_MAP else []

    checkpoints = []
    previously_gained_count = 0
    for cp in _TIME_MACHINE_CHECKPOINTS:
        weeks_elapsed = cp["months"] * 4.33
        # How far into the roadmap would they be by this checkpoint, at the
        # same 8h/week pace used for career_gps above?
        completed_fraction = min(weeks_elapsed / max(gps["total_eta_weeks"], 1), 1.0)
        skills_gained_count = round(completed_fraction * len(missing_ordered))
        projected_skills = list(skills) + missing_ordered[:skills_gained_count]
        newly_this_checkpoint = missing_ordered[previously_gained_count:skills_gained_count]
        previously_gained_count = skills_gained_count

        years = cp["months"] / 12
        salary = salary_prediction(projected_skills, target_role=role, experience_years=years)

        role_fit = round(len(set(projected_skills) & role_skills) / len(role_skills) * 100) if role_skills else 0
        # Future resume score: current ATS score, nudged up as skill fit and
        # experience grow - capped, and never presented as more than an
        # illustrative trend line.
        projected_ats = min(97, round(report.get("ats_score", 50) + (role_fit - (report.get("score_breakdown", {}).get("skills_coverage", 0))) * 0.15 + years * 2))

        checkpoints.append({
            "label": cp["label"],
            "seniority": _seniority_label(years),
            "role_fit_percent": role_fit,
            "newly_acquired_skills": newly_this_checkpoint,
            "expected_salary_lpa": salary["estimated_range_lpa"],
            "projected_resume_score": max(report.get("ats_score", 50), projected_ats),
            "possible_companies": _EXAMPLE_COMPANIES_BY_ROLE.get(role, ["a mid-size product company", "a growth-stage startup"])[:3],
        })

    return {
        "target_role": role,
        "checkpoints": checkpoints,
        "assumption": "Assumes ~8 hrs/week of steady learning toward the missing skills in your Career GPS roadmap for this role.",
        "disclaimer": "An illustrative projection from your current profile and a fixed learning pace - not a guarantee, and not live market data. Company names are representative examples for this role, not confirmed openings.",
    }