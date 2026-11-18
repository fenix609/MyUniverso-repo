# -*- coding: utf-8 -*-
"""Lee menú.xml (menú principal) y TDT.xml (submenú TDT)."""
import xml.etree.ElementTree as ET

DEFAULT_SECTIONS = [
    {"id": "television", "name": "Televisión", "catalog": "Televisión", "private": False, "thumb": "", "fanart": "",
     "submenus": [{"id": "tdt", "name": "TDT", "file": "TDT.xml", "thumb": ""}]},
    {"id": "peliculas_series", "name": "Películas y Series", "catalog": "Películas y Series", "private": False, "thumb": "", "fanart": "",
     "submenus": [{"id": "prueba", "name": "Prueba", "file": "Prueba.xml", "thumb": ""}]},
    {"id": "entretenimiento", "name": "Entretenimiento", "catalog": "Entretenimiento", "private": False, "thumb": "", "fanart": "", "submenus": []},
    {"id": "privado", "name": "Privado", "catalog": "Privado", "private": True, "thumb": "", "fanart": "", "submenus": []},
]


def _root(text):
    return ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)


def parse_menu(text):
    sections = []
    for node in _root(text).findall("section"):
        name = node.get("name", "").strip()
        if not name:
            continue
        submenus = []
        for sub in node.findall("submenu"):
            if sub.get("name") and sub.get("file"):
                submenus.append({"id": sub.get("id") or sub.get("name").lower(), "name": sub.get("name"),
                                 "file": sub.get("file"), "thumb": sub.get("thumb", "")})
        sections.append({
            "id": node.get("id") or name.lower().replace(" ", "_"),
            "name": name,
            "catalog": node.get("catalog") or name,
            "private": (node.get("private", "false").lower() == "true"),
            "thumb": node.get("thumb", ""),
            "fanart": node.get("fanart", ""),
            "submenus": submenus,
        })
    return sections


def parse_tdt(text):
    root = _root(text)
    channels = []
    for grp in root.findall("group"):
        gname = grp.get("name", "").strip()
        for ch in grp.findall("channel"):
            if ch.get("name") and ch.get("url"):
                channels.append({"title": ch.get("name"), "url": ch.get("url"),
                                 "thumb": ch.get("thumb", ""), "group": gname})
    return {
        "sources": [n.get("url") for n in root.findall("source") if n.get("url")],
        "exclude": [n.get("group") for n in root.findall("exclude") if n.get("group")],
        "channels": channels,
    }


def root_tag(text):
    return _root(text).tag


def parse_list(text):
    """<lista autotest="true"><group name=".."><item title url type plot thumb><alt url/></item></group></lista>
    Devuelve {"groups": [...], "autotest": bool}."""
    root = _root(text)
    groups = []
    for grp in root.findall("group"):
        items = []
        for it in grp.findall("item"):
            if it.get("url"):
                items.append({"title": it.get("title") or it.get("name") or it.get("url"), "url": it.get("url"),
                              "type": it.get("type", ""), "plot": it.get("plot", ""), "thumb": it.get("thumb", ""),
                              "headers": it.get("headers", ""),
                              "alts": [a.get("url") for a in it.findall("alt") if a.get("url")]})
        groups.append({"name": grp.get("name", "").strip() or "Sin nombre", "items": items})
    return {"groups": groups, "autotest": root.get("autotest", "false").lower() == "true"}
