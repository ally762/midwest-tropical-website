"""Create GitHub-Upload/ : a small folder that can be dragged into github.com in ONE browser upload
(web upload limits: max 100 files per upload, max 25 MB per file).

- README.md, DEPLOY.md, MISSING-IMAGES.txt, .gitignore, tools/, site-src/  -> copied as normal files
- site/ (the generated website, WITHOUT images/videos)                    -> GitHub-Upload/site.zip

usage: python -I tools/make_github_upload.py
"""
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "GitHub-Upload")
SKIP_DIRS = {os.path.join("site", "wp-content", "uploads"), os.path.join("site", "wp-content", "grand-media")}

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

for name in ("README.md", "DEPLOY.md", "MISSING-IMAGES.txt", ".gitignore"):
    shutil.copy2(os.path.join(ROOT, name), os.path.join(OUT, name))
for d in ("tools", "site-src"):
    shutil.copytree(os.path.join(ROOT, d), os.path.join(OUT, d),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

zpath = os.path.join(OUT, "site.zip")
n = 0
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for dp, dn, fn in os.walk(os.path.join(ROOT, "site")):
        rel = os.path.relpath(dp, ROOT)
        if any(rel == s or rel.startswith(s + os.sep) for s in SKIP_DIRS):
            dn[:] = []
            continue
        for f in fn:
            if f == "form-submissions.log":
                continue
            full = os.path.join(dp, f)
            z.write(full, os.path.relpath(full, ROOT))
            n += 1

files = sum(len(fn) for _, _, fn in os.walk(OUT))
print(f"site.zip: {n} files, {os.path.getsize(zpath) / 1024 / 1024:.1f} MB")
print(f"GitHub-Upload: {files} files in total")
