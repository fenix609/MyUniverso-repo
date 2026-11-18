# -*- coding: utf-8 -*-
"""Lee menú.xml (menú principal) y TDT.xml (submenú TDT)."""
import xml.etree.ElementTree as ET

DEFAULT_SECTIONS = [
    {"id": "television", "name": "Televisión", "catalog": "Televisión", "private": False, "thumb": "", "fanart": "",
     "submenus": [{"id": "tdt", "name": "TDT", "file": "TDT.xml", "thumb": ""}]},
    {"id": "peliculas_series", "name": "Películas y Series", "catalog": "Películas y Series", "private": False, "thumb": "", "fanart": "",
     "submenus": [{"id": "prueba", "name": "Prueba", "file": "Prueba.xml", "thumb": ""},
                  {"id": "series", "name": "Series", "file": "Series.xml", "thumb": ""}]},
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
                entry = dict(sub.attrib)
                entry["id"] = sub.get("id") or sub.get("name").lower()
                submenus.append(entry)
        entry = dict(node.attrib)
        entry.update({
            "id": node.get("id") or name.lower().replace(" ", "_"),
            "name": name,
            "catalog": node.get("catalog") or name,
            "private": (node.get("private", "false").lower() == "true"),
            "submenus": submenus,
        })
        sections.append(entry)
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
                entry = dict(it.attrib)
                entry["title"] = it.get("title") or it.get("name") or it.get("url")
                entry["alts"] = [a.get("url") for a in it.findall("alt") if a.get("url")]
                items.append(entry)
        groups.append({"name": grp.get("name", "").strip() or "Sin nombre", "items": items})
    return {"groups": groups, "autotest": root.get("autotest", "false").lower() == "true"}


def parse_tree(text):
    """<tree name=".."><folder name=".." icon fanart plot ...><item title drive=".." .../></folder></tree>
    Cada nodo conserva todos sus atributos (icon, thumb, fanart, plot, year, genre...)."""
    def node(el):
        d = dict(el.attrib)
        d["name"] = d.get("name", "").strip()
        d["folders"] = [node(c) for c in el.findall("folder")]
        items = []
        for it in el.findall("item"):
            entry = dict(it.attrib)
            entry["title"] = it.get("title") or it.get("name") or "Sin título"
            entry["alts"] = [a.get("url") for a in it.findall("alt") if a.get("url")]
            items.append(entry)
        d["items"] = items
        return d
    return node(_root(text))
