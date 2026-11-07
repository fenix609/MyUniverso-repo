# -*- coding: utf-8 -*-
"""mi addon - compatible con Kodi 19 (Matrix) en adelante (20 Nexus, 21 Omega...)."""
import re
import sys
from urllib.parse import urlencode, parse_qsl, quote
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

sys.path.insert(0, xbmcaddon.Addon().getAddonInfo("path") + "/resources/lib")
from menus import MENU  # noqa: E402

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

try:
    KODI_MAJOR = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0].split("-")[0])
except Exception:
    KODI_MAJOR = 19


# ----------------------------------------------------------------- utilidades
def build_url(**params):
    return BASE_URL + "?" + urlencode(params)


def has_addon(addon_id):
    return xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id)


def notify(msg, icon=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification(ADDON.getAddonInfo("name"), msg, icon, 4000)


def set_info(item, label, plot=""):
    """Metadatos compatibles: setInfo en Kodi 19, InfoTagVideo en Kodi 20+."""
    if KODI_MAJOR >= 20:
        tag = item.getVideoInfoTag()
        tag.setTitle(label)
        if plot:
            tag.setPlot(plot)
    else:
        item.setInfo("video", {"title": label, "plot": plot})


YT = "plugin://plugin.video.youtube"


def yt_video_id(value):
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/|live/)([\w-]{11})", value)
    if m:
        return m.group(1)
    return value if re.fullmatch(r"[\w-]{11}", value) else None


def yt_playlist_id(value):
    m = re.search(r"list=([\w-]+)", value)
    return m.group(1) if m else value


def yt_channel_id(value):
    m = re.search(r"channel/([\w-]+)", value)
    return m.group(1) if m else value


def is_youtube(url):
    return bool(re.match(r"https?://(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/", url))


def find_children(path):
    nodes = MENU
    for part in [p for p in path.split("/") if p]:
        match = next((n for n in nodes if n.get("id") == part and "children" in n), None)
        if match is None:
            return []
        nodes = match["children"]
    return nodes


# ----------------------------------------------------------------- listados
def list_menu(path):
    xbmcplugin.setPluginCategory(HANDLE, ADDON.getAddonInfo("name"))
    xbmcplugin.setContent(HANDLE, "videos")
    children = find_children(path)

    if not children:
        item = xbmcgui.ListItem(label="(Vacío - aún no hay contenido)")
        item.setArt({"icon": "DefaultIconInfo.png"})
        xbmcplugin.addDirectoryItem(HANDLE, build_url(action="empty"), item, False)

    for node in children:
        label = node["label"]
        item = xbmcgui.ListItem(label=label)
        icon = node.get("icon", "DefaultFolder.png")
        item.setArt({"icon": icon, "thumb": icon})
        set_info(item, label, node.get("plot", ""))

        if "children" in node:
            new_path = (path + "/" if path else "") + node["id"]
            xbmcplugin.addDirectoryItem(HANDLE, build_url(action="list", path=new_path), item, True)
        elif "m3u" in node:
            xbmcplugin.addDirectoryItem(HANDLE, build_url(action="m3u", url=node["m3u"]), item, True)
        elif "youtube_playlist" in node:
            target = "%s/playlist/%s/" % (YT, yt_playlist_id(node["youtube_playlist"]))
            xbmcplugin.addDirectoryItem(HANDLE, target, item, True)
        elif "youtube_channel" in node:
            target = "%s/channel/%s/" % (YT, yt_channel_id(node["youtube_channel"]))
            xbmcplugin.addDirectoryItem(HANDLE, target, item, True)
        elif "youtube_search" in node:
            target = "%s/kodion/search/query/?q=%s" % (YT, quote(node["youtube_search"]))
            xbmcplugin.addDirectoryItem(HANDLE, target, item, True)
        elif "youtube_video" in node:
            vid = yt_video_id(node["youtube_video"])
            if vid:
                item.setProperty("IsPlayable", "true")
                xbmcplugin.addDirectoryItem(
                    HANDLE, build_url(action="play", url="%s/play/?video_id=%s" % (YT, vid)), item, False)
        elif "url" in node:
            item.setProperty("IsPlayable", "true")
            params = {"action": "play", "url": node["url"]}
            for key in ("live", "headers", "license_type", "license_key"):
                if node.get(key):
                    params[key] = "1" if node[key] is True else node[key]
            xbmcplugin.addDirectoryItem(HANDLE, build_url(**params), item, False)

    xbmcplugin.endOfDirectory(HANDLE)


# ----------------------------------------------------------------- M3U / IPTV
def read_text(url):
    if url.startswith(("http://", "https://")):
        req = Request(url, headers={"User-Agent": UA})
        return urlopen(req, timeout=20).read().decode("utf-8", "replace")
    f = xbmcvfs.File(url)
    try:
        data = f.read()
    finally:
        f.close()
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def parse_m3u(text):
    channels, cur = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            cur = {
                "name": line.rsplit(",", 1)[-1].strip() or attrs.get("tvg-name", "Canal"),
                "logo": attrs.get("tvg-logo", ""),
                "group": attrs.get("group-title", ""),
            }
        elif line and not line.startswith("#") and cur is not None:
            cur["url"] = line
            channels.append(cur)
            cur = None
    return channels


def list_m3u(url, group):
    xbmcplugin.setContent(HANDLE, "videos")
    try:
        channels = parse_m3u(read_text(url))
    except Exception as exc:  # red caída, ruta inválida...
        notify("No se pudo cargar la lista: %s" % exc, xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    groups = sorted({c["group"] for c in channels if c["group"]})
    if group is None and len(groups) > 1:
        for g in ["__all__"] + groups:
            item = xbmcgui.ListItem(label="Todos los canales" if g == "__all__" else g)
            item.setArt({"icon": "DefaultFolder.png"})
            xbmcplugin.addDirectoryItem(HANDLE, build_url(action="m3u", url=url, group=g), item, True)
    else:
        for ch in channels:
            if group not in (None, "__all__") and ch["group"] != group:
                continue
            item = xbmcgui.ListItem(label=ch["name"])
            art = {"icon": ch["logo"] or "DefaultAddonPVRClient.png"}
            art["thumb"] = art["icon"]
            item.setArt(art)
            set_info(item, ch["name"])
            item.setProperty("IsPlayable", "true")
            xbmcplugin.addDirectoryItem(
                HANDLE, build_url(action="play", url=ch["url"], live="1"), item, False)
    xbmcplugin.endOfDirectory(HANDLE)


# ----------------------------------------------------------------- reproducción
def play(params):
    url = params["url"]
    live = params.get("live") == "1"
    headers = params.get("headers", "")
    low = url.lower().split("?")[0]

    # --- Torrents / magnets -> Elementum o Torrest
    if url.startswith("magnet:") or low.endswith(".torrent"):
        if has_addon("plugin.video.elementum"):
            target = "plugin://plugin.video.elementum/play?uri=" + quote(url, safe="")
        elif has_addon("plugin.video.torrest"):
            if url.startswith("magnet:"):
                target = "plugin://plugin.video.torrest/play_magnet?magnet=" + quote(url, safe="")
            else:
                target = "plugin://plugin.video.torrest/play_url?url=" + quote(url, safe="")
        else:
            notify("Instala Elementum o Torrest para reproducir torrents", xbmcgui.NOTIFICATION_WARNING)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        xbmcplugin.setResolvedUrl(HANDLE, True, xbmcgui.ListItem(path=target))
        return

    # --- Enlaces de YouTube (watch, youtu.be, shorts...) -> addon de YouTube
    if is_youtube(url):
        vid = yt_video_id(url)
        if vid:
            url = "%s/play/?video_id=%s" % (YT, vid)

    # --- Otros addons (YouTube, etc.)
    if url.startswith("plugin://"):
        if url.startswith(YT) and not has_addon("plugin.video.youtube"):
            notify("Instala el addon de YouTube", xbmcgui.NOTIFICATION_WARNING)
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            return
        xbmcplugin.setResolvedUrl(HANDLE, True, xbmcgui.ListItem(path=url))
        return

    play_url = url + ("|" + headers if headers and url.startswith("http") else "")
    item = xbmcgui.ListItem(path=play_url)

    if low.endswith(".m3u8") or low.endswith(".mpd"):
        manifest = "hls" if low.endswith(".m3u8") else "mpd"
        mime = "application/x-mpegURL" if manifest == "hls" else "application/dash+xml"
        if has_addon("inputstream.adaptive"):
            item.setProperty("inputstream", "inputstream.adaptive")
            item.setProperty("inputstream.adaptive.manifest_type", manifest)
            item.setMimeType(mime)
            item.setContentLookup(False)
            if headers:
                item.setProperty("inputstream.adaptive.stream_headers", headers)
            if params.get("license_type"):
                item.setProperty("inputstream.adaptive.license_type", params["license_type"])
                if params.get("license_key"):
                    item.setProperty("inputstream.adaptive.license_key", params["license_key"])
                try:
                    import inputstreamhelper
                    inputstreamhelper.Helper(manifest, drm=params["license_type"]).check_inputstream()
                except Exception:
                    pass
    elif url.startswith(("rtmp://", "rtmpe://", "rtmps://", "rtmpt://")):
        if has_addon("inputstream.rtmp"):
            item.setProperty("inputstream", "inputstream.rtmp")
    elif live and url.startswith("http") and has_addon("inputstream.ffmpegdirect"):
        item.setProperty("inputstream", "inputstream.ffmpegdirect")
        item.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "true")
        item.setProperty("inputstream.ffmpegdirect.stream_mode", "default")
        item.setMimeType("video/mp2t")
        item.setContentLookup(False)

    xbmcplugin.setResolvedUrl(HANDLE, True, item)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    action = params.get("action", "list")
    if action == "list":
        list_menu(params.get("path", ""))
    elif action == "m3u":
        list_m3u(params["url"], params.get("group"))
    elif action == "play":
        play(params)
    elif action == "empty":
        notify("Esta sección aún no tiene contenido")
    else:
        list_menu("")


if __name__ == "__main__":
    router(sys.argv[2][1:])
