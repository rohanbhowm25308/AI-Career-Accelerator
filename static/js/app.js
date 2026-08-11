/*=========================================================
    Ascend — app.js
    Wires the 4 modules (Analyzer, Interview, Roadmap, Internships)
    to the Flask API and keeps them in sync: running the analyzer
    auto-feeds detected skills into the other three modules.
=========================================================*/

import {
    checkServer, getRoles, analyzeResume, downloadReport,
    startInterview, submitAnswer, getInterviewSummary,
    buildRoadmap, matchInternships,
    suitePersonas, suiteConfidence,
} from "./api.js";

const state = {
    report: null,
    interviewSession: null,
    roles: [],
    selectedPersona: null,
};

/*=========================================================
    WAYPOINT "DONE" BADGES
    Marks a waypoint card (1-5) complete once that module's
    action has actually succeeded. suite.js calls the same
    window.markWaypointDone(5) once all 15 AI Suite modules
    have been used at least once.
=========================================================*/
function markWaypointDone(n) {
    const card = document.querySelector(`.waypoint-card[data-waypoint="${n}"]`);
    if (!card || card.classList.contains("is-done")) return;
    card.classList.add("is-done");
    const badge = document.createElement("span");
    badge.className = "waypoint-done-badge";
    badge.innerHTML = "✓ Done";
    card.appendChild(badge);
}
window.markWaypointDone = markWaypointDone;

// Ascend AI Suite (suite.js) reads the resume report and role list through
// this shared reference rather than duplicating analysis logic.
window.ascendState = state;

/*=========================================================
                TOAST
=========================================================*/

function showToast(message, type = "info") {
    let toast = document.getElementById("toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "toast";
        toast.className = "toast";
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(() => toast.classList.remove("show"), 3500);
}

window.__ascendShowToast = showToast;

function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

/*=========================================================
                SERVER STATUS
=========================================================*/

async function initServerStatus() {
    const pill = document.getElementById("serverStatus");
    const text = document.getElementById("serverStatusText");
    const health = await checkServer();
    if (health.status === "online") {
        pill.classList.add("online");
        text.textContent = health.llm_enabled ? "Server online · LLM enabled" : "Server online · offline mode";
    } else {
        pill.classList.add("offline");
        text.textContent = "Backend offline — run: python app.py";
        showToast("Backend server is offline. Run: python app.py", "warning");
    }
}

/*=========================================================
                SCROLLSPY NAV
=========================================================*/

function initScrollspy() {
    const links = document.querySelectorAll("#navLinks a[data-nav]");
    const sections = [...links].map((l) => document.getElementById(l.dataset.nav)).filter(Boolean);
    if (!sections.length) return;

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    links.forEach((l) => l.classList.toggle("active", l.dataset.nav === entry.target.id));
                }
            });
        },
        { rootMargin: "-45% 0px -50% 0px" }
    );
    sections.forEach((s) => observer.observe(s));
}

/*=========================================================
                SCORE RING HELPER
=========================================================*/

function setScoreRing(ringEl, valueEl, percent, color = "var(--accent)") {
    if (!ringEl || !valueEl) return;
    const clamped = Math.max(0, Math.min(100, Math.round(percent)));
    const degrees = (clamped / 100) * 360;
    ringEl.style.background = `conic-gradient(${color} 0deg, ${color} ${degrees}deg, var(--surface-2) ${degrees}deg)`;
    valueEl.textContent = `${clamped}%`;
}

/*=========================================================
    MODULE 1 — RESUME ANALYZER
=========================================================*/

const resumeFile = document.getElementById("resumeFile");
const fileDrop = document.getElementById("fileDrop");
const fileNameDisplay = document.getElementById("fileNameDisplay");
const jdInput = document.getElementById("jobDescription");
const analyzeBtn = document.getElementById("analyzeBtn");
const downloadReportBtn = document.getElementById("downloadReportBtn");

function updateFileName() {
    fileNameDisplay.textContent = resumeFile.files.length ? `Selected: ${resumeFile.files[0].name}` : "";
}

if (resumeFile) {
    resumeFile.addEventListener("change", updateFileName);
}

