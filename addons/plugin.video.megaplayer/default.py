# -*- coding: utf-8 -*-
import os, re, sys, json
from urllib.parse import urlencode, parse_qsl, quote
from urllib.request import urlopen
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
PORT = int(ADDON.getSetting('port') or 8765)
SRV = 'http://127.0.0.1:%d' % PORT

VIDEO = {'.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.ts', '.m2ts', '.mpg', '.mpeg', '.webm', '.vob', '.iso', '.3gp', '.divx'}
IMAGE = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff'}
AUDIO = {'.mp3', '.flac', '.m4a', '.aac', '.ogg', '.wav', '.opus', '.wma'}
SUB = {'.srt', '.ass', '.ssa', '.sub', '.vtt'}


def ext(name):
    return os.path.splitext(name)[1].lower()


def url(**kw):
    return BASE + '?' + urlencode(kw)


def api(path, **q):
    full = SRV + path + ('?' + urlencode(q) if q else '')
    with urlopen(full, timeout=180) as r:
        data = json.loads(r.read().decode())
    if isinstance(data, dict) and 'error' in data:
        raise RuntimeError(data['error'])
    return data


def stream_url(n):
    return '%s/stream/%s/%s' % (SRV, n['h'], quote(n['name']))


def notify(msg):
    xbmcgui.Dialog().notification('MEGA Player', msg, xbmcgui.NOTIFICATION_INFO, 4000)


def add(label, u, folder, li=None):
    li = li or xbmcgui.ListItem(label)
    xbmcplugin.addDirectoryItem(HANDLE, u, li, folder)


def root_menu():
    add('Mi nube MEGA', url(a='folder', h=''), True)
    add('Reproducir magnet / torrent (pegar enlace)', url(a='magnet'), False)
    add('Exportar vídeos a la biblioteca de Kodi (.strm)', url(a='export'), False)
    add('Refrescar nube', url(a='refresh'), False)
    add('Ajustes', url(a='settings'), False)
    xbmcplugin.endOfDirectory(HANDLE)


def folder(h):
    items = api('/list', parent=h)
    thumbs = ADDON.getSetting('thumbs') != 'false'
    n_img = 0
    for n in items:
        e = ext(n['name'])
        if n['t'] != 0:
            add(n['name'], url(a='folder', h=n['h']), True)
        elif e in VIDEO:
            li = xbmcgui.ListItem(n['name'])
            li.setInfo('video', {'title': n['name']})
            li.setProperty('IsPlayable', 'true')
            add(n['name'], url(a='play', h=n['h'], p=h, name=n['name']), False, li)
        elif e in AUDIO:
            li = xbmcgui.ListItem(n['name'])
            li.setInfo('music', {'title': n['name']})
            li.setProperty('IsPlayable', 'true')
            add(n['name'], url(a='play', h=n['h'], p=h, name=n['name']), False, li)
        elif e in IMAGE:
            n_img += 1
            li = xbmcgui.ListItem(n['name'])
            li.setInfo('pictures', {'title': n['name']})
            if thumbs:
                li.setArt({'thumb': stream_url(n), 'icon': stream_url(n)})
            add(n['name'], stream_url(n), False, li)
        elif e in ('.torrent', '.magnet'):
            li = xbmcgui.ListItem('[Torrent] ' + n['name'])
            add(n['name'], url(a='torrent', h=n['h'], name=n['name']), False, li)
    xbmcplugin.setContent(HANDLE, 'images' if n_img > len(items) / 2 else 'files')
    xbmcplugin.endOfDirectory(HANDLE)


