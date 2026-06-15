/**
 * Interview Q&A Interaction Logic (multi-page)
 */
(function () {
  'use strict';

  const BASE = window.__BASE_PREFIX__ || '';
  const SEARCH_INDEX = Array.isArray(window.__SEARCH_INDEX__) ? window.__SEARCH_INDEX__ : [];

  // State
  const state = {
    fuse: null,
    results: [],
    activeResult: -1,
    mastered: new Set(JSON.parse(localStorage.getItem('interview-mastered') || '[]')),
    starred: new Set(JSON.parse(localStorage.getItem('interview-starred') || '[]'))
  };

  // Elements
  const el = {
    cards: document.querySelectorAll('.card'),
    searchInput: document.getElementById('search'),
    searchResults: document.getElementById('searchResults'),
    searchStats: document.getElementById('searchStats'),
    searchPrev: document.getElementById('searchPrev'),
    searchNext: document.getElementById('searchNext'),
    noResults: document.getElementById('noResults'),
    navLinks: document.querySelectorAll('.nav-list a'),
    backTop: document.getElementById('backTop'),
    sidebar: document.getElementById('sidebar'),
    menuBtn: document.getElementById('menuBtn'),
    themeBtn: document.getElementById('themeBtn'),
    expandAllBtn: document.getElementById('expandAll'),
    collapseAllBtn: document.getElementById('collapseAll'),
    randomBtn: document.getElementById('randomBtn')
  };

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  /**
   * Card expansion
   */
  function setExpanded(card, open) {
    const body = card.querySelector('.card-body');
    const header = card.querySelector('.card-header');
    const btn = card.querySelector('.toggle-btn');
    if (!body) return;
    if (open) {
      body.hidden = false;
      card.classList.add('expanded');
      if (header) header.setAttribute('aria-expanded', 'true');
      if (btn) btn.textContent = '收起';
    } else {
      body.hidden = true;
      card.classList.remove('expanded');
      if (header) header.setAttribute('aria-expanded', 'false');
      if (btn) btn.textContent = '展开';
    }
  }

  el.cards.forEach(card => {
    const header = card.querySelector('.card-header');
    const idx = card.dataset.idx;

    if (state.mastered.has(idx)) card.classList.add('mastered');
    if (state.starred.has(idx)) card.classList.add('starred');

    const toggle = (e) => {
      if (e.target.closest('.action-btn')) return;
      const isHidden = card.querySelector('.card-body').hidden;
      setExpanded(card, isHidden);
    };

    if (header) {
      header.addEventListener('click', toggle);
      header.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          toggle(e);
        }
      });
    }

    const masterBtn = card.querySelector('.master-btn');
    if (masterBtn) masterBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isMastered = card.classList.toggle('mastered');
      if (isMastered) state.mastered.add(idx);
      else state.mastered.delete(idx);
      localStorage.setItem('interview-mastered', JSON.stringify(Array.from(state.mastered)));
    });

    const starBtn = card.querySelector('.star-btn');
    if (starBtn) starBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isStarred = card.classList.toggle('starred');
      if (isStarred) state.starred.add(idx);
      else state.starred.delete(idx);
      localStorage.setItem('interview-starred', JSON.stringify(Array.from(state.starred)));
    });

    const toggleBtn = card.querySelector('.toggle-btn');
    if (toggleBtn) toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = card.querySelector('.card-body').hidden;
      setExpanded(card, isHidden);
    });
  });

  /**
   * Toolbar actions
   */
  el.expandAllBtn?.addEventListener('click', () => {
    el.cards.forEach(c => setExpanded(c, true));
  });

  el.collapseAllBtn?.addEventListener('click', () => {
    el.cards.forEach(c => setExpanded(c, false));
  });

  el.randomBtn?.addEventListener('click', () => {
    if (el.cards.length > 0) {
      const card = el.cards[Math.floor(Math.random() * el.cards.length)];
      focusCard(card);
    } else if (SEARCH_INDEX.length > 0) {
      const entry = SEARCH_INDEX[Math.floor(Math.random() * SEARCH_INDEX.length)];
      window.location.href = `${BASE}${entry.url}#card-${entry.idx}`;
    }
  });

  function focusCard(card) {
    setExpanded(card, true);
    el.cards.forEach(c => c.classList.remove('search-current'));
    card.classList.add('search-current');
    card.scrollIntoView({ behavior: 'auto', block: 'center' });
    setTimeout(() => card.classList.remove('search-current'), 2200);
  }

  /**
   * Global search (Fuse over the shared index)
   */
  function initSearch() {
    if (window.Fuse && SEARCH_INDEX.length) {
      state.fuse = new Fuse(SEARCH_INDEX, {
        keys: ['title', 'text', 'category'],
        threshold: 0.3,
        ignoreLocation: true,
        minMatchCharLength: 2
      });
    }
  }

  function highlight(text, q) {
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i < 0) return escapeHtml(text);
    return escapeHtml(text.slice(0, i)) +
      '<mark class="hl">' + escapeHtml(text.slice(i, i + q.length)) + '</mark>' +
      escapeHtml(text.slice(i + q.length));
  }

  function snippet(text, q, len) {
    if (!text) return '';
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    let start = 0;
    if (i > 40) start = i - 40;
    let slice = text.slice(start, start + len);
    if (start > 0) slice = '…' + slice;
    if (start + len < text.length) slice = slice + '…';
    return highlight(slice, q);
  }

  function renderResults(q) {
    if (!state.results.length) {
      el.searchResults.innerHTML = '<div class="search-empty">未找到相关内容</div>';
      el.searchResults.hidden = false;
      el.searchStats.textContent = '无匹配';
      return;
    }
    const html = state.results.map((r, i) => {
      const item = r.item;
      const active = i === state.activeResult ? ' active' : '';
      const displayIdx = item.display_idx || ('#' + item.idx);
      return `<a class="search-result-item${active}" data-i="${i}" href="${BASE}${item.url}#card-${item.idx}">
        <div class="result-top"><span class="result-cat">${escapeHtml(item.category)}</span><span class="result-idx">${escapeHtml(displayIdx)}</span></div>
        <div class="result-title">${highlight(item.title, q)}</div>
        <div class="result-snippet">${snippet(item.text, q, 90)}</div>
      </a>`;
    }).join('');
    el.searchResults.innerHTML = html;
    el.searchResults.hidden = false;
    el.searchStats.textContent = `共 ${state.results.length} 条`;

    el.searchResults.querySelectorAll('.search-result-item').forEach(node => {
      node.addEventListener('click', (e) => {
        const i = Number(node.dataset.i);
        const item = state.results[i].item;
        const local = document.getElementById('card-' + item.idx);
        if (local) {
          e.preventDefault();
          closeResults();
          focusCard(local);
        }
      });
    });
  }

  function runSearch() {
    const q = el.searchInput.value.trim();
    state.activeResult = -1;
    if (!q || !state.fuse) {
      closeResults();
      return;
    }
    state.results = state.fuse.search(q).slice(0, 30);
    updateSearchNav();
    renderResults(q);
  }

  function closeResults() {
    state.results = [];
    state.activeResult = -1;
    el.searchResults.hidden = true;
    el.searchResults.innerHTML = '';
    el.searchStats.textContent = '';
    updateSearchNav();
  }

  function updateSearchNav() {
    const has = state.results.length > 0;
    el.searchPrev.disabled = !has;
    el.searchNext.disabled = !has;
  }

  function moveActive(delta) {
    if (!state.results.length) return;
    let i = state.activeResult + delta;
    if (i < 0) i = state.results.length - 1;
    if (i >= state.results.length) i = 0;
    state.activeResult = i;
    const nodes = el.searchResults.querySelectorAll('.search-result-item');
    nodes.forEach((n, ni) => n.classList.toggle('active', ni === i));
    el.searchStats.textContent = `${i + 1} / ${state.results.length}`;
    nodes[i]?.scrollIntoView({ block: 'nearest' });
  }

  function openActive() {
    if (state.activeResult < 0 || !state.results[state.activeResult]) return;
    const item = state.results[state.activeResult].item;
    const local = document.getElementById('card-' + item.idx);
    if (local) {
      closeResults();
      focusCard(local);
    } else {
      window.location.href = `${BASE}${item.url}#card-${item.idx}`;
    }
  }

  /**
   * Code copy buttons
   */
  function setupCodeBlocks() {
    document.querySelectorAll('.code-block').forEach(block => {
      const copyBtn = document.createElement('button');
      copyBtn.className = 'copy-btn';
      copyBtn.textContent = '复制';
      copyBtn.style.position = 'absolute';
      copyBtn.style.right = '10px';
      copyBtn.style.top = '10px';
      block.style.position = 'relative';
      block.appendChild(copyBtn);
      copyBtn.addEventListener('click', () => {
        const code = block.querySelector('code').textContent;
        navigator.clipboard.writeText(code).then(() => {
          copyBtn.textContent = '已复制!';
          setTimeout(() => copyBtn.textContent = '复制', 2000);
        });
      });
    });
  }

  /**
   * Deep-link: #card-N expands and scrolls on load
   */
  function handleAnchor() {
    const m = (location.hash || '').match(/^#card-(\d+)$/);
    if (!m) return;
    const card = document.getElementById('card-' + m[1]);
    if (card) {
      setExpanded(card, true);
      setTimeout(() => focusCard(card), 50);
    }
  }

  // Events
  let searchTimer;
  el.searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 250);
  });

  el.searchInput.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); moveActive(-1); }
    else if (e.key === 'Enter') { e.preventDefault(); openActive(); }
    else if (e.key === 'Escape') { closeResults(); }
  });

  el.searchPrev.addEventListener('click', () => moveActive(-1));
  el.searchNext.addEventListener('click', () => moveActive(1));

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrap')) closeResults();
  });

  // Init
  window.addEventListener('DOMContentLoaded', () => {
    initSearch();
    setupCodeBlocks();
    handleAnchor();
  });
  window.addEventListener('hashchange', handleAnchor);

  el.navLinks.forEach(a => {
    a.addEventListener('click', () => el.sidebar.classList.remove('open'));
  });

  el.menuBtn.addEventListener('click', () => el.sidebar.classList.toggle('open'));
  window.addEventListener('scroll', () => el.backTop.classList.toggle('visible', window.scrollY > 500));
  el.backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'auto' }));

  // Theme
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('interview-theme', theme);
    el.themeBtn.textContent = theme === 'dark' ? '浅色模式' : '深色模式';
  }
  const savedTheme = localStorage.getItem('interview-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  setTheme(savedTheme);
  el.themeBtn.addEventListener('click', () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'));

})();
