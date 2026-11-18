# -*- coding: utf-8 -*-
import os
from urllib.parse import urlencode, urlparse, parse_qsl

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
    for sec in catalog.load_menu():
        add_folder(sec["name"], url_for(action="section", id=sec["id"]), sec)
    if utils.get_bool("show_open_link"):
        item = xbmcgui.ListItem(label="Enlace")
        xbmcplugin.addDirectoryItem(HANDLE, url_for(action="open_link"), item, False)
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE)


def open_section(section_id):
    sec = next((x for x in catalog.load_menu() if x["id"] == section_id), None)
    if sec is None:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    pin = utils.get_setting("pin_privado")
    if sec["private"] and pin:
        typed = xbmcgui.Dialog().input("PIN", type=xbmcgui.INPUT_NUMERIC,
                                       option=xbmcgui.ALPHANUM_HIDE_INPUT)
        if typed != pin:
            if typed:
                utils.notify("PIN incorrecto", error=True)
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
            return
    idx = catalog.find_category(catalog.load_root(), sec["catalog"])
    if idx < 0:
        utils.notify("Sección sin contenido todavía")
        xbmcplugin.endOfDirectory(HANDLE)
        return
    list_folder(str(idx))


def _group_entries(node):
    """Canales de la lista en línea; si falla, de la copia de respaldo."""
    for url in (node.get("m3u_groups"), node.get("m3u_fallback")):
        if not url:
            continue
        try:
            entries = media.parse_m3u(catalog.fetch_text(url))
            if entries:
                return entries
        except Exception as exc:
            utils.log("Lista '{}' no disponible: {}".format(url, exc), error=True)
    if node.get("m3u_fallback"):
        try:
            name = os.path.basename(urlparse(node["m3u_fallback"]).path)
            entries = media.parse_m3u(catalog.read_local(name))
            if entries:
                utils.log("Usando la lista de canales incluida en el addon")
                return entries
        except Exception as exc:
            utils.log("Lista local no disponible: {}".format(exc), error=True)
    utils.notify("No se pudo cargar la lista de canales", error=True)
    return []


def _visible(entries, node):
    excluded = {media.norm(x) for x in node.get("exclude_groups", [])}
    return [e for e in entries if media.norm(e.get("group") or "Otros") not in excluded]


def list_groups(path_str, node):
    counts = {}
    for entry in _visible(_group_entries(node), node):
        group = entry.get("group") or "Otros"
        counts[group] = counts.get(group, 0) + 1
    for group in sorted(counts, key=media.group_sort_key):
        add_folder("{} ({})".format(group, counts[group]), url_for(action="group", path=path_str, group=group))
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE)


def list_group(path_str, group):
    path = [int(p) for p in path_str.split(".") if p != ""]
    node = catalog.get_node(catalog.load_root(), path)
    xbmcplugin.setContent(HANDLE, "videos")
    for entry in _visible(_group_entries(node), node):
        if (entry.get("group") or "Otros") == group:
            add_media(entry)
    xbmcplugin.endOfDirectory(HANDLE)


def list_folder(path_str):
    path = [int(p) for p in path_str.split(".") if p != ""]
    node = catalog.get_node(catalog.load_root(), path)
    if node.get("m3u_groups"):
        list_groups(path_str, node)
        return
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


def run(argv, menu_url=None):
    global HANDLE, BASE
    BASE, HANDLE = argv[0], int(argv[1])
    if menu_url:
        catalog.MENU_URL = menu_url
    params = dict(parse_qsl(argv[2][1:]))
    action = params.get("action")
    if action == "section":
        open_section(params.get("id", ""))
    elif action == "folder":
        list_folder(params.get("path", ""))
    elif action == "group":
        list_group(params.get("path", ""), params.get("group", ""))
    elif action == "play":
        player.resolve(HANDLE, params["url"], params.get("title", ""), params.get("kind", "video"))
    elif action == "open_link":
        player.open_link()
    else:
        list_root()
