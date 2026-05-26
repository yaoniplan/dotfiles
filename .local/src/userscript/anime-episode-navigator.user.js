// ==UserScript==
// @name         Anime Episode Navigator
// @namespace    https://github.com/yaoniplan/dotfiles/.local/src/userscript
// @version      1.0.0
// @description  Press Enter to go to next episode, Shift+Enter to go to previous episode.
// @match        https://www.yhdm530.com/*
// @match        https://yhdm6a.com/*
// @match        *://*.agedm1.com/*
// @match        https://www.olevod.com/*
// @match        https://yhdm.one/*
// @match        https://www.agedm.io/*
// @match        https://www.skr2.cc/*
// @icon         data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iNTEyLjAwMDAwMHB0IiBoZWlnaHQ9IjUxMi4wMDAwMDBwdCIgdmlld0JveD0iMCAwIDUxMi4wMDAwMDAgNTEyLjAwMDAwMCIKIHByZXNlcnZlQXNwZWN0UmF0aW89InhNaWRZTWlkIG1lZXQiPgoKPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC4wMDAwMDAsNTEyLjAwMDAwMCkgc2NhbGUoMC4xMDAwMDAsLTAuMTAwMDAwKSIKZmlsbD0iIzAwMDAwMCIgc3Ryb2tlPSJub25lIj4KPHBhdGggZD0iTTIzMzAgNTExMCBjLTQ5NCAtNDggLTk1MCAtMjMwIC0xMzUwIC01MzggLTE5NSAtMTUwIC00NDggLTQzMiAtNTk0Ci02NjIgLTYzIC05OSAtMTg2IC0zNTEgLTIzMCAtNDcxIC00OSAtMTM0IC0xMDIgLTM0MCAtMTI4IC00OTkgLTMxIC0xOTUgLTMxCi01NjUgMCAtNzYwIDQ1IC0yNzYgMTE2IC00OTggMjM3IC03NDUgMTMyIC0yNjkgMjY5IC00NjAgNDg5IC02ODEgMjIxIC0yMjAKNDEyIC0zNTcgNjgxIC00ODkgMjQ3IC0xMjEgNDY5IC0xOTIgNzQ1IC0yMzcgMTk1IC0zMSA1NjUgLTMxIDc2MCAwIDI3NiA0NQo0OTggMTE2IDc0NSAyMzcgMjY5IDEzMiA0NjAgMjY5IDY4MSA0ODkgMjIwIDIyMSAzNTcgNDEyIDQ4OSA2ODEgODggMTc5IDEzMgoyOTYgMTgwIDQ3NiA2MyAyNDAgNzggMzcxIDc4IDY0OSAwIDI3OCAtMTUgNDA5IC03OCA2NDkgLTQ4IDE4MCAtOTIgMjk3IC0xODAKNDc2IC0xMzIgMjY5IC0yNjkgNDYwIC00ODkgNjgxIC0yMjEgMjIwIC00MTIgMzU3IC02ODEgNDg5IC0yNDYgMTIxIC00NzQgMTkzCi03NDAgMjM1IC0xNDcgMjMgLTQ3NSAzNCAtNjE1IDIweiBtNTUwIC0zNTUgYzM3MyAtNTYgNzEzIC0xOTkgMTAxOSAtNDI4IDEyMwotOTIgMzM2IC0zMDUgNDI4IC00MjggMzAwIC00MDEgNDQ3IC04NDEgNDQ3IC0xMzM5IDAgLTQ5OCAtMTQ3IC05MzggLTQ0NwotMTMzOSAtOTIgLTEyMyAtMzA1IC0zMzYgLTQyOCAtNDI4IC00MDEgLTMwMCAtODQxIC00NDcgLTEzMzkgLTQ0NyAtNDk4IDAKLTkzOCAxNDcgLTEzMzkgNDQ3IC0xMjMgOTIgLTMzNiAzMDUgLTQyOCA0MjggLTMwMCA0MDEgLTQ0NyA4NDEgLTQ0NyAxMzM5IDAKMjc3IDM3IDQ5NiAxMjQgNzQwIDExMyAzMTcgMjgxIDU4MSA1MjUgODI1IDI1NiAyNTYgNTMyIDQyOCA4NjggNTM5IDE3MyA1OAozMTUgODcgNTQyIDExMCA3OCA4IDM3MiAtNCA0NzUgLTE5eiIvPgo8cGF0aCBkPSJNMjMzMCAzMjY2IGMtNjYzIC0yNjUgLTEyMTUgLTQ4OCAtMTIyNyAtNDk0IC01NiAtMzEgLTkwIC0xMzAgLTY3Ci0xOTcgMTMgLTM5IDQ2IC04MCA3OSAtOTggMTEgLTYgMjcwIC02MSA1NzUgLTEyMiBsNTU0IC0xMTEgMTExIC01NTQgYzYxCi0zMDUgMTE3IC01NjUgMTIzIC01NzYgNiAtMTIgMjUgLTMzIDQyIC00OCA3OSAtNjYgMjAyIC00NyAyNTIgNDAgOSAxNiAyMzMKNTcwIDQ5NyAxMjMyIDUyMyAxMzA4IDUwNyAxMjYwIDQ1OCAxMzMzIC0xMiAxOCAtMzggNDQgLTU2IDU2IC03NCA1MCAtMjYgNjYKLTEzNDEgLTQ2MXogbTkzNiAtMTMgYy0zNCAtOTQgLTU4MSAtMTQ1MiAtNTgzIC0xNDQ5IC0yIDEgLTMyIDE0NyAtNjggMzI0Ci0zNSAxNzcgLTY4IDMzMCAtNzQgMzM5IC0xNiAzMSAtNjUgNzAgLTEwMSA4MiAtMTkgNyAtMTcwIDM5IC0zMzQgNzEgLTE2NSAzMwotMzAxIDYxIC0zMDIgNjMgLTQgNCAxNDQ1IDU4NiAxNDYwIDU4NyA0IDAgNSAtOCAyIC0xN3oiLz4KPC9nPgo8L3N2Zz4K
// @author       yaoniplan
// @license      MIT
// @grant        none
// @run-at       document-start
// ==/UserScript==
 
(function () {
  'use strict';
 
  document.addEventListener('keydown', function(event) {
    if (event.key !== 'Enter') return;
  
    const currentURL = window.location.href;
    const direction = event.shiftKey ? -1 : 1;
  
    // ---------------------------------------------------------
    // Universal pattern:
    // Find the last number in the URL and increase/decrease it.
    //
    // Works for:
    //   /005.html
    //   /6467-1.html
    //   /9314-2-6.html
    //   /209418-2-13/
    //   /18
    //   /18/
    //   /play/xxx/yyy/008/
    // ---------------------------------------------------------
    const match = currentURL.match(/^(.*?)(\d+)((?:\.\w+)?\/?)$/);
  
    if (!match) return;
  
    const prefix = match[1];
    const num    = match[2];
    const suffix = match[3];
  
    const nextNum = String(parseInt(num, 10) + direction)
                      .padStart(num.length, "0");
  
    const nextURL = prefix + nextNum + suffix;
  
    window.location.href = nextURL;
  });
 
})();
