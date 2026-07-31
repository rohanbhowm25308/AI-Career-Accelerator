/*=========================================================
    Ascend — AI Chip
    A central AI chip with circuit traces radiating outward to
    small nodes, with glowing pulses of light traveling along
    the traces on a loop. Colors are pulled from the site's CSS
    variables (--accent / --mint) so it automatically matches
    the rest of the theme.
=========================================================*/

(function () {
    "use strict";

    const canvas = document.getElementById("aiChipCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    function themeColor(varName, fallback) {
        const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
        return val || fallback;
    }

    const AMBER = themeColor("--accent", "#FFB020");
    const MINT = themeColor("--mint", "#47E0A6");

    const PINS_PER_SIDE = 6;
    const MAX_PULSES = 8;
    const PULSE_SPAWN_CHANCE = 0.05;

    let width, height, dpr;
    let chip = {};
    let traces = [];
    let pulses = [];
    let t = 0;

    function rand(min, max) { return Math.random() * (max - min) + min; }

    function hexToRgba(hex, a) {
        const c = hex.replace("#", "");
        const r = parseInt(c.substring(0, 2), 16);
        const g = parseInt(c.substring(2, 4), 16);
        const b = parseInt(c.substring(4, 6), 16);
        return `rgba(${r},${g},${b},${a})`;
    }

    function buildChip() {
        const halfW = width * 0.19;
        const halfH = width * 0.19;
        chip = {
            cx: width / 2, cy: height / 2,
            halfW, halfH,
            pinLen: width * 0.03,
        };
    }

    function buildTraces() {
        traces = [];
        const sides = [
            { axis: "x", fixed: chip.cy - chip.halfH, dir: { x: 0, y: -1 } },
            { axis: "x", fixed: chip.cy + chip.halfH, dir: { x: 0, y: 1 } },
            { axis: "y", fixed: chip.cx - chip.halfW, dir: { x: -1, y: 0 } },
            { axis: "y", fixed: chip.cx + chip.halfW, dir: { x: 1, y: 0 } },
        ];

        for (const side of sides) {
            for (let i = 0; i < PINS_PER_SIDE; i++) {
                const frac = (i + 0.5) / PINS_PER_SIDE;
                let px, py;
                if (side.axis === "x") {
                    px = chip.cx - chip.halfW + frac * chip.halfW * 2;
                    py = side.fixed;
                } else {
                    px = side.fixed;
                    py = chip.cy - chip.halfH + frac * chip.halfH * 2;
                }

                const points = [{ x: px, y: py }];
                let cx = px + side.dir.x * chip.pinLen;
                let cy = py + side.dir.y * chip.pinLen;
                points.push({ x: cx, y: cy });

                const seg1 = rand(width * 0.05, width * 0.11);
                cx += side.dir.x * seg1;
                cy += side.dir.y * seg1;
                points.push({ x: cx, y: cy });

                if (Math.random() < 0.6) {
                    const turnSign = Math.random() < 0.5 ? 1 : -1;
                    const perp = side.axis === "x"
                        ? { x: turnSign, y: 0 }
                        : { x: 0, y: turnSign };
                    const seg2 = rand(width * 0.04, width * 0.11);
                    cx += perp.x * seg2;
                    cy += perp.y * seg2;
                    points.push({ x: cx, y: cy });

                    if (Math.random() < 0.5) {
                        const seg3 = rand(width * 0.03, width * 0.06);
                        cx += side.dir.x * seg3;
                        cy += side.dir.y * seg3;
                        points.push({ x: cx, y: cy });
                    }
                } else {
                    const seg1b = rand(width * 0.03, width * 0.07);
                    cx += side.dir.x * seg1b;
                    cy += side.dir.y * seg1b;
                    points.push({ x: cx, y: cy });
                }

                traces.push({
                    points,
                    nodeR: Math.random() < 0.3 ? rand(4, 6) : rand(1.8, 2.8),
                    phase: rand(0, Math.PI * 2),
                    color: Math.random() < 0.75 ? AMBER : MINT,
                });
            }
        }
    }

    function pathLength(points) {
        let len = 0;
        for (let i = 1; i < points.length; i++) {
            len += Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
        }
        return len;
    }

    function pointAtFraction(points, frac) {
        const total = pathLength(points);
        let target = total * frac;
        for (let i = 1; i < points.length; i++) {
            const segLen = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
            if (target <= segLen) {
                const segT = segLen === 0 ? 0 : target / segLen;
                return {
                    x: points[i - 1].x + (points[i].x - points[i - 1].x) * segT,
                    y: points[i - 1].y + (points[i].y - points[i - 1].y) * segT,
                };
            }
            target -= segLen;
        }
        return points[points.length - 1];
    }

    function spawnPulse() {
        if (pulses.length >= MAX_PULSES || traces.length === 0) return;
        const tr = traces[Math.floor(Math.random() * traces.length)];
        pulses.push({ trace: tr, t: 0, speed: 0.008 + Math.random() * 0.012 });
    }

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        const parent = canvas.parentElement;
        const parentWidth = parent ? parent.getBoundingClientRect().width : 480;
        const size = Math.max(280, Math.min(680, parentWidth || 480));
        width = size;
        height = size;

        canvas.style.width = width + "px";
        canvas.style.height = height + "px";
        canvas.style.display = "block";
        canvas.style.margin = "0 auto";

        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        buildChip();
        buildTraces();
        pulses = [];
    }

    function drawTraces(time) {
        for (const tr of traces) {
            const glow = 0.5 + 0.35 * Math.sin(time * 0.0015 + tr.phase);

            ctx.beginPath();
            ctx.moveTo(tr.points[0].x, tr.points[0].y);
            for (let i = 1; i < tr.points.length; i++) ctx.lineTo(tr.points[i].x, tr.points[i].y);
            ctx.strokeStyle = hexToRgba(tr.color, 0.26 + glow * 0.2);
            ctx.lineWidth = 1.4;
            ctx.lineJoin = "round";
            ctx.stroke();

            const last = tr.points[tr.points.length - 1];
            ctx.beginPath();
            ctx.arc(last.x, last.y, tr.nodeR, 0, Math.PI * 2);
            ctx.strokeStyle = hexToRgba(tr.color, 0.55 + glow * 0.3);
            ctx.lineWidth = 1.5;
            ctx.stroke();

            for (let i = 1; i < tr.points.length - 1; i++) {
                ctx.beginPath();
                ctx.arc(tr.points[i].x, tr.points[i].y, 1.6, 0, Math.PI * 2);
                ctx.fillStyle = hexToRgba(tr.color, 0.4 + glow * 0.25);
                ctx.fill();
            }
        }
    }

    function drawPulses() {
        if (Math.random() < PULSE_SPAWN_CHANCE) spawnPulse();
        pulses = pulses.filter((p) => p.t <= 1);
        for (const p of pulses) {
            const pos = pointAtFraction(p.trace.points, p.t);
            ctx.save();
            ctx.shadowColor = "#ffffff";
            ctx.shadowBlur = 10;
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
            p.t += p.speed;
        }
    }

    function drawChip() {
        const pulse = 0.75 + 0.25 * Math.sin(t * 0.04);
        const r = chip.halfW * 0.18;
        ctx.save();

        ctx.beginPath();
        ctx.moveTo(chip.cx - chip.halfW + r, chip.cy - chip.halfH);
        ctx.arcTo(chip.cx + chip.halfW, chip.cy - chip.halfH, chip.cx + chip.halfW, chip.cy + chip.halfH, r);
        ctx.arcTo(chip.cx + chip.halfW, chip.cy + chip.halfH, chip.cx - chip.halfW, chip.cy + chip.halfH, r);
        ctx.arcTo(chip.cx - chip.halfW, chip.cy + chip.halfH, chip.cx - chip.halfW, chip.cy - chip.halfH, r);
        ctx.arcTo(chip.cx - chip.halfW, chip.cy - chip.halfH, chip.cx + chip.halfW, chip.cy - chip.halfH, r);
        ctx.closePath();

        ctx.fillStyle = "#0B0E18";
        ctx.fill();

        ctx.shadowColor = hexToRgba(AMBER, 0.8 * pulse);
        ctx.shadowBlur = 20;
        ctx.strokeStyle = hexToRgba(AMBER, 0.95);
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.shadowBlur = 0;
        ctx.fillStyle = hexToRgba(AMBER, 0.95);
        ctx.font = `800 ${chip.halfW * 0.62}px 'Space Grotesk', sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("AI", chip.cx, chip.cy + 2);

        ctx.restore();
    }

    function draw(time) {
        try {
            ctx.clearRect(0, 0, width, height);
            drawTraces(time || 0);
            drawPulses();
            drawChip();
            t += 1;
        } catch (err) {
            console.error("ai_chip.js draw error (recovering):", err);
        }
        requestAnimationFrame(draw);
    }

    window.addEventListener("resize", resize);
    resize();
    requestAnimationFrame(draw);
})();