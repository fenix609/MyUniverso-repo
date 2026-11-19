# -*- coding: utf-8 -*-

import sys

import xbmc, xbmcvfs  


if sys.version_info[0] >= 3:
    translatePath = xbmcvfs.translatePath
    long = int
    unicode = str
else:
    translatePath = xbmc.translatePath   


import os, re, xbmcaddon  


__base_url = sys.argv[0]

__addon_name = 'Servidores'
__addon_id = __base_url.replace('plugin://','').replace('/','')

__real_addon__ = xbmcaddon.Addon(id=__addon_id)

# ~ ---- Integración en el addon "multimedia" ----------------------------------------------------
# ~ Servidores vive dentro de resources/balandro. Sus ajustes NO se guardan en settings.xml del addon
# ~ anfitrión (Kodi ignora ids no declarados): se guardan en un JSON propio dentro de la carpeta de
# ~ datos y los valores por defecto se leen del settings.xml original de Servidores.
import json as _json_

__BAL_DIR__ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
__DATA_DIR__ = os.path.join(translatePath(__real_addon__.getAddonInfo('Profile')), 'balandro')


__FAST_DEFAULTS__ = {
    'search_timeout': '3',            # segundos máx. por petición durante la búsqueda
    'search_deadline': '10',          # segundos máx. en total antes de mostrar lo que haya
    'search_multithread': 'true',
    'search_limit_by_channel': '2',
    'search_no_inestables': 'true',
    'search_no_problematicos': 'true',
    'search_no_clones': 'true',
    'search_no_proxies': 'true',
    'search_no_notices': 'true',      # sin canales con protección CloudFlare (lentos/fallan)
    'search_no_cryptos': 'true',
}


class _BalandroSettings(object):
    def __init__(self):
        self._file = os.path.join(__DATA_DIR__, 'balandro_settings.json')
        self._defaults = None
        self._values = None

    def _load_defaults(self):
        d = {}
        try:
            with open(os.path.join(__BAL_DIR__, 'resources', 'settings.xml'), 'r', encoding='utf-8') as f:
                xml = f.read()
            for m in re.finditer(r'<setting\s+[^>]*?\bid="([^"]+)"[^>]*?\bdefault="([^"]*)"', xml):
                d.setdefault(m.group(1), m.group(2))
        except Exception:
            pass
        d.update(__FAST_DEFAULTS__)  # búsqueda rápida por defecto en "Servidores"
        return d

    def _load(self):
        if self._values is None:
            try:
                with open(self._file, 'r', encoding='utf-8') as f: self._values = _json_.load(f)
            except Exception:
                self._values = {}
        if self._defaults is None: self._defaults = self._load_defaults()

    def getSetting(self, name):
        self._load()
        if name in self._values: return self._values[name]
        return self._defaults.get(name, '')

    def setSetting(self, name, value):
        self._load()
        self._values[name] = value if isinstance(value, str) else str(value)
        try:
            if not os.path.exists(__DATA_DIR__): os.makedirs(__DATA_DIR__)
            with open(self._file, 'w', encoding='utf-8') as f: _json_.dump(self._values, f)
        except Exception:
            pass

    def getAddonInfo(self, key):
        if key == 'Path' or key == 'path': return __BAL_DIR__
        if key == 'Profile' or key == 'profile': return __DATA_DIR__
        if key == 'version': return '4.0.34'
        return __real_addon__.getAddonInfo(key)

    def openSettings(self):
        return __real_addon__.openSettings()

    def __getattr__(self, name):
        return getattr(__real_addon__, name)


__settings__ = _BalandroSettings()


def build_url(item):
    return __base_url + '?' + item.tourl()

def build_RunPlugin(item):
    return 'RunPlugin(%s?%s)' % (__base_url, item.tourl())

def build_ContainerRefresh(item):
    return 'Container.Refresh(%s?%s)' % (__base_url, item.tourl())

