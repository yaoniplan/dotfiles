// ==UserScript==
// @name         Reddit & Imgur Redirector
// @namespace    https://github.com/yaoniplan/dotfiles/tree/master/.local/src/userscript
// @version      1.0.4
// @description  Redirect Reddit to Redlib, Imgur to Rimgo.
// @match        *://www.reddit.com/*
// @match        *://imgur.com/*
// @match        *://*.imgur.com/*
// @icon         data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iMzYwLjAwMDAwMHB0IiBoZWlnaHQ9IjM2MC4wMDAwMDBwdCIgdmlld0JveD0iMCAwIDM2MC4wMDAwMDAgMzYwLjAwMDAwMCIKIHByZXNlcnZlQXNwZWN0UmF0aW89InhNaWRZTWlkIG1lZXQiPgoKPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMC4wMDAwMDAsMzYwLjAwMDAwMCkgc2NhbGUoMC4xMDAwMDAsLTAuMTAwMDAwKSIKZmlsbD0iIzAwMDAwMCIgc3Ryb2tlPSJub25lIj4KPHBhdGggZD0iTTI2NzAgMzA1NSBjLTIxMiAtMTggLTQ3OSAtNDEgLTU5MyAtNTEgbC0yMDkgLTE3IDE5MyAtMTkzIDE5MyAtMTkzCi0zNjEgLTM2MyBjLTQzMCAtNDM0IC01MjcgLTUzNCAtNTcxIC01OTYgLTUzIC03NCAtMTA4IC0xNzIgLTEzOCAtMjQ1IC0xNQotMzcgLTMzIC02NiAtMzggLTY0IC0xOSA2IC04NSAxMzAgLTExMSAyMDcgLTM2IDExMSAtNDkgMjAxIC00MiAzMDQgOCAxMjEgMzAKMjAzIDgzIDMxMSAxMjggMjU5IDM1NiA0MTcgNjYyIDQ1OCBsOTIgMTIgLTE5OSAxOTkgLTIwMCAyMDAgLTQzIC0xMyBjLTYzCi0xOSAtMjI1IC0xMDEgLTMxMCAtMTU3IC05NCAtNjIgLTI3MSAtMjM5IC0zMzEgLTMzMCAtMTQ5IC0yMjYgLTIxOSAtNDU3Ci0yMTggLTcxOSAwIC0yNzYgNjUgLTQ5MSAyMTYgLTcyMCA1OSAtODkgMTk4IC0yMzYgMjkwIC0zMDYgMjIzIC0xNzAgNDg2Ci0yNTkgNzY3IC0yNTkgbDEwMSAwIC02MCAzOSBjLTc5IDUxIC0xNjQgMTM5IC0yMDIgMjEwIC04MyAxNTYgLTgwIDM0OCA2IDUxNQozMyA2MyA4NSAxMjAgNDg3IDUyNCAyNDggMjQ5IDQ1MyA0NTEgNDU3IDQ1MCA1IC0yIDkzIC04NyAxOTcgLTE5MCAxMDUgLTEwNAoxOTQgLTE4OCAxOTkgLTE4OCA1IDAgMjYgMjQ0IDQ3IDU0MyAyMCAyOTggNDAgNTcwIDQzIDYwNSA1IDQ5IDMgNjIgLTggNjEgLTgKLTEgLTE4NyAtMTYgLTM5OSAtMzR6Ii8+CjxwYXRoIGQ9Ik0yNTA2IDEzOTEgYy04OSAtMTQ0IC0yMDMgLTI0OSAtMzUwIC0zMjEgLTExOSAtNTkgLTIxNiAtODAgLTM2NAotODEgbC0xMjMgMCA2IC0zMiBjMjIgLTEwMSA1OSAtMTc4IDExMyAtMjMzIDE5MSAtMTk4IDQyOCAtMTk0IDcyOCAxMiAxMjYgODYKMjY2IDIyNSAzNTAgMzQ1IGwyOCA0MCAtMTY1IDE2NSBjLTkwIDkwIC0xNjkgMTY0IC0xNzUgMTY0IC02IDAgLTI4IC0yNyAtNDgKLTU5eiIvPgo8L2c+Cjwvc3ZnPgo=
// @author       yaoniplan
// @license      MIT
// @run-at       document-start
// @grant        GM_xmlhttpRequest
// @connect      raw.githubusercontent.com
// @connect      codeberg.org
// ==/UserScript==

