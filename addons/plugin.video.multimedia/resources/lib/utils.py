# -*- coding: utf-8 -*-
import os
import socket
import time
from urllib.parse import urlparse

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
NAME = "multimedia"


def log(msg, error=False):
    xbmc.log("[{}] {}".format(NAME, msg), xbmc.LOGERROR if error else xbmc.LOGINFO)


def notify(msg, error=False):
    icon = xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO
    xbmcgui.Dialog().notification(NAME, msg, icon)


def get_setting(key):
    return ADDON.getSetting(key)


def get_bool(key, default=True):
    value = ADDON.getSetting(key)
    return default if value == "" else value.lower() == "true"


def has_youtube():
    return xbmc.getCondVisibility("System.HasAddon(plugin.video.youtube)")


def profile_dir():
    """Carpeta de datos del usuario (addon_data); se crea si no existe."""
    path = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def safe_url(url):
    """Dirección sin parámetros (ni claves API) para escribirla en el log."""
    parts = urlparse((url or "").split("|")[0])
    return "{}://{}{}".format(parts.scheme, parts.netloc, parts.path) if parts.scheme else (url or "")[:60]


_PROXY = {"t": 0.0, "v": ""}


def drive_proxy_base():
    """http://127.0.0.1:PUERTO si el proxy local de Drive está activo y responde; si no, ''."""
    if not get_bool("drive_proxy", True):
        return ""
    if time.time() - _PROXY["t"] < 5:  # una lista de episodios llama muchas veces seguidas
        return _PROXY["v"]
    value = ""
    port = xbmcgui.Window(10000).getProperty("multimedia.drive_proxy_port")
    if port:
        try:
            socket.create_connection(("127.0.0.1", int(port)), timeout=0.5).close()
            value = "http://127.0.0.1:{}".format(port)
        except (OSError, ValueError):
            value = ""
    _PROXY.update(t=time.time(), v=value)
    return value
