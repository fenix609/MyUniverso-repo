# -*- coding: utf-8 -*-
from urllib.parse import urlencode, parse_qsl

import xbmcgui
import xbmcplugin

from . import catalog, media, player, utils

HANDLE = -1
BASE = ""


def url_for(**kwargs):
    return "{}?{}".format(BASE, urlencode(kwargs))


def _art(item, entry):
    art = {}
    if entry.get("thumb"):
        art["thumb"] = art["icon"] = entry["thumb"]
    if entry.get("fanart"):
        art["fanart"] = entry["fanart"]
    if art:
        item.setArt(art)


def add_folder(label, url, entry=None):
    item = xbmcgui.ListItem(label=label)
    _art(item, entry or {})
    xbmcplugin.addDirectoryItem(HANDLE, url, item, True)


def add_media(entry):
    title = entry.get("title") or entry.get("name") or "Sin título"
    plot = entry.get("plot", "")
    kind, sub, yt_id = media.item_kind(entry)

    if kind == "youtube":
        if sub != "video":
            add_folder(title, media.youtube_url(sub, yt_id), entry)
            return
        item = xbmcgui.ListItem(label=title)
        item.setInfo("video", {"title": title, "plot": plot})
        _art(item, entry)
        item.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(HANDLE, media.youtube_url("video", yt_id), item, False)
        return

    url = entry.get("url", "")
    if entry.get("headers"):
        url = "{}|{}".format(url, entry["headers"])

    item = xbmcgui.ListItem(label=title)
    _art(item, entry)
    if kind == "image":
        item.setInfo("pictures", {"title": title})
        if not entry.get("thumb"):
            item.setArt({"thumb": url, "icon": url})
        xbmcplugin.addDirectoryItem(HANDLE, url, item, False)
        return
    if kind == "audio":
        item.setInfo("music", {"title": title, "artist": entry.get("artist", ""),
                               "album": entry.get("album", "")})
    else:
        item.setInfo("video", {"title": title, "plot": plot})
    item.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, url_for(action="play", url=url, title=title, kind=kind), item, False)


def list_root():
    root = catalog.load_root()
    for idx, cat in enumerate(root.get("categories", [])):
        add_folder(cat.get("name", "Sin nombre"), url_for(action="folder", path=str(idx)), cat)
    if utils.get_bool("show_youtube") and utils.has_youtube():
        add_folder("YouTube", media.YT_PLUGIN)
    if utils.get_bool("show_open_link"):
        item = xbmcgui.ListItem(label="Reproducir enlace...")
        xbmcplugin.addDirectoryItem(HANDLE, url_for(action="open_link"), item, False)
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE)


def list_folder(path_str):
    path = [int(p) for p in path_str.split(".") if p != ""]
    node = catalog.get_node(catalog.load_root(), path)
    for idx, cat in enumerate(node.get("categories", [])):
        add_folder(cat.get("name", "Sin nombre"), url_for(action="folder", path=".".join(map(str, path + [idx]))), cat)
    entries = []
    if node.get("m3u"):
        try:
            entries += media.parse_m3u(catalog.fetch_text(node["m3u"]))
        except Exception as exc:
            utils.log("Error cargando M3U: {}".format(exc), error=True)
            utils.notify("No se pudo cargar la lista M3U", error=True)
    entries += node.get("items", [])
    kinds = set()
    for entry in entries:
        kinds.add(media.item_kind(entry)[0])
        add_media(entry)
    content = {"video": "videos", "audio": "songs", "image": "images"}.get(next(iter(kinds)) if len(kinds) == 1 else "", "files")
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.endOfDirectory(HANDLE)


def run(argv):
    global HANDLE, BASE
    BASE, HANDLE = argv[0], int(argv[1])
    params = dict(parse_qsl(argv[2][1:]))
    action = params.get("action")
    if action == "folder":
        list_folder(params.get("path", ""))
    elif action == "play":
        player.resolve(HANDLE, params["url"], params.get("title", ""), params.get("kind", "video"))
    elif action == "open_link":
        player.open_link()
    else:
        list_root()
