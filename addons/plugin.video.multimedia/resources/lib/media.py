# -*- coding: utf-8 -*-
"""Utilidades puras: tipo de medio, enlaces de YouTube y listas M3U."""
import re
from urllib.parse import urlparse, parse_qs

AUDIO_EXT = (".mp3", ".flac", ".wav", ".ogg", ".oga", ".opus", ".m4a", ".aac", ".wma", ".ape", ".alac", ".aiff", ".mka")
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic", ".avif")

YT_PLUGIN = "plugin://plugin.video.youtube/"
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _ext(url):
    path = urlparse(url.split("|")[0]).path.lower()
    return path[path.rfind("."):] if "." in path else ""


def parse_youtube(value):
    """Devuelve ('video'|'playlist'|'channel', id) o None."""
    if not value:
        return None
    value = value.strip()
    if "://" not in value and "/" not in value and "." not in value:
        if _VIDEO_ID.match(value):
            return ("video", value)
        if value.startswith("UC") and len(value) == 24:
            return ("channel", value)
        if len(value) >= 13 and value[:2] in ("PL", "UU", "OL", "FL", "RD", "LL"):
            return ("playlist", value)
        return None
    parsed = urlparse(value if "://" in value else "https://" + value)
    host = parsed.netloc.lower()
    if not any(h in host for h in ("youtube.com", "youtu.be", "youtube-nocookie.com")):
        return None
    query = parse_qs(parsed.query)
    parts = [p for p in parsed.path.split("/") if p]
    if "youtu.be" in host and parts:
        return ("video", parts[0])
    if query.get("v"):
        return ("video", query["v"][0])
    if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
        return ("video", parts[1])
    if len(parts) >= 2 and parts[0] == "channel":
        return ("channel", parts[1])
    if query.get("list"):
        return ("playlist", query["list"][0])
    return None


def youtube_url(kind, yt_id):
    if kind == "video":
        return "{}play/?video_id={}".format(YT_PLUGIN, yt_id)
    if kind == "playlist":
        return "{}playlist/{}/".format(YT_PLUGIN, yt_id)
    return "{}channel/{}/".format(YT_PLUGIN, yt_id)


def item_kind(entry):
    """Devuelve ('youtube', subtipo, id) o ('audio'|'image'|'video', None, None)."""
    yt = parse_youtube(entry.get("youtube") or entry.get("url", ""))
    if yt:
        return ("youtube", yt[0], yt[1])
    declared = (entry.get("type") or "").lower()
    if declared in ("audio", "music", "musica"):
        return ("audio", None, None)
    if declared in ("image", "photo", "foto", "imagen"):
        return ("image", None, None)
    if declared in ("video",):
        return ("video", None, None)
    ext = _ext(entry.get("url", ""))
    if ext in AUDIO_EXT:
        return ("audio", None, None)
    if ext in IMAGE_EXT:
        return ("image", None, None)
    return ("video", None, None)


def parse_m3u(text):
    """Lista de dicts {title, url, thumb} a partir de un M3U/M3U8."""
    items, title, thumb = [], None, ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-logo="([^"]*)"', line)
            thumb = m.group(1) if m else ""
            title = line.split(",", 1)[1].strip() if "," in line else None
        elif not line.startswith("#"):
            items.append({"title": title or line, "url": line, "thumb": thumb})
            title, thumb = None, ""
    return items
