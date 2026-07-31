"""
interview.py
-------------
A lightweight AI mock-interview engine.

Sessions are kept in memory (INTERVIEW_SESSIONS, keyed by session id) which
is fine for a hackathon-scale single-instance demo, mirroring the REPORTS
store already used for analysis reports in app.py.

Each session mixes:
  - 2 behavioral questions (always relevant, any role)
  - up to 4 technical questions pulled from the candidate's own detected
    skills (falls back to the target role's core skills if the resume has
    too few recognized skills)

Answers are scored with a transparent, explainable heuristic so the demo
always produces a sensible result offline. If ANTHROPIC_API_KEY is set,
`evaluate_answer(..., use_llm=True)` asks Claude for a sharper critique and
falls back to the heuristic on any failure.
"""

import os
import re
import time
import uuid

from roadmap import ROLE_SKILL_MAP

BEHAVIORAL_QUESTIONS = [
    "Tell me about a time you had to deliver a project under a tight deadline. What did you do?",
    "Describe a situation where you disagreed with a teammate. How did you resolve it?",
    "Walk me through a mistake you made at work or in a project, and what you learned from it.",
    "Tell me about a time you had to learn a new tool or technology quickly.",
    "Describe a project you're most proud of and your specific contribution to it.",
]

TECHNICAL_QUESTIONS = {
    "python": "What's the difference between a list and a tuple in Python, and when would you use each?",
    "javascript": "Explain the difference between `let`, `const`, and `var` in JavaScript.",
    "react": "How does React's virtual DOM improve rendering performance?",
    "sql": "Write (in words) how you'd find duplicate rows in a SQL table, and how you'd remove them.",
    "django": "How does Django's ORM help you avoid writing raw SQL, and when might you still need it?",
    "flask": "How would you structure a medium-sized Flask app to keep routes, models, and business logic separate?",
    "docker": "What's the difference between a Docker image and a Docker container?",
    "kubernetes": "Explain the difference between a Kubernetes Pod, a Deployment, and a Service.",
    "aws": "How would you choose between AWS Lambda and an EC2 instance for a given workload?",
    "machine learning": "How do you decide whether a model is overfitting, and what would you do about it?",
    "deep learning": "What problem do dropout and batch normalization each try to solve in neural networks?",
    "pandas": "How would you efficiently merge two large DataFrames and handle missing values afterward?",
    "data analysis": "Walk me through how you'd validate that a dataset is clean before analyzing it.",
    "system design": "How would you design a URL shortener that needs to scale to millions of requests a day?",
    "data structures": "When would you choose a hash map over a balanced binary search tree?",
    "algorithms": "How would you explain Big-O notation to a non-technical stakeholder?",
    "git": "What's the difference between `git merge` and `git rebase`, and when would you use each?",
    "rest api": "What makes an API RESTful, and how would you version a public API?",
    "figma": "How do you use components and auto-layout in Figma to keep a design system consistent?",
    "ui design": "How do you balance visual polish with usability when a deadline is tight?",
    "product management": "How would you prioritize a backlog when every stakeholder says their feature is P0?",
    "agile": "What's the difference between Scrum and Kanban, and when would you pick one over the other?",
    "cybersecurity": "What's the difference between authentication and authorization, and why does it matter?",
}

_STAR_MARKERS = ["situation", "task", "action", "result", "i led", "i built", "i managed", "we ", "impact"]

_DISPLAY_NAME_OVERRIDES = {
    "sql": "SQL", "rest api": "REST API", "aws": "AWS", "ui design": "UI Design",
    "ux design": "UX Design", "css": "CSS", "html": "HTML",
}


def _display_skill(skill):
    return _DISPLAY_NAME_OVERRIDES.get(skill, skill.title())

INTERVIEW_SESSIONS = {}
_SESSION_TTL_SECONDS = 60 * 60 * 2  # 2 hours


def _pick_technical_questions(skills, role, limit=4):
    pool = [s for s in skills if s in TECHNICAL_QUESTIONS]
    if len(pool) < limit and role in ROLE_SKILL_MAP:
        for s in ROLE_SKILL_MAP[role]:
            if s in TECHNICAL_QUESTIONS and s not in pool:
                pool.append(s)
            if len(pool) >= limit:
                break
    return pool[:limit] or list(TECHNICAL_QUESTIONS.keys())[:limit]


