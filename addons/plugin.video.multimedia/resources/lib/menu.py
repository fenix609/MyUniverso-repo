# -*- coding: utf-8 -*-
"""Lee el menú principal desde menú.xml."""
import xml.etree.ElementTree as ET

DEFAULT_SECTIONS = [
    {"id": "television", "name": "Televisión", "catalog": "Televisión", "private": False, "thumb": "", "fanart": ""},
    {"id": "peliculas_series", "name": "Películas y Series", "catalog": "Películas y Series", "private": False, "thumb": "", "fanart": ""},
    {"id": "entretenimiento", "name": "Entretenimiento", "catalog": "Entretenimiento", "private": False, "thumb": "", "fanart": ""},
    {"id": "privado", "name": "Privado", "catalog": "Privado", "private": True, "thumb": "", "fanart": ""},
]


def parse_menu(text):
    root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    sections = []
    for node in root.findall("section"):
        name = node.get("name", "").strip()
        if not name:
            continue
        sections.append({
            "id": node.get("id") or name.lower().replace(" ", "_"),
            "name": name,
            "catalog": node.get("catalog") or name,
            "private": (node.get("private", "false").lower() == "true"),
            "thumb": node.get("thumb", ""),
            "fanart": node.get("fanart", ""),
        })
    return sections
