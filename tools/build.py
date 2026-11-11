"""
Midwest Tropical -> fast static PHP site converter.

Fetches every URL from the live sitemaps, keeps the exact content / layout / SEO
head, strips WordPress + plugin JavaScript, downloads every image/font locally
(same /wp-content/uploads/ paths so Google Images URLs keep working), bundles and
minifies CSS per page-template, and writes clean PHP pages with shared
header/footer includes.

usage:  python -I build.py <out_dir> <cache_dir> [pages|posts|products|all] [limit]
"""
import concurrent.futures as cf
import hashlib
import html
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request

ORIGIN = "https://www.midwest-tropical.com"
HOST_RE = r"(?:https?:)?(?:\\?/){2}(?:www\.)?midwest-tropical\.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

OUT = os.path.abspath(sys.argv[1])
CACHE = os.path.abspath(sys.argv[2])
MODE = sys.argv[3] if len(sys.argv) > 3 else "pages"
LIMIT = int(sys.argv[4]) if len(sys.argv) > 4 else 0
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

lock = threading.Lock()
asset_done = {}
failed = []


# ---------------------------------------------------------------- fetching
def to_uri(url):
    """percent-encode non-ASCII characters (e.g. en-dash in file names) so urllib can request them"""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~"),
                                    urllib.parse.quote(p.query, safe="=&%/:+,;-._~"), ""))


def fetch(url, binary=False, tries=3):
    key = hashlib.sha1(url.encode()).hexdigest()
    url = to_uri(url)
    cpath = os.path.join(CACHE, key)
    if os.path.exists(cpath) and os.path.getsize(cpath) > 0:
        with open(cpath, "rb") as f:
            data = f.read()
    else:
        data = None
        for i in range(tries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code in (404, 410, 403):
                    return None
                time.sleep(1 + i * 2)
            except Exception:
                time.sleep(1 + i * 2)
        if not data:  # None or empty body: treat as failure, never cache
            return None
        with open(cpath, "wb") as f:
            f.write(data)
    return data if binary else data.decode("utf-8", "replace")


def sitemap(name):
    xml = fetch(f"{ORIGIN}/{name}-sitemap.xml") or ""
    return re.findall(r"<url>\s*<loc>([^<]+)</loc>", xml)


# ---------------------------------------------------------------- assets
def local_asset_path(abs_url):
    """Map an absolute asset URL to a root-relative local path (and download it)."""
    p = urllib.parse.urlsplit(abs_url)
    path = urllib.parse.unquote(p.path)
    host = p.netloc.lower()
    if re.match(r"i\d\.wp\.com$", host):  # jetpack photon cdn -> origin
        parts = path.lstrip("/").split("/", 1)
        host, path = parts[0], "/" + parts[1]
        abs_url = "https://" + host + path
        p = urllib.parse.urlsplit(abs_url)
    if host.endswith("midwest-tropical.com") and path.startswith(("/wp-content/uploads/", "/wp-content/grand-media/")):
        local = path
    else:
        local = "/assets/ext/" + host.replace(":", "_") + path
    local = re.sub(r"[^A-Za-z0-9_./%-]", "_", local)
    src = urllib.parse.urlunsplit((p.scheme or "https", p.netloc if not host else host, p.path, "", ""))
    with lock:
        if local in asset_done:
            return local
        asset_done[local] = src
    return local


def download_all_assets():
    items = list(asset_done.items())
    todo = [(l, s) for l, s in items if not os.path.exists(OUT + l) or os.path.getsize(OUT + l) == 0]
    print(f"assets: {len(items)} referenced, {len(todo)} to download", flush=True)

    def dl(item):
        local, src = item
        data = fetch(src, binary=True)
        if data is not None and not src.lower().endswith((".svg", ".html")) and data[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
            data = None  # soft 404 page
        if data is None:
            failed.append(src)
            return
        dst = OUT + local
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)

    with cf.ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(dl, todo)):
            if i and i % 500 == 0:
                print(f"  {i}/{len(todo)}", flush=True)

    # remember files whose local (safe) name differs from the live file name (e.g. en-dash -> "_"),
    # so the GitHub Pages demo can load those images from the live site under their real name
    mp = os.path.join(OUT, "includes", "media-map.json")
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    mapping = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    for local, src in items:
        live_path = urllib.parse.urlsplit(src).path
        if local.startswith("/wp-content/") and urllib.parse.unquote(live_path) != local:
            mapping[local] = src
    json.dump(mapping, open(mp, "w", encoding="utf-8"), indent=0)