if (fileDrop) {
    ["dragover", "dragleave", "drop"].forEach((evt) => {
        fileDrop.addEventListener(evt, (e) => {
            e.preventDefault();
            fileDrop.classList.toggle("dragover", evt === "dragover");
        });
    });
    fileDrop.addEventListener("drop", (e) => {
        if (e.dataTransfer.files.length) {
            resumeFile.files = e.dataTransfer.files;
            updateFileName();
        }
    });
}

const BREAKDOWN_LABELS = {
    structure: "Section structure",
    contact_info: "Contact info",
    skills_coverage: "Skills coverage",
    content_depth: "Content depth",
    quantified_impact: "Quantified impact",
    parse_cleanliness: "ATS parse cleanliness",
};

function renderBreakdown(breakdown) {
    const el = document.getElementById("breakdownBars");
    el.innerHTML = "";
    Object.entries(breakdown).forEach(([key, value]) => {
        const row = document.createElement("div");
        row.className = "bar-row";
        row.innerHTML = `
            <span class="bar-label">${BREAKDOWN_LABELS[key] || key}</span>
            <span class="bar-track"><span class="bar-fill" style="width:${value}%"></span></span>
            <span class="bar-value">${value}%</span>
        `;
        el.appendChild(row);
    });
}

function renderChips(container, items, className = "") {
    container.innerHTML = "";
    if (!items || !items.length) {
        container.innerHTML = `<span class="hint">None detected.</span>`;
        return;
    }
    items.forEach((skill) => {
        const chip = document.createElement("span");
        chip.className = `chip ${className}`.trim();
        chip.textContent = skill;
        container.appendChild(chip);
    });
}

/*=========================================================
    SHARED — recommended courses renderer
    (used by Roadmap results and Internship track cards)
=========================================================*/

function renderCourseGroups(container, recommendedCourses) {
    if (!container) return;
    container.innerHTML = "";
    if (!recommendedCourses || !recommendedCourses.recommendations || !recommendedCourses.recommendations.length) {
        container.innerHTML = `<span class="hint">No course matches for this yet.</span>`;
        return;
    }
    recommendedCourses.recommendations.forEach((group) => {
        if (!group.courses.length) return;
        const wrap = document.createElement("div");
        wrap.className = "course-domain-group";
        const grid = group.courses.map((c) => `
            <a class="course-card" href="${c.url}" target="_blank" rel="noopener">
                <div class="course-title">${escapeHTML(c.title)}</div>
                <div class="course-provider">${escapeHTML(c.provider)}</div>
                <div class="course-meta">
                    <span class="course-level">${escapeHTML(c.level)}</span>
                    <span class="course-hours">~${c.hours}h</span>
                </div>
            </a>
        `).join("");
        wrap.innerHTML = `<div class="course-domain-title">${escapeHTML(group.domain)}</div><div class="course-grid">${grid}</div>`;
        container.appendChild(wrap);
    });
}

function renderAnalysis(report) {
    document.getElementById("analyzerEmpty").style.display = "none";
    document.getElementById("analyzerResults").style.display = "block";

    setScoreRing(document.getElementById("atsScoreRing"), document.getElementById("atsScoreValue"), report.ats_score);

    const matchWrap = document.getElementById("matchScoreWrap");
    if (report.match_score !== null && report.match_score !== undefined) {
        matchWrap.style.display = "block";
        setScoreRing(document.getElementById("matchScoreRing"), document.getElementById("matchScoreValue"), report.match_score, "var(--mint)");
    } else {
        matchWrap.style.display = "none";
    }

    renderBreakdown(report.score_breakdown);
    renderChips(document.getElementById("skillsFoundRow"), report.skills_found);

    const missingRow = document.getElementById("missingSkillsRow");
    if (report.job_description_provided) {
        if (report.jd_skills_detected === 0) {
            missingRow.innerHTML = `<span class="hint">We couldn't detect specific skill keywords in that job description — try pasting the full posting (requirements/responsibilities), not just a title.</span>`;
        } else if (!report.missing_skills.length) {
            renderChips(missingRow, [], "missing");
            missingRow.innerHTML = `<span class="hint">Great coverage — every skill keyword we found in the JD is already on your resume. 🎉</span>`;
        } else {
            renderChips(missingRow, report.missing_skills, "missing");
        }
    } else {
        missingRow.innerHTML = `<span class="hint">Paste a job description above to see gaps.</span>`;
    }

    const suggestionsList = document.getElementById("suggestionsList");
    suggestionsList.innerHTML = "";
    (report.suggestions || []).forEach((tip) => {
        const li = document.createElement("li");
        li.textContent = tip;
        suggestionsList.appendChild(li);
    });

    downloadReportBtn.style.display = "inline-flex";
}

async function handleAnalyze() {
    if (!resumeFile.files.length) {
        showToast("Please choose a resume file first.", "error");
        return;
    }

    const file = resumeFile.files[0];
    const jobDescription = jdInput.value.trim();

    analyzeBtn.disabled = true;
    const originalText = analyzeBtn.textContent;
    analyzeBtn.innerHTML = `<span class="spinner"></span> Analyzing…`;

    try {
        const report = await analyzeResume(file, jobDescription);
        if (report.error) {
            showToast(report.error, "error");
            return;
        }
        state.report = report;
        renderAnalysis(report);
        refreshDownstreamModules();
        window.dispatchEvent(new CustomEvent("ascend:report", { detail: report }));
        showToast("Analysis complete!", "success");
        markWaypointDone(1);
    } catch (error) {
        console.error(error);
        showToast("Could not reach the server. Is app.py running?", "error");
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = originalText;
    }
}

if (analyzeBtn) analyzeBtn.addEventListener("click", handleAnalyze);

if (downloadReportBtn) {
    downloadReportBtn.addEventListener("click", () => {
        if (!state.report) {
            showToast("Run an analysis first.", "error");
            return;
        }
        downloadReport(state.report.report_id).catch(() => showToast("Could not download the report.", "error"));
    });
}

/*=========================================================
    MODULE 2 — MOCK INTERVIEW
=========================================================*/

const interviewRoleSelect = document.getElementById("interviewRole");
const interviewSkillSourceText = document.getElementById("interviewSkillSourceText");
const startInterviewBtn = document.getElementById("startInterviewBtn");
const interviewRunner = document.getElementById("interviewRunner");
const interviewProgress = document.getElementById("interviewProgress");
const qaThread = document.getElementById("qaThread");
const answerBox = document.getElementById("answerBox");
const answerInput = document.getElementById("answerInput");
const submitAnswerBtn = document.getElementById("submitAnswerBtn");
const interviewSummaryEl = document.getElementById("interviewSummary");

function addQuestionBubble(question) {
    const bubble = document.createElement("div");
    bubble.className = "msg question";
    bubble.innerHTML = `<span class="msg-tag">${escapeHTML(question.category)}</span>${escapeHTML(question.text)}`;
    qaThread.appendChild(bubble);
    qaThread.scrollTop = qaThread.scrollHeight;
}

function addAnswerBubble(answer) {
    const bubble = document.createElement("div");
    bubble.className = "msg answer";
    bubble.innerHTML = `<span class="msg-tag">Your answer</span>${escapeHTML(answer)}`;
    qaThread.appendChild(bubble);
    qaThread.scrollTop = qaThread.scrollHeight;
}

function addFeedbackCard(feedback) {
    const card = document.createElement("div");
    card.className = "feedback-card";
    const personaTag = feedback.persona
        ? `<div class="hint" style="margin:-4px 0 8px;">as scored by <strong>${escapeHTML(feedback.persona)}</strong></div>`
        : "";
    card.innerHTML = `
        <div class="feedback-score"><span>Answer score</span><span class="score-num">${feedback.score}/100</span></div>
        ${personaTag}
        <ul class="feedback-list strengths">${feedback.strengths.map((s) => `<li>${escapeHTML(s)}</li>`).join("")}</ul>
        <ul class="feedback-list">${feedback.improvements.map((s) => `<li>${escapeHTML(s)}</li>`).join("")}</ul>
    `;
    qaThread.appendChild(card);
    qaThread.scrollTop = qaThread.scrollHeight;
}

/*=========================================================
    AI Interview Avatar — interviewer persona picker
=========================================================*/

const personaRow = document.getElementById("personaRow");
const personaIntroText = document.getElementById("personaIntroText");

