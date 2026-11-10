"""SEO URL audit: every live URL must exist in site/, and no internal link may 404.

1. Fetch the CURRENT live sitemaps (no cache) and compare with the pages in site/.
2. Collect every internal link in the built pages + includes and check that the target exists.
3. For link targets that don't exist locally, ask the live site whether they are real pages (200)
   so they can be added to the build.

usage: python -I tools/audit_urls.py [--check-live]
writes: url-audit.txt in the project root
"""
import collections
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
ORIGIN = "https://www.midwest-tropical.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
CHECK_LIVE = "--check-live" in sys.argv


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")


def exists(path):
    """does a root-relative URL path resolve to a file in site/ ?"""
    p = urllib.parse.unquote(path.split("#")[0].split("?")[0])
    fs = os.path.join(SITE, p.lstrip("/").replace("/", os.sep))
    if p.endswith("/") or p == "":
        return os.path.exists(os.path.join(fs, "index.php")) or os.path.exists(os.path.join(fs, "index.html"))
    return os.path.exists(fs) or os.path.exists(os.path.join(fs, "index.php"))


out = []
# ---------------------------------------------------------------- 1. sitemaps
_, _, idx = get(ORIGIN + "/sitemap_index.xml")
live = {}
for sm in re.findall(r"<loc>([^<]+)</loc>", idx):
    _, _, x = get(sm)
    for loc in re.findall(r"<url>\s*<loc>([^<]+)</loc>", x):
        live[urllib.parse.urlsplit(loc).path or "/"] = sm.rsplit("/", 1)[-1]
built = set()
for dp, dn, fn in os.walk(SITE):
    rel = os.path.relpath(dp, SITE).replace(os.sep, "/")
    if rel.split("/")[0] in ("wp-content", "assets", "includes"):
        dn[:] = []
        continue
    if "index.php" in fn:
        built.add("/" if rel == "." else "/" + rel + "/")
missing = sorted(u for u in live if u not in built)
extra = sorted(u for u in built if u not in live)
out.append(f"LIVE SITEMAP URLS: {len(live)}   BUILT PAGES: {len(built)}")
out.append(f"\n== live URLs MISSING in build ({len(missing)}):")
out += [f"  {u}   [{live[u]}]" for u in missing]
out.append(f"\n== built pages NOT in live sitemap ({len(extra)}):")
out += [f"  {u}" for u in extra]

# ---------------------------------------------------------------- 2. internal links
links = collections.Counter()
where = {}
for dp, dn, fn in os.walk(SITE):
    rel = os.path.relpath(dp, SITE).replace(os.sep, "/")
    if rel.split("/")[0] in ("wp-content", "assets"):
        dn[:] = []
        continue
    for f in fn:
        if not f.endswith(".php"):
            continue
        t = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
        for h in re.findall(r'<a\b[^>]*\bhref="([^"]+)"', t):
            h = h.replace("&amp;", "&").replace("&#038;", "&")
            if h.startswith(("http://", "https://")):
                pu = urllib.parse.urlsplit(h)
                if not pu.netloc.endswith("midwest-tropical.com") or pu.netloc.startswith("store."):
                    continue
                h = pu.path + (("?" + pu.query) if pu.query else "")
            if not h.startswith("/") or h.startswith("//"):
                continue
            if re.search(r"/wp-content/|/feed/?$|/wp-json/|elementor-action|^/\?|/wp-admin|/xmlrpc", h):
                continue
            path = h.split("#")[0]
            if not path:
                continue
            links[path] += 1
            where.setdefault(path, (rel + "/" + f).lstrip("./"))
broken = {p: n for p, n in links.items() if not exists(p.split("?")[0])}
out.append(f"\n== internal link targets: {len(links)} unique, BROKEN (no page in build): {len(broken)}")
for p, n in sorted(broken.items(), key=lambda x: -x[1]):
    out.append(f"  {n:5d}x  {p}   (e.g. in {where[p]})")

# ---------------------------------------------------------------- 3. ask live about broken targets
if CHECK_LIVE and broken:
    out.append("\n== live status of broken targets:")
    for p in sorted(broken):
        try:
            st, final, body = get(ORIGIN + p)
            fp = urllib.parse.urlsplit(final).path
            note = f"-> redirects to {fp}" if fp != p.split("?")[0] else ""
            out.append(f"  {st} {p} {note}")
        except urllib.error.HTTPError as e:
            out.append(f"  {e.code} {p}")
        except Exception as e:
            out.append(f"  ERR {p} {e}")

report = "\n".join(out)
open(os.path.join(ROOT, "url-audit.txt"), "w", encoding="utf-8").write(report)
print(report[:6000])
