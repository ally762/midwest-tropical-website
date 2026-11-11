"""Build docs/ : a static HTML preview of site/ for GitHub Pages (Pages can't run PHP).

- PHP includes are resolved into plain index.html files.
- Root-relative links (/airports/, /assets/...) become relative, so the demo works under
  https://<user>.github.io/<repo>/ without knowing the user/repo name.
- Images are not in the repo (1.8 GB): they load from the live site's same paths.
- Every page gets <meta name="robots" content="noindex, nofollow"> so Google never indexes
  this preview as duplicate content (canonical tags already point to the real domain).

usage: python -I tools/make_pages_demo.py
"""
import os
import posixpath
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "docs")
LIVE = "https://www.midwest-tropical.com"
INC = re.compile(r"<\?php include __DIR__ \. '([^']+)'; \?>")
MEDIA = re.compile(r"(?<![\w:])(\\?/)wp-content(\\?/)(uploads|grand-media)(\\?/)")

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)


FONT_RE = re.compile(r"/wp-content/(?:uploads|grand-media)/[^\s\"'()<>,?#]+\.(?:woff2?|ttf|otf|eot)", re.I)


def keep_fonts_local(s):
    """Fonts can't be loaded cross-site (CORS), so copy the few font files into docs/ and keep them local."""
    for f in set(FONT_RE.findall(s)):
        src = os.path.join(SITE, f.lstrip("/").replace("/", os.sep))
        dst = os.path.join(OUT, f.lstrip("/").replace("/", os.sep))
        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return s


import json

_MAP_FILE = os.path.join(SITE, "includes", "media-map.json")
MEDIA_MAP = json.load(open(_MAP_FILE, encoding="utf-8")) if os.path.exists(_MAP_FILE) else {}
# longest first so a path is never replaced inside a longer one
_MAP_ITEMS = sorted(MEDIA_MAP.items(), key=lambda kv: -len(kv[0]))


def live_media(s):
    # /wp-content/uploads/...  and JSON-escaped \/wp-content\/uploads\/...  -> live site (except fonts)
    keep_fonts_local(s)
    # files saved under a safe local name: point at the real live file name
    for local, real in _MAP_ITEMS:
        if local in s:
            s = re.sub(r'(?<![\w:/])' + re.escape(local) + r'(?=[\s"\'),]|$)', real, s)

    def rep(m):
        tail = s[m.end(): m.end() + 300]
        if re.match(r"[^\s\"'()<>,?#]+\.(?:woff2?|ttf|otf|eot)", tail, re.I):
            return m.group(0)
        return (LIVE.replace("/", "\\/") if m.group(1) == "\\/" else LIVE) + m.group(0)

    return MEDIA.sub(rep, s)


def rel(from_dir, target):
    """root-relative target ('/a/b/') -> relative path from page directory from_dir ('x/y')"""
    t = target.lstrip("/")
    r = posixpath.relpath("/" + t if t else "/", "/" + from_dir if from_dir else "/")
    if target.endswith("/") and not r.endswith("/"):
        r += "/"
    if r == "./" or r == ".":
        r = "./"
    return r


def relativize(html, page_dir):
    def attr(m):
        name, q, val = m.group(1), m.group(2), m.group(3)
        if val.startswith("//") or not val.startswith("/"):
            return m.group(0)
        return f"{name}={q}{rel(page_dir, val)}{q}"

    html = re.sub(r'\b(href|src|action|poster|data-src)=(["\'])(/[^"\']*)\2', attr, html)

    def srcset(m):
        parts = []
        for c in m.group(2).split(","):
            c = c.strip()
            if not c:
                continue
            u, *d = c.split()
            if u.startswith("/") and not u.startswith("//"):
                u = rel(page_dir, u)
            parts.append(" ".join([u, *d]))
        return f'{m.group(1)}="{", ".join(parts)}"'

    html = re.sub(r"\b(srcset|imagesrcset)=\"([^\"]*)\"", srcset, html)
    html = re.sub(r"url\((['\"]?)(/(?!/)[^)'\"]*)\1\)", lambda m: f"url({m.group(1)}{rel(page_dir, m.group(2))}{m.group(1)})", html)
    return html


def render(php_path):
    src = open(php_path, encoding="utf-8").read()
    base = os.path.dirname(php_path)

    def inc(m):
        p = os.path.normpath(base + m.group(1))
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

    src = INC.sub(inc, src)
    return re.sub(r"<\?php.*?\?>", "", src, flags=re.S)


pages = 0
for dp, dn, fn in os.walk(SITE):
    relp = os.path.relpath(dp, SITE).replace(os.sep, "/")
    relp = "" if relp == "." else relp
    if relp.split("/")[0] in ("wp-content", "assets", "includes"):
        dn[:] = []
        continue
    for f in fn:
        if f not in ("index.php", "404.php"):
            continue
        html = render(os.path.join(dp, f))
        html = live_media(html)
        html = re.sub(r'<meta name="robots"[^>]*>', "", html)
        html = html.replace("<head>", '<head>\n<meta name="robots" content="noindex, nofollow">', 1)
        html = relativize(html, relp)
        out_name = "404.html" if f == "404.php" else "index.html"
        dst = os.path.join(OUT, relp, out_name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(html)
        pages += 1

# assets: css/js/fonts. CSS url(/assets/...) -> relative, url(/wp-content/...) -> live site
shutil.copytree(os.path.join(SITE, "assets"), os.path.join(OUT, "assets"))
for dp, dn, fn in os.walk(os.path.join(OUT, "assets", "css")):
    for f in fn:
        if f.endswith(".css"):
            p = os.path.join(dp, f)
            css = live_media(open(p, encoding="utf-8").read())
            css = re.sub(r"url\((['\"]?)(/(?!/)[^)'\"]*)\1\)", lambda m: f"url({m.group(1)}{rel('assets/css', m.group(2))}{m.group(1)})", css)
            open(p, "w", encoding="utf-8").write(css)
# search index: thumbnails use the real (live) file names; main.js prefixes the live origin on github.io
_sj = os.path.join(OUT, "assets", "search.json")
if os.path.exists(_sj):
    rows = json.load(open(_sj, encoding="utf-8"))
    for r in rows:
        r[2] = MEDIA_MAP.get(r[2], r[2]) if r[2] else ""
    json.dump(rows, open(_sj, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
open(os.path.join(OUT, ".nojekyll"), "w").close()  # serve files as-is (no Jekyll processing)

# ---- redirects (GitHub Pages can't send 301s; mirror the live site's behaviour with tiny pages)
PAGES_BASE = "/midwest-tropical-website/docs/"   # https://ally762.github.io/midwest-tropical-website/docs/


def redirect_page(target):
    return ('<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0; url={target}"><script>location.replace("{target}")</script>'
            f'</head><body><a href="{target}">Continue</a></body></html>')


for old, new in (("waterwalls/", "../water-walls/"), ("contact-us-2/", "../contact-us/"),
                 ("materials/wire-mesh-water-features-2/", "../wire-mesh-water-features/")):
    os.makedirs(os.path.join(OUT, old), exist_ok=True)
    open(os.path.join(OUT, old, "index.html"), "w", encoding="utf-8").write(redirect_page(new))
# Pages serves /404.html from the publishing root (repo root) for any unknown URL:
# like the live site (301 -> home), send it to the demo home page.
open(os.path.join(ROOT, "404.html"), "w", encoding="utf-8").write(redirect_page(PAGES_BASE))
os.remove(os.path.join(OUT, "404.html")) if os.path.exists(os.path.join(OUT, "404.html")) else None
print(f"docs/: {pages} pages")
