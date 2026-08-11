<div align="center">

# ✨ Ascend
### The AI Career Accelerator

**One resume in. An interview-ready plan out.**

Analyze → Interview → Roadmap → Match — four AI-powered stops on the flight path from resume to offer.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org)
[![Claude](https://img.shields.io/badge/Gen%20AI-Claude%20(optional)-D97757?logo=anthropic&logoColor=white)](https://www.anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-8A6420)](#license)

</div>

---

## 🚀 What is Ascend?

Most resume tools stop at a single score. Ascend treats job-readiness as a **journey**, not a checkbox — it takes one resume and turns it into a complete, actionable career plan across four connected modules:

| Waypoint | Module | What it does |
|---|---|---|
| 01 | 🔍 **Resume Analyzer** | ATS score, JD match score, and a category-by-category breakdown (structure, contact info, skills coverage, content depth) |
| 02 | 🎤 **AI Mock Interview** | Behavioral + technical questions generated from *your own detected skills*, with instant, explainable feedback |
| 03 | 🗺️ **Skill Roadmap** | Turns skill gaps into a phased plan (Foundation → Intermediate → Advanced) with curated resources and a realistic timeline |
| 04 | 🎯 **Internship Matcher** | Ranks common early-career tracks by a weighted match against your real skill set |

Everything runs **fully offline** by default — no API key, no external calls, no dependency on uptime. Set an `ANTHROPIC_API_KEY` and the suggestion engine and interview feedback silently upgrade to real Gen AI via Claude, with automatic fallback if the call ever fails.

---

## 🧠 Why it's different

- **Explainable, not a black box** — every score breaks down into the exact factors driving it (sections detected, contact info, skill count, word count, TF-IDF similarity to the JD)
- **Weighted, not naive, matching** — internship tracks score core skills 2x and complementary tools 1x, so a candidate with TensorFlow/Keras/OpenCV isn't penalized just because "machine learning" wasn't the literal resume text
- **Gen AI as an upgrade, not a dependency** — the entire pipeline (suggestions, interview scoring) has a deterministic offline mode and an optional Claude-powered mode, chosen automatically at runtime
- **A real user journey, not four disconnected tools** — analyzing your resume auto-feeds detected skills into the interview, roadmap, and internship modules

---

## 🛠️ Tech Stack

**Backend** — Python, Flask, scikit-learn (TF-IDF + cosine similarity), pdfplumber, python-docx, ReportLab
**Frontend** — HTML, CSS, vanilla JavaScript (ES modules) — no framework, no build step
**Gen AI (optional)** — Anthropic Claude API
**Deployment** — Gunicorn + Render (`render.yaml` included)

---

## ⚡ Quick Start

```bash
git clone https://github.com/rohanbhowm25308/ascend-ai-career-accelerator.git
cd ascend-ai-career-accelerator
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** — that's it, no config required.

### Enable real Gen AI (optional)

```bash
export ANTHROPIC_API_KEY=your-key-here     # PowerShell: $env:ANTHROPIC_API_KEY="your-key-here"
python app.py
```

The nav pill in the UI will switch from *"offline mode"* to *"LLM enabled"* once it's active.

---

## 📁 Project Structure

```
ascend/
├── app.py                  # Flask routes tying every module together
├── resume_parser.py        # PDF/DOCX/TXT extraction + contact/skill detection
├── similarity.py           # ATS scoring + TF-IDF JD match scoring
├── ai_suggestions.py       # Prioritized suggestion engine (offline + Claude)
├── interview.py            # Mock interview question bank + answer scoring
├── roadmap.py               # Skill-gap → phased learning roadmap
├── internships.py          # Weighted internship track matcher
├── data/skills.csv          # 150+ tracked technical & soft skills
├── templates/index.html
└── static/{css,js}/         # Design system + vanilla JS controllers
```

---

## ☁️ Deploy on Render

```bash
git push origin main
```
Then connect the repo at [dashboard.render.com](https://dashboard.render.com) — `render.yaml` auto-configures the build and start commands.

---

## 👤 Author

**Built by [Rohan Bhowmik](https://www.linkedin.com/in/rohan-bhowmik-b014473a1)**
[GitHub](https://github.com/rohanbhowm25308) · [LinkedIn](https://www.linkedin.com/in/rohan-bhowmik-b014473a1)

<div align="center">

*Built for Buildathon 2K26 — Problem Statement 1: AI Career Accelerator*

</div>
