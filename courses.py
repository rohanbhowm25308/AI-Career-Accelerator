"""
courses.py
-----------
A curated, offline course catalog spanning the major tech career domains -
AI & Machine Learning, Cloud Computing, Cybersecurity, Web Development,
Data Science & Analytics, DevOps & Infrastructure, Mobile Development,
UI/UX Design, Product Management, and Blockchain & Web3.

This is deliberately separate from roadmap.py's per-skill LEARNING_RESOURCES
(which drives the phased Foundation/Intermediate/Advanced skill roadmap).
courses.py instead answers a slightly different question: "what broader
courses/certificates should I look at for this domain or these skills?" -
used to surface course recommendations inside the Roadmap, the Internship
Track matches, and a dedicated Course Explorer in the AI Suite.

Nothing here calls an external API - like the rest of the project, it's a
curated, offline knowledge base of well-known, stable providers (Coursera,
edX, Google/Microsoft/AWS official learning platforms, freeCodeCamp, etc.)
so recommendations never go stale or require network access to render.
"""

COURSE_CATALOG = {
    "AI & Machine Learning": [
        {"title": "Machine Learning Specialization", "provider": "Coursera (DeepLearning.AI / Stanford)", "level": "Intermediate", "hours": 60, "url": "https://www.coursera.org/specializations/machine-learning-introduction"},
        {"title": "Deep Learning Specialization", "provider": "Coursera (DeepLearning.AI)", "level": "Advanced", "hours": 80, "url": "https://www.coursera.org/specializations/deep-learning"},
        {"title": "CS50's Introduction to AI with Python", "provider": "edX (Harvard)", "level": "Intermediate", "hours": 50, "url": "https://cs50.harvard.edu/ai/"},
        {"title": "Practical Deep Learning for Coders", "provider": "fast.ai", "level": "Advanced", "hours": 40, "url": "https://course.fast.ai/"},
        {"title": "Natural Language Processing Specialization", "provider": "Coursera (DeepLearning.AI)", "level": "Advanced", "hours": 50, "url": "https://www.coursera.org/specializations/natural-language-processing"},
        {"title": "Generative AI for Everyone", "provider": "Coursera (DeepLearning.AI)", "level": "Foundation", "hours": 6, "url": "https://www.coursera.org/learn/generative-ai-for-everyone"},
    ],
    "Cloud Computing": [
        {"title": "AWS Cloud Practitioner Essentials", "provider": "AWS Skill Builder", "level": "Foundation", "hours": 20, "url": "https://skillbuilder.aws/"},
        {"title": "Microsoft Azure Fundamentals (AZ-900)", "provider": "Microsoft Learn", "level": "Foundation", "hours": 15, "url": "https://learn.microsoft.com/training/courses/az-900t00"},
        {"title": "Google Cloud Digital Leader", "provider": "Google Cloud Skills Boost", "level": "Foundation", "hours": 15, "url": "https://www.cloudskillsboost.google/"},
        {"title": "Kubernetes for Developers", "provider": "Linux Foundation", "level": "Advanced", "hours": 30, "url": "https://training.linuxfoundation.org/"},
        {"title": "HashiCorp Certified: Terraform Associate", "provider": "HashiCorp Learn", "level": "Intermediate", "hours": 20, "url": "https://developer.hashicorp.com/terraform/tutorials/certification-associate-tutorials"},
    ],
    "Cybersecurity": [
        {"title": "Introduction to Cybersecurity", "provider": "Cisco Networking Academy", "level": "Foundation", "hours": 15, "url": "https://www.netacad.com/courses/cybersecurity"},
        {"title": "Google Cybersecurity Certificate", "provider": "Coursera (Google)", "level": "Foundation", "hours": 40, "url": "https://www.coursera.org/professional-certificates/google-cybersecurity"},
        {"title": "Practical Ethical Hacking", "provider": "TryHackMe", "level": "Intermediate", "hours": 25, "url": "https://tryhackme.com/"},
        {"title": "OWASP Top 10 Deep Dive", "provider": "OWASP Foundation", "level": "Advanced", "hours": 15, "url": "https://owasp.org/www-project-top-ten/"},
        {"title": "Network Security Fundamentals", "provider": "Cisco Networking Academy", "level": "Intermediate", "hours": 20, "url": "https://www.netacad.com/courses/networking"},
    ],
    "Web Development": [
        {"title": "Responsive Web Design Certification", "provider": "freeCodeCamp", "level": "Foundation", "hours": 25, "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/"},
        {"title": "JavaScript Algorithms and Data Structures", "provider": "freeCodeCamp", "level": "Foundation", "hours": 30, "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"},
        {"title": "The Complete React Developer Course", "provider": "react.dev tutorials", "level": "Intermediate", "hours": 25, "url": "https://react.dev/learn"},
        {"title": "Full Stack Open", "provider": "University of Helsinki", "level": "Advanced", "hours": 60, "url": "https://fullstackopen.com/en/"},
        {"title": "Meta Front-End Developer Certificate", "provider": "Coursera (Meta)", "level": "Intermediate", "hours": 35, "url": "https://www.coursera.org/professional-certificates/meta-front-end-developer"},
    ],
    "Data Science & Analytics": [
        {"title": "Google Data Analytics Certificate", "provider": "Coursera (Google)", "level": "Foundation", "hours": 40, "url": "https://www.coursera.org/professional-certificates/google-data-analytics"},
        {"title": "Data Analysis with Python", "provider": "freeCodeCamp", "level": "Intermediate", "hours": 20, "url": "https://www.freecodecamp.org/learn/data-analysis-with-python/"},
        {"title": "IBM Data Science Professional Certificate", "provider": "Coursera (IBM)", "level": "Intermediate", "hours": 50, "url": "https://www.coursera.org/professional-certificates/ibm-data-science"},
        {"title": "Kaggle Learn micro-courses", "provider": "Kaggle", "level": "Foundation", "hours": 15, "url": "https://www.kaggle.com/learn"},
        {"title": "Tableau Public training", "provider": "Tableau", "level": "Intermediate", "hours": 12, "url": "https://public.tableau.com/en-us/s/resources"},
    ],
    "DevOps & Infrastructure": [
        {"title": "Docker & Kubernetes: The Complete Guide", "provider": "Docker official curriculum", "level": "Intermediate", "hours": 25, "url": "https://docs.docker.com/get-started/"},
        {"title": "IBM DevOps and Software Engineering Certificate", "provider": "Coursera (IBM)", "level": "Intermediate", "hours": 45, "url": "https://www.coursera.org/professional-certificates/devops-and-software-engineering"},
        {"title": "Linux Journey", "provider": "linuxjourney.com", "level": "Foundation", "hours": 15, "url": "https://linuxjourney.com/"},
        {"title": "CI/CD with GitHub Actions", "provider": "GitHub Skills", "level": "Intermediate", "hours": 10, "url": "https://skills.github.com/"},
    ],
    "Mobile Development": [
        {"title": "Android Basics with Compose", "provider": "Android Developers", "level": "Foundation", "hours": 25, "url": "https://developer.android.com/courses"},
        {"title": "Flutter Development Bootcamp", "provider": "docs.flutter.dev", "level": "Intermediate", "hours": 30, "url": "https://docs.flutter.dev/get-started/codelab"},
        {"title": "Meta iOS Developer Certificate", "provider": "Coursera (Meta)", "level": "Intermediate", "hours": 35, "url": "https://www.coursera.org/professional-certificates/meta-ios-developer"},
        {"title": "Kotlin Bootcamp for Programmers", "provider": "Android Developers", "level": "Foundation", "hours": 20, "url": "https://developer.android.com/courses/kotlin-bootcamp/overview"},
    ],
    "UI/UX Design": [
        {"title": "Google UX Design Professional Certificate", "provider": "Coursera (Google)", "level": "Foundation", "hours": 40, "url": "https://www.coursera.org/professional-certificates/google-ux-design"},
        {"title": "Laws of UX", "provider": "lawsofux.com", "level": "Foundation", "hours": 5, "url": "https://lawsofux.com/"},
        {"title": "Figma for Beginners", "provider": "Figma official channel", "level": "Foundation", "hours": 8, "url": "https://help.figma.com/hc/en-us"},
        {"title": "Nielsen Norman Group UX Certification", "provider": "NN/g", "level": "Advanced", "hours": 30, "url": "https://www.nngroup.com/ux-certification/"},
    ],
    "Product Management": [
        {"title": "Google Project Management Certificate", "provider": "Coursera (Google)", "level": "Foundation", "hours": 40, "url": "https://www.coursera.org/professional-certificates/google-project-management"},
        {"title": "Product School Free Resources", "provider": "Product School", "level": "Foundation", "hours": 10, "url": "https://productschool.com/free-product-management-resources"},
        {"title": "Reforge Blog & Guides", "provider": "Reforge", "level": "Intermediate", "hours": 15, "url": "https://www.reforge.com/blog"},
        {"title": "Scrum.org Learning Series", "provider": "Scrum.org", "level": "Foundation", "hours": 10, "url": "https://www.scrum.org/resources"},
    ],
    "Blockchain & Web3": [
        {"title": "Blockchain Basics", "provider": "Coursera (University at Buffalo)", "level": "Foundation", "hours": 15, "url": "https://www.coursera.org/learn/blockchain-basics"},
        {"title": "CryptoZombies - Solidity Tutorial", "provider": "cryptozombies.io", "level": "Intermediate", "hours": 20, "url": "https://cryptozombies.io/"},
        {"title": "Ethereum Developer Docs", "provider": "ethereum.org", "level": "Advanced", "hours": 25, "url": "https://ethereum.org/en/developers/docs/"},
    ],
}

