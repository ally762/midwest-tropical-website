"""Check the GitHub Pages demo (docs/): every relative link / src / css url must resolve to a file.

usage: python -I tools/audit_demo.py
"""
import collections
import os
import re
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
broken = collections.Counter()
example = {}
pages = 0


def resolve(base_dir, ref):
    ref = urllib.parse.unquote(ref.split("#")[0].split("?")[0])
    if not ref:
        return True
    p = os.path.normpath(os.path.join(base_dir, ref.replace("/", os.sep)))
    if not p.startswith(DOCS):  # pointing above docs/ (only the root redirect files live there)
        return os.path.exists(p) or os.path.exists(os.path.join(p, "index.html"))
    return os.path.isfile(p) or os.path.isfile(os.path.join(p, "index.html"))


for dp, dn, fn in os.walk(DOCS):
    for f in fn:
        full = os.path.join(dp, f)
        if f.endswith(".html"):
            pages += 1
            t = open(full, encoding="utf-8", errors="replace").read()
            refs = re.findall(r'\b(?:href|src|action|poster)="([^"]+)"', t)
            for ss in re.findall(r'\bsrcset="([^"]+)"', t):
                refs += [c.strip().split(" ")[0] for c in ss.split(",") if c.strip()]
            refs += re.findall(r"url\(['\"]?([^)'\"]+)['\"]?\)", t)
        elif f.endswith(".css"):
            t = open(full, encoding="utf-8", errors="replace").read()
            refs = re.findall(r"url\(['\"]?([^)'\"]+)['\"]?\)", t)
        else:
            continue
        for r in refs:
            r = r.replace("&amp;", "&").replace("&#038;", "&")
            if re.match(r"^(?:[a-z]+:|//|#|data:|\{|\$)", r, re.I) or "elementor-action" in r:
                continue
            if not resolve(dp, r):
                key = os.path.normpath(os.path.join(os.path.relpath(dp, DOCS), r.split("#")[0].split("?")[0])).replace(os.sep, "/")
                broken[key] += 1
                example.setdefault(key, os.path.relpath(full, DOCS).replace(os.sep, "/"))

print(f"demo pages: {pages}   broken relative references: {len(broken)} unique, {sum(broken.values())} total")
for k, n in broken.most_common(40):
    print(f"  {n:5d}x  {k}    (e.g. {example[k]})")
