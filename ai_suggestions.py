"""
ai_suggestions.py
--------------------
Generates human-readable improvement suggestions for a resume.

Runs fully offline using rules driven by the parsed resume + scoring data,
so the project works out of the box with no API key. If ANTHROPIC_API_KEY is
set in the environment, `generate_suggestions(..., use_llm=True)` will ask
Claude for sharper, more tailored suggestions and silently fall back to the
rule-based list if the call fails for any reason (missing key, no network,
rate limit, etc.) -- the demo never breaks because of a missing key.
"""

import os


# ---------------------------------------------------------------------------
# Rule-based suggestions (always available, zero dependencies)
# ---------------------------------------------------------------------------

def _rule_based_suggestions(parsed_resume, ats_score, match_score=None, missing_skills=None,
                             breakdown=None, jd_skills_detected=None):
    """Builds a prioritized suggestion list: each candidate suggestion is
    tagged with a priority (higher = fix this first) based on how much it's
    actually costing the resume, so the sharpest, most useful advice surfaces
    at the top instead of a fixed checklist order."""
    sections = parsed_resume["sections"]
    contact = parsed_resume["contact_info"]
    breakdown = breakdown or {}
    candidates = []  # list of (priority, text)

    def add(priority, text):
        candidates.append((priority, text))

    # --- Structure (weighted by how much of the 40-pt structure score is missing) ---
    missing_sections = [s for s in ["summary", "experience", "skills", "projects", "education"] if not sections.get(s)]
    section_copy = {
        "summary": "Add a short professional summary at the top so recruiters immediately know who you are and what you bring.",
        "experience": "Add a clearly labeled 'Experience' section with your work history, even if it's internships or freelance work.",
        "skills": "Add a dedicated 'Skills' section so ATS systems can reliably pick up your technical and soft skills.",
        "projects": "Add a 'Projects' section - it's one of the highest-signal sections for early-career candidates.",
        "education": "Add an 'Education' section with your degree(s) and institution(s).",
    }
    for s in missing_sections:
        add(90, section_copy[s])

    # --- Contact info ---
    if not contact.get("email"):
        add(85, "Add a professional email address so recruiters can reach you.")
    if not contact.get("linkedin") and not contact.get("github"):
        add(60, "Add a link to your LinkedIn or GitHub profile to give recruiters more context on your work.")
    elif not contact.get("phone"):
        add(20, "Consider adding a phone number - some recruiters still prefer a quick call to schedule interviews.")

    # --- Content depth ---
    word_count = parsed_resume["word_count"]
    if word_count < 200:
        add(80, "Your resume is quite short - add more detail about your responsibilities and measurable achievements in each role.")
    elif word_count > 1200:
        add(45, "Your resume is on the longer side - trim it to the most relevant, impactful points (ideally 1-2 pages).")

    # --- Skills coverage ---
    skill_count = len(parsed_resume["skills"])
    if skill_count < 5:
        add(70, "Only a few recognizable skills were detected - list the specific tools, languages and frameworks you're proficient in.")
    elif skill_count < 9:
        add(30, "Your skills list is solid - adding 2-3 more specific tools or frameworks would strengthen keyword coverage further.")

    # --- Job description driven ---
    if jd_skills_detected == 0 and missing_skills is not None:
        add(55, "We couldn't find clear skill keywords in the pasted job description - paste the full posting (not just a title) for a sharper gap analysis.")
    elif missing_skills:
        top_missing = ", ".join(missing_skills[:6])
        add(95, f"The job description calls for skills not found on your resume: {top_missing}. Add these if you genuinely have experience with them.")

    if match_score is not None:
        if match_score < 40:
            add(65, "Your overall match with this job description is low - mirror more of the JD's key terms and responsibilities (where truthful) to improve keyword alignment.")
        elif match_score >= 75:
            add(15, "Great alignment with this job description - your resume already reflects most of the key requirements.")

    # --- Quantified impact (are bullets backed by real numbers?) ---
    qi = breakdown.get("quantified_impact")
    if qi is not None:
        if qi < 40:
            add(88, "Almost none of your bullet points include a measurable outcome - add a number, %, or scale to at least one bullet per role (e.g. 'cut processing time by 20%', 'supported 50+ users').")
        elif qi < 75:
            add(50, "Some bullet points are missing a measurable outcome - add a number or % to the rest so every line shows concrete impact, not just duties.")

    # --- Always-useful writing tips, but only fill in if there's room ---
    generic_tips = [
        (25, "Use strong action verbs (led, built, optimized, launched) at the start of each bullet point."),
        (20, "Tailor your resume for each job application to match the specific role and keywords."),
    ]
    candidates.extend(generic_tips)

    candidates.sort(key=lambda item: item[0], reverse=True)

    # De-duplicate while preserving priority order, cap to a focused top 6
    seen, ordered = set(), []
    for _, text in candidates:
        if text not in seen:
            seen.add(text)
            ordered.append(text)
        if len(ordered) >= 6:
            break

    if not ordered:
        ordered.append("Your resume looks solid across the board - nice work!")

    return ordered


# ---------------------------------------------------------------------------
# Optional: real LLM-backed suggestions via the Anthropic API
# ---------------------------------------------------------------------------

def _call_claude_for_suggestions(resume_text, jd_text=None):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            "You are a resume coach. Give 5 short, specific, actionable bullet "
            "point suggestions to improve this resume"
            + (" for the following job description." if jd_text else ".")
            + f"\n\nRESUME:\n{resume_text[:4000]}\n"
        )
        if jd_text:
            prompt += f"\nJOB DESCRIPTION:\n{jd_text[:2000]}\n"
        prompt += "\nReturn ONLY the 5 suggestions, one per line, no numbering or preamble."

        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        lines = [l.strip("-•* ").strip() for l in text.split("\n") if l.strip()]
        return lines or None
    except Exception:
        # Any failure (bad key, network, rate limit) -> caller falls back
        # to the offline rule-based suggestions. The demo never breaks.
        return None


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def generate_suggestions(parsed_resume, ats_score, match_score=None, missing_skills=None,
                          use_llm=False, jd_text=None, breakdown=None, jd_skills_detected=None):
    """Main entrypoint used by app.py. Tries Claude first when use_llm=True and
    a key is available, otherwise (and always as a fallback) uses the offline
    rule-based engine."""
    if use_llm:
        llm_suggestions = _call_claude_for_suggestions(parsed_resume.get("raw_text", ""), jd_text)
        if llm_suggestions:
            return llm_suggestions

    return _rule_based_suggestions(
        parsed_resume, ats_score, match_score, missing_skills,
        breakdown=breakdown, jd_skills_detected=jd_skills_detected,
    )
