"""
hiring_simulation.py
-----------------------
AI Hiring Simulation: walks a resume through a realistic, staged hiring
pipeline (HR Screening -> Technical Review -> Manager Decision), the way a
real applicant-tracking + interview loop actually works at most companies.

This is NOT a new scoring model bolted on top - every number here is
derived from the same explainable engines the rest of the app already uses
(the standard `report` dict from app.build_report(), same convention as
advanced_features.recruiter_mode). The "simulation" is a presentation
layer: it stages already-computed signals as a hiring narrative instead of
inventing new ones, so it stays consistent with the rest of the app's
"every score is explainable" story.
"""

from interview import _pick_technical_questions, TECHNICAL_QUESTIONS, _display_skill

_LEADERSHIP_SKILLS = {"leadership", "mentoring", "project management", "product management"}


def _has_leadership_signal(skills_found):
    return bool(_LEADERSHIP_SKILLS & set(skills_found))


# ---------------------------------------------------------------------------
# Stage 1 - HR Screening
# ---------------------------------------------------------------------------

def _hr_screening(report):
    breakdown = report.get("score_breakdown", {})
    ats_score = report.get("ats_score", 0)
    skills = report.get("skills_found", [])

    checks = []

    ats_pass = ats_score >= 65
    checks.append({"label": "ATS score above hiring threshold (65%)", "pass": ats_pass,
                    "detail": f"Scored {ats_score}%."})

    formatting_pass = breakdown.get("structure", 0) >= 80 and breakdown.get("contact_info", 0) >= 80
    checks.append({"label": "Clean formatting & complete contact info", "pass": formatting_pass,
                    "detail": f"Structure {breakdown.get('structure', 0)}%, contact info {breakdown.get('contact_info', 0)}%."})

    skills_pass = breakdown.get("skills_coverage", 0) >= 50
    checks.append({"label": "Relevant skills clearly listed", "pass": skills_pass,
                    "detail": f"Skills coverage {breakdown.get('skills_coverage', 0)}%, {len(skills)} skills detected."})

    leadership = _has_leadership_signal(skills)
    checks.append({"label": "Leadership / ownership keywords present", "pass": leadership,
                    "detail": "Found leadership, mentoring, or management language." if leadership
                              else "Not disqualifying, but recruiters do look for this - consider adding it if true for you."})

    passed = ats_pass and formatting_pass and skills_pass
    return {
        "stage": "HR Screening",
        "checks": checks,
        "result": "PASSED" if passed else "FLAGGED",
        "passed": passed,
        "leadership_signal": leadership,
    }


# ---------------------------------------------------------------------------
# Stage 2 - Technical Lead Review
# ---------------------------------------------------------------------------

def _technical_review(report, target_role=None):
    breakdown = report.get("score_breakdown", {})
    skills = report.get("skills_found", [])

    technical_score = round(
        breakdown.get("skills_coverage", 0) * 0.6
        + breakdown.get("quantified_impact", 0) * 0.4
    )

    question_keys = _pick_technical_questions(skills, target_role, limit=3)
    questions = [TECHNICAL_QUESTIONS[k] for k in question_keys if k in TECHNICAL_QUESTIONS]
    if not questions:
        questions = list(TECHNICAL_QUESTIONS.values())[:3]

    return {
        "stage": "Technical Lead Review",
        "score": technical_score,
        "questions": questions,
        "based_on_skills": [_display_skill(k) for k in question_keys],
        "note": "Score blends skill coverage against the target role and how well your bullets quantify impact - the same numbers from your Analyzer report.",
    }


# ---------------------------------------------------------------------------
# Stage 3 - Manager / Hiring Committee decision
# ---------------------------------------------------------------------------

def _manager_review(ats_score, technical_score, hr_passed, leadership):
    # Weighted committee vote - transparent, not a black box. Max: 35+45+15+5=100.
    chance = round(ats_score * 0.35 + technical_score * 0.45 + (15 if hr_passed else 0) + (5 if leadership else 0))
    chance = max(5, min(97, chance))

    if chance >= 75:
        verdict = "Interview Call"
    elif chance >= 50:
        verdict = "Waitlisted"
    else:
        verdict = "Not Selected This Round"

    factors = [
        f"ATS/resume quality contributed {round(ats_score * 0.35)} pts.",
        f"Technical review contributed {round(technical_score * 0.45)} pts.",
        f"HR screening: {'+15 pts (passed)' if hr_passed else '+0 pts (flagged)'}.",
        f"Leadership signal: {'+5 pts' if leadership else '+0 pts'}.",
    ]

    return {
        "stage": "Hiring Committee",
        "chance_percent": chance,
        "verdict": verdict,
        "factors": factors,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_hiring_simulation(report, target_role=None):
    """report: the standard report dict produced by app.build_report()."""
    hr = _hr_screening(report)
    tech = _technical_review(report, target_role)
    manager = _manager_review(report.get("ats_score", 0), tech["score"], hr["passed"], hr["leadership_signal"])

    return {
        "target_role": target_role,
        "pipeline": [hr, tech, manager],
        "note": "A staged walkthrough of your existing Analyzer scores, presented the way a real hiring pipeline is structured - not a separate AI model or new data source.",
    }
