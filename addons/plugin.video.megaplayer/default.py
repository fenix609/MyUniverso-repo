# -*- coding: utf-8 -*-
import os, re, sys, json
from urllib.parse import urlencode, parse_qsl, quote
from urllib.request import urlopen
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

ADDON = xbmcaddon.Addon()
sys.path.insert(0, os.path.join(ADDON.getAddonInfo('path'), 'resources', 'lib'))
from accounts import get_accounts

HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
PORT = int(ADDON.getSetting('port') or 48765)
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


def stream_url(acc, n):
    return '%s/stream/%s/%s/%s' % (SRV, acc, n['h'], quote(n['name']))


def notify(msg):
    xbmcgui.Dialog().notification('MEGA Player', msg, xbmcgui.NOTIFICATION_INFO, 4000)


def add(label, u, folder, li=None):
    xbmcplugin.addDirectoryItem(HANDLE, u, li or xbmcgui.ListItem(label), folder)


def root_menu():
    accs = get_accounts()
    if not accs:
        xbmcgui.Dialog().ok('MEGA Player', 'Añade al menos una cuenta MEGA en los ajustes del addon.')
        ADDON.openSettings()
        return xbmcplugin.endOfDirectory(HANDLE, False)
    for a in accs:
        add(a['name'], url(a='folder', acc=a['id'], h=''), True)
    add('Reproducir magnet / torrent (pegar enlace)', url(a='magnet'), False)
    add('Exportar vídeos a la biblioteca de Kodi (.strm)', url(a='export'), False)
    add('Refrescar nubes', url(a='refresh'), False)
    add('Ajustes', url(a='settings'), False)
    xbmcplugin.endOfDirectory(HANDLE)


def folder(acc, h):
    items = api('/list', acc=acc, parent=h)
    thumbs = ADDON.getSetting('thumbs') != 'false'
    n_img = 0
    for n in items:
        e = ext(n['name'])
        if n['t'] != 0:
            add(n['name'], url(a='folder', acc=acc, h=n['h']), True)
        elif e in VIDEO or e in AUDIO:
            li = xbmcgui.ListItem(n['name'])
            li.setInfo('video' if e in VIDEO else 'music', {'title': n['name']})
            li.setProperty('IsPlayable', 'true')
            add(n['name'], url(a='play', acc=acc, h=n['h'], p=h, name=n['name']), False, li)
        elif e in IMAGE:
            n_img += 1
            li = xbmcgui.ListItem(n['name'])
            li.setInfo('pictures', {'title': n['name']})
            if thumbs:
                li.setArt({'thumb': stream_url(acc, n), 'icon': stream_url(acc, n)})
            add(n['name'], stream_url(acc, n), False, li)
        elif e in ('.torrent', '.magnet'):
            add(n['name'], url(a='torrent', acc=acc, h=n['h'], name=n['name']), False,
                xbmcgui.ListItem('[Torrent] ' + n['name']))
    xbmcplugin.setContent(HANDLE, 'images' if n_img > len(items) / 2 else 'files')
    xbmcplugin.endOfDirectory(HANDLE)


def play(acc, h, p, name):
    li = xbmcgui.ListItem(path='%s/stream/%s/%s/%s' % (SRV, acc, h, quote(name)))
    li.setContentLookup(False)
    try:
        base = os.path.splitext(name)[0].lower()
        subs = [stream_url(acc, s) for s in api('/list', acc=acc, parent=p)
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


def torrent_node(acc, h, name):
    u = '%s/stream/%s/%s/%s' % (SRV, acc, h, quote(name))
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
    accs = get_accounts()
    if not accs:
        return notify('No hay cuentas configuradas')
    multi = len(accs) > 1
    if multi:
        c = xbmcgui.Dialog().select('Cuenta a exportar', ['Todas las cuentas'] + [a['name'] for a in accs])
        if c < 0:
            return
        if c > 0:
            accs = [accs[c - 1]]
    dest = dest.rstrip('/\\')
    dp = xbmcgui.DialogProgress()
    dp.create('MEGA Player', 'Exportando...')
    total = 0
    for acc in accs:
        files = [f for f in api('/walk', acc=acc['id']) if ext(f['name']) in VIDEO]
        for i, f in enumerate(files):
            if dp.iscanceled():
                break
            dp.update(int(i * 100 / max(len(files), 1)), '%s: %s' % (acc['name'], f['path']))
            rel = [safe(x) for x in f['path'].split('/')]
            rel[-1] = os.path.splitext(rel[-1])[0] + '.strm'
            if multi:
                rel.insert(0, safe(acc['name']))
            full = dest + '/' + '/'.join(rel)
            xbmcvfs.mkdirs(full.rsplit('/', 1)[0] + '/')
            fh = xbmcvfs.File(full, 'w')
            fh.write(stream_url(acc['id'], f))
            fh.close()
            total += 1
    dp.close()
    xbmcgui.Dialog().ok('MEGA Player', 'Exportados %d vídeos.\n\nAñade la carpeta como fuente en Kodi (Vídeos > Archivos > Añadir vídeos), '
                        'elige "Películas" o "Series" y un scraper (TMDb) para obtener carátulas y sinopsis.' % total)


def refresh():
    for a in get_accounts():
        try:
            api('/refresh', acc=a['id'])
        except Exception as e:
            xbmcgui.Dialog().ok('MEGA Player', 'No se pudo actualizar %s:\n%s' % (a['name'], e))
    notify('Nubes actualizadas')
    xbmc.executebuiltin('Container.Refresh')


def router(params):
    a = params.get('a')
    acc = params.get('acc', '1')
    try:
        if not a:
            root_menu()
        elif a == 'folder':
            folder(acc, params.get('h', ''))
        elif a == 'play':
            play(acc, params['h'], params.get('p', ''), params['name'])
        elif a == 'torrent':
            torrent_node(acc, params['h'], params['name'])
        elif a == 'magnet':
            magnet_prompt()
        elif a == 'export':
            export()
        elif a == 'refresh':
            refresh()
        elif a == 'settings':
            ADDON.openSettings()
    except Exception as e:
        xbmc.log('[MEGA Player] %r' % e, xbmc.LOGERROR)
        xbmcgui.Dialog().ok('MEGA Player', 'Error: %s\n\nSi acabas de instalar el addon, reinicia Kodi para iniciar el servicio local.' % e)
        if a == 'play':
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


router(dict(parse_qsl(sys.argv[2][1:])))
