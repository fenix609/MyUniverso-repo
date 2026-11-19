# -*- coding: utf-8 -*-
"""Lee menú.xml (menú principal) y TDT.xml (submenú TDT)."""
import re
import xml.etree.ElementTree as ET

# '&' sin escapar (p. ej. en enlaces pegados a mano) -> '&amp;'
_BARE_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)")

DEFAULT_SECTIONS = [
    {"id": "television", "name": "Televisión", "catalog": "Televisión", "private": False, "thumb": "", "fanart": "",
     "submenus": [{"id": "tdt", "name": "TDT", "file": "TDT.xml", "thumb": ""}]},
    {"id": "peliculas_series", "name": "Películas y Series", "catalog": "Películas y Series", "private": False, "thumb": "", "fanart": "",
     "submenus": [{"id": "prueba", "name": "Prueba", "file": "Prueba.xml", "thumb": ""},
                  {"id": "series", "name": "Series", "file": "Series.xml", "thumb": ""}]},
    {"id": "entretenimiento", "name": "Entretenimiento", "catalog": "Entretenimiento", "private": False, "thumb": "", "fanart": "", "submenus": []},
    {"id": "privado", "name": "Privado", "catalog": "Privado", "private": True, "thumb": "", "fanart": "", "submenus": []},
]


# --- reparación de atributos mal escritos (comillas dobles dentro de un texto, '<' suelto) ---
_TAG = re.compile(r"<([A-Za-z_][\w:.-]*)(\s.*?)?(/?)>(?=\s*(?:<|$))", re.DOTALL)  # una etiqueta acaba en ">" seguido de otra etiqueta
_ATTR = re.compile(r'\s*([\w:.-]+)\s*=\s*"(.*?)"(?=\s+[\w:.-]+\s*=\s*"|\s*$)', re.DOTALL)


def _fix_value(value):
    value = _BARE_AMP.sub("&amp;", value)
    return value.replace('"', "&quot;").replace("<", "&lt;")


def _fix_tag(match):
    name, attrs, slash = match.group(1), match.group(2) or "", match.group(3)
    pos, parts = 0, []
    for attr in _ATTR.finditer(attrs):
        if attrs[pos:attr.start()].strip():
            return match.group(0)  # algo raro entre atributos: no se toca
        parts.append(' {}="{}"'.format(attr.group(1), _fix_value(attr.group(2))))
        pos = attr.end()
    if attrs[pos:].strip():
        return match.group(0)
    return "<{}{}{}>".format(name, "".join(parts), slash)


def repair_xml(text):
    """Escapa comillas dobles y '<' que alguien escribió dentro de un valor (plot="Dice "hola" ..."). """
    pieces = re.split(r"(<!--.*?-->|<\?.*?\?>)", text, flags=re.DOTALL)
    for i in range(0, len(pieces), 2):  # los comentarios y la cabecera XML no se tocan
        pieces[i] = _TAG.sub(_fix_tag, pieces[i])
    return "".join(pieces)


def _root(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    text = _BARE_AMP.sub("&amp;", text.lstrip("\ufeff"))
    try:
        return ET.fromstring(text.encode("utf-8"))
    except ET.ParseError as first:
        try:
            return ET.fromstring(repair_xml(text).encode("utf-8"))
        except ET.ParseError:
            raise first  # se muestra el error original (línea y columna reales)


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
    return _root(text).tag.lower()


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


_FOLDER_TAGS = {"folder", "carpeta", "serie", "series", "temporada", "season", "grupo", "group", "categoria", "categoría", "submenu"}
_ITEM_TAGS = {"item", "episodio", "episode", "capitulo", "capítulo", "video", "vídeo", "pelicula", "película"}


def parse_tree(text):
    """<tree name=".."><folder name=".." icon fanart plot ...><item title drive=".." .../></folder></tree>
    Cada nodo conserva todos sus atributos (icon, thumb, fanart, plot, year, genre...).
    Acepta las etiquetas en mayúsculas o en español (carpeta, temporada, episodio...) y name/nombre, title/titulo."""
    def item(el):
        d = dict(el.attrib)
        d["title"] = d.get("title") or d.get("titulo") or d.get("name") or d.get("nombre") or "Sin título"
        if not (d.get("url") or d.get("drive")):
            for key in ("enlace", "link", "ruta"):
                if d.get(key):
                    d["url"] = d[key]
                    break
        d["alts"] = [a.get("url") for a in el.findall("alt") if a.get("url")]
        d["sources"] = [{"name": (c.get("name") or "").strip(), "url": c.get("url").strip()}
                        for c in el.findall("source") if (c.get("url") or "").strip()]  # otros servidores
        return d

    def node(el):
        d = dict(el.attrib)
        d["name"] = (d.get("name") or d.get("nombre") or d.get("title") or d.get("titulo") or "").strip()
        d["file"] = (d.get("file") or d.get("archivo") or d.get("xml") or "").strip()  # el contenido está en otro archivo
        d["folders"], d["items"], d["unknown"] = [], [], []
        for child in el:
            tag = child.tag.lower()
            if tag in _FOLDER_TAGS:
                d["folders"].append(node(child))
            elif tag in _ITEM_TAGS:
                d["items"].append(item(child))
            else:
                d["unknown"].append(child.tag)
        return d
    return node(_root(text))
