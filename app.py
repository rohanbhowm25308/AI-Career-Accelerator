"""
app.py
--------
Flask backend for Ascend - the AI Career Accelerator.

Endpoints (all JSON except /download-report which returns a PDF file):
    GET  /                              -> serves the frontend
    GET  /health                        -> {"status": "online", "llm_enabled": bool}
    GET  /roles                         -> list of target roles for interview/roadmap
    POST /analyze                       -> multipart: resume=<file>, job_description=<text, optional>
    POST /job-match                     -> multipart: resume=<file>, job_description=<text, required>
    POST /job-description               -> json: {"description": "..."}
    POST /chat                          -> json: {"question": "..."}
    GET  /download-report/<id>          -> PDF download of a previously generated report

    POST /interview/start               -> json: {"report_id"?: str, "skills"?: [str], "role"?: str}
    POST /interview/answer              -> json: {"session_id": str, "answer": str}
    GET  /interview/summary/<id>        -> aggregate interview performance

    POST /roadmap                       -> json: {"report_id"?, "skills"?, "target_role"?, "hours_per_week"?}
    POST /internships                   -> json: {"report_id"?, "skills"?}
"""

import os
import uuid
import datetime

from flask import Flask, request, jsonify, render_template, send_file, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

from resume_parser import parse_resume, load_skills
from similarity import compute_ats_score, compute_match_score, find_missing_skills, score_breakdown
from ai_suggestions import generate_suggestions
import interview as interview_engine
import roadmap as roadmap_engine
import internships as internships_engine
import advanced_features as adv
import hiring_simulation
import career_story
import digital_recruiter
import courses as courses_engine
import extras

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

SKILLS_LIST = load_skills(os.path.join(BASE_DIR, "data", "skills.csv"))

# In-memory stores, fine for a hackathon-scale single-instance demo.
REPORTS = {}


def llm_enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage):
    filename = secure_filename(file_storage.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(UPLOAD_FOLDER, unique_name)
    file_storage.save(path)
    return path


def build_report(resume_file, job_description=""):
    """Core analysis pipeline shared by /analyze and /job-match."""
    if not resume_file or resume_file.filename == "":
        return None, ("No resume file was uploaded.", 400)

    if not allowed_file(resume_file.filename):
        return None, ("Unsupported file type. Please upload a PDF, DOCX or TXT file.", 400)

    file_path = save_upload(resume_file)

    try:
        parsed = parse_resume(file_path, SKILLS_LIST)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the client
        return None, (f"Could not read resume file: {exc}", 422)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    ats_score = compute_ats_score(parsed)
    breakdown = score_breakdown(parsed)

    match_score = None
    missing_skills = []
    matched_skills = []

    job_description = (job_description or "").strip()
    if job_description:
        match_score = compute_match_score(parsed["raw_text"], job_description)
        skill_diff = find_missing_skills(parsed["raw_text"], job_description, SKILLS_LIST)
        missing_skills = skill_diff["missing_skills"]
        matched_skills = skill_diff["matched_skills"]
        jd_skills_detected = len(skill_diff["jd_skills"])
    else:
        jd_skills_detected = 0

    suggestions = generate_suggestions(
        parsed,
        ats_score,
        match_score=match_score,
        missing_skills=missing_skills,
        use_llm=llm_enabled(),
        jd_text=job_description or None,
        breakdown=breakdown,
        jd_skills_detected=jd_skills_detected if job_description else None,
    )

    report_id = uuid.uuid4().hex[:12]
    report = {
        "report_id": report_id,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "ats_score": ats_score,
        "score_breakdown": breakdown,
        "match_score": match_score,
        "skills_found": parsed["skills"],
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "jd_skills_detected": jd_skills_detected,
        "sections_detected": parsed["sections"],
        "contact_info": parsed["contact_info"],
        "word_count": parsed["word_count"],
        "suggestions": suggestions,
        "job_description_provided": bool(job_description),
    }

    REPORTS[report_id] = report
    return report, None


# ---------------------------------------------------------------------------
# Core routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "time": datetime.datetime.utcnow().isoformat() + "Z",
        "llm_enabled": llm_enabled(),
    })


