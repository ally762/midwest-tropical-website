# Midwest Tropical – Fast PHP Website

A rebuild of **midwest-tropical.com**, moved off WordPress/Elementor to plain
**HTML + CSS + JavaScript + PHP**. URLs, page titles, meta descriptions, canonical tags,
Open Graph and schema markup are the same as the live site, so SEO rankings carry over.

| | |
|---|---|
| Pages | **1,261** (99 main pages · 478 blog posts · 685 portfolio/product pages) |
| JavaScript | ~10 KB vanilla JS (was jQuery + Elementor + ~40 WordPress plugins) |
| Server needs | PHP 7.4+ on Apache/LiteSpeed. No database. |

## What changed vs. the live site

**Speed**
- No WordPress, jQuery, WooCommerce, Jetpack or plugin scripts.
- Unused CSS removed; one shared, browser-cached `core.css` plus a small CSS file per page.
- Only Latin font files; the main font is preloaded.
- Images lazy-load; YouTube loads only on click; analytics load after the first interaction.
- `.htaccess`: gzip/brotli and a 1-year cache for images and fonts.

**Layout fixes**
- One design system on every page: same font (Quicksand), title style (grey band, 50px light H1),
  section headings and body text. 550+ headings had been falling back to the system font.
- ~60 location and other theme-template pages had edge-to-edge text and no title; they now use the
  same frame and width as the other pages.
- Mobile sideways scrolling fixed (accordions, button rows, mobile menu).
- Exactly one H1 on every page.

**Content restored**
- All 477 blog posts render **empty** on the live site (broken post template). Their article text,
  date and featured image were restored from the client's WordPress.

## Folder structure

```
site/                  <- upload the CONTENTS of this folder to public_html/
  index.php            home page; every other URL is <slug>/index.php
  includes/            shared header, footer and quote popup
  assets/css/          core.css (shared), b-*.css (per page), fix.css (layout fixes)
  assets/js/main.js    menu, sliders, tabs, popup, forms, lightbox, video, analytics
  form-handler.php     emails every quote/contact form (set MT_TO inside)
  sitemap.xml, robots.txt, 404.php, .htaccess
  wp-content/uploads/  images (NOT in this repo – see below)
site-src/              hand-written files copied into site/ on each build
tools/                 build pipeline (Python)
DEPLOY.md              step-by-step deployment guide
MISSING-IMAGES.txt     12 images that are also missing/empty on the live site
```

## Images

The images and videos (`site/wp-content/uploads/`, ~1.8 GB) are **not in this repository**
because of GitHub's size limits. They keep the same paths as the old site, so copy the
`uploads` folder into `site/wp-content/` before deploying or previewing.

## Preview locally

```bash
python tools/preview_server.py site 8080
```

Then open http://localhost:8080. It's a small Python server that resolves the PHP includes,
so no PHP install is needed. On real hosting, PHP serves the pages directly.

## Rebuild from the live site

```bash
python -I tools/rebuild.py <cache-folder> all
```

Steps: build pages, posts and products, then restore blog articles, finalize (sitemap, 404,
title bands), then purge unused CSS.

## Deploy

See [DEPLOY.md](DEPLOY.md).
