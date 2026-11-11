/* Midwest Tropical – lightweight replacement for jQuery + Elementor frontend (~6KB) */
(function () {
  'use strict';
  var d = document, $$ = function (s, c) { return Array.prototype.slice.call((c || d).querySelectorAll(s)); };
  function settings(el) { try { return JSON.parse(el.getAttribute('data-settings') || '{}'); } catch (e) { return {}; } }
  function bp() { var w = innerWidth; return w <= 767 ? 'mobile' : w <= 1024 ? 'tablet' : 'desktop'; }

  /* ---------- header shrink on scroll + back-to-top (from the site's mtx-ux.js) ---------- */
  var root = d.documentElement, header = d.querySelector('header.elementor-location-header'), tick = false, collapsed = false;
  function measureH() { header && root.style.setProperty('--mtx-header-h', header.offsetHeight + 'px'); }
  // Collapsing the top bar makes the sticky header ~60px shorter; the browser then moves the scroll
  // position up by the same amount. With one threshold (72px) that toggled the class back and forth
  // forever ("header shaking"). Separate collapse/expand thresholds, further apart than 60px, stop it.
  function onScroll() {
    if (tick) return; tick = true;
    requestAnimationFrame(function () {
      var y = scrollY || 0;
      if (!collapsed && y > 150) { collapsed = true; root.classList.add('mtx-scrolled'); }
      else if (collapsed && y < 10) { collapsed = false; root.classList.remove('mtx-scrolled'); }
      root.classList.toggle('mtx-scrolled-far', y > 640);
      tick = false;
    });
  }
  addEventListener('scroll', onScroll, { passive: true }); addEventListener('resize', measureH, { passive: true }); measureH(); onScroll();
  var topBtn = d.createElement('button'); topBtn.type = 'button'; topBtn.className = 'mtx-top'; topBtn.setAttribute('aria-label', 'Back to top');
  topBtn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 5l7 7-1.4 1.4L13 8.8V20h-2V8.8l-4.6 4.6L5 12z" fill="currentColor"/></svg>';
  topBtn.addEventListener('click', function () { scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); });
  d.body.appendChild(topBtn);
  $$('a[target="_blank"]:not([rel~="noopener"])').forEach(function (a) { a.rel = (a.rel ? a.rel + ' ' : '') + 'noopener'; });

  /* ---------- current menu item ---------- */
  var here = location.pathname.replace(/\/+$/, '/') ;
  $$('.elementor-nav-menu a[href]').forEach(function (a) {
    var p = a.getAttribute('href');
    if (p === here) { a.classList.add('elementor-item-active'); a.setAttribute('aria-current', 'page'); var li = a.closest('li'); li && li.classList.add('current-menu-item'); }
  });

  /* ---------- nav menu: burger + submenus ---------- */
  $$('.elementor-menu-toggle').forEach(function (t) {
    var w = t.closest('.elementor-widget-nav-menu');
    var dd = t.nextElementSibling && t.nextElementSibling.matches('nav') ? t.nextElementSibling : (w && w.querySelector('nav.elementor-nav-menu--dropdown'));
    function place() {
      // Elementor "stretch" dropdown: full viewport width, directly under the toggle
      if (!dd || !w || !w.classList.contains('elementor-nav-menu--stretch')) return;
      var op = dd.offsetParent || d.body, opr = op.getBoundingClientRect(), tr = t.getBoundingClientRect();
      dd.style.width = d.documentElement.clientWidth + 'px';
      dd.style.left = (-opr.left) + 'px';
      dd.style.top = (tr.bottom - opr.top) + 'px';
    }
    t.addEventListener('click', function () {
      var on = t.classList.toggle('elementor-active');
      t.setAttribute('aria-expanded', on);
      if (dd) { dd.setAttribute('aria-hidden', !on); if (on) place(); }
    });
    addEventListener('resize', place); place();
  });
  $$('.elementor-nav-menu li.menu-item-has-children > a').forEach(function (a) {
    a.classList.add('has-submenu');
    var inDropdown = a.closest('.elementor-nav-menu--dropdown');
    // the site's main menu shows no submenu icon; only the mobile dropdown gets a tap target
    if (inDropdown && !a.querySelector('.sub-arrow')) { var s = d.createElement('span'); s.className = 'sub-arrow'; s.innerHTML = '<svg class="e-font-icon-svg" viewBox="0 0 320 512" width="10" height="10"><path d="M31.3 192h257.3c17.8 0 26.7 21.5 14.1 34.1L174.1 354.8c-7.8 7.8-20.5 7.8-28.3 0L17.2 226.1C4.6 213.5 13.5 192 31.3 192z"/></svg>'; a.appendChild(s); }
    if (inDropdown) {
      a.querySelector('.sub-arrow').addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        a.parentNode.classList.toggle('mt-sub-open'); a.classList.toggle('highlighted');
      });
    }
  });

  /* ---------- sticky sections (Elementor Pro sticky) ---------- */
  $$('[data-settings*="sticky"]').forEach(function (el) {
    var s = settings(el); if (s.sticky !== 'top') return;
    var on = s.sticky_on || ['desktop', 'tablet', 'mobile'], spacer = null, top = 0;
    function measure() { if (!spacer) { var r = el.getBoundingClientRect(); top = r.top + scrollY; } }
    function upd() {
      var active = on.indexOf(bp()) > -1 && scrollY > top + (s.sticky_offset || 0);
      if (active && !spacer) {
        spacer = el.cloneNode(false); spacer.removeAttribute('data-settings'); spacer.classList.add('elementor-sticky__spacer'); spacer.style.visibility = 'hidden'; spacer.style.height = el.offsetHeight + 'px';
        el.parentNode.insertBefore(spacer, el.nextSibling);
        el.classList.add('elementor-sticky', 'elementor-sticky--active', 'elementor-sticky--effects');
        el.style.cssText += ';position:fixed;top:0;left:0;width:100%;z-index:99;margin-top:0';
      } else if (!active && spacer) {
        spacer.remove(); spacer = null;
        el.classList.remove('elementor-sticky--active', 'elementor-sticky--effects');
        el.style.position = el.style.top = el.style.left = el.style.width = el.style.zIndex = el.style.marginTop = '';
      }
    }
    measure(); addEventListener('scroll', upd, { passive: true }); addEventListener('resize', function () { measure(); upd(); }); upd();
  });

  /* ---------- tabs / accordion / toggle ---------- */
  $$('.elementor-widget-tabs, .elementor-widget-accordion, .elementor-widget-toggle').forEach(function (w) {
    var isTabs = w.classList.contains('elementor-widget-tabs');
    var isToggle = w.classList.contains('elementor-widget-toggle');
    $$('.elementor-tab-title', w).forEach(function (t) {
      t.addEventListener('click', function () {
        var n = t.getAttribute('data-tab');
        var open = !t.classList.contains('elementor-active');
        if (isTabs) open = true;
        if (!isToggle) {
          $$('.elementor-tab-title', w).forEach(function (x) { x.classList.remove('elementor-active'); x.setAttribute('aria-selected', 'false'); x.setAttribute('aria-expanded', 'false'); });
          $$('.elementor-tab-content', w).forEach(function (c) { c.classList.remove('elementor-active'); c.style.display = 'none'; c.hidden = true; });
        }
        $$('.elementor-tab-title[data-tab="' + n + '"]', w).forEach(function (x) { x.classList.toggle('elementor-active', open); x.setAttribute('aria-selected', open); x.setAttribute('aria-expanded', open); });
        $$('.elementor-tab-content[data-tab="' + n + '"]', w).forEach(function (c) { c.classList.toggle('elementor-active', open); c.style.display = open ? 'block' : 'none'; c.hidden = !open; });
      });
    });
    var first = w.querySelector('.elementor-tab-title.elementor-active') || (isTabs && w.querySelector('.elementor-tab-title'));
    if (first && isTabs) first.click();
  });

  /* ---------- carousels (slides / image-carousel / testimonials) ---------- */
  $$('.swiper').forEach(function (sw) {
    var wrap = sw.querySelector('.swiper-wrapper'); if (!wrap) return;
    var slides = $$(':scope > .swiper-slide', wrap); if (!slides.length) return;
    var widget = sw.closest('.elementor-widget') || sw, s = settings(widget);
    function perView() { var b = bp(); return +(b === 'mobile' ? (s.slides_to_show_mobile || 1) : b === 'tablet' ? (s.slides_to_show_tablet || s.slides_to_show || 1) : (s.slides_to_show || 1)) || 1; }
    var gap = s.image_spacing_custom && s.image_spacing_custom.size || 0;
    var fade = s.transition === 'fade' || s.effect === 'fade', i = 0, timer, speed = s.transition_speed || s.speed || 500;
    sw.classList.add('swiper-initialized', 'swiper-horizontal');
    wrap.style.transitionProperty = fade ? 'none' : 'transform';
    function layout() {
      var n = perView(), w = sw.clientWidth;
      slides.forEach(function (sl, k) {
        sl.style.width = ((w - gap * (n - 1)) / n) + 'px'; sl.style.marginRight = gap + 'px';
        if (fade) { sl.style.position = k ? 'absolute' : 'relative'; sl.style.top = 0; sl.style.left = 0; sl.style.transition = 'opacity ' + speed + 'ms'; }
      });
      go(i, true);
    }
    function go(k, instant) {
      var n = perView(), max = Math.max(0, slides.length - n);
      i = k > max ? 0 : k < 0 ? max : k;
      slides.forEach(function (sl, j) { var a = j === i; sl.classList.toggle('swiper-slide-active', a); if (fade) { sl.style.opacity = a ? 1 : 0; sl.style.zIndex = a ? 1 : 0; } });
      if (!fade) { wrap.style.transitionDuration = instant ? '0ms' : speed + 'ms'; wrap.style.transform = 'translate3d(' + (-i * (slides[0].offsetWidth + gap)) + 'px,0,0)'; }
      $$('.swiper-pagination-bullet', widget).forEach(function (b, j) { b.classList.toggle('swiper-pagination-bullet-active', j === i); });
      // replay Elementor slide content animation
      var inner = slides[i].querySelector('.swiper-slide-inner'); if (inner && sw.getAttribute('data-animation')) { inner.classList.remove('animated'); void inner.offsetWidth; inner.classList.add('animated', sw.getAttribute('data-animation')); }
    }
    var pag = widget.querySelector('.swiper-pagination');
    if (pag && !pag.children.length && /dots|both/.test(s.navigation || 'both')) {
      slides.forEach(function (_, j) { var b = d.createElement('span'); b.className = 'swiper-pagination-bullet'; b.setAttribute('role', 'button'); b.setAttribute('aria-label', 'Go to slide ' + (j + 1)); b.onclick = function () { go(j); restart(); }; pag.appendChild(b); });
      pag.classList.add('swiper-pagination-bullets', 'swiper-pagination-horizontal');
    }
    var prev = widget.querySelector('.elementor-swiper-button-prev, .swiper-button-prev'), next = widget.querySelector('.elementor-swiper-button-next, .swiper-button-next');
    prev && prev.addEventListener('click', function () { go(i - 1); restart(); });
    next && next.addEventListener('click', function () { go(i + 1); restart(); });
    var x0 = null;
    sw.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    sw.addEventListener('touchend', function (e) { if (x0 === null) return; var dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) { go(i + (dx < 0 ? 1 : -1)); restart(); } x0 = null; });
    function restart() { clearInterval(timer); if (s.autoplay === 'yes' && slides.length > perView()) timer = setInterval(function () { go(i + 1); }, s.autoplay_speed || 5000); }
    if (s.pause_on_hover === 'yes') { sw.addEventListener('mouseenter', function () { clearInterval(timer); }); sw.addEventListener('mouseleave', restart); }
    layout(); restart(); addEventListener('resize', layout);
  });

  /* ---------- posts / portfolio grids: image ratio cropping (Elementor posts handler) ---------- */
  $$('.elementor-posts-container').forEach(function (c) {
    var thumbs = $$('.elementor-post__thumbnail', c);
    // only a real aspect-ratio box (padding-bottom = a % of the width) means "crop images to ratio";
    // a small padding (e.g. 10px spacing on the gallery cards) must not trigger it
    if (!thumbs.length || parseFloat(getComputedStyle(thumbs[0]).paddingBottom) < thumbs[0].offsetWidth * 0.2) return;
    c.classList.add('elementor-has-item-ratio');
    thumbs.forEach(function (t) {
      var img = t.querySelector('img'); if (!img) return;
      function fit() {
        var boxRatio = t.offsetHeight / t.offsetWidth, w = img.naturalWidth || +img.getAttribute('width'), h = img.naturalHeight || +img.getAttribute('height');
        if (w && h) t.classList.toggle('elementor-fit-height', h / w < boxRatio);
      }
      img.complete ? fit() : img.addEventListener('load', fit); fit();
    });
  });
  /* masonry-free portfolio widget: show items (Elementor fades them in with JS) */
  $$('.elementor-portfolio-item, .elementor-portfolio .elementor-post').forEach(function (p) { p.style.opacity = 1; });

  /* ---------- portfolio (gallery) category filter: cards carry mt-tag-<slug> classes (added at build) ---------- */
  function slugify(s) { return s.toLowerCase().trim().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  $$('.elementor-widget-portfolio').forEach(function (w) {
    var items = $$('.elementor-portfolio-item', w), btns = $$('.elementor-portfolio__filter', w);
    items.forEach(function (i) { i.style.opacity = 1; });
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        btns.forEach(function (x) { x.classList.toggle('elementor-active', x === b); });
        var all = b.getAttribute('data-filter') === '__all', cls = 'mt-tag-' + slugify(b.textContent);
        items.forEach(function (i) { i.style.display = all || i.classList.contains(cls) ? '' : 'none'; });
      });
      b.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); b.click(); } });
    });
  });

  /* ---------- WooCommerce product gallery (replaces flexslider): big image + square thumbnail row ---------- */
  $$('.woocommerce-product-gallery').forEach(function (g) {
    var wrap = g.querySelector('.woocommerce-product-gallery__wrapper'); if (!wrap) return;
    var slides = $$('.woocommerce-product-gallery__image', wrap);
    g.style.opacity = 1;
    if (slides.length < 2) return;
    var ol = d.createElement('ol'); ol.className = 'flex-control-nav flex-control-thumbs';
    function show(k) {
      slides.forEach(function (s, j) { s.style.display = j === k ? 'block' : 'none'; s.classList.toggle('flex-active-slide', j === k); });
      $$('img', ol).forEach(function (im, j) { im.classList.toggle('flex-active', j === k); });
    }
    slides.forEach(function (s, i) {
      s.style.width = '100%';
      var li = d.createElement('li'), im = d.createElement('img'), big = s.querySelector('img');
      im.src = s.getAttribute('data-thumb') || (big && big.src) || '';
      im.alt = s.getAttribute('data-thumb-alt') || (big && big.alt) || '';
      im.width = 100; im.height = 100; im.loading = 'lazy';
      im.addEventListener('click', function () { show(i); });
      li.appendChild(im); ol.appendChild(li);
    });
    g.appendChild(ol); show(0);
  });

  /* ---------- video widgets: lite YouTube / Vimeo / hosted ---------- */
  function ytId(u) { var m = /(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/.exec(u || ''); return m && m[1]; }
  $$('.elementor-widget-video').forEach(function (w) {
    var s = settings(w), box = w.querySelector('.elementor-video') || w.querySelector('.elementor-wrapper'); if (!box || box.querySelector('iframe,video')) return;
    var id = s.video_type !== 'vimeo' && s.video_type !== 'hosted' && ytId(s.youtube_url);
    if (id) {
      box.classList.add('mt-yt'); box.style.backgroundImage = 'url(https://i.ytimg.com/vi/' + id + '/hqdefault.jpg)';
      box.innerHTML = '<button class="mt-yt-play" aria-label="Play video"></button>';
      box.addEventListener('click', function () { box.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen style="position:absolute;inset:0;width:100%;height:100%;border:0"></iframe>'; }, { once: true });
    } else if (s.vimeo_url) {
      var v = /vimeo\.com\/(?:video\/)?(\d+)/.exec(s.vimeo_url); if (v) box.innerHTML = '<iframe loading="lazy" src="https://player.vimeo.com/video/' + v[1] + '" allow="autoplay; fullscreen" allowfullscreen style="position:absolute;inset:0;width:100%;height:100%;border:0"></iframe>';
    }
  });
  /* ---------- "TS Video Gallery" tiles (videos page): play in a popup (replaces the plugin's JS) ---------- */
  d.addEventListener('click', function (e) {
    var li = e.target.closest('[data-tsvg-src]'); if (!li) return;
    var src = li.getAttribute('data-tsvg-src'); if (!src) return;
    e.preventDefault();
    var id = ytId(src), m = d.createElement('div');
    m.className = 'mt-modal mt-open mt-video-modal'; m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
    var player = id
      ? '<iframe src="https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="Video"></iframe>'
      : '<video src="' + src.replace(/"/g, '&quot;') + '" controls autoplay playsinline></video>';
    m.innerHTML = '<div class="mt-video-box"><button class="mt-modal-x" aria-label="Close">&times;</button>' + player + '</div>';
    function shut() { m.remove(); d.documentElement.classList.remove('mt-noscroll'); d.removeEventListener('keydown', esc); }
    function esc(ev) { if (ev.key === 'Escape') shut(); }
    m.addEventListener('click', function (ev) { if (ev.target === m || ev.target.closest('.mt-modal-x')) shut(); });
    d.addEventListener('keydown', esc);
    d.body.appendChild(m); d.documentElement.classList.add('mt-noscroll');
  });

  // lazy-activate any YouTube iframes already in markup that were given data-src
  $$('iframe[data-src]').forEach(function (f) { f.src = f.getAttribute('data-src'); });

  /* ---------- popups (Elementor Pro) ---------- */
  var popups = {};
  $$('[data-elementor-type="popup"]').forEach(function (p) {
    var id = p.getAttribute('data-elementor-id'), m = d.createElement('div');
    m.className = 'mt-modal dialog-widget dialog-lightbox-widget elementor-popup-modal'; m.id = 'elementor-popup-modal-' + id; m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
    m.innerHTML = '<div class="dialog-widget-content dialog-lightbox-widget-content mt-modal-box"><a role="button" tabindex="0" aria-label="Close" class="dialog-close-button dialog-lightbox-close-button mt-modal-x">&times;</a><div class="dialog-message dialog-lightbox-message"></div></div>';
    m.querySelector('.dialog-message').appendChild(p); d.body.appendChild(m);
    m.addEventListener('click', function (e) { if (e.target === m || e.target.closest('.mt-modal-x')) close(m); });
    popups[id] = m;
  });
  function close(m) { m.classList.remove('mt-open'); d.documentElement.classList.remove('mt-noscroll'); }
  function open(id) { var m = popups[id] || popups[Object.keys(popups)[0]]; if (m) { m.classList.add('mt-open'); d.documentElement.classList.add('mt-noscroll'); var f = m.querySelector('input:not([type=hidden])'); f && f.focus({ preventScroll: true }); } }
  d.addEventListener('keydown', function (e) { if (e.key === 'Escape') $$('.mt-modal.mt-open').forEach(close); });
  d.addEventListener('click', function (e) {
    var a = e.target.closest('a[href*="elementor-action"]'); if (!a) return;
    var h = decodeURIComponent(a.getAttribute('href'));
    if (/popup:open/.test(h)) {
      e.preventDefault(); var id = null;
      try { id = JSON.parse(atob(/settings=([^&]+)/.exec(h)[1])).id; } catch (x) {}
      open(id);
    } else if (/popup:close/.test(h)) { e.preventDefault(); $$('.mt-modal.mt-open').forEach(close); }
  });

  /* ---------- lightbox for linked images ---------- */
  var lb;
  d.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-elementor-open-lightbox="yes"], a[data-elementor-open-lightbox="default"], .gallery-item a, a.mt-lightbox');
    if (!a || !/\.(jpe?g|png|webp|avif|gif)(\?|$)/i.test(a.getAttribute('href') || '')) return;
    e.preventDefault();
    if (!lb) { lb = d.createElement('div'); lb.className = 'mt-lightbox-box'; lb.innerHTML = '<img alt=""><button aria-label="Close">&times;</button>'; lb.onclick = function () { lb.classList.remove('mt-open'); }; d.body.appendChild(lb); }
    var im = lb.querySelector('img'); im.src = a.href; im.alt = (a.querySelector('img') || {}).alt || ''; lb.classList.add('mt-open');
  });

  /* ---------- Elementor forms -> /form-handler.php ---------- */
  $$('form.elementor-form').forEach(function (f) {
    // multi-step forms
    var steps = $$('.e-form__step', f), cur = 0;
    function show(k) { steps.forEach(function (st, j) { st.classList.toggle('elementor-hidden', j !== k); }); cur = k; }
    if (steps.length) {
      show(0);
      f.addEventListener('click', function (e) {
        var b = e.target.closest('[id^="form-field-"][class*="step-"], .e-form__buttons__wrapper__button-next, .e-form__buttons__wrapper__button-previous'); if (!b) return;
        e.preventDefault();
        if (b.className.indexOf('next') > -1) { var ok = $$('input,select,textarea', steps[cur]).every(function (x) { return x.reportValidity(); }); if (ok) show(Math.min(cur + 1, steps.length - 1)); }
        else show(Math.max(cur - 1, 0));
      });
    }
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      if (f.querySelector('[name="form_fields[mt_hp]"]') && f.querySelector('[name="form_fields[mt_hp]"]').value) return;
      var btn = f.querySelector('[type=submit]'); btn && (btn.disabled = true, btn.classList.add('elementor-form-waiting'));
      $$('.elementor-message', f).forEach(function (m) { m.remove(); });
      var fd = new FormData(f); fd.append('page_url', location.href); fd.append('page_title', d.title);
      fetch('/form-handler.php', { method: 'POST', body: fd, headers: { 'X-Requested-With': 'fetch' } })
        .then(function (r) { return r.json(); })
        .then(function (j) { msg(j && j.success, j && j.message); if (j && j.success) { f.reset(); if (j.redirect) location.href = j.redirect; } })
        .catch(function () { msg(false); })
        .then(function () { btn && (btn.disabled = false, btn.classList.remove('elementor-form-waiting')); });
      function msg(ok, text) {
        var m = d.createElement('div'); m.className = 'elementor-message ' + (ok ? 'elementor-message-success' : 'elementor-message-danger'); m.setAttribute('role', 'alert');
        m.textContent = text || (ok ? 'Your submission was successful.' : 'Your submission failed because of an error.'); f.appendChild(m);
      }
    });
  });

  /* ---------- search form -> site search on Google ---------- */
  $$('form.elementor-search-form, form.search-form').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      e.preventDefault(); var q = (f.querySelector('[name=s]') || {}).value || '';
      location.href = 'https://www.google.com/search?q=' + encodeURIComponent('site:midwest-tropical.com ' + q);
    });
    var tg = f.querySelector('.elementor-search-form__toggle'); tg && tg.addEventListener('click', function () { f.classList.toggle('elementor-search-form--full-screen'); });
  });

  /* ---------- reveal animations (Elementor entrance animations) ---------- */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (en) { en.forEach(function (x) { if (x.isIntersecting) { var s = settings(x.target), a = s._animation || s.animation; if (a && a !== 'none') x.target.classList.add('animated', a); io.unobserve(x.target); } }); }, { rootMargin: '0px 0px -10% 0px' });
    $$('[data-settings*="animation"]').forEach(function (el) { if (!el.closest('.swiper')) io.observe(el); });
  }

  /* ---------- analytics: loaded after first interaction (keeps page fast) ---------- */
  var GA = 'G-R1TTQPKSTK', GTMS = ['GTM-N3GGZ2J', 'GTM-M6VHCMP'], loaded = false;
  function analytics() {
    if (loaded) return; loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); }; gtag('js', new Date()); gtag('config', GA);
    var s = d.createElement('script'); s.async = true; s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA; d.head.appendChild(s);
    GTMS.forEach(function (id) { dataLayer.push({ 'gtm.start': Date.now(), event: 'gtm.js' }); var g = d.createElement('script'); g.async = true; g.src = 'https://www.googletagmanager.com/gtm.js?id=' + id; d.head.appendChild(g); });
  }
  ['scroll', 'mousemove', 'touchstart', 'keydown'].forEach(function (ev) { addEventListener(ev, analytics, { once: true, passive: true }); });
  setTimeout(analytics, 6000);
})();