def start_interview(skills=None, role=None):
    skills = skills or []
    behavioral = BEHAVIORAL_QUESTIONS[:2]
    technical_skills = _pick_technical_questions(skills, role)

    questions = []
    for i, q in enumerate(behavioral):
        questions.append({"id": f"b{i}", "category": "Behavioral", "text": q})
    for i, skill in enumerate(technical_skills):
        questions.append({
            "id": f"t{i}",
            "category": f"Technical - {_display_skill(skill)}",
            "text": TECHNICAL_QUESTIONS[skill],
        })

    session_id = uuid.uuid4().hex[:12]
    session = {
        "id": session_id,
        "role": role,
        "skills": skills,
        "questions": questions,
        "index": 0,
        "answers": [],
        "created_at": time.time(),
    }
    INTERVIEW_SESSIONS[session_id] = session
    return session


def get_session(session_id):
    _cleanup_sessions()
    return INTERVIEW_SESSIONS.get(session_id)


def _cleanup_sessions():
    now = time.time()
    expired = [sid for sid, s in INTERVIEW_SESSIONS.items() if now - s["created_at"] > _SESSION_TTL_SECONDS]
    for sid in expired:
        INTERVIEW_SESSIONS.pop(sid, None)


# ---------------------------------------------------------------------------
# Answer evaluation
# ---------------------------------------------------------------------------

def _heuristic_feedback(question, answer):
    words = answer.split()
    word_count = len(words)
    lowered = answer.lower()

    score = 40
    strengths, improvements = [], []

    if word_count >= 40:
        score += 20
        strengths.append("Good level of detail in your answer.")
    elif word_count < 15:
        improvements.append("Try to expand your answer - aim for at least a few sentences with concrete detail.")
    else:
        score += 8

    if question["category"] == "Behavioral":
        star_hits = sum(1 for m in _STAR_MARKERS if m in lowered)
        if star_hits >= 2:
            score += 20
            strengths.append("You framed the answer with clear context and outcome (STAR-style).")
        else:
            improvements.append(
                "Structure behavioral answers with Situation - Task - Action - Result so the "
                "interviewer can follow the story and see your specific impact."
            )
    else:
        if re.search(r"\b(because|since|so that|therefore|which means)\b", lowered):
            score += 15
            strengths.append("You explained your reasoning, not just the 'what'.")
        else:
            improvements.append("Explain the 'why' behind your technical choice, not just what you'd do.")

    if re.search(r"\d", answer):
        score += 10
        strengths.append("Nice - you backed the answer with a concrete number or metric.")
    else:
        improvements.append("Where possible, quantify the impact (time saved, % improvement, scale, etc.).")

    score = max(10, min(100, score))
    if not strengths:
        strengths.append("You addressed the question directly.")
    if not improvements:
        improvements.append("Solid answer - tighten the delivery for a confident, concise close.")

    return {"score": score, "strengths": strengths[:2], "improvements": improvements[:2]}


def _call_claude_for_feedback(question, answer):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "You are a friendly but rigorous interview coach. Score the candidate's "
            "answer from 0-100 and give exactly 2 strengths and 2 improvements as "
            "short bullet points. Respond ONLY as compact JSON: "
            '{"score": <int>, "strengths": ["...","..."], "improvements": ["...","..."]}'
            f"\n\nQUESTION ({question['category']}): {question['text']}\n\nANSWER: {answer[:2000]}"
        )
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in response.content if hasattr(b, "text"))
        import json
        cleaned = text.strip().strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        data = json.loads(cleaned)
        if "score" in data and "strengths" in data and "improvements" in data:
            return data
        return None
    except Exception:
        return None


def evaluate_answer(session, answer, use_llm=False):
    question = session["questions"][session["index"]]
    feedback = None
    if use_llm:
        feedback = _call_claude_for_feedback(question, answer)
    if feedback is None:
        feedback = _heuristic_feedback(question, answer)

    record = {
        "question": question,
        "answer": answer,
        "feedback": feedback,
    }
    session["answers"].append(record)
    session["index"] += 1

    done = session["index"] >= len(session["questions"])
    next_question = None if done else session["questions"][session["index"]]

    return {
        "feedback": feedback,
        "done": done,
        "next_question": next_question,
        "progress": {"answered": session["index"], "total": len(session["questions"])},
    }


def build_summary(session):
    answers = session["answers"]
    if not answers:
        return {"average_score": 0, "strengths": [], "improvements": [], "answers": 0}

    avg = round(sum(a["feedback"]["score"] for a in answers) / len(answers))
    strengths, improvements = [], []
    for a in answers:
        strengths.extend(a["feedback"]["strengths"])
        improvements.extend(a["feedback"]["improvements"])

    def top_unique(items, n=3):
        seen, out = set(), []
        for i in items:
            if i not in seen:
                seen.add(i)
                out.append(i)
            if len(out) >= n:
                break
        return out

    return {
        "average_score": avg,
        "answers": len(answers),
        "strengths": top_unique(strengths),
        "improvements": top_unique(improvements),
    }
