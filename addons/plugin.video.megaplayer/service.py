# -*- coding: utf-8 -*-
import os, sys, json, re, threading, mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import xbmc, xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo('path'), 'resources', 'lib'))
from mega import MegaClient, MegaError
from accounts import get_accounts

mimetypes.add_type('video/x-matroska', '.mkv')
mimetypes.add_type('video/x-msvideo', '.avi')
mimetypes.add_type('application/x-bittorrent', '.torrent')


class Manager(object):
    def __init__(self):
        self.clients = {}
        self.locks = {}
        self.glock = threading.Lock()

    def _lock(self, i):
        with self.glock:
            return self.locks.setdefault(i, threading.Lock())

    def get(self, i):
        i = str(i or '1')
        with self._lock(i):
            c = self.clients.get(i)
            if c is None:
                acc = next((x for x in get_accounts() if x['id'] == i), None)
                if not acc:
                    raise MegaError('La cuenta %s no está configurada' % i)
                try:
                    c = MegaClient()
                    c.login(acc['email'], acc['password'], acc['mfa'])
                    c.load_nodes()
                except MegaError as e:
                    raise MegaError('[%s] %s' % (acc['name'], e))
                self.clients[i] = c
            return c

    def reset(self, i=None):
        with self.glock:
            if i is None:
                self.clients.clear()
            else:
                self.clients.pop(str(i), None)


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
        acc = '1'
        try:
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            acc = q.get('acc', '1')
            if u.path == '/list':
                self._json(MANAGER.get(acc).list_children(q.get('parent')))
            elif u.path == '/walk':
                self._json(MANAGER.get(acc).walk(q.get('parent')))
            elif u.path == '/reset':
                MANAGER.reset()
                self._json({'ok': True})
            elif u.path == '/refresh':
                MANAGER.reset(acc)
                MANAGER.get(acc)
                self._json({'ok': True})
            elif u.path.startswith('/stream/'):
                parts = u.path.split('/')
                # /stream/<cuenta>/<handle>/<nombre>   (formato antiguo: /stream/<handle>/<nombre>)
                if len(parts) >= 5:
                    self._stream(parts[2], parts[3], head)
                else:
                    self._stream('1', parts[2], head)
            else:
                self._json({'error': 'No encontrado'}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except MegaError as e:
            if 'sesión' in str(e).lower():
                MANAGER.reset(acc)
            self._json({'error': str(e)}, 500)
        except Exception as e:
            xbmc.log('[MEGA Player] %r' % e, xbmc.LOGERROR)
            try:
                self._json({'error': repr(e)}, 500)
            except Exception:
                pass

    def _stream(self, acc, h, head):
        c = MANAGER.get(acc)
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
    port = int(xbmcaddon.Addon().getSetting('port') or 48765)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    except OSError as e:
        xbmc.log('[MEGA Player] No se pudo abrir el puerto %d: %r' % (port, e), xbmc.LOGERROR)
        return
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    xbmc.log('[MEGA Player] Servidor en 127.0.0.1:%d' % port, xbmc.LOGINFO)
    while not monitor.waitForAbort(2):
        pass
    server.shutdown()
    server.server_close()


main()