(function () {
  // --- CONFIGURATION ---
  const CONFIG = {
    FETCH_REMOTE_INSTANCES: false, // Set to true to pull dynamic lists from remote JSON
    REDDIT_DEFAULT: 'redlib.catsarch.com',
    REDDIT_JSON_URL: 'https://raw.githubusercontent.com/redlib-org/redlib-instances/refs/heads/main/instances.json',
    IMGUR_DEFAULT: 'ri.bcow.xyz',
    // https://github.com/libredirect/instances/raw/refs/heads/main/data.json
    IMGUR_JSON_URL: 'https://codeberg.org/rimgo/instances/raw/branch/main/config.json'
  };
  // ---------------------

  const { hostname, pathname, search, hash } = location;
  const MEDIA_EXT_RE = /\.(mp4|webm|gifv?|jpe?g|png|webp|avif)$/i;

  function buildTargetUrl(targetHost) {
    let targetPath = pathname;
    if (hostname === 'i.imgur.com' && MEDIA_EXT_RE.test(targetPath)) {
      targetPath = targetPath.replace(MEDIA_EXT_RE, '');
    }
    return `https://${targetHost}${targetPath}${search}${hash}`;
  }

  function redirectToHost(targetHost) {
    if (!targetHost) return;
    const targetUrl = buildTargetUrl(targetHost);
    if (targetUrl !== location.href) {
      location.replace(targetUrl);
    }
  }

  function extractHttpsHosts(payload, preferredKeys = []) {
    const candidates = [];

    const collect = (node) => {
      if (!node) return;
      if (typeof node === 'string') {
        if (node.startsWith('https://')) candidates.push(node);
        return;
      }
      if (Array.isArray(node)) {
        node.forEach(collect);
        return;
      }
      if (typeof node === 'object') {
        for (const key of ['url', 'clearnet', 'instance', 'host', 'domain', ...preferredKeys]) {
          if (node[key]) collect(node[key]);
        }
      }
    };

    if (Array.isArray(payload)) {
      collect(payload);
    } else if (payload && typeof payload === 'object') {
      for (const key of preferredKeys) {
        if (payload[key]) collect(payload[key]);
      }
      if (candidates.length === 0) {
        collect(payload.instances || payload);
      }
    }

    const hosts = [];
    for (const rawUrl of candidates) {
      try {
        const parsed = new URL(rawUrl.startsWith('http') ? rawUrl : `https://${rawUrl}`);
        if (parsed.protocol === 'https:' && parsed.hostname) {
          hosts.push(parsed.hostname);
        }
      } catch (_) {
        // Ignore malformed entries
      }
    }

    return [...new Set(hosts)];
  }

  function fetchAndRedirect(url, fallbackHost, preferredKeys = []) {
    GM_xmlhttpRequest({
      method: 'GET',
      url,
      onload: function (response) {
        try {
          const data = JSON.parse(response.responseText);
          const hosts = extractHttpsHosts(data, preferredKeys);
          if (hosts.length > 0) {
            const randomHost = hosts[Math.floor(Math.random() * hosts.length)];
            redirectToHost(randomHost);
            return;
          }
        } catch (_) {
          // Fall back on parse failure
        }
        redirectToHost(fallbackHost);
      },
      onerror: function () {
        redirectToHost(fallbackHost);
      }
    });
  }

  // 1. Handle Imgur
  if (hostname.endsWith('imgur.com')) {
    if (!CONFIG.FETCH_REMOTE_INSTANCES) {
      redirectToHost(CONFIG.IMGUR_DEFAULT);
      return;
    }
    fetchAndRedirect(CONFIG.IMGUR_JSON_URL, CONFIG.IMGUR_DEFAULT, ['rimgo', 'clearnet', 'instances']);
    return;
  }

  // 2. Handle Reddit
  if (hostname === 'www.reddit.com') {
    if (!CONFIG.FETCH_REMOTE_INSTANCES) {
      redirectToHost(CONFIG.REDDIT_DEFAULT);
      return;
    }
    fetchAndRedirect(CONFIG.REDDIT_JSON_URL, CONFIG.REDDIT_DEFAULT, ['instances']);
  }
})();
