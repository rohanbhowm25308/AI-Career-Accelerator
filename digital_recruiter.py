"""
digital_recruiter.py
-----------------------
AI Digital Recruiter: a floating avatar widget that opens with one specific,
real observation instead of a generic "hi" - picks the lowest-scoring
category from the resume's own breakdown and offers to route the person to
the AI Suite tool that actually addresses it.

No name-guessing: resume name-extraction via regex is unreliable enough to
risk getting someone's name wrong, which would undermine trust immediately -
so the greeting stays warm but generic.
"""

_CATEGORY_LABELS = {
    "structure": "your resume's section structure",
    "contact_info": "your contact info completeness",
    "skills_coverage": "how many relevant skills are listed",
    "content_depth": "how much detail your resume gives",
    "quantified_impact": "your project descriptions - they're missing measurable impact",
    "spelling_grammar": "spelling and grammar",
    "repetition": "repeated action verbs across your bullet points",
}

# Where "yes, help me fix it" should route the person in the AI Suite.
_CATEGORY_SUITE_TAB = {
    "skills_coverage": "skill-radar",
    "content_depth": "achievement",
    "quantified_impact": "achievement",
    "repetition": "achievement",
}


def digital_recruiter_message(report):
    breakdown = report.get("score_breakdown", {})
    if not breakdown:
        return {
            "greeting": "Hi! Run the Resume Analyzer first and I'll tell you the single biggest thing to fix.",
            "weakness": None,
            "action": None,
        }

    weakest_key = min(breakdown, key=breakdown.get)
    weakest_score = breakdown[weakest_key]
    weakest_label = _CATEGORY_LABELS.get(weakest_key, weakest_key.replace("_", " "))

    greeting = (
        f"Hi! I analyzed your resume. Your biggest opportunity right now is {weakest_label} "
        f"({weakest_score}%). Want me to help you fix it?"
    )

    suite_tab = _CATEGORY_SUITE_TAB.get(weakest_key)
    action = {
        "label": "Yes, help me fix it",
        "suite_tab": suite_tab,
    } if suite_tab else None

    return {
        "greeting": greeting,
        "weakness": {"category": weakest_key, "score": weakest_score, "label": weakest_label},
        "action": action,
    }
