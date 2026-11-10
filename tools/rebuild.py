"""Full rebuild of site/ from the live WordPress site (HTML/CSS/images are cached in <cache>).

Steps: clean generated pages/CSS (keeps downloaded media) -> build pages/posts/products
       -> restore blog articles -> finalize (sitemap, 404, title bands, site-src files) -> purge CSS.

usage: python -I tools/rebuild.py <cache dir> [all|pages|posts|products]
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.join(ROOT, "site")
cache = os.path.abspath(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "all"
modes = ["pages", "posts", "products", "extra"] if mode == "all" else [mode]

os.makedirs(SITE, exist_ok=True)
for name in os.listdir(SITE):  # generated files only; media in wp-content / assets/ext is kept
    if name in ("wp-content", "assets"):
        continue
    p = os.path.join(SITE, name)
    shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
shutil.rmtree(os.path.join(SITE, "assets", "css"), ignore_errors=True)


def run(*args):
    print(">>", " ".join(args[2:4]), flush=True)
    r = subprocess.run([sys.executable, "-I", "-u", *args], cwd=ROOT)
    if r.returncode:
        sys.exit(f"step failed ({r.returncode}): {args}")


for m in modes:
    run(os.path.join(HERE, "build.py"), SITE, cache, m)
if "posts" in modes:
    run(os.path.join(HERE, "restore_posts.py"), SITE, cache)
run(os.path.join(HERE, "finalize.py"), SITE, os.path.join(ROOT, "site-src"))
run(os.path.join(HERE, "purge_css.py"), SITE)
print("REBUILD OK")
