/*=========================================================
    Ascend — suite.js
    Wires the "Ascend AI Suite" (Waypoint 05 — 15 advanced modules)
    to the Flask backend. Reads the shared resume report from
    window.ascendState (populated by app.js after an analysis run)
    so every module here can reuse real skills/scores instead of
    asking the user to re-enter them.
=========================================================*/

import {
    getRoles,
    suiteRecruiterMode, suiteHiringSimulation, suiteTimeMachine, suiteCareerStory, suiteDigitalRecruiter,
    suiteTimeline, suiteCareerTwin, suiteEyeTracking,
    suiteConfidence, suiteHeatmap, suiteSkillRadar, suiteSalary,
    suiteCareerGPS, suiteCompareVersions, suitePortfolioReview,
    suiteHRSummary, suiteCareerRisk, suiteAchievement,
    suiteStressTest, suiteResumeBattle, suiteHiddenTalent, suiteScorecard,
    suiteRecruiterPsychology, suiteResumeEvolution, suiteOpportunityRadar,
    suiteHackathonPartner, suiteDreamCompany, suiteDecisionExplanation,
    getCourseCatalog, getCoursesForSkills, getInterviewReplay,
} from "./api.js";

function getSharedState() {
    return window.ascendState || { report: null, roles: [] };
}

/*=========================================================
    WAYPOINT 5 — "ALL 15 AI SUITE MODULES USED" TRACKING
=========================================================*/
const ALL_SUITE_FEATURES = [
    "recruiter-mode", "hiring-simulation", "time-machine", "career-story", "timeline", "career-twin", "eye-tracking", "confidence",
    "heatmap", "skill-radar", "salary", "career-gps", "compare-versions",
    "portfolio-review", "hr-summary", "career-risk", "achievement",
    "course-explorer",
    "stress-test", "resume-battle", "hidden-talent", "scorecard",
    "recruiter-psychology", "resume-evolution", "opportunity-radar",
    "hackathon-partner", "dream-company", "decision-explanation", "interview-replay",
];
const usedSuiteFeatures = new Set();

function noteSuiteFeatureUsed(key) {
    usedSuiteFeatures.add(key);
    if (usedSuiteFeatures.size >= ALL_SUITE_FEATURES.length && window.markWaypointDone) {
        window.markWaypointDone(5);
    }
}

function escapeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str == null ? "" : String(str);
    return div.innerHTML;
}

function showToast(message, type = "info") {
    if (window.__ascendShowToast) return window.__ascendShowToast(message, type);
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

function requireReport() {
    const report = getSharedState().report;
    if (!report) {
        showToast("Run the Resume Analyzer (Waypoint 01) first.", "error");
        return null;
    }
    return report;
}

function requireInterviewSession() {
    const session = getSharedState().interviewSession;
    if (!session) {
        showToast("Answer at least one question in the Interview module (Waypoint 02) first.", "error");
        return null;
    }
    return session;
}

function setScoreRing(ringEl, valueEl, percent, color = "var(--accent)") {
    if (!ringEl || !valueEl) return;
    const clamped = Math.max(0, Math.min(100, Math.round(percent)));
    const degrees = (clamped / 100) * 360;
    ringEl.style.background = `conic-gradient(${color} 0deg, ${color} ${degrees}deg, var(--surface-2) ${degrees}deg)`;
    valueEl.textContent = `${clamped}%`;
}

function renderList(el, items, emptyText = "Nothing to show.") {
    el.innerHTML = "";
    if (!items || !items.length) {
        el.innerHTML = `<li class="hint">${escapeHTML(emptyText)}</li>`;
        return;
    }
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        el.appendChild(li);
    });
}

function renderBarRows(el, items) {
    // items: [{label, value (0-100)}]
    el.innerHTML = "";
    items.forEach((item) => {
        const row = document.createElement("div");
        row.className = "bar-row";
        row.innerHTML = `
            <span class="bar-label">${escapeHTML(item.label)}</span>
            <span class="bar-track"><span class="bar-fill" style="width:${item.value}%"></span></span>
            <span class="bar-value">${item.value}%</span>
        `;
        el.appendChild(row);
    });
}

function renderChips(el, items, className = "") {
    el.innerHTML = "";
    if (!items || !items.length) {
        el.innerHTML = `<span class="hint">None detected.</span>`;
        return;
    }
    items.forEach((item) => {
        const chip = document.createElement("span");
        chip.className = `chip ${className}`.trim();
        chip.textContent = item;
        el.appendChild(chip);
    });
}