def build_ContainerUpdate(item, replace=False):
    if replace:
        return 'Container.Update(%s?%s, replace)' % (__base_url, item.tourl())
    else:
        return 'Container.Update(%s?%s)' % (__base_url, item.tourl())


def get_temp_file(filename):
    from core import filetools

    temp = os.path.join(get_data_path(), filename)

    if os.path.exists(temp): filetools.rmdirtree(temp)

    if not os.path.exists(temp): os.makedirs(temp)

    return temp


def get_runtime_path():
    return translatePath(__settings__.getAddonInfo('Path'))

def get_user_channels_path():
    # ~ Servidores añadidos por el usuario (fuera de la carpeta del addon: no se pierden al actualizar)
    dev = os.path.join(get_data_path(), 'user_channels')
    if not os.path.exists(dev): os.makedirs(dev)
    return dev


def get_data_path():
    dev = translatePath(__settings__.getAddonInfo('Profile'))
    if not os.path.exists(dev): os.makedirs(dev)
    return dev


def get_addon_version(with_fix=True):
    if with_fix:
        return __settings__.getAddonInfo('version') + get_addon_version_fix()
    else:
        return __settings__.getAddonInfo('version')

def get_addon_version_fix():
    try:
        last_fix_json = os.path.join(get_runtime_path(), 'last_fix.json')
        if os.path.exists(last_fix_json):
            with open(last_fix_json, 'r') as f: data=f.read(); f.close()
            fix = re.findall('"fix_version"\s*:\s*(\d+)', data)
            if fix:
                return '.fix%s' % fix[0]
    except:
        pass

    return ''


def get_thumb(thumb_name, theme='default', mtype='themes'):
    ficheros = {
        'movie': 'clapboard', 'tvshow': 'tv', 'documentary': 'genius', 'search': 'magnifyingglass', 
        'videolibrary': 'star', 'downloads': 'download', 'settings': 'settings', 
        'hot': 'bolt', 'help': 'help', 'genres': 'swatches'
    }

    path = os.path.join(get_runtime_path(), 'resources', 'media', mtype, theme, ficheros.get(thumb_name, thumb_name) + '.png')
    if not os.path.exists(path):
        path = os.path.join(get_runtime_path(), 'resources', 'media', mtype, theme, ficheros.get(thumb_name, thumb_name) + '.jpg')

    if os.path.exists(path):
        return path

    path = os.path.join(get_runtime_path(), 'resources', 'media', 'channels', 'thumb', thumb_name + '.jpg')
    if not os.path.exists(path):
        path = os.path.join(get_runtime_path(), 'resources', 'media', 'channels', 'thumb', thumb_name + '.png')

    if os.path.exists(path):
        return path

    return ''

def get_localized_category(categ):
    categories = {'movie': 'Películas', 'tvshow': 'Series', 
                  'documentary': 'Documentales', 'vos': 'Versiones originales',
                  'dorama': 'Dorama', 'anime': 'Anime', 'adult': 'Adultos',
                  'direct': 'Directos', 'torrent': 'Torrents'}

    return categories[categ] if categ in categories else categ


def quitar_colores(texto):
    # ~ Eliminar tags de color de un texto
    return re.sub(r'\[COLOR [^\]]*\]', '', texto.replace('[/COLOR]', '')).strip()


def text_clean(txt, disallowed_chars = '[^a-zA-Z0-9\-_()\[\]. ]+', blank_char = ' '):
    # ~ Limpiar texto de acentos y otros caracteres para generar nombres de ficheros

    import unicodedata
    try:
        txt = unicode(txt, 'utf-8')
    except: # ~ unicode is a default on python 3 
        pass

    txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore')
    txt = txt.decode('utf-8').strip()
    if blank_char != ' ': txt = txt.replace(' ', blank_char)
    txt = re.sub(disallowed_chars, '', txt)
    return str(txt)

