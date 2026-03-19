/**
 * DigiBhoj Hero — Liquid Glass Reveal Effect
 *
 * Creates an interactive canvas overlay that simulates a liquid glass surface.
 * Moving the cursor reveals the sharp food image beneath the frosted glass.
 *
 * Layers (bottom → top):
 *   1. CSS-blurred background <img>
 *   2. This <canvas> – draws the SHARP image only inside the cursor "bubble"
 *      with refraction distortion, ripple rings, and specular highlights
 *   3. Foreground UI (CSS z-index above canvas)
 */

(function () {
    'use strict';

    // ── DOM references ───────────────────────────────────────
    const canvas  = document.getElementById('liquid-canvas');
    const bgImg   = document.getElementById('hero-bg-img');
    const hero    = document.querySelector('.hero-liquid');
    const particleContainer = document.getElementById('hero-particles');

    if (!canvas || !bgImg || !hero) return;

    const ctx = canvas.getContext('2d');

    // ── State ────────────────────────────────────────────────
    const mouse = { x: -9999, y: -9999 };   // Raw mouse position
    const lerp  = { x: -9999, y: -9999 };   // Smoothed (lagging) position
    const LERP_FACTOR  = 0.02;              // Lag factor (lower = extreme viscosity)
    const BUBBLE_RADIUS = 130;              // Base radius of reveal bubble
    let isActive = false;                   // Whether cursor is over hero
    let animationId;
    let time = 0;                           // Used for animating the wavy shape

    // Ripple trail data
    const ripples = [];
    const MAX_RIPPLES = 12;
    let lastRippleTime = 0;

    // ── Sizing ───────────────────────────────────────────────
    function resize() {
        const dpr = window.devicePixelRatio || 1;
        const rect = hero.getBoundingClientRect();
        canvas.width  = rect.width  * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width  = rect.width  + 'px';
        canvas.style.height = rect.height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    window.addEventListener('resize', resize);
    resize();

    // ── Mouse / Touch tracking ───────────────────────────────
    hero.addEventListener('mousemove', (e) => {
        const rect = hero.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        isActive = true;

        // Spawn ripple every ~120ms
        const now = Date.now();
        if (now - lastRippleTime > 120) {
            ripples.push({ x: mouse.x, y: mouse.y, r: 0, maxR: BUBBLE_RADIUS * 1.8, alpha: 0.4 });
            if (ripples.length > MAX_RIPPLES) ripples.shift();
            lastRippleTime = now;
        }
    });

    hero.addEventListener('mouseleave', () => {
        isActive = false;
    });

    // Touch support
    hero.addEventListener('touchmove', (e) => {
        const touch = e.touches[0];
        const rect = hero.getBoundingClientRect();
        mouse.x = touch.clientX - rect.left;
        mouse.y = touch.clientY - rect.top;
        isActive = true;

        const now = Date.now();
        if (now - lastRippleTime > 140) {
            ripples.push({ x: mouse.x, y: mouse.y, r: 0, maxR: BUBBLE_RADIUS * 1.6, alpha: 0.35 });
            if (ripples.length > MAX_RIPPLES) ripples.shift();
            lastRippleTime = now;
        }
    }, { passive: true });

    hero.addEventListener('touchend', () => { isActive = false; });

    // ── Image loading ────────────────────────────────────────
    // We need a clean (un-CSS-filtered) version of the image for canvas drawing
    const sharpImg = new Image();
    sharpImg.crossOrigin = 'anonymous';
    sharpImg.src = bgImg.src;

    let imgReady = false;
    sharpImg.onload = () => {
        imgReady = true;
        startLoop();
    };

    // Fallback if image was already cached
    if (sharpImg.complete && sharpImg.naturalWidth > 0) {
        imgReady = true;
    }

    // ── Helper: Draw Wavy Shape ──────────────────────────────
    function drawWavyPath(context, cx, cy, baseRadius, timeOffset) {
        context.beginPath();
        const segments = 80; // More segments for smoother organic curve
        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            
            // Create a highly viscous, extreme blob shape using sine waves.
            // Increased amplitudes (from 0.08 defaults up to 0.15)
            const noise = 
                Math.sin(angle * 2.5 + timeOffset * 1.8) * 0.15 +
                Math.cos(angle * 4.2 - timeOffset * 1.2) * 0.08 +
                Math.sin(angle * 3.1 - timeOffset * 2.5) * 0.05 +
                Math.cos(angle * 1.5 + timeOffset * 3.0) * 0.06;
                
            const r = baseRadius * (1 + noise);
            
            const x = cx + Math.cos(angle) * r;
            const y = cy + Math.sin(angle) * r;
            
            if (i === 0) {
                context.moveTo(x, y);
            } else {
                context.lineTo(x, y);
            }
        }
        context.closePath();
    }

    // ── Render loop ──────────────────────────────────────────
    function startLoop() {
        if (animationId) return;
        loop();
    }

    function loop() {
        animationId = requestAnimationFrame(loop);
        render();
    }

    function render() {
        time += 0.012; // Adjusted animation speed for wavy morphing
        
        const w = canvas.style.width  ? parseFloat(canvas.style.width)  : hero.clientWidth;
        const h = canvas.style.height ? parseFloat(canvas.style.height) : hero.clientHeight;

        ctx.clearRect(0, 0, w, h);

        if (!imgReady) return;

        // Smooth interpolation (liquid inertia/viscosity)
        lerp.x += (mouse.x - lerp.x) * LERP_FACTOR;
        lerp.y += (mouse.y - lerp.y) * LERP_FACTOR;

        // ── Compute image cover-fit coordinates ──────────
        const imgW = sharpImg.naturalWidth;
        const imgH = sharpImg.naturalHeight;
        const imgAspect = imgW / imgH;
        const canAspect = w / h;

        let drawW, drawH, drawX, drawY;
        if (canAspect > imgAspect) {
            drawW = w;
            drawH = w / imgAspect;
        } else {
            drawH = h;
            drawW = h * imgAspect;
        }
        drawX = (w - drawW) / 2;
        drawY = (h - drawH) / 2;

        // Scale slightly to match the CSS scale(1.1) on the blurred bg
        const scaleCompensation = 1.1;
        const cDrawW = drawW * scaleCompensation;
        const cDrawH = drawH * scaleCompensation;
        const cDrawX = (w - cDrawW) / 2;
        const cDrawY = (h - cDrawH) / 2;

        // ── Draw ripple rings (now slightly wavy) ───────
        for (let i = ripples.length - 1; i >= 0; i--) {
            const rp = ripples[i];
            rp.r += 2.0; // Slower expansion for more viscosity
            rp.alpha -= 0.006;

            if (rp.alpha <= 0 || rp.r >= rp.maxR) {
                ripples.splice(i, 1);
                continue;
            }

            ctx.save();
            drawWavyPath(ctx, rp.x, rp.y, rp.r, time * 0.5 + rp.r * 0.01);
            ctx.strokeStyle = `rgba(255, 255, 255, ${rp.alpha * 0.3})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
            ctx.restore();
        }

        if (!isActive && Math.abs(lerp.x - mouse.x) < 1 && Math.abs(lerp.y - mouse.y) < 1) {
            return; // Nothing to draw when cursor has fully left
        }

        // ── Main reveal blob ───────────────────────────
        const bx = lerp.x;
        const by = lerp.y;

        // Velocity-based radius modulation (less drastic due to higher viscosity)
        const dx = mouse.x - lerp.x;
        const dy = mouse.y - lerp.y;
        const speed = Math.sqrt(dx * dx + dy * dy);
        const dynamicRadius = BUBBLE_RADIUS + Math.min(speed * 0.25, 30);

        // ── Draw sharp image clipped to wavy blob ────────
        ctx.save();

        drawWavyPath(ctx, bx, by, dynamicRadius, time);
        
        ctx.globalCompositeOperation = 'source-over';
        // Fill the path with a heavy shadow to create a extremely soft blurry edge mask
        ctx.shadowColor = 'rgba(0, 0, 0, 1)';
        ctx.shadowBlur = 60; // Very high blur for soft edges
        ctx.fillStyle = 'black';
        ctx.fill();
        ctx.shadowBlur = 0;
        
        // Switch to source-in: the image will only be drawn where the soft black blob is
        ctx.globalCompositeOperation = 'source-in';

        // Apply extreme refraction distortion: offset the image draw position heavily
        // This makes the background food image look like it's under thick, moving glass/water
        const refractionStrength = 18; // Much higher refraction for thick liquid
        const rfx = (bx - w / 2) / w * refractionStrength + Math.sin(time * 1.5) * 8;
        const rfy = (by - h / 2) / h * refractionStrength + Math.cos(time * 1.2) * 8;

        ctx.drawImage(sharpImg, cDrawX + rfx, cDrawY + rfy, cDrawW, cDrawH);

        // Restore back to source-over for highlights
        ctx.restore();
        ctx.save(); // Save again for specular drawing

        // ── Specular highlight ───────────────────────────
        const specGrad = ctx.createRadialGradient(
            bx - dynamicRadius * 0.25,
            by - dynamicRadius * 0.3,
            0,
            bx,
            by,
            dynamicRadius * 1.2
        );
        specGrad.addColorStop(0, 'rgba(255, 255, 255, 0.25)');
        specGrad.addColorStop(0.3, 'rgba(255, 255, 255, 0.08)');
        specGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
        
        ctx.globalCompositeOperation = 'screen';
        ctx.fillStyle = specGrad;
        drawWavyPath(ctx, bx, by, dynamicRadius, time); // Fill highlight inside the blob
        ctx.fill();

        ctx.restore();

        // ── Blob border ring ───────────────────────────
        ctx.save();
        drawWavyPath(ctx, bx, by, dynamicRadius, time);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 2.5;
        ctx.stroke();
        ctx.restore();

        // ── Inner glow ring ──────────────────────────────
        ctx.save();
        drawWavyPath(ctx, bx, by, dynamicRadius * 0.9, time);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.restore();
    }

    // ── Floating ambient particles ───────────────────────────
    function createParticles() {
        if (!particleContainer) return;

        const count = 20;
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'hero-particle';
            const size = Math.random() * 6 + 2;
            particle.style.width  = size + 'px';
            particle.style.height = size + 'px';
            particle.style.left   = Math.random() * 100 + '%';
            particle.style.animationDuration = (Math.random() * 12 + 8) + 's';
            particle.style.animationDelay    = (Math.random() * 10) + 's';
            particle.style.opacity = Math.random() * 0.3 + 0.05;
            particleContainer.appendChild(particle);
        }
    }

    createParticles();

    // Start the loop once the image is ready (or if already loaded)
    if (imgReady) startLoop();

})();
