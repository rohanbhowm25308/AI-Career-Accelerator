/*=========================================================
    Ascend — background.js
    Full-page ambient particle network: drifting nodes in a
    magenta -> violet -> cyan palette, connected by thin lines
    when close, plus a few slow-moving glowing "flow" curves
    for the wavy look in the reference art. Sits fixed behind
    all content at z-index:-1 (see style.css #networkCanvas).
=========================================================*/

(function () {
    "use strict";

    const canvas = document.getElementById("networkCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const PALETTE = ["#e879f9", "#a855f7", "#818cf8", "#38bdf8"];
    const LINK_DISTANCE = 130;
    const PARTICLE_DENSITY = 15000; // lower = more particles
    const MOUSE_RADIUS = 150;
    const FLOW_COUNT = 4;

    let width, height, dpr;
    let particles = [];
    let flows = [];
    let mouse = { x: null, y: null };

    function hexToRgba(hex, a) {
        const c = hex.replace("#", "");
        const r = parseInt(c.substring(0, 2), 16);
        const g = parseInt(c.substring(2, 4), 16);
        const b = parseInt(c.substring(4, 6), 16);
        return `rgba(${r},${g},${b},${a})`;
    }

    function lerpColor(hexA, hexB, t) {
        const a = hexA.replace("#", ""), b = hexB.replace("#", "");
        const ar = parseInt(a.substring(0, 2), 16), ag = parseInt(a.substring(2, 4), 16), ab = parseInt(a.substring(4, 6), 16);
        const br = parseInt(b.substring(0, 2), 16), bg = parseInt(b.substring(2, 4), 16), bb = parseInt(b.substring(4, 6), 16);
        return [Math.round(ar + (br - ar) * t), Math.round(ag + (bg - ag) * t), Math.round(ab + (bb - ab) * t)];
    }

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + "px";
        canvas.style.height = height + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        buildParticles();
        buildFlows();
    }

    function buildParticles() {
        const count = Math.min(150, Math.floor((width * height) / PARTICLE_DENSITY));
        particles = new Array(count).fill(null).map(() => ({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            r: Math.random() * 1.6 + 0.9,
            color: PALETTE[Math.floor(Math.random() * PALETTE.length)],
            twinklePhase: Math.random() * Math.PI * 2,
        }));
    }

    // A handful of large, slow, glowing sine-wave curves that drift across
    // the screen -- this is what gives the reference image its "flowing
    // ribbon" quality rather than just a flat dot-grid.
    function buildFlows() {
        flows = [];
        for (let i = 0; i < FLOW_COUNT; i++) {
            flows.push({
                baseY: height * (0.25 + 0.5 * (i / FLOW_COUNT)) + (Math.random() - 0.5) * height * 0.15,
                amplitude: height * (0.05 + Math.random() * 0.06),
                wavelength: width * (0.6 + Math.random() * 0.5),
                phase: Math.random() * Math.PI * 2,
                speed: 0.00012 + Math.random() * 0.00015,
                colorA: PALETTE[i % PALETTE.length],
                colorB: PALETTE[(i + 2) % PALETTE.length],
                lineWidth: 1 + Math.random() * 1.2,
                opacity: 0.10 + Math.random() * 0.08,
            });
        }
    }

    function drawFlows(time) {
        flows.forEach((f) => {
            ctx.beginPath();
            const steps = 60;
            for (let i = 0; i <= steps; i++) {
                const x = (i / steps) * width;
                const y = f.baseY + Math.sin(x / f.wavelength * Math.PI * 2 + f.phase + time * f.speed) * f.amplitude;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            const gradient = ctx.createLinearGradient(0, f.baseY, width, f.baseY);
            gradient.addColorStop(0, hexToRgba(f.colorA, f.opacity));
            gradient.addColorStop(0.5, hexToRgba(f.colorB, f.opacity * 1.4));
            gradient.addColorStop(1, hexToRgba(f.colorA, f.opacity));
            ctx.strokeStyle = gradient;
            ctx.lineWidth = f.lineWidth;
            ctx.shadowColor = f.colorB;
            ctx.shadowBlur = 12;
            ctx.stroke();
            ctx.shadowBlur = 0;
        });
    }

    function step(time) {
        try {
            ctx.clearRect(0, 0, width, height);

            drawFlows(time || 0);

            for (const p of particles) {
                p.x += p.vx;
                p.y += p.vy;

                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;

                if (mouse.x !== null) {
                    const dx = p.x - mouse.x;
                    const dy = p.y - mouse.y;
                    const dist = Math.hypot(dx, dy);
                    if (dist < MOUSE_RADIUS) {
                        const force = (MOUSE_RADIUS - dist) / MOUSE_RADIUS;
                        p.x += (dx / (dist || 1)) * force * 1.1;
                        p.y += (dy / (dist || 1)) * force * 1.1;
                    }
                }

                const twinkle = 0.7 + 0.3 * Math.sin((time || 0) * 0.0015 + p.twinklePhase);
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.shadowColor = p.color;
                ctx.shadowBlur = 7 * twinkle;
                ctx.globalAlpha = 0.85 * twinkle;
                ctx.fill();
            }
            ctx.globalAlpha = 1;
            ctx.shadowBlur = 0;

            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const a = particles[i];
                    const b = particles[j];
                    const dist = Math.hypot(a.x - b.x, a.y - b.y);
                    if (dist < LINK_DISTANCE) {
                        const t = dist / LINK_DISTANCE;
                        const [r, g, bch] = lerpColor(a.color, b.color, 0.5);
                        ctx.beginPath();
                        ctx.moveTo(a.x, a.y);
                        ctx.lineTo(b.x, b.y);
                        ctx.strokeStyle = `rgba(${r},${g},${bch},${(1 - t) * 0.32})`;
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                }
            }
        } catch (err) {
            console.error("background.js step error (recovering):", err);
        }

        requestAnimationFrame(step);
    }

    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });
    window.addEventListener("mouseleave", () => {
        mouse.x = null;
        mouse.y = null;
    });

    resize();
    requestAnimationFrame(step);
})();