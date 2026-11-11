"""Copy hand-written files (site-src) into the build, write sitemap.xml and 404.php.
usage: python -I tools/finalize.py site site-src"""
import os
import re
import shutil
import sys

OUT, SRC = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
ORIGIN = "https://www.midwest-tropical.com"

for dp, dn, fn in os.walk(SRC):
    for f in fn:
        s = os.path.join(dp, f)
        d = os.path.join(OUT, os.path.relpath(s, SRC))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)

# Theme-template pages whose title was hidden had no H1 and no title band: add the band with the
# page's own SEO title (from <title>, minus the site-name suffix) so every page has the same frame + one H1.
def page_name(t):
    title = re.search(r"<title>(.*?)</title>", t, re.S)
    return re.split(r"\s+[-|–]\s+Midwest Tropical.*$", title.group(1).strip())[0].strip() if title else ""


INC_RE = r"<\?php include __DIR__ \. '[^']*/includes/%s-[0-9a-f]+\.php'; \?>"


def wrap_classic(t):
    """Classic-editor text dropped straight into a full-width template (no wrapper at all):
    wrap it in the theme frame so it gets the same title band / width as every other page."""
    h = re.search(INC_RE % "header", t)
    f = re.search(INC_RE % "footer", t)
    if not h or not f or f.start() < h.end():
        return t
    mid = t[h.end(): f.start()]
    if "data-elementor-type=" in mid or "<main" in mid or not re.search(r"<(p|h2|h3|ul)\b", mid):
        return t
    h1 = "" if "<h1" in mid else f'<div class="page-header"><h1 class="entry-title">{page_name(t)}</h1></div>'
    return t[: h.end()] + f'\n<main id="content" class="site-main page mt-classic">{h1}<div class="page-content">' + mid + "</div></main>\n" + t[f.start():]


def add_title_band(t):
    t = wrap_classic(t)
    if 'class="page-header"' in t or "<h1" in t:
        return t
    m = re.search(r'(<main id="content" class="site-main[^"]*"[^>]*>)\s*(<div class="page-content">)', t)
    if not m:
        return t
    band = f'<div class="page-header"><h1 class="entry-title">{page_name(t)}</h1></div>'
    return t[: m.end(1)] + band + t[m.start(2):]


# Gallery / portfolio filters: on the live site the cards carry no category classes, so every filter
# button shows nothing. Each product page knows its tags: copy them onto the matching card (same post-ID)
# as mt-tag-<slug> classes; main.js filters by those.
tags_by_id = {}
prod_dir = os.path.join(OUT, "product")
if os.path.isdir(prod_dir):
    for slug in os.listdir(prod_dir):
        f = os.path.join(prod_dir, slug, "index.php")
        if not os.path.exists(f):
            continue
        t = open(f, encoding="utf-8", errors="replace").read()
        m = re.search(r'class="[^"]*\bpost-(\d+)\b[^"]*\btype-product\b([^"]*)"', t)
        if m:
            tags_by_id[m.group(1)] = sorted(set(re.findall(r"product_tag-([\w-]+)", m.group(0))))


def tag_cards(t):
    def rep(m):
        cls = m.group(1)
        if "mt-tag-" in cls:  # already tagged (finalize can run more than once)
            return m.group(0)
        pid = re.search(r"\bpost-(\d+)\b", cls)
        tags = tags_by_id.get(pid.group(1), []) if pid else []
        extra = " ".join("mt-tag-" + s for s in tags)
        return f'<article class="{cls}{(" " + extra) if extra else ""}"'
    return re.sub(r'<article class="(elementor-portfolio-item[^"]*)"', rep, t)


# Project-gallery grid (".mt-lg-card", up to 648 cards on every blog post): the live site loads the
# full-size originals (1448px+) into ~416px cards. Use a ~600px variant that exists locally instead,
# and give each link the image's alt as its name (the live site adds that with JS).
UPL = os.path.join(OUT, "wp-content", "uploads")
_variants = {}
if os.path.isdir(UPL):
    for _f in os.listdir(UPL):
        _m = re.match(r"(.+)-(\d+)x(\d+)\.(png|jpe?g|webp|avif)$", _f, re.I)
        if _m:
            _variants.setdefault((_m.group(1), _m.group(4).lower()), []).append((int(_m.group(2)), _f))