@app.route("/roles", methods=["GET"])
def roles():
    return jsonify({"roles": roadmap_engine.available_roles()})


@app.route("/analyze", methods=["POST"])
def analyze():
    resume_file = request.files.get("resume")
    job_description = request.form.get("job_description", "")

    report, error = build_report(resume_file, job_description)
    if error:
        message, status = error
        return jsonify({"error": message}), status

    return jsonify(report)


@app.route("/job-match", methods=["POST"])
def job_match():
    resume_file = request.files.get("resume")
    job_description = request.form.get("job_description", "")

    if not job_description.strip():
        return jsonify({"error": "job_description is required for /job-match."}), 400

    report, error = build_report(resume_file, job_description)
    if error:
        message, status = error
        return jsonify({"error": message}), status

    return jsonify(report)


@app.route("/job-description", methods=["POST"])
def job_description():
    data = request.get_json(silent=True) or {}
    description = data.get("description", "").strip()

    if not description:
        return jsonify({"error": "description is required."}), 400

    session["job_description"] = description
    detected_skills = [s for s in SKILLS_LIST if s in description.lower()]

    return jsonify({
        "status": "saved",
        "length": len(description),
        "detected_skills": sorted(set(detected_skills)),
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "question is required."}), 400

    q = question.lower()
    if "ats" in q:
        answer = (
            "ATS (Applicant Tracking System) score reflects how well-structured "
            "and machine-readable your resume is - clear sections, contact info, "
            "and relevant keywords all help."
        )
    elif "interview" in q:
        answer = (
            "Try the Mock Interview module - it asks behavioral and technical "
            "questions based on your resume's skills and gives instant feedback."
        )
    elif "roadmap" in q or "learn" in q:
        answer = (
            "Head to the Skill Roadmap module - it turns your missing skills into "
            "a phased, time-boxed learning plan with curated resources."
        )
    elif "internship" in q or "job" in q:
        answer = (
            "The Internship Matches module ranks common early-career tracks by how "
            "well your current skills already fit each one."
        )
    elif "skill" in q:
        answer = (
            "List skills as specific keywords (e.g. 'Python', 'React') rather "
            "than vague phrases, and only include ones you can speak to in an interview."
        )
    else:
        answer = (
            "I can help with resume structure, ATS optimization, skill matching, "
            "mock interviews, and learning roadmaps - ask me something specific!"
        )

    return jsonify({"answer": answer})


@app.route("/download-report/<report_id>", methods=["GET"])
def download_report(report_id):
    report = REPORTS.get(report_id)
    if not report:
        return jsonify({"error": "Report not found."}), 404

    pdf_path = os.path.join(OUTPUT_FOLDER, f"report_{report_id}.pdf")
    _write_report_pdf(report, pdf_path)

    return send_file(pdf_path, as_attachment=True, download_name="Ascend_Resume_Report.pdf")


