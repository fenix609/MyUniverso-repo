# -*- coding: utf-8 -*-
"""Google Drive API v3 (solo lectura) usando la sesión del usuario."""
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

import xbmcaddon
import xbmcgui

from . import auth

API = 'https://www.googleapis.com/drive/v3'
FOLDER_MIME = 'application/vnd.google-apps.folder'
SHORTCUT_MIME = 'application/vnd.google-apps.shortcut'
PROXY_PORT = 8766
PROXY_PROP = 'drivelinks.proxy_key'


class ApiError(Exception):
    pass


def _json(path, params):
    token = auth.get_token()
    url = API + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode('utf-8'))['error']['message']
        except Exception:
            msg = 'HTTP %d' % e.code
        raise ApiError(msg)
    except urllib.error.URLError as e:
        raise ApiError('Sin conexión: %s' % e.reason)


def _esc(text):
    return text.replace('\\', '\\\\').replace("'", "\\'")


def _thumb(link):
    return re.sub(r'=s\d+$', '=s512', link) if link else ''


def query(q, limit=3000):
    out, page = [], None
    while True:
        params = {'q': q, 'pageSize': 1000, 'orderBy': 'folder,name',
                  'fields': 'nextPageToken,files(id,name,mimeType,thumbnailLink)',
                  'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true'}
        if page:
            params['pageToken'] = page
        data = _json('/files', params)
        for f in data.get('files', []):
            if f['mimeType'] == SHORTCUT_MIME:
                continue
            out.append({'id': f['id'], 'name': f['name'], 'mime': f['mimeType'],
                        'folder': f['mimeType'] == FOLDER_MIME,
                        'thumb': _thumb(f.get('thumbnailLink'))})
        page = data.get('nextPageToken')
        if not page or len(out) >= limit:
            return out


def list_children(folder_id):
    return query("'%s' in parents and trashed=false" % _esc(folder_id))


def list_folder(folder_id):
    """Misma forma que drive.list_folder: (titulo, entradas)."""
    name = _json('/files/' + urllib.parse.quote(folder_id, safe=''),
                 {'fields': 'name', 'supportsAllDrives': 'true'}).get('name', 'Carpeta')
    return name, list_children(folder_id)


def shared_with_me():
    return query('sharedWithMe=true and trashed=false')


def search(text):
    return query("name contains '%s' and trashed=false and "
                 "(mimeType contains 'video/' or mimeType contains 'image/' or "
                 "mimeType = '%s')" % (_esc(text), FOLDER_MIME))


def _media_url(file_id, token):
    return '%s/files/%s?alt=media&supportsAllDrives=true|Authorization=%s' % (
        API, urllib.parse.quote(file_id, safe=''),
        urllib.parse.quote('Bearer ' + token, safe=''))


def _proxy_url(file_id):
    """URL del proxy local (renueva el token solo) si el servicio está activo."""
    try:
        if not xbmcaddon.Addon().getSettingBool('use_proxy'):
            return None
        key = xbmcgui.Window(10000).getProperty(PROXY_PROP)
        if not key:
            return None
        socket.create_connection(('127.0.0.1', PROXY_PORT), timeout=0.5).close()
        return 'http://127.0.0.1:%d/%s/%s' % (PROXY_PORT, key, urllib.parse.quote(file_id, safe=''))
    except Exception:
        return None


def stream_url(file_id):
    """URL reproducible. Lanza ApiError si no hay acceso al archivo."""
    _json('/files/' + urllib.parse.quote(file_id, safe=''),
          {'fields': 'id', 'supportsAllDrives': 'true'})        # comprueba acceso
    proxy = _proxy_url(file_id)
    if proxy:
        return proxy
    return _media_url(file_id, auth.get_token(min_valid=3300))   # sin servicio: token recién renovado


def image_url(file_id):
    return _media_url(file_id, auth.get_token())


def fetch_file(file_id, name, dest_dir):
    """Descarga un archivo pequeño (subtítulo) con la sesión del usuario."""
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    safe = re.sub(r'[\\/:*?"<>|]', '_', name)
    path = os.path.join(dest_dir, '%s_%s' % (file_id[:6], safe))
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    url = '%s/files/%s?alt=media&supportsAllDrives=true' % (API, urllib.parse.quote(file_id, safe=''))
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + auth.get_token()})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(5 * 1024 * 1024)
    with open(path, 'wb') as f:
        f.write(data)
    return path