# Maps skill keywords (lowercase, matching resume_parser's detected skill
# strings) to the course-catalog domain(s) they signal interest/gaps in.
DOMAIN_SKILL_KEYWORDS = {
    "AI & Machine Learning": {
        "python", "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "keras", "nltk", "spacy", "opencv", "artificial intelligence",
        "ai", "ml", "computer vision", "natural language processing", "nlp",
        "data science", "generative ai", "llm", "mlops",
    },
    "Cloud Computing": {
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "ci/cd", "firebase",
    },
    "Cybersecurity": {
        "cybersecurity", "network security", "penetration testing", "cryptography",
        "oauth", "jwt",
    },
    "Web Development": {
        "html", "css", "javascript", "typescript", "react", "vue", "angular",
        "node.js", "next.js", "tailwind css", "bootstrap", "material ui", "redux",
        "webpack", "vite", "sass", "express", "graphql", "rest api", "webrtc",
        "websockets", "grpc",
    },
    "Data Science & Analytics": {
        "sql", "nosql", "excel", "data analysis", "data visualization", "tableau",
        "power bi", "pandas", "numpy", "r", "r studio", "matlab", "data engineering",
        "spark", "hadoop", "airflow", "dbt", "snowflake",
    },
    "DevOps & Infrastructure": {
        "linux", "bash", "powershell", "docker", "kubernetes", "terraform",
        "ansible", "jenkins", "ci/cd", "system design", "microservices",
    },
    "Mobile Development": {
        "kotlin", "swift", "flutter", "react native", "android development",
        "ios development", "unity", "game development",
    },
    "UI/UX Design": {
        "figma", "adobe xd", "sketch", "ui design", "ux design", "wireframing",
        "prototyping",
    },
    "Product Management": {
        "product management", "project management", "agile", "scrum", "kanban",
        "jira", "confluence", "presentation skills", "public speaking",
        "communication", "leadership",
    },
    "Blockchain & Web3": {
        "blockchain", "solidity",
    },
}


