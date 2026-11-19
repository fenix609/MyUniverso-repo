# -*- coding: utf-8 -*-
"""Utilidades Mega: parseo de enlaces, metadatos y descifrado AES-CTR (basado en el addon de ejemplo)."""
import re, json, base64, time
import requests
from Cryptodome.Cipher import AES

API = "https://g.api.mega.co.nz/cs"
_cache = {}

def b64d(s):
    s = s.replace('-', '+').replace('_', '/').replace(',', '')
    return base64.b64decode(s + '=' * (-len(s) % 4))

def parse_link(link):
    m = re.search(r'mega\.(?:nz|co\.nz)/file/([\w-]+)#([\w-]+)', link) or \
        re.search(r'mega\.(?:nz|co\.nz)/#!([\w-]+)!([\w-]+)', link)
    if not m:
        raise ValueError("Enlace Mega no válido (solo archivos individuales)")
    return m.group(1), m.group(2)

def get_info(link):
    fid, key = parse_link(link)
    c = _cache.get(fid)
    if c and time.time() - c['t'] < 1800:
        return c
    r = requests.post(API, params={'id': int(time.time())},
                      data=json.dumps([{'a': 'g', 'g': 1, 'p': fid}]), timeout=20)
    d = r.json()
    d = d[0] if isinstance(d, list) else d
    if isinstance(d, int):
        raise RuntimeError("Mega devolvió error %s (enlace caído o bloqueado)" % d)
    raw = b64d(key)
    k = bytes(a ^ b for a, b in zip(raw[:16], raw[16:32]))
    nonce = raw[16:24]
    name = "video.mp4"
    try:
        at = AES.new(k, AES.MODE_CBC, iv=b'\0' * 16).decrypt(b64d(d['at']))
        if at.startswith(b'MEGA'):
            name = json.loads(at[4:].rstrip(b'\0').decode('utf-8', 'ignore')).get('n', name)
    except Exception:
        pass
    c = {'t': time.time(), 'url': d['g'], 'size': d['s'], 'key': k, 'nonce': nonce, 'name': name}
    _cache[fid] = c
    return c

def stream(info, start, end):
    """Generador de bytes descifrados entre start y end (inclusive)."""
    aligned = start - (start % 16)
    skip = start - aligned
    cipher = AES.new(info['key'], AES.MODE_CTR, nonce=info['nonce'], initial_value=aligned // 16)
    r = requests.get("%s/%d-%d" % (info['url'], aligned, end), stream=True, timeout=30)
    r.raise_for_status()
    for chunk in r.iter_content(65536):
        data = cipher.decrypt(chunk)
        if skip:
            data, skip = data[skip:], 0
        if data:
            yield data
