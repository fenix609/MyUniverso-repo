# -*- coding: utf-8 -*-
"""Proxy HTTP local para reproducir archivos de Google Drive.

Kodi se conecta a 127.0.0.1 (rápido y con Content-Length / Range correctos) y el proxy habla con Drive.
Cuando Kodi cierra (stop), la conexión local se cierra al instante y el proxy suelta la descarga de Drive
por su cuenta, sin hacer esperar a Kodi."""
import re
import socket
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlparse

from . import media

_PATH = re.compile(r"^/drive/([A-Za-z0-9_-]{10,100})$")
_CLIENT_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, socket.timeout, OSError)
CHUNK = 64 * 1024


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "multimedia-proxy"

    def log_message(self, *args):  # silencio: no escribir en el log de Kodi
        pass

    def do_HEAD(self):
        self._serve(head=True)

    def do_GET(self):
        self._serve(head=False)

    def _reply(self, code, headers=()):
        self.send_response(code)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _serve(self, head):
        match = _PATH.match(urlparse(self.path).path)
        if not match:
            self._reply(404, [("Content-Length", "0")])
            return
        request_headers = {"User-Agent": media._UA}
        client_range = self.headers.get("Range")
        if head:
            request_headers["Range"] = "bytes=0-0"  # así Drive nos dice el tamaño total sin descargar nada
        elif client_range:
            request_headers["Range"] = client_range
        upstream = media.drive_url(match.group(1), self.server.get_key(), headers=False)
        try:
            resp = urllib.request.urlopen(urllib.request.Request(upstream, headers=request_headers), timeout=30)
        except HTTPError as exc:
            extra = [("Content-Range", exc.headers["Content-Range"])] if exc.headers.get("Content-Range") else []
            self._reply(exc.code, extra + [("Content-Length", "0")])
            return
        except Exception:
            self._reply(502, [("Content-Length", "0")])
            return
        try:
            self._relay(resp, head, client_range)
        finally:
            resp.close()  # suelta la descarga de Drive pase lo que pase

    def _relay(self, resp, head, client_range):
        status = resp.status
        total = None
        content_range = resp.headers.get("Content-Range")
        if content_range and "/" in content_range:
            tail = content_range.rsplit("/", 1)[1]
            total = int(tail) if tail.isdigit() else None
        headers = [("Content-Type", resp.headers.get("Content-Type") or "application/octet-stream")]
        if head:
            length = total if total is not None else resp.headers.get("Content-Length")
            if length is not None:
                headers.append(("Content-Length", str(length)))
            headers.append(("Accept-Ranges", "bytes"))
            self._reply(200, headers)
            return
        if resp.headers.get("Content-Length"):
            headers.append(("Content-Length", resp.headers["Content-Length"]))
        if status == 206:
            headers.append(("Content-Range", content_range or ""))
        if status == 206 or (resp.headers.get("Accept-Ranges") or "").lower() == "bytes":
            headers.append(("Accept-Ranges", "bytes"))
        self._reply(status, headers)
        try:
            while True:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except _CLIENT_GONE:
            pass  # Kodi cerró (stop o salto): se termina sin esperar


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(get_key=lambda: "", port=0):
    """Crea el servidor en 127.0.0.1 (puerto libre si port=0). Llamar a serve_forever() en un hilo."""
    server = _Server(("127.0.0.1", port), _Handler)
    server.get_key = get_key
    return server
