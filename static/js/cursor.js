/**
 * AstroControl - Global Interactive Cursor Effect
 * Features:
 * - Fluid Lerp Physics for Ambient Glow
 * - Responsive Precision Dot with Interactive Element Expansion
 * - Auto DOM element creation (zero-configuration on new pages)
 * - Auto Touch/Mobile detection
 */

(function () {
    // Only run on desktop devices with a precision pointer
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
        return;
    }

    function initCursor() {
        // Ensure DOM elements exist
        let glow = document.getElementById('cursorGlow');
        let dot = document.getElementById('cursorDot');

        if (!glow) {
            glow = document.createElement('div');
            glow.id = 'cursorGlow';
            glow.className = 'cursor-glow';
            document.body.appendChild(glow);
        }

        if (!dot) {
            dot = document.createElement('div');
            dot.id = 'cursorDot';
            dot.className = 'cursor-dot';
            document.body.appendChild(dot);
        }

        let mouseX = -1000;
        let mouseY = -1000;
        let glowX = -1000;
        let glowY = -1000;
        let dotX = -1000;
        let dotY = -1000;
        let isVisible = false;

        window.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;

            if (!isVisible) {
                isVisible = true;
                glow.style.opacity = '1';
                dot.style.opacity = '1';
                glowX = mouseX;
                glowY = mouseY;
                dotX = mouseX;
                dotY = mouseY;
            }
        }, { passive: true });

        document.addEventListener('mouseleave', () => {
            isVisible = false;
            glow.style.opacity = '0';
            dot.style.opacity = '0';
        });

        document.addEventListener('mouseenter', () => {
            if (mouseX > 0 && mouseY > 0) {
                isVisible = true;
                glow.style.opacity = '1';
                dot.style.opacity = '1';
            }
        });

        // Smooth physics render loop
        function renderCursor() {
            if (isVisible) {
                // Smooth damping on the ambient glow (lerp 0.10)
                glowX += (mouseX - glowX) * 0.10;
                glowY += (mouseY - glowY) * 0.10;
                glow.style.transform = `translate3d(${glowX}px, ${glowY}px, 0)`;

                // Crisp precision on the dot (lerp 0.35)
                dotX += (mouseX - dotX) * 0.35;
                dotY += (mouseY - dotY) * 0.35;
                dot.style.transform = `translate3d(${dotX}px, ${dotY}px, 0)`;
            }
            requestAnimationFrame(renderCursor);
        }
        requestAnimationFrame(renderCursor);

        // Hover selector list for interactive elements
        const interactiveSelectors = 'a, button, input, select, textarea, .btn, .theme-toggle-btn, .cockpit-tab-btn, .feature-card, .prod-showcase-card, .price-card, .faq-item, .demo-action-card, .card, .table tr, .sidebar-item, .stat-card, [role="button"]';

        document.addEventListener('mouseover', (e) => {
            if (e.target && e.target.closest && e.target.closest(interactiveSelectors)) {
                document.body.classList.add('cursor-active-hover');
            }
        });

        document.addEventListener('mouseout', (e) => {
            if (e.target && e.target.closest && e.target.closest(interactiveSelectors)) {
                document.body.classList.remove('cursor-active-hover');
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCursor);
    } else {
        initCursor();
    }
})();
