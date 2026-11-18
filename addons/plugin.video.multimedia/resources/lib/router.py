# -*- coding: utf-8 -*-
from urllib.parse import urlencode, parse_qsl

import xbmcgui
import xbmcplugin

from . import catalog, media, menu, player, utils

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


# ---------- menú principal y secciones ----------
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
    extras = [(sub["name"], url_for(action="submenu", file=sub["file"]), sub) for sub in sec.get("submenus", [])]
    idx = catalog.find_category(catalog.load_root(), sec["catalog"])
    if idx < 0:
        if not extras:
            utils.notify("Sección sin contenido todavía")
        for name, url, entry in extras:
            add_folder(name, url, entry)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    list_folder(str(idx), extras)


def list_folder(path_str, extras=()):
    for name, url, entry in extras:
        add_folder(name, url, entry)
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


# ---------- submenú TDT (definido en TDT.xml) ----------
def _tdt_entries(tdt):
    """Canales de la lista en línea; si falla, los canales escritos en TDT.xml."""
    entries = []
    for url in tdt.get("sources", []):
        try:
            entries = media.parse_m3u(catalog.fetch_text(url))
        except Exception as exc:
            utils.log("Lista '{}' no disponible: {}".format(url, exc))
            entries = []
        if entries:
            break
    if not entries:
        entries = list(tdt.get("channels", []))
    excluded = {media.norm(x) for x in tdt.get("exclude", [])}
    return [e for e in entries if media.norm(e.get("group") or "Otros") not in excluded]


def _parse_code_file(file):
    """Devuelve ('tdt', datos) o ('lista', grupos) según el tipo de archivo."""
    text = catalog.load_code_text(file)
    try:
        if menu.root_tag(text) == "tdt":
            return "tdt", menu.parse_tdt(text)
        return "lista", menu.parse_list(text)
    except Exception as exc:
        utils.log("'{}' inválido: {}".format(file, exc), error=True)
        return "lista", []


def open_submenu(file):
    kind, data = _parse_code_file(file)
    if kind == "tdt":
        list_tdt(file, data)
    else:
        list_lista(file, data)


def list_tdt(file, tdt):
    entries = _tdt_entries(tdt)
    if not entries:
        utils.notify("No se pudo cargar la lista de canales", error=True)
    counts = {}
    for entry in entries:
        group = entry.get("group") or "Otros"
        counts[group] = counts.get(group, 0) + 1
    for group in sorted(counts, key=media.group_sort_key):
        add_folder("{} ({})".format(group, counts[group]), url_for(action="tdtgroup", file=file, group=group))
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE)


def list_tdt_group(file, group):
    xbmcplugin.setContent(HANDLE, "videos")
    kind, tdt = _parse_code_file(file)
    for entry in (_tdt_entries(tdt) if kind == "tdt" else []):
        if (entry.get("group") or "Otros") == group:
            add_media(entry)
    xbmcplugin.endOfDirectory(HANDLE)


# ---------- submenús genéricos (<lista>, p. ej. Prueba.xml) ----------
def list_lista(file, groups):
    if len(groups) == 1:
        _add_items(groups[0]["items"])
        return
    for grp in groups:
        add_folder("{} ({})".format(grp["name"], len(grp["items"])), url_for(action="listgroup", file=file, group=grp["name"]))
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE)


def _add_items(items):
    for entry in items:
        add_media(entry)
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


def list_lista_group(file, group):
    kind, data = _parse_code_file(file)
    items = []
    if kind == "lista":
        items = next((g["items"] for g in data if g["name"] == group), [])
    _add_items(items)


def run(argv, menu_url=None):
    global HANDLE, BASE
    BASE, HANDLE = argv[0], int(argv[1])
    if menu_url:
        catalog.MENU_URL = menu_url
    params = dict(parse_qsl(argv[2][1:]))
    action = params.get("action")
    if action == "section":
        open_section(params.get("id", ""))
    elif action == "submenu":
        open_submenu(params.get("file", ""))
    elif action == "listgroup":
        list_lista_group(params.get("file", ""), params.get("group", ""))
    elif action == "tdtgroup":
        list_tdt_group(params.get("file", ""), params.get("group", ""))
    elif action == "folder":
        list_folder(params.get("path", ""))
    elif action == "play":
        player.resolve(HANDLE, params["url"], params.get("title", ""), params.get("kind", "video"))
    elif action == "open_link":
        player.open_link()
    else:
        list_root()
