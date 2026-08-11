/*=========================================================
    Ascend — trajectory.js
    Signature hero visual: an ascending flight path with four
    waypoint markers (Analyze / Interview / Roadmap / Match) and
    a glowing pulse that travels the route on a loop. This is the
    one visual idea the whole product returns to — the waypoint
    strip and progress bars all echo it.
=========================================================*/

(function () {
    "use strict";

    const canvas = document.getElementById("trajectoryCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const AMBER = "#FFB020";
    const MINT = "#47E0A6";
    const MUTED = "#8D96B3";

    const LABELS = ["Analyze", "Interview", "Roadmap", "Match"];
    const T_STOPS = [0.06, 0.36, 0.66, 0.95];

    let width, height, dpr;
    let pathPoints = [];
    let stars = [];
    let pulseT = 0;

    function hexToRgba(hex, a) {
        const c = hex.replace("#", "");
        const r = parseInt(c.substring(0, 2), 16);
        const g = parseInt(c.substring(2, 4), 16);
        const b = parseInt(c.substring(4, 6), 16);
        return `rgba(${r},${g},${b},${a})`;
    }

    // Ascending curve from bottom-left to top-right, normalized 0-1 space,
    // with a gentle S-curve so it doesn't read as a straight diagonal.
    function buildPath() {
        const ctrl = [
            { x: 0.06, y: 0.92 },
            { x: 0.28, y: 0.78 },
            { x: 0.36, y: 0.55 },
            { x: 0.58, y: 0.50 },
            { x: 0.66, y: 0.30 },
            { x: 0.86, y: 0.20 },
            { x: 0.95, y: 0.08 },
        ];
        const pts = [];
        const steps = 200;
        for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            pts.push(bezierChain(ctrl, t));
        }
        pathPoints = pts;
    }

    // Catmull-Rom-ish smoothing across the control points for a fluid curve.
    function bezierChain(pts, t) {
        const n = pts.length - 1;
        const segT = t * n;
        const i = Math.min(Math.floor(segT), n - 1);
        const localT = segT - i;
        const p0 = pts[Math.max(i - 1, 0)];
        const p1 = pts[i];
        const p2 = pts[Math.min(i + 1, n)];
        const p3 = pts[Math.min(i + 2, n)];
        return catmullRom(p0, p1, p2, p3, localT);
    }

    function catmullRom(p0, p1, p2, p3, t) {
        const t2 = t * t, t3 = t2 * t;
        const x = 0.5 * ((2 * p1.x) + (-p0.x + p2.x) * t + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3);
        const y = 0.5 * ((2 * p1.y) + (-p0.y + p2.y) * t + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3);
        return { x, y };
    }

    function pointAt(t) {
        const clamped = Math.max(0, Math.min(1, t));
        const idx = Math.min(Math.floor(clamped * (pathPoints.length - 1)), pathPoints.length - 1);
        return pathPoints[idx];
    }

    function buildStars() {
        stars = [];
        for (let i = 0; i < 46; i++) {
            stars.push({
                x: Math.random(), y: Math.random(),
                r: Math.random() * 1.3 + 0.4,
                phase: Math.random() * Math.PI * 2,
                speed: Math.random() * 0.6 + 0.3,
            });
        }
    }

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        const parent = canvas.parentElement;
        const parentWidth = parent ? parent.getBoundingClientRect().width : 480;
        width = Math.max(280, Math.min(560, parentWidth));
        height = width * (520 / 560);

        canvas.style.width = width + "px";
        canvas.style.height = height + "px";
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        buildPath();
        buildStars();
    }

    function P(pt) {
        return { x: pt.x * width, y: pt.y * height };
    }

    function drawStars(time) {
        for (const s of stars) {
            const twinkle = 0.35 + 0.35 * Math.sin(time * 0.0012 * s.speed + s.phase);
            ctx.beginPath();
            ctx.arc(s.x * width, s.y * height, s.r, 0, Math.PI * 2);
            ctx.fillStyle = hexToRgba(MUTED, 0.25 * twinkle + 0.08);
            ctx.fill();
        }
    }

    function drawPath() {
        ctx.beginPath();
        const first = P(pathPoints[0]);
        ctx.moveTo(first.x, first.y);
        for (let i = 1; i < pathPoints.length; i++) {
            const p = P(pathPoints[i]);
            ctx.lineTo(p.x, p.y);
        }
        ctx.strokeStyle = hexToRgba(AMBER, 0.22);
        ctx.lineWidth = 2;
        ctx.setLineDash([1, 7]);
        ctx.lineCap = "round";
        ctx.stroke();
        ctx.setLineDash([]);
    }

    function drawWaypoints() {
        T_STOPS.forEach((t, i) => {
            const pos = P(pointAt(t));
            const active = pulseT >= t;

            ctx.beginPath();
            ctx.arc(pos.x, pos.y, active ? 6 : 4.5, 0, Math.PI * 2);
            ctx.fillStyle = active ? MINT : hexToRgba(AMBER, 0.7);
            ctx.shadowColor = active ? MINT : AMBER;
            ctx.shadowBlur = active ? 14 : 6;
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.beginPath();
            ctx.arc(pos.x, pos.y, active ? 12 : 9, 0, Math.PI * 2);
            ctx.strokeStyle = hexToRgba(active ? MINT : AMBER, 0.35);
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.font = "500 12px 'Space Grotesk', sans-serif";
            ctx.fillStyle = active ? "#EDEFF7" : MUTED;
            ctx.textAlign = i > 2 ? "right" : "left";
            const labelX = pos.x + (i > 2 ? -16 : 16);
            ctx.fillText(LABELS[i], labelX, pos.y + 4);
        });
    }

    function drawPulse() {
        const pos = P(pointAt(pulseT));
        ctx.save();
        ctx.shadowColor = "#ffffff";
        ctx.shadowBlur = 16;
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 3.2, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        pulseT += 0.0022;
        if (pulseT > 1.08) pulseT = -0.05;
    }

    function draw(time) {
        try {
            ctx.clearRect(0, 0, width, height);
            drawStars(time || 0);
            drawPath();
            drawPulse();
            drawWaypoints();
        } catch (err) {
            // Never let a stray error kill the loop permanently - the whole
            // point is that this animation runs forever without a refresh.
            console.error("trajectory.js draw error (recovering):", err);
        }
        requestAnimationFrame(draw);
    }

    window.addEventListener("resize", resize);
    resize();
    requestAnimationFrame(draw);
})();