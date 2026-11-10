"""Content audit: is every piece of visible text from the live page present in our build?

For each URL in the live sitemaps (pages + products; blog posts are empty on the live site),
take the visible text of the live HTML (cached copy, header/footer/popup/scripts removed)
and check which of its words/sentences are missing from the built page.

usage: python -I tools/audit_content.py <cache dir>
writes: content-audit.txt
"""
import hashlib
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
CACHE = os.path.abspath(sys.argv[1])
ORIGIN = "https://www.midwest-tropical.com"


def cached(u):
    p = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest())
    return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None


def strip_region(body, kind):
    m = re.search(r'<(header|footer|div)\b[^>]*data-elementor-type="' + kind + r'"[^>]*>', body)
    if not m:
        return body
    tag, depth = m.group(1), 0
    for t in re.finditer(r"<(/?)" + tag + r"\b[^>]*>", body[m.start():]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return body[: m.start()] + body[m.start() + t.end():]
    return body


def visible_text(h):
    h = re.sub(r"<(script|style|noscript|svg|template|form)\b.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<!--.*?-->", " ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    return re.sub(r"\s+", " ", h).strip()


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if len(s.split()) >= 6]


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


sm_urls = []
for name in ("page", "post", "product"):
    x = cached(f"{ORIGIN}/{name}-sitemap.xml")
    if x:
        sm_urls += re.findall(r"<url>\s*<loc>([^<]+)</loc>", x)

rows, problems = [], []
for u in sm_urls:
    src = cached(u)
    path = u.replace(ORIGIN, "").strip("/")
    f = os.path.join(SITE, path, "index.php") if path else os.path.join(SITE, "index.php")
    if not src or not os.path.exists(f):
        problems.append(f"NOT BUILT / NOT CACHED: {u}")
        continue
    body = src[src.find("<body"):]
    for k in ("header", "footer", "popup"):
        body = strip_region(body, k)
    live_txt = visible_text(body)
    built = open(f, encoding="utf-8", errors="replace").read()
    built_txt = norm(visible_text(re.sub(r"<\?php.*?\?>", " ", built, flags=re.S)))
    sents = sentences(live_txt)
    miss = [s for s in sents if norm(s) and norm(s) not in built_txt]
    lw, bw = len(live_txt.split()), len(built_txt.split())
    rows.append((len(miss), u, lw, bw, miss[:3]))

rows.sort(key=lambda r: -r[0])
out = [f"pages checked: {len(rows)}   pages with missing sentences: {sum(1 for r in rows if r[0])}"]
out += problems
for n, u, lw, bw, ex in rows:
    if n:
        out.append(f"\n{n} missing sentences | live words {lw} / built words {bw} | {u.replace(ORIGIN, '')}")
        out += [f"   - {e[:160]}" for e in ex]
open(os.path.join(ROOT, "content-audit.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:80]))