function renderCourseGroups(container, groups) {
    container.innerHTML = "";
    if (!groups || !groups.length) {
        container.innerHTML = `<span class="hint">No courses to show yet.</span>`;
        return;
    }
    groups.forEach((group) => {
        if (!group.courses || !group.courses.length) return;
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

async function withButtonLoading(btn, fn) {
    if (!btn) return fn();
    const original = btn.textContent;
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Working…`;
    try {
        return await fn();
    } finally {
        btn.disabled = false;
        btn.textContent = original;
    }
}

/*=========================================================
    TAB SWITCHING
=========================================================*/

function initTabs() {
    const tabs = document.querySelectorAll(".suite-tab");
    const panels = document.querySelectorAll(".suite-panel");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            panels.forEach((p) => p.classList.remove("active"));
            tab.classList.add("active");
            const panel = document.getElementById(`panel-${tab.dataset.suite}`);
            if (panel) panel.classList.add("active");
            panel.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    });
}

/*=========================================================
    ROLE SELECTS (shared across several panels)
=========================================================*/

async function populateSuiteRoleSelects() {
    const selectIds = ["ctRole", "srRole", "gpsRole", "spRole"];
    const selects = selectIds.map((id) => document.getElementById(id)).filter(Boolean);
    if (!selects.length) return;
    try {
        const roles = await getRoles();
        selects.forEach((select) => {
            roles.forEach((role) => {
                const opt = document.createElement("option");
                opt.value = role;
                opt.textContent = role;
                select.appendChild(opt);
            });
        });
    } catch (error) {
        console.error(error);
    }
}

/*=========================================================
    1. AI RECRUITER MODE
=========================================================*/

function initRecruiterMode() {
    const btn = document.getElementById("rmRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteRecruiterMode({ report_id: report.report_id });
                noteSuiteFeatureUsed("recruiter-mode");
                document.getElementById("rmEmpty").style.display = "none";
                document.getElementById("rmResult").style.display = "block";
                setScoreRing(document.getElementById("rmScoreRing"), document.getElementById("rmScoreValue"), data.first_impression_score);
                const verdictEl = document.getElementById("rmVerdict");
                verdictEl.textContent = data.verdict;
                verdictEl.className = "verdict-badge " + (data.verdict === "Shortlist" ? "good" : data.verdict === "Maybe pile" ? "warn" : "bad");
                document.getElementById("rmHeadline").textContent = data.headline;
                renderList(document.getElementById("rmPositives"), data.positive_signals);
                renderList(document.getElementById("rmFlags"), data.red_flags);
                renderChips(document.getElementById("rmScanOrder"), data.scan_order);
            } catch (error) {
                console.error(error);
                showToast("Could not run the recruiter scan.", "error");
            }
        });
    });
}

/*=========================================================
    2. AI HIRING SIMULATION
=========================================================*/

function initHiringSimulation() {
    const btn = document.getElementById("hsRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const state = getSharedState();
        const targetRole = state.selectedTargetRole || null;

        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteHiringSimulation({ report_id: report.report_id, target_role: targetRole });
                noteSuiteFeatureUsed("hiring-simulation");

                document.getElementById("hsEmpty").style.display = "none";
                document.getElementById("hsResult").style.display = "block";

                const [hr, tech, manager] = data.pipeline;

                // Stage 1 - HR Screening
                const hrVerdictEl = document.getElementById("hsHRVerdict");
                hrVerdictEl.textContent = hr.result;
                hrVerdictEl.className = "verdict-badge " + (hr.passed ? "good" : "warn");
                const hrList = document.getElementById("hsHRChecks");
                hrList.innerHTML = "";
                hr.checks.forEach((c) => {
                    const li = document.createElement("li");
                    li.textContent = (c.pass ? "✔ " : "✖ ") + c.label + " — " + c.detail;
                    li.style.color = c.pass ? "var(--mint)" : "var(--text-muted)";
                    hrList.appendChild(li);
                });

                // Stage 2 - Technical Lead Review
                setScoreRing(document.getElementById("hsTechScoreRing"), document.getElementById("hsTechScoreValue"), tech.score);
                const qList = document.getElementById("hsQuestions");
                qList.innerHTML = "";
                tech.questions.forEach((q) => {
                    const li = document.createElement("li");
                    li.textContent = q;
                    li.style.marginBottom = "6px";
                    qList.appendChild(li);
                });

                // Stage 3 - Hiring Committee
                setScoreRing(document.getElementById("hsChanceRing"), document.getElementById("hsChanceValue"), manager.chance_percent);
                const finalVerdictEl = document.getElementById("hsFinalVerdict");
                finalVerdictEl.textContent = manager.verdict;
                finalVerdictEl.className = "verdict-badge " + (manager.verdict === "Interview Call" ? "good" : manager.verdict === "Waitlisted" ? "warn" : "bad");
                renderList(document.getElementById("hsFactors"), manager.factors);

                // Reveal each stage in sequence, like a pipeline actually running.
                ["hsStageHR", "hsStageTech", "hsStageManager"].forEach((id, i) => {
                    const el = document.getElementById(id);
                    el.classList.remove("is-revealed");
                    setTimeout(() => el.classList.add("is-revealed"), i * 450);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not run the hiring simulation.", "error");
            }
        });
    });
}

/*=========================================================
    2b. AI CAREER TIME MACHINE
=========================================================*/

function initTimeMachine() {
    const btn = document.getElementById("tmRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const state = getSharedState();
        const targetRole = state.selectedTargetRole || null;

        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteTimeMachine({ report_id: report.report_id, target_role: targetRole });
                noteSuiteFeatureUsed("time-machine");

                document.getElementById("tmEmpty").style.display = "none";
                document.getElementById("tmResult").style.display = "block";
                document.getElementById("tmAssumption").textContent = data.assumption + " " + data.disclaimer;

                const track = document.getElementById("tmTrack");
                track.innerHTML = "";
                data.checkpoints.forEach((cp) => {
                    const row = document.createElement("div");
                    row.className = "tm-checkpoint";

                    const skillsLine = cp.newly_acquired_skills.length
                        ? `Newly acquired: <strong>${escapeHTML(cp.newly_acquired_skills.join(", "))}</strong>`
                        : "No new skills gained yet at this checkpoint.";
                    const companiesLine = cp.possible_companies.join(", ");

                    row.innerHTML = `
                        <div class="tm-checkpoint-label">${escapeHTML(cp.label)}<span class="tm-checkpoint-seniority">${escapeHTML(cp.seniority)}</span></div>
                        <div class="tm-checkpoint-body">
                            <div class="tm-checkpoint-row">Role fit: <strong>${cp.role_fit_percent}%</strong> · Projected resume score: <strong>${cp.projected_resume_score}%</strong></div>
                            <div class="tm-checkpoint-row">Expected salary: <strong>₹${cp.expected_salary_lpa.low}–${cp.expected_salary_lpa.high} LPA</strong></div>
                            <div class="tm-checkpoint-row">${skillsLine}</div>
                            <div class="tm-checkpoint-row">Possible companies: ${escapeHTML(companiesLine)}</div>
                        </div>
                    `;
                    track.appendChild(row);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not run the time machine.", "error");
            }
        });
    });
}

/*=========================================================
    AI RESUME STRESS TEST
=========================================================*/
function initStressTest() {
    const btn = document.getElementById("stRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteStressTest({ report_id: report.report_id });
                noteSuiteFeatureUsed("stress-test");
                document.getElementById("stEmpty").style.display = "none";
                document.getElementById("stResult").style.display = "block";
                const grid = document.getElementById("stGrid");
                grid.innerHTML = "";
                data.results.forEach((r) => {
                    const card = document.createElement("div");
                    card.className = "st-card";
                    card.innerHTML = `
                        <div class="st-company">${escapeHTML(r.company)}</div>
                        <div class="st-score">${r.score}%</div>
                        <div class="verdict-badge ${r.score >= 70 ? "good" : r.score >= 50 ? "warn" : "bad"}" style="margin:6px 0;">${escapeHTML(r.verdict)}</div>
                        <p class="hint" style="margin:0;">${escapeHTML(r.why)}</p>
                    `;
                    grid.appendChild(card);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not run the stress test.", "error");
            }
        });
    });
}

/*=========================================================
    AI RESUME BATTLE
=========================================================*/
function initResumeBattle() {
    const btn = document.getElementById("rbRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const fileA = document.getElementById("rbFileA").files[0];
        const fileB = document.getElementById("rbFileB").files[0];
        if (!fileA || !fileB) {
            showToast("Upload both resumes first.", "error");
            return;
        }
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteResumeBattle(fileA, fileB, "Resume A", "Resume B");
                noteSuiteFeatureUsed("resume-battle");
                document.getElementById("rbEmpty").style.display = "none";
                document.getElementById("rbResult").style.display = "block";

                const overallEl = document.getElementById("rbOverall");
                overallEl.textContent = data.overall_winner === "Tie" ? "Tie" : `Winner: ${data.overall_winner}`;
                overallEl.className = "verdict-badge " + (data.overall_winner === "Tie" ? "warn" : "good");

                const catsEl = document.getElementById("rbCategories");
                catsEl.innerHTML = "";
                data.categories.forEach((c) => {
                    const row = document.createElement("div");
                    row.className = "bar-row";
                    row.innerHTML = `
                        <span class="bar-label">${escapeHTML(c.category)}</span>
                        <span class="bar-track"><span class="bar-fill" style="width:${Math.max(c.value_a, c.value_b)}%"></span></span>
                        <span class="bar-value">${escapeHTML(c.winner)}</span>
                    `;
                    catsEl.appendChild(row);
                });

                renderChips(document.getElementById("rbOnlyA"), data.skills_only_in_a);
                renderChips(document.getElementById("rbOnlyB"), data.skills_only_in_b);
            } catch (error) {
                console.error(error);
                showToast("Could not run the battle.", "error");
            }
        });
    });
}

/*=========================================================
    HIDDEN TALENT DETECTOR
=========================================================*/
function initHiddenTalent() {
    const btn = document.getElementById("htRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteHiddenTalent({ report_id: report.report_id });
                noteSuiteFeatureUsed("hidden-talent");
                document.getElementById("htEmpty").style.display = "none";
                document.getElementById("htResult").style.display = "block";
                renderChips(document.getElementById("htTalents"), data.detected_talents);
                const rolesEl = document.getElementById("htRoles");
                rolesEl.innerHTML = "";
                data.recommended_roles.forEach((r) => {
                    const li = document.createElement("li");
                    li.textContent = `${r.role} — ${r.fit_percent}% fit`;
                    rolesEl.appendChild(li);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not detect hidden talents.", "error");
            }
        });
    });
}

/*=========================================================
    AI CAREER SCORE CARD
=========================================================*/
function initScorecard() {
    const btn = document.getElementById("scRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteScorecard({ report_id: report.report_id });
                noteSuiteFeatureUsed("scorecard");
                document.getElementById("scEmpty").style.display = "none";
                document.getElementById("scResult").style.display = "block";
                const items = Object.entries(data.career_dna).map(([label, value]) => ({ label, value }));
                renderBarRows(document.getElementById("scBars"), items);
                document.getElementById("scStrong").textContent = data.strongest;
                document.getElementById("scWeak").textContent = data.weakest;
            } catch (error) {
                console.error(error);
                showToast("Could not generate the score card.", "error");
            }
        });
    });
}

/*=========================================================
    AI RECRUITER PSYCHOLOGY
=========================================================*/
function initRecruiterPsychology() {
    const btn = document.getElementById("rpRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteRecruiterPsychology({ report_id: report.report_id });
                noteSuiteFeatureUsed("recruiter-psychology");
                document.getElementById("rpEmpty").style.display = "none";
                document.getElementById("rpResult").style.display = "block";
                renderChips(document.getElementById("rpLookedAt"), data.looked_at);
                renderChips(document.getElementById("rpIgnored"), data.ignored);
                document.getElementById("rpTip").textContent = data.tip;
                document.getElementById("rpTimer").textContent = data.scan_seconds + "s";

                // Animate the scan bar filling over the actual scan duration.
                const fill = document.getElementById("rpBarFill");
                fill.style.transition = "none";
                fill.style.width = "0%";
                void fill.offsetWidth; // force reflow so the transition restarts
                fill.style.transition = `width ${data.scan_seconds}s linear`;
                requestAnimationFrame(() => { fill.style.width = "100%"; });
            } catch (error) {
                console.error(error);
                showToast("Could not run the scan simulation.", "error");
            }
        });
    });
}

/*=========================================================
    AI RESUME EVOLUTION
=========================================================*/
function initResumeEvolution() {
    const btn = document.getElementById("reRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteResumeEvolution({ report_id: report.report_id });
                noteSuiteFeatureUsed("resume-evolution");
                document.getElementById("reEmpty").style.display = "none";
                document.getElementById("reResult").style.display = "block";
                document.getElementById("reTotalGain").textContent = data.total_projected_gain;

                const track = document.getElementById("reTrack");
                track.innerHTML = "";
                data.stages.forEach((s) => {
                    const row = document.createElement("div");
                    row.className = "tm-checkpoint";
                    row.innerHTML = `
                        <div class="tm-checkpoint-label">${s.ats_score}%</div>
                        <div class="tm-checkpoint-body">
                            <div class="tm-checkpoint-row"><strong>${escapeHTML(s.label)}</strong></div>
                            ${s.change ? `<div class="tm-checkpoint-row" style="color:var(--mint);">${escapeHTML(s.change)}</div>` : ""}
                        </div>
                    `;
                    track.appendChild(row);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not build the evolution path.", "error");
            }
        });
    });
}

/*=========================================================
    AI OPPORTUNITY RADAR
=========================================================*/
function initOpportunityRadar() {
    const btn = document.getElementById("orRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteOpportunityRadar({ report_id: report.report_id });
                noteSuiteFeatureUsed("opportunity-radar");
                document.getElementById("orEmpty").style.display = "none";
                document.getElementById("orResult").style.display = "block";
                const items = Object.entries(data.radar).map(([label, value]) => ({ label, value }));
                renderBarRows(document.getElementById("orBars"), items);
                document.getElementById("orTop").textContent = data.top_opportunity;
            } catch (error) {
                console.error(error);
                showToast("Could not scan opportunities.", "error");
            }
        });
    });
}

/*=========================================================
    HACKATHON PARTNER FINDER
=========================================================*/
function initHackathonPartner() {
    const btn = document.getElementById("hpRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteHackathonPartner({ report_id: report.report_id });
                noteSuiteFeatureUsed("hackathon-partner");
                document.getElementById("hpEmpty").style.display = "none";
                document.getElementById("hpResult").style.display = "block";
                renderChips(document.getElementById("hpStrengths"), data.your_strengths);
                renderChips(document.getElementById("hpCovers"), data.ideal_teammate_covers);
            } catch (error) {
                console.error(error);
                showToast("Could not compute teammate gaps.", "error");
            }
        });
    });
}

/*=========================================================
    DREAM COMPANY SIMULATOR
=========================================================*/
function initDreamCompany() {
    const btn = document.getElementById("dcRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const company = document.getElementById("dcCompany").value;
        const state = getSharedState();
        const targetRole = state.selectedTargetRole || null;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteDreamCompany({ report_id: report.report_id, company, target_role: targetRole });
                noteSuiteFeatureUsed("dream-company");
                document.getElementById("dcEmpty").style.display = "none";
                document.getElementById("dcResult").style.display = "block";
                setScoreRing(document.getElementById("dcRing"), document.getElementById("dcMatchValue"), data.current_match_percent);
                document.getElementById("dcReady").textContent = data.estimated_ready_months;
                renderChips(document.getElementById("dcNeed"), data.need);
                document.getElementById("dcDisclaimer").textContent = data.disclaimer;
            } catch (error) {
                console.error(error);
                showToast("Could not run the dream company simulation.", "error");
            }
        });
    });
}

/*=========================================================
    AI RECRUITER DECISION EXPLANATION
=========================================================*/
function initDecisionExplanation() {
    const btn = document.getElementById("deRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteDecisionExplanation({ report_id: report.report_id });
                noteSuiteFeatureUsed("decision-explanation");
                document.getElementById("deEmpty").style.display = "none";
                document.getElementById("deResult").style.display = "block";
                setScoreRing(document.getElementById("deRing"), document.getElementById("deScoreValue"), data.current_ats_score);
                const verdictEl = document.getElementById("deVerdict");
                verdictEl.textContent = data.current_verdict;
                verdictEl.className = "verdict-badge " + (data.current_ats_score >= 75 ? "good" : data.current_ats_score >= 50 ? "warn" : "bad");
                document.getElementById("deTotalGain").textContent = data.estimated_improvement_total;

                const issuesEl = document.getElementById("deIssues");
                issuesEl.innerHTML = "";
                data.issues.forEach((iss) => {
                    const li = document.createElement("li");
                    li.textContent = `${iss.issue} (${iss.category}: ${iss.current_score}%) — fixing this could earn back +${iss.estimated_ats_gain} ATS points.`;
                    issuesEl.appendChild(li);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not explain the decision.", "error");
            }
        });
    });
}

/*=========================================================
    AI INTERVIEW REPLAY
=========================================================*/
function initInterviewReplay() {
    const btn = document.getElementById("irRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const session = requireInterviewSession();
        if (!session) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await getInterviewReplay(session.id);
                if (!data.markers || !data.markers.length) {
                    showToast("No answers recorded yet - answer at least one question first.", "error");
                    return;
                }
                noteSuiteFeatureUsed("interview-replay");
                document.getElementById("irEmpty").style.display = "none";
                document.getElementById("irResult").style.display = "block";

                const total = data.total_estimated_seconds || 1;
                const scrubber = document.getElementById("irScrubber");
                scrubber.innerHTML = "";
                data.markers.forEach((m) => {
                    const seg = document.createElement("div");
                    const widthPercent = Math.max(2, ((m.end_seconds - m.start_seconds) / total) * 100);
                    seg.className = "ir-segment " + m.tag;
                    seg.style.width = widthPercent + "%";
                    seg.title = `${m.start_seconds}s–${m.end_seconds}s: ${m.note}`;
                    scrubber.appendChild(seg);
                });

                const markersEl = document.getElementById("irMarkers");
                markersEl.innerHTML = "";
                data.markers.forEach((m) => {
                    const row = document.createElement("div");
                    row.className = "ir-marker " + m.tag;
                    row.innerHTML = `
                        <div class="ir-marker-time">${Math.floor(m.start_seconds / 60)}:${String(m.start_seconds % 60).padStart(2, "0")}</div>
                        <div class="ir-marker-tag">${escapeHTML(m.tag)}</div>
                        <div class="ir-marker-body"><strong>${escapeHTML(m.question)}</strong>${escapeHTML(m.note)} (${m.word_count} words, score ${m.score}%)</div>
                    `;
                    markersEl.appendChild(row);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not build the interview replay.", "error");
            }
        });
    });
}

/*=========================================================
    3. AI CAREER STORY
=========================================================*/

function initCareerStory() {
    const btn = document.getElementById("csRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const state = getSharedState();
        const targetRole = state.selectedTargetRole || null;

        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteCareerStory({ report_id: report.report_id, target_role: targetRole });
                noteSuiteFeatureUsed("career-story");
                document.getElementById("csEmpty").style.display = "none";
                document.getElementById("csResult").style.display = "block";
                document.getElementById("csStageLabel").textContent =
                    "Current stage: " + data.stage + (data.used_llm ? " · Claude-authored" : "");
                document.getElementById("csStory").textContent = data.story;
            } catch (error) {
                console.error(error);
                showToast("Could not generate the career story.", "error");
            }
        });
    });
}

/*=========================================================
    2. RESUME TIMELINE PREDICTION
=========================================================*/

function initTimeline() {
    const btn = document.getElementById("tlRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const appsPerWeek = parseInt(document.getElementById("tlApps").value, 10) || 10;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteTimeline({ report_id: report.report_id, applications_per_week: appsPerWeek });
                noteSuiteFeatureUsed("timeline");
                document.getElementById("tlEmpty").style.display = "none";
                document.getElementById("tlResult").style.display = "block";
                document.getElementById("tlStrength").textContent = data.profile_strength;
                document.getElementById("tlCallback").textContent = `${data.estimated_callback_rate_percent}%`;
                document.getElementById("tlInterview").textContent = `${data.estimated_interview_rate_percent}%`;
                document.getElementById("tlDisclaimer").textContent = data.disclaimer;

                const track = document.getElementById("tlMilestones");
                track.innerHTML = "";
                data.milestones.forEach((m) => {
                    const item = document.createElement("div");
                    item.className = "timeline-item";
                    item.innerHTML = `
                        <div class="tl-week">Week ${m.week}</div>
                        <h4>${escapeHTML(m.label)}</h4>
                        <p>${escapeHTML(m.detail)}</p>
                    `;
                    track.appendChild(item);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not predict the timeline.", "error");
            }
        });
    });
}

/*=========================================================
    3. AI CAREER TWIN
=========================================================*/

function initCareerTwin() {
    const btn = document.getElementById("ctRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const targetRole = document.getElementById("ctRole").value || null;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteCareerTwin({ report_id: report.report_id, target_role: targetRole });
                noteSuiteFeatureUsed("career-twin");
                document.getElementById("ctEmpty").style.display = "none";
                document.getElementById("ctResult").style.display = "block";
                document.getElementById("ctStage").textContent = data.current_stage;
                document.getElementById("ctRoleMatch").textContent = data.closest_role_match;
                document.getElementById("ctRoleMatchPct").textContent = `${data.role_match_percent}% fit`;
                document.getElementById("ctNarrative").textContent = data.narrative;

                const path = document.getElementById("ctPath");
                path.innerHTML = "";
                data.growth_path.forEach((step) => {
                    const el = document.createElement("div");
                    el.className = "twin-step";
                    el.innerHTML = `
                        <div class="twin-years">+${step.years_out} YEAR${step.years_out > 1 ? "S" : ""}</div>
                        <h4>${escapeHTML(step.title_estimate)}</h4>
                        <p>${escapeHTML(step.focus)}</p>
                    `;
                    path.appendChild(el);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not generate your career twin.", "error");
            }
        });
    });
}

/*=========================================================
    4. RECRUITER EYE TRACKING
=========================================================*/

function initEyeTracking() {
    const btn = document.getElementById("etRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteEyeTracking({ report_id: report.report_id });
                noteSuiteFeatureUsed("eye-tracking");
                document.getElementById("etEmpty").style.display = "none";
                document.getElementById("etResult").style.display = "block";
                document.getElementById("etPattern").textContent = data.pattern;
                document.getElementById("etTip").textContent = data.tip;

                const zonesEl = document.getElementById("etZones");
                zonesEl.innerHTML = "";
                data.zones.forEach((z) => {
                    const row = document.createElement("div");
                    row.className = "bar-row";
                    row.innerHTML = `
                        <span class="bar-label">${escapeHTML(z.zone)}${z.present ? "" : " (missing)"}</span>
                        <span class="bar-track"><span class="bar-fill" style="width:${z.attention_percent}%"></span></span>
                        <span class="bar-value">${z.attention_percent}%</span>
                    `;
                    zonesEl.appendChild(row);
                });
                renderChips(document.getElementById("etDeadZones"), data.dead_zones, "missing");
            } catch (error) {
                console.error(error);
                showToast("Could not run the eye-tracking simulation.", "error");
            }
        });
    });
}

/*=========================================================
    6. LIVE CONFIDENCE METER (standalone panel)
=========================================================*/

function initConfidenceMeter() {
    const btn = document.getElementById("cmRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const text = document.getElementById("cmText").value.trim();
        if (!text) {
            showToast("Paste some text to analyze first.", "error");
            return;
        }
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteConfidence(text);
                noteSuiteFeatureUsed("confidence");
                document.getElementById("cmEmpty").style.display = "none";
                document.getElementById("cmResult").style.display = "block";
                const color = data.confidence_level === "Confident" ? "var(--mint)" : data.confidence_level === "Hesitant" ? "var(--danger)" : "var(--accent)";
                setScoreRing(document.getElementById("cmRing"), document.getElementById("cmScoreValue"), data.confidence_score, color);
                document.getElementById("cmLevel").textContent = data.confidence_level;
                document.getElementById("cmHedges").textContent = data.hedging_phrases_detected;
                document.getElementById("cmFillers").textContent = data.filler_words_detected;
                document.getElementById("cmAssertive").textContent = data.assertive_statements_detected;
                renderList(document.getElementById("cmTips"), data.tips);
            } catch (error) {
                console.error(error);
                showToast("Could not analyze that text.", "error");
            }
        });
    });
}

/*=========================================================
    7. AI RESUME HEATMAP
=========================================================*/

function initHeatmap() {
    const btn = document.getElementById("hmRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteHeatmap({ report_id: report.report_id });
                noteSuiteFeatureUsed("heatmap");
                document.getElementById("hmEmpty").style.display = "none";
                document.getElementById("hmResult").style.display = "block";
                document.getElementById("hmWeakest").textContent = data.weakest_zone;
                document.getElementById("hmDensity").textContent = `${data.skill_keyword_density}%`;

                const grid = document.getElementById("hmGrid");
                grid.innerHTML = "";
                data.heatmap.forEach((cell) => {
                    const div = document.createElement("div");
                    div.className = `heat-cell ${cell.band}`;
                    div.innerHTML = `<div class="heat-section">${escapeHTML(cell.section)}</div><div class="heat-score">${cell.score}</div>`;
                    grid.appendChild(div);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not generate the heatmap.", "error");
            }
        });
    });
}

/*=========================================================
    8. AI SKILL RADAR
=========================================================*/

function initSkillRadar() {
    const btn = document.getElementById("srRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        const targetRole = document.getElementById("srRole").value || null;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteSkillRadar({ skills: report.skills_found, target_role: targetRole });
                noteSuiteFeatureUsed("skill-radar");
                document.getElementById("srEmpty").style.display = "none";
                document.getElementById("srResult").style.display = "block";
                document.getElementById("srStrong").textContent = data.strongest_area || "—";
                document.getElementById("srWeak").textContent = data.weakest_area || "—";
                const roleFitWrap = document.getElementById("srRoleFitWrap");
                if (data.target_role_fit_percent !== null && data.target_role_fit_percent !== undefined) {
                    roleFitWrap.style.display = "inline";
                    document.getElementById("srRoleFit").textContent = `${data.target_role_fit_percent}%`;
                } else {
                    roleFitWrap.style.display = "none";
                }

                const axesEl = document.getElementById("srAxes");
                axesEl.innerHTML = "";
                data.axes.forEach((axis) => {
                    const row = document.createElement("div");
                    row.className = "bar-row";
                    const title = axis.skills.length ? `${axis.category} (${axis.skills.join(", ")})` : axis.category;
                    row.innerHTML = `
                        <span class="bar-label">${escapeHTML(title)}</span>
                        <span class="bar-track"><span class="bar-fill" style="width:${axis.score}%"></span></span>
                        <span class="bar-value">${axis.score}%</span>
                    `;
                    axesEl.appendChild(row);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not generate the skill radar.", "error");
            }
        });
    });
}

/*=========================================================
    9. PERSONALIZED SALARY PREDICTION
=========================================================*/

function initSalary() {
    const btn = document.getElementById("spRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const skills = getSharedState().report ? getSharedState().report.skills_found : [];
        const targetRole = document.getElementById("spRole").value || null;
        const experienceYears = parseFloat(document.getElementById("spExp").value) || 0;
        const locationTier = document.getElementById("spLocation").value;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteSalary({ skills, target_role: targetRole, experience_years: experienceYears, location_tier: locationTier });
                noteSuiteFeatureUsed("salary");
                document.getElementById("spEmpty").style.display = "none";
                document.getElementById("spResult").style.display = "block";
                document.getElementById("spRoleOut").textContent = data.target_role;
                document.getElementById("spRange").textContent = `₹${data.estimated_range_lpa.low} – ₹${data.estimated_range_lpa.high} LPA`;
                document.getElementById("spDisclaimer").textContent = data.disclaimer;
            } catch (error) {
                console.error(error);
                showToast("Could not predict a salary range.", "error");
            }
        });
    });
}

/*=========================================================
    10. AI CAREER GPS
=========================================================*/

function initCareerGPS() {
    const btn = document.getElementById("gpsRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const targetRole = document.getElementById("gpsRole").value;
        if (!targetRole) {
            showToast("Choose a destination role first.", "error");
            return;
        }
        const skills = getSharedState().report ? getSharedState().report.skills_found : [];
        const hours = parseInt(document.getElementById("gpsHours").value, 10) || 8;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteCareerGPS({ skills, target_role: targetRole, hours_per_week: hours });
                noteSuiteFeatureUsed("career-gps");
                document.getElementById("gpsEmpty").style.display = "none";
                document.getElementById("gpsResult").style.display = "block";
                document.getElementById("gpsCurrent").textContent = `${data.current_location_percent}%`;
                document.getElementById("gpsRemaining").textContent = data.distance_skills_remaining;
                document.getElementById("gpsEta").textContent = data.total_eta_weeks;

                const dirEl = document.getElementById("gpsDirections");
                dirEl.innerHTML = "";
                data.directions.forEach((d) => {
                    const step = document.createElement("div");
                    step.className = "gps-step";
                    step.innerHTML = `
                        <div class="gps-num">${d.step}</div>
                        <div>
                            <p>${escapeHTML(d.instruction)}</p>
                            <div class="gps-eta">${escapeHTML(d.phase)} · ETA week ${d.eta_week}</div>
                        </div>
                    `;
                    dirEl.appendChild(step);
                });
            } catch (error) {
                console.error(error);
                showToast("Could not build the career GPS route.", "error");
            }
        });
    });
}

/*=========================================================
    11. RESUME VERSION COMPARISON
=========================================================*/

function initFileDrop(dropId, inputId, nameId) {
    const drop = document.getElementById(dropId);
    const input = document.getElementById(inputId);
    const nameEl = document.getElementById(nameId);
    if (!drop || !input) return;
    input.addEventListener("change", () => {
        nameEl.textContent = input.files.length ? `Selected: ${input.files[0].name}` : "";
    });
    ["dragover", "dragleave", "drop"].forEach((evt) => {
        drop.addEventListener(evt, (e) => {
            e.preventDefault();
            drop.classList.toggle("dragover", evt === "dragover");
        });
    });
    drop.addEventListener("drop", (e) => {
        if (e.dataTransfer.files.length) {
            input.files = e.dataTransfer.files;
            nameEl.textContent = `Selected: ${input.files[0].name}`;
        }
    });
}

function initCompareVersions() {
    initFileDrop("cvDropA", "cvFileA", "cvFileANameDisplay");
    initFileDrop("cvDropB", "cvFileB", "cvFileBNameDisplay");

    const btn = document.getElementById("cvRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const fileA = document.getElementById("cvFileA").files[0];
        const fileB = document.getElementById("cvFileB").files[0];
        if (!fileA || !fileB) {
            showToast("Upload both resume versions first.", "error");
            return;
        }
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteCompareVersions(fileA, fileB);
                noteSuiteFeatureUsed("compare-versions");
                if (data.error) {
                    showToast(data.error, "error");
                    return;
                }
                document.getElementById("cvEmpty").style.display = "none";
                document.getElementById("cvResult").style.display = "block";
                document.getElementById("cvAtsA").textContent = data.version_a.ats_score;
                document.getElementById("cvAtsB").textContent = data.version_b.ats_score;
                const deltaEl = document.getElementById("cvDelta");
                deltaEl.textContent = (data.ats_score_delta > 0 ? "+" : "") + data.ats_score_delta;
                const verdictEl = document.getElementById("cvVerdict");
                verdictEl.textContent = data.verdict;
                verdictEl.className = "verdict-badge " + (data.ats_score_delta > 0 ? "good" : data.ats_score_delta < 0 ? "bad" : "warn");
                renderChips(document.getElementById("cvAdded"), data.skills_added_in_b, "matched");
                renderChips(document.getElementById("cvRemoved"), data.skills_removed_in_b, "missing");
            } catch (error) {
                console.error(error);
                showToast("Could not compare the two resumes.", "error");
            }
        });
    });
}

/*=========================================================
    12. AI PORTFOLIO REVIEW
=========================================================*/

function initPortfolioReview() {
    const btn = document.getElementById("prRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const text = document.getElementById("prText").value.trim();
        if (!text) {
            showToast("Paste your portfolio/project text first.", "error");
            return;
        }
        await withButtonLoading(btn, async () => {
            try {
                const data = await suitePortfolioReview(text);
                noteSuiteFeatureUsed("portfolio-review");
                document.getElementById("prEmpty").style.display = "none";
                document.getElementById("prResult").style.display = "block";
                setScoreRing(document.getElementById("prRing"), document.getElementById("prScoreValue"), data.completeness_score, "var(--mint)");
                renderChips(document.getElementById("prTechStack"), data.tech_stack_detected);
                const aiCard = document.getElementById("prAICard");
                if (data.ai_review) {
                    aiCard.style.display = "block";
                    document.getElementById("prAIReview").textContent = data.ai_review;
                } else {
                    aiCard.style.display = "none";
                }
                renderList(document.getElementById("prSuggestions"), data.suggestions);
            } catch (error) {
                console.error(error);
                showToast("Could not review the portfolio text.", "error");
            }
        });
    });
}

/*=========================================================
    13. ONE-CLICK HR SUMMARY
=========================================================*/

function initHRSummary() {
    const btn = document.getElementById("hrRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const report = requireReport();
        if (!report) return;
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteHRSummary({ report_id: report.report_id });
                noteSuiteFeatureUsed("hr-summary");
                document.getElementById("hrEmpty").style.display = "none";
                document.getElementById("hrResult").style.display = "block";
                document.getElementById("hrSummaryText").textContent = data.summary;
                document.getElementById("hrStage").textContent = data.quick_facts.seniority_stage;
                document.getElementById("hrAts").textContent = data.quick_facts.ats_score;
                document.getElementById("hrSkills").textContent = data.quick_facts.skills_detected;
            } catch (error) {
                console.error(error);
                showToast("Could not generate the HR summary.", "error");
            }
        });
    });
}

/*=========================================================
    14. AI CAREER RISK SCORE
=========================================================*/

function initCareerRisk() {
    const btn = document.getElementById("crsRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const skills = getSharedState().report ? getSharedState().report.skills_found : [];
        if (!skills.length) {
            showToast("Run the Resume Analyzer (Waypoint 01) first.", "error");
            return;
        }
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteCareerRisk({ skills });
                noteSuiteFeatureUsed("career-risk");
                document.getElementById("crsEmpty").style.display = "none";
                document.getElementById("crsResult").style.display = "block";
                const color = data.risk_level === "Low" ? "var(--mint)" : data.risk_level === "High" ? "var(--danger)" : "var(--accent)";
                setScoreRing(document.getElementById("crsRing"), document.getElementById("crsScoreValue"), data.risk_score, color);
                const levelEl = document.getElementById("crsLevel");
                levelEl.textContent = `${data.risk_level} risk`;
                levelEl.className = "verdict-badge " + (data.risk_level === "Low" ? "good" : data.risk_level === "High" ? "bad" : "warn");
                document.getElementById("crsDiversity").textContent = `${data.category_diversity} categories`;
                renderList(document.getElementById("crsFactors"), data.factors);
                renderList(document.getElementById("crsRecs"), data.recommendations);
            } catch (error) {
                console.error(error);
                showToast("Could not calculate the career risk score.", "error");
            }
        });
    });
}

/*=========================================================
    15. AI ACHIEVEMENT GENERATOR
=========================================================*/

function initAchievementGenerator() {
    const btn = document.getElementById("agRunBtn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
        const bulletText = document.getElementById("agBullet").value.trim();
        const skillContext = document.getElementById("agSkill").value.trim() || null;
        if (!bulletText) {
            showToast("Enter a bullet point first.", "error");
            return;
        }
        await withButtonLoading(btn, async () => {
            try {
                const data = await suiteAchievement({ bullet_text: bulletText, skill_context: skillContext });
                noteSuiteFeatureUsed("achievement");
                document.getElementById("agEmpty").style.display = "none";
                document.getElementById("agResult").style.display = "block";
                document.getElementById("agRule").textContent = data.rule_based_rewrite;
                document.getElementById("agXYZ").textContent = data.xyz_formula_rewrite;
                const aiCard = document.getElementById("agAICard");
                if (data.ai_rewrite) {
                    aiCard.style.display = "block";
                    document.getElementById("agAI").textContent = data.ai_rewrite;
                } else {
                    aiCard.style.display = "none";
                }
                document.getElementById("agTip").textContent = data.tip;
            } catch (error) {
                console.error(error);
                showToast("Could not rewrite that bullet point.", "error");
            }
        });
    });
}

/*=========================================================
    COURSE EXPLORER
=========================================================*/

let fullCatalog = null;

async function initCourseExplorer() {
    const domainSelect = document.getElementById("ceDomain");
    const browseBtn = document.getElementById("ceBrowseBtn");
    const recommendBtn = document.getElementById("ceRecommendBtn");
    if (!domainSelect || !browseBtn) return;

    try {
        fullCatalog = await getCourseCatalog();
        fullCatalog.domains.forEach((domain) => {
            const opt = document.createElement("option");
            opt.value = domain;
            opt.textContent = domain;
            domainSelect.appendChild(opt);
        });
    } catch (error) {
        console.error(error);
    }

    browseBtn.addEventListener("click", () => {
        if (!fullCatalog) return;
        const domain = domainSelect.value;
        const courses = fullCatalog.catalog[domain] || [];
        document.getElementById("ceEmpty").style.display = "none";
        document.getElementById("ceResult").style.display = "block";
        renderCourseGroups(document.getElementById("ceGroups"), [{ domain, courses }]);
    });

    recommendBtn.addEventListener("click", async () => {
        const report = getSharedState().report;
        if (!report || !report.skills_found || !report.skills_found.length) {
            showToast("Run the Resume Analyzer (Waypoint 01) first for personalized picks.", "error");
            return;
        }
        await withButtonLoading(recommendBtn, async () => {
            try {
                const data = await getCoursesForSkills({ skills: report.skills_found, limit_domains: 3, limit_per_domain: 4 });
                noteSuiteFeatureUsed("course-explorer");
                document.getElementById("ceEmpty").style.display = "none";
                document.getElementById("ceResult").style.display = "block";
                renderCourseGroups(document.getElementById("ceGroups"), data.recommendations);
            } catch (error) {
                console.error(error);
                showToast("Could not fetch recommended courses.", "error");
            }
        });
    });
}

/*=========================================================
    AI DIGITAL RECRUITER (floating avatar)
    Fires automatically off the same "ascend:report" event app.js
    already dispatches after a successful analysis - no app.js
    changes needed.
=========================================================*/

function showDigitalRecruiter(data) {
    const widget = document.getElementById("digitalRecruiterWidget");
    if (!widget) return;

    document.getElementById("drMessage").textContent = data.greeting;
    const actionBtn = document.getElementById("drActionBtn");

    if (data.action) {
        actionBtn.textContent = data.action.label;
        actionBtn.style.display = "inline-block";
        actionBtn.onclick = () => {
            document.getElementById("ai-suite").scrollIntoView({ behavior: "smooth", block: "start" });
            const tabBtn = document.querySelector(`.suite-tab[data-suite="${data.action.suite_tab}"]`);
            if (tabBtn) tabBtn.click();
            widget.style.display = "none";
        };
    } else {
        actionBtn.style.display = "none";
    }

    widget.style.display = "block";
}

function initDigitalRecruiter() {
    const closeBtn = document.getElementById("drCloseBtn");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            document.getElementById("digitalRecruiterWidget").style.display = "none";
        });
    }

    window.addEventListener("ascend:report", async (e) => {
        const report = e.detail;
        if (!report) return;
        try {
            const data = await suiteDigitalRecruiter({ report_id: report.report_id });
            showDigitalRecruiter(data);
        } catch (error) {
            console.error(error);
        }
    });
}

/*=========================================================
    INIT
=========================================================*/

window.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("ai-suite")) return;
    initTabs();
    populateSuiteRoleSelects();
    initRecruiterMode();
    initHiringSimulation();
    initTimeMachine();
    initStressTest();
    initResumeBattle();
    initHiddenTalent();
    initScorecard();
    initRecruiterPsychology();
    initResumeEvolution();
    initOpportunityRadar();
    initHackathonPartner();
    initDreamCompany();
    initDecisionExplanation();
    initInterviewReplay();
    initCareerStory();
    initDigitalRecruiter();
    initTimeline();
    initCareerTwin();
    initEyeTracking();
    initConfidenceMeter();
    initHeatmap();
    initSkillRadar();
    initSalary();
    initCareerGPS();
    initCompareVersions();
    initPortfolioReview();
    initHRSummary();
    initCareerRisk();
    initAchievementGenerator();
    initCourseExplorer();
});