async function loadPersonas() {
    if (!personaRow) return;
    try {
        const { personas } = await suitePersonas();
        personaRow.innerHTML = "";
        personas.forEach((p) => {
            const card = document.createElement("div");
            card.className = "persona-card";
            card.dataset.personaId = p.id;
            card.innerHTML = `<div class="persona-name">${escapeHTML(p.name)}</div><div class="persona-tone">${escapeHTML(p.tone)}</div>`;
            card.addEventListener("click", () => {
                const alreadySelected = state.selectedPersona === p.id;
                personaRow.querySelectorAll(".persona-card").forEach((c) => c.classList.remove("selected"));
                if (alreadySelected) {
                    state.selectedPersona = null;
                    personaIntroText.textContent = "";
                } else {
                    state.selectedPersona = p.id;
                    card.classList.add("selected");
                    personaIntroText.textContent = `"${p.intro}"`;
                }
            });
            personaRow.appendChild(card);
        });
    } catch (error) {
        console.error(error);
    }
}

/*=========================================================
    Live Confidence Meter — inline during the interview
=========================================================*/

const confidenceLive = document.getElementById("confidenceLive");
const confidenceLiveFill = document.getElementById("confidenceLiveFill");
const confidenceLiveValue = document.getElementById("confidenceLiveValue");
let confidenceDebounce = null;

if (answerInput) {
    answerInput.addEventListener("input", () => {
        clearTimeout(confidenceDebounce);
        const text = answerInput.value.trim();
        if (text.split(/\s+/).length < 4) {
            confidenceLive.style.display = "none";
            return;
        }
        confidenceDebounce = setTimeout(async () => {
            try {
                const result = await suiteConfidence(text);
                confidenceLive.style.display = "flex";
                confidenceLiveFill.style.width = `${result.confidence_score}%`;
                confidenceLiveValue.textContent = `${result.confidence_score}% · ${result.confidence_level}`;
            } catch (error) {
                console.error(error);
            }
        }, 600);
    });
}

async function handleStartInterview() {
    const role = interviewRoleSelect.value || null;
    const skills = state.report ? state.report.skills_found : [];

    startInterviewBtn.disabled = true;
    try {
        const session = await startInterview({
            skills, role,
            report_id: state.report ? state.report.report_id : null,
            persona_id: state.selectedPersona,
        });
        state.interviewSession = { id: session.session_id, total: session.progress.total };

        qaThread.innerHTML = "";
        interviewSummaryEl.style.display = "none";
        answerBox.style.display = "block";
        interviewRunner.style.display = "block";
        if (session.persona) {
            const introBubble = document.createElement("div");
            introBubble.className = "msg question";
            introBubble.innerHTML = `<span class="msg-tag">${escapeHTML(session.persona.name)}</span>${escapeHTML(session.persona.intro)}`;
            qaThread.appendChild(introBubble);
        }
        addQuestionBubble(session.question);
        interviewProgress.style.width = "0%";
        answerInput.value = "";
        confidenceLive.style.display = "none";
        interviewRunner.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
        console.error(error);
        showToast("Could not start the interview. Is the server running?", "error");
    } finally {
        startInterviewBtn.disabled = false;
    }
}

async function handleSubmitAnswer() {
    const answer = answerInput.value.trim();
    if (!answer) {
        showToast("Type an answer before submitting.", "error");
        return;
    }
    if (!state.interviewSession) return;

    addAnswerBubble(answer);
    submitAnswerBtn.disabled = true;
    answerInput.value = "";

    try {
        const result = await submitAnswer(state.interviewSession.id, answer);
        if (result.error) {
            showToast(result.error, "error");
            return;
        }
        addFeedbackCard(result.feedback);
        const pct = (result.progress.answered / result.progress.total) * 100;
        interviewProgress.style.width = `${pct}%`;

        if (result.done) {
            answerBox.style.display = "none";
            const summary = await getInterviewSummary(state.interviewSession.id);
            renderInterviewSummary(summary);
            markWaypointDone(2);
        } else {
            addQuestionBubble(result.next_question);
        }
    } catch (error) {
        console.error(error);
        showToast("Could not submit your answer.", "error");
    } finally {
        submitAnswerBtn.disabled = false;
    }
}

