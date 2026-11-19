# -*- coding: utf-8 -*-
"""Resuelve enlaces de varios servidores a una dirección reproducible por Kodi.

    Google Drive -> proxy local de Drive (o descarga directa si el proxy no está activo)
    Mega         -> proxy local de Mega del servicio del addon (descifra al vuelo, con seek)
    TeraBox      -> API de TeraBox con la cookie 'ndus' de los ajustes (no oficial)
    magnet/.torrent -> Elementum / Torrest / Quasar
    Vidoza, Gamovideo, Streamtape, Voe... -> addon ResolveURL (opcional)
    enlaces .mp4/.mkv/.m3u8... -> directos
"""
import socket
from urllib.parse import urlencode, quote

import xbmcgui

from . import media, utils

DIRECT_EXT = (".mp4", ".mkv", ".m3u8", ".mpd", ".avi", ".webm", ".mov", ".ts")
MEGA_PROPERTY = "multimedia.mega_proxy_port"


class ResolveError(Exception):
    """Error con un mensaje legible para mostrar al usuario."""


def classify(link):
    low = link.lower()
    if low.startswith("magnet:") or media._ext(link) == ".torrent":
        return "torrent"
    name = media.host_name(link)
    if name == "Google Drive":
        return "drive"
    if name == "Mega":
        return "mega"
    if name == "TeraBox":
        return "terabox"
    if media._ext(link) in DIRECT_EXT:
        return "direct"
    return "hoster"


def _drive(link):
    fid = media.drive_id({"drive": link})
    if not fid:
        raise ResolveError("Enlace de Google Drive no válido")
    proxy = utils.drive_proxy_base()
    if proxy:
        return "{}/drive/{}".format(proxy, fid)
    return media.drive_url(fid, utils.get_setting("drive_api_key"))


def mega_proxy_base():
    """http://127.0.0.1:PUERTO si el proxy de Mega del servicio está activo; si no, ''."""
    port = xbmcgui.Window(10000).getProperty(MEGA_PROPERTY)
    if not port:
        return ""
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=0.5).close()
    except (OSError, ValueError):
        return ""
    return "http://127.0.0.1:{}".format(port)


def _mega(link):
    try:
        from . import mega
    except ImportError:
        raise ResolveError("Falta el addon script.module.pycryptodome (necesario para Mega)")
    try:
        mega.parse_link(link)
    except ValueError as exc:
        raise ResolveError(str(exc))
    base = mega_proxy_base()
    if not base:
        raise ResolveError("El proxy de Mega no está activo (reinicia Kodi o revisa script.module.pycryptodome)")
    return "{}/mega?link={}".format(base, quote(link, safe=""))


def _terabox(link):
    try:
        from . import terabox
    except ImportError:
        raise ResolveError("Falta el addon script.module.requests (necesario para TeraBox)")
    cookie = (utils.get_setting("terabox_cookie") or "").strip()
    try:
        dlink, headers = terabox.resolve(link, cookie)
    except (RuntimeError, ValueError) as exc:
        raise ResolveError(str(exc))
    except Exception as exc:  # red caída, respuesta que no es JSON...
        utils.log("TeraBox: {}".format(exc), error=True)
        raise ResolveError("TeraBox no respondió; inténtalo de nuevo más tarde")
    hdr = urlencode({"User-Agent": headers["User-Agent"], "Referer": headers["Referer"], "Cookie": "ndus=" + cookie})
    return "{}|{}".format(dlink, hdr)


def _resolveurl(link):
    try:
        import resolveurl
    except ImportError:
        raise ResolveError("Instala el addon ResolveURL para usar este servidor")
    try:
        if not resolveurl.HostedMediaFile(link).valid_url():
            raise ResolveError("Servidor no soportado por ResolveURL")
        direct = resolveurl.resolve(link)
    except ResolveError:
        raise
    except Exception as exc:
        utils.log("ResolveURL: {}".format(exc), error=True)
        raise ResolveError("No se pudo resolver el enlace (¿caído?)")
    if not direct:
        raise ResolveError("No se pudo resolver el enlace (¿caído?)")
    return direct


def resolve(link):
    """Devuelve (url, kind) listos para player.resolve(); lanza ResolveError con el motivo."""
    kind = classify(link)
    if kind == "drive":
        return _drive(link), "video"
    if kind == "mega":
        return _mega(link), "video"
    if kind == "terabox":
        return _terabox(link), "video"
    if kind == "torrent":
        return link, "torrent"
    if kind == "direct":
        return link, "video"
    return _resolveurl(link), "video"
