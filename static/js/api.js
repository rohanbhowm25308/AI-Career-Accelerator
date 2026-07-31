/*=========================================================
    Ascend — api.js
    Thin wrapper around the Flask backend. Every function returns
    parsed JSON (or throws) so app.js stays declarative.
=========================================================*/

const BASE_URL = "";
const REQUEST_TIMEOUT = 30000;

function timeoutPromise(ms) {
    return new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Request Timeout")), ms);
    });
}

async function fetchWithTimeout(url, options = {}) {
    return Promise.race([fetch(url, options), timeoutPromise(REQUEST_TIMEOUT)]);
}

function checkResponse(response) {
    if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
    return response;
}

async function getJSON(path) {
    const res = await fetchWithTimeout(BASE_URL + path, { headers: { Accept: "application/json" } });
    checkResponse(res);
    return res.json();
}

async function postJSON(path, body) {
    const res = await fetchWithTimeout(BASE_URL + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body || {}),
    });
    checkResponse(res);
    return res.json();
}

/*=========================================================
                HEALTH
=========================================================*/

export async function checkServer() {
    try {
        return await getJSON("/health");
    } catch (error) {
        console.error(error);
        return { status: "offline" };
    }
}

export async function getRoles() {
    try {
        const data = await getJSON("/roles");
        return data.roles || [];
    } catch (error) {
        console.error(error);
        return [];
    }
}

/*=========================================================
                RESUME ANALYSIS
=========================================================*/

export async function analyzeResume(file, jobDescription = "") {
    const formData = new FormData();
    formData.append("resume", file);
    if (jobDescription) formData.append("job_description", jobDescription);

    const endpoint = jobDescription ? "/job-match" : "/analyze";
    const res = await fetchWithTimeout(BASE_URL + endpoint, { method: "POST", body: formData });
    checkResponse(res);
    return res.json();
}

export async function downloadReport(reportId) {
    const res = await fetchWithTimeout(BASE_URL + "/download-report/" + reportId);
    checkResponse(res);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Ascend_Resume_Report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
}

/*=========================================================
                MOCK INTERVIEW
=========================================================*/

export function startInterview(payload) {
    return postJSON("/interview/start", payload);
}

export function submitAnswer(sessionId, answer) {
    return postJSON("/interview/answer", { session_id: sessionId, answer });
}

export function getInterviewSummary(sessionId) {
    return getJSON(`/interview/summary/${sessionId}`);
}

/*=========================================================
                ROADMAP
=========================================================*/

export function buildRoadmap(payload) {
    return postJSON("/roadmap", payload);
}

/*=========================================================
                INTERNSHIPS
=========================================================*/

export function matchInternships(payload) {
    return postJSON("/internships", payload);
}

/*=========================================================
                CHAT
=========================================================*/

export function askAI(question) {
    return postJSON("/chat", { question });
}

/*=========================================================
                ASCEND AI SUITE (15 advanced modules)
=========================================================*/

export function suiteRecruiterMode(payload) {
    return postJSON("/suite/recruiter-mode", payload);
}

export function suiteTimeline(payload) {
    return postJSON("/suite/timeline", payload);
}

export function suiteCareerTwin(payload) {
    return postJSON("/suite/career-twin", payload);
}

export function suiteEyeTracking(payload) {
    return postJSON("/suite/eye-tracking", payload);
}

export function suitePersonas() {
    return getJSON("/suite/personas");
}

export function suiteConfidence(text) {
    return postJSON("/suite/confidence", { text });
}

export function suiteHeatmap(payload) {
    return postJSON("/suite/heatmap", payload);
}

export function suiteSkillRadar(payload) {
    return postJSON("/suite/skill-radar", payload);
}

export function suiteSalary(payload) {
    return postJSON("/suite/salary", payload);
}

export function suiteCareerGPS(payload) {
    return postJSON("/suite/career-gps", payload);
}

export async function suiteCompareVersions(fileA, fileB) {
    const formData = new FormData();
    formData.append("resume_a", fileA);
    formData.append("resume_b", fileB);
    const res = await fetchWithTimeout(BASE_URL + "/suite/compare-versions", { method: "POST", body: formData });
    checkResponse(res);
    return res.json();
}

export function suitePortfolioReview(text) {
    return postJSON("/suite/portfolio-review", { text });
}

export function suiteHRSummary(payload) {
    return postJSON("/suite/hr-summary", payload);
}

export function suiteCareerRisk(payload) {
    return postJSON("/suite/career-risk", payload);
}

export function suiteAchievement(payload) {
    return postJSON("/suite/achievement", payload);
}

/*=========================================================
                COURSE EXPLORER
=========================================================*/

export function getCourseCatalog() {
    return getJSON("/courses");
}

export function getCoursesForSkills(payload) {
    return postJSON("/courses/for-skills", payload);
}