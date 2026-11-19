# -*- coding: utf-8 -*-
"""Proxy HTTP local para reproducir archivos de Google Drive.

Kodi se conecta a 127.0.0.1 (rápido y con Content-Length / Range correctos) y el proxy habla con Drive.
Cuando Kodi cierra (stop), la conexión local se cierra al instante y el proxy suelta la descarga de Drive
por su cuenta, sin hacer esperar a Kodi.

Si Drive responde con una página web (límite de descargas, archivo privado...) en lugar del vídeo, el proxy
contesta 403 con la cabecera X-Multimedia-Reason para que el addon pueda decir qué ha pasado."""
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
# Sin proxies del sistema ni de variables de entorno: Kodi tampoco los usa para esta conexión
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def classify(page):
    """Motivo (código corto) por el que Drive devolvió una página web en vez del vídeo."""
    text = page.decode("utf-8", "replace").lower() if isinstance(page, bytes) else (page or "").lower()
    if "too many users" in text or "quota" in text or "demasiados usuarios" in text:
        return "quota"
    if "can't view or download" in text or "no se puede ver ni descargar" in text or "cannot be shared" in text:
        return "blocked"
    if "accounts.google.com" in text or "servicelogin" in text or "sign in" in text or "iniciar sesión" in text:
        return "private"
    if "virus scan" in text or "can't scan this file" in text or "no puede analizar" in text:
        return "scan"
    return "html"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "multimedia-proxy"

    def log_message(self, *args):  # silencio: nada de ruido en el log de Kodi
        pass

    def _log(self, message):
        try:
            if self.server.log:
                self.server.log(message)
        except Exception:
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

    def _key(self):
        try:
            return self.server.get_key() or ""
        except Exception:
            return ""

    def _serve(self, head):
        match = _PATH.match(urlparse(self.path).path)
        if not match:
            self._reply(404, [("Content-Length", "0")])
            return
        file_id = match.group(1)
        request_headers = {"User-Agent": media._UA}
        client_range = self.headers.get("Range")
        if head:
            request_headers["Range"] = "bytes=0-0"  # así Drive nos dice el tamaño total sin descargar nada
        elif client_range:
            request_headers["Range"] = client_range
        upstream = media.drive_url(file_id, self._key(), headers=False)
        try:
            resp = _OPENER.open(urllib.request.Request(upstream, headers=request_headers), timeout=30)
        except HTTPError as exc:
            reason = classify(exc.read(8192)) if exc.code in (403, 429) else None
            self._log("Drive respondió HTTP {} ({})".format(exc.code, reason or "sin detalle"))
            extra = [("Content-Range", exc.headers["Content-Range"])] if exc.headers.get("Content-Range") else []
            if reason:
                extra.append(("X-Multimedia-Reason", reason))
            self._reply(exc.code, extra + [("Content-Length", "0")])
            return
        except Exception as exc:
            self._log("No se pudo conectar con Drive: {}".format(exc))
            self._reply(502, [("Content-Length", "0")])
            return
        try:
            if (resp.headers.get("Content-Type") or "").lower().startswith("text/html"):
                reason = classify(resp.read(8192))
                self._log("Drive devolvió una página web en lugar del vídeo ({})".format(reason))
                self._reply(403, [("X-Multimedia-Reason", reason), ("Content-Length", "0")])
                return
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


def make_server(get_key=lambda: "", port=0, log=None):
    """Crea el servidor en 127.0.0.1 (puerto libre si port=0). Llamar a serve_forever() en un hilo."""
    server = _Server(("127.0.0.1", port), _Handler)
    server.get_key = get_key
    server.log = log
    return server
