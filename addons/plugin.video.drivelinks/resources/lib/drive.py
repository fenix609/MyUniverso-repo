# -*- coding: utf-8 -*-
"""Utilidades de Google Drive SIN cuenta ni API: solo enlaces públicos."""
import html
import http.cookiejar
import os
import re
import urllib.parse
import urllib.request

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0 Safari/537.36')

VIDEO_EXT = ('.mkv', '.mp4', '.avi', '.mov', '.m4v', '.webm', '.ts',
             '.wmv', '.flv', '.mpg', '.mpeg')
IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')

_ID_PATTERNS = [
    r'/file/d/([A-Za-z0-9_-]{10,})',
    r'/folders/([A-Za-z0-9_-]{10,})',
    r'[?&]id=([A-Za-z0-9_-]{10,})',
    r'^([A-Za-z0-9_-]{20,})$',
]


def extract_id(text):
    text = (text or '').strip()
    for p in _ID_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return None


def is_folder_link(text):
    return '/folders/' in (text or '')


def kind_of(name):
    ext = os.path.splitext(name.lower())[1]
    if ext in VIDEO_EXT:
        return 'video'
    if ext in IMAGE_EXT:
        return 'image'
    return None


def clean_title(name):
    base = os.path.splitext(name)[0]
    return re.sub(r'[._]+', ' ', base).strip()


def parse_se(name):
    """Devuelve (temporada, episodio) si el nombre lo indica, si no None."""
    m = re.search(r'[Ss](\d{1,2})[ ._-]*[Ee](\d{1,3})', name)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r'(?<!\d)(\d{1,2})x(\d{2,3})(?!\d)', name)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def parse_season(folder_name):
    m = re.search(r'(?:temporada|season|temp|t)[ ._-]*(\d{1,2})', folder_name, re.I)
    if m:
        return int(m.group(1))
    m = re.match(r'^\s*(\d{1,2})\s*$', folder_name)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------- red
def _get(url, opener=None, timeout=25):
    req = urllib.request.Request(url, headers={'User-Agent': UA,
                                               'Accept-Language': 'es,en;q=0.8'})
    return (opener or urllib.request.build_opener()).open(req, timeout=timeout)


def get_file_name(file_id):
    """Intenta obtener el nombre del archivo (para sugerirlo como título)."""
    try:
        page = _get('https://drive.google.com/file/d/%s/view' % file_id).read(60000)
        m = re.search(r'<title>(.*?)</title>', page.decode('utf-8', 'ignore'), re.S)
        if m:
            t = html.unescape(m.group(1)).strip()
            return re.sub(r'\s*-\s*Google Drive\s*$', '', t)
    except Exception:
        pass
    return ''


def list_folder(folder_id):
    """Lista una carpeta pública. Devuelve (titulo, [ {id,name,folder} ])."""
    page = _get('https://drive.google.com/embeddedfolderview?id=%s' % folder_id)
    page = page.read().decode('utf-8', 'ignore')
    t = re.search(r'<title>(.*?)</title>', page, re.S)
    title = html.unescape(t.group(1)).strip() if t else 'Carpeta'
    entries = []
    for block in re.split(r'<div class="flip-entry"', page)[1:]:
        mid = re.search(r'id="entry-([A-Za-z0-9_-]+)"', block)
        mhref = re.search(r'href="([^"]+)"', block)
        mname = re.search(r'class="flip-entry-title">(.*?)</div>', block, re.S)
        if not (mid and mhref and mname):
            continue
        entries.append({
            'id': mid.group(1),
            'name': html.unescape(mname.group(1)).strip(),
            'folder': '/folders/' in mhref.group(1),
        })
    return title, entries


def resolve_video(file_id):
    """
    Devuelve una URL reproducible por Kodi (con cabeceras) o None si el archivo
    no es accesible. Gestiona la página de "no se puede analizar por virus"
    de los archivos grandes.
    """
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    url = ('https://drive.usercontent.google.com/download?id=%s'
           '&export=download&confirm=t' % file_id)
    resp = opener.open(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=25)
    ctype = resp.headers.get('Content-Type', '')
    final = resp.geturl()
    if 'text/html' in ctype:
        page = resp.read().decode('utf-8', 'ignore')
        resp.close()
        form = re.search(r'<form[^>]+action="([^"]+)"', page)
        if not form:
            return None  # sin permisos, borrado o cuota excedida
        fields = dict(re.findall(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', page))
        final = html.unescape(form.group(1)) + '?' + urllib.parse.urlencode(fields)
        resp = opener.open(urllib.request.Request(final, headers={'User-Agent': UA}), timeout=25)
        if 'text/html' in resp.headers.get('Content-Type', ''):
            resp.close()
            return None
        final = resp.geturl()
    resp.close()
    cookies = '; '.join('%s=%s' % (c.name, c.value) for c in cj)
    headers = 'User-Agent=%s' % urllib.parse.quote(UA, safe='')
    if cookies:
        headers += '&Cookie=%s' % urllib.parse.quote(cookies, safe='')
    return final + '|' + headers


def image_url(file_id):
    return 'https://drive.google.com/thumbnail?id=%s&sz=w1920' % file_id
