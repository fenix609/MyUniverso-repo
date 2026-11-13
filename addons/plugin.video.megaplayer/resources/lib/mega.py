# -*- coding: utf-8 -*-
"""Cliente MEGA mínimo: login (v1/v2, 2FA), listado de nodos y lectura descifrada por rangos."""
import base64, hashlib, json, re, struct, time
import requests
try:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
except ImportError:  # script.module.pycryptodome de Kodi usa el espacio de nombres Cryptodome
    from Cryptodome.Cipher import AES
    from Cryptodome.Util import Counter

API = 'https://g.api.mega.co.nz/cs'
ERRORS = {-2: 'Argumento inválido', -9: 'No existe', -15: 'Sesión caducada',
          -16: 'Usuario bloqueado', -26: 'Código 2FA requerido o incorrecto',
          -3: 'Servidor ocupado', -8: 'Caducado', -11: 'Acceso denegado',
          -18: 'No disponible temporalmente'}


class MegaError(Exception):
    pass


def b64d(s):
    s = s.replace('-', '+').replace('_', '/').replace(',', '')
    return base64.b64decode(s + '=' * (-len(s) % 4))


def b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


def s2a(s):
    s += b'\0' * (-len(s) % 4)
    return list(struct.unpack('>%dI' % (len(s) // 4), s))


def a2s(a):
    return struct.pack('>%dI' % len(a), *a)


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def ecb_dec(data, key):
    return AES.new(key, AES.MODE_ECB).decrypt(data)


def prepare_key_v1(password):
    arr = s2a(password.encode())
    pkey = bytes.fromhex('93C467E37DB0C7A4D1BE3F810152CB56')
    for _ in range(0x10000):
        for j in range(0, len(arr), 4):
            k = arr[j:j + 4]
            k += [0] * (4 - len(k))
            pkey = AES.new(a2s(k), AES.MODE_ECB).encrypt(pkey)
    return pkey


def string_hash_v1(email, aeskey):
    s32 = s2a(email.encode())
    h32 = [0, 0, 0, 0]
    for i, v in enumerate(s32):
        h32[i % 4] ^= v
    h = a2s(h32)
    c = AES.new(aeskey, AES.MODE_ECB)
    for _ in range(0x4000):
        h = c.encrypt(h)
    return b64e(h[0:4] + h[8:12])


def natural_key(name):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', name.lower())]


class MegaClient(object):
    def __init__(self):
        self.sid = None
        self.master = None
        self.user = None
        self.seq = int(time.time()) & 0xFFFF
        self.nodes = {}
        self.children = {}
        self.root = None
        self._urls = {}
        self.http = requests.Session()

    # ---------- API ----------
    def _api(self, req, retries=5):
        for i in range(retries):
            self.seq += 1
            params = {'id': self.seq}
            if self.sid:
                params['sid'] = self.sid
            r = self.http.post(API, params=params, data=json.dumps([req]), timeout=30)
            r.raise_for_status()
            res = r.json()
            if isinstance(res, int):
                res = [res]
            res = res[0]
            if res == -3:
                time.sleep(0.5 * (2 ** i))
                continue
            if isinstance(res, int) and res < 0:
                raise MegaError(ERRORS.get(res, 'Error MEGA %d' % res))
            return res
        raise MegaError('Servidor MEGA ocupado')

    def login(self, email, password, mfa=''):
        if not email or not password:
            raise MegaError('Configura correo y contraseña en los ajustes')
        email = email.strip().lower()
        try:
            pre = self._api({'a': 'us0', 'user': email})
        except MegaError:
            pre = {}
        if isinstance(pre, dict) and pre.get('v') == 2:
            dk = hashlib.pbkdf2_hmac('sha512', password.encode(), b64d(pre['s']), 100000, 32)
            pkey, uh = dk[:16], b64e(dk[16:])
        else:
            pkey = prepare_key_v1(password)
            uh = string_hash_v1(email, pkey)
        req = {'a': 'us', 'user': email, 'uh': uh}
        if mfa:
            req['mfa'] = mfa.strip()
        res = self._api(req)
        self.master = ecb_dec(b64d(res['k']), pkey)
        self.user = res.get('u')
        if 'tsid' in res:
            tsid = b64d(res['tsid'])
            if AES.new(self.master, AES.MODE_ECB).encrypt(tsid[:16]) == tsid[-16:]:
                self.sid = res['tsid']
                return
        if 'csid' in res:
            priv = ecb_dec(b64d(res['privk']), self.master)
            vals = []
            for _ in range(4):
                l = ((priv[0] * 256 + priv[1] + 7) // 8) + 2
                vals.append(int.from_bytes(priv[2:l], 'big'))
                priv = priv[l:]
            p, q, d, _u = vals
            enc = int.from_bytes(b64d(res['csid'])[2:], 'big')
            h = '%x' % pow(enc, d, p * q)
            if len(h) % 2:
                h = '0' + h
            self.sid = b64e(bytes.fromhex(h)[:43])
            return
        raise MegaError('No se pudo iniciar sesión')

    # ---------- Árbol ----------
    def load_nodes(self):
        res = self._api({'a': 'f', 'c': 1, 'r': 1})
        self.nodes, self.children = {}, {}
        for n in res.get('f', []):
            if n['t'] == 2:
                self.root = n['h']
                self.nodes[n['h']] = {'h': n['h'], 'p': '', 't': 2, 'name': 'Nube MEGA', 'size': 0}
                continue
            if n['t'] not in (0, 1) or not n.get('k'):
                continue
            key = None
            for part in n['k'].split('/'):
                if ':' in part:
                    uid, ek = part.split(':', 1)
                    if uid == self.user:
                        key = ecb_dec(b64d(ek), self.master)
                        break
            if not key:
                continue
            kk = xor(key[:16], key[16:32]) if n['t'] == 0 and len(key) >= 32 else key[:16]
            try:
                raw = AES.new(kk, AES.MODE_CBC, iv=b'\0' * 16).decrypt(b64d(n['a'])).rstrip(b'\0')
                if not raw.startswith(b'MEGA{'):
                    continue
                name = json.loads(raw[4:].decode('utf-8', 'replace')).get('n', n['h'])
            except Exception:
                continue
            self.nodes[n['h']] = {'h': n['h'], 'p': n['p'], 't': n['t'], 'name': name,
                                  'size': n.get('s', 0), 'key': key, 'aes': kk}
        for h, n in self.nodes.items():
            if n['p']:
                self.children.setdefault(n['p'], []).append(n)

    def list_children(self, parent=None):
        parent = parent or self.root
        items = self.children.get(parent, [])
        items = sorted(items, key=lambda n: (n['t'] == 0, natural_key(n['name'])))
        return [{'h': n['h'], 'name': n['name'], 't': n['t'], 'size': n['size'], 'p': parent} for n in items]

    def walk(self, parent=None, prefix=''):
        out = []
        for c in self.list_children(parent):
            if c['t'] == 0:
                out.append({'h': c['h'], 'name': c['name'], 'path': prefix + c['name']})
            else:
                out += self.walk(c['h'], prefix + c['name'] + '/')
        return out

    # ---------- Descarga ----------
    def _url(self, node):
        h = node['h']
        cached = self._urls.get(h)
        if cached and cached[1] > time.time():
            return cached[0]
        res = self._api({'a': 'g', 'g': 1, 'n': h})
        if 'g' not in res:
            raise MegaError('MEGA no devolvió URL de descarga')
        self._urls[h] = (res['g'], time.time() + 1800)
        return res['g']

    def read(self, node, start, end, chunk=65536):
        """Genera bytes descifrados del rango [start, end] (inclusive)."""
        url = self._url(node)
        astart = start - (start % 16)
        iv = int.from_bytes(node['key'][16:24], 'big') << 64
        ctr = Counter.new(128, initial_value=iv + astart // 16)
        cipher = AES.new(node['aes'], AES.MODE_CTR, counter=ctr)
        skip = start - astart
        r = self.http.get('%s/%d-%d' % (url, astart, end), stream=True, timeout=30)
        try:
            if r.status_code >= 400:
                self._urls.pop(node['h'], None)
                raise MegaError('HTTP %d de MEGA' % r.status_code)
            for part in r.iter_content(chunk):
                d = cipher.decrypt(part)
                if skip:
                    if skip >= len(d):
                        skip -= len(d)
                        continue
                    d, skip = d[skip:], 0
                yield d
        finally:
            r.close()
