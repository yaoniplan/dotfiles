// ==UserScript==
// @name         Global Media Long-Press Speed
// @namespace    https://github.com/yaoniplan/dotfiles/tree/master/.local/src/userscript
// @version      1.0.1
// @description  Hold any <video>/<audio> to boost playback to 2x, then slide horizontally to fine-tune the rate (0.5x-8x). Release to restore. A quick tap still toggles play/pause. Auto-hiding speed HUD. Works on every media site.
// @author       yaoniplan
// @license      MIT
// @match        *://*/*
// @icon         data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iNTEyLjAwMDAwMHB0IiBoZWlnaHQ9IjUxMi4wMDAwMDBwdCIgdmlld0JveD0iMCAwIDUxMi4wMDAwMDAgNTEyLjAwMDAwMCIKIHByZXNlcnZlQXNwZWN0UmF0aW89InhNaWRZTWlkIG1lZXQiPgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgwLjAwMDAwMCw1MTIuMDAwMDAwKSBzY2FsZSgwLjEwMDAwMCwtMC4xMDAwMDApIgpmaWxsPSIjMDAwMDAwIiBzdHJva2U9Im5vbmUiPgo8cGF0aCBkPSJNMzI0IDQxODAgYy0xNyAtNiAtMzkgLTE5IC01MCAtMzEgLTE5IC0yMSAtMTkgLTU5IC0yMiAtMTU3MyAtMQotMTA4NiAxIC0xNTU5IDggLTE1NzcgMTQgLTM0IDgzIC03MiAxMTggLTY3IDE1IDMgNDcxIDMwNCAxMDE0IDY3MCBsOTg4IDY2NgoyIC02MzUgMyAtNjM1IDMyIC0yOCBjMTggLTE2IDQ4IC0zMiA2OCAtMzYgMzUgLTYgNTYgNyA1MjMgMzE5IDE0MTEgOTQyIDE4MzgKMTIzMSAxODQ5IDEyNTAgMTggMzIgMTYgNzggLTYgMTEyIC0xMiAyMSAtMzY5IDI2NSAtMTE2NyA4MDAgLTEwODAgNzI0IC0xMTUyCjc3MCAtMTE5MSA3NjkgLTU1IC0xIC05MCAtMjUgLTEwMiAtNzEgLTcgLTI1IC0xMSAtMjUxIC0xMSAtNjM1IDAgLTMyOSAtMgotNTk4IC01IC01OTggLTMgMCAtNDQ3IDI5MyAtOTg3IDY1MSAtNTQwIDM1NyAtOTkzIDY1MiAtMTAwNyA2NTQgLTE0IDIgLTQwIDAKLTU3IC01eiIvPgo8L2c+Cjwvc3ZnPgo=
// @all-frames   true
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    /**
     * CONFIGURATION - edit to taste
     */
    const LONG_PRESS_MS = 400;   // ms to hold before speed control kicks in
    const BASE_SPEED = 2.0;      // starting rate once boosted (Telegram uses 2x)
    const RATE_PER_100PX = 1.0;  // how many x each 100px of horizontal slide adds
    const MIN_SPEED = 0.5;
    const MAX_SPEED = 8.0;
    const MOVE_CANCEL_PX = 12;   // movement before the hold completes = scroll/drag -> cancel
    const HUD_DWELL_MS = 800;    // how long the HUD stays visible after the last change

    // ---- Auto-hiding HUD ---------------------------------------------
    const HUD = document.createElement('div');
    Object.assign(HUD.style, {
        position: 'fixed', top: '10%', left: '50%', transform: 'translateX(-50%)',
        padding: '8px 16px', background: 'rgba(0,0,0,0.7)', color: '#fff',
        borderRadius: '20px', zIndex: '999999', display: 'none', pointerEvents: 'none',
        fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
        fontWeight: '700', fontSize: '16px',
        userSelect: 'none', WebkitUserSelect: 'none', WebkitTouchCallout: 'none',
        transition: 'opacity 0.3s ease'
    });
    (document.body || document.documentElement).appendChild(HUD);

    let hudTimer = null;
    function showHUD(rate) {
        HUD.textContent = rate.toFixed(1) + 'x';
        HUD.style.display = 'block';
        void HUD.offsetHeight; // reflow so the transition restarts
        HUD.style.opacity = '1';
        clearTimeout(hudTimer);
        hudTimer = setTimeout(() => {
            HUD.style.opacity = '0';
            setTimeout(() => { HUD.style.display = 'none'; }, 300);
        }, HUD_DWELL_MS);
    }

    // ---- Long-press / swipe state machine ---------------------------
    let press = null; // { media, pointerId, startX, startY, originalRate, boosted, moved }

    function endPress() {
        if (!press) return;
        clearTimeout(press.timer);
        if (press.boosted) {
            try { press.media.playbackRate = press.originalRate; } catch (e) {}
            showHUD(press.originalRate);
        } else if (!press.moved) {
            // A clean, quick tap with no movement: toggle play/pause.
            const m = press.media;
            if (m.paused) { try { m.play(); } catch (e) {} }
            else m.pause();
        }
        press = null;
    }

    function onPointerDown(e) {
        if (press) return;
        if (typeof e.button === 'number' && e.button !== 0) return;
        const target = e.target;
        const media = target && target.closest
            ? target.closest('video, audio')
            : null;
        if (!media || !(media instanceof HTMLMediaElement)) return;

        // Stop iOS long-press system menu / text selection / image drag.
        media.style.userSelect = 'none';
        media.style.webkitUserSelect = 'none';
        media.style.webkitTouchCallout = 'none';

        const startX = e.clientX;
        const startY = e.clientY;
        press = {
            media, pointerId: e.pointerId,
            startX, startY, originalRate: null, boosted: false, moved: false,
            timer: setTimeout(() => {
                const p = press;
                if (!p || p.boosted) return;
                p.boosted = true;
                p.originalRate = p.media.playbackRate;
                p.media.playbackRate = BASE_SPEED;
                showHUD(BASE_SPEED);
                // Keep receiving pointermove/up even if the finger drifts off.
                try { p.media.setPointerCapture(p.pointerId); } catch (err) {}
            }, LONG_PRESS_MS),
        };
    }

    function onPointerMove(e) {
        if (!press || e.pointerId !== press.pointerId) return;
        const dx = e.clientX - press.startX;
        const dy = e.clientY - press.startY;

        if (!press.boosted) {
            // Movement before the hold completes is a scroll/drag -> cancel.
            if (Math.max(Math.abs(dx), Math.abs(dy)) > MOVE_CANCEL_PX) {
                press.moved = true;
                endPress();
            }
            return;
        }

        // Boosted: linear horizontal slide adjusts the speed.
        press.moved = true;
        const rate = Math.round(
            (BASE_SPEED + (dx / 100) * RATE_PER_100PX) * 10
        ) / 10;
        const finalRate = Math.max(MIN_SPEED, Math.min(rate, MAX_SPEED));
        if (press.media.playbackRate !== finalRate) {
            press.media.playbackRate = finalRate;
            showHUD(finalRate);
        }
    }

    function onPointerUp(e) {
        if (press && e.pointerId === press.pointerId) endPress();
    }

    function onPointerCancel(e) {
        if (press && e.pointerId === press.pointerId) endPress();
    }

    function onBlur() { endPress(); } // tab switch / context loss safety net

    // ---- Bind (non-passive so we may preventDefault) ----------------
    const doc = document;
    doc.addEventListener('pointerdown', onPointerDown, { passive: false, capture: true });
    doc.addEventListener('pointermove', onPointerMove, { passive: true });
    doc.addEventListener('pointerup', onPointerUp, { passive: true });
    doc.addEventListener('pointercancel', onPointerCancel, { passive: true });
    window.addEventListener('blur', onBlur);
    // Guard against a context menu appearing after a real long-press.
    doc.addEventListener('contextmenu', (e) => {
        if (press && press.boosted) e.preventDefault();
    }, { capture: true });
})();