def play(h, p, name):
    path = '%s/stream/%s/%s' % (SRV, h, quote(name))
    li = xbmcgui.ListItem(path=path)
    li.setContentLookup(False)
    try:
        base = os.path.splitext(name)[0].lower()
        subs = [stream_url(s) for s in api('/list', parent=p)
                if s['t'] == 0 and ext(s['name']) in SUB and s['name'].lower().startswith(base)]
        if subs:
            li.setSubtitles(subs)
    except Exception:
        pass
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def torrent_engine_url(uri):
    engine = int(ADDON.getSetting('torrent_engine') or 0)
    if engine == 0:
        addon_id, target = 'plugin.video.elementum', 'plugin://plugin.video.elementum/play?uri=' + quote(uri, safe='')
    else:
        addon_id = 'plugin.video.torrest'
        if uri.startswith('magnet:'):
            target = 'plugin://plugin.video.torrest/play_magnet?magnet=' + quote(uri, safe='')
        else:
            target = 'plugin://plugin.video.torrest/play_url?url=' + quote(uri, safe='')
    if not xbmc.getCondVisibility('System.HasAddon(%s)' % addon_id):
        xbmcgui.Dialog().ok('MEGA Player', 'Instala el addon [B]%s[/B] para reproducir torrents.' % addon_id)
        return None
    return target


def play_torrent(uri):
    target = torrent_engine_url(uri)
    if target:
        xbmc.executebuiltin('PlayMedia("%s")' % target)


def torrent_node(h, name):
    u = '%s/stream/%s/%s' % (SRV, h, quote(name))
    if ext(name) == '.torrent':
        return play_torrent(u)
    with urlopen(u, timeout=30) as r:
        txt = r.read(8192).decode('utf-8', 'ignore')
    m = re.search(r'magnet:\?[^\s"\'<>]+', txt)
    if m:
        play_torrent(m.group(0))
    else:
        notify('No se encontró ningún magnet en el archivo')


def magnet_prompt():
    t = xbmcgui.Dialog().input('Magnet o URL de .torrent')
    if t.strip():
        play_torrent(t.strip())


def safe(s):
    return re.sub(r'[<>:"|?*\\]', '_', s).strip()


def export():
    dest = ADDON.getSetting('export_path')
    if not dest:
        xbmcgui.Dialog().ok('MEGA Player', 'Elige primero la carpeta destino en Ajustes > Biblioteca.')
        return ADDON.openSettings()
    dest = dest.rstrip('/\\')
    sep = '/'
    files = [f for f in api('/walk') if ext(f['name']) in VIDEO]
    dp = xbmcgui.DialogProgress()
    dp.create('MEGA Player', 'Exportando...')
    for i, f in enumerate(files):
        if dp.iscanceled():
            break
        dp.update(int(i * 100 / max(len(files), 1)), f['path'])
        rel = [safe(x) for x in f['path'].split('/')]
        rel[-1] = os.path.splitext(rel[-1])[0] + '.strm'
        full = dest + sep + sep.join(rel)
        xbmcvfs.mkdirs(full.rsplit(sep, 1)[0] + sep)
        fh = xbmcvfs.File(full, 'w')
        fh.write(stream_url(f))
        fh.close()
    dp.close()
    xbmcgui.Dialog().ok('MEGA Player', 'Exportados %d vídeos.\n\nAñade la carpeta como fuente en Kodi (Vídeos > Archivos > Añadir vídeos), '
                        'elige "Películas" o "Series" y un scraper (TMDb) para obtener carátulas y sinopsis.' % len(files))


def router(params):
    a = params.get('a')
    try:
        if not a:
            root_menu()
        elif a == 'folder':
            folder(params.get('h', ''))
        elif a == 'play':
            play(params['h'], params.get('p', ''), params['name'])
        elif a == 'torrent':
            torrent_node(params['h'], params['name'])
        elif a == 'magnet':
            magnet_prompt()
        elif a == 'export':
            export()
        elif a == 'refresh':
            api('/refresh')
            notify('Nube actualizada')
            xbmc.executebuiltin('Container.Refresh')
        elif a == 'settings':
            ADDON.openSettings()
    except Exception as e:
        xbmc.log('[MEGA Player] %r' % e, xbmc.LOGERROR)
        xbmcgui.Dialog().ok('MEGA Player', 'Error: %s\n\nSi acabas de instalar el addon, reinicia Kodi para iniciar el servicio local.' % e)
        if a == 'play':
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


router(dict(parse_qsl(sys.argv[2][1:])))
