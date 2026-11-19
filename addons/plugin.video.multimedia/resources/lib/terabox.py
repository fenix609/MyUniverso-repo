# -*- coding: utf-8 -*-
"""Resolver TeraBox (best-effort: la API no es oficial y puede cambiar)."""
import re, requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

def resolve(link, cookie):
    if not cookie:
        raise RuntimeError("Falta la cookie 'ndus' de TeraBox en los ajustes del addon")
    m = re.search(r'/s/([\w-]+)', link) or re.search(r'surl=([\w-]+)', link)
    if not m:
        raise ValueError("Enlace TeraBox no válido")
    code = m.group(1)
    host = re.search(r'https?://([^/]+)', link).group(1)
    s = requests.Session()
    s.headers.update({'User-Agent': UA, 'Referer': 'https://%s/' % host})
    s.cookies.set('ndus', cookie)

    info = None
    for surl in (code, code[1:] if code.startswith('1') else code):
        r = s.get('https://%s/api/shorturlinfo' % host,
                  params={'app_id': '250528', 'shorturl': surl, 'root': '1'}, timeout=20).json()
        if r.get('errno') == 0 and r.get('list'):
            info = r
            break
    if not info:
        raise RuntimeError("TeraBox: no se pudo leer el enlace (¿expirado o sin permiso?)")

    f = next((x for x in info['list'] if str(x.get('isdir')) == '0'), None)
    if not f:
        raise RuntimeError("TeraBox: el enlace no contiene un archivo directo")
    if f.get('dlink'):
        return f['dlink'], s.headers
    r = s.get('https://%s/share/download' % host, params={
        'app_id': '250528', 'channel': 'dubox', 'clienttype': '0', 'web': '1',
        'sign': info.get('sign', ''), 'timestamp': info.get('timestamp', ''),
        'shareid': info.get('shareid', ''), 'uk': info.get('uk', ''),
        'primaryid': info.get('shareid', ''), 'product': 'share',
        'fid_list': '[%s]' % f['fs_id']}, timeout=20).json()
    if r.get('dlink'):
        return r['dlink'], s.headers
    raise RuntimeError("TeraBox: no se obtuvo enlace de descarga (errno %s)" % r.get('errno'))