def all_courses():
    """Returns the full, unfiltered course catalog grouped by domain."""
    return {"domains": sorted(COURSE_CATALOG.keys()), "catalog": COURSE_CATALOG}


def courses_for_domain(domain):
    return COURSE_CATALOG.get(domain, [])


def domains_for_skills(skills, limit=3):
    """Ranks catalog domains by overlap with the given skills list."""
    skills_set = set(s.lower() for s in skills)
    scored = []
    for domain, keywords in DOMAIN_SKILL_KEYWORDS.items():
        overlap = len(skills_set & keywords)
        if overlap > 0:
            scored.append((domain, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [d for d, _ in scored[:limit]]


def courses_for_skills(skills, limit_domains=3, limit_per_domain=3):
    """
    Recommends a handful of courses relevant to the given skills (typically
    missing_skills from an analysis, a roadmap, or an internship track's
    core_skills), grouped by the domain(s) they best match.

    Falls back to the two broadest, most universally useful domains if no
    keyword overlap is found, so this never returns an empty result.
    """
    domains = domains_for_skills(skills, limit=limit_domains)
    if not domains:
        domains = ["Web Development", "Data Science & Analytics"][:limit_domains]

    return {
        "matched_domains": domains,
        "recommendations": [
            {"domain": d, "courses": COURSE_CATALOG.get(d, [])[:limit_per_domain]}
            for d in domains
        ],
    }