# -*- coding: utf-8 -*-
import json
import os
import urllib.request
from urllib.parse import quote

from . import menu, utils

DEFAULT_CATALOG = ("https://raw.githubusercontent.com/fenix609/"
                   "MyUniverso-repo/main/content/catalog.json")


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Kodi-multimedia"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_root():
    url = utils.get_setting("catalog_url") or DEFAULT_CATALOG
    try:
        data = json.loads(fetch_text(url))
        if isinstance(data, list):
            data = {"categories": data}
        return data
    except Exception as exc:
        utils.log("Error cargando catálogo: {}".format(exc), error=True)
        utils.notify("No se pudo cargar el catálogo", error=True)
        return {"categories": []}


def get_node(root, path):
    node = root
    for idx in path:
        cats = node.get("categories", [])
        if idx < 0 or idx >= len(cats):
            return {}
        node = cats[idx]
    return node


MENU_URL = ""  # la fija main.py
MENU_BASE = ("https://raw.githubusercontent.com/fenix609/MyUniverso-repo/main/"
             "plugin.video.multimedia/")
MENU_FILES = ("menú.xml", "menu.xml")
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_menu():
    """Menú desde GitHub; si falla, copia incluida en el addon; si no, valores por defecto."""
    candidates = [MENU_URL] if MENU_URL else []
    candidates += [MENU_BASE + quote(name) for name in MENU_FILES]
    for url in candidates:
        try:
            return menu.parse_menu(fetch_text(url))
        except Exception as exc:
            utils.log("Menú remoto '{}' no disponible: {}".format(url, exc))
    for name in MENU_FILES:
        path = os.path.join(ADDON_DIR, name)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    return menu.parse_menu(fh.read())
            except Exception as exc:
                utils.log("Menú local '{}' inválido: {}".format(name, exc), error=True)
    return list(menu.DEFAULT_SECTIONS)


def find_category(root, name):
    wanted = (name or "").strip().lower()
    for idx, cat in enumerate(root.get("categories", [])):
        if cat.get("name", "").strip().lower() == wanted:
            return idx
    return -1
