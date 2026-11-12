"""Remove the leftover WordPress / plugin fingerprints from the built site.

The pages were converted from WordPress, so their markup still carried class names and <head>
links that technology scanners (Wappalyzer, BuiltWith, ...) read as "WordPress + WooCommerce +
Swiper + Font Awesome", although none of that software is used any more. This step:
  * drops the WordPress-only <head> links (RSS feeds, oEmbed, wp-json REST API, shortlink,
    generator); those URLs do not exist on the custom site anyway;
  * renames plugin class names consistently in the HTML, the CSS and main.js, so the look
    is unchanged:  woocommerce* -> mtshop*,  swiper* -> mtslider*,  fa / fa-* -> mtic / mtic-*;
  * drops the schema-plugin class on the JSON-LD block.
Idempotent (a second run changes nothing). Run after finalize.py and before purge_css.py.

usage: python -I tools/declutter.py site
"""
import os
import re
import sys

SITE = os.path.abspath(sys.argv[1])


def ren_token(tok):
    if "woocommerce" in tok:  # woocommerce, woocommerce-no-js, elementor-widget-woocommerce-...
        return tok.replace("woocommerce", "mtshop")
    if "swiper" in tok:  # swiper-slide, elementor-main-swiper, elementor-swiper-button ...
        return tok.replace("swiper", "mtslider")
    if re.fullmatch(r"fa[bsrl]?", tok):
        return "mtic" + tok[2:]
    if tok.startswith("fa-"):
        return "mtic-" + tok[3:]
    m = re.fullmatch(r"e-fa([bsr])-(.+)", tok)  # Elementor's inline-SVG icon names (e-fas-search)
    if m:
        return f"e-ic{m.group(1)}-{m.group(2)}"
    return tok


def fix_class_attr(m):
    toks = [ren_token(t) for t in m.group(2).split()]
    return f"{m.group(1)}{' '.join(toks)}{m.group(3)}"


CLASS_ATTR = re.compile(r'(\bclass=")([^"]*)(")')

CSS_SEL = re.compile(r"\.([\w-]*woocommerce[\w-]*|[\w-]*swiper[\w-]*|fa[bsrl]?(?![\w-])|fa-[\w-]+|e-fa[bsr]-[\w-]+)")
CSS_ATTR = re.compile(r"(\[class[*^~|$]?=\s*[\"']?\s*)(woocommerce|swiper|fa-)")
MASK = re.compile(r"/\*.*?\*/|url\([^)]*\)|\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'", re.S)


def fix_css(css):
    keep = []

    def mask(m):
        # strings inside attribute selectors must still be renamed; urls / content strings are kept
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    def sel(m):
        return "." + ren_token(m.group(1))

    def attr(m):
        return m.group(1) + {"woocommerce": "mtshop", "swiper": "mtslider", "fa-": "mtic-"}[m.group(2)]

    css = CSS_ATTR.sub(attr, css)
    css = css.replace("--swiper-", "--mtslider-").replace("swiper-icons", "mtslider-icons").replace("swiper-preloader-spin", "mtslider-preloader-spin")
    masked = MASK.sub(mask, css)
    masked = CSS_SEL.sub(sel, masked)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], masked)


HEAD_JUNK = re.compile(
    r'<link\b[^>]*(?:application/rss\+xml|json\+oembed|xml\+oembed|/wp-json/|rel=["\'](?:https://api\.w\.org/|shortlink|EditURI|wlwmanifest|pingback)["\'])[^>]*>\s*'
    r'|<meta name="generator"[^>]*>\s*',
    re.I,
)
STYLE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.S | re.I)


def drop_div(t, opening):
    """remove the <div> that starts with `opening` together with everything inside it"""
    while True:
        i = t.find(opening)
        if i < 0:
            return t
        depth, j = 0, i
        for m in re.finditer(r"<div\b|</div>", t[i:]):
            depth += 1 if m.group(0) == "<div" else -1
            if depth == 0:
                j = i + m.end()
                break
        else:
            return t
        t = t[:i].rstrip(" \t") + t[j:]


