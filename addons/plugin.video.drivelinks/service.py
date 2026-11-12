# -*- coding: utf-8 -*-
"""
Servicio de Drive Links: proxy local 127.0.0.1 que sirve los archivos de tu Drive a Kodi
renovando el token de Google en cada petición. Así los vídeos largos y los saltos de
posición no fallan cuando el token (1 hora) caduca. Solo escucha en el propio equipo y
exige una clave aleatoria que cambia en cada arranque de Kodi.
"""
import http.server
import socketserver
import threading
import secrets
import urllib.error
import urllib.parse
import urllib.request

import xbmc
import xbmcgui

from resources.lib import api, auth


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = 'DriveLinksProxy/1.0'
    key = ''

    def log_message(self, *args):
        pass

    def _file_id(self):
        parts = [p for p in urllib.parse.urlparse(self.path).path.split('/') if p]
        if len(parts) >= 2 and secrets.compare_digest(parts[0], Handler.key):
            return urllib.parse.unquote(parts[1])
        return None

    def _upstream(self, file_id, rng, force=False):
        token = auth.get_token(min_valid=10 ** 9 if force else 120)  # force => renovar ya
        url = '%s/files/%s?alt=media&supportsAllDrives=true' % (
            api.API, urllib.parse.quote(file_id, safe=''))
        headers = {'Authorization': 'Bearer ' + token}
        if rng:
            headers['Range'] = rng
        return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30)

    def do_HEAD(self):
        fid = self._file_id()
        if not fid:
            self.send_error(403)
            return
        try:
            meta = api._json('/files/' + urllib.parse.quote(fid, safe=''),
                             {'fields': 'size,mimeType', 'supportsAllDrives': 'true'})
        except Exception:
            self.send_error(502)
            return
        self.send_response(200)
        self.send_header('Content-Type', meta.get('mimeType', 'application/octet-stream'))
        if meta.get('size'):
            self.send_header('Content-Length', str(meta['size']))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()

    def do_GET(self):
        fid = self._file_id()
        if not fid:
            self.send_error(403)
            return
        rng = self.headers.get('Range')
        try:
            try:
                resp = self._upstream(fid, rng)
            except urllib.error.HTTPError as e:
                if e.code != 401:
                    raise
                resp = self._upstream(fid, rng, force=True)   # token caducado: reintento
        except urllib.error.HTTPError as e:
            self.send_error(e.code)
            return
        except Exception as e:
            xbmc.log('DriveLinks proxy: %s' % e, xbmc.LOGWARNING)
            self.send_error(502)
            return
        try:
            self.send_response(resp.status)
            for h in ('Content-Type', 'Content-Length', 'Content-Range'):
                v = resp.headers.get(h)
                if v:
                    self.send_header(h, v)
            self.send_header('Accept-Ranges', 'bytes')
            self.end_headers()
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass          # Kodi cerró la conexión (salto de posición, parada...)
        finally:
            resp.close()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run():
    Handler.key = secrets.token_urlsafe(16)
    try:
        srv = Server(('127.0.0.1', api.PROXY_PORT), Handler)
    except OSError as e:
        xbmc.log('DriveLinks proxy no pudo arrancar: %s' % e, xbmc.LOGERROR)
        return
    xbmcgui.Window(10000).setProperty(api.PROXY_PROP, Handler.key)
    threading.Thread(target=srv.serve_forever, kwargs={'poll_interval': 0.5},
                     daemon=True).start()
    xbmc.log('DriveLinks proxy en 127.0.0.1:%d' % api.PROXY_PORT, xbmc.LOGINFO)
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    srv.shutdown()
    srv.server_close()
    xbmcgui.Window(10000).clearProperty(api.PROXY_PROP)


if __name__ == '__main__':
    run()
