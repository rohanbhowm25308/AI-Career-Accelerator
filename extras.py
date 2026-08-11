"""
extras.py
-----------
The remaining 10 AI Suite features, matching the same philosophy as
advanced_features.py: deterministic, explainable, built on the resume's
real detected data - nothing about the candidate is invented.

One honesty note up front: "AI Hackathon Partner Matching" as originally
described implies matching against a real pool of other users. This app
has no user accounts or database of other candidates, so
hackathon_partner_finder() does the honest version of that idea instead -
it profiles what an IDEAL teammate would cover for this candidate's gaps,
clearly labeled as a profile to search for, not a real match against real
people.
"""

from advanced_features import SKILL_CATEGORIES, _categorize_skills, _infer_closest_role, ROLE_SKILL_MAP
from roadmap import missing_skills_for_role, build_roadmap


# ---------------------------------------------------------------------------
# Shared: illustrative company hiring profiles, reused by both the Stress
# Test and the Dream Company Simulator. Each profile has its own emphasis -
# real companies do weigh things differently (a bank's ATS leans harder on
# formatting/compliance-safe formatting; a startup cares less about polish
# and more about raw skill breadth). These are illustrative archetypes,
# not actual company hiring criteria - disclosed as such in every response.
# ---------------------------------------------------------------------------

COMPANY_PROFILES = {
    "Google": {
        "emphasis_skills": ["data structures", "algorithms", "system design", "c++", "python"],
        "weight_skills": 0.45, "weight_ats": 0.25, "weight_impact": 0.30,
        "bar": 78,
    },
    "Amazon": {
        "emphasis_skills": ["leadership", "system design", "aws", "sql", "python"],
        "weight_skills": 0.35, "weight_ats": 0.25, "weight_impact": 0.40,
        "bar": 72,
    },
    "Microsoft": {
        "emphasis_skills": ["c#", "azure", "system design", "sql", ".net"],
        "weight_skills": 0.40, "weight_ats": 0.30, "weight_impact": 0.30,
        "bar": 74,
    },
    "Startup": {
        "emphasis_skills": ["python", "react", "node.js", "git", "rest api"],
        "weight_skills": 0.50, "weight_ats": 0.15, "weight_impact": 0.35,
        "bar": 55,
    },
    "Bank": {
        "emphasis_skills": ["sql", "java", "excel", "risk management", "compliance"],
        "weight_skills": 0.30, "weight_ats": 0.45, "weight_impact": 0.25,
        "bar": 68,
    },
}


def _score_against_profile(report, profile):
    breakdown = report.get("score_breakdown", {})
    skills = set(report.get("skills_found", []))
    ats = report.get("ats_score", 0)

    emphasis = set(profile["emphasis_skills"])
    skill_fit = round(len(skills & emphasis) / len(emphasis) * 100) if emphasis else 0
    impact = breakdown.get("quantified_impact", 0)

    score = round(
        skill_fit * profile["weight_skills"]
        + ats * profile["weight_ats"]
        + impact * profile["weight_impact"]
    )
    score = max(5, min(97, score))
    missing = sorted(emphasis - skills)
    return score, skill_fit, missing


# =============================================================================
# 1. AI Resume Stress Test
# =============================================================================

