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
    // only this widget's own titles/panes: a tabs widget placed inside another tab (gallery: "Waterfall
    // Water Walls" > "Glass / Acrylic / Mesh ...") must not be opened or closed by the outer one
    function own(sel) { return $$(sel, w).filter(function (x) { return x.closest('.elementor-widget-tabs, .elementor-widget-accordion, .elementor-widget-toggle') === w; }); }
    own('.elementor-tab-title').forEach(function (t) {
      t.addEventListener('click', function () {
        var n = t.getAttribute('data-tab');
        var open = !t.classList.contains('elementor-active');
        if (isTabs) open = true;
        if (!isToggle) {
          own('.elementor-tab-title').forEach(function (x) { x.classList.remove('elementor-active'); x.setAttribute('aria-selected', 'false'); x.setAttribute('aria-expanded', 'false'); });
          own('.elementor-tab-content').forEach(function (c) { c.classList.remove('elementor-active'); c.style.display = 'none'; c.hidden = true; });
        }
        own('.elementor-tab-title[data-tab="' + n + '"]').forEach(function (x) { x.classList.toggle('elementor-active', open); x.setAttribute('aria-selected', open); x.setAttribute('aria-expanded', open); });
        own('.elementor-tab-content[data-tab="' + n + '"]').forEach(function (c) { c.classList.toggle('elementor-active', open); c.style.display = open ? 'block' : 'none'; c.hidden = !open; });
      });
    });
    var first = own('.elementor-tab-title.elementor-active')[0] || (isTabs && own('.elementor-tab-title')[0]);
    if (first && isTabs) first.click();
  });

  /* ---------- carousels (slides / image-carousel / testimonials) ---------- */
  $$('.mtslider').forEach(function (sw) {
    var wrap = sw.querySelector('.mtslider-wrapper'); if (!wrap) return;
    var slides = $$(':scope > .mtslider-slide', wrap); if (!slides.length) return;
    var widget = sw.closest('.elementor-widget') || sw, s = settings(widget);
    function perView() { var b = bp(); return +(b === 'mobile' ? (s.slides_to_show_mobile || 1) : b === 'tablet' ? (s.slides_to_show_tablet || s.slides_to_show || 1) : (s.slides_to_show || 1)) || 1; }
    var gap = s.image_spacing_custom && s.image_spacing_custom.size || 0;
    var fade = s.transition === 'fade' || s.effect === 'fade', i = 0, timer, speed = s.transition_speed || s.speed || 500;
    sw.classList.add('mtslider-initialized', 'mtslider-horizontal');
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
      slides.forEach(function (sl, j) { var a = j === i; sl.classList.toggle('mtslider-slide-active', a); if (fade) { sl.style.opacity = a ? 1 : 0; sl.style.zIndex = a ? 1 : 0; } });
      if (!fade) { wrap.style.transitionDuration = instant ? '0ms' : speed + 'ms'; wrap.style.transform = 'translate3d(' + (-i * (slides[0].offsetWidth + gap)) + 'px,0,0)'; }
      $$('.mtslider-pagination-bullet', widget).forEach(function (b, j) { b.classList.toggle('mtslider-pagination-bullet-active', j === i); });
      // replay Elementor slide content animation
      var inner = slides[i].querySelector('.mtslider-slide-inner'); if (inner && sw.getAttribute('data-animation')) { inner.classList.remove('animated'); void inner.offsetWidth; inner.classList.add('animated', sw.getAttribute('data-animation')); }
    }
    var pag = widget.querySelector('.mtslider-pagination');
    if (pag && !pag.children.length && /dots|both/.test(s.navigation || 'both')) {
      slides.forEach(function (_, j) { var b = d.createElement('span'); b.className = 'mtslider-pagination-bullet'; b.setAttribute('role', 'button'); b.setAttribute('aria-label', 'Go to slide ' + (j + 1)); b.onclick = function () { go(j); restart(); }; pag.appendChild(b); });
      pag.classList.add('mtslider-pagination-bullets', 'mtslider-pagination-horizontal');
    }
    var prev = widget.querySelector('.elementor-mtslider-button-prev, .mtslider-button-prev'), next = widget.querySelector('.elementor-mtslider-button-next, .mtslider-button-next');
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
  function initGrid(c) {
    var thumbs = $$('.elementor-post__thumbnail', c);
    if (!thumbs.length) return;
    // grid inside a closed tab / accordion has no width yet: decide once it becomes visible,
    // otherwise "10px < 0" below would wrongly switch the cards to ratio boxes (squashed images)
    if (!thumbs[0].offsetWidth) {
      if (window.ResizeObserver) { var ro = new ResizeObserver(function () { if (thumbs[0].offsetWidth) { ro.disconnect(); initGrid(c); } }); ro.observe(c); }
      return;
    }
    // only a real aspect-ratio box (padding-bottom = a % of the width) means "crop images to ratio";
    // a small padding (e.g. 10px spacing on the gallery cards) must not trigger it
    if (parseFloat(getComputedStyle(thumbs[0]).paddingBottom) < thumbs[0].offsetWidth * 0.2) return;
    c.classList.add('elementor-has-item-ratio');
    thumbs.forEach(function (t) {
      var img = t.querySelector('img'); if (!img) return;
      function fit() {
        var boxRatio = t.offsetHeight / t.offsetWidth, w = img.naturalWidth || +img.getAttribute('width'), h = img.naturalHeight || +img.getAttribute('height');
        if (w && h) t.classList.toggle('elementor-fit-height', h / w < boxRatio);
      }
      img.complete ? fit() : img.addEventListener('load', fit); fit();
    });
  }
  $$('.elementor-posts-container').forEach(initGrid);
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

  /* ---------- shop product gallery (replaces flexslider): big image + square thumbnail row ---------- */
  $$('.mtshop-product-gallery').forEach(function (g) {
    var wrap = g.querySelector('.mtshop-product-gallery__wrapper'); if (!wrap) return;
    var slides = $$('.mtshop-product-gallery__image', wrap);
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
      var labels = {};
      $$('[name^="form_fields["]', f).forEach(function (el) {
        var k = el.name.replace(/^form_fields\[|\]$|\]\[\]$/g, ''), lab = el.id && f.querySelector('label[for="' + el.id + '"]');
        labels[k] = (lab && lab.textContent.trim()) || el.placeholder || '';
      });
      fd.append('field_labels', JSON.stringify(labels));
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

  /* ---------- site search (own index, no plugin): overlay with image cards like the live site ---------- */
  var SITE_BASE = (d.currentScript && d.currentScript.src || '/assets/js/main.js').replace(/assets\/js\/main\.js.*$/, '');
  var MEDIA_BASE = /github\.io$/.test(location.hostname) ? 'https://www.midwest-tropical.com' : '';
  var sIndex = null, sLoading = null, sBox = null, sState = { q: '', sort: 'rel', shown: 0, res: [] };
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function loadIndex() {
    if (sIndex) return Promise.resolve(sIndex);
    return sLoading || (sLoading = fetch(SITE_BASE + 'assets/search.json').then(function (r) { return r.json(); }).then(function (rows) {
      sIndex = rows.map(function (r) { return { u: r[0], t: r[1], i: r[2], d: r[3], lt: r[1].toLowerCase(), lx: r[4].toLowerCase() }; });
      return sIndex;
    }));
  }
  function words(q) { return q.toLowerCase().replace(/[^\w\s'-]+/g, ' ').split(/\s+/).filter(Boolean); }
  function runSearch() {
    var ws = words(sState.q), res = [];
    if (ws.length) sIndex.forEach(function (e) {
      var score = 0;
      for (var k = 0; k < ws.length; k++) {
        var w = ws[k], inT = e.lt.indexOf(w), inX = e.lx.indexOf(w);
        if (inT < 0 && inX < 0) return;
        if (inT >= 0) score += 10 + (inT === 0 || /\W/.test(e.lt.charAt(inT - 1)) ? 5 : 0);
        if (inX >= 0) score += 1 + Math.min(4, e.lx.split(w).length - 1);
      }
      var ph = ws.join(' '), at = e.lt.indexOf(ph);
      if (ws.length > 1 && at >= 0) score += 20;          // whole phrase in the title
      if (at === 0) score += 10;                           // title starts with it
      score -= e.lt.length / 200;                          // shorter (more specific) titles first on ties
      res.push({ e: e, s: score });
    });
    res.sort(sState.sort === 'new' ? function (a, b) { return a.e.d < b.e.d ? 1 : a.e.d > b.e.d ? -1 : 0; }
      : sState.sort === 'old' ? function (a, b) { return a.e.d > b.e.d ? 1 : a.e.d < b.e.d ? -1 : 0; }
      : function (a, b) { return b.s - a.s; });
    sState.res = res; sState.shown = 0;
    var grid = sBox.querySelector('.mt-search-grid'); grid.innerHTML = '';
    sBox.querySelector('.mt-search-count').textContent = ws.length ? (res.length ? 'Found ' + res.length + ' result' + (res.length === 1 ? '' : 's') : 'No results found') : '';
    sBox.querySelector('.mt-search-sortwrap').hidden = !res.length;
    more();
  }
  function hl(title) {
    var ws = words(sState.q).filter(function (w) { return w.length > 1; }).map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
    var t = esc(title);
    return ws.length ? t.replace(new RegExp('(' + ws.join('|') + ')', 'gi'), '<mark>$1</mark>') : t;
  }
  function more() {
    var grid = sBox.querySelector('.mt-search-grid'), end = Math.min(sState.res.length, sState.shown + 30), html = '';
    for (var k = sState.shown; k < end; k++) {
      var e = sState.res[k].e, href = SITE_BASE + e.u.replace(/^\//, '');
      var img = e.i ? '<img loading="lazy" decoding="async" alt="" src="' + esc((/^\//.test(e.i) ? MEDIA_BASE : '') + e.i) + '">' : '<span class="mt-search-noimg" aria-hidden="true"></span>';
      html += '<a class="mt-search-card" href="' + esc(href) + '"><span class="mt-search-thumb">' + img + '</span><span class="mt-search-title">' + hl(e.t) + '</span></a>';
    }
    grid.insertAdjacentHTML('beforeend', html); sState.shown = end;
  }
  function buildBox() {
    sBox = d.createElement('div'); sBox.className = 'mt-search'; sBox.hidden = true;
    sBox.setAttribute('role', 'dialog'); sBox.setAttribute('aria-modal', 'true'); sBox.setAttribute('aria-label', 'Search results');
    sBox.innerHTML = '<div class="mt-search-panel"><form class="mt-search-bar" role="search"><svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M15.5 14h-.8l-.3-.3A6.5 6.5 0 1 0 9.5 16a6.5 6.5 0 0 0 4.2-1.6l.3.3v.8l5 5 1.5-1.5-5-5zm-6 0A4.5 4.5 0 1 1 14 9.5 4.5 4.5 0 0 1 9.5 14z"/></svg>' +
      '<input type="search" name="s" placeholder="Search..." aria-label="Search" autocomplete="off"><button type="button" class="mt-search-clear">Clear</button>' +
      '<button type="button" class="mt-search-close" aria-label="Close search">&times;</button></form>' +
      '<div class="mt-search-head"><h2 class="mt-search-count"></h2><label class="mt-search-sortwrap" hidden>Sort: <select><option value="rel">Relevance</option><option value="new">Newest</option><option value="old">Oldest</option></select></label></div>' +
      '<div class="mt-search-grid"></div></div>';
    d.body.appendChild(sBox);
    sBox.addEventListener('error', function (e) {  // image that fails to load -> grey "no image" tile
      var t = e.target; if (t.tagName === 'IMG' && t.parentNode) t.parentNode.innerHTML = '<span class="mt-search-noimg" aria-hidden="true"></span>';
    }, true);
    var input = sBox.querySelector('input'), timer;
    input.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(function () { sState.q = input.value.trim(); syncUrl(); runSearch(); }, 180); });
    sBox.querySelector('form').addEventListener('submit', function (e) { e.preventDefault(); sState.q = input.value.trim(); syncUrl(); runSearch(); });
    sBox.querySelector('.mt-search-clear').addEventListener('click', function () { input.value = ''; sState.q = ''; syncUrl(); runSearch(); input.focus(); });
    sBox.querySelector('.mt-search-close').addEventListener('click', closeSearch);
    sBox.querySelector('select').addEventListener('change', function () { sState.sort = this.value; runSearch(); });
    sBox.addEventListener('click', function (e) { if (e.target === sBox) closeSearch(); });
    sBox.addEventListener('scroll', function () { if (sState.shown < sState.res.length && sBox.scrollTop + sBox.clientHeight > sBox.scrollHeight - 600) more(); }, { passive: true });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !sBox.hidden) closeSearch(); });
  }
  function syncUrl() {
    try { var u = new URL(location.href); sState.q ? u.searchParams.set('s', sState.q) : u.searchParams.delete('s'); history.replaceState(null, '', u); } catch (e) { }
  }
  function openSearch(q) {
    sBox || buildBox();
    var input = sBox.querySelector('input'); input.value = q; sState.q = q.trim();
    sBox.hidden = false; root.classList.add('mt-search-open'); input.focus();
    sBox.querySelector('.mt-search-count').textContent = 'Searching…';
    loadIndex().then(function () { syncUrl(); runSearch(); }, function () { sBox.querySelector('.mt-search-count').textContent = 'Search is not available right now.'; });
  }
  function closeSearch() { sBox.hidden = true; root.classList.remove('mt-search-open'); sState.q = ''; syncUrl(); }
  try { var qs = new URLSearchParams(location.search).get('s'); if (qs !== null) openSearch(qs); } catch (e) { }
  $$('form.elementor-search-form, form.search-form').forEach(function (f) {
    var inp = f.querySelector('[name=s]');
    f.addEventListener('submit', function (e) { e.preventDefault(); openSearch((inp || {}).value || ''); });
    inp && inp.addEventListener('focus', loadIndex, { once: true });  // warm the index while the visitor types
    var tg = f.querySelector('.elementor-search-form__toggle'); tg && tg.addEventListener('click', function () { f.classList.toggle('elementor-search-form--full-screen'); });
  });

  /* ---------- reveal animations (Elementor entrance animations) ---------- */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (en) { en.forEach(function (x) { if (x.isIntersecting) { var s = settings(x.target), a = s._animation || s.animation; if (a && a !== 'none') x.target.classList.add('animated', a); io.unobserve(x.target); } }); }, { rootMargin: '0px 0px -10% 0px' });
    $$('[data-settings*="animation"]').forEach(function (el) { if (!el.closest('.mtslider')) io.observe(el); });
  }

  /* ---------- PDF flipbook (catalog): pdf.js renders the pages, loaded only when the book is near ---------- */
  $$('.mt-flipbook[data-pdf]').forEach(function (box) {
    var src = box.getAttribute('data-pdf');
    // demo on github.io: the live site sends no CORS header, so the PDF is copied next to the demo
    var LIVE = 'https://www.midwest-tropical.com/';
    if (src.indexOf(LIVE) === 0 && location.origin + '/' !== LIVE) src = SITE_BASE + src.slice(LIVE.length);
    else if (/^\//.test(src)) src = SITE_BASE + src.slice(1);
    var started = false;
    function start() {
      if (started) return; started = true;
      box.classList.add('mt-fb-loading');
      loadScript(SITE_BASE + 'assets/js/pdfjs/pdf.min.js').then(function () {
        var lib = window.pdfjsLib; lib.GlobalWorkerOptions.workerSrc = SITE_BASE + 'assets/js/pdfjs/pdf.worker.min.js';
        return lib.getDocument({ url: src }).promise;
      }).then(function (pdf) { book(box, pdf, src); })
        .catch(function () { box.classList.remove('mt-fb-loading'); box.classList.add('mt-fb-failed'); });
    }
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) { if (es[0].isIntersecting) { io.disconnect(); start(); } }, { rootMargin: '400px' });
      io.observe(box);
    } else start();
  });
  function loadScript(u) {
    return new Promise(function (ok, bad) { var s = d.createElement('script'); s.src = u; s.onload = ok; s.onerror = bad; d.head.appendChild(s); });
  }
  function book(box, pdf, src) {
    // A book like the live catalog: cover alone, then two-page spreads; pages turn in 3D around the
    // spine (800 ms, as on the live site). Click/tap a side, use the arrows or keys, or drag a page.
    var n = pdf.numPages, ratio = 1.414, title = box.getAttribute('data-title') || 'Catalog', DUR = 800;
    var urls = {}, ready = {}, view = null, busy = false, W = 0, H = 0, TWO = true, gen = 0;
    box.innerHTML =
      '<div class="mt-fb-stage" tabindex="0" aria-label="' + esc(title) + ' - use the arrow keys to turn pages">' +
      '<div class="mt-fb-book"><div class="mt-fb-slot mt-fb-l"></div><div class="mt-fb-slot mt-fb-r"></div></div></div>' +
      '<button type="button" class="mt-fb-arrow mt-fb-prev" aria-label="Previous page"></button>' +
      '<button type="button" class="mt-fb-arrow mt-fb-next" aria-label="Next page"></button>' +
      '<div class="mt-fb-bar">' +
      '<button type="button" data-go="first" aria-label="First page">&#171;</button>' +
      '<button type="button" data-go="prev" aria-label="Previous page">&#8249;</button>' +
      '<span class="mt-fb-num" aria-live="polite"></span>' +
      '<button type="button" data-go="next" aria-label="Next page">&#8250;</button>' +
      '<button type="button" data-go="last" aria-label="Last page">&#187;</button>' +
      '<a href="' + esc(src) + '" download aria-label="Download PDF" title="Download PDF">&#8681;</a>' +
      '<button type="button" data-go="full" aria-label="Fullscreen" title="Fullscreen">&#9974;</button></div>';
    var stage = box.querySelector('.mt-fb-stage'), bk = box.querySelector('.mt-fb-book'),
      L = box.querySelector('.mt-fb-l'), R = box.querySelector('.mt-fb-r'), num = box.querySelector('.mt-fb-num');
    box.classList.remove('mt-fb-loading'); box.classList.add('mt-fb-ready');

    function layout() {
      var sw = stage.clientWidth;
      TWO = sw >= 700;
      var w = Math.floor(sw / (TWO ? 2 : 1)), maxH = Math.max(420, Math.min(window.innerHeight - 140, 900));
      if (w * ratio > maxH) w = Math.floor(maxH / ratio);
      W = w; H = Math.round(w * ratio);
      bk.style.width = (TWO ? 2 * W : W) + 'px'; bk.style.height = H + 'px';
      L.style.width = R.style.width = W + 'px'; R.style.left = TWO ? W + 'px' : '0'; L.style.display = TWO ? '' : 'none';
    }
    // a view is [left page, right page]; 0 = no page. Single-page mode only uses the right slot.
    function spreadOf(p) {
      p = Math.max(1, Math.min(n, p));
      if (!TWO) return [0, p];
      var l = p - (p % 2);
      return [l, l + 1 <= n ? l + 1 : 0];
    }
    function nextOf(v) { return TWO ? (v[1] && v[1] < n ? spreadOf(v[1] + 1) : null) : (v[1] < n ? [0, v[1] + 1] : null); }
    function prevOf(v) { return TWO ? (v[0] ? spreadOf(v[0] - 1) : null) : (v[1] > 1 ? [0, v[1] - 1] : null); }
    function shift(v) { return !TWO ? 0 : !v[0] ? -W / 2 : !v[1] ? W / 2 : 0; }

    function render(p) {
      if (!p || p > n) return Promise.resolve('');
      if (urls[p]) return urls[p];
      var g = gen;
      return (urls[p] = pdf.getPage(p).then(function (pg) {
        var v0 = pg.getViewport({ scale: 1 }), dpr = Math.min(window.devicePixelRatio || 1, 2);
        var v = pg.getViewport({ scale: W / v0.width * dpr });
        var c = d.createElement('canvas'); c.width = Math.round(v.width); c.height = Math.round(v.height);
        return pg.render({ canvasContext: c.getContext('2d'), viewport: v }).promise.then(function () {
          return new Promise(function (ok) { c.toBlob(function (b) { ok(URL.createObjectURL(b)); }, 'image/jpeg', 0.9); });
        });
      }).then(function (u) { if (g === gen) ready[p] = u; return u; }));
    }
    function put(slot, p) {
      var u = p && ready[p];
      slot.innerHTML = u ? '<img src="' + u + '" alt="' + esc(title) + ' - page ' + p + '" draggable="false">' : '';
      slot.classList.toggle('mt-fb-blank', !p);
    }
    function ui() {
      var v = view, a = v[0], b = v[1];
      num.textContent = (a && b ? a + '-' + b : (a || b)) + ' / ' + n;
      box.querySelector('.mt-fb-prev').disabled = !prevOf(v);
      box.querySelector('.mt-fb-next').disabled = !nextOf(v);
    }
    function preload() { // render the neighbouring spreads so turning starts instantly
      [nextOf(view), prevOf(view)].forEach(function (v) { if (v) { render(v[0]); render(v[1]); } });
    }
    function setView(v) {
      view = v; busy = true;
      Promise.all([render(v[0]), render(v[1])]).then(function () {
        put(L, v[0]); put(R, v[1]); busy = false; preload(); runQueued();
      });
      bk.style.transform = 'translateX(' + shift(v) + 'px)';
      ui();
    }

    // build a turning page; returns {set(t), finish(done)} once its images are ready
    function start(dir, target) {
      busy = true;
      var from = view, single = !TWO, front, back, under, underP, origin, left;
      if (single) {
        front = dir === 'next' ? from[1] : target[1]; back = 0; left = 0; origin = 'left';
        under = R; underP = dir === 'next' ? target[1] : from[1];
      } else if (dir === 'next') {
        front = from[1]; back = target[0]; under = R; underP = target[1]; left = W; origin = 'left';
      } else {
        front = from[0]; back = target[1]; under = L; underP = target[0]; left = 0; origin = 'right';
      }
      return Promise.all([render(front), render(back), render(underP)]).then(function () {
        var f = d.createElement('div');
        f.className = 'mt-fb-flip';
        f.style.cssText = 'left:' + left + 'px;width:' + W + 'px;height:' + H + 'px;transform-origin:' + origin + ' center';
        f.innerHTML = '<div class="mt-fb-face mt-fb-front"></div><div class="mt-fb-face mt-fb-back"></div>';
        var ff = f.firstChild, fb = f.lastChild;
        put(ff, front); put(fb, back);
        ff.insertAdjacentHTML('beforeend', '<i class="mt-fb-shade mt-fb-shade-' + origin + '"></i>');
        fb.insertAdjacentHTML('beforeend', '<i class="mt-fb-shade mt-fb-shade-' + (origin === 'left' ? 'right' : 'left') + '"></i>');
        var sf = ff.lastChild, sb = fb.lastChild;
        if (single && dir === 'prev') { /* the previous page swings back in over the current one */ } else put(under, underP);
        bk.appendChild(f); bk.classList.add('mt-fb-turning');
        bk.style.transition = 'none';
        var s0 = shift(from), s1 = shift(target), t = 0;
        function set(x) {
          t = Math.max(0, Math.min(1, x));
          var e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; // ease in-out
          var a = single ? (dir === 'next' ? -180 * e : -180 * (1 - e)) : (dir === 'next' ? -180 * e : 180 * e);
          f.style.transform = 'rotateY(' + a + 'deg)';
          var k = Math.sin((single && dir === 'prev' ? 1 - e : e) * Math.PI);
          sf.style.opacity = sb.style.opacity = (0.5 * k).toFixed(3);
          if (single) f.style.opacity = dir === 'next' ? (e > 0.5 ? 2 - 2 * e : 1) : (e < 0.5 ? 2 * e : 1);
          bk.style.transform = 'translateX(' + (s0 + (s1 - s0) * e) + 'px)';
        }
        function finish(done) {
          var t0 = t, t1 = done ? 1 : 0, ms = Math.max(120, DUR * Math.abs(t1 - t0)), st = null;
          function step(now) {
            if (st === null) st = now;
            var k = Math.min(1, (now - st) / ms);
            t = t0 + (t1 - t0) * k; set(t);
            if (k < 1) return requestAnimationFrame(step);
            if (done) {
              view = target;
              if (single) put(R, target[1]); else if (dir === 'next') put(L, target[0]); else put(R, target[1]);
            } else put(under, single ? from[1] : (dir === 'next' ? from[1] : from[0]));
            f.remove(); bk.classList.remove('mt-fb-turning');
            bk.style.transform = 'translateX(' + shift(view) + 'px)';
            requestAnimationFrame(function () { bk.style.transition = ''; });
            busy = false; ui(); preload(); runQueued();
          }
          requestAnimationFrame(step);
        }
        set(0);
        return { set: set, finish: finish };
      });
    }
    function turn(dir, target) {
      if (busy || !view) { queued = [dir, target]; return; }
      target = target || (dir === 'next' ? nextOf(view) : prevOf(view));
      if (!target || (target[0] === view[0] && target[1] === view[1])) return;
      start(dir, target).then(function (f) { f.finish(true); });
    }
    var queued = null;
    function runQueued() { var q = queued; queued = null; if (q) turn(q[0], q[1]); }
    function jump(p) { var t = spreadOf(p); turn((t[1] || t[0]) > (view[1] || view[0]) ? 'next' : 'prev', t); }

    box.querySelector('.mt-fb-prev').onclick = function () { turn('prev'); };
    box.querySelector('.mt-fb-next').onclick = function () { turn('next'); };
    box.querySelector('.mt-fb-bar').addEventListener('click', function (e) {
      var b = e.target.closest('[data-go]'); if (!b) return;
      var g = b.getAttribute('data-go');
      if (g === 'first') jump(1); else if (g === 'last') jump(n);
      else if (g === 'prev' || g === 'next') turn(g);
      else if (g === 'full') { if (d.fullscreenElement) d.exitFullscreen(); else if (box.requestFullscreen) box.requestFullscreen(); }
    });
    stage.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { turn('next'); e.preventDefault(); } else if (e.key === 'ArrowLeft') { turn('prev'); e.preventDefault(); }
    });

    // click a side to turn; or grab a page and drag it over (like turning a real page)
    var sx = null, side = null, drag = null, dragT = 0, dragDir = null;
    stage.addEventListener('pointerdown', function (e) {
      if (busy || e.button > 0 || !view) return;
      var r = bk.getBoundingClientRect();
      sx = e.clientX; side = e.clientX > r.left + r.width / 2 ? 'next' : 'prev'; drag = null; dragT = 0;
      if (!TWO) side = e.clientX > r.left + r.width / 2 ? 'next' : 'prev';
      try { stage.setPointerCapture(e.pointerId); } catch (x) {}
    });
    stage.addEventListener('pointermove', function (e) {
      if (sx === null) return;
      var dx = e.clientX - sx;
      if (!drag && Math.abs(dx) > 10) {
        dragDir = dx < 0 ? 'next' : 'prev';
        var target = dragDir === 'next' ? nextOf(view) : prevOf(view);
        if (!target) { sx = null; return; }
        drag = start(dragDir, target);
        drag.then(function (f) { drag = f; f.set(dragT); });
      }
      if (drag) {
        dragT = Math.max(0, (dragDir === 'next' ? -dx : dx) / (TWO ? 1.6 * W : 0.9 * W));
        if (drag.set) drag.set(dragT);
      }
    });
    function release(e) {
      if (sx === null) return;
      var moved = drag;
      sx = null;
      if (moved) {
        var done = dragT > 0.25, finishIt = function (f) { f.finish(done); };
        if (moved.set) finishIt(moved); else moved.then(finishIt);
        drag = null;
      } else if (e.type === 'pointerup') turn(side);
    }
    stage.addEventListener('pointerup', release);
    stage.addEventListener('pointercancel', release);

    function rebuild() {
      gen++;
      Object.keys(ready).forEach(function (k) { URL.revokeObjectURL(ready[k]); });
      urls = {}; ready = {};
      var p = view ? (view[1] || view[0]) : 1;
      layout(); setView(spreadOf(p));
    }
    pdf.getPage(1).then(function (pg) { var v = pg.getViewport({ scale: 1 }); ratio = v.height / v.width; layout(); setView(spreadOf(1)); });
    var rw = stage.clientWidth;
    addEventListener('resize', function () { if (!busy && Math.abs(stage.clientWidth - rw) > 40) { rw = stage.clientWidth; rebuild(); } });
    d.addEventListener('fullscreenchange', function () { setTimeout(function () { rw = stage.clientWidth; rebuild(); }, 100); });
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
