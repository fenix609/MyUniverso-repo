# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcaddon

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
