# -*- coding: utf-8 -*-
import os, sys, json, re, threading, mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import xbmc, xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib'))
from mega import MegaClient, MegaError

mimetypes.add_type('video/x-matroska', '.mkv')
mimetypes.add_type('video/x-msvideo', '.avi')
mimetypes.add_type('application/x-bittorrent', '.torrent')


class Manager(object):
    def __init__(self):
        self.client = None
        self.lock = threading.Lock()

    def get(self):
        with self.lock:
            if self.client is None:
                a = xbmcaddon.Addon()
                c = MegaClient()
                c.login(a.getSetting('email'), a.getSetting('password'), a.getSetting('mfa'))
                c.load_nodes()
                self.client = c
            return self.client

    def reset(self):
        with self.lock:
            self.client = None


MANAGER = Manager()


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self._route(True)

    def do_GET(self):
        self._route(False)

    def _route(self, head):
        try:
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path == '/list':
                self._json(MANAGER.get().list_children(q.get('parent')))
            elif u.path == '/walk':
                self._json(MANAGER.get().walk(q.get('parent')))
            elif u.path == '/refresh':
                MANAGER.reset()
                MANAGER.get()
                self._json({'ok': True})
            elif u.path.startswith('/stream/'):
                self._stream(u.path.split('/')[2], head)
            else:
                self._json({'error': 'No encontrado'}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except MegaError as e:
            MANAGER.reset() if 'sesión' in str(e).lower() else None
            self._json({'error': str(e)}, 500)
        except Exception as e:
            xbmc.log('[MEGA Player] %r' % e, xbmc.LOGERROR)
            try:
                self._json({'error': repr(e)}, 500)
            except Exception:
                pass

    def _stream(self, h, head):
        c = MANAGER.get()
        node = c.nodes.get(h)
        if not node or node['t'] != 0:
            return self._json({'error': 'Archivo no encontrado'}, 404)
        size = int(node['size'])
        start, end, code = 0, size - 1, 200
        m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
        if m:
            s, e = m.groups()
            if s == '':
                start = max(size - int(e or 0), 0)
            else:
                start = int(s)
                if e:
                    end = min(int(e), size - 1)
            if start >= size:
                self.send_response(416)
                self.send_header('Content-Range', 'bytes */%d' % size)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            code = 206
        self.send_response(code)
        self.send_header('Content-Type', mimetypes.guess_type(node['name'])[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if code == 206:
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (start, end, size))
        self.end_headers()
        if not head:
            for chunk in c.read(node, start, end):
                self.wfile.write(chunk)


class SettingsMonitor(xbmc.Monitor):
    def onSettingsChanged(self):
        MANAGER.reset()


def main():
    monitor = SettingsMonitor()
    port = int(xbmcaddon.Addon().getSetting('port') or 8765)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    xbmc.log('[MEGA Player] Servidor en 127.0.0.1:%d' % port, xbmc.LOGINFO)
    while not monitor.waitForAbort(2):
        pass
    server.shutdown()
    server.server_close()


main()