def _write_report_pdf(report, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    def line(text, size=11, gap=7 * mm, bold=False):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(20 * mm, y, text)
        y -= gap

    line("Ascend - AI Career Accelerator Report", size=18, bold=True, gap=12 * mm)
    line(f"Generated: {report['generated_at']}", size=9, gap=10 * mm)

    line(f"ATS Score: {report['ats_score']}%", size=13, bold=True)
    if report.get("match_score") is not None:
        line(f"Job Description Match: {report['match_score']}%", size=13, bold=True)

    y -= 3 * mm
    line("Skills Found:", bold=True)
    skills_text = ", ".join(report["skills_found"]) or "None detected"
    for chunk in _wrap(skills_text, 90):
        line(chunk, size=10)

    if report.get("missing_skills"):
        y -= 3 * mm
        line("Missing Skills (from job description):", bold=True)
        for chunk in _wrap(", ".join(report["missing_skills"]), 90):
            line(chunk, size=10)

    y -= 3 * mm
    line("Suggestions:", bold=True)
    for suggestion in report["suggestions"]:
        for chunk in _wrap(f"- {suggestion}", 95):
            line(chunk, size=10)
        if y < 25 * mm:
            c.showPage()
            y = height - 25 * mm

    c.save()


def _wrap(text, width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


# ---------------------------------------------------------------------------
# Mock interview routes
# ---------------------------------------------------------------------------

def _resolve_skills(data):
    """Pull skills either from an explicit list or a prior analysis report."""
    if data.get("skills"):
        return data["skills"]
    report_id = data.get("report_id")
    if report_id and report_id in REPORTS:
        return REPORTS[report_id]["skills_found"]
    return []


@app.route("/interview/start", methods=["POST"])
def interview_start():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    role = data.get("role")
    persona_id = data.get("persona_id")

    session_obj = interview_engine.start_interview(skills=skills, role=role)
    session_obj["persona_id"] = persona_id
    first_question = session_obj["questions"][0]

    persona = next((p for p in adv.available_personas() if p["id"] == persona_id), None)

    return jsonify({
        "session_id": session_obj["id"],
        "role": role,
        "persona": persona,
        "question": first_question,
        "progress": {"answered": 0, "total": len(session_obj["questions"])},
    })


@app.route("/interview/answer", methods=["POST"])
def interview_answer():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    answer = (data.get("answer") or "").strip()

    session_obj = interview_engine.get_session(session_id)
    if not session_obj:
        return jsonify({"error": "Interview session not found or expired."}), 404
    if not answer:
        return jsonify({"error": "answer is required."}), 400

    result = interview_engine.evaluate_answer(session_obj, answer, use_llm=llm_enabled())
    persona_id = session_obj.get("persona_id")
    if persona_id and result.get("feedback"):
        # Mutates in place: the same feedback dict is stored in the session's
        # answer history, so the persona-adjusted score also flows into the
        # interview summary at /interview/summary/<id>.
        adjusted = adv.apply_persona_feedback(result["feedback"], persona_id)
        result["feedback"].update(adjusted)
    return jsonify(result)


@app.route("/interview/summary/<session_id>", methods=["GET"])
def interview_summary(session_id):
    session_obj = interview_engine.get_session(session_id)
    if not session_obj:
        return jsonify({"error": "Interview session not found or expired."}), 404

    return jsonify(interview_engine.build_summary(session_obj))


# ---------------------------------------------------------------------------
# Roadmap & internship routes
# ---------------------------------------------------------------------------

@app.route("/roadmap", methods=["POST"])
def roadmap_route():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    target_role = data.get("target_role")
    hours_per_week = int(data.get("hours_per_week") or 8)

    if data.get("missing_skills"):
        missing = data["missing_skills"]
    elif target_role:
        missing = roadmap_engine.missing_skills_for_role(skills, target_role)
    else:
        report_id = data.get("report_id")
        missing = REPORTS.get(report_id, {}).get("missing_skills", []) if report_id else []

    plan = roadmap_engine.build_roadmap(missing, hours_per_week=hours_per_week)
    plan["target_role"] = target_role
    return jsonify(plan)


@app.route("/internships", methods=["POST"])
def internships_route():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    return jsonify(internships_engine.match_internships(skills))


# ---------------------------------------------------------------------------
# Ascend AI Suite - 15 advanced career modules (advanced_features.py)
# ---------------------------------------------------------------------------

def _resolve_report(data):
    """Look up a stored report by id, or return None with an error tuple."""
    report_id = data.get("report_id")
    if not report_id:
        return None, ("report_id is required. Run the Resume Analyzer first.", 400)
    report = REPORTS.get(report_id)
    if not report:
        return None, ("Report not found or expired - re-run the Resume Analyzer.", 404)
    return report, None


@app.route("/suite/recruiter-mode", methods=["POST"])
def suite_recruiter_mode():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(adv.recruiter_mode(report))


@app.route("/suite/hiring-simulation", methods=["POST"])
def suite_hiring_simulation():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    target_role = data.get("target_role")
    return jsonify(hiring_simulation.run_hiring_simulation(report, target_role=target_role))


@app.route("/suite/time-machine", methods=["POST"])
def suite_time_machine():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    target_role = data.get("target_role")
    return jsonify(adv.career_time_machine(report, target_role=target_role))


@app.route("/suite/career-story", methods=["POST"])
def suite_career_story():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    target_role = data.get("target_role")
    return jsonify(career_story.generate_career_story(report, target_role=target_role))


@app.route("/suite/digital-recruiter", methods=["POST"])
def suite_digital_recruiter():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(digital_recruiter.digital_recruiter_message(report))


@app.route("/suite/timeline", methods=["POST"])
def suite_timeline():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    apps_per_week = int(data.get("applications_per_week") or 10)
    apps_per_week = max(1, min(apps_per_week, 100))
    return jsonify(adv.timeline_prediction(report, applications_per_week=apps_per_week))


@app.route("/suite/career-twin", methods=["POST"])
def suite_career_twin():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(adv.career_twin(report, target_role=data.get("target_role") or None))


@app.route("/suite/eye-tracking", methods=["POST"])
def suite_eye_tracking():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(adv.eye_tracking(report))


@app.route("/suite/personas", methods=["GET"])
def suite_personas():
    return jsonify({"personas": adv.available_personas()})


@app.route("/suite/confidence", methods=["POST"])
def suite_confidence():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required."}), 400
    return jsonify(adv.confidence_meter(text))


@app.route("/suite/heatmap", methods=["POST"])
def suite_heatmap():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(adv.resume_heatmap(report))


@app.route("/suite/skill-radar", methods=["POST"])
def suite_skill_radar():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    if not skills:
        return jsonify({"error": "No skills available. Run the Analyzer first or pass 'skills'."}), 400
    return jsonify(adv.skill_radar(skills, target_role=data.get("target_role") or None))


@app.route("/suite/salary", methods=["POST"])
def suite_salary():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    result = adv.salary_prediction(
        skills,
        target_role=data.get("target_role") or None,
        experience_years=data.get("experience_years") or 0,
        location_tier=data.get("location_tier") or "metro",
    )
    return jsonify(result)


@app.route("/suite/career-gps", methods=["POST"])
def suite_career_gps():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    target_role = data.get("target_role")
    if not target_role:
        return jsonify({"error": "target_role is required."}), 400
    hours_per_week = int(data.get("hours_per_week") or 8)
    return jsonify(adv.career_gps(skills, target_role, hours_per_week=hours_per_week))


@app.route("/suite/compare-versions", methods=["POST"])
def suite_compare_versions():
    resume_a = request.files.get("resume_a")
    resume_b = request.files.get("resume_b")
    if not resume_a or not resume_b or resume_a.filename == "" or resume_b.filename == "":
        return jsonify({"error": "Both resume_a and resume_b files are required."}), 400
    if not (allowed_file(resume_a.filename) and allowed_file(resume_b.filename)):
        return jsonify({"error": "Unsupported file type. Please upload PDF, DOCX or TXT files."}), 400

    path_a = save_upload(resume_a)
    path_b = save_upload(resume_b)
    try:
        result = adv.compare_resume_versions(path_a, path_b, SKILLS_LIST)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Could not compare resumes: {exc}"}), 422
    finally:
        for p in (path_a, path_b):
            if os.path.exists(p):
                os.remove(p)
    return jsonify(result)


@app.route("/suite/portfolio-review", methods=["POST"])
def suite_portfolio_review():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required."}), 400
    return jsonify(adv.portfolio_review(text, SKILLS_LIST))


@app.route("/suite/hr-summary", methods=["POST"])
def suite_hr_summary():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(adv.hr_summary(report))


@app.route("/suite/career-risk", methods=["POST"])
def suite_career_risk():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    if not skills:
        return jsonify({"error": "No skills available. Run the Analyzer first or pass 'skills'."}), 400
    return jsonify(adv.career_risk_score(skills))


@app.route("/suite/achievement", methods=["POST"])
def suite_achievement():
    data = request.get_json(silent=True) or {}
    bullet_text = (data.get("bullet_text") or "").strip()
    if not bullet_text:
        return jsonify({"error": "bullet_text is required."}), 400
    result = adv.achievement_generator(bullet_text, skill_context=data.get("skill_context") or None)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/suite/stress-test", methods=["POST"])
def suite_stress_test():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.resume_stress_test(report))


@app.route("/suite/resume-battle", methods=["POST"])
def suite_resume_battle():
    resume_a = request.files.get("resume_a")
    resume_b = request.files.get("resume_b")
    if not resume_a or not resume_b or resume_a.filename == "" or resume_b.filename == "":
        return jsonify({"error": "Both resume_a and resume_b files are required."}), 400
    if not (allowed_file(resume_a.filename) and allowed_file(resume_b.filename)):
        return jsonify({"error": "Unsupported file type. Please upload PDF, DOCX or TXT files."}), 400

    path_a = save_upload(resume_a)
    path_b = save_upload(resume_b)
    try:
        parsed_a = parse_resume(path_a, SKILLS_LIST)
        parsed_b = parse_resume(path_b, SKILLS_LIST)
        report_a = {"ats_score": compute_ats_score(parsed_a), "score_breakdown": score_breakdown(parsed_a)}
        report_b = {"ats_score": compute_ats_score(parsed_b), "score_breakdown": score_breakdown(parsed_b)}
        result = extras.resume_battle(parsed_a, parsed_b, report_a, report_b,
                                       label_a=request.form.get("label_a", "Resume A"),
                                       label_b=request.form.get("label_b", "Resume B"))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Could not run the battle: {exc}"}), 422
    finally:
        for p in (path_a, path_b):
            if os.path.exists(p):
                os.remove(p)
    return jsonify(result)


@app.route("/suite/hidden-talent", methods=["POST"])
def suite_hidden_talent():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.hidden_talent_detector(report))


