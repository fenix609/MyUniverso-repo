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


ALT_CATALOG = ("https://raw.githubusercontent.com/fenix609/Addon-multimedia/"
               "refs/heads/main/C%C3%B3digo/catalog.json")


def read_local(name):
    """Archivo incluido dentro del addon (resources/data)."""
    path = os.path.join(ADDON_DIR, "resources", "data", name)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _as_root(data):
    return {"categories": data} if isinstance(data, list) else data


def load_root():
    """Catálogo desde GitHub; si no está disponible, la copia incluida en el addon."""
    url = utils.get_setting("catalog_url") or DEFAULT_CATALOG
    for candidate in dict.fromkeys([url, ALT_CATALOG]):
        try:
            return _as_root(json.loads(fetch_text(candidate)))
        except Exception as exc:
            utils.log("Catálogo '{}' no disponible: {}".format(candidate, exc))
    try:
        data = _as_root(json.loads(read_local("catalog.json")))
        utils.log("Usando el catálogo incluido en el addon")
        utils.notify("Catálogo en línea no disponible: usando copia local")
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
            text = fetch_text(url)
        except Exception as exc:
            utils.log("Menú remoto '{}' no disponible: {}".format(url, exc))
            continue
        try:
            return menu.parse_menu(text)
        except Exception as exc:
            utils.log("menú.xml con error: {}".format(exc), error=True)
            utils.notify("menú.xml tiene un error: {}".format(exc), error=True)
    try:
        return menu.parse_menu(read_local("menu.xml"))
    except Exception as exc:
        utils.log("Menú local no disponible: {}".format(exc))
    return list(menu.DEFAULT_SECTIONS)


def find_category(root, name):
    wanted = (name or "").strip().lower()
    for idx, cat in enumerate(root.get("categories", [])):
        if cat.get("name", "").strip().lower() == wanted:
            return idx
    return -1


def code_base():
    """Carpeta 'Código' de GitHub (la misma de menú.xml)."""
    return MENU_URL.rsplit("/", 1)[0] + "/" if MENU_URL else ""


SOURCES = {}  # nombre de archivo -> "GitHub, N bytes" / "copia local"


def load_code_text(name):
    """Texto de un archivo de la carpeta Código desde GitHub; si falla, copia local del addon."""
    base = code_base()
    if base:
        try:
            text = fetch_text(base + quote(name))
            utils.log("{} leído de GitHub ({} bytes)".format(name, len(text.encode("utf-8"))))
            SOURCES[name] = "GitHub, {} bytes".format(len(text.encode("utf-8")))
            return text
        except Exception as exc:
            utils.log("'{}' no disponible en GitHub: {}".format(name, exc))
    try:
        text = read_local(name)
        utils.log("{} leído de la copia incluida en el addon (no se pudo leer de GitHub)".format(name))
        SOURCES[name] = "copia incluida en el addon, NO de GitHub"
        return text
    except Exception as exc:
        utils.log("'{}' local no disponible: {}".format(name, exc), error=True)
        SOURCES[name] = "NO se pudo leer: ni de GitHub ni de la copia del addon (¿el archivo existe en la carpeta Código?)"
        return ""
