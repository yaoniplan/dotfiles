// ==UserScript==
// @name         Reddit & Imgur Redirector
// @namespace    https://github.com/yaoniplan/dotfiles/tree/master/.local/src/userscript
// @version      1.0.2
// @description  Redirect Reddit to Redlib, Imgur to Rimgo.
// @match        *://www.reddit.com/*
// @match        *://imgur.com/*
// @icon         data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iMzYwLjAwMDAwMHB0IiBoZWlnaHQ9IjM2MC4wMDAwMDBwdCIgdmlld0JveD0iMCAwIDM2MC4wMDAwMDAgMzYwLjAwMDAwMCIKIHByZXNlcnZlQXNwZWN0UmF0aW89InhNaWRZTWlkIG1lZXQiPgoKPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC4wMDAwMDAsMzYwLjAwMDAwMCkgc2NhbGUoMC4xMDAwMDAsLTAuMTAwMDAwKSIKZmlsbD0iIzAwMDAwMCIgc3Ryb2tlPSJub25lIj4KPHBhdGggZD0iTTI2NzAgMzA1NSBjLTIxMiAtMTggLTQ3OSAtNDEgLTU5MyAtNTEgbC0yMDkgLTE3IDE5MyAtMTkzIDE5MyAtMTkzCi0zNjEgLTM2MyBjLTQzMCAtNDM0IC01MjcgLTUzNCAtNTcxIC01OTYgLTUzIC03NCAtMTA4IC0xNzIgLTEzOCAtMjQ1IC0xNQotMzcgLTMzIC02NiAtMzggLTY0IC0xOSA2IC04NSAxMzAgLTExMSAyMDcgLTM2IDExMSAtNDkgMjAxIC00MiAzMDQgOCAxMjEgMzAKMjAzIDgzIDMxMSAxMjggMjU5IDM1NiA0MTcgNjYyIDQ1OCBsOTIgMTIgLTE5OSAxOTkgLTIwMCAyMDAgLTQzIC0xMyBjLTYzCi0xOSAtMjI1IC0xMDEgLTMxMCAtMTU3IC05NCAtNjIgLTI3MSAtMjM5IC0zMzEgLTMzMCAtMTQ5IC0yMjYgLTIxOSAtNDU3Ci0yMTggLTcxOSAwIC0yNzYgNjUgLTQ5MSAyMTYgLTcyMCA1OSAtODkgMTk4IC0yMzYgMjkwIC0zMDYgMjIzIC0xNzAgNDg2Ci0yNTkgNzY3IC0yNTkgbDEwMSAwIC02MCAzOSBjLTc5IDUxIC0xNjQgMTM5IC0yMDIgMjEwIC04MyAxNTYgLTgwIDM0OCA2IDUxNQozMyA2MyA4NSAxMjAgNDg3IDUyNCAyNDggMjQ5IDQ1MyA0NTEgNDU3IDQ1MCA1IC0yIDkzIC04NyAxOTcgLTE5MCAxMDUgLTEwNAoxOTQgLTE4OCAxOTkgLTE4OCA1IDAgMjYgMjQ0IDQ3IDU0MyAyMCAyOTggNDAgNTcwIDQzIDYwNSA1IDQ5IDMgNjIgLTggNjEgLTgKLTEgLTE4NyAtMTYgLTM5OSAtMzR6Ii8+CjxwYXRoIGQ9Ik0yNTA2IDEzOTEgYy04OSAtMTQ0IC0yMDMgLTI0OSAtMzUwIC0zMjEgLTExOSAtNTkgLTIxNiAtODAgLTM2NAotODEgbC0xMjMgMCA2IC0zMiBjMjIgLTEwMSA1OSAtMTc4IDExMyAtMjMzIDE5MSAtMTk4IDQyOCAtMTk0IDcyOCAxMiAxMjYgODYKMjY2IDIyNSAzNTAgMzQ1IGwyOCA0MCAtMTY1IDE2NSBjLTkwIDkwIC0xNjkgMTY0IC0xNzUgMTY0IC02IDAgLTI4IC0yNyAtNDgKLTU5eiIvPgo8L2c+Cjwvc3ZnPgo=
// @author       yaoniplan
// @license      MIT
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @connect      raw.githubusercontent.com
// ==/UserScript==

(function () {
  // --- CONFIGURATION ---
  const CONFIG = {
    FETCH_REMOTE_INSTANCES: false, // Set to true to pull dynamic list from GitHub
    REDDIT_DEFAULT: 'redlib.catsarch.com',
    REDDIT_JSON_URL: 'https://raw.githubusercontent.com/redlib-org/redlib-instances/refs/heads/main/instances.json',
    IMGUR_REPLACEMENT: 'rmgur.com'
  };
  // ---------------------

  const { hostname, href } = location;

  // 1. Handle Imgur (Direct Redirect)
  if (hostname === 'imgur.com') {
    location.replace(href.replace('imgur.com', CONFIG.IMGUR_REPLACEMENT));
    return;
  }

  // 2. Handle Reddit
  if (hostname === 'www.reddit.com') {

    // FAST MODE: Direct redirect to your preferred instance
    if (!CONFIG.FETCH_REMOTE_INSTANCES) {
      location.replace(href.replace('www.reddit.com', CONFIG.REDDIT_DEFAULT));
      return;
    }

    // DYNAMIC MODE: Pull from GitHub
    GM_xmlhttpRequest({
      method: 'GET',
      url: CONFIG.REDDIT_JSON_URL,
      onload: function (response) {
        try {
          const data = JSON.parse(response.responseText);
          const instances = data.instances.filter(i => i.url && i.url.startsWith('https://'));

          if (instances.length > 0) {
            const random = instances[Math.floor(Math.random() * instances.length)];
            const instanceHost = new URL(random.url).hostname;
            location.replace(href.replace('www.reddit.com', instanceHost));
          } else {
            // If list is empty, use your default
            location.replace(href.replace('www.reddit.com', CONFIG.REDDIT_DEFAULT));
          }
        } catch (e) {
          location.replace(href.replace('www.reddit.com', CONFIG.REDDIT_DEFAULT));
        }
      },
      onerror: function () {
        location.replace(href.replace('www.reddit.com', CONFIG.REDDIT_DEFAULT));
      }
    });
  }
})();
