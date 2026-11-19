# -*- coding: utf-8 -*-
import os
import socket

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


def drive_proxy_base():
    """http://127.0.0.1:PUERTO si el proxy local de Drive está activo y responde; si no, ''."""
    if not get_bool("drive_proxy", True):
        return ""
    port = xbmcgui.Window(10000).getProperty("multimedia.drive_proxy_port")
    if not port:
        return ""
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=0.5).close()
    except (OSError, ValueError):
        return ""
    return "http://127.0.0.1:{}".format(port)