# dead markup left behind by removed plugins (search widget area, image carousel, mail-tracker inputs)
DEAD_DIVS = ('<div class="jetpack-instant-search__widget-area"', '<div id="jp-carousel-loading-overlay"',
             '<div class="jp-carousel-overlay"')
DEAD_INPUTS = re.compile(r"\s*<input id='ws_ma_event_(?:type|data)'[^>]*/>")


def fix_html(t):
    for o in DEAD_DIVS:
        t = drop_div(t, o)
    t = DEAD_INPUTS.sub("", t)
    t = HEAD_JUNK.sub("", t)
    t = CLASS_ATTR.sub(fix_class_attr, t)
    t = STYLE.sub(lambda m: m.group(1) + fix_css(m.group(2)) + m.group(3), t)
    t = t.replace(' class="saswp-schema-markup-output"', "")
    t = re.sub(r'(data-widget_type="[^"]*)woocommerce', r"\1mtshop", t)
    t = re.sub(r'((?:id|aria-describedby|for)="[^"]*)woocommerce', r"\1mtshop", t)
    return t


def fix_js(t):
    t = re.sub(r"woocommerce", "mtshop", t)
    t = re.sub(r"swiper", "mtslider", t)
    return t.replace("WooCommerce", "shop")


# Vendor files (fonts / icons the CSS needs) were saved under their original host + plugin paths,
# e.g. /assets/ext/c0.wp.com/p/woocommerce/... Move them to neutral folders and fix the CSS urls.
import shutil

MOVES = [
    ("assets/ext/c0.wp.com/p/woocommerce/11.2.1", "assets/vendor/shop"),
    ("assets/ext/www.midwest-tropical.com/wp-content/plugins/woocommerce", "assets/vendor/shop-plugin"),
    ("assets/ext/www.midwest-tropical.com/wp-content/plugins/elementor", "assets/vendor/builder"),
    ("assets/ext/www.midwest-tropical.com/wp-content/plugins/gallery-videos", "assets/vendor/videos"),
    ("assets/ext/www.midwest-tropical.com/wp-content/plugins/mailin", "assets/vendor/mail"),
]
for old, new in MOVES:
    src, dst = os.path.join(SITE, old), os.path.join(SITE, new)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
        shutil.rmtree(src)
_fix_css_names = fix_css


def fix_css(css):  # noqa: F811 - names + vendor paths
    for old, new in MOVES:
        css = css.replace("/" + old + "/", "/" + new + "/")
    css = _fix_css_names(css).replace("--woocommerce:", "--mtshop:").replace("var(--woocommerce)", "var(--mtshop)")
    return css.replace("WooCommerce", "ShopIcons")  # icon font family + its file name (renamed below)


for _d in ("assets/vendor/shop", "assets/vendor/shop-plugin"):
    for dp, dn, fn in os.walk(os.path.join(SITE, _d)):
        for f in fn:
            if f.startswith("WooCommerce."):
                os.replace(os.path.join(dp, f), os.path.join(dp, "ShopIcons" + f[len("WooCommerce"):]))
for dp, dn, fn in os.walk(os.path.join(SITE, "assets", "ext"), topdown=False):  # empty folders left by the moves
    if not os.listdir(dp):
        os.rmdir(dp)


changed = 0
for dp, dn, fn in os.walk(SITE):
    if os.sep + "wp-content" in dp:
        continue
    for f in fn:
        p = os.path.join(dp, f)
        if f.endswith(".php") and f != "form-handler.php":
            fx = fix_html
        elif f.endswith(".css") and os.sep + os.path.join("assets", "css") in p:
            fx = fix_css
        elif f == "main.js":
            fx = fix_js
        else:
            continue
        t = open(p, encoding="utf-8", errors="replace").read()
        n = fx(t)
        if n != t:
            open(p, "w", encoding="utf-8").write(n)
            changed += 1
print("declutter: files changed", changed)