function renderInterviewSummary(summary) {
    interviewSummaryEl.style.display = "block";
    interviewSummaryEl.innerHTML = `
        <div class="score-ring" style="margin:0 auto 16px;"><span>${summary.average_score}</span></div>
        <h3>Interview complete</h3>
        <p>Average score across ${summary.answers} answers.</p>
        <div class="grid-2" style="text-align:left; margin-top:20px;">
            <div>
                <div class="field-label">Top strengths</div>
                <ul class="feedback-list strengths">${summary.strengths.map((s) => `<li>${escapeHTML(s)}</li>`).join("")}</ul>
            </div>
            <div>
                <div class="field-label">Focus on next</div>
                <ul class="feedback-list">${summary.improvements.map((s) => `<li>${escapeHTML(s)}</li>`).join("")}</ul>
            </div>
        </div>
        <button class="btn btn-secondary" id="retakeInterviewBtn" style="margin-top:24px;">Retake interview</button>
    `;
    const ring = interviewSummaryEl.querySelector(".score-ring");
    setScoreRing(ring, ring.querySelector("span"), summary.average_score);
    document.getElementById("retakeInterviewBtn").addEventListener("click", handleStartInterview);
}

if (startInterviewBtn) startInterviewBtn.addEventListener("click", handleStartInterview);
if (submitAnswerBtn) submitAnswerBtn.addEventListener("click", handleSubmitAnswer);
if (answerInput) {
    answerInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleSubmitAnswer();
    });
}

/*=========================================================
    MODULE 3 — SKILL ROADMAP
=========================================================*/

const roadmapSource = document.getElementById("roadmapSource");
const roadmapRoleField = document.getElementById("roadmapRoleField");
const roadmapRoleSelect = document.getElementById("roadmapRole");
const roadmapHours = document.getElementById("roadmapHours");
const buildRoadmapBtn = document.getElementById("buildRoadmapBtn");

if (roadmapSource) {
    roadmapSource.addEventListener("change", () => {
        roadmapRoleField.style.display = roadmapSource.value === "role" ? "block" : "none";
    });
}

function renderRoadmap(plan) {
    document.getElementById("roadmapEmpty").style.display = "none";
    document.getElementById("roadmapResults").style.display = "block";

    document.getElementById("roadmapTotalSkills").textContent = plan.total_skills;
    document.getElementById("roadmapTotalHours").textContent = plan.total_estimated_hours;
    document.getElementById("roadmapWeeks").textContent = plan.estimated_weeks;

    const columns = document.getElementById("phaseColumns");
    columns.innerHTML = "";

    if (!plan.phases.length) {
        columns.innerHTML = `<div class="empty-state">No skill gaps found — you're already covering everything we checked for. 🎉</div>`;
        return;
    }

    plan.phases.forEach((phase) => {
        const col = document.createElement("div");
        col.className = `phase-col ${phase.name}`;
        col.innerHTML = `<h4><span class="phase-dot"></span>${phase.name}</h4>`;
        phase.skills.forEach((item) => {
            const row = document.createElement("div");
            row.className = "roadmap-item";
            row.innerHTML = `
                <div class="skill-name">${escapeHTML(item.skill)}</div>
                <div class="hours">~${item.estimated_hours}h</div>
                <div class="resources">${item.resources.map((r) => `<span>${escapeHTML(r)}</span>`).join("")}</div>
            `;
            col.appendChild(row);
        });
        columns.appendChild(col);
    });

    const coursesCard = document.getElementById("roadmapCoursesCard");
    if (plan.recommended_courses) {
        coursesCard.style.display = "block";
        renderCourseGroups(document.getElementById("roadmapCourseGroups"), plan.recommended_courses);
    } else {
        coursesCard.style.display = "none";
    }
}

async function handleBuildRoadmap() {
    const hours = parseInt(roadmapHours.value, 10) || 8;
    let payload = { hours_per_week: hours };

    if (roadmapSource.value === "role") {
        if (!roadmapRoleSelect.value) {
            showToast("Pick a target role first.", "error");
            return;
        }
        payload.skills = state.report ? state.report.skills_found : [];
        payload.target_role = roadmapRoleSelect.value;
    } else {
        if (!state.report || !state.report.job_description_provided) {
            showToast("Run the Analyzer with a job description first, or switch to 'A target role'.", "error");
            return;
        }
        payload.missing_skills = state.report.missing_skills;
    }

    buildRoadmapBtn.disabled = true;
    try {
        const plan = await buildRoadmap(payload);
        renderRoadmap(plan);
        document.getElementById("roadmapResults").scrollIntoView({ behavior: "smooth", block: "start" });
        markWaypointDone(3);
    } catch (error) {
        console.error(error);
        showToast("Could not build the roadmap.", "error");
    } finally {
        buildRoadmapBtn.disabled = false;
    }
}

