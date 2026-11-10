"""Invalidate cached HTML for pages that changed on the live site since they were downloaded.

Reads the live sitemaps (lastmod) and deletes the cached copy of every URL whose lastmod is
newer than the cache file, plus the cached sitemaps themselves, so the next build refetches them.

usage: python -I tools/refresh_cache.py <cache dir>
"""
import datetime
import hashlib
import os
import re
import sys
import urllib.request

CACHE = os.path.abspath(sys.argv[1])
ORIGIN = "https://www.midwest-tropical.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def cpath(u):
    return os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest())


idx = get(ORIGIN + "/sitemap_index.xml")
changed = new = 0
for sm in re.findall(r"<loc>([^<]+)</loc>", idx):
    if os.path.exists(cpath(sm)):
        os.remove(cpath(sm))  # always use the current sitemap
    xml = get(sm)
    for loc, lastmod in re.findall(r"<url>\s*<loc>([^<]+)</loc>\s*(?:<lastmod>([^<]+)</lastmod>)?", xml):
        p = cpath(loc)
        if not os.path.exists(p):
            new += 1
            continue
        if lastmod:
            lm = datetime.datetime.fromisoformat(lastmod.replace("Z", "+00:00")).timestamp()
            if lm > os.path.getmtime(p):
                os.remove(p)
                changed += 1
print(f"cache refresh: {changed} changed pages will be re-downloaded, {new} new URLs")