UPLOAD_RE = re.compile(
    r"(?:https?:)?(?:\\?/){2}(?:i\d\.wp\.com(?:\\?/))?(?:www\.)?midwest-tropical\.com"
    r"((?:\\?/)wp-content(?:\\?/)(?:uploads|grand-media)(?:\\?/)[^\s\"'()<>,?#&;]+?\.(?:jpe?g|png|gif|webp|avif|svg|mp4|webm|mov|pdf|ico|woff2?|ttf|eot|otf))"
    r"(?=[\s\"'()<>,?#&;\\]|$)"
    r"(?:\?[^\s\"'()<>,]*)?",
    re.I,
)


def localize_uploads(text):
    def rep(m):
        escaped = "\\/" in m.group(0)
        path = m.group(1).replace("\\/", "/")
        local = local_asset_path(ORIGIN + path)
        return local.replace("/", "\\/") if escaped else local

    return UPLOAD_RE.sub(rep, text)


# ---------------------------------------------------------------- css
css_cache = {}


def css_minify(css):
    css = re.sub(r"/\*(?!!).*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)  # safe enough: selectors like 'a :hover' are rare
    css = css.replace(";}", "}")
    return css.strip()


def woff2_only(css):
    """In @font-face rules keep only the woff2 source when there is one (fewer downloads)."""
    def ff(m):
        block = m.group(0)
        w = re.search(r"url\(\s*['\"]?([^)'\"]+\.woff2[^)'\"]*)['\"]?\s*\)", block)
        if not w:
            return block
        block = re.sub(r"src\s*:[^;}]*(;|(?=}))", "", block)
        return block[:-1] + f";src:url({w.group(1)}) format(\"woff2\")}}"
    return re.sub(r"@font-face\s*{[^}]*}", ff, css)


def latin_only(css):
    """English-only site: drop @font-face subsets for cyrillic/greek/vietnamese/etc. (keep latin + latin-ext)."""
    def ff(m):
        block = m.group(0)
        ur = re.search(r"unicode-range\s*:\s*([^;}]*)", block, re.I)
        if not ur:
            return block
        r = ur.group(1).upper()
        return block if ("U+0000-00FF" in r or "U+0100-02" in r or "U+0100-024F" in r) else ""
    return re.sub(r"(?:/\*[^*]*\*/\s*)?@font-face\s*{[^}]*}", ff, css)


TWO_LAZY_BG = re.compile(r"""url\(\s*(['"]?)data:image/svg\+xml[^)]*?#\}\s*(https?://[^)'"\s]+)\s*\1\s*\)""", re.I)


def real_backgrounds(css):
    """10Web Booster lazy backgrounds: url(data:svg-placeholder#}REAL-URL) is swapped by its JS.
    We don't ship that JS, so use the real image URL directly (also keeps CSS parsable)."""
    return TWO_LAZY_BG.sub(lambda m: f"url({m.group(2)})", css)


def process_css(css, base_url):
    css = latin_only(woff2_only(real_backgrounds(css)))

    def rep(m):
        raw = m.group(1).strip().strip("'\"")
        if raw.startswith("data:") or raw.startswith("#") or not raw:
            return m.group(0)
        absu = urllib.parse.urljoin(base_url, raw)
        if not absu.startswith("http"):
            return m.group(0)
        # the optimizer's "rucss" copies point Font Awesome 4 at a file that doesn't exist next to them;
        # use the copy the site ships in a plugin folder
        if "/mt-page-cache/rucss/" in absu and re.search(r"fontawesome-webfont\.(woff2?|ttf|eot|svg)", absu):
            absu = "https://www.midwest-tropical.com/wp-content/plugins/gallery-videos/public/css/fontawesome-webfont.woff2"
        return "url(" + local_asset_path(absu.split("#")[0].split("?")[0]) + ("#" + raw.split("#")[1] if "#" in raw else "") + ")"

    css = re.sub(r"url\(\s*([^)]+?)\s*\)", rep, css)
    # @import of google fonts etc: leave as-is
    return css


ORIGINAL_CSS = [
    (r"^elementor-post-(\d+)-css$", "/wp-content/uploads/elementor/css/post-{0}.css"),
    (r"^hello-elementor-css$", "/wp-content/themes/hello-elementor/assets/css/reset.css"),
    (r"^hello-elementor-theme-style-css$", "/wp-content/themes/hello-elementor/assets/css/theme.css"),
    (r"^hello-elementor-header-footer-css$", "/wp-content/themes/hello-elementor/assets/css/header-footer.css"),
    (r"^elementor-gf-local-([\w-]+)-css$", "/wp-content/uploads/elementor/google-fonts/css/{0}.css"),
    (r"^base-desktop-css$", "/wp-content/uploads/elementor/css/base-desktop.css"),
]


def original_css_url(link_id):
    for pat, tpl in ORIGINAL_CSS:
        m = re.match(pat, link_id or "")
        if m:
            return ORIGIN + tpl.format(*m.groups())
    return None


def get_css_file(url, link_id=""):
    key = url + "|" + (link_id or "")
    if key in css_cache:
        return css_cache[key]
    absu = urllib.parse.urljoin(ORIGIN + "/", html.unescape(url))
    txt = fetch(absu) or ""
    if looks_bad_css(txt):
        # optimizer cache file expired (server answers with an html page): use the original stylesheet
        orig = original_css_url(link_id)
        txt = (fetch(orig) or "") if orig else ""
        if orig and not looks_bad_css(txt):
            absu = orig
        else:
            print("BAD CSS", link_id, absu, flush=True)
            bad_css_hits.append(absu)
            for u in (absu, orig):  # never cache a bad css answer
                if u:
                    cp = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest())
                    if os.path.exists(cp):
                        os.remove(cp)
            return ""
    txt = process_css(txt, absu)
    css_cache[key] = txt
    return txt


