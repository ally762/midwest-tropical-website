"""Build assets/search.json: the index for the site's own search (replaces the Jetpack search plugin).

Each entry: [url, title, thumbnail, date (YYYY-MM-DD or ""), text]. main.js loads it the first
time someone searches and shows results in an overlay like the live site's.

usage: python -I tools/search_index.py site
"""
import html as H
import json
import os
import re
import sys

SITE = os.path.abspath(sys.argv[1])
UPL = os.path.join(SITE, "wp-content", "uploads")

# thumbnails: stem -> [(width, height, filename)]
variants = {}
if os.path.isdir(UPL):
    for f in os.listdir(UPL):
        m = re.match(r"(.+)-(\d+)x(\d+)\.(\w+)$", f)
        if m:
            variants.setdefault(m.group(1) + "." + m.group(4).lower(), []).append((int(m.group(2)), int(m.group(3)), f))


def thumb(url):
    if not url:
        return ""
    path = re.sub(r"^https?://[^/]+", "", url)
    if not path.startswith("/wp-content/uploads/"):
        return path
    name = path.rsplit("/", 1)[1]
    stem = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", name)
    vs = variants.get(stem.rsplit(".", 1)[0] + "." + stem.rsplit(".", 1)[1].lower(), [])
    sq = [v for v in vs if v[0] == v[1] and 250 <= v[0] <= 450]
    pick = sq[0] if sq else min((v for v in vs if 250 <= v[0] <= 900), key=lambda v: abs(v[0] - 400), default=None)
    chosen = pick[2] if pick else name
    if os.path.isdir(UPL) and not os.path.exists(os.path.join(UPL, chosen)):
        return ""  # file missing (also broken on the live site): show the "no image" tile
    return "/wp-content/uploads/" + chosen


def text_of(s):
    s = re.sub(r"<(script|style|noscript|svg|form|nav)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", H.unescape(s)).strip()


def meta(t, prop):
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), t)
    return H.unescape(m.group(1)) if m else ""


SKIP = re.compile(r"^/(shop/page/|product-category/|tag/|category/|page/\d+/|.*/page/\d+/|thank-you)")
urls = open(os.path.join(SITE, "includes", "urls.txt"), encoding="utf-8").read().split()
out = []
for u in urls:
    if SKIP.match(u):
        continue
    p = os.path.join(SITE, u.strip("/"), "index.php")
    if not os.path.exists(p):
        continue
    t = open(p, encoding="utf-8", errors="replace").read()
    if re.search(r'<meta name="robots" content="[^"]*noindex', t):
        continue
    body_cls = (re.search(r'<body class="([^"]*)"', t) or [None, ""])[1]
    h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", t, re.S)
    title = re.search(r"<title>(.*?)</title>", t, re.S)
    page_title = re.split(r"\s+[-|–]\s+Midwest Tropical.*$", H.unescape(title.group(1).strip()))[0] if title else ""
    if h1 and re.search(r"\b(single-post|single-product|postid-\d+)\b", body_cls):
        name = text_of(h1.group(1))
    else:
        name = page_title or (text_of(h1.group(1)) if h1 else u)
    # first image that really exists: share image, featured image, then images in the content
    cands = [meta(t, "og:image")]
    cands += re.findall(r'<img\b[^>]*\ssrc="(/wp-content/uploads/[^"]+)"[^>]*class="[^"]*wp-post-image', t)
    body_part = t.split("includes/header-", 1)[-1]
    cands += [c for c in re.findall(r'<img\b[^>]*\ssrc="(/wp-content/uploads/[^"]+)"', body_part)
              if not re.search(r"logo|Gallery-Banner|icon", c, re.I)][:6]
    img = next((c for c in cands if c and thumb(c)), "")
    date = (meta(t, "article:published_time") or meta(t, "og:updated_time"))[:10]
    # main content only: between the header and footer includes
    m = re.search(r"includes/header-[0-9a-f]+\.php'; \?>(.*)<\?php include __DIR__ \. '[^']*includes/footer-", t, re.S)
    main = text_of(m.group(1) if m else t).replace("Get A Free Water Feature Consultation & Price Estimate:", "")
    heads = " ".join(text_of(x) for x in re.findall(r"<h[23]\b[^>]*>(.*?)</h[23]>", m.group(1) if m else "", re.S))
    tags = " ".join(sorted(set(re.findall(r"product_tag-([\w-]+)", t)))).replace("-", " ")
    txt = " ".join(x for x in (meta(t, "description"), heads, tags, main[:400]) if x)
    out.append([u, name, thumb(img), date, re.sub(r"\s+", " ", txt)[:700]])

dst = os.path.join(SITE, "assets", "search.json")
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("search index:", len(out), "entries,", os.path.getsize(dst) // 1024, "KB")