if (buildRoadmapBtn) buildRoadmapBtn.addEventListener("click", handleBuildRoadmap);

/*=========================================================
    MODULE 4 — INTERNSHIP MATCHES
=========================================================*/

const internshipSkillsInput = document.getElementById("internshipSkillsInput");
const findInternshipsBtn = document.getElementById("findInternshipsBtn");

function renderInternships(data) {
    document.getElementById("internshipsEmpty").style.display = "none";
    document.getElementById("internshipsResults").style.display = "block";

    const list = document.getElementById("trackList");
    list.innerHTML = "";
    data.tracks.forEach((track) => {
        const card = document.createElement("div");
        card.className = "track-card";
        card.innerHTML = `
            <div class="track-head">
                <div>
                    <h4>${escapeHTML(track.title)}</h4>
                    <p>${escapeHTML(track.description)}</p>
                </div>
                <span class="match-badge">${track.match_percent}% match</span>
            </div>
            <div class="track-bar"><div class="track-bar-fill" style="width:${track.match_percent}%"></div></div>
            <div class="track-chips">
                <div>
                    <span class="group-label">You have</span>
                    <div class="chip-row">${track.matched_skills.map((s) => `<span class="chip matched">${escapeHTML(s)}</span>`).join("") || '<span class="hint">None yet</span>'}</div>
                </div>
                <div>
                    <span class="group-label">To build</span>
                    <div class="chip-row">${track.missing_skills.map((s) => `<span class="chip missing">${escapeHTML(s)}</span>`).join("") || '<span class="hint">Fully covered</span>'}</div>
                </div>
            </div>
            <div class="track-courses">
                <span class="field-label">📚 Recommended courses</span>
                <div class="course-domain-groups"></div>
            </div>
        `;
        renderCourseGroups(card.querySelector(".track-courses .course-domain-groups"), track.recommended_courses);
        list.appendChild(card);
    });

    const platformRow = document.getElementById("platformRow");
    platformRow.innerHTML = "";
    data.search_platforms.forEach((p) => {
        const a = document.createElement("a");
        a.href = p.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.className = "btn btn-secondary";
        a.textContent = `Search on ${p.name}`;
        platformRow.appendChild(a);
    });
}

async function handleFindInternships() {
    const raw = internshipSkillsInput.value.trim();
    const skills = raw.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);

    if (!skills.length) {
        showToast("Add at least one skill, or run the Analyzer first.", "error");
        return;
    }

    findInternshipsBtn.disabled = true;
    try {
        const data = await matchInternships({ skills });
        renderInternships(data);
        document.getElementById("internshipsResults").scrollIntoView({ behavior: "smooth", block: "start" });
        markWaypointDone(4);
    } catch (error) {
        console.error(error);
        showToast("Could not fetch internship matches.", "error");
    } finally {
        findInternshipsBtn.disabled = false;
    }
}

if (findInternshipsBtn) findInternshipsBtn.addEventListener("click", handleFindInternships);

/*=========================================================
    CROSS-MODULE SYNC
=========================================================*/

function refreshDownstreamModules() {
    if (!state.report) return;
    const skills = state.report.skills_found || [];

    interviewSkillSourceText.textContent = skills.length
        ? `Using ${skills.length} skills detected from your resume.`
        : "No skills detected yet — pick a target role above.";
    document.getElementById("interviewSkillSource").classList.toggle("online", skills.length > 0);

    internshipSkillsInput.value = skills.join(", ");
}

/*=========================================================
    INIT
=========================================================*/

async function populateRoleSelects() {
    const roles = await getRoles();
    state.roles = roles;
    [interviewRoleSelect, roadmapRoleSelect].forEach((select) => {
        if (!select) return;
        roles.forEach((role) => {
            const opt = document.createElement("option");
            opt.value = role;
            opt.textContent = role;
            select.appendChild(opt);
        });
    });
}

window.addEventListener("DOMContentLoaded", () => {
    initServerStatus();
    initScrollspy();
    populateRoleSelects();
    loadPersonas();
});