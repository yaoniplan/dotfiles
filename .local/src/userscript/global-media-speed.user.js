// ==UserScript==
// @name         Global Media Speed
// @namespace    https://github.com/yaoniplan/dotfiles/tree/master/.local/src/userscript
// @version      1.0.2
// @description  Set all video/audio playback speed to 2x by default. Developers can edit the SPEED constant below
// @author       yaoniplan
// @license      MIT
// @match        *://*/*
// @icon         data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iNTEyLjAwMDAwMHB0IiBoZWlnaHQ9IjUxMi4wMDAwMDBwdCIgdmlld0JveD0iMCAwIDUxMi4wMDAwMDAgNTEyLjAwMDAwMCIKIHByZXNlcnZlQXNwZWN0UmF0aW89InhNaWRZTWlkIG1lZXQiPgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgwLjAwMDAwMCw1MTIuMDAwMDAwKSBzY2FsZSgwLjEwMDAwMCwtMC4xMDAwMDApIgpmaWxsPSIjMDAwMDAwIiBzdHJva2U9Im5vbmUiPgo8cGF0aCBkPSJNMzI0IDQxODAgYy0xNyAtNiAtMzkgLTE5IC01MCAtMzEgLTE5IC0yMSAtMTkgLTU5IC0yMiAtMTU3MyAtMQotMTA4NiAxIC0xNTU5IDggLTE1NzcgMTQgLTM0IDgzIC03MiAxMTggLTY3IDE1IDMgNDcxIDMwNCAxMDE0IDY3MCBsOTg4IDY2NgoyIC02MzUgMyAtNjM1IDMyIC0yOCBjMTggLTE2IDQ4IC0zMiA2OCAtMzYgMzUgLTYgNTYgNyA1MjMgMzE5IDE0MTEgOTQyIDE4MzgKMTIzMSAxODQ5IDEyNTAgMTggMzIgMTYgNzggLTYgMTEyIC0xMiAyMSAtMzY5IDI2NSAtMTE2NyA4MDAgLTEwODAgNzI0IC0xMTUyCjc3MCAtMTE5MSA3NjkgLTU1IC0xIC05MCAtMjUgLTEwMiAtNzEgLTcgLTI1IC0xMSAtMjUxIC0xMSAtNjM1IDAgLTMyOSAtMgotNTk4IC01IC01OTggLTMgMCAtNDQ3IDI5MyAtOTg3IDY1MSAtNTQwIDM1NyAtOTkzIDY1MiAtMTAwNyA2NTQgLTE0IDIgLTQwIDAKLTU3IC01eiIvPgo8L2c+Cjwvc3ZnPgo=
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    /**
     * CONFIGURATION
     * Change this value to your preferred default speed.
     */
    const TARGET_SPEED = 2.0;

    function setSpeed() {
        const mediaElements = document.querySelectorAll('video, audio');
        mediaElements.forEach(el => {
            // Only update if the rate is different to avoid unnecessary overhead
            if (el.playbackRate !== TARGET_SPEED) {
                el.playbackRate = TARGET_SPEED;
            }
        });
    }

    // Initial run to catch elements already on the page
    setSpeed();

    // Observe DOM changes to catch dynamically loaded media (AJAX/Infinite Scroll)
    const observer = new MutationObserver(() => setSpeed());
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
})();
