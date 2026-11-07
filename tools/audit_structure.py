"""Group pages by layout structure to find inconsistent templates.
usage: python -I tools/audit_structure.py site"""
import os
import re
import sys
import collections

ROOT = os.path.abspath(sys.argv[1])
urls = open(os.path.join(ROOT, "includes", "urls.txt"), encoding="utf-8").read().split()


def top_level(body):
    """yield (kind, html) for top-level elementor sections/containers of the page content"""
    m = re.search(r'<div data-elementor-type="(?:wp-page|single-page|single-post|product|wp-post)"[^>]*>', body)
    if not m:
        return []
    i = m.end()
    out, depth, start = [], 0, None
    for t in re.finditer(r"<(/?)(div|section)\b[^>]*>", body[i:]):
        if t.group(1):
            depth -= 1
            if depth == 0 and start is not None:
                out.append(body[start: i + t.end()])
                start = None
            if depth < 0:
                break
        else:
            if depth == 0:
                start = i + t.start()
            depth += 1
    return out


def sig(sec):
    cols = len(re.findall(r'class="elementor-column |e-child', sec[:20000]))
    widgets = re.findall(r'data-widget_type="([\w-]+)\.', sec)
    w = collections.Counter(widgets)
    key = []
    for name in ("heading", "text-editor", "image", "button", "form", "slides", "video", "gallery", "posts", "html", "icon-list", "image-box", "tabs", "theme-page-title"):
        if w.get(name):
            key.append(name)
    return f"[{cols}c:{'+'.join(key)}]"


groups = collections.defaultdict(list)
rows = []
for u in urls:
    p = os.path.join(ROOT, u.strip("/"), "index.php") if u != "/" else os.path.join(ROOT, "index.php")
    if not os.path.exists(p):
        continue
    t = open(p, encoding="utf-8").read()
    secs = top_level(t)
    fp = " ".join(sig(s) for s in secs)
    seg = u.strip("/").split("/")[0] if "/" in u.strip("/") else "(root)"
    h1 = len(re.findall(r"<h1\b", t))
    form = "form" if 'data-widget_type="form.default"' in t else "-"
    rows.append((seg, u, len(secs), h1, form, fp))
    groups[fp].append(u)

print("== pages by section:")
for seg in sorted(set(r[0] for r in rows)):
    rs = [r for r in rows if r[0] == seg]
    fps = collections.Counter(r[5] for r in rs)
    print(f"\n## {seg}: {len(rs)} pages, {len(fps)} distinct layouts")
    for fp, n in fps.most_common():
        ex = [r[1] for r in rs if r[5] == fp][:4]
        print(f"  {n:3d}x  h1s={[r[3] for r in rs if r[5]==fp][0]}  {fp[:230]}\n        e.g. {', '.join(ex)}")
