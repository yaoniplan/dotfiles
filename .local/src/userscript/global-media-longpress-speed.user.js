// ==UserScript==
// @name         Global Media Speed (Simple Auto-Hide)
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  拦截系统菜单，线性滑动调节，速度提示自动淡出不遮挡视频。
// @author       ni
// @match        *://*/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    let startX, timer, hudTimer, v, isMoved;
    const HUD = document.createElement('div');

    // 1. 增加 transition 平滑淡出效果
    Object.assign(HUD.style, {
        position: 'fixed', top: '10%', left: '50%', transform: 'translateX(-50%)',
        padding: '8px 16px', background: 'rgba(0,0,0,0.7)', color: '#fff',
        borderRadius: '20px', zIndex: '999999', display: 'none', pointerEvents: 'none',
        transition: 'opacity 0.3s ease'
    });
    document.body.appendChild(HUD);

    // 2. 独立的提示框控制逻辑
    const showHUD = (rate) => {
        HUD.textContent = `${rate.toFixed(1)}x`;
        HUD.style.display = 'block';
        // 强制重绘以确保过渡动画生效
        HUD.offsetHeight;
        HUD.style.opacity = '1';

        clearTimeout(hudTimer);
        // 800ms 内没有速度变化，自动淡出消失
        hudTimer = setTimeout(() => {
            HUD.style.opacity = '0';
            setTimeout(() => HUD.style.display = 'none', 300);
        }, 800);
    };

    const handle = (e) => {
        const target = e.target.closest('video');
        if (!target) return;

        if (e.type === 'touchstart') {
            v = target;
            startX = e.touches[0].clientX;
            isMoved = false;
            v.isLP = false;
            e.preventDefault();

            timer = setTimeout(() => {
                v.isLP = true;
                v.playbackRate = 2.0;
                showHUD(2.0); // 长按触发时显示
            }, 400);
        }
        else if (e.type === 'touchmove') {
            isMoved = true;
            if (v?.isLP) {
                const rate = Math.round((2.0 + (e.touches[0].clientX - startX) / 100) * 10) / 10;
                const finalRate = Math.max(0.5, Math.min(rate, 8));

                // 只有速度确实发生变化时才更新 HUD
                if (v.playbackRate !== finalRate) {
                    v.playbackRate = finalRate;
                    showHUD(finalRate);
                }
            }
        }
        else if (e.type === 'touchend' || e.type === 'touchcancel') {
            clearTimeout(timer);
            if (v?.isLP) {
                v.playbackRate = 1.0;
                showHUD(1.0); // 松开时提示恢复 1.0x，随后自动消失
            } else if (!isMoved) {
                v.paused ? v.play() : v.pause();
            }
            v = null;
        }
    };

    ['touchstart', 'touchmove', 'touchend', 'touchcancel'].forEach(ev => {
        document.addEventListener(ev, handle, { passive: false });
    });

    const init = () => document.querySelectorAll('video').forEach(el => {
        if (!el.hasInit) { el.playbackRate = 1.0; el.hasInit = true; }
    });
    init();
    new MutationObserver(init).observe(document.body, { childList: true, subtree: true });
})();