def small(path):
    """768px-wide copy (WordPress 'medium_large': always the whole picture scaled, never cropped;
    sizes like 640x480 or 600x600 can be hard crops). Falls back to 1024 wide."""
    m = re.match(r"/wp-content/uploads/(.+?)(?:-\d+x\d+)?\.(png|jpe?g|webp|avif)$", path, re.I)
    if not m:
        return None
    vs = dict(_variants.get((m.group(1), m.group(2).lower()), []))
    for w in (768, 1024):
        if w in vs:
            return "/wp-content/uploads/" + vs[w]
    # no safe smaller copy: use the original file (undo an earlier, possibly cropped, choice)
    orig = f"/wp-content/uploads/{m.group(1)}.{m.group(2)}"
    if orig != path and os.path.exists(os.path.join(UPL, f"{m.group(1)}.{m.group(2)}")):
        return orig
    return None


def lg_card(m):
    card = m.group(0)
    img = re.search(r'<img\b[^>]*\ssrc="([^"]+)"', card)
    alt = re.search(r'<img\b[^>]*\salt="([^"]*)"', card)
    if img:
        s = small(img.group(1))
        if s and s != img.group(1):
            card = card.replace(f'src="{img.group(1)}"', f'src="{s}"')
            wh = re.search(r"-(\d+)x(\d+)\.\w+$", s)
            card = re.sub(r'(<img\b[^>]*?)\swidth="\d+"\sheight="\d+"', r"\1", card)
            if wh:
                card = card.replace("<img ", f'<img width="{wh.group(1)}" height="{wh.group(2)}" ', 1)
            webp = s + ".webp"
            if os.path.exists(os.path.join(OUT, webp.lstrip("/").replace("/", os.sep))):
                card = re.sub(r'<source srcset="[^"]*"', f'<source srcset="{webp}"', card)
            else:
                card = re.sub(r"<source\b[^>]*>", "", card)
    # already resized by an earlier run: make sure the size attributes are there (no layout shift)
    cur = re.search(r'<img\b[^>]*\ssrc="[^"]*-(\d+)x(\d+)\.\w+"', card)
    if cur and not re.search(r"<img\b[^>]*\swidth=", card):
        card = card.replace("<img ", f'<img width="{cur.group(1)}" height="{cur.group(2)}" ', 1)
    if alt and "aria-label=" not in card[:200]:
        card = card.replace('<a class="mt-lg-card"', f'<a class="mt-lg-card" aria-label="{alt.group(1)}"', 1)
    return card


lg_pages = 0
for dp, dn, fn in os.walk(OUT):
    if os.sep + "wp-content" in dp or os.sep + "assets" in dp:
        continue
    if "index.php" in fn:
        p = os.path.join(dp, "index.php")
        t = open(p, encoding="utf-8", errors="replace").read()
        if "mt-lg-card" in t:
            n = re.sub(r'<a class="mt-lg-card"[^>]*>.*?</a>', lg_card, t, flags=re.S)
            if n != t:
                open(p, "w", encoding="utf-8").write(n)
                lg_pages += 1
print("project-gallery cards resized on", lg_pages, "pages")


# PDF flipbook: the live site uses a flipbook plugin; replace its placeholder with our own viewer
# (main.js + pdf.js). The plugin's PDF is the page's own .pdf link (the plugin options are not kept).
def flipbook(t):
    def rep(m):
        before = t[: m.start()]
        pdfs = re.findall(r'href="([^"]+\.pdf)"', before) or re.findall(r'href="([^"]+\.pdf)"', t)
        if not pdfs:
            return m.group(0)
        src = pdfs[-1]
        title = re.search(r'data-title="([^"]*)"', m.group(0))
        title = title.group(1).replace("-", " ").title() if title else "Catalog"
        return (f'<div class="mt-flipbook" data-pdf="{src}" data-title="{title}">'
                f'<a class="mt-fb-fallback" href="{src}">Open the catalog (PDF)</a></div>')
    return re.sub(r'<div class="_df_book[^"]*"[^>]*>\s*</div>', rep, t)