# ~ This function will convert bytes to MB, GB, etc
def format_bytes(num):
    step_unit = 1000.0 #1024 bad the size
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < step_unit:
            return "%3.1f %s" % (num, x)

        num /= step_unit

# ~ This function will convert seconds to HhMMm
def format_seconds_to_duration(seconds):
    hours = seconds // (60*60)
    seconds %= (60*60)
    minutes = seconds // 60

    if hours == 0:
        return '%dm' % minutes

    return '%dh%02dm' % (hours, minutes)


def get_lang_preferences():
    # 0:no mostrar  1:primera 2:segunda 3:tercera
    pref_esp = get_setting('preferencia_idioma_esp', default='1')
    pref_lat = get_setting('preferencia_idioma_lat', default='2')
    pref_vos = get_setting('preferencia_idioma_vos', default='3')
    return {'Esp': pref_esp, 'Lat': pref_lat, 'VO': pref_vos}


def get_setting(name, channel="", server="", default=None):
    """
    Retorna el valor de configuracion del parametro solicitado.

    Devuelve el valor del parametro 'name' en la configuración global o en la propia del canal o servidor.

    Si se especifica el nombre de un canal o servidor se guarda en la configuración global con un prefijo channel_ o server_.
    Los parametros channel y server no deben usarse simultaneamente.
    """

    if channel:
        name = 'channel_' + channel + '_' + name
    elif server:
        name = 'server_' + server + '_' + name

    value = __settings__.getSetting(name)
    if not value:
        if default is None: default = ''
        return default

    # ~ Translate Path if start with "special://"
    if value.startswith("special://"):
        value = translatePath(value)

    # ~ hack para devolver el tipo correspondiente
    if value == "true":
        return True
    elif value == "false":
        return False
    else:
        # ~ special case return as str
        if name in ["adult_password", "adult_aux_intro_password", "adult_aux_new_password1", "adult_aux_new_password2"]:
            return value
        elif name.startswith('search_last_'): # ~ Para los settings de textos buscados no convertir si hay numéros (ej: 007)
            return str(value)
        elif name.endswith('_color'):
            return quitar_colores(value)
        else:
            try:
                value = int(value)
            except ValueError:
                pass
            return value


def set_setting(name, value, channel="", server=""):
    """
    Fija el valor de configuración del parametro indicado.

    Establece 'value' como el valor del parametro 'name' en la configuración global o en la propia del canal o servidor.
    Devuelve el valor cambiado o None si la asignación no se ha podido completar.

    Si se especifica el nombre de un canal o servidor se guarda en la configuración global con un prefijo channel_ o server_.
    Los parametros channel y server no deben usarse simultaneamente.
    """

    if channel:
        name = 'channel_' + channel + '_' + name
    elif server:
        name = 'server_' + server + '_' + name

    try:
        if isinstance(value, bool):
            if value:
                value = "true"
            else:
                value = "false"

        elif isinstance(value, (int, long)):
            value = str(value)

        __settings__.setSetting(name, value)

    except Exception as ex:
        from platformcode import logger
        logger.error("Error al convertir '%s' no se guarda el valor \n%s" % (name, ex))
        return None

    return value


# Obtener y guardar últimas búsquedas
def get_last_search(search_type):
    if get_setting('search_show_last', default=True):
        if search_type not in ['all', 'movie', 'tvshow', 'documentary', 'person', 'list', 'torrent', 'dorama', 'anime', 'video', 'youtube']: search_type = 'all'
        last_search = get_setting('search_last_' + search_type, default='')
    else:
        last_search = ''

    return last_search

def set_last_search(search_type, tecleado):
    if search_type not in ['all', 'movie', 'tvshow', 'documentary', 'person', 'list', 'torrent', 'dorama', 'anime', 'video', 'youtube']: search_type = 'all'

    set_setting('search_last_' + search_type, tecleado)


class WebErrorException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
