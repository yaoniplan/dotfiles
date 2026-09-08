// ==UserScript==
// @name         Yaoniplan Sidebar
// @namespace    https://github.com/yaoniplan/dotfiles/tree/master/.local/src/userscript
// @version      1.0.0
// @description  Minimal sidebar — local-first list, optional remote, fzf search
// @match        https://yaoniplan.eu.org/*
// @icon         data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIiB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIj4KICA8IS0tIENpcmNsZSAoTWF4aW1pemVkIHNpemUpIC0tPgogIDxjaXJjbGUgY3g9IjI1NiIgY3k9IjI1NiIgcj0iMjM2IiBmaWxsPSJub25lIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjM0IiAvPgogIAogIDwhLS0gVXBwZXIgTGluZSAoRmxhdCBlbmRzLCBsZWZ0LWFsaWduZWQpIC0tPgogIDxsaW5lIHgxPSIxNDgiIHkxPSIyMDAiIHgyPSIzNTgiIHkyPSIyMDAiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMzQiIHN0cm9rZS1saW5lY2FwPSJidXR0IiAvPgogIAogIDwhLS0gTG93ZXIgTGluZSAoRmxhdCBlbmRzLCBsZWZ0LWFsaWduZWQpIC0tPgogIDxsaW5lIHgxPSIxNDgiIHkxPSIzMjAiIHgyPSIyNjgiIHkyPSIzMjAiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMzQiIHN0cm9rZS1saW5lY2FwPSJidXR0IiAvPgo8L3N2Zz4K
// @author       yaoniplan
// @license      MIT
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @connect      *
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // 空 = 纯本地；填自建地址则启用同步（如 https://paste.c-net.org/<an-id-known-only-to-you>）
  const REMOTE_URL = '';

  const BASE = 'https://yaoniplan.eu.org/';
  const SIDEBAR_WIDTH = 280;
  const CACHE_KEY = 'yp-sidebar-urls';
  const MIN_FETCH_INTERVAL = 30 * 1000;

  let initialized = false;
  let sidebar, toggleBtn, searchEl, listEl, statusEl;
  let urls = [];
  let filtered = [];
  let currentUrl = '';
  let theme, styleEl;
  let hideTimer, lastFetchTime = 0, fetching = false;

  // ---------- 启动：隐形按钮 ----------
  toggleBtn = document.createElement('button');
  toggleBtn.id = 'yp-sidebar-toggle';
  toggleBtn.textContent = '☰';
  toggleBtn.title = 'Sidebar';
  toggleBtn.setAttribute('aria-label', 'Open sidebar');
  toggleBtn.style.cssText = `
    position: fixed; top: 14px; left: 14px; z-index: 10001;
    width: 36px; height: 36px; border-radius: 10px;
    background: transparent; color: transparent;
    border: 1px solid transparent; cursor: pointer;
    opacity: 0; font-size: 16px;
    display: flex; align-items: center; justify-content: center;
  `;
  document.documentElement.appendChild(toggleBtn);
  toggleBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    ensureInit();
    sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
  });

  function ensureInit() {
    if (initialized) return;
    initialized = true;
    initSidebar();
  }

  function getTheme() {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return isDark
      ? { bg: '#0d1117', text: '#c9d1d9', muted: '#8b949e', border: '#21262d', hover: '#161b22', active: '#161b22', danger: '#f85149' }
      : { bg: '#ffffff', text: '#24292f', muted: '#57606a', border: '#d0d7de', hover: '#f6f8fa', active: '#f6f8fa', danger: '#cf222e' };
  }

  function applyTheme() {
    theme = getTheme();
    if (styleEl) styleEl.remove();
    styleEl = GM_addStyle(`
      #yp-sidebar-toggle {
        position: fixed; top: 14px; left: 14px; z-index: 10001;
        width: 36px; height: 36px; border-radius: 10px;
        background: transparent; color: ${theme.text};
        border: 1px solid transparent; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px; opacity: 0;
        transition: opacity .4s ease, background .25s ease, border-color .25s ease, transform .22s ease;
      }
      #yp-sidebar-toggle:hover, #yp-sidebar-toggle:active, #yp-sidebar-toggle.show {
        opacity: 0.85; background: ${theme.bg}; border-color: ${theme.border};
      }
      #yp-sidebar-toggle.hidden { opacity: 0 !important; pointer-events: none; transform: scale(0.92); }
      #yp-sidebar {
        position: fixed; top: 0; bottom: 0; left: 0; width: ${SIDEBAR_WIDTH}px;
        background: ${theme.bg}; color: ${theme.text}; z-index: 10000;
        transform: translateX(-100%); transition: transform .28s cubic-bezier(0.32, 0.72, 0, 1);
        display: flex; flex-direction: column;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        border-right: 1px solid ${theme.border};
      }
      #yp-sidebar.open { transform: translateX(0); }
      body { transition: transform .28s cubic-bezier(0.32, 0.72, 0, 1) !important; }
      body.yp-shifted { transform: translateX(${SIDEBAR_WIDTH}px) !important; }
      html.yp-shifted, html.yp-shifted body { overflow-x: hidden !important; overscroll-behavior-x: none !important; }
      #yp-sidebar-header { padding: 14px 12px 10px; border-bottom: 1px solid ${theme.border}; }
      #yp-search {
        width: 100%; padding: 9px 14px; border: none; border-radius: 10px;
        background: transparent; color: ${theme.text}; font-size: 16px;
        outline: none; box-sizing: border-box; -webkit-appearance: none;
      }
      #yp-search::placeholder { color: ${theme.muted}; font-size: 13px; }
      #yp-search:focus { background: ${theme.hover}; }
      #yp-list { flex: 1; overflow-y: auto; padding: 6px 0; -webkit-overflow-scrolling: touch; }
      #yp-list::-webkit-scrollbar { width: 5px; }
      #yp-list::-webkit-scrollbar-thumb { background: ${theme.border}; border-radius: 3px; }
      .yp-item {
        display: flex; align-items: center; padding: 7px 14px; cursor: pointer; gap: 6px;
        font-size: 13px; line-height: 1.4; color: ${theme.text}; border-radius: 6px; margin: 0 6px;
      }
      .yp-item:hover { background: ${theme.hover}; }
      .yp-item.active { background: ${theme.active}; font-weight: 500; }
      .yp-item-text { flex: 1; word-break: break-all; }
      .yp-delete {
        opacity: 0; background: none; border: none; color: ${theme.danger};
        font-size: 14px; cursor: pointer; padding: 0 4px; line-height: 1;
      }
      .yp-item:hover .yp-delete { opacity: 0.65; }
      .yp-delete:hover { opacity: 1 !important; }
      #yp-status { font-size: 11px; color: ${theme.muted}; text-align: center; padding: 6px 12px 10px; min-height: 14px; }
    `);
  }

  function initSidebar() {
    applyTheme();
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);

    sidebar = document.createElement('div');
    sidebar.id = 'yp-sidebar';
    sidebar.innerHTML = `
      <div id="yp-sidebar-header">
        <input type="search" id="yp-search" placeholder="Filter or paste URL…" autocomplete="off" enterkeyhint="go">
      </div>
      <div id="yp-list"></div>
      <div id="yp-status"></div>
    `;
    document.documentElement.appendChild(sidebar);

    listEl = document.getElementById('yp-list');
    searchEl = document.getElementById('yp-search');
    statusEl = document.getElementById('yp-status');

    const path = location.pathname.slice(1);
    if (path) currentUrl = decodeURIComponent(path);

    searchEl.addEventListener('input', filterList);
    searchEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); tryAddOrOpen(); }
    });

    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    if (isIOS) {
      searchEl.addEventListener('touchstart', () => {
        const sx = window.scrollX, sy = window.scrollY;
        searchEl.style.transform = 'translateY(-10000px)';
        searchEl.focus({ preventScroll: true });
        requestAnimationFrame(() => {
          searchEl.style.transform = '';
          window.scrollTo(sx, sy);
          [0, 50, 120].forEach((t) => setTimeout(() => window.scrollTo(sx, sy), t));
        });
      }, { passive: true });
    }
    searchEl.addEventListener('focus', () => {
      const sx = window.scrollX, sy = window.scrollY;
      requestAnimationFrame(() => window.scrollTo(sx, sy));
      setTimeout(() => window.scrollTo(sx, sy), 10);
      setTimeout(() => window.scrollTo(sx, sy), 80);
    });

    document.addEventListener('click', (e) => {
      if (!sidebar.classList.contains('open')) return;
      if (sidebar.contains(e.target) || toggleBtn.contains(e.target)) return;
      closeSidebar();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('open')) closeSidebar();
    });
    window.addEventListener('popstate', (e) => {
      const url = (e.state && e.state.url) || getCurrentRawUrl();
      if (url) { currentUrl = url; openUrl(url, true); }
    });
    window.addEventListener('pageshow', () => {
      resetToFullList();
      if (sidebar.classList.contains('open')) closeSidebar();
    });
    document.addEventListener('mousemove', (e) => {
      if (e.clientX < 60 && e.clientY < 60) flashToggle();
    });

    load(true);
  }

  function flashToggle() {
    if (!toggleBtn) return;
    toggleBtn.classList.add('show');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => toggleBtn.classList.remove('show'), 1200);
  }

  function setStatus(msg, isError = false) {
    if (!statusEl) return;
    statusEl.textContent = msg || '';
    statusEl.style.color = isError ? theme.danger : theme.muted;
    if (msg) {
      clearTimeout(setStatus._t);
      setStatus._t = setTimeout(() => { if (statusEl.textContent === msg) statusEl.textContent = ''; }, 2000);
    }
  }

  function getCurrentRawUrl() {
    if (currentUrl) return currentUrl;
    const path = location.pathname.slice(1);
    return path ? decodeURIComponent(path) : '';
  }

  function displayName(url) {
    try {
      const parts = new URL(url).pathname.split('/').filter(Boolean);
      if (parts.length >= 2) return parts.slice(-2).join('/');
      return parts[0] || new URL(url).hostname;
    } catch {
      const segs = url.split('/').filter(Boolean);
      return segs.length >= 2 ? segs.slice(-2).join('/') : (segs.at(-1) || url);
    }
  }

  function isValidHttpUrl(str) {
    try {
      const u = new URL(str);
      return u.protocol === 'http:' || u.protocol === 'https:';
    } catch { return false; }
  }

  function looksLikeMarkdown(text) {
    if (!text || typeof text !== 'string') return false;
    const t = text.trim();
    if (t.length < 2) return false;
    if (/^\s*<(!DOCTYPE|html|head|body)\b/i.test(t)) return false;
    if (/<html[\s>]/i.test(t) && /<\/html>/i.test(t)) return false;
    const signals = [/^#{1,6}\s+\S/m, /^\s*[-*+]\s+\S/m, /^\s*\d+\.\s+\S/m, /\[[^\]]+\]\([^)]+\)/, /`[^`]+`/, /^```/m, /^>\s+\S/m];
    if (signals.some((re) => re.test(t))) return true;
    return !/<[a-z][\s\S]*>/i.test(t);
  }

  function fetchText(url) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET', url,
        onload: (res) => res.status >= 200 && res.status < 300 ? resolve(res.responseText || '') : reject(new Error('HTTP ' + res.status)),
        onerror: () => reject(new Error('Network error')),
      });
    });
  }

  async function validateMarkdownUrl(url) {
    const text = await fetchText(url);
    if (!looksLikeMarkdown(text)) throw new Error('Not valid Markdown');
    return text;
  }

  function renderList() {
    if (!listEl) return;
    listEl.innerHTML = '';
    const current = getCurrentRawUrl();
    if (filtered.length === 0) {
      listEl.innerHTML = `<div style="padding:24px 14px;text-align:center;color:${theme.muted};font-size:13px;">${urls.length === 0 ? 'Empty' : 'No matches'}</div>`;
      return;
    }
    filtered.forEach((url) => {
      const item = document.createElement('div');
      item.className = 'yp-item' + (url === current ? ' active' : '');
      item.innerHTML = `<div class="yp-item-text" title="${url}">${displayName(url)}</div><button class="yp-delete" title="Delete">×</button>`;
      item.querySelector('.yp-item-text').onclick = () => openUrl(url);
      item.querySelector('.yp-delete').onclick = (e) => { e.stopPropagation(); deleteUrl(url); };
      listEl.appendChild(item);
    });
  }

  // fzf：空格分词 AND
  function filterList() {
    const q = searchEl.value.trim().toLowerCase();
    if (!q) filtered = [...urls];
    else {
      const terms = q.split(/\s+/).filter(Boolean);
      filtered = urls.filter((u) => {
        const hay = u.toLowerCase();
        return terms.every((t) => hay.includes(t));
      });
    }
    renderList();
  }

  function resetToFullList() {
    if (!searchEl) return;
    searchEl.value = '';
    filtered = [...urls];
    renderList();
  }

  async function openUrl(url, fromHistory = false, preloadedText = null) {
    if (!url) return;
    const markdownEl = document.querySelector('#markdown-content');
    if (!markdownEl) { location.href = BASE + url; return; }

    setStatus('Loading…');
    try {
      const markdown = preloadedText != null ? preloadedText : await fetchText(url);
      markdownEl.innerHTML = typeof marked === 'function' ? marked(markdown) : markdown;
      if (typeof renderMathInElement === 'function') {
        renderMathInElement(markdownEl, {
          delimiters: [{ left: '$$', right: '$$', display: true }, { left: '$', right: '$', display: false }],
        });
      }
      currentUrl = url;
      if (!fromHistory) history.pushState({ url }, '', BASE + url);
      renderList();
      searchEl.value = '';
      filterList();
      if (!fromHistory) { searchEl.blur(); closeSidebar(); }
      setStatus('');
    } catch (e) {
      setStatus('Load failed', true);
    }
  }

  // ---------- 存储：本地优先，可选远程 ----------
  function readLocal() {
    try {
      const data = JSON.parse(localStorage.getItem(CACHE_KEY) || '[]');
      return Array.isArray(data) ? data.filter(isValidHttpUrl) : [];
    } catch { return []; }
  }

  function writeLocal(list) {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(list)); } catch {}
  }

  function fetchRemote() {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url: `${REMOTE_URL}?t=${Date.now()}`,
        headers: { 'User-Agent': 'curl/8.0', 'Cache-Control': 'no-cache' },
        onload: (res) => {
          if (res.status >= 200 && res.status < 300) {
            const text = (res.responseText || '').trim();
            resolve(text ? text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean) : []);
          } else reject(new Error('HTTP ' + res.status));
        },
        onerror: () => reject(new Error('Network error')),
      });
    });
  }

  function saveRemote(list) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'PUT',
        url: REMOTE_URL,
        data: list.join('\n'),
        headers: { 'Content-Type': 'text/plain', 'User-Agent': 'curl/8.0' },
        onload: (res) => res.status >= 200 && res.status < 300 ? resolve() : reject(new Error('HTTP ' + res.status)),
        onerror: () => reject(new Error('Network error')),
      });
    });
  }

  async function persist(list) {
    writeLocal(list);
    if (REMOTE_URL) await saveRemote(list);
  }

  async function load(force = false) {
    const local = readLocal();
    if (local.length) {
      urls = local;
      filtered = [...urls];
      renderList();
    }

    if (!REMOTE_URL) return;

    const now = Date.now();
    if (!force && (fetching || now - lastFetchTime < MIN_FETCH_INTERVAL)) return;
    fetching = true;
    lastFetchTime = now;
    try {
      const fresh = await fetchRemote();
      if (JSON.stringify(fresh) !== JSON.stringify(urls)) {
        urls = fresh;
        filtered = [...urls];
        writeLocal(urls);
        filterList();
      }
    } catch {
      if (urls.length === 0) setStatus('Load failed', true);
    } finally {
      fetching = false;
    }
  }

  async function tryAddOrOpen() {
    const value = searchEl.value.trim();

    if (isValidHttpUrl(value) && !urls.includes(value)) {
      try {
        setStatus('Validating…');
        const text = await validateMarkdownUrl(value);
        setStatus('Adding…');
        urls = [value, ...urls];
        await persist(urls);
        searchEl.value = '';
        filterList();
        await openUrl(value, false, text);
      } catch (e) {
        setStatus(e.message === 'Not valid Markdown' ? 'Not valid Markdown' : 'Add failed', true);
      }
      return;
    }

    if (filtered.length > 0) { openUrl(filtered[0]); return; }
    if (isValidHttpUrl(value) && urls.includes(value)) openUrl(value);
    else if (value) setStatus('No match', true);
  }

  async function deleteUrl(url) {
    if (!confirm('Delete?\n\n' + url)) return;
    try {
      urls = urls.filter((u) => u !== url);
      await persist(urls);
      filterList();
      setStatus('Deleted');
    } catch {
      setStatus('Delete failed', true);
    }
  }

  function openSidebar() {
    ensureInit();
    sidebar.classList.add('open');
    document.body.classList.add('yp-shifted');
    document.documentElement.classList.add('yp-shifted');
    toggleBtn.classList.add('hidden');
    load();
    if (window.innerWidth > 768) setTimeout(() => searchEl.focus({ preventScroll: true }), 60);
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    document.body.classList.remove('yp-shifted');
    document.documentElement.classList.remove('yp-shifted');
    toggleBtn.classList.remove('hidden');
    if (searchEl) searchEl.blur();
    flashToggle();
  }

  document.addEventListener('mousemove', (e) => {
    if (e.clientX < 60 && e.clientY < 60) { ensureInit(); flashToggle(); }
  }, { passive: true });

  document.addEventListener('touchstart', (e) => {
    if (initialized && sidebar?.classList.contains('open')) return;
    const t = e.touches[0];
    if (t.clientX < 70 && t.clientY < 70) {
      ensureInit();
      flashToggle();
      openSidebar();
      searchEl.focus({ preventScroll: true });
    }
  }, { passive: true });
})();
