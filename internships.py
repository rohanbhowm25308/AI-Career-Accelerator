"""
internships.py
----------------
Matches a candidate's detected skills against a curated set of common
internship/early-career tracks and ranks them by a weighted skill overlap.

Each track defines:
  - core_skills:  the handful of skills that really define the track. These
                   are weighted 2x and any gaps here are surfaced as
                   "missing" (actionable).
  - bonus_skills: related tools/frameworks that strengthen a match but
                   aren't strictly required (weighted 1x). Gaps here are
                   NOT reported as missing - having none of them shouldn't
                   read as a blocker.

These are illustrative role *tracks* (title + typical skill set + where to
search), not live job postings - the module doesn't fabricate specific
company openings. Each track links to well-known, general search platforms
so the recommendation is genuinely actionable without pretending to be a
real-time job feed.
"""

import courses as courses_engine

SEARCH_PLATFORMS = [
    {"name": "LinkedIn Jobs", "url": "https://www.linkedin.com/jobs/"},
    {"name": "Internshala", "url": "https://internshala.com/"},
    {"name": "Wellfound (AngelList Talent)", "url": "https://wellfound.com/jobs"},
    {"name": "Handshake", "url": "https://joinhandshake.com/"},
]

INTERNSHIP_TRACKS = [
    {
        "title": "Frontend Engineering Intern",
        "description": "Build and ship user-facing features in a modern web app.",
        "core_skills": ["html", "css", "javascript", "react"],
        "bonus_skills": ["typescript", "tailwind css", "webpack", "vite", "git", "rest api", "redux"],
    },
    {
        "title": "Backend Engineering Intern",
        "description": "Design APIs and data models that power a product's core logic.",
        "core_skills": ["python", "sql", "rest api"],
        "bonus_skills": ["django", "flask", "fastapi", "docker", "redis", "postgresql", "system design", "git"],
    },
    {
        "title": "Full-Stack Software Intern",
        "description": "Work across the stack, from UI to database, on real product features.",
        "core_skills": ["javascript", "react", "sql"],
        "bonus_skills": ["node.js", "express", "docker", "git", "rest api", "mongodb", "typescript"],
    },
    {
        "title": "Data Analyst Intern",
        "description": "Turn raw data into dashboards and insights that inform decisions.",
        "core_skills": ["sql", "excel", "data analysis"],
        "bonus_skills": ["python", "pandas", "data visualization", "tableau", "power bi"],
    },
    {
        "title": "Machine Learning / AI Intern",
        "description": "Prototype and evaluate ML/AI models on real datasets.",
        "core_skills": ["python", "machine learning"],
        "bonus_skills": [
            "pandas", "numpy", "scikit-learn", "deep learning", "tensorflow", "pytorch",
            "keras", "opencv", "nltk", "spacy", "artificial intelligence", "data science",
            "computer vision", "natural language processing",
        ],
    },
    {
        "title": "DevOps / Cloud Intern",
        "description": "Automate deployments and keep infrastructure reliable.",
        "core_skills": ["linux", "docker", "git"],
        "bonus_skills": ["aws", "kubernetes", "ci/cd", "ansible", "terraform", "bash", "azure", "gcp"],
    },
    {
        "title": "Mobile App Development Intern",
        "description": "Build features for an iOS or Android app used by real users.",
        "core_skills": ["git", "rest api"],
        "bonus_skills": ["kotlin", "swift", "flutter", "react native", "android development", "ios development"],
    },
    {
        "title": "UI/UX Design Intern",
        "description": "Design and test interfaces that make a product easier to use.",
        "core_skills": ["figma", "ui design", "ux design"],
        "bonus_skills": ["wireframing", "prototyping", "adobe xd", "sketch", "research"],
    },
    {
        "title": "Product Management Intern",
        "description": "Help define what gets built next and why, working across teams.",
        "core_skills": ["product management", "communication"],
        "bonus_skills": ["agile", "scrum", "jira", "data analysis", "presentation skills", "research"],
    },
    {
        "title": "Cybersecurity Intern",
        "description": "Support security reviews, monitoring, and vulnerability triage.",
        "core_skills": ["network security", "cybersecurity"],
        "bonus_skills": ["linux", "python", "cryptography", "penetration testing"],
    },
    {
        "title": "QA / Test Engineering Intern",
        "description": "Build automated test suites that catch bugs before users do.",
        "core_skills": ["unit testing", "git"],
        "bonus_skills": ["selenium", "cypress", "pytest", "jest", "api testing"],
    },
    {
        "title": "Data Engineering Intern",
        "description": "Build the pipelines that move and clean data for the rest of the team.",
        "core_skills": ["python", "sql"],
        "bonus_skills": ["spark", "airflow", "docker", "aws", "hadoop", "dbt", "snowflake"],
    },
]

CORE_WEIGHT = 2
BONUS_WEIGHT = 1


def match_internships(skills, limit=6):
    candidate = set(s.lower() for s in skills)
    results = []

    for track in INTERNSHIP_TRACKS:
        core = set(track["core_skills"])
        bonus = set(track["bonus_skills"])

        matched_core = candidate & core
        matched_bonus = candidate & bonus
        missing_core = sorted(core - candidate)

        total_weight = len(core) * CORE_WEIGHT + len(bonus) * BONUS_WEIGHT
        earned_weight = len(matched_core) * CORE_WEIGHT + len(matched_bonus) * BONUS_WEIGHT
        match_pct = round(earned_weight / total_weight * 100) if total_weight else 0

        results.append({
            "title": track["title"],
            "description": track["description"],
            "match_percent": min(match_pct, 100),
            "matched_skills": sorted(matched_core | matched_bonus),
            "missing_skills": missing_core,
            "recommended_courses": courses_engine.courses_for_skills(
                list(core | bonus), limit_domains=1, limit_per_domain=3
            ),
        })

    results.sort(key=lambda r: r["match_percent"], reverse=True)
    return {
        "tracks": results[:limit],
        "search_platforms": SEARCH_PLATFORMS,
    }