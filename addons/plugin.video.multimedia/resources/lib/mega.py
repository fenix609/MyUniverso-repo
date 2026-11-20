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

_FOLDER_RE = re.compile(r'mega\.(?:nz|co\.nz)/folder/([\w-]+)#([\w-]+)(?:/(file|folder)/([\w-]+))?')
_OLD_FOLDER_RE = re.compile(r'mega\.(?:nz|co\.nz)/#F!([\w-]+)!([\w-]+)(?:[!?/]([\w-]+))?')


def parse_folder_link(link):
    """Enlace de carpeta de Mega -> (handle, clave, id_de_nodo|None, 'file'|'folder'|None)."""
    m = _FOLDER_RE.search(link)
    if m:
        return m.group(1), m.group(2), m.group(4), m.group(3)
    m = _OLD_FOLDER_RE.search(link)
    if m:
        return m.group(1), m.group(2), m.group(3), ('folder' if m.group(3) else None)
    raise ValueError("Enlace de carpeta de Mega no válido")


def is_folder_link(link):
    return bool(_FOLDER_RE.search(link) or _OLD_FOLDER_RE.search(link))


def parse_link(link):
    """Valida un enlace de Mega: archivo suelto o archivo dentro de una carpeta compartida."""
    if is_folder_link(link):
        handle, key, node, kind = parse_folder_link(link)
        if kind == 'file' and node:
            return node, key
        raise ValueError("Es una carpeta de Mega: ábrela desde el menú (mega_folder) para ver sus archivos")
    m = re.search(r'mega\.(?:nz|co\.nz)/file/([\w-]+)#([\w-]+)', link) or \
        re.search(r'mega\.(?:nz|co\.nz)/#!([\w-]+)!([\w-]+)', link)
    if not m:
        raise ValueError("Enlace Mega no válido")
    return m.group(1), m.group(2)


# ---------- carpetas compartidas ----------
_fcache = {}


def _api(handle, body):
    r = requests.post(API, params={'id': int(time.time() * 1000) % 10 ** 9, 'n': handle},
                      data=json.dumps(body), timeout=20)
    d = r.json()
    return d[0] if isinstance(d, list) else d


def _xor16(raw):
    return bytes(a ^ b for a, b in zip(raw[:16], raw[16:32]))


def folder_nodes(handle, key):
    """Todos los nodos de una carpeta compartida: {id: {id, parent, folder, name, size, key}}."""
    c = _fcache.get(handle)
    if c and time.time() - c['t'] < 1800:
        return c['nodes']
    d = _api(handle, [{'a': 'f', 'c': 1, 'r': 1}])
    if isinstance(d, int):
        raise RuntimeError("Mega devolvió error %s (carpeta caída, privada o bloqueada)" % d)
    master = b64d(key)
    nodes = {}
    for n in d.get('f', []):
        try:
            raw = None
            for part in n.get('k', '').split('/'):
                if ':' in part:
                    raw = b64d(part.split(':', 1)[1])
                    break
            if not raw:
                continue
            dec = AES.new(master[:16], AES.MODE_ECB).decrypt(raw[:len(raw) - len(raw) % 16])
            is_folder = n.get('t') != 0
            akey = dec[:16] if is_folder else _xor16(dec)
            name = n['h']
            try:
                at = AES.new(akey, AES.MODE_CBC, iv=b'\0' * 16).decrypt(b64d(n['a']))
                if at.startswith(b'MEGA'):
                    name = json.loads(at[4:].rstrip(b'\0').decode('utf-8', 'ignore')).get('n', name)
            except Exception:
                pass
            nodes[n['h']] = {'id': n['h'], 'parent': n.get('p', ''), 'folder': is_folder,
                             'name': name, 'size': n.get('s', 0), 'key': dec}
        except Exception:
            continue
    if not nodes:
        raise RuntimeError("No se pudo leer la carpeta de Mega (¿clave incorrecta?)")
    _fcache[handle] = {'t': time.time(), 'nodes': nodes}
    return nodes


def list_folder(link, sub=None):
    """Contenido de una carpeta de Mega (o de una subcarpeta 'sub'): lista de nodos ordenada por nombre."""
    handle, key, node, kind = parse_folder_link(link)
    nodes = folder_nodes(handle, key)
    parent = sub or (node if kind == 'folder' and node in nodes else handle)
    out = [n for n in nodes.values() if n['parent'] == parent]
    out.sort(key=lambda n: (not n['folder'], n['name'].lower()))
    return handle, key, out


def get_info(link):
    if is_folder_link(link):
        return _get_info_folder(link)
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

def _get_info_folder(link):
    handle, key, node, kind = parse_folder_link(link)
    ck = handle + '/' + str(node)
    c = _cache.get(ck)
    if c and time.time() - c['t'] < 1800:
        return c
    n = folder_nodes(handle, key).get(node)
    if not n or n['folder']:
        raise RuntimeError("Archivo no encontrado en la carpeta de Mega")
    d = _api(handle, [{'a': 'g', 'g': 1, 'n': node}])
    if isinstance(d, int):
        raise RuntimeError("Mega devolvió error %s (enlace caído o bloqueado)" % d)
    dec = n['key']
    c = {'t': time.time(), 'url': d['g'], 'size': d['s'], 'key': _xor16(dec), 'nonce': dec[16:24], 'name': n['name']}
    _cache[ck] = c
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
