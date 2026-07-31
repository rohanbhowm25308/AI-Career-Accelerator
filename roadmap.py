"""
roadmap.py
-----------
Turns a list of missing skills into a prioritized, phased learning roadmap.

Two ways to get missing skills into this module:
  1. From a resume <-> job description match (see similarity.find_missing_skills)
  2. From a target role picked from ROLE_SKILL_MAP, compared against the
     skills already detected on the resume.

Nothing here calls an external API - it's a curated, offline knowledge base,
so the roadmap always renders instantly in a demo.
"""

import courses as courses_engine

# ---------------------------------------------------------------------------
# Target role -> core skill profile (used when the user picks a role instead
# of pasting a job description)
# ---------------------------------------------------------------------------

ROLE_SKILL_MAP = {
    "Frontend Developer": [
        "html", "css", "javascript", "react", "typescript", "tailwind css",
        "webpack", "rest api", "git",
    ],
    "Backend Developer": [
        "python", "sql", "rest api", "django", "flask", "postgresql",
        "docker", "redis", "git", "system design",
    ],
    "Full Stack Developer": [
        "javascript", "react", "node.js", "sql", "rest api", "docker",
        "git", "mongodb", "system design",
    ],
    "Data Analyst": [
        "sql", "excel", "python", "pandas", "data visualization", "tableau",
        "power bi", "data analysis",
    ],
    "Data Scientist": [
        "python", "pandas", "numpy", "machine learning", "scikit-learn",
        "sql", "data visualization", "deep learning",
    ],
    "Machine Learning Engineer": [
        "python", "machine learning", "deep learning", "tensorflow", "pytorch",
        "sql", "docker", "system design", "data structures",
    ],
    "DevOps Engineer": [
        "linux", "docker", "kubernetes", "terraform", "aws", "ci/cd",
        "ansible", "bash", "git",
    ],
    "Mobile Developer": [
        "kotlin", "swift", "flutter", "react native", "android development",
        "ios development", "rest api", "git",
    ],
    "UI/UX Designer": [
        "figma", "adobe xd", "wireframing", "prototyping", "ui design",
        "ux design", "research",
    ],
    "Product Manager": [
        "product management", "agile", "scrum", "jira", "data analysis",
        "communication", "presentation skills", "research",
    ],
    "Cybersecurity Analyst": [
        "network security", "penetration testing", "cybersecurity",
        "cryptography", "linux", "python",
    ],
}


# ---------------------------------------------------------------------------
# Curated resource hubs per skill. Kept to canonical, stable, well-known
# sites (official docs / freeCodeCamp / MDN) rather than specific course
# URLs that could go stale.
# ---------------------------------------------------------------------------

_DOCS = "official documentation"

