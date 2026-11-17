# -*- coding: utf-8 -*-
import json
import urllib.request

from . import utils

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
