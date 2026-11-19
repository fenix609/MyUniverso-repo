# -*- coding: utf-8 -*-
"""Proxy HTTP local (127.0.0.1) que descifra archivos de Mega al vuelo, con soporte de seek (Range)."""
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import mega  # necesita script.module.pycryptodome


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _log(self, message):
        try:
            if self.server.log:
                self.server.log(message)
        except Exception:
            pass

    def _serve(self, head=False):
        try:
            parsed = urlparse(self.path)
            if parsed.path != "/mega":
                self.send_error(404)
                return
            link = parse_qs(parsed.query)["link"][0]
            info = mega.get_info(link)
            size = info["size"]
            start, end, code = 0, size - 1, 200
            rng = self.headers.get("Range")
            if rng and rng.startswith("bytes="):
                a, _, b = rng[6:].partition("-")
                start = int(a) if a else 0
                end = min(int(b) if b else size - 1, size - 1)
                code = 206
            if start >= size or start > end:
                self.send_response(416)
                self.send_header("Content-Range", "bytes */%d" % size)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            ctype = mimetypes.guess_type(info["name"])[0] or "video/mp4"
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if code == 206:
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
            self.end_headers()
            if head:
                return
            for data in mega.stream(info, start, end):
                self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Kodi cerró (stop o salto)
        except Exception as exc:
            self._log("Mega: {}".format(exc))
            try:
                self.send_error(500)
            except Exception:
                pass

    def do_GET(self):
        self._serve()

    def do_HEAD(self):
        self._serve(True)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(port=0, log=None):
    """Crea el servidor en 127.0.0.1 (puerto libre si port=0). Llamar a serve_forever() en un hilo."""
    server = _Server(("127.0.0.1", port), _Handler)
    server.log = log
    return server
