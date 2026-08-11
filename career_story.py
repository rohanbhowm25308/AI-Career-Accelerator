"""
career_story.py
------------------
AI Career Story Generator: turns the resume analysis into a short narrative
("You started with X... then built Y... next chapter: become a Z") instead
of another chart. Same convention as advanced_features.py: a deterministic,
data-grounded template by default, with an optional Claude-authored version
if ANTHROPIC_API_KEY is set - falling back cleanly if that call fails.

Every fact in the story is pulled directly from the resume report; nothing
about the candidate's actual history is invented.
"""

from advanced_features import (
    _categorize_skills, _infer_closest_role, _seniority_from_report,
    _llm_enabled, _call_claude,
)
from roadmap import ROLE_SKILL_MAP, missing_skills_for_role


def _opening_line(categories, stage):
    ranked = sorted(categories.items(), key=lambda kv: len(kv[1]), reverse=True)
    top_category, top_skills = next(((c, s) for c, s in ranked if s), (None, []))
    if not top_category:
        return f"Your resume is just getting started at the {stage} stage - the foundation is still being built."
    return (
        f"Your journey shows a foundation in {top_category.lower()}, starting with "
        f"{', '.join(top_skills[:3])}."
    )


def _middle_line(report, categories):
    sections = report.get("sections_detected", {})
    breakdown = report.get("score_breakdown", {})
    parts = []

    if sections.get("projects") or sections.get("experience"):
        secondary = [c for c, s in categories.items() if s][1:3]
        if secondary:
            parts.append(f"From there, you branched into {', '.join(s.lower() for s in secondary)}, turning theory into built projects.")
        else:
            parts.append("From there, you moved from learning into building - real projects, not just tutorials.")
    else:
        parts.append("The next chapter still needs a Projects or Experience section - that's where a story becomes provable.")

    qi = breakdown.get("quantified_impact", 0)
    if qi >= 60:
        parts.append("You've also started backing that work with real numbers, which is exactly what makes a resume convincing.")
    elif qi > 0:
        parts.append("A few of those projects already have measurable outcomes attached - worth doing for the rest too.")

    return " ".join(parts)


def _next_chapter_line(report, target_role=None):
    skills = report.get("skills_found", [])
    role = target_role or _infer_closest_role(skills)
    role_skills = ROLE_SKILL_MAP.get(role, [])
    have = set(skills)
    match_pct = round(len(have & set(role_skills)) / len(role_skills) * 100) if role_skills else 0
    missing = missing_skills_for_role(skills, role) if role in ROLE_SKILL_MAP else []

    if match_pct >= 75:
        return f"The next chapter is already within reach: you're a {match_pct}% skills match for {role} - this is mostly an interview-readiness story now, not a learning one."
    gap_note = f" by adding {', '.join(missing[:3])}" if missing else ""
    return f"The recommended next chapter: {role}. You're already a {match_pct}% skills match - closing the rest{gap_note} is the plot for what comes next."


def generate_career_story(report, target_role=None):
    skills = report.get("skills_found", [])
    categories = _categorize_skills(skills)
    stage = _seniority_from_report(report)

    if _llm_enabled():
        prompt = (
            "Write a short, warm, 3-4 sentence 'career story' narrative for a candidate, in second person "
            "('You started...'), based ONLY on this real data - do not invent employers, job titles, or "
            f"achievements they haven't shown: current stage = {stage}; skills detected = {', '.join(skills[:15]) or 'very few'}; "
            f"target next role = {target_role or _infer_closest_role(skills)}. End with one sentence naming the "
            "recommended next chapter/role."
        )
        llm_text = _call_claude(prompt, max_tokens=220)
        if llm_text:
            return {"story": llm_text.strip(), "used_llm": True, "stage": stage}

    story = " ".join([
        _opening_line(categories, stage),
        _middle_line(report, categories),
        _next_chapter_line(report, target_role),
    ])

    return {"story": story, "used_llm": False, "stage": stage}
