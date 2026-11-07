"""Local preview without PHP installed: serves site/ and resolves the
`<?php include __DIR__ . '...'; ?>` lines the generated pages use.
usage: python -I tools/preview_server.py site 8080"""
import http.server
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
INC = re.compile(r"<\?php include __DIR__ \. '([^']+)'; \?>")


def render(path):
    src = open(path, encoding="utf-8").read()
    base = os.path.dirname(path)

    def rep(m):
        p = os.path.normpath(base + m.group(1))
        return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

    src = INC.sub(rep, src)
    return re.sub(r"<\?php.*?\?>", "", src, flags=re.S)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        fs = os.path.join(ROOT, path.lstrip("/").replace("/", os.sep))
        if os.path.isdir(fs):
            fs = os.path.join(fs, "index.php")
        if fs.endswith(".php"):
            if not os.path.exists(fs):
                fs = os.path.join(ROOT, "404.php")
                code = 404
            else:
                code = 200
            body = render(fs).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
