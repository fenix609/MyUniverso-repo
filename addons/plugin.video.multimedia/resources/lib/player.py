# -*- coding: utf-8 -*-
from urllib.parse import quote

import xbmc
import xbmcgui
import xbmcplugin

from . import media, utils


def build_listitem(url, title="", kind="video"):
    item = xbmcgui.ListItem(label=title, path=url)
    clean = url.split("|")[0].lower()
    if ".m3u8" in clean:
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "hls")
    elif ".mpd" in clean:
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "mpd")
    if kind == "audio":
        item.setInfo("music", {"title": title})
    elif kind == "video":
        item.setInfo("video", {"title": title})
    return item


# (id del addon, plantilla para magnet, plantilla para archivo .torrent)
TORRENT_ADDONS = (
    ("plugin.video.elementum", "plugin://plugin.video.elementum/play?uri={}", "plugin://plugin.video.elementum/play?uri={}"),
    ("plugin.video.torrest", "plugin://plugin.video.torrest/play_magnet?magnet={}", "plugin://plugin.video.torrest/play_url?url={}"),
    ("plugin.video.quasar", "plugin://plugin.video.quasar/playuri?uri={}", "plugin://plugin.video.quasar/playuri?uri={}"),
)


def torrent_url(uri):
    """Dirección para reproducir un magnet/.torrent con el addon de torrents instalado (o None)."""
    is_magnet = uri.lower().startswith("magnet:")
    for addon_id, magnet_tpl, file_tpl in TORRENT_ADDONS:
        if xbmc.getCondVisibility("System.HasAddon({})".format(addon_id)):
            return (magnet_tpl if is_magnet else file_tpl).format(quote(uri, safe=""))
    return None


def resolve(handle, url, title="", kind="video"):
    if kind == "torrent":
        target = torrent_url(url)
        if not target:
            utils.notify("Instala Elementum o Torrest para reproducir torrents", error=True)
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
        url = target
    xbmcplugin.setResolvedUrl(handle, True, build_listitem(url, title, kind))
