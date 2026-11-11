"""Compare element geometry between the live page and our build.

Input: two text files with "data-id:x,y,w,h data-id:x,y,w,h ..." (measured in the browser at the
same viewport width, see MEASURE_JS below). Prints elements whose x / width / height differ by more
than TOL px (y is shown but differences in y are usually a knock-on effect of something above).

usage: python -I tools/layout_diff.py live.txt build.txt
"""
import sys

MEASURE_JS = """
const main=document.querySelector('[data-elementor-type="wp-page"],[data-elementor-type="single-post"],[data-elementor-type="product"],[data-elementor-type="wp-post"]')||document.body;
const out=[];main.querySelectorAll('[data-id]').forEach(e=>{const r=e.getBoundingClientRect();if(!r.width&&!r.height)return;
out.push(e.getAttribute('data-id')+':'+Math.round(r.left)+','+Math.round(r.top+scrollY)+','+Math.round(r.width)+','+Math.round(r.height))});out.join(' ')
"""
TOL = 6


def load(p):
    d = {}
    for tok in open(p, encoding="utf-8").read().split():
        if ":" not in tok:
            continue
        k, v = tok.split(":", 1)
        try:
            d.setdefault(k, tuple(int(x) for x in v.split(",")))
        except ValueError:
            pass
    return d


live, built = load(sys.argv[1]), load(sys.argv[2])
only_live = [k for k in live if k not in built]
only_built = [k for k in built if k not in live]
diffs = []
for k, (x, y, w, h) in live.items():
    if k not in built:
        continue
    bx, by, bw, bh = built[k]
    if abs(x - bx) > TOL or abs(w - bw) > TOL or abs(h - bh) > TOL:
        diffs.append((k, (x, y, w, h), (bx, by, bw, bh)))
print(f"elements: live {len(live)}, build {len(built)}, compared {len(live) - len(only_live)}, "
      f"DIFFERENT {len(diffs)}, missing in build {len(only_live)}, extra in build {len(only_built)}")
for k, a, b in diffs[:60]:
    print(f"  {k:10s} live x{a[0]:5d} y{a[1]:6d} w{a[2]:5d} h{a[3]:6d}  |  build x{b[0]:5d} y{b[1]:6d} w{b[2]:5d} h{b[3]:6d}")
if only_live:
    print("  missing (visible on live, not in build):", " ".join(only_live[:30]))