fb_pages = 0
for dp, dn, fn in os.walk(OUT):
    if os.sep + "wp-content" in dp or os.sep + "assets" in dp:
        continue
    if "index.php" in fn:
        p = os.path.join(dp, "index.php")
        t = open(p, encoding="utf-8", errors="replace").read()
        if "_df_book" in t:
            n = flipbook(t)
            if n != t:
                open(p, "w", encoding="utf-8").write(n)
                fb_pages += 1
print("pdf flipbooks on", fb_pages, "pages")

tagged_pages = 0
for dp, dn, fn in os.walk(OUT):
    if os.sep + "wp-content" in dp or os.sep + "assets" in dp:
        continue
    for f in fn:
        if f == "index.php":
            p = os.path.join(dp, f)
            t = open(p, encoding="utf-8", errors="replace").read()
            if "elementor-portfolio-item" in t:
                n = tag_cards(t)
                if n != t:
                    open(p, "w", encoding="utf-8").write(n)
                    tagged_pages += 1
print("portfolio cards tagged on", tagged_pages, "pages (", len(tags_by_id), "products with tags )")

# preload the main text font (Quicksand, latin) so the first paint already uses it
preload = ""
core = os.path.join(OUT, "assets", "css", "core.css")
if os.path.exists(core):
    cc = open(core, encoding="utf-8").read()
    late_css = os.path.join(OUT, "assets", "css", "core-late.css")
    if os.path.exists(late_css):
        cc += open(late_css, encoding="utf-8").read()
    for blk in re.findall(r"@font-face\s*{[^}]*}", cc):
        if re.search(r"font-family:\s*['\"]?Quicksand", blk, re.I) and "U+0000-00FF" in blk.upper():
            u = re.search(r"url\(([^)]+\.woff2)\)", blk)
            if u:
                preload = f'<link rel="preload" href="{u.group(1)}" as="font" type="font/woff2" crossorigin>\n'
                break

banded = 0
for dp, dn, fn in os.walk(OUT):
    if os.sep + "wp-content" in dp or os.sep + "assets" in dp or os.sep + "includes" in dp:
        continue
    for f in fn:
        if f == "index.php":
            p = os.path.join(dp, f)
            t = open(p, encoding="utf-8").read()
            n = add_title_band(t)
            if preload and 'as="font"' not in n:
                n = n.replace('<link rel="stylesheet" href="/assets/css/core.css', preload + '<link rel="stylesheet" href="/assets/css/core.css', 1)
            if n != t:
                open(p, "w", encoding="utf-8").write(n)
                banded += 1
print("title band + H1 added to", banded, "theme pages that had none")

# drop srcset candidates / image refs whose file is missing (sizes that 404 on the live server too)
def exists(u):
    u = u.split("?")[0].split("#")[0]
    if not u.startswith("/") or u.startswith("//"):
        return True
    p = OUT + urllib.parse.unquote(u)
    return os.path.exists(p) and os.path.getsize(p) > 0


def fix_img(m):
    tag = m.group(0)
    ss = re.search(r'\ssrcset="([^"]*)"', tag)
    good = []
    if ss:
        for cand in ss.group(1).split(","):
            parts = cand.strip().split()
            if parts and exists(parts[0]):
                good.append(" ".join(parts))
        tag = tag.replace(ss.group(0), (' srcset="' + ", ".join(good) + '"') if good else "")
        if not good:
            tag = re.sub(r'\ssizes="[^"]*"', "", tag)
    src = re.search(r'\ssrc="([^"]*)"', tag)
    if src and not exists(src.group(1)) and good:
        # missing main file: use the largest existing srcset entry
        best = sorted(good, key=lambda c: int(re.sub(r"\D", "", c.split()[-1]) or 0))[-1].split()[0]
        tag = tag.replace(src.group(0), f' src="{best}"')
    return tag


import urllib.parse
# Image paths are kept exactly as on the live site (/wp-content/uploads/...). Any file that could
# not be downloaded is listed in MISSING-IMAGES.txt; copying the client's wp-content/uploads folder
# from their hosting into site/wp-content/uploads fills those gaps with no HTML change needed.
def drop_bad_source(m):
    # <picture><source srcset="x.webp"> whose file is missing would win over the working <img>: drop it
    tag = m.group(0)
    ss = re.search(r'srcset="([^"]*)"', tag)
    if ss and any(not exists(c.strip().split(" ")[0]) for c in ss.group(1).split(",") if c.strip()):
        return ""
    return tag


