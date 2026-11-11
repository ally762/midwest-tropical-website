"""Conservative unused-CSS removal for the generated bundles.

A selector is dropped only when it references a class or id that appears in
NO generated page / include (and is not a runtime state class added by JS).
usage: python -I tools/purge_css.py site
"""
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1])

classes, ids = set(), set()
for dp, dn, fn in os.walk(ROOT):
    if "wp-content" in dp or "assets" in dp:
        continue
    for f in fn:
        if f.endswith(".php"):
            t = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'class\s*=\s*["\']([^"\']*)["\']', t):
                classes.update(m.group(1).split())
            ids.update(re.findall(r'id\s*=\s*["\']([^"\']+)["\']', t))
js = open(os.path.join(ROOT, "assets/js/main.js"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "assets/js/main.js")) else ""
classes.update(re.findall(r"['\"]([a-zA-Z][\w-]+)['\"]", js))

KEEP = re.compile(
    r"active|open|show|hide|hidden|sticky|swiper|dialog|lightbox|e--|elementor-motion|animated|animation|"
    r"loading|loaded|focus|hover|current|selected|expanded|toggle|error|success|message|invalid|valid|"
    r"screen-reader|sr-only|visible|fade|in$|playing|e-con|e-flex|e-grid|e-lazy|has-|is-|mt-|mtx-|"
    r"elementor-hidden|elementor-device|elementor-editor|e-n-|sub-arrow|highlighted|pswp|fa-|fab|fas|far|eicon",
    re.I,
)


def split_top(sel):
    """split a selector list on commas that are not inside (), [] or quotes"""
    out, buf, depth, q = [], [], 0, None
    for c in sel:
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            out.append("".join(buf))
            buf = []
            continue
        buf.append(c)
    out.append("".join(buf))
    return out


def alive(sel):
    if re.search(r":(?:is|where|has|not)\(", sel):
        # functional pseudo-classes: only judge the part outside the parentheses
        outer = re.sub(r":(?:is|where|has|not)\((?:[^()]|\([^()]*\))*\)", "", sel)
        return alive(outer) if outer != sel else True
    sel = re.sub(r"::?[a-zA-Z-]+(\([^)]*\))?", "", sel)  # pseudo classes/elements (incl :not(...))
    for c in re.findall(r"\.(-?[_a-zA-Z][\w-]*)", sel):
        if c not in classes and not KEEP.search(c):
            return False
    for i in re.findall(r"#(-?[_a-zA-Z][\w-]*)", sel):
        if i not in ids and not KEEP.search(i):
            return False
    return True


def parse(css, i=0):
    """yield (prelude, body_or_None, is_block) items at one nesting level"""
    out = []
    n = len(css)
    while i < n:
        j = css.find("{", i)
        k = css.find("}", i)
        semi = css.find(";", i)
        if k != -1 and (j == -1 or k < j):
            return out, k + 1
        if j == -1:
            break
        if semi != -1 and semi < j and css[i:semi].lstrip().startswith("@"):
            out.append((css[i : semi + 1], None))
            i = semi + 1
            continue
        pre = css[i:j]
        if pre.lstrip().startswith(("@media", "@supports", "@container", "@layer", "@document")):
            inner, nxt = parse(css, j + 1)
            out.append((pre, inner))
            i = nxt
        else:
            # find matching close brace (keyframes / font-face have nested braces)
            depth, p = 0, j
            while p < n:
                if css[p] == "{":
                    depth += 1
                elif css[p] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                p += 1
            out.append((pre, css[j + 1 : p]))
            i = p + 1
    return out, n


def emit(items):
    res = []
    for pre, body in items:
        if body is None:
            res.append(pre)
        elif isinstance(body, list):
            inner = emit(body)
            if inner:
                res.append(pre + "{" + inner + "}")
        else:
            p = pre.strip()
            if p.startswith("@"):
                res.append(pre + "{" + body + "}")
                continue
            sels = [s for s in split_top(p) if alive(s)]
            if sels:
                res.append(",".join(sels) + "{" + body + "}")
    return "".join(res)


cssdir = os.path.join(ROOT, "assets/css")
import hashlib
for f in os.listdir(cssdir):
    if not (f.startswith("b-") or f in ("core.css", "core-late.css")):
        continue
    p = os.path.join(cssdir, f)
    src = open(p, encoding="utf-8").read()
    # hide url(...) and quoted strings while parsing: braces/commas inside them (e.g. data: URIs,
    # content:"}") must not be treated as CSS structure
    masked = []

    def _mask(m):
        masked.append(m.group(0))
        return f"\x00{len(masked) - 1}\x00"

    work = re.sub(r"url\((?:\"[^\"]*\"|'[^']*'|[^)]*)\)|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", _mask, src)
    items, _ = parse(work)
    out = emit(items)
    out = re.sub(r"\x00(\d+)\x00", lambda m: masked[int(m.group(1))], out)
    if len(out) < len(src) * 0.05 and len(src) > 50000:
        print(f"  WARNING {f}: purge kept under 5% ({len(out)} of {len(src)} bytes) - keeping the original")
        out = src
    # drop @keyframes / @font-face that are no longer referenced
    used_anims = set(re.findall(r"animation(?:-name)?\s*:\s*([\w-]+)", out))
    out = re.sub(r"@(?:-webkit-)?keyframes\s+([\w-]+)\s*{(?:[^{}]*{[^{}]*})*[^{}]*}",
                 lambda m: m.group(0) if m.group(1) in used_anims or KEEP.search(m.group(1)) else "", out)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"{f}: {len(src)//1024}KB -> {len(out)//1024}KB")

# cache-busting: ?v=<content hash> on the shared files so browsers pick up new deploys
def ver(rel):
    return hashlib.sha1(open(os.path.join(ROOT, rel), "rb").read()).hexdigest()[:8]

v = {p: ver(p.lstrip("/")) for p in ("/assets/css/core.css", "/assets/css/core-late.css", "/assets/css/fix.css", "/assets/js/main.js")
     if os.path.exists(os.path.join(ROOT, p.lstrip("/")))}
for dp, dn, fn in os.walk(ROOT):
    if os.sep + "wp-content" in dp or os.sep + "assets" in dp:
        continue
    for f in fn:
        if f.endswith(".php"):
            p = os.path.join(dp, f)
            t = open(p, encoding="utf-8").read()
            n = t
            for path, h in v.items():
                n = re.sub(re.escape(path) + r'(\?v=\w+)?"', f'{path}?v={h}"', n)
            if n != t:
                open(p, "w", encoding="utf-8").write(n)
print("versioned:", v)
