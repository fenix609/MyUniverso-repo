# -*- coding: utf-8 -*-
"""Puente hacia Balandro (código de Team Balandro, GNU GPL v3) incrustado en resources/balandro.

Balandro usa imports absolutos (platformcode, core, modules, channels, servers...), así que
su carpeta se añade a sys.path y se ejecuta su default.py con los mismos sys.argv de Kodi.
Todas las URL que genera Balandro (plugin://plugin.video.multimedia/?<item>) vuelven a
main.py y el router las reenvía aquí.
"""
import os
import sys

ADDON_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BAL_DIR = os.path.join(ADDON_DIR, "resources", "balandro")

# Entradas que se pueden poner en menú.xml:  <submenu name="..." file="balandro:movies"/>
KINDS = {
    "manage": ("Servidores · Gestionar", "Activar, desactivar y añadir servidores"),
    "search": ("Servidores · Buscar", "Escribe un título y se busca en todos los servidores de películas y series"),
    "main": ("Servidores", "Todos los servidores: películas, series, buscador, novedades..."),
    "movies": ("Servidores · Películas", "Servidores con películas"),
    "tvshows": ("Servidores · Series", "Servidores con series"),
}


def is_balandro_query(raw):
    """True si la cadena de parámetros ('?....') la generó Balandro."""
    raw = (raw or "")[1:] if (raw or "").startswith("?") else (raw or "")
    return bool(raw) and ("action=" not in raw or "channel=" in raw)


def _prepare():
    if BAL_DIR not in sys.path:
        sys.path.insert(0, BAL_DIR)
    lib = os.path.join(BAL_DIR, "lib")
    if lib not in sys.path:
        sys.path.append(lib)


def _query_for(kind):
    if kind in (None, "", "main"):
        return ""  # default.py abre mainmenu/mainlist
    from platformcode import config
    if str(config.get_setting("PY3")) == "":  # igual que hace default.py en la primera ejecución
        config.set_setting("PY3", True)
    from core.item import Item
    if kind == "search":  # buscador general: pide el título y busca en todos los canales (películas y series)
        return "?" + Item(channel="search", action="search", search_type="all",
                          title=KINDS[kind][0]).tourl()
    if kind == "manage":  # gestor: activar/desactivar y añadir servidores
        return "?" + Item(channel="manager", action="mainlist", title=KINDS[kind][0]).tourl()
    return "?" + Item(channel="mainmenu", action="channels", extra=kind,
                      title=KINDS[kind][0]).tourl()


def run(argv, query="", kind=None):
    """Ejecuta Balandro. query: '?<item>' ya hecho por Balandro, o kind: main/movies/tvshows."""
    _prepare()
    # sys.argv[0] debe seguir siendo plugin://plugin.video.multimedia/ ANTES de importar Balandro
    # (platformcode.config lo lee al importarse y con él construye todas las URL).
    sys.argv = [argv[0], str(argv[1]), query or ""]
    if not query:
        sys.argv[2] = _query_for(kind)
    path = os.path.join(BAL_DIR, "default.py")
    with open(path, "r", encoding="utf-8") as fh:
        code = compile(fh.read(), path, "exec")
    exec(code, {"__name__": "__main__", "__file__": path})  # no runpy: pisaría sys.argv[0]