def looks_bad_css(txt):
    head = txt[:500].lstrip().lower()
    return head.startswith("<") or "window.onload" in txt or "navigator.sendbeacon" in txt.lower()


SKIP_CSS_IDS = ("jetpack-search", "jetpack-instant-search", "jetpack-swiper-library", "jetpack-carousel", "sib-front")
SKIP_STYLE_IDS = ("jetpack-search", "jetpack-stats", "mt-pc-critical")

bundles = {}


def make_bundle(parts):
    """parts = list of (media, css). Returns root-relative bundle path."""
    body = []
    for media, css in parts:
        if media and media not in ("all", "screen"):
            body.append(f"@media {media}{{{css}}}")
        else:
            body.append(css)
    joined = css_minify(real_backgrounds("\n".join(body)))
    # placeholders that only become visible after minifying (whitespace/quotes inside url())
    joined = real_backgrounds(joined)
    # @charset/@import must be first: hoist
    imports = re.findall(r"@import[^;]+;", joined)
    joined = re.sub(r"@charset[^;]+;|@import[^;]+;", "", joined)
    joined = "".join(imports) + joined
    h = hashlib.sha1(joined.encode()).hexdigest()[:10]
    path = f"/assets/css/b-{h}.css"
    with lock:
        if path not in bundles:
            bundles[path] = joined
            os.makedirs(OUT + "/assets/css", exist_ok=True)
            with open(OUT + path, "w", encoding="utf-8") as f:
                f.write(joined)
    return path


# ---------------------------------------------------------------- html
def attr(tag, name):
    m = re.search(r'\s' + name + r'\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag, re.I)
    if not m:
        return None
    return m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))


HEAD_KEEP = re.compile(
    r"<meta\s[^>]*(?:name=\"(?:description|robots|google-site-verification|theme-color|twitter:[^\"]+)\"|property=\"(?:og|article|product):[^\"]+\")[^>]*>"
    r"|<link\s[^>]*rel=['\"](?:canonical|icon|apple-touch-icon|shortlink|alternate|prev|next)['\"][^>]*>"
    r"|<script[^>]*type=['\"]application/ld\+json['\"][^>]*>.*?</script>",
    re.S | re.I,
)