def resume_stress_test(report):
    results = []
    for company, profile in COMPANY_PROFILES.items():
        score, skill_fit, missing = _score_against_profile(report, profile)
        if score >= profile["bar"] + 15:
            verdict = "Strong Match"
        elif score >= profile["bar"]:
            verdict = "Likely Pass"
        else:
            verdict = "Needs Work"
        results.append({
            "company": company,
            "score": score,
            "verdict": verdict,
            "missing_emphasis_skills": missing[:3],
            "why": (f"Needs {', '.join(missing[:2])}" if missing else "Perfect Match on core emphasis skills"),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return {
        "results": results,
        "disclaimer": "Illustrative hiring-profile archetypes (skill emphasis + weighting), not each company's actual real ATS or hiring criteria - useful for seeing how differently-weighted employers might read the same resume.",
    }


# =============================================================================
# 2. AI Resume Battle
# =============================================================================

def resume_battle(parsed_a, parsed_b, report_a, report_b, label_a="Resume A", label_b="Resume B"):
    skills_a, skills_b = set(parsed_a["skills"]), set(parsed_b["skills"])
    breakdown_a, breakdown_b = report_a["score_breakdown"], report_b["score_breakdown"]

    categories = []

    def add_category(name, val_a, val_b, higher_better=True):
        if val_a == val_b:
            winner = "Tie"
        elif (val_a > val_b) == higher_better:
            winner = label_a
        else:
            winner = label_b
        categories.append({"category": name, "value_a": val_a, "value_b": val_b, "winner": winner})

    add_category("Skills", len(skills_a), len(skills_b))
    add_category("Projects/Experience depth", breakdown_a.get("content_depth", 0), breakdown_b.get("content_depth", 0))
    add_category("Quantified Impact", breakdown_a.get("quantified_impact", 0), breakdown_b.get("quantified_impact", 0))
    add_category("ATS Score", report_a["ats_score"], report_b["ats_score"])

    wins_a = sum(1 for c in categories if c["winner"] == label_a)
    wins_b = sum(1 for c in categories if c["winner"] == label_b)
    overall = label_a if wins_a > wins_b else label_b if wins_b > wins_a else "Tie"

    return {
        "label_a": label_a, "label_b": label_b,
        "categories": categories,
        "wins_a": wins_a, "wins_b": wins_b,
        "overall_winner": overall,
        "skills_only_in_a": sorted(skills_a - skills_b),
        "skills_only_in_b": sorted(skills_b - skills_a),
    }


# =============================================================================
# 3. AI Hidden Talent Detector
# =============================================================================

_TALENT_SIGNALS = {
    "High Creativity": {"categories": ["Design & Product", "Web & Frontend"], "min_hits": 2},
    "Strong Problem Solving": {"categories": ["Data, ML & AI", "Programming Languages"], "min_hits": 3},
    "Leadership Potential": {"skills": ["leadership", "mentoring", "project management", "product management"], "min_hits": 1},
    "Research Ability": {"skills": ["research", "data analysis", "data visualization", "machine learning"], "min_hits": 2},
    "Systems Thinking": {"categories": ["Cloud & DevOps", "Backend & APIs"], "min_hits": 2},
}

_TALENT_TO_ROLE = {
    "High Creativity": [("Product Engineer", 89), ("UI/UX Designer", 85)],
    "Strong Problem Solving": [("AI Engineer", 92), ("Machine Learning Engineer", 90)],
    "Leadership Potential": [("Product Manager", 88), ("Engineering Team Lead", 84)],
    "Research Ability": [("Research Engineer", 86), ("Data Scientist", 87)],
    "Systems Thinking": [("Backend Developer", 88), ("DevOps Engineer", 85)],
}


def hidden_talent_detector(report):
    skills = set(report.get("skills_found", []))
    categorized = _categorize_skills(list(skills))

    detected = []
    for talent, rule in _TALENT_SIGNALS.items():
        hits = 0
        if "categories" in rule:
            hits += sum(len(categorized.get(c, [])) for c in rule["categories"])
        if "skills" in rule:
            hits += len(skills & set(rule["skills"]))
        if hits >= rule["min_hits"]:
            detected.append(talent)

    role_scores = {}
    for talent in detected:
        for role, pct in _TALENT_TO_ROLE.get(talent, []):
            role_scores[role] = max(role_scores.get(role, 0), pct)

    recommended_roles = sorted(role_scores.items(), key=lambda kv: kv[1], reverse=True)[:3]

    return {
        "detected_talents": detected or ["Not enough signal yet - add more projects/skills for a clearer read."],
        "recommended_roles": [{"role": r, "fit_percent": p} for r, p in recommended_roles],
        "note": "Inferred from the mix and breadth of your detected skills, not a psychometric test - use it as a prompt to explore, not a verdict.",
    }


# =============================================================================
# 4. AI Career Score Card
# =============================================================================

def career_scorecard(report):
    breakdown = report.get("score_breakdown", {})
    skills = set(report.get("skills_found", []))
    categorized = _categorize_skills(list(skills))

    technical = round((breakdown.get("skills_coverage", 0) + breakdown.get("structure", 0)) / 2)
    communication = breakdown.get("spelling_grammar", breakdown.get("content_depth", 60))
    leadership = 85 if (skills & {"leadership", "mentoring", "project management"}) else 45
    innovation = min(97, round(len([c for c in categorized.values() if c]) * 16))
    problem_solving = round((len(categorized.get("Data, ML & AI", [])) * 10 + len(categorized.get("Programming Languages", [])) * 8))
    problem_solving = max(20, min(97, problem_solving))
    learning_ability = breakdown.get("repetition", 70)

    dna = {
        "Technical": technical,
        "Communication": communication,
        "Leadership": leadership,
        "Innovation": innovation,
        "Problem Solving": problem_solving,
        "Learning Ability": learning_ability,
    }

    return {
        "career_dna": dna,
        "strongest": max(dna, key=dna.get),
        "weakest": min(dna, key=dna.get),
        "note": "Each dimension is derived from your resume's real structure and skill mix (e.g. Leadership from ownership-language skills, Innovation from skill-category breadth) - a snapshot, not a certified assessment.",
    }


# =============================================================================
# 5. AI Recruiter Psychology
# =============================================================================

def recruiter_psychology(report):
    sections = report.get("sections_detected", {})
    breakdown = report.get("score_breakdown", {})

    looked_at = []
    ignored = []
    if sections.get("skills") or report.get("skills_found"):
        looked_at.append("Skills")
    else:
        ignored.append("Skills (section not clearly detected)")
    if sections.get("experience"):
        looked_at.append("Projects/Experience")
    else:
        ignored.append("Projects/Experience (section not clearly detected)")
    if sections.get("summary"):
        looked_at.append("Summary")
    else:
        ignored.append("Objective/Summary")
    if "references" not in sections:
        ignored.append("References")

    scan_seconds = 6.8

    return {
        "scan_seconds": scan_seconds,
        "looked_at": looked_at,
        "ignored": ignored,
        "structure_score": breakdown.get("structure", 0),
        "tip": "Everything in 'Looked At' should carry your strongest, most specific line - that's what actually gets read in the first pass.",
        "disclaimer": "Based on published resume eye-tracking research (~6-7s initial scans favor Skills/Experience), applied to your resume's own section layout - not a live recording of an actual recruiter.",
    }


# =============================================================================
# 6. AI Resume Evolution
# =============================================================================

def resume_evolution(report):
    breakdown = dict(report.get("score_breakdown", {}))
    current_ats = report.get("ats_score", 0)

    # Same category weights the real ATS score uses (similarity.py). Rather
    # than re-deriving an absolute score by hand (error-prone - it drifted
    # from the real formula in testing), we only ever add the *delta* on
    # top of the real, already-correct current_ats - so this can only ever
    # move the projection up, never produce a nonsensical decrease.
    weights = {"structure": 0.30, "contact_info": 0.13, "skills_coverage": 0.17,
               "content_depth": 0.10, "quantified_impact": 0.15, "spelling_grammar": 0.08, "repetition": 0.07}

    stages = [{"label": "Resume V1 (current)", "ats_score": current_ats, "change": None}]
    cumulative_gain = 0.0

    def apply_improvement(category, new_value, label, change_note):
        nonlocal cumulative_gain
        old_value = breakdown.get(category, 0)
        if new_value <= old_value:
            return
        cumulative_gain += (new_value - old_value) * weights.get(category, 0)
        breakdown[category] = new_value
        stages.append({
            "label": label,
            "ats_score": min(100, round(current_ats + cumulative_gain)),
            "change": change_note,
        })

    if breakdown.get("quantified_impact", 100) < 70:
        apply_improvement("quantified_impact", min(100, breakdown.get("quantified_impact", 0) + 50),
                           "Resume Improved (add metrics to bullets)", "+ quantified impact")
    if breakdown.get("content_depth", 100) < 70:
        apply_improvement("content_depth", min(100, breakdown.get("content_depth", 0) + 25),
                           "Resume Optimized (expand thin sections)", "+ content depth")
    if breakdown.get("repetition", 100) < 80 or breakdown.get("spelling_grammar", 100) < 90:
        apply_improvement("repetition", 100, "Resume Recruiter-Ready (polish pass)", "+ polish")
        apply_improvement("spelling_grammar", 100, "Resume Recruiter-Ready (polish pass)", "+ polish")

    if len(stages) == 1:
        stages.append({"label": "Already Recruiter-Ready", "ats_score": current_ats, "change": "No major gaps detected"})

    return {
        "stages": stages,
        "total_projected_gain": (stages[-1]["ats_score"] or current_ats) - current_ats,
        "disclaimer": "A hypothetical improvement path based on your own report's weakest categories, applied in priority order - not a re-analysis of a rewritten resume. Actually apply the changes and re-run the Analyzer to get your real new score.",
    }


# =============================================================================
# 7. AI Opportunity Radar
# =============================================================================

def opportunity_radar(report):
    breakdown = report.get("score_breakdown", {})
    sections = report.get("sections_detected", {})
    skills = report.get("skills_found", [])

    internship = round((breakdown.get("skills_coverage", 0) + breakdown.get("structure", 0)) / 2)
    hackathons = min(97, round(len(skills) * 4 + (20 if sections.get("projects") else 0)))
    research = round(breakdown.get("content_depth", 0) * 0.6 + (30 if "research" in skills or "data analysis" in skills else 0))
    open_source = min(95, round((25 if "git" in skills or "github" in skills else 0) + len(skills) * 3))
    freelancing = round((breakdown.get("quantified_impact", 0) + breakdown.get("skills_coverage", 0)) / 2)

    radar = {
        "Internships": max(10, min(97, internship)),
        "Hackathons": max(10, min(97, hackathons)),
        "Research": max(10, min(97, research)),
        "Open Source": max(10, min(97, open_source)),
        "Freelancing": max(10, min(97, freelancing)),
    }

    return {
        "radar": radar,
        "top_opportunity": max(radar, key=radar.get),
        "note": "Fit is estimated from your resume's real signals (skill breadth, project presence, GitHub/Git detection, quantified outcomes) for each opportunity type.",
    }


# =============================================================================
# 8. AI Hackathon Partner Finder - honest reframe (see module docstring)
# =============================================================================

def hackathon_partner_finder(report):
    skills = set(report.get("skills_found", []))
    categorized = _categorize_skills(list(skills))
    have_categories = {c for c, hits in categorized.items() if hits}
    all_categories = set(SKILL_CATEGORIES.keys())
    missing_categories = sorted(all_categories - have_categories)

    your_strengths = sorted(have_categories)[:4]
    look_for = missing_categories[:3] or ["A generalist to double down on your existing strengths"]

    return {
        "your_strengths": your_strengths,
        "ideal_teammate_covers": look_for,
        "note": "This app doesn't have a database of other users to match you against, so instead of a fake match, here's the honest version: the skill categories your profile is missing that a strong teammate would ideally cover.",
    }


# =============================================================================
# 9. AI Dream Company Simulator
# =============================================================================

def dream_company_simulator(report, company, target_role=None):
    profile = COMPANY_PROFILES.get(company)
    if not profile:
        return {"error": f"No profile for '{company}'.", "available_companies": sorted(COMPANY_PROFILES.keys())}

    skills = report.get("skills_found", [])
    score, skill_fit, missing = _score_against_profile(report, profile)

    role = target_role or _infer_closest_role(skills)
    role_missing = missing_skills_for_role(skills, role) if role in ROLE_SKILL_MAP else []
    combined_missing = sorted(set(missing) | set(role_missing[:4]))

    plan = build_roadmap(combined_missing, hours_per_week=8) if combined_missing else {"total_estimated_hours": 0}
    weeks_ready = round(plan.get("total_estimated_hours", 0) / 8) if combined_missing else 0
    months_ready = round(weeks_ready / 4.33, 1)

    return {
        "company": company,
        "current_match_percent": score,
        "need": combined_missing or ["You already cover this profile's core emphasis skills."],
        "estimated_ready_months": months_ready,
        "disclaimer": "Based on an illustrative hiring-profile archetype for this company, not confirmed real hiring criteria or an open role.",
    }


# =============================================================================
# 10. AI Recruiter Decision Explanation
# =============================================================================

_CATEGORY_WEIGHT = {
    "structure": 30, "contact_info": 13, "skills_coverage": 17,
    "content_depth": 10, "quantified_impact": 15, "spelling_grammar": 8, "repetition": 7,
}
_CATEGORY_ISSUE_LABEL = {
    "structure": "Missing or incomplete resume sections",
    "contact_info": "Incomplete contact information",
    "skills_coverage": "Too few relevant skills listed",
    "content_depth": "Resume is too thin on detail",
    "quantified_impact": "Weak action verbs / no quantified numbers",
    "spelling_grammar": "Spelling or grammar issues detected",
    "repetition": "Repeated action verbs across bullet points",
}


def recruiter_decision_explanation(report):
    breakdown = report.get("score_breakdown", {})
    ats = report.get("ats_score", 0)

    issues = []
    for cat, score in breakdown.items():
        if score >= 85:
            continue
        weight = _CATEGORY_WEIGHT.get(cat, 10)
        recoverable = round((100 - score) / 100 * weight)
        if recoverable <= 0:
            continue
        issues.append({
            "issue": _CATEGORY_ISSUE_LABEL.get(cat, cat.replace("_", " ")),
            "category": cat,
            "current_score": score,
            "estimated_ats_gain": recoverable,
        })

    issues.sort(key=lambda i: i["estimated_ats_gain"], reverse=True)
    total_gain = sum(i["estimated_ats_gain"] for i in issues)

    verdict = "Likely Interview" if ats >= 75 else "Borderline" if ats >= 55 else "Likely Rejected"

    return {
        "current_verdict": verdict,
        "current_ats_score": ats,
        "issues": issues,
        "estimated_improvement_total": min(total_gain, 100 - ats),
        "note": "Estimated gains are derived from your report's own category weights - fixing the top issue first gives the most points back.",
    }
