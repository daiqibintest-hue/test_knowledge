/**
 * Interview Q&A Interaction Logic
 */
(function () {
  'use strict';

  // State
  const state = {
    matchCards: [],
    matchIndex: -1,
    isSidebarOpen: false,
    fuse: null,
    mastered: new Set(JSON.parse(localStorage.getItem('interview-mastered') || '[]')),
    starred: new Set(JSON.parse(localStorage.getItem('interview-starred') || '[]'))
  };

  // Elements
  const el = {
    cards: document.querySelectorAll('.card'),
    searchInput: document.getElementById('search'),
    searchStats: document.getElementById('searchStats'),
    searchPrev: document.getElementById('searchPrev'),
    searchNext: document.getElementById('searchNext'),
    noResults: document.getElementById('noResults'),
    navLinks: document.querySelectorAll('.nav-list a'),
    sections: document.querySelectorAll('.part-section'),
    backTop: document.getElementById('backTop'),
    sidebar: document.getElementById('sidebar'),
    menuBtn: document.getElementById('menuBtn'),
    themeBtn: document.getElementById('themeBtn'),
    expandAllBtn: document.getElementById('expandAll'),
    collapseAllBtn: document.getElementById('collapseAll'),
    randomBtn: document.getElementById('randomBtn')
  };

  /**
   * Initialize Fuse.js
   */
  function initSearch() {
    const list = Array.from(el.cards).map(card => ({
      id: card.dataset.idx,
      title: card.querySelector('.card-title').textContent,
      content: card.querySelector('.answer-content').textContent,
      searchData: card.dataset.search || '',
      el: card
    }));

    const options = {
      keys: ['title', 'content', 'searchData'],
      threshold: 0.3,
      ignoreLocation: true
    };

    if (window.Fuse) {
      state.fuse = new Fuse(list, options);
    }
  }

  /**
   * Toggle card expansion
   */
  function setExpanded(card, open) {
    const body = card.querySelector('.card-body');
    const header = card.querySelector('.card-header');
    const btn = card.querySelector('.toggle-btn');
    if (!body) return;

    if (open) {
      body.hidden = false;
      card.classList.add('expanded');
      header.setAttribute('aria-expanded', 'true');
      if (btn) btn.textContent = '收起';
    } else {
      body.hidden = true;
      card.classList.remove('expanded');
      header.setAttribute('aria-expanded', 'false');
      if (btn) btn.textContent = '展开';
    }
  }

  /**
   * Setup Card Event Listeners
   */
  el.cards.forEach(card => {
    const header = card.querySelector('.card-header');
    const idx = card.dataset.idx;

    // Apply initial state
    if (state.mastered.has(idx)) card.classList.add('mastered');
    if (state.starred.has(idx)) card.classList.add('starred');
    
    const toggle = (e) => {
      // If clicked on action buttons, don't toggle expansion
      if (e.target.closest('.action-btn')) return;
      const isHidden = card.querySelector('.card-body').hidden;
      setExpanded(card, isHidden);
    };

    header.addEventListener('click', toggle);
    header.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggle(e);
      }
    });

    // Action Buttons
    card.querySelector('.master-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      const isMastered = card.classList.toggle('mastered');
      if (isMastered) state.mastered.add(idx);
      else state.mastered.delete(idx);
      localStorage.setItem('interview-mastered', JSON.stringify(Array.from(state.mastered)));
    });

    card.querySelector('.star-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      const isStarred = card.classList.toggle('starred');
      if (isStarred) state.starred.add(idx);
      else state.starred.delete(idx);
      localStorage.setItem('interview-starred', JSON.stringify(Array.from(state.starred)));
    });

    // Toggle Button
    card.querySelector('.toggle-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = card.querySelector('.card-body').hidden;
      setExpanded(card, isHidden);
    });
  });

  /**
   * Toolbar Actions
   */
  el.expandAllBtn?.addEventListener('click', () => {
    el.cards.forEach(c => {
      if (!c.classList.contains('hidden-by-search')) setExpanded(c, true);
    });
  });

  el.collapseAllBtn?.addEventListener('click', () => {
    el.cards.forEach(c => setExpanded(c, false));
  });

  el.randomBtn?.addEventListener('click', () => {
    const visibleCards = Array.from(el.cards).filter(c => !c.classList.contains('hidden-by-search'));
    if (visibleCards.length > 0) {
      const randomCard = visibleCards[Math.floor(Math.random() * visibleCards.length)];
      setExpanded(randomCard, true);
      randomCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      randomCard.classList.add('search-current');
      setTimeout(() => randomCard.classList.remove('search-current'), 2000);
    }
  });

  /**
   * Search Logic
   */
  function highlightText(node, q) {
    if (!q) return;
    if (node.nodeType === 3) {
      const text = node.textContent;
      const idx = text.toLowerCase().indexOf(q.toLowerCase());
      if (idx >= 0) {
        const span = document.createElement('span');
        const before = text.slice(0, idx);
        const match = text.slice(idx, idx + q.length);
        const after = text.slice(idx + q.length);
        span.innerHTML = `${escapeHtml(before)}<mark class="hl">${escapeHtml(match)}</mark>${escapeHtml(after)}`;
        node.parentNode.replaceChild(span, node);
      }
    } else if (node.nodeType === 1 && !['SCRIPT', 'STYLE', 'MARK', 'BUTTON'].includes(node.tagName)) {
      Array.from(node.childNodes).forEach(child => highlightText(child, q));
    }
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function runSearch(jumpToFirst = true) {
    const q = el.searchInput.value.trim();
    state.matchCards = [];
    state.matchIndex = -1;

    if (!q) {
      el.cards.forEach(card => {
        card.classList.remove('hidden-by-search');
        resetHighlights(card);
      });
      updateSectionVisibility();
      el.searchStats.textContent = '';
      updateSearchNav();
      el.noResults.classList.remove('show');
      return;
    }

    if (state.fuse) {
      const results = state.fuse.search(q);
      const matchIds = new Set(results.map(r => r.item.id));
      
      el.cards.forEach(card => {
        const isMatch = matchIds.has(card.dataset.idx);
        card.classList.toggle('hidden-by-search', !isMatch);
        resetHighlights(card);
        if (isMatch) {
          state.matchCards.push(card);
          highlightCard(card, q);
          setExpanded(card, true);
        }
      });
    } else {
      // Fallback to simple search
      el.cards.forEach(card => {
        const text = (card.getAttribute('data-search') || '') + ' ' + 
                     card.querySelector('.card-title').textContent + ' ' + 
                     card.querySelector('.answer-content').textContent;
        const isMatch = text.toLowerCase().includes(q.toLowerCase());
        card.classList.toggle('hidden-by-search', !isMatch);
        resetHighlights(card);
        if (isMatch) {
          state.matchCards.push(card);
          highlightCard(card, q);
          setExpanded(card, true);
        }
      });
    }

    updateSectionVisibility();
    el.noResults.classList.toggle('show', state.matchCards.length === 0);

    if (state.matchCards.length === 0) {
      el.searchStats.textContent = '无匹配';
    } else if (jumpToFirst) {
      goToMatch(0);
    } else {
      el.searchStats.textContent = `共 ${state.matchCards.length} 条`;
    }
    updateSearchNav();
  }

  function resetHighlights(card) {
    const titleEl = card.querySelector('.card-title');
    const contentEl = card.querySelector('.answer-content');
    [titleEl, contentEl].forEach(element => {
      if (!element) return;
      if (!element.dataset.originalHtml) element.dataset.originalHtml = element.innerHTML;
      element.innerHTML = element.dataset.originalHtml;
    });
  }

  function highlightCard(card, q) {
    const titleEl = card.querySelector('.card-title');
    const contentEl = card.querySelector('.answer-content');
    [titleEl, contentEl].forEach(element => {
      if (element) highlightText(element, q);
    });
  }

  function updateSectionVisibility() {
    el.sections.forEach(sec => {
      const hasVisibleCards = sec.querySelector('.card:not(.hidden-by-search)');
      sec.style.display = hasVisibleCards ? '' : 'none';
    });
  }

  function updateSearchNav() {
    const hasMatches = state.matchCards.length > 0;
    el.searchPrev.disabled = !hasMatches;
    el.searchNext.disabled = !hasMatches;
  }

  function goToMatch(index) {
    if (!state.matchCards.length) return;
    if (index < 0) index = state.matchCards.length - 1;
    if (index >= state.matchCards.length) index = 0;
    
    state.matchIndex = index;
    el.cards.forEach(c => c.classList.remove('search-current'));
    
    const card = state.matchCards[state.matchIndex];
    card.classList.add('search-current');
    setExpanded(card, true);
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    
    el.searchStats.textContent = `${state.matchIndex + 1} / ${state.matchCards.length}`;
    updateSearchNav();
  }

  /**
   * Code Blocks & Copy
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

  // Events
  let searchTimer;
  el.searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(true), 300);
  });

  el.searchInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) goToMatch(state.matchIndex - 1);
      else goToMatch(state.matchIndex + 1);
    }
  });

  el.searchPrev.addEventListener('click', () => goToMatch(state.matchIndex - 1));
  el.searchNext.addEventListener('click', () => goToMatch(state.matchIndex + 1));

  // Init
  window.addEventListener('DOMContentLoaded', () => {
    initSearch();
    setupCodeBlocks();
  });

  // Navigation Observer
  const navObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        el.navLinks.forEach(a => {
          a.classList.toggle('active', a.getAttribute('href') === `#${id}`);
        });
      }
    });
  }, { rootMargin: '-30% 0px -60% 0px' });
  el.sections.forEach(s => navObserver.observe(s));

  el.navLinks.forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      const id = a.getAttribute('href').slice(1);
      const target = document.getElementById(id);
      if (target) {
        el.sidebar.classList.remove('open');
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        history.replaceState(null, '', `#${id}`);
      }
    });
  });

  el.menuBtn.addEventListener('click', () => el.sidebar.classList.toggle('open'));
  window.addEventListener('scroll', () => el.backTop.classList.toggle('visible', window.scrollY > 500));
  el.backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

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
