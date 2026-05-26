// ==UserScript==
// @name         Global Media Speed
// @namespace    https://github.com/yaoniplan/dotfiles/.local/src/userscript
// @version      1.0.0
// @description  Set all video/audio playback speed to 2x by default. Developers can edit the SPEED constant below
// @author       yaoniplan
// @license      MIT
// @match        *://*/*
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