JUNK_ATTRS = re.compile(
    r"\s(?:data-attachment-id|data-permalink|data-orig-file|data-orig-size|data-comments-opened|data-image-title|"
    r"data-image-description|data-image-caption|data-medium-file|data-large-file|data-image-meta|crossorigin|"
    r"data-od-[a-z-]+|data-mt-[a-z-]+)=(\"[^\"]*\"|'[^']*'|[^\s>]+)",
    re.I,
)


def split_region(body, kind):
    """Return (start, end) of the outermost element with data-elementor-type=kind."""
    m = re.search(r'<(header|footer|div)\b[^>]*data-elementor-type="' + kind + r'"[^>]*>', body)
    if not m:
        return None
    tag = m.group(1)
    depth, pos = 0, m.start()
    for t in re.finditer(r"<(/?)" + tag + r"\b[^>]*>", body[m.start():]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return m.start(), m.start() + t.end()
    return None


def gmedia_fix(body):
    """Grand-Media 'phantom' galleries are rendered by plugin JS: output real images instead."""
    if "gmPhantom" not in body:
        return body

    def thumb(m):
        a, img = m.group(1), m.group(3)
        img = re.sub(r'\s(?:src|data-src)="[^"]*"', "", img)
        img = re.sub(r"\bclass=\"noLazy\"", 'class="gmPhantom_img"', img)
        return f'{a}{img[:4]} src="{m.group(2)}" loading="lazy"{img[4:]}'

    body = re.sub(r'(<a href="([^"]+)" class="gmPhantom_Thumb"[^>]*>)(<img\b[^>]*>)', thumb, body)
    body = re.sub(r'(class="gmPhantom_Container[^"]*") style="opacity:0"', r"\1", body)
    body = body.replace('class="gmPhantom_Thumb"', 'class="gmPhantom_Thumb mt-lightbox"')

    def imp(m):
        u = html.unescape(m.group(1))
        absu = urllib.parse.urljoin(ORIGIN + "/", u)
        css = fetch(absu) or ""
        return "" if looks_bad_css(css) else css_minify(process_css(css, absu))

    body = re.sub(r"@import url\('([^']*grand-media[^']*)'\)[^;]*;", imp, body)
    return body


def unlazy(body):
    """10Web Booster lazy-load: <img src="data:svg placeholder" data-src=REAL data-srcset=... class="lazy">
    (also <source data-srcset>, <iframe data-src>). Without its JS the images stay empty, so put the
    real URLs back; the browser's own loading="lazy" (added later) keeps it fast."""
    def img(m):
        tag = m.group(0)
        ds = re.search(r'\sdata-src=(["\'])(.*?)\1', tag)
        if not ds:
            return tag
        tag = re.sub(r"""\ssrc=(["'])data:image/[^"']*\1""", "", tag)
        tag = tag.replace(ds.group(0), f' src="{ds.group(2)}"')
        tag = re.sub(r'\sdata-(srcset|sizes)=(["\'])', r' \1=\2', tag)
        tag = re.sub(r'(class=["\'][^"\']*?)\s*\blazy\b', r"\1", tag)
        return tag

    body = re.sub(r"<img\b[^>]*\bdata-src=[^>]*>", img, body)
    body = re.sub(r"(<source\b[^>]*?)\sdata-srcset=", r"\1 srcset=", body)
    # the site's own "mt-page-cache" deferral: an empty <img class="mt-pc-deferred"> (no src), optionally in a
    # <picture> with an empty <source>, followed by <noscript> holding the real image -> use the real one
    body = re.sub(
        r"(?:<picture>\s*(?:<source\b[^>]*>\s*)*<img\b[^>]*\bmt-pc-deferred\b[^>]*>\s*</picture>|<img\b[^>]*\bmt-pc-deferred\b[^>]*>)"
        r"\s*<noscript>(.*?)</noscript>",
        lambda m: m.group(1), body, flags=re.S | re.I)
    # 10Web also keeps a second copy of every lazy image in <noscript> for no-JS visitors;
    # the real image is in the page now, so drop the duplicate (smaller HTML)
    body = re.sub(r"<noscript>\s*(?:<img\b[^>]*>\s*)+</noscript>", "", body, flags=re.I)
    return body


def clean_body(body):
    # keep ld+json + zoho validation scripts, drop all other scripts
    def script_rep(m):
        s = m.group(0)
        if re.search(r"application/(?:ld\+json)", s[:200]):
            return s
        open_tag = s[: s.find(">") + 1]
        if "src=" in open_tag:
            return ""
        # keep the site's own small widget scripts (Zoho form validation, image lightbox, accordion);
        # they were "delayed" by the old optimizer, so turn them back into normal scripts
        if re.search(r"zf_|getElementById\('lightbox'\)|\.accordion button", s):
            body_js = s[len(open_tag): -len("</script>")]
            return "<script>" + body_js + "</script>"
        return ""

    body = re.sub(r"<script\b[^>]*>.*?</script>", script_rep, body, flags=re.S | re.I)
    body = unlazy(real_backgrounds(body))
    body = gmedia_fix(body)
    body = re.sub(r"<noscript>\s*<iframe[^>]*googletagmanager.*?</noscript>", "", body, flags=re.S | re.I)
    body = re.sub(r"<a [^>]*cdn-cgi/content[^>]*></a>", "", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = JUNK_ATTRS.sub("", body)
    body = re.sub(r"\belementor-invisible\b", "", body)
    # css links inside body are handled by caller (removed here)
    body = re.sub(r"<link[^>]*rel=['\"]stylesheet['\"][^>]*>", "", body)
    # resource hints for WordPress plugin scripts we don't ship (e.g. jetpack swiper.js) -> wasted 404 requests
    body = re.sub(r"<link\b[^>]*rel=['\"](?:prefetch|preload|modulepreload|prerender)['\"][^>]*>", "", body, flags=re.I)
    body = re.sub(r"<style[^>]*id=['\"](?:" + "|".join(SKIP_STYLE_IDS) + r")[^'\"]*['\"][^>]*>.*?</style>", "", body, flags=re.S)
    return body


def rewrite_links(text):
    text = localize_uploads(text)
    # internal links -> root relative (keeps same URL structure)
    text = re.sub(r'(href|action)=(["\'])https?://(?:www\.)?midwest-tropical\.com(?=[/"\'#?])/?', r"\1=\2/", text)
    return text


# .tif uploads used without any srcset: the same photo exists in the media library as JPG
TIF_ALTERNATIVES = {
    "Hotel-Lobby-Glass-and-Stainless-Water-Wall.tif":
        "https://www.midwest-tropical.com/wp-content/uploads/Hotel-Lobby-Glass-and-Stainless-Water-Wall-scaled--768x1090.jpg",
}


def fix_tif(body):
    """Browsers can't show .tif images (broken on the live site too). WordPress also made JPG/WebP
    sizes of those uploads: use the largest of them as src and drop the .tif entries."""
    def rep(m):
        tag = m.group(0)
        src = re.search(r'\ssrc="([^"]+)"', tag)
        if not src or not re.search(r"\.tiff?$", src.group(1), re.I):
            return tag
        alt = TIF_ALTERNATIVES.get(src.group(1).rsplit("/", 1)[-1])
        if alt:
            return tag.replace(src.group(0), f' src="{alt}"')
        ss = re.search(r'\ssrcset="([^"]*)"', tag)
        cands = []
        if ss:
            for c in ss.group(1).split(","):
                parts = c.strip().split()
                if parts and not re.search(r"\.tiff?$", parts[0], re.I):
                    w = int(re.sub(r"\D", "", parts[1])) if len(parts) > 1 and re.sub(r"\D", "", parts[1]) else 0
                    cands.append((w, parts[0], c.strip()))
        if not cands:
            return tag
        best = max(cands)[1]
        tag = tag.replace(src.group(0), f' src="{best}"')
        tag = tag.replace(ss.group(0), ' srcset="' + ", ".join(c[2] for c in cands) + '"')
        return tag
    return re.sub(r"<img\b[^>]*>", rep, body)


def one_h1_in_posts(body):
    """Blog posts: the template already has the title as H1; H1s inside the article text become H2."""
    if 'data-elementor-type="single-post"' not in body:
        return body
    i = body.find("elementor-widget-theme-post-content")
    if i < 0:
        return body
    head, rest = body[:i], body[i:]
    rest = re.sub(r"<h1(\b[^>]*)>", r"<h2\1>", rest)
    rest = rest.replace("</h1>", "</h2>")
    return head + rest


def lazyify(body, eager=2):
    n = [0]

    def rep(m):
        tag = m.group(0)
        n[0] += 1
        tag = re.sub(r'\s(?:loading|decoding|fetchpriority)="[^"]*"', "", tag)
        extra = ' decoding="async"'
        if n[0] > eager:
            extra += ' loading="lazy"'
        elif n[0] == eager:
            extra += ' fetchpriority="high"'
        return tag[:4] + extra + tag[4:]

    return re.sub(r"<img\b[^>]*>", rep, body)


def url_to_dir(url):
    path = urllib.parse.urlsplit(url).path
    path = urllib.parse.unquote(path).strip("/")
    return path


shared = {}


bad_css_hits = []


def build_page(url, retry=True):
    """Build one page; if its optimizer CSS links are stale, refetch fresh HTML once and rebuild."""
    del bad_css_hits[:]
    r = _build_page(url)
    if bad_css_hits and retry:
        cp = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest())
        if os.path.exists(cp):
            os.remove(cp)
        print("  refetching fresh html for", url, flush=True)
        del bad_css_hits[:]
        r = _build_page(url)
        if bad_css_hits:
            failed.extend(bad_css_hits)
    return r


def _build_page(url):
    src = fetch(url)
    if not src or "<body" not in src:
        failed.append(url)
        return None
    head = src[: src.find("<body")]
    bstart = src.find("<body")
    body_tag = src[bstart : src.find(">", bstart) + 1]
    body = src[src.find(">", bstart) + 1 : src.rfind("</body>")]

    # ---- css (in document order, head + body)
    parts = []
    for m in re.finditer(r"<link\b[^>]*rel=['\"]stylesheet['\"][^>]*>|<style\b([^>]*)>(.*?)</style>", head + body, re.S | re.I):
        tag = m.group(0)
        if tag.startswith("<link"):
            id_ = attr(tag, "id") or ""
            if id_.startswith(SKIP_CSS_IDS):
                continue
            if id_.startswith("woocommerce") and not re.search(r"/(product|shop|cart|checkout)", url):
                continue
            href = attr(tag, "href")
            if not href:
                continue
            parts.append((attr(tag, "media") or "all", get_css_file(href, id_)))
        else:
            if m.start() >= len(head):
                continue  # body <style> stays inline
            sattrs = m.group(1) or ""
            if re.search(r"id=['\"](?:" + "|".join(SKIP_STYLE_IDS) + ")", sattrs):
                continue
            parts.append(("all", process_css(m.group(2), url)))
    page_parts[url] = parts

    # ---- head meta
    title = re.search(r"<title>(.*?)</title>", head, re.S)
    title = title.group(1).strip() if title else ""
    keep = "\n".join(m.group(0) for m in HEAD_KEEP.finditer(head))
    keep = localize_uploads_head(keep)
    lcp = ""

    # ---- body: split header/footer/popup into includes
    body = clean_body(body)
    regions = {}
    for kind in ("header", "footer", "popup"):
        while True:
            r = split_region(body, kind)
            if not r:
                break
            chunk = body[r[0] : r[1]]
            regions.setdefault(kind, "")
            regions[kind] += chunk
            body = body[: r[0]] + f"<!--@{kind}-->" + body[r[1] :]
    body = rewrite_links(body)
    for k in regions:
        regions[k] = rewrite_links(regions[k])
        regions[k] = re.sub(r"\s*\b(?:current-menu-item|current_page_item|current-menu-ancestor|current-menu-parent|current_page_parent|current_page_ancestor|current-page-ancestor|current-page-parent|page_item|page-item-\d+|elementor-item-active)\b", "", regions[k])
        regions[k] = regions[k].replace(' aria-current="page"', "")
        regions[k] = re.sub(r'<input type="hidden" name="(?:referer_title|queried_id|post_id)" value="[^"]*"\s*/?>', "", regions[k])
        # WordPress puts the current page/product name in the logo's title attribute -> 1 header per page
        regions[k] = re.sub(r"(<img\b[^>]*?)\s+title=\"[^\"]*\"", r"\1", regions[k])
        regions[k] = re.sub(r'class="\s+', 'class="', regions[k])
        regions[k] = re.sub(r'(class="[^"]*?)\s+"', r'\1"', regions[k])
    body = one_h1_in_posts(fix_tif(body))
    body = lazyify(body)
    for k in regions:
        regions[k] = re.sub(r"<img\b", '<img decoding="async"', re.sub(r'\s(?:loading|decoding|fetchpriority)="[^"]*"', "", regions[k]))

    inc = {}
    for k, v in regions.items():
        h = hashlib.sha1(v.encode()).hexdigest()[:8]
        name = f"{k}-{h}.php"
        with lock:
            if name not in shared:
                shared[name] = v
                os.makedirs(OUT + "/includes", exist_ok=True)
                with open(f"{OUT}/includes/{name}", "w", encoding="utf-8") as f:
                    f.write(v)
        inc[k] = name

    rel = url_to_dir(url)
    depth = 0 if rel == "" else rel.count("/") + 1
    body_cls = attr(body_tag, "class") or ""
    body_cls = re.sub(r"\s+", " ", body_cls)

    def include(k):
        return f"<?php include __DIR__ . '{'/..' * depth}/includes/{inc[k]}'; ?>" if k in inc else ""

    body = re.sub(r"(?:<!--@header-->)+", lambda m: include("header"), body, count=1)
    body = body.replace("<!--@header-->", "")
    body = re.sub(r"(?:<!--@footer-->)+", lambda m: include("footer"), body, count=1)
    body = body.replace("<!--@footer-->", "")
    body = re.sub(r"(?:<!--@popup-->)+", lambda m: include("popup"), body, count=1)
    body = body.replace("<!--@popup-->", "")
    body = re.sub(r"\n\s*\n+", "\n", body)

    # preload hero image if first image is a css background? (left to browser)
    page = f"""<!doctype html>
<html lang="en-US">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{keep}
<!--@css-->
<link rel="stylesheet" href="/assets/css/fix.css">
<script src="/assets/js/main.js" defer></script>
</head>
<body class="{body_cls}">
{body}
</body>
</html>
"""
    dst = os.path.join(OUT, rel, "index.php") if rel else os.path.join(OUT, "index.php")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(page)
    page_files[url] = dst
    return rel


page_parts = {}
page_files = {}


def phash(part):
    return hashlib.sha1((part[0] + "\0" + part[1]).encode()).hexdigest()


def finish_css():
    """Shared core.css (parts used by most pages, cached across the site) + small per-page bundle."""
    core_path = os.path.join(OUT, "includes", "core.json")
    # A stylesheet that occurs twice on a page (e.g. the site's custom design CSS is printed both
    # early and at the very end) takes effect at its LAST position: keep only that one, otherwise
    # dedupe would move it before the kit/base CSS it is meant to override.
    for url in list(page_parts):
        parts, seen_h, kept = page_parts[url], set(), []
        for p in reversed(parts):
            h = phash(p)
            if h not in seen_h:
                seen_h.add(h)
                kept.append(p)
        page_parts[url] = kept[::-1]
    if os.path.exists(core_path):
        core = set(json.load(open(core_path)))
    else:
        freq = {}
        order = []
        for parts in page_parts.values():
            for p in parts:
                h = phash(p)
                if h not in freq:
                    freq[h] = 0
                    order.append(p)
                freq[h] += 1
        n = len(page_parts)
        core_parts = [p for p in order if freq[phash(p)] >= max(2, n * 0.5)]
        core = {phash(p) for p in core_parts}
        # Keep the cascade order of the original pages: shared parts that normally come AFTER the
        # page's own CSS (the site's custom design layer, inline overrides) go to core-late.css,
        # loaded after the page bundle. Otherwise the page bundle's base/kit rules would override them.
        late_votes, seen = {}, {}
        for parts in page_parts.values():
            hs = [phash(p) for p in parts]
            first_own = next((i for i, h in enumerate(hs) if h not in core), None)
            for i, h in enumerate(hs):
                if h in core:
                    seen[h] = seen.get(h, 0) + 1
                    if first_own is not None and i > first_own:
                        late_votes[h] = late_votes.get(h, 0) + 1
        late = {h for h in core if late_votes.get(h, 0) * 2 > seen.get(h, 0)}
        for name, sel in (("core.css", [p for p in core_parts if phash(p) not in late]),
                          ("core-late.css", [p for p in core_parts if phash(p) in late])):
            body = make_bundle(sel)
            os.replace(OUT + body, OUT + "/assets/css/" + name)
            bundles.pop(body, None)
        json.dump({"core": sorted(core), "late": sorted(late)}, open(core_path, "w"))
    if isinstance(core, set) and os.path.exists(core_path):
        data = json.load(open(core_path))
        if isinstance(data, dict):
            core, late = set(data["core"]), set(data["late"])
        else:
            late = set()
    for url, parts in page_parts.items():
        rest = [p for p in parts if phash(p) not in core]
        tags = '<link rel="stylesheet" href="/assets/css/core.css">'
        if rest:
            tags += f'\n<link rel="stylesheet" href="{make_bundle(rest)}">'
        if late:
            tags += '\n<link rel="stylesheet" href="/assets/css/core-late.css">'
        f = page_files[url]
        t = open(f, encoding="utf-8").read().replace("<!--@css-->", tags)
        open(f, "w", encoding="utf-8").write(t)


def localize_uploads_head(text):
    # only icons need local copies; og/canonical stay absolute for SEO
    def rep(m):
        tag = m.group(0)
        if re.search(r"rel=['\"](?:icon|apple-touch-icon)", tag):
            return localize_uploads(tag)
        return tag

    return re.sub(r"<link[^>]*>", rep, text)


# ---------------------------------------------------------------- main
def main():
    urls = []
    if MODE in ("pages", "all"):
        urls += sitemap("page")
    if MODE in ("posts", "all"):
        urls += sitemap("post")
    if MODE in ("products", "all"):
        urls += sitemap("product")
    if MODE in ("extra", "all"):
        # live pages that are not in the sitemaps but are linked from the site (archives, pagination)
        lst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra-urls.txt")
        if os.path.exists(lst):
            urls += [ORIGIN + l.strip() for l in open(lst, encoding="utf-8-sig") if l.strip() and not l.strip().startswith("#")]
    if MODE.startswith("http"):
        urls = [MODE]
    if LIMIT:
        urls = urls[:LIMIT]
    print(f"{len(urls)} urls", flush=True)

    # fetch HTML in parallel (cached), then build
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(fetch, urls))
    built = []
    for i, u in enumerate(urls):
        try:
            r = build_page(u)
            if r is not None:
                built.append(r)
        except Exception as e:
            print("ERR", u, e, flush=True)
            failed.append(u)
        if i % 25 == 0:
            print(f"built {i}/{len(urls)}", flush=True)
    os.makedirs(os.path.join(OUT, "includes"), exist_ok=True)
    finish_css()
    download_all_assets()

    # record built urls (for sitemap)
    os.makedirs(os.path.join(OUT, "includes"), exist_ok=True)
    lst = os.path.join(OUT, "includes", "urls.txt")
    prev = set()
    if os.path.exists(lst):
        prev = set(open(lst, encoding="utf-8").read().split())
    prev |= {("/" + b + "/") if b else "/" for b in built}
    with open(lst, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(prev)))
    print(f"done: {len(built)} pages, {len(shared)} includes, {len(bundles)} css bundles, {len(failed)} failed")
    for x in failed[:40]:
        print("  FAIL", x)


if __name__ == "__main__":
    main()
