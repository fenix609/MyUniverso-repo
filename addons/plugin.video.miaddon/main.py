# -*- coding: utf-8 -*-
"""plugin.video.miaddon - MyUniverso"""
import sys
import re
import json
import urllib.parse
import urllib.request

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.m4v', '.ts', '.mpg',
             '.mpeg', '.wmv', '.flv', '.webm', '.m2ts', '.iso')


def tr(string_id):
    return ADDON.getLocalizedString(string_id)


def build_url(**query):
    return BASE_URL + '?' + urllib.parse.urlencode(query)


def notify(msg):
    xbmcgui.Dialog().notification('MiAddon', msg, xbmcgui.NOTIFICATION_INFO, 4000)


def add_folder(label, **query):
    li = xbmcgui.ListItem(label=label)
    li.setArt({'icon': ADDON.getAddonInfo('icon'),
               'fanart': ADDON.getAddonInfo('fanart')})
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**query), li, True)


def add_video(label, link, thumb='', plot=''):
    li = xbmcgui.ListItem(label=label)
    li.setArt({'thumb': thumb, 'icon': thumb})
    li.setInfo('video', {'title': label, 'plot': plot})
    li.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(HANDLE, build_url(action='play', link=link), li, False)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Kodi-MyUniverso'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', 'replace')


# ------------------------------------------------------------------ menús
def main_menu():
    add_folder(tr(30200), action='catalogo', tipo='peliculas')
    add_folder(tr(30201), action='catalogo', tipo='series')
    add_folder(tr(30202), action='tv')
    add_folder(tr(30203), action='youtube')
    add_folder(tr(30204), action='archivos', path='')
    xbmcplugin.endOfDirectory(HANDLE)


# --------------------------------------------------- películas y series
def load_catalog():
    url = ADDON.getSetting('catalogo_url').strip()
    if not url:
        notify(tr(30300))
        return {}
    try:
        return json.loads(fetch(url))
    except Exception as exc:
        xbmc.log('[MiAddon] catálogo: %s' % exc, xbmc.LOGERROR)
        notify(tr(30301))
        return {}


def show_catalog(tipo):
    items = load_catalog().get(tipo, [])
    for idx, it in enumerate(items):
        title = it.get('title', '?')
        if it.get('episodes'):
            add_folder(title, action='episodios', tipo=tipo, idx=idx)
        elif it.get('url'):
            add_video(title, it['url'], it.get('thumb', ''), it.get('plot', ''))
    xbmcplugin.setContent(HANDLE, 'movies' if tipo == 'peliculas' else 'tvshows')
    xbmcplugin.endOfDirectory(HANDLE)


def show_episodes(tipo, idx):
    items = load_catalog().get(tipo, [])
    if 0 <= idx < len(items):
        serie = items[idx]
        for ep in serie.get('episodes', []):
            add_video(ep.get('title', '?'), ep.get('url', ''),
                      ep.get('thumb', serie.get('thumb', '')), ep.get('plot', ''))
    xbmcplugin.setContent(HANDLE, 'episodes')
    xbmcplugin.endOfDirectory(HANDLE)


# ----------------------------------------------------------------- TV M3U
def parse_m3u(text):
    items, name, logo, group = [], None, '', ''
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#EXTINF'):
            name = line.split(',', 1)[-1].strip()
            m = re.search(r'tvg-logo="([^"]*)"', line)
            logo = m.group(1) if m else ''
            m = re.search(r'group-title="([^"]*)"', line)
            group = m.group(1) if m else ''
        elif line and not line.startswith('#'):
            items.append((name or line, line, logo, group))
            name, logo, group = None, '', ''
    return items


def show_tv(group=None):
    url = ADDON.getSetting('m3u_url').strip()
    if not url:
        notify(tr(30302))
        xbmcplugin.endOfDirectory(HANDLE)
        return
    try:
        channels = parse_m3u(fetch(url))
    except Exception as exc:
        xbmc.log('[MiAddon] m3u: %s' % exc, xbmc.LOGERROR)
        notify(tr(30303))
        xbmcplugin.endOfDirectory(HANDLE)
        return

    groups = sorted({c[3] for c in channels if c[3]})
    if group is None and groups:
        for g in groups:
            add_folder(g, action='tv', group=g)
        for c in channels:
            if not c[3]:
                add_video(c[0], c[1], c[2])
    else:
        for name, link, logo, g in channels:
            if group is None or g == group:
                add_video(name, link, logo)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------- YouTube
def open_youtube():
    if xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)'):
        xbmc.executebuiltin('ActivateWindow(Videos,plugin://plugin.video.youtube/,return)')
    else:
        xbmc.executebuiltin('InstallAddon(plugin.video.youtube)')
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


# --------------------------------------------------------------- archivos
def browse_files(path):
    root = path or ADDON.getSetting('carpeta_media').strip()
    if not root:
        notify(tr(30304))
        xbmcplugin.endOfDirectory(HANDLE)
        return
    dirs, files = xbmcvfs.listdir(root)
    sep = '' if root.endswith(('/', '\\')) else '/'
    for d in sorted(dirs):
        add_folder(d, action='archivos', path=root + sep + d + '/')
    for f in sorted(files):
        if f.lower().endswith(VIDEO_EXT):
            add_video(f, root + sep + f)
    xbmcplugin.setContent(HANDLE, 'files')
    xbmcplugin.endOfDirectory(HANDLE)


# ------------------------------------------------------------- reproducir
def play(link):
    xbmcplugin.setResolvedUrl(HANDLE, True, xbmcgui.ListItem(path=link))


# ---------------------------------------------------------------- router
def router(paramstring):
    p = {k: v[0] for k, v in urllib.parse.parse_qs(paramstring).items()}
    action = p.get('action')
    if action is None:
        main_menu()
    elif action == 'catalogo':
        show_catalog(p.get('tipo', 'peliculas'))
    elif action == 'episodios':
        show_episodes(p.get('tipo', 'series'), int(p.get('idx', 0)))
    elif action == 'tv':
        show_tv(p.get('group'))
    elif action == 'youtube':
        open_youtube()
    elif action == 'archivos':
        browse_files(p.get('path', ''))
    elif action == 'play':
        play(p.get('link', ''))


if __name__ == '__main__':
    router(sys.argv[2][1:])