@app.route("/suite/scorecard", methods=["POST"])
def suite_scorecard():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.career_scorecard(report))


@app.route("/suite/recruiter-psychology", methods=["POST"])
def suite_recruiter_psychology():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.recruiter_psychology(report))


@app.route("/suite/resume-evolution", methods=["POST"])
def suite_resume_evolution():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.resume_evolution(report))


@app.route("/suite/opportunity-radar", methods=["POST"])
def suite_opportunity_radar():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.opportunity_radar(report))


@app.route("/suite/hackathon-partner", methods=["POST"])
def suite_hackathon_partner():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.hackathon_partner_finder(report))


@app.route("/suite/dream-company", methods=["POST"])
def suite_dream_company():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    company = (data.get("company") or "Google").strip()
    return jsonify(extras.dream_company_simulator(report, company, target_role=data.get("target_role")))


@app.route("/suite/decision-explanation", methods=["POST"])
def suite_decision_explanation():
    data = request.get_json(silent=True) or {}
    report, error = _resolve_report(data)
    if error:
        return jsonify({"error": error[0]}), error[1]
    return jsonify(extras.recruiter_decision_explanation(report))


@app.route("/interview/replay/<session_id>", methods=["GET"])
def interview_replay(session_id):
    session_obj = interview_engine.get_session(session_id)
    if not session_obj:
        return jsonify({"error": "Interview session not found or expired."}), 404
    return jsonify(interview_engine.build_replay(session_obj))


# ---------------------------------------------------------------------------
# Course Explorer - a curated catalog spanning AI/ML, Cloud, Cybersecurity,
# Web Dev, Data Science, DevOps, Mobile, UI/UX, Product, and Blockchain.
# Also feeds "recommended courses" shown in the Roadmap and Internship
# Track Matches modules (see roadmap.py / internships.py).
# ---------------------------------------------------------------------------

@app.route("/courses", methods=["GET"])
def courses_catalog():
    return jsonify(courses_engine.all_courses())


@app.route("/courses/for-skills", methods=["POST"])
def courses_for_skills_route():
    data = request.get_json(silent=True) or {}
    skills = _resolve_skills(data)
    if not skills:
        return jsonify({"error": "No skills available. Run the Analyzer first or pass 'skills'."}), 400
    limit_domains = int(data.get("limit_domains") or 3)
    limit_per_domain = int(data.get("limit_per_domain") or 4)
    return jsonify(courses_engine.courses_for_skills(skills, limit_domains=limit_domains, limit_per_domain=limit_per_domain))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "File is too large. Max size is 10MB."}), 413


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(_e):
    return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)