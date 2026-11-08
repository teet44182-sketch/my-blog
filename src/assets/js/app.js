(() => {
  'use strict';
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.documentElement.dataset.theme = document.documentElement.dataset.theme || 'light';
  document.querySelectorAll('[data-year]').forEach((el) => { el.textContent = String(new Date().getFullYear()); });

  const themeToggle = document.querySelector('[data-theme-toggle]');
  let themeTimer = 0;
  const syncThemeButton = () => {
    if (!themeToggle) return;
    const isDark = document.documentElement.dataset.theme === 'dark';
    themeToggle.setAttribute('aria-pressed', String(isDark));
    themeToggle.setAttribute('aria-label', isDark ? 'เปลี่ยนเป็นธีมสว่าง' : 'เปลี่ยนเป็นธีมมืด');
  };
  themeToggle?.addEventListener('click', () => {
    const root = document.documentElement;
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    if (!prefersReduced) {
      root.classList.add('theme-transition');
      void root.offsetWidth;
      window.clearTimeout(themeTimer);
      themeTimer = window.setTimeout(() => root.classList.remove('theme-transition'), 2500);
    }
    root.dataset.theme = next;
    try { localStorage.setItem('profile-theme', next); } catch (_) {}
    syncThemeButton();
  });
  syncThemeButton();

  const navToggle = document.querySelector('[data-nav-toggle]');
  const siteNav = document.querySelector('[data-site-nav]');
  navToggle?.addEventListener('click', () => {
    const expanded = navToggle.getAttribute('aria-expanded') === 'true';
    navToggle.setAttribute('aria-expanded', String(!expanded));
    siteNav?.classList.toggle('is-open', !expanded);
  });
  siteNav?.addEventListener('click', (event) => {
    if (event.target instanceof HTMLAnchorElement) siteNav.classList.remove('is-open');
  });

  let progress = document.querySelector('#progress-bar');
  if (!progress) {
    progress = document.createElement('div');
    progress.id = 'progress-bar';
    progress.className = 'progress-bar';
    progress.setAttribute('aria-hidden', 'true');
    (document.querySelector('.site-header') || document.body).append(progress);
  }
  let progressFrame = 0;
  const updateProgress = () => {
    progressFrame = 0;
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    progress.style.transform = `scaleX(${max > 0 ? doc.scrollTop / max : 0})`;
  };
  const requestProgress = () => {
    if (!progressFrame) progressFrame = window.requestAnimationFrame(updateProgress);
  };
  document.addEventListener('scroll', requestProgress, { passive: true });
  window.addEventListener('resize', requestProgress);

  const siteBase = window.__SITE_BASE__ || '';
  const stripBase = (value) => {
    let path = value || '/';
    if (!path.startsWith('/')) path = `/${path}`;
    if (siteBase && path === siteBase) return '/';
    if (siteBase && path.startsWith(`${siteBase}/`)) return path.slice(siteBase.length) || '/';
    return path;
  };
  const normalizePath = (pathname) => {
    let path = pathname || '/';
    if (path.endsWith('/index.html')) path = path.slice(0, -10);
    if (!path.startsWith('/')) path = `/${path}`;
    return stripBase(path);
  };
  const positionNavIndicator = () => {
    const nav = document.querySelector('.site-nav');
    if (!nav) return;
    const active = nav.querySelector('.nav-link[aria-current="page"]');
    if (!active || !active.offsetParent) {
      nav.style.setProperty('--indicator-left', '0px');
      nav.style.setProperty('--indicator-width', '0px');
      return;
    }
    nav.style.setProperty('--indicator-left', `${active.offsetLeft}px`);
    nav.style.setProperty('--indicator-width', `${active.offsetWidth}px`);
  };

  const positionLangSlider = () => {
    const sw = document.querySelector('.lang-switch');
    if (!sw) return;
    const active = sw.querySelector('.lang-option.is-active');
    if (!active || !active.offsetParent) {
      sw.style.setProperty('--lang-left', '.15rem');
      sw.style.setProperty('--lang-width', '2.9rem');
      return;
    }
    sw.style.setProperty('--lang-left', `${active.offsetLeft}px`);
    sw.style.setProperty('--lang-width', `${active.offsetWidth}px`);
  };

  document.querySelectorAll('.lang-switch a.lang-option').forEach((link) => {
    link.addEventListener('click', () => {
      try { sessionStorage.setItem('lang-switching', '1'); } catch (_) {}
    });
  });

  const updateNavCurrent = (pathname) => {
    const path = normalizePath(pathname);
    document.querySelectorAll('.site-nav .nav-link[href]').forEach((link) => {
      const href = stripBase(link.getAttribute('href') || '');
      let current = false;
      if (href === '/') current = path === '/';
      else if (href === '/writeups/') current = path.startsWith('/writeups/') || path.startsWith('/posts/');
      else if (href === '/history/') current = path.startsWith('/history/');
      else if (href === '/about/') current = path.startsWith('/about/');
      if (current) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    positionNavIndicator();
  };

  const initArchive = (scope) => {
    const search = scope.querySelector('#archive-search');
    const list = scope.querySelector('[data-archive-list]');
    if (!search || !list) return;

    const entries = Array.from(list.querySelectorAll('.post-item')).map((item) => ({
      item,
      haystack: [
        item.textContent || '',
        item.dataset.title || '',
        item.dataset.tags || '',
        item.dataset.category || '',
        item.dataset.difficulty || '',
        item.dataset.platform || ''
      ].join(' ').toLowerCase()
    }));
    const count = scope.querySelector('#result-count');
    const empty = scope.querySelector('#empty-state');
    let filterFrame = 0;

    const apply = () => {
      filterFrame = 0;
      const query = search.value.trim().toLowerCase();
      let visible = 0;
      entries.forEach(({ item, haystack }) => {
        const show = !query || haystack.includes(query);
        item.hidden = !show;
        if (show) visible += 1;
      });
      const isTh = document.documentElement.lang.startsWith('th');
      if (count) count.textContent = isTh ? `${visible} บทความที่พบ` : `${visible} writeup${visible === 1 ? '' : 's'} shown`;
      empty?.classList.toggle('is-visible', visible === 0);
    };
    const scheduleApply = () => {
      if (!filterFrame) filterFrame = window.requestAnimationFrame(apply);
    };

    search.addEventListener('input', scheduleApply);

    try {
      const params = new URLSearchParams(window.location.search);
      const tagParam = params.get('tag');
      if (tagParam) search.value = tagParam;
    } catch (_) {}
    apply();
  };

  document.addEventListener('keydown', (event) => {
    const search = document.querySelector('#archive-search');
    if (!search) return;
    const target = event.target;
    const isTyping = target instanceof HTMLElement && (
      target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable
    );
    if (event.key === '/' && !isTyping) {
      event.preventDefault();
      search.focus();
    }
    if (event.key === 'Escape' && document.activeElement === search) {
      search.value = '';
      search.blur();
      search.dispatchEvent(new Event('input', { bubbles: true }));
    }
  });

  const initMain = (scope) => { initArchive(scope); requestProgress(); };
  const isNonHtmlPath = (pathname) => /\.(xml|txt|json|pdf|zip|png|jpe?g|gif|svg|ico|webp|css|js)$/i.test(pathname);
  const internalHtmlUrl = (anchor) => {
    if (anchor.closest('.lang-switch')) return null;
    if (anchor.target || anchor.hasAttribute('download')) return null;
    let url;
    try { url = new URL(anchor.href, window.location.href); } catch (_) { return null; }
    if (url.origin !== window.location.origin) return null;
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    if (isNonHtmlPath(url.pathname)) return null;
    if (url.href === window.location.href) return null;
    if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) return null;
    return url;
  };

  if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';

  const fetchHtml = async (url) => {
    const response = await fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'text/html,application/xhtml+xml' }
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('text/html') && !contentType.includes('application/xhtml+xml')) throw new Error('not html');
    return response.text();
  };

  let navigating = false;
  const swapTo = async (href, { push = true } = {}) => {
    if (navigating) return;
    navigating = true;
    const url = new URL(href, window.location.href);
    const currentMain = document.querySelector('main');
    try {
      const html = await fetchHtml(url.href);
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const newMain = doc.querySelector('main');
      if (!newMain) throw new Error('missing main');

      const imported = document.importNode(newMain, true);
      if (currentMain) currentMain.replaceWith(imported);
      else document.body.append(imported);

      if (doc.title) document.title = doc.title;
      const description = doc.querySelector('meta[name="description"]')?.getAttribute('content');
      if (description) {
        const meta = document.querySelector('meta[name="description"]');
        if (meta) meta.setAttribute('content', description);
      }
      if (push) history.pushState({}, '', url.href);
      updateNavCurrent(url.pathname);

      if (url.hash) {
        const target = document.querySelector(url.hash);
        if (target) target.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'start' });
        else window.scrollTo(0, 0);
      } else {
        window.scrollTo(0, 0);
      }
      initMain(imported);
    } catch (_) {
      window.location.href = url.href;
    } finally {
      navigating = false;
    }
  };

  document.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const anchor = event.target instanceof Element ? event.target.closest('a[href]') : null;
    if (!anchor) return;
    const url = internalHtmlUrl(anchor);
    if (!url) return;
    event.preventDefault();
    swapTo(url.href);
  });

  window.addEventListener('popstate', () => { swapTo(window.location.href, { push: false }); });

  updateNavCurrent(window.location.pathname);
  positionLangSlider();
  window.addEventListener('load', () => { positionNavIndicator(); positionLangSlider(); });
  window.addEventListener('resize', () => window.requestAnimationFrame(() => { positionNavIndicator(); positionLangSlider(); }));
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { positionNavIndicator(); positionLangSlider(); });
  initMain(document);
})();
