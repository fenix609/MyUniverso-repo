# -*- coding: utf-8 -*-
from urllib.parse import urlencode, parse_qsl

import xbmc
import xbmcgui
import xbmcplugin

from . import catalog, media, menu, player, probe, utils

HANDLE = -1
BASE = ""


def url_for(**kwargs):
    return "{}?{}".format(BASE, urlencode(kwargs))


def _art(item, entry):
    art = media.art_of(entry)
    if art:
        item.setArt(art)


def add_folder(label, url, entry=None):
    entry = entry or {}
    item = xbmcgui.ListItem(label=label)
    _art(item, entry)
    info = media.video_info(entry, label)
    if len(info) > 1:  # solo si el nodo trae información (plot, year, genre...)
        item.setInfo("video", info)
    xbmcplugin.addDirectoryItem(HANDLE, url, item, True)


def add_media(entry):
    title = entry.get("title") or entry.get("name") or "Sin título"
    plot = entry.get("plot", "")
    kind, sub, yt_id = media.item_kind(entry)

    if kind == "nolink":
        item = xbmcgui.ListItem(label=title)
        _art(item, entry)
        item.setInfo("video", media.video_info(entry, title))
        item.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(HANDLE, url_for(action="nolink"), item, False)
        return
    if kind == "drive":
        proxy = utils.drive_proxy_base()  # con proxy local Kodi no se queda esperando a Drive al parar
        direct = media.drive_url(yt_id, utils.get_setting("drive_api_key"))
        entry = dict(entry, url="{}/drive/{}".format(proxy, yt_id) if proxy else direct)
        kind = "video"

    if kind == "youtube":
        if sub != "video":
            add_folder(title, media.youtube_url(sub, yt_id), entry)
            return
        item = xbmcgui.ListItem(label=title)
        item.setInfo("video", media.video_info(entry, title))
        _art(item, entry)
        item.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(HANDLE, media.youtube_url("video", yt_id), item, False)
        return

    if kind == "torrent":
        item = xbmcgui.ListItem(label=title)
        item.setInfo("video", media.video_info(entry, title))
        _art(item, entry)
        item.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(HANDLE, url_for(action="play", url=entry.get("url", ""), title=title, kind="torrent"), item, False)
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
        item.setInfo("video", media.video_info(entry, title))
    item.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(HANDLE, url_for(action="play", url=url, title=title, kind=kind), item, False)


# ---------- menú principal y secciones ----------
def list_root():
    for sec in catalog.load_menu():
        add_folder(sec["name"], url_for(action="section", id=sec["id"]), sec)
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


def _parse_code_file(file, use_cache=True):
    """Devuelve ('tdt', datos) o ('lista', datos) según el tipo de archivo."""
    text = catalog.load_code_text(file)
    try:
        tag = menu.root_tag(text)
        if tag == "tdt":
            return "tdt", menu.parse_tdt(text)
        if tag == "tree":
            return "tree", menu.parse_tree(text)
        data = menu.parse_list(text)
        if use_cache:
            try:
                data = probe.apply_cache(data, probe.load_cache(utils.profile_dir()))
            except Exception as exc:
                utils.log("Caché de pruebas no disponible: {}".format(exc))
        return "lista", data
    except Exception as exc:
        utils.log("'{}' inválido: {}".format(file, exc), error=True)
        utils.notify("Error en {}: {}".format(file, exc), error=True)
        return "lista", {"groups": [], "autotest": False}


def open_submenu(file):
    kind, data = _parse_code_file(file)
    if kind == "tdt":
        list_tdt(file, data)
    elif kind == "tree":
        list_tree(file, "", data)
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
def _add_auto_option(file, data):
    if data.get("autotest"):
        add_folder("[ Probar todos automáticamente ]", url_for(action="auto_test", file=file))


def list_lista(file, data):
    groups = data["groups"]
    _add_auto_option(file, data)
    if len(groups) == 1:
        for entry in groups[0]["items"]:
            add_media(entry)
        xbmcplugin.setContent(HANDLE, "videos")
    else:
        for grp in groups:
            add_folder("{} ({})".format(grp["name"], len(grp["items"])),
                       url_for(action="listgroup", file=file, group=grp["name"]))
        xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE)


def list_lista_group(file, group):
    kind, data = _parse_code_file(file)
    items = []
    if kind == "lista":
        items = next((g["items"] for g in data["groups"] if g["name"] == group), [])
    for entry in items:
        add_media(entry)
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


# ---------- árboles (<tree>, p. ej. Series.xml): series > temporadas > episodios ----------
_CONTENT = {"tvshow": "tvshows", "season": "seasons", "episode": "episodes"}


def list_tree(file, path_str, root=None):
    if root is None:
        kind, root = _parse_code_file(file)
        if kind != "tree":
            root = {"folders": [], "items": []}
    path = [int(p) for p in path_str.split(".") if p != ""]
    node = root
    inherit = {"fanart": root.get("fanart", "")}
    for idx in path:
        folders = node.get("folders", [])
        if idx < 0 or idx >= len(folders):
            node = {"folders": [], "items": []}
            break
        node = folders[idx]
        if node.get("fanart"):
            inherit["fanart"] = node["fanart"]
        if node.get("mediatype") == "tvshow":
            inherit["tvshowtitle"] = node.get("name", "")
        if node.get("season"):
            inherit["season"] = node["season"]

    def with_inherited(entry):
        entry = dict(entry)
        for key, value in inherit.items():
            if value and not entry.get(key):
                entry[key] = value
        return entry

    for idx, folder in enumerate(node.get("folders", [])):
        add_folder(folder.get("name", "Sin nombre"),
                   url_for(action="tree", file=file, path=".".join(map(str, path + [idx]))),
                   with_inherited(folder))
    for entry in node.get("items", []):
        add_media(with_inherited(entry))
    if node.get("items"):
        content = "episodes"
    elif node.get("folders"):
        content = _CONTENT.get(node["folders"][0].get("mediatype", ""), "files")
    else:
        content = "files"
    xbmcplugin.setContent(HANDLE, content)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.endOfDirectory(HANDLE)


def no_link():
    utils.notify("Este episodio todavía no tiene enlace de Drive")
    xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


def start_auto_test(file):
    """Lanza la prueba en segundo plano (puede durar minutos) y deja la lista como estaba."""
    xbmc.executebuiltin("RunPlugin({})".format(url_for(action="auto_run", file=file)))
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)


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
    elif action == "auto_test":
        start_auto_test(params.get("file", ""))
    elif action == "auto_run":
        from . import autotest
        autotest.run(params.get("file", ""))
    elif action == "tree":
        list_tree(params.get("file", ""), params.get("path", ""))
    elif action == "nolink":
        no_link()
    elif action == "listgroup":
        list_lista_group(params.get("file", ""), params.get("group", ""))
    elif action == "tdtgroup":
        list_tdt_group(params.get("file", ""), params.get("group", ""))
    elif action == "folder":
        list_folder(params.get("path", ""))
    elif action == "play":
        player.resolve(HANDLE, params["url"], params.get("title", ""), params.get("kind", "video"))
    else:
        list_root()
