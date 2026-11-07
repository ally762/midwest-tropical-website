"""Restore blog article bodies.

On the live site every blog post renders without its article (broken single-post template),
but the text is still in WordPress. This pulls title/date/featured image/content from the
public REST API and puts the article into each generated post page (before "Keep reading").

usage: python -I tools/restore_posts.py <site dir> <cache dir>
"""
import concurrent.futures as cf
import datetime
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

OUT, CACHE = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
ORIGIN = "https://www.midwest-tropical.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def to_uri(url):
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~"),
                                    urllib.parse.quote(p.query, safe="=&%/:+,;-._~"), ""))


def get(url, binary=False):
    cp = os.path.join(CACHE, "api-" + hashlib.sha1(url.encode()).hexdigest())
    url = to_uri(url)
    if os.path.exists(cp) and os.path.getsize(cp) > 0:
        data = open(cp, "rb").read()
        return data if binary else data.decode("utf-8")
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                data = r.read()
            if data:
                open(cp, "wb").write(data)
                return data if binary else data.decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            time.sleep(2 + 3 * i)
        except Exception:
            time.sleep(2 + 3 * i)
    return None


# ---------------------------------------------------------------- fetch all posts
posts = []
page = 1
while True:
    q = (f"{ORIGIN}/wp-json/wp/v2/posts?per_page=100&page={page}&orderby=id&order=asc"
         "&_embed=wp:featuredmedia&_fields=id,slug,link,title,date,modified,content,_links,_embedded")
    txt = get(q)
    if not txt:
        break
    batch = json.loads(txt)
    if not isinstance(batch, list) or not batch:
        break
    posts += batch
    if len(batch) < 100:
        break
    page += 1
print("posts from API:", len(posts))

# ---------------------------------------------------------------- media localisation
to_download = {}
UP = re.compile(r"(?:https?:)?//(?:www\.)?midwest-tropical\.com(/wp-content/uploads/[^\s\"'<>,?#]+?\.(?:jpe?g|png|gif|webp|avif|svg|pdf|mp4))(?:\?[^\s\"'<>,]*)?(?=[\s\"'<>,]|$)", re.I)


def localize(s):
    def rep(m):
        # same safe local file name rule as build.py (non-ASCII etc. -> "_"), so both steps agree
        local = re.sub(r"[^A-Za-z0-9_./%-]", "_", urllib.parse.unquote(m.group(1)))
        to_download[local] = ORIGIN + urllib.parse.unquote(m.group(1))
        return local
    s = UP.sub(rep, s)
    return re.sub(r'(href)=(["\'])https?://(?:www\.)?midwest-tropical\.com(?=[/"\'#?])/?', r"\1=\2/", s)


def clean_content(c, title):
    c = re.sub(r"<!--.*?-->", "", c, flags=re.S)
    c = re.sub(r"<script\b.*?</script>", "", c, flags=re.S | re.I)
    # the article often repeats its own title as the first heading: drop that duplicate
    # (also when it is wrapped in Elementor containers, so look at the first heading in the opening part)
    m = re.search(r"<(h[1-3])\b[^>]*>(.*?)</\1>", c[:6000], re.S)
    norm = lambda s: re.sub(r"[^a-z0-9]", "", html.unescape(re.sub(r"<[^>]+>", "", s)).lower())
    if m and norm(m.group(2)) == norm(title):
        c = c[: m.start()] + c[m.end():]
    c = re.sub(r"<h1(\b[^>]*)>(.*?)</h1>", r"<h2\1>\2</h2>", c, flags=re.S)  # one H1 per page
    c = re.sub(r"<img\b(?![^>]*\bloading=)", '<img loading="lazy" decoding="async"', c)
    c = re.sub(r"<iframe\b(?![^>]*\bloading=)", '<iframe loading="lazy"', c)
    return localize(c)


