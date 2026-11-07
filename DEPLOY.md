# Midwest Tropical – fast PHP version

`site/` is the complete website: same URLs, text, images, titles, meta descriptions,
canonical tags, Open Graph and schema (JSON-LD) as the WordPress site, with no WordPress,
jQuery or plugin scripts.

## Upload

1. Hosting needs **PHP 7.4+** on Apache (or LiteSpeed). No database is needed.
2. Upload **everything inside `site/`** (including the hidden `.htaccess`) to `public_html/`.
3. Open `form-handler.php` and set `MT_TO` to the inbox that should receive leads.
   Every lead is also saved to `includes/form-submissions.log` (blocked from the web).
4. Check `MISSING-IMAGES.txt`: these files are also broken or empty on the current live
   site. If the client has them, put them in `site/wp-content/uploads/` under the same names.
5. Point the domain to the new hosting. URLs are identical, so there is nothing to redirect.
6. Search Console: submit `https://www.midwest-tropical.com/sitemap.xml`.

## What's in the folder

| Path | What it is |
|---|---|
| `*/index.php` | One file per page, same URL as before (`/airports/` → `airports/index.php`) |
| `includes/header-*.php`, `footer-*.php`, `popup-*.php` | Shared header, footer and quote popup |
| `assets/css/core.css` | CSS shared by all pages (browser caches it once) |
| `assets/css/b-*.css` | Small page-specific CSS |
| `assets/css/fix.css` | Layout fixes (mobile overflow, menus, popups) |
| `assets/js/main.js` | ~10 KB: replaces jQuery and Elementor (menu, sliders, tabs, popup, forms, videos, lightbox, analytics) |
| `wp-content/uploads/` | All images, at the same paths as before (keeps Google Images rankings) |
| `form-handler.php` | Sends all quote/contact forms by email |
| `sitemap.xml`, `robots.txt`, `404.php`, `.htaccess` | SEO, 404 page, gzip, browser caching, https/www redirects |

## Fixes compared with the live site

- **Blog:** all 477 posts on the live site render empty (broken single-post template).
  Their article text, date and featured image were restored from the client's WordPress.
- **One design system on every page:** Quicksand on all headings (550+ used the system
  font), the same title style (50px light, in a grey band), 36px section headings and 16px text.
- **Location pages and other theme-template pages** (about 60): content was edge to edge
  with no title band; they now use the same frame and width as the other pages, with one H1 each.
- **Mobile sideways scrolling** fixed (accordions, glass-water-features buttons, menu).
- Elementor widgets that needed jQuery now use ~10 KB of vanilla JS.

## Speed changes (content and design unchanged)

- Removed WordPress, WooCommerce, Jetpack, jQuery and about 40 plugin scripts.
- Unused CSS stripped; one shared CSS file, cached by the browser.
- Images lazy-load below the fold; the first content images load with high priority.
- Google Analytics and Tag Manager (same IDs) load after the first scroll or tap.
- YouTube videos show a thumbnail and only load the player when clicked.
- `.htaccess`: gzip/brotli compression and a 1-year browser cache for images and fonts.

## Rebuilding from the live site

If the WordPress site changes before launch:

```bash
python -I tools/rebuild.py <cache folder> all
```

Local preview without PHP: `python -I tools/preview_server.py site 8080`, then open http://localhost:8080