LEARNING_RESOURCES = {
    "python": {"level": "Foundation", "hours": 25, "hubs": ["docs.python.org", "freeCodeCamp Python curriculum", "Real Python"]},
    "javascript": {"level": "Foundation", "hours": 25, "hubs": ["developer.mozilla.org (MDN)", "freeCodeCamp JavaScript curriculum", "javascript.info"]},
    "typescript": {"level": "Intermediate", "hours": 15, "hubs": ["typescriptlang.org/docs", "freeCodeCamp"]},
    "html": {"level": "Foundation", "hours": 8, "hubs": ["developer.mozilla.org (MDN)", "freeCodeCamp Responsive Web Design"]},
    "css": {"level": "Foundation", "hours": 12, "hubs": ["developer.mozilla.org (MDN)", "freeCodeCamp Responsive Web Design", "CSS-Tricks"]},
    "react": {"level": "Intermediate", "hours": 20, "hubs": ["react.dev", "freeCodeCamp"]},
    "node.js": {"level": "Intermediate", "hours": 18, "hubs": ["nodejs.org/docs", "freeCodeCamp Back End curriculum"]},
    "sql": {"level": "Foundation", "hours": 15, "hubs": ["freeCodeCamp Relational Database curriculum", "Mode SQL Tutorial", "PostgreSQL docs"]},
    "django": {"level": "Intermediate", "hours": 20, "hubs": ["docs.djangoproject.com", "Django Girls Tutorial"]},
    "flask": {"level": "Intermediate", "hours": 12, "hubs": ["flask.palletsprojects.com", _DOCS]},
    "git": {"level": "Foundation", "hours": 6, "hubs": ["git-scm.com/doc", "GitHub Skills"]},
    "docker": {"level": "Intermediate", "hours": 12, "hubs": ["docs.docker.com", "Docker Curriculum"]},
    "kubernetes": {"level": "Advanced", "hours": 25, "hubs": ["kubernetes.io/docs", "KodeKloud free tier"]},
    "aws": {"level": "Intermediate", "hours": 25, "hubs": ["aws.amazon.com/training", "AWS Skill Builder (free tier)"]},
    "machine learning": {"level": "Advanced", "hours": 40, "hubs": ["scikit-learn.org docs", "Google Machine Learning Crash Course", "Andrew Ng's Coursera ML course"]},
    "deep learning": {"level": "Advanced", "hours": 40, "hubs": ["pytorch.org tutorials", "tensorflow.org tutorials", "DeepLearning.AI"]},
    "pandas": {"level": "Intermediate", "hours": 10, "hubs": ["pandas.pydata.org docs", "Kaggle Learn: Pandas"]},
    "numpy": {"level": "Foundation", "hours": 8, "hubs": ["numpy.org/doc", "Kaggle Learn"]},
    "tensorflow": {"level": "Advanced", "hours": 25, "hubs": ["tensorflow.org tutorials", "DeepLearning.AI TensorFlow Specialization"]},
    "pytorch": {"level": "Advanced", "hours": 25, "hubs": ["pytorch.org tutorials", "fast.ai course"]},
    "data analysis": {"level": "Foundation", "hours": 15, "hubs": ["Kaggle Learn", "freeCodeCamp Data Analysis with Python"]},
    "data visualization": {"level": "Intermediate", "hours": 10, "hubs": ["Kaggle Learn: Data Visualization", "matplotlib.org tutorials"]},
    "tableau": {"level": "Intermediate", "hours": 12, "hubs": ["Tableau Public training videos", "Tableau official docs"]},
    "power bi": {"level": "Intermediate", "hours": 12, "hubs": ["Microsoft Learn: Power BI", "Power BI official docs"]},
    "figma": {"level": "Foundation", "hours": 8, "hubs": ["Figma official YouTube channel", "help.figma.com"]},
    "ui design": {"level": "Foundation", "hours": 15, "hubs": ["Laws of UX", "Google UX Design Certificate (Coursera)"]},
    "ux design": {"level": "Foundation", "hours": 15, "hubs": ["Nielsen Norman Group articles", "Google UX Design Certificate (Coursera)"]},
    "agile": {"level": "Foundation", "hours": 6, "hubs": ["Atlassian Agile Coach", "Scrum.org resources"]},
    "scrum": {"level": "Foundation", "hours": 6, "hubs": ["Scrum.org Learning Series", "Atlassian Agile Coach"]},
    "system design": {"level": "Advanced", "hours": 25, "hubs": ["github.com/donnemartin/system-design-primer", "ByteByteGo free content"]},
    "data structures": {"level": "Foundation", "hours": 20, "hubs": ["freeCodeCamp: Data Structures", "GeeksforGeeks"]},
    "algorithms": {"level": "Intermediate", "hours": 25, "hubs": ["freeCodeCamp: Algorithms", "LeetCode practice"]},
    "rest api": {"level": "Foundation", "hours": 8, "hubs": ["MDN: HTTP", "freeCodeCamp APIs curriculum"]},
    "linux": {"level": "Foundation", "hours": 10, "hubs": ["Linux Journey", "OverTheWire Bandit (hands-on)"]},
    "terraform": {"level": "Advanced", "hours": 15, "hubs": ["developer.hashicorp.com/terraform", "HashiCorp Learn"]},
    "kotlin": {"level": "Intermediate", "hours": 20, "hubs": ["kotlinlang.org docs", "Android Developers: Kotlin Bootcamp"]},
    "swift": {"level": "Intermediate", "hours": 20, "hubs": ["swift.org documentation", "Apple's Swift Playgrounds"]},
    "flutter": {"level": "Intermediate", "hours": 20, "hubs": ["docs.flutter.dev", "Flutter YouTube channel"]},
    "cybersecurity": {"level": "Advanced", "hours": 30, "hubs": ["TryHackMe free rooms", "OWASP resources"]},
    "network security": {"level": "Advanced", "hours": 25, "hubs": ["TryHackMe free rooms", "Cisco Networking Academy"]},
    "product management": {"level": "Foundation", "hours": 15, "hubs": ["Product School free resources", "Reforge blog"]},
}


def _resource_for(skill):
    return LEARNING_RESOURCES.get(skill, {
        "level": "Foundation",
        "hours": 10,
        "hubs": [f"official {skill} documentation", "freeCodeCamp / YouTube crash course search"],
    })


_LEVEL_ORDER = {"Foundation": 0, "Intermediate": 1, "Advanced": 2}


def build_roadmap(missing_skills, hours_per_week=8):
    """missing_skills: ordered list[str]. Returns a phased roadmap dict."""
    items = []
    for skill in missing_skills:
        res = _resource_for(skill)
        items.append({
            "skill": skill,
            "level": res["level"],
            "estimated_hours": res["hours"],
            "resources": res["hubs"],
        })

    items.sort(key=lambda i: _LEVEL_ORDER.get(i["level"], 1))

    phases = {"Foundation": [], "Intermediate": [], "Advanced": []}
    for item in items:
        phases[item["level"]].append(item)

    total_hours = sum(i["estimated_hours"] for i in items)
    weeks = max(1, round(total_hours / max(hours_per_week, 1)))

    recommended_courses = courses_engine.courses_for_skills(missing_skills) if missing_skills else None

    return {
        "phases": [
            {"name": name, "skills": phases[name]}
            for name in ["Foundation", "Intermediate", "Advanced"]
            if phases[name]
        ],
        "total_skills": len(items),
        "total_estimated_hours": total_hours,
        "estimated_weeks": weeks,
        "hours_per_week": hours_per_week,
        "recommended_courses": recommended_courses,
    }


def missing_skills_for_role(current_skills, target_role):
    role_skills = ROLE_SKILL_MAP.get(target_role, [])
    current = set(current_skills)
    return [s for s in role_skills if s not in current]


def available_roles():
    return sorted(ROLE_SKILL_MAP.keys())