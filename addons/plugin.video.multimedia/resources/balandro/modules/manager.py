# -*- coding: utf-8 -*-
"""Gestor de Servidores (canales): activar/desactivar, añadir nuevos y borrar los añadidos."""

import os, re, io, json, zipfile

import xbmc

from platformcode import config, logger, platformtools
from core import channeltools

from core.item import Item


fanart = os.path.join(config.get_runtime_path(), 'fanart.jpg')

_CATS = ('movie', 'tvshow')


def _builtin_ids():
    d = os.path.join(config.get_runtime_path(), 'channels')
    return set(f[:-5] for f in os.listdir(d) if f.endswith('.json'))


def _user_ids():
    d = config.get_user_channels_path()
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith('.json'))


def mainlist(item):
    logger.info()
    itemlist = []

    item.category = 'Gestionar Servidores'

    todos = _channels()
    activos = len([c for c in todos if c['status'] != -1])

    itemlist.append(item.clone(action='list_servers', title='[B]Activar / Desactivar servidores[/B]  (%d de %d activos)' % (activos, len(todos)),
                               plot='Los desactivados no salen en menús ni en la búsqueda general. Se pueden volver a activar cuando quieras.',
                               thumbnail=config.get_thumb('settings'), fanart=fanart, text_color='yellow'))

    itemlist.append(item.clone(action='add_server', title='[B]Añadir servidor nuevo[/B]',
                               plot='Importa un servidor (ficheros .py y .json, o un .zip) desde tu dispositivo o desde una dirección web.',
                               thumbnail=config.get_thumb('help'), fanart=fanart, text_color='chartreuse'))

    n_user = len(_user_ids())
    itemlist.append(item.clone(action='list_user', title='[B]Servidores añadidos por mí[/B]  (%d)' % n_user,
                               plot='Aquí se pueden borrar del todo los servidores que añadiste.',
                               thumbnail=config.get_thumb('stack'), fanart=fanart, text_color='darksalmon'))

    itemlist.append(item.clone(action='all_on', title='Activar todos', folder=False, thumbnail=config.get_thumb('help'), fanart=fanart, text_color='lime'))
    itemlist.append(item.clone(action='all_off', title='Desactivar todos', folder=False, thumbnail=config.get_thumb('help'), fanart=fanart, text_color='red'))

    return itemlist


def _channels():
    lista = []
    for ch in channeltools.get_channels_list(filtros={}):
        cats = ch.get('categories', [])
        if 'adults' in cats: continue
        if not any(c in cats for c in _CATS): continue
        lista.append(ch)
    return lista


def list_servers(item):
    logger.info()
    itemlist = []

    item.category = 'Activar / Desactivar'

    for ch in _channels():
        off = ch['status'] == -1
        tag = '[COLOR red][B]OFF[/B][/COLOR]' if off else '[COLOR lime][B]ON [/B][/COLOR]'
        tipo = []
        if 'movie' in ch['categories']: tipo.append('películas')
        if 'tvshow' in ch['categories']: tipo.append('series')
        plot = ', '.join(tipo) + ('\nAñadido por el usuario' if ch['id'] in _user_ids() else '')
        itemlist.append(item.clone(action='toggle', canal=ch['id'], nuevo=(0 if off else -1), folder=False,
                                   title='%s  %s' % (tag, ch['name']), plot=plot,
                                   thumbnail=ch['thumbnail'], fanart=fanart,
                                   text_color=('gray' if off else 'white')))

    if not itemlist: platformtools.dialog_notification(config.__addon_name, 'No hay servidores', time=3000)

    return itemlist


def toggle(item):
    config.set_setting('status', item.nuevo, item.canal)
    txt = 'Activado' if item.nuevo != -1 else 'Desactivado'
    platformtools.dialog_notification(config.__addon_name, '%s: %s' % (item.canal, txt), time=1500)
    platformtools.itemlist_refresh()


def _set_all(valor):
    for ch in _channels(): config.set_setting('status', valor, ch['id'])
    platformtools.dialog_notification(config.__addon_name, 'Hecho', time=1500)
    platformtools.itemlist_refresh()


def all_on(item): _set_all(0)


def all_off(item):
    if platformtools.dialog_yesno(config.__addon_name, '¿Desactivar TODOS los servidores?', 'Después activa solo los que quieras.'): _set_all(-1)


# ---------------- añadir ----------------
_ID = re.compile(r'^[A-Za-z0-9_]{2,40}$')


def _install(files):
    """files: {nombre: bytes}. Instala parejas <id>.py + <id>.json válidas. Devuelve (ok, errores)."""
    ok, errs = [], []
    ids = set(n[:-3] for n in files if n.endswith('.py')) & set(n[:-5] for n in files if n.endswith('.json'))

    if not ids: return ok, ['No hay una pareja .py + .json con el mismo nombre']

    dest = config.get_user_channels_path()
    builtin = _builtin_ids()

    for cid in sorted(ids):
        try:
            if not _ID.match(cid): raise Exception('nombre no válido')
            if cid in builtin: raise Exception('ya existe un servidor incluido con ese nombre')

            datos = json.loads(files[cid + '.json'].decode('utf-8-sig'))
            if datos.get('id') != cid: raise Exception('el "id" del .json no coincide con el nombre')
            if not datos.get('name'): raise Exception('falta "name" en el .json')

            src = files[cid + '.py'].decode('utf-8-sig')
            compile(src, cid + '.py', 'exec')
            if 'def mainlist' not in src: raise Exception('el .py no tiene mainlist')

            datos['active'] = True
            for nombre, contenido in ((cid + '.py', src.encode('utf-8')), (cid + '.json', json.dumps(datos, ensure_ascii=False, indent=2).encode('utf-8'))):
                with io.open(os.path.join(dest, nombre), 'wb') as f: f.write(contenido)

            config.set_setting('status', 0, cid)
            ok.append(cid)
        except Exception as e:
            errs.append('%s: %s' % (cid, e))

    return ok, errs


def _files_from_zip(data):
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            nombre = os.path.basename(info.filename)  # se ignoran carpetas/rutas (evita escribir fuera)
            if info.is_dir() or not nombre.endswith(('.py', '.json')): continue
            if info.file_size > 2 * 1024 * 1024: continue
            files[nombre] = z.read(info)
    return files


def _read_local(path):
    with io.open(path, 'rb') as f: data = f.read()

    if path.lower().endswith('.zip'): return _files_from_zip(data)

    base, ext = os.path.splitext(path)
    otro = base + ('.json' if ext.lower() == '.py' else '.py')
    files = {os.path.basename(path): data}

    if os.path.exists(otro):
        with io.open(otro, 'rb') as f: files[os.path.basename(otro)] = f.read()

    return files


def _download(url):
    import requests
    r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    return r.content


def _read_url(url):
    url = url.strip()
    if url.lower().split('?')[0].endswith('.zip'): return _files_from_zip(_download(url))

    base, ext = os.path.splitext(url)
    if ext.lower() not in ('.py', '.json'): raise Exception('La dirección debe acabar en .zip, .py ó .json')

    files = {}
    for e in ('.py', '.json'):
        files[os.path.basename(base) + e] = _download(base + e)

    return files


def add_server(item):
    logger.info()

    msg = ('[COLOR red][B]Atención:[/B][/COLOR] un servidor es código Python que se ejecuta en tu dispositivo.',
           'Añade solo servidores de fuentes en las que confíes.', '¿Continuar?')
    if not platformtools.dialog_yesno(config.__addon_name + ' - Añadir servidor', msg[0], msg[1], msg[2]): return

    op = platformtools.dialog_select('Añadir servidor desde', ['Un archivo del dispositivo (.zip / .py / .json)', 'Una dirección web (URL)'])
    if op < 0: return

    try:
        if op == 0:
            import xbmcgui
            path = xbmcgui.Dialog().browseSingle(1, 'Elige el .zip, .py ó .json del servidor', 'files', '.zip|.py|.json', False, False, '')
            if not path: return
            files = _read_local(path)
        else:
            url = platformtools.dialog_input('', 'Dirección (.zip, .py ó .json)')
            if not url: return
            files = _read_url(url)

        ok, errs = _install(files)
    except Exception as e:
        logger.error('add_server: %s' % e)
        platformtools.dialog_ok(config.__addon_name, 'No se pudo añadir: %s' % e)
        return

    txt = ''
    if ok: txt += '[COLOR lime]Añadidos:[/COLOR] ' + ', '.join(ok) + '[CR]'
    if errs: txt += '[COLOR red]Con error:[/COLOR][CR]' + '[CR]'.join(errs)

    platformtools.dialog_textviewer(config.__addon_name + ' - Añadir servidor', txt or 'Nada que añadir')

    if ok: platformtools.itemlist_refresh()


# ---------------- borrar los añadidos ----------------
def list_user(item):
    logger.info()
    itemlist = []

    item.category = 'Servidores añadidos'

    for cid in _user_ids():
        itemlist.append(item.clone(action='del_user', canal=cid, folder=False, title='[COLOR red][B]Borrar[/B][/COLOR]  ' + cid, fanart=fanart, thumbnail=config.get_thumb('help')))

    if not itemlist: platformtools.dialog_notification(config.__addon_name, 'No has añadido ningún servidor', time=3000)

    return itemlist


def del_user(item):
    if not platformtools.dialog_yesno(config.__addon_name, '¿Borrar definitivamente el servidor [B]%s[/B]?' % item.canal): return

    d = config.get_user_channels_path()
    for e in ('.py', '.json', '.pyc'):
        p = os.path.join(d, item.canal + e)
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

    config.set_setting('status', '', item.canal)
    platformtools.dialog_notification(config.__addon_name, 'Borrado: ' + item.canal, time=2000)
    platformtools.itemlist_refresh()
