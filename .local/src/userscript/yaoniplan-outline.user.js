// ==UserScript==
// @name         Yaoniplan Outline
// @namespace    https://github.com/yaoniplan/dotfiles/tree/master/.local/src/userscript
// @version      1.0.0
// @description  On-demand Markdown contents sidebar with an invisible Vimium-accessible toggle, current-heading highlighting, and history-free navigation without tap flashes.
// @match        https://yaoniplan.eu.org/*
// @icon         data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIiB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIj4KICA8IS0tIE91dGVyIGNpcmNsZSAtLT4KICA8Y2lyY2xlIGN4PSIyNTYiIGN5PSIyNTYiIHI9IjIzNiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIzNCIgLz4KCiAgPCEtLSBVcHBlciByb3c6IGhvbGxvdyByaW5nICsgbGluZSAtLT4KICA8Y2lyY2xlIGN4PSIxNzIiIGN5PSIxNzIiIHI9IjQyIiBmaWxsPSJub25lIiBzdHJva2U9ImJsYWNrIiBzdHJva2Utd2lkdGg9IjI4IiAvPgogIDxsaW5lIHgxPSIyNTYiIHkxPSIxNzIiIHgyPSIzOTYiIHkyPSIxNzIiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMjgiIHN0cm9rZS1saW5lY2FwPSJidXR0IiAvPgoKICA8IS0tIExvd2VyIHJvdzogaG9sbG93IHJpbmcgKyBsaW5lIC0tPgogIDxjaXJjbGUgY3g9IjE3MiIgY3k9IjM0MCIgcj0iNDIiIGZpbGw9Im5vbmUiIHN0cm9rZT0iYmxhY2siIHN0cm9rZS13aWR0aD0iMjgiIC8+CiAgPGxpbmUgeDE9IjI1NiIgeTE9IjM0MCIgeDI9IjM5NiIgeTI9IjM0MCIgc3Ryb2tlPSJibGFjayIgc3Ryb2tlLXdpZHRoPSIyOCIgc3Ryb2tlLWxpbmVjYXA9ImJ1dHQiIC8+Cjwvc3ZnPgo=
// @author       yaoniplan
// @license      MIT
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const content = document.querySelector('#markdown-content');
  if (!content) return;

  const style = document.createElement('style');
  style.textContent = `
    .tm-md-contents.markdown-body {
      display: none;
      position: fixed;
      inset: 0 0 0 auto;
      z-index: 20;
      width: min(280px, 90vw);
      max-width: none;
      min-width: 0;
      margin: 0;
      padding: 0;
      border-left: 1px solid var(--color-border-default, currentColor);
      background: var(--color-canvas-default, Canvas);
      color: var(--color-fg-default, CanvasText);
      font-size: 13px;
      line-height: 1.4;
      box-sizing: border-box;
      overflow-y: auto;
      overscroll-behavior: contain;
    }
    .tm-md-contents.markdown-body.tm-md-open:not([hidden]) { display: block; }
    .tm-md-contents[hidden], .tm-md-toggle[hidden] { display: none !important; }
    .tm-md-toggle {
      position: fixed;
      top: max(14px, env(safe-area-inset-top));
      right: max(14px, env(safe-area-inset-right));
      z-index: 21;
      width: 36px;
      height: 36px;
      margin: 0;
      padding: 0;
      appearance: none !important;
      -webkit-appearance: none !important;
      border: 0 !important;
      border-radius: 0 !important;
      background: transparent !important;
      color: transparent !important;
      box-shadow: none !important;
      outline: none !important;
      text-shadow: none !important;
      overflow: hidden;
      forced-color-adjust: none;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    .tm-md-toggle:hover, .tm-md-toggle:focus, .tm-md-toggle:active {
      border: 0 !important;
      background: transparent !important;
      color: transparent !important;
      box-shadow: none !important;
      outline: none !important;
    }
    .tm-md-toggle::before, .tm-md-toggle::after {
      content: none !important;
      display: none !important;
    }
    .tm-md-contents.markdown-body .tm-md-list:not([type]) {
      margin: 0;
      padding: max(60px, calc(env(safe-area-inset-top) + 50px)) 0 12px;
      list-style: none;
    }
    .tm-md-contents .tm-md-list li {
      margin: 0 6px;
      padding: 0 0 0 calc(var(--depth) * .8rem);
      list-style: none;
      overflow-wrap: anywhere;
    }
    .tm-md-contents .tm-md-list a {
      display: block;
      padding: 7px 8px;
      border-radius: 6px;
      color: var(--color-fg-default, CanvasText);
      text-decoration: none;
      /* Suppress the browser's transient touch highlight on sidebar links. */
      -webkit-tap-highlight-color: transparent;
    }
    .tm-md-contents .tm-md-list a:focus:not(:focus-visible) {
      outline: none;
      box-shadow: none;
    }
    .tm-md-contents .tm-md-list a:hover,
    .tm-md-contents .tm-md-list a:focus-visible {
      background: var(--color-canvas-subtle, Canvas);
      text-decoration: none;
    }
    .tm-md-contents .tm-md-list a[aria-current="location"] {
      color: var(--color-accent-fg, LinkText);
      background: var(--color-neutral-muted, var(--color-canvas-subtle, Canvas));
      font-weight: 600;
    }
  `;
  document.head.appendChild(style);

  // Transparent rather than display:none or visibility:hidden, so Vimium C
  // can discover and activate the button while it remains visually unobtrusive.
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'tm-md-toggle';
  button.setAttribute('aria-label', 'Toggle table of contents');
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('aria-controls', 'tm-md-contents-panel');
  // The accessible label identifies the control without rendering text.
  button.hidden = true;

  const nav = document.createElement('nav');
  // Reuse the site's own light and dark theme variables.
  nav.className = 'tm-md-contents markdown-body';
  nav.id = 'tm-md-contents-panel';
  nav.setAttribute('aria-label', 'Table of contents');
  nav.hidden = true;
  const list = document.createElement('ol');
  list.className = 'tm-md-list';
  nav.appendChild(list);
  document.body.append(nav, button);

  let isOpen = false;
  let entries = [];
  let activeLink = null;

  function revealActiveLink() {
    if (!isOpen || !activeLink) return;
    const panelRect = nav.getBoundingClientRect();
    const linkRect = activeLink.getBoundingClientRect();
    if (linkRect.top < panelRect.top) {
      nav.scrollTop += linkRect.top - panelRect.top - 8;
    } else if (linkRect.bottom > panelRect.bottom) {
      nav.scrollTop += linkRect.bottom - panelRect.bottom + 8;
    }
  }

  function updateCurrentHeading() {
    if (!entries.length) return;
    const threshold = Math.min(120, window.innerHeight * 0.2);
    let current = entries[0];
    for (const entry of entries) {
      if (entry.heading.getBoundingClientRect().top <= threshold) current = entry;
      else break;
    }
    // The final heading may never reach the threshold on a short last section.
    const scroller = document.scrollingElement;
    if (scroller && scroller.scrollHeight > scroller.clientHeight &&
        scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 2) {
      current = entries[entries.length - 1];
    }
    if (activeLink !== current.link) {
      if (activeLink) activeLink.removeAttribute('aria-current');
      activeLink = current.link;
      activeLink.setAttribute('aria-current', 'location');
      revealActiveLink();
    }
  }

  let scrollFrame = 0;
  function scheduleCurrentHeading() {
    if (scrollFrame) return;
    scrollFrame = requestAnimationFrame(() => {
      scrollFrame = 0;
      updateCurrentHeading();
    });
  }
  window.addEventListener('scroll', scheduleCurrentHeading, { passive: true });
  window.addEventListener('resize', scheduleCurrentHeading, { passive: true });

  function setOpen(open) {
    isOpen = open;
    nav.hidden = !open;
    nav.classList.toggle('tm-md-open', open);
    button.setAttribute('aria-expanded', String(open));
    if (open) {
      updateCurrentHeading();
      revealActiveLink();
    }
  }

  // Do not restore an open panel after reload or back/forward cache navigation.
  // A Vimium C activation may be synthetic, so do not require isTrusted here.
  window.addEventListener('pagehide', () => setOpen(false));
  window.addEventListener('pageshow', event => {
    if (event.persisted) setOpen(false);
  });
  button.addEventListener('click', () => setOpen(!isOpen));
  list.addEventListener('click', event => {
    if (event.target.closest('a')) setOpen(false);
  });
  document.addEventListener('click', event => {
    if (!nav.hidden && !nav.contains(event.target) && !button.contains(event.target)) setOpen(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !nav.hidden) {
      setOpen(false);
      button.focus();
    }
  });

  function refresh() {
    const headings = Array.from(content.querySelectorAll('h1, h2, h3, h4, h5, h6'))
      .filter(heading => heading.textContent.trim());
    button.hidden = headings.length === 0;
    if (!headings.length) setOpen(false);
    const fragment = document.createDocumentFragment();
    entries = [];
    activeLink = null;
    if (headings.length) {
      const minLevel = Math.min(...headings.map(heading => Number(heading.tagName[1])));
      for (const heading of headings) {
        const item = document.createElement('li');
        item.style.setProperty('--depth', String(Number(heading.tagName[1]) - minLevel));
        const link = document.createElement('a');
        if (heading.id && document.getElementById(heading.id) === heading) {
          link.href = '#' + encodeURIComponent(heading.id);
        } else {
          // Do not add IDs to or otherwise alter the original headings.
          link.href = '#';
        }
        // Scroll directly rather than navigating to a fragment, which would
        // change the URL and add an entry to the browser's history.
        link.addEventListener('click', event => {
          event.preventDefault();
          heading.scrollIntoView();
        });
        link.addEventListener('auxclick', event => event.preventDefault());
        link.textContent = heading.textContent.trim();
        entries.push({ heading, link });
        item.appendChild(link);
        fragment.appendChild(item);
      }
    }
    list.replaceChildren(fragment);
    updateCurrentHeading();
  }

  // Markdown is loaded or replaced asynchronously, including by the user's
  // separate sidebar script. Observe only the content, not our own sidebar.
  let timer;
  const observer = new MutationObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(refresh, 100);
  });
  observer.observe(content, { childList: true, subtree: true, characterData: true });
  refresh();
})();