missing = set()
dropped = 0
for dp, dn, fn in os.walk(OUT):
    if os.sep + "wp-content" in dp or os.sep + "assets" in dp:
        continue
    for f in fn:
        if f.endswith(".php") and f != "form-handler.php":
            pth = os.path.join(dp, f)
            t = open(pth, encoding="utf-8").read()
            n = re.sub(r"<source\b[^>]*>", drop_bad_source, t)
            if n != t:
                dropped += t.count("<source") - n.count("<source")
                open(pth, "w", encoding="utf-8").write(n)
                t = n
            for u in re.findall(r'(?:src|href|srcset)="([^"]+)"', t):
                for part in u.split(","):
                    p = part.strip().split(" ")[0]
                    if p.startswith("/wp-content/") and re.search(r"\.(jpe?g|png|gif|webp|avif|svg|mp4|pdf)$", p, re.I) and not exists(p):
                        missing.add(p)
with open(os.path.join(os.path.dirname(OUT), "MISSING-IMAGES.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(sorted(missing)))
print("missing media files:", len(missing), "| <source> tags dropped (fallback to <img>):", dropped)

# sitemap.xml – same URLs as the WordPress sitemaps
urls = open(os.path.join(OUT, "includes", "urls.txt"), encoding="utf-8").read().split()
# same set as the live sitemaps: archive / pagination pages exist but are not listed there
urls = [u for u in urls if not re.match(r"^/(shop/page/|product-category/|tag/|category/)", u)]
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    p = os.path.join(OUT, u.strip("/"), "index.php")
    mod = os.path.getmtime(p) if os.path.exists(p) else None
    xml.append(f"<url><loc>{ORIGIN}{u}</loc></url>")
xml.append("</urlset>")
open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(xml))

# 404.php built from the home page shell (same header/footer/css)
home = open(os.path.join(OUT, "index.php"), encoding="utf-8").read()
head, rest = home.split("</head>", 1)
head = re.sub(r"<title>.*?</title>", "<title>Page Not Found - Midwest Tropical</title>", head, flags=re.S)
head = re.sub(r"<meta name=\"robots\"[^>]*>", "", head)
head = re.sub(r"<(?:meta property|meta name=\"(?:description|twitter)|link rel=\"canonical|script type=\"application/ld)[^>]*?(?:/>|>(?:.*?</script>)?)", "", head, flags=re.S)
head = head.replace("<head>", '<head>\n<meta name="robots" content="noindex, follow">', 1)
inc = re.findall(r"<\?php include __DIR__ \. '[^']+'; \?>", rest)
header = next((i for i in inc if "/header-" in i), "")
footer = next((i for i in inc if "/footer-" in i), "")
popup = next((i for i in inc if "/popup-" in i), "")
body_cls = re.search(r'<body class="([^"]*)"', rest)
page = head + "</head>\n" + f'<body class="{body_cls.group(1) if body_cls else ""}">\n' + header + """
<?php http_response_code(404); ?>
<main id="content" style="max-width:900px;margin:0 auto;padding:80px 20px;text-align:center;font-family:Nunito,sans-serif">
<h1 style="font-size:42px;margin-bottom:16px">Page Not Found</h1>
<p style="font-size:18px;margin-bottom:28px">Sorry, the page you are looking for doesn't exist or has been moved.</p>
<p><a href="/" style="display:inline-block;padding:14px 28px;background:#3761A7;color:#fff;text-decoration:none;border-radius:3px">Back to Home</a>
&nbsp; <a href="/request-a-quote/" style="display:inline-block;padding:14px 28px;border:2px solid #3761A7;color:#3761A7;text-decoration:none;border-radius:3px">Request a Quote</a></p>
</main>
""" + footer + popup + "\n</body>\n</html>\n"
open(os.path.join(OUT, "404.php"), "w", encoding="utf-8").write(page)
print("finalized:", len(urls), "urls in sitemap")