restored, skipped, notfound = 0, 0, 0
for p in posts:
    slug_path = urllib.parse.urlsplit(p["link"]).path.strip("/")
    f = os.path.join(OUT, slug_path, "index.php")
    if not os.path.exists(f):
        notfound += 1
        continue
    t = open(f, encoding="utf-8").read()
    if "mt-article" in t or "<h1" in t:
        skipped += 1
        continue
    hm = re.search(r"<\?php include __DIR__ \. '[^']*/includes/header-[0-9a-f]+\.php'; \?>", t)
    if not hm:
        skipped += 1
        continue
    title = p["title"]["rendered"]
    date = datetime.datetime.fromisoformat(p["date"])
    # Some posts (built with Elementor) DO show their article on the live site, just without an H1/title band:
    # give those only the band + date, never a second copy of the text (duplicate content).
    em = re.search(r'<div data-elementor-type="wp-post"[^>]*>(.*?)<\?php include', t, re.S)
    if em and len(re.sub(r"<[^>]+>", " ", em.group(1)).split()) > 150:
        head = (f'\n<main id="content" class="site-main post mt-article mt-article--head">'
                f'<div class="page-header"><h1 class="entry-title">{title}</h1></div>'
                f'<div class="page-content"><p class="mt-article-meta"><time datetime="{p["date"]}">{date.strftime("%B")} {date.day}, {date.year}</time></p></div></main>\n')
        t = t[: hm.end()] + head + t[hm.end():]
        open(f, "w", encoding="utf-8").write(t)
        restored_head = globals().setdefault("restored_head", [0])
        restored_head[0] += 1
        continue
    hero = ""
    media = (p.get("_embedded") or {}).get("wp:featuredmedia") or []
    if media and isinstance(media[0], dict) and media[0].get("source_url"):
        m0 = media[0]
        sizes = (m0.get("media_details") or {}).get("sizes") or {}
        src = (sizes.get("large") or sizes.get("full") or {}).get("source_url") or m0["source_url"]
        w = (sizes.get("large") or sizes.get("full") or {}).get("width") or ""
        h = (sizes.get("large") or sizes.get("full") or {}).get("height") or ""
        srcset = ", ".join(f'{v["source_url"]} {v["width"]}w' for k, v in sizes.items()
                           if isinstance(v, dict) and v.get("width") and k not in ("thumbnail",) and v.get("source_url"))
        alt = html.escape(m0.get("alt_text") or html.unescape(re.sub(r"<[^>]+>", "", title)), quote=True)
        hero = localize(
            f'<figure class="mt-article-hero"><img src="{src}"' + (f' srcset="{srcset}" sizes="(max-width: 900px) 100vw, 860px"' if srcset else "")
            + (f' width="{w}" height="{h}"' if w and h else "") + f' alt="{alt}" fetchpriority="high" decoding="async"></figure>')
    article = (
        f'\n<main id="content" class="site-main post mt-article">'
        f'<div class="page-header"><h1 class="entry-title">{title}</h1></div>'
        f'<div class="page-content"><p class="mt-article-meta"><time datetime="{p["date"]}">{date.strftime("%B")} {date.day}, {date.year}</time></p>'
        f'{hero}<div class="mt-article-body">{clean_content(p["content"]["rendered"], title)}</div></div></main>\n'
    )
    t = t[: hm.end()] + article + t[hm.end():]
    open(f, "w", encoding="utf-8").write(t)
    restored += 1

# ---------------------------------------------------------------- download article images
todo = [(l, s) for l, s in to_download.items() if not (os.path.exists(OUT + l) and os.path.getsize(OUT + l) > 0)]


def dl(item):
    local, src = item
    data = get(src, binary=True)
    if data and not data[:200].lstrip().lower().startswith((b"<!doctype", b"<html")):
        os.makedirs(os.path.dirname(OUT + local), exist_ok=True)
        open(OUT + local, "wb").write(data)
        return True
    return False


with cf.ThreadPoolExecutor(6) as ex:
    ok = sum(ex.map(dl, todo))
print(f"articles restored: {restored}, title-band only (article already on page): {globals().get('restored_head', [0])[0]}, "
      f"already had H1: {skipped}, no page for post: {notfound}, "
      f"article images: {len(to_download)} referenced, {ok}/{len(todo)} downloaded")
