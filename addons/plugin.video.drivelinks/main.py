# -*- coding: utf-8 -*-
"""Drive Links - addon de Kodi para vídeos, series y fotos de Google Drive (enlaces públicos)."""
import sys
import urllib.parse as up

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib import db, drive

HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
DLG = xbmcgui.Dialog()


def u(**kw):
    return BASE + '?' + up.urlencode(kw)


def notify(msg, icon=xbmcgui.NOTIFICATION_INFO):
    DLG.notification('Drive Links', msg, icon, 4000)


def add_dir(label, url, ctx=None):
    li = xbmcgui.ListItem(label=label)
    if ctx:
        li.addContextMenuItems(ctx)
    xbmcplugin.addDirectoryItem(HANDLE, url, li, True)


def add_action(label, url):
    li = xbmcgui.ListItem(label=label)
    xbmcplugin.addDirectoryItem(HANDLE, url, li, False)


def ctx_item(item):
    return [
        ('Editar título', 'RunPlugin(%s)' % u(mode='edit', id=item['id'])),
        ('Eliminar de la biblioteca', 'RunPlugin(%s)' % u(mode='delete', id=item['id'])),
    ]


# ------------------------------------------------------------------ menús
def root():
    add_dir('[B]Películas / Vídeos[/B]', u(mode='movies'))
    add_dir('[B]Series[/B]', u(mode='series'))
    add_dir('[B]Fotos[/B]', u(mode='albums'))
    add_dir('Buscar', u(mode='search'))
    add_action('[COLOR lime]+ Añadir enlace de Drive[/COLOR]', u(mode='add'))
    add_action('[COLOR lime]+ Importar carpeta de Drive[/COLOR]', u(mode='import'))
    add_action('Ayuda', u(mode='help'))
    xbmcplugin.endOfDirectory(HANDLE)


def playable_item(item, label=None):
    li = xbmcgui.ListItem(label=label or item['title'])
    li.setProperty('IsPlayable', 'true')
    tag = li.getVideoInfoTag()
    tag.setTitle(item['title'])
    if item['type'] == 'series':
        tag.setMediaType('episode')
        tag.setTvShowTitle(item.get('series', ''))
        tag.setSeason(int(item.get('season', 1)))
        tag.setEpisode(int(item.get('episode', 0)))
    else:
        tag.setMediaType('movie')
    li.addContextMenuItems(ctx_item(item))
    return li


def list_movies():
    items = sorted([i for i in db.load() if i['type'] == 'movie'],
                   key=lambda i: i['title'].lower())
    for it in items:
        xbmcplugin.addDirectoryItem(HANDLE, u(mode='play', id=it['id']),
                                    playable_item(it), False)
    xbmcplugin.setContent(HANDLE, 'movies')
    xbmcplugin.endOfDirectory(HANDLE)


def list_series():
    names = sorted({i['series'] for i in db.load() if i['type'] == 'series'},
                   key=str.lower)
    for n in names:
        add_dir(n, u(mode='seasons', series=n),
                [('Eliminar serie completa',
                  'RunPlugin(%s)' % u(mode='delete_group', kind='series', key='series', value=n))])
    xbmcplugin.setContent(HANDLE, 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def list_seasons(series):
    seasons = sorted({int(i.get('season', 1)) for i in db.load()
                      if i['type'] == 'series' and i['series'] == series})
    for s in seasons:
        add_dir('Temporada %d' % s, u(mode='episodes', series=series, season=s))
    xbmcplugin.setContent(HANDLE, 'seasons')
    xbmcplugin.endOfDirectory(HANDLE)


def list_episodes(series, season):
    eps = sorted([i for i in db.load() if i['type'] == 'series' and i['series'] == series
                  and int(i.get('season', 1)) == int(season)],
                 key=lambda i: int(i.get('episode', 0)))
    for it in eps:
        label = '%dx%02d - %s' % (int(it.get('season', 1)), int(it.get('episode', 0)), it['title'])
        xbmcplugin.addDirectoryItem(HANDLE, u(mode='play', id=it['id']),
                                    playable_item(it, label), False)
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


def list_albums():
    photos = [i for i in db.load() if i['type'] == 'photo']
    albums = sorted({i.get('album', 'Sin álbum') for i in photos}, key=str.lower)
    for a in albums:
        add_dir('%s (%d)' % (a, sum(1 for p in photos if p.get('album', 'Sin álbum') == a)),
                u(mode='photos', album=a),
                [('Eliminar álbum completo',
                  'RunPlugin(%s)' % u(mode='delete_group', kind='photo', key='album', value=a))])
    xbmcplugin.endOfDirectory(HANDLE)


def list_photos(album):
    photos = sorted([i for i in db.load() if i['type'] == 'photo'
                     and i.get('album', 'Sin álbum') == album],
                    key=lambda i: i['title'].lower())
    add_action('[COLOR yellow]▶ Presentación de diapositivas[/COLOR]', u(mode='slideshow', album=album))
    for it in photos:
        li = xbmcgui.ListItem(label=it['title'])
        img = drive.image_url(it['id'])
        li.setArt({'thumb': img, 'icon': img})
        li.setInfo('pictures', {'title': it['title']})
        li.addContextMenuItems(ctx_item(it))
        xbmcplugin.addDirectoryItem(HANDLE, img, li, False)
    xbmcplugin.setContent(HANDLE, 'images')
    xbmcplugin.endOfDirectory(HANDLE)


def search():
    q = DLG.input('Buscar (título)', type=xbmcgui.INPUT_ALPHANUM)
    if not q:
        return
    q = q.lower()
    for it in db.load():
        if it['type'] in ('movie', 'series') and q in it['title'].lower():
            label = it['title']
            if it['type'] == 'series':
                label = '%s - %dx%02d %s' % (it['series'], int(it.get('season', 1)),
                                             int(it.get('episode', 0)), it['title'])
            xbmcplugin.addDirectoryItem(HANDLE, u(mode='play', id=it['id']),
                                        playable_item(it, label), False)
    xbmcplugin.endOfDirectory(HANDLE)


# ------------------------------------------------------------------ acciones
def play(file_id):
    try:
        url = drive.resolve_video(file_id)
    except Exception as e:
        xbmc.log('DriveLinks error: %s' % e, xbmc.LOGERROR)
        url = None
    if not url:
        DLG.ok('Drive Links',
               'No se puede reproducir el archivo.\n\nComprueba que está compartido como '
               '"Cualquier persona con el enlace" y que no se ha superado la cuota de descargas de Drive.')
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    li = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def slideshow(album):
    # Pasa por la propia carpeta del plugin para que Kodi lea las imágenes
    xbmc.executebuiltin('SlideShow(%s,recursive)' % u(mode='photos_plain', album=album))


def photos_plain(album):
    for it in [i for i in db.load() if i['type'] == 'photo'
               and i.get('album', 'Sin álbum') == album]:
        li = xbmcgui.ListItem(label=it['title'])
        img = drive.image_url(it['id'])
        li.setArt({'thumb': img})
        xbmcplugin.addDirectoryItem(HANDLE, img, li, False)
    xbmcplugin.setContent(HANDLE, 'images')
    xbmcplugin.endOfDirectory(HANDLE)


def ask_number(prompt, default):
    v = DLG.numeric(0, prompt, str(default))
    try:
        return int(v)
    except Exception:
        return default


def add_link():
    while True:
        link = DLG.input('Pega el enlace de Drive (archivo)', type=xbmcgui.INPUT_ALPHANUM)
        if not link:
            return
        fid = drive.extract_id(link)
        if not fid:
            notify('Enlace no válido', xbmcgui.NOTIFICATION_ERROR)
            return
        if drive.is_folder_link(link):
            DLG.ok('Drive Links', 'Ese enlace es una carpeta. Usa "Importar carpeta de Drive".')
            return
        t = DLG.select('Tipo de contenido', ['Película / vídeo', 'Episodio de serie', 'Foto'])
        if t < 0:
            return
        suggested = drive.clean_title(drive.get_file_name(fid))
        title = DLG.input('Título', defaultt=suggested, type=xbmcgui.INPUT_ALPHANUM)
        if not title:
            return
        item = {'id': fid, 'title': title}
        if t == 0:
            item['type'] = 'movie'
        elif t == 1:
            serie = DLG.input('Nombre de la serie', type=xbmcgui.INPUT_ALPHANUM)
            if not serie:
                return
            se = drive.parse_se(suggested) or (1, 1)
            item.update(type='series', series=serie,
                        season=ask_number('Temporada', se[0]),
                        episode=ask_number('Episodio', se[1]))
        else:
            item.update(type='photo', album=DLG.input('Álbum', defaultt='Mis fotos',
                                                      type=xbmcgui.INPUT_ALPHANUM) or 'Mis fotos')
        db.add_many([item])
        notify('Añadido: %s' % title)
        if not DLG.yesno('Drive Links', '¿Añadir otro enlace?'):
            break
    xbmc.executebuiltin('Container.Refresh')


def import_folder():
    link = DLG.input('Pega el enlace de la CARPETA de Drive', type=xbmcgui.INPUT_ALPHANUM)
    fid = drive.extract_id(link)
    if not fid:
        return
    mode = DLG.select('¿Qué contiene la carpeta?',
                      ['Películas / vídeos', 'Una serie (carpetas = temporadas)', 'Fotos'])
    if mode < 0:
        return
    try:
        title, _ = drive.list_folder(fid)
    except Exception as e:
        DLG.ok('Drive Links', 'No se pudo leer la carpeta.\nComprueba que es pública.\n\n%s' % e)
        return
    series_name = None
    if mode == 1:
        series_name = DLG.input('Nombre de la serie', defaultt=title, type=xbmcgui.INPUT_ALPHANUM)
        if not series_name:
            return

    found = []
    prog = xbmcgui.DialogProgress()
    prog.create('Drive Links', 'Leyendo carpeta...')

    def walk(folder_id, folder_name, depth, season):
        if prog.iscanceled() or depth > 4:
            return
        prog.update(0, 'Leyendo: %s' % folder_name)
        _, entries = drive.list_folder(folder_id)
        entries.sort(key=lambda e: e['name'].lower())
        counter = 0
        for e in entries:
            if e['folder']:
                s = drive.parse_season(e['name']) or (season + 1 if mode == 1 else season)
                walk(e['id'], e['name'], depth + 1, s)
                continue
            k = drive.kind_of(e['name'])
            counter += 1
            if mode in (0, 1) and k == 'video':
                if mode == 0:
                    found.append({'id': e['id'], 'type': 'movie',
                                  'title': drive.clean_title(e['name'])})
                else:
                    se = drive.parse_se(e['name'])
                    found.append({'id': e['id'], 'type': 'series', 'series': series_name,
                                  'season': se[0] if se else season,
                                  'episode': se[1] if se else counter,
                                  'title': drive.clean_title(e['name'])})
            elif mode == 2 and k == 'image':
                found.append({'id': e['id'], 'type': 'photo', 'album': folder_name,
                              'title': drive.clean_title(e['name'])})

    try:
        walk(fid, title, 0, 0 if mode == 1 else 1)
        if mode == 1:
            for f in found:           # si no hubo subcarpetas, todo es temporada 1
                if f['season'] == 0:
                    f['season'] = 1
    except Exception as e:
        prog.close()
        DLG.ok('Drive Links', 'Error leyendo la carpeta:\n%s' % e)
        return
    prog.close()
    n = db.add_many(found)
    DLG.ok('Drive Links', 'Importados %d elementos nuevos (%d encontrados).' % (n, len(found)))
    xbmc.executebuiltin('Container.Refresh')


def edit(file_id):
    for it in db.load():
        if it['id'] == file_id:
            new = DLG.input('Nuevo título', defaultt=it['title'], type=xbmcgui.INPUT_ALPHANUM)
            if new:
                db.update(file_id, title=new)
                xbmc.executebuiltin('Container.Refresh')
            return


def delete(file_id):
    if DLG.yesno('Drive Links', '¿Eliminar este elemento de la biblioteca?\n(No se borra de tu Drive)'):
        db.remove(file_id)
        xbmc.executebuiltin('Container.Refresh')


def delete_group(kind, key, value):
    if DLG.yesno('Drive Links', '¿Eliminar "%s" de la biblioteca?\n(No se borra de tu Drive)' % value):
        db.remove_group(kind, key, value)
        xbmc.executebuiltin('Container.Refresh')


def help_():
    DLG.textviewer('Ayuda - Drive Links',
        'CÓMO USAR\n\n'
        '1. En Drive, clic derecho en el archivo o carpeta > Compartir > '
        'Acceso general: "Cualquier persona con el enlace" (rol Lector).\n'
        '2. Copia el enlace.\n'
        '3. En el addon: "Añadir enlace" (archivo suelto) o "Importar carpeta" '
        '(toda una carpeta de una vez).\n\n'
        'SERIES\n'
        'Al importar una carpeta como serie, cada subcarpeta es una temporada '
        '("Temporada 1", "T2", "Season 3"...). Los nombres tipo S01E05 o 1x05 se '
        'detectan automáticamente.\n\n'
        'LÍMITES DE GOOGLE\n'
        'Drive limita las descargas de archivos muy populares o grandes en 24 h. '
        'Si falla, reintenta más tarde o haz una copia del archivo (Hacer una copia) en tu Drive.\n\n'
        'Las carpetas con muchísimos archivos pueden listarse de forma incompleta; '
        'si pasa, divídelas en subcarpetas.')


# ------------------------------------------------------------------ router
def router():
    p = dict(up.parse_qsl(sys.argv[2][1:]))
    mode = p.get('mode')
    if mode is None:
        root()
    elif mode == 'movies':
        list_movies()
    elif mode == 'series':
        list_series()
    elif mode == 'seasons':
        list_seasons(p['series'])
    elif mode == 'episodes':
        list_episodes(p['series'], p['season'])
    elif mode == 'albums':
        list_albums()
    elif mode == 'photos':
        list_photos(p['album'])
    elif mode == 'photos_plain':
        photos_plain(p['album'])
    elif mode == 'slideshow':
        slideshow(p['album'])
    elif mode == 'search':
        search()
    elif mode == 'play':
        play(p['id'])
    elif mode == 'add':
        add_link()
    elif mode == 'import':
        import_folder()
    elif mode == 'edit':
        edit(p['id'])
    elif mode == 'delete':
        delete(p['id'])
    elif mode == 'delete_group':
        delete_group(p['kind'], p['key'], p['value'])
    elif mode == 'help':
        help_()


router()
