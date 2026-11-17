# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
import xbmcplugin

from . import media, utils


def build_listitem(url, title="", kind="video"):
    item = xbmcgui.ListItem(label=title, path=url)
    clean = url.split("|")[0].lower()
    if ".m3u8" in clean:
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "hls")
    elif ".mpd" in clean:
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "mpd")
    if kind == "audio":
        item.setInfo("music", {"title": title})
    elif kind == "video":
        item.setInfo("video", {"title": title})
    return item


def resolve(handle, url, title="", kind="video"):
    xbmcplugin.setResolvedUrl(handle, True, build_listitem(url, title, kind))


def open_link():
    """Pide un enlace (YouTube, vídeo, audio o imagen) y lo reproduce/muestra."""
    link = xbmcgui.Dialog().input("Pega un enlace o ID de YouTube", type=xbmcgui.INPUT_ALPHANUM)
    if not link:
        return
    entry = {"url": link.strip()}
    kind, sub, yt_id = media.item_kind(entry)
    if kind == "youtube":
        if not utils.has_youtube():
            utils.notify("Falta el addon de YouTube", error=True)
            return
        if sub == "video":
            xbmc.Player().play(media.youtube_url("video", yt_id))
        else:
            xbmc.executebuiltin('ActivateWindow(Videos,"{}",return)'.format(media.youtube_url(sub, yt_id)))
    elif kind == "image":
        xbmc.executebuiltin('ShowPicture("{}")'.format(entry["url"]))
    else:
        xbmc.Player().play(entry["url"], build_listitem(entry["url"], entry["url"], kind))
