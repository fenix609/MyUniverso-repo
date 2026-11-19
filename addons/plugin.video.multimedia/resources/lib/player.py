# -*- coding: utf-8 -*-
import http.client
from urllib.parse import quote, urlparse

import xbmc
import xbmcgui
import xbmcplugin

from . import media, utils


def build_listitem(url, title="", kind="video"):
    item = xbmcgui.ListItem(label=title, path=url)
    clean = url.split("|")[0].lower()
    if "google.com" in clean or "googleapis.com" in clean or ("127.0.0.1" in clean and "/drive/" in clean):
        item.setContentLookup(False)  # Drive no responde bien al HEAD previo de Kodi
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


# (id del addon, plantilla para magnet, plantilla para archivo .torrent)
TORRENT_ADDONS = (
    ("plugin.video.elementum", "plugin://plugin.video.elementum/play?uri={}", "plugin://plugin.video.elementum/play?uri={}"),
    ("plugin.video.torrest", "plugin://plugin.video.torrest/play_magnet?magnet={}", "plugin://plugin.video.torrest/play_url?url={}"),
    ("plugin.video.quasar", "plugin://plugin.video.quasar/playuri?uri={}", "plugin://plugin.video.quasar/playuri?uri={}"),
)


def torrent_url(uri):
    """Dirección para reproducir un magnet/.torrent con el addon de torrents instalado (o None)."""
    is_magnet = uri.lower().startswith("magnet:")
    for addon_id, magnet_tpl, file_tpl in TORRENT_ADDONS:
        if xbmc.getCondVisibility("System.HasAddon({})".format(addon_id)):
            return (magnet_tpl if is_magnet else file_tpl).format(quote(uri, safe=""))
    return None


_DRIVE_REASONS = {
    "quota": "Drive: demasiados accesos a este archivo (límite de descargas). Prueba más tarde.",
    "blocked": "Drive bloquea este archivo (límite de accesos o contenido protegido).",
    "private": "El archivo no está compartido como 'Cualquier persona con el enlace'.",
    "scan": "Drive pide confirmación por el tamaño del archivo. Prueba con una clave API en los ajustes.",
    "html": "Drive devolvió una página web en lugar del vídeo.",
}


def _is_drive_proxy(url):
    return url.startswith("http://127.0.0.1:") and "/drive/" in url


def drive_preflight(url):
    """Pregunta al proxy si Drive va a servir el archivo. Devuelve ('ok'|'denied'|'down', mensaje)."""
    parts = urlparse(url)
    try:
        conn = http.client.HTTPConnection(parts.hostname, parts.port, timeout=20)
        conn.request("HEAD", parts.path)
        resp = conn.getresponse()
        status, reason = resp.status, resp.getheader("X-Multimedia-Reason")
        conn.close()
    except Exception as exc:
        return "down", str(exc)
    if status == 200:
        return "ok", ""
    if status in (403, 404, 429):
        if reason in _DRIVE_REASONS:
            return "denied", _DRIVE_REASONS[reason]
        return "denied", "Drive no encuentra el archivo (ID incorrecto o borrado)." if status == 404 else "Drive respondió HTTP {}.".format(status)
    return "down", "HTTP {}".format(status)


def resolve(handle, url, title="", kind="video"):
    if kind == "video" and _is_drive_proxy(url):
        state, message = drive_preflight(url)
        utils.log("Drive vía proxy local: comprobación previa = {} {}".format(state, message))
        if state == "denied":
            utils.log("Drive: {}".format(message), error=True)
            utils.notify(message, error=True)
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
        if state == "down":  # el proxy no funciona: se usa el enlace directo como antes
            utils.log("Proxy de Drive no disponible ({}), se usa el enlace directo".format(message))
            url = media.drive_url(url.rsplit("/", 1)[1], utils.get_setting("drive_api_key"))
    if kind == "torrent":
        target = torrent_url(url)
        if not target:
            utils.notify("Instala Elementum o Torrest para reproducir torrents", error=True)
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
            return
        url = target
    xbmcplugin.setResolvedUrl(handle, True, build_listitem(url, title, kind))
