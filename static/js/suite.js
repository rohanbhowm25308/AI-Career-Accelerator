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
    suiteRecruiterMode, suiteTimeline, suiteCareerTwin, suiteEyeTracking,
    suiteConfidence, suiteHeatmap, suiteSkillRadar, suiteSalary,
    suiteCareerGPS, suiteCompareVersions, suitePortfolioReview,
    suiteHRSummary, suiteCareerRisk, suiteAchievement,
    getCourseCatalog, getCoursesForSkills,
} from "./api.js";

function getSharedState() {
    return window.ascendState || { report: null, roles: [] };
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
    INIT
=========================================================*/

window.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("ai-suite")) return;
    initTabs();
    populateSuiteRoleSelects();
    initRecruiterMode();
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