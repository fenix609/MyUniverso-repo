# -*- coding: utf-8 -*-
"""Utilidades puras: tipo de medio, enlaces de YouTube y listas M3U."""
import re
import unicodedata
from urllib.parse import urlparse, parse_qs, quote

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


# ---------- Google Drive ----------
_DRIVE_HOSTS = ("drive.google.com", "docs.google.com", "drive.usercontent.google.com")
_DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{20,}$")
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def drive_id(entry):
    """ID de archivo de Drive a partir de `drive` (enlace o ID) o de un `url` de Drive."""
    value = (entry.get("drive") or "").strip()
    if not value:
        url = (entry.get("url") or "").strip()
        if urlparse(url).netloc.lower() in _DRIVE_HOSTS:
            value = url
    if not value:
        return ""
    if "://" not in value:
        return value if _DRIVE_ID.match(value) else ""
    parsed = urlparse(value)
    if parsed.netloc.lower() not in _DRIVE_HOSTS:
        return ""
    query = parse_qs(parsed.query)
    if query.get("id"):
        return query["id"][0]
    parts = [p for p in parsed.path.split("/") if p]
    if "d" in parts and parts.index("d") + 1 < len(parts):
        return parts[parts.index("d") + 1]
    return ""


def drive_url(file_id, api_key="", headers=True):
    """Enlace directo de reproducción para un archivo de Drive con permiso 'cualquiera con el enlace'."""
    if api_key:
        return "https://www.googleapis.com/drive/v3/files/{}?alt=media&key={}".format(file_id, quote(api_key, safe=""))
    url = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t".format(file_id)
    return url + "|User-Agent={}".format(quote(_UA, safe="")) if headers else url


# ---------- arte e información ----------
ART_KEYS = ("thumb", "icon", "poster", "fanart", "banner", "clearlogo", "landscape")
_TEXT_INFO = ("plot", "genre", "mpaa", "studio", "director", "writer", "premiered", "aired", "tagline",
              "originaltitle", "tvshowtitle", "country", "mediatype")


def art_of(entry):
    art = {k: entry[k] for k in ART_KEYS if entry.get(k)}
    if "thumb" not in art and "icon" in art:
        art["thumb"] = art["icon"]
    if "icon" not in art and "thumb" in art:
        art["icon"] = art["thumb"]
    return art


def video_info(entry, title):
    """Diccionario para ListItem.setInfo('video', ...) a partir de los atributos del elemento."""
    info = {"title": title}
    for key in _TEXT_INFO:
        if entry.get(key):
            info[key] = entry[key]
    for key in ("year", "season", "episode"):
        try:
            info[key] = int(entry[key])
        except (KeyError, TypeError, ValueError):
            pass
    try:
        info["rating"] = float(entry["rating"])
    except (KeyError, TypeError, ValueError):
        pass
    try:
        info["duration"] = int(float(entry["duration"]) * 60)  # en el XML, minutos
    except (KeyError, TypeError, ValueError):
        pass
    if "mediatype" not in info and "episode" in info:
        info["mediatype"] = "episode"
    return info


# ---------- varios servidores por vídeo ----------
# Atributos del XML que admiten un enlace: drive="", mega="", terabox="", vidoza="", gamovideo="".
SERVER_ATTRS = (("drive", "Google Drive"), ("mega", "Mega"), ("terabox", "TeraBox"),
                ("vidoza", "Vidoza"), ("gamovideo", "Gamovideo"))
_HOSTERS = {
    "mega.nz": "Mega", "mega.co.nz": "Mega",
    "terabox.com": "TeraBox", "1024terabox.com": "TeraBox", "teraboxapp.com": "TeraBox",
    "1024tera.com": "TeraBox", "terafileshare.com": "TeraBox", "4funbox.com": "TeraBox", "mirrobox.com": "TeraBox",
    "vidoza.net": "Vidoza", "vidoza.org": "Vidoza",
    "gamovideo.com": "Gamovideo",
    "streamtape.com": "Streamtape", "voe.sx": "Voe", "filemoon.sx": "Filemoon", "mixdrop.co": "Mixdrop",
    "upstream.to": "Upstream", "dood.wf": "Doodstream", "doodstream.com": "Doodstream",
    "streamwish.to": "Streamwish", "filelions.to": "Filelions",
}


def host_name(url):
    """Nombre del servidor si el enlace es de uno conocido (Mega, TeraBox, Vidoza...); si no, ''."""
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower().split(":")[0]
    if host in _DRIVE_HOSTS:
        return "Google Drive"
    for domain, name in _HOSTERS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return ""


def server_sources(entry):
    """Lista de {'name','url'} con todos los enlaces del vídeo: drive/mega/terabox/vidoza/gamovideo,
    url (si es de un servidor conocido o hay más enlaces) y los <source name= url=> hijos."""
    out = []
    for key, name in SERVER_ATTRS:
        value = (entry.get(key) or "").strip()
        if not value:
            continue
        if key == "drive":
            fid = drive_id({"drive": value})
            value = "https://drive.google.com/file/d/{}/view".format(fid) if fid else value
        out.append({"name": name, "url": value})
    for src in entry.get("sources") or []:
        out.append({"name": src.get("name") or host_name(src["url"]) or "Enlace", "url": src["url"]})
    url = (entry.get("url") or "").strip()
    if url and not drive_id({"url": url}) and (host_name(url) or out):
        out.append({"name": host_name(url) or "Enlace directo", "url": url})
    seen, unique = set(), []
    for src in out:
        if src["url"] not in seen:
            seen.add(src["url"])
            unique.append(src)
    return unique


def needs_server_picker(sources):
    """True si el vídeo se reproduce con la lógica de servidores (varios enlaces o un servidor que no es Drive)."""
    if not sources:
        return False
    return len(sources) > 1 or host_name(sources[0]["url"]) not in ("", "Google Drive")


def item_kind(entry):
    """Devuelve ('youtube', subtipo, id) o ('audio'|'image'|'video', None, None)."""
    fid = drive_id(entry)
    if fid:
        return ("drive", None, fid)
    if any(k in entry for k, _ in SERVER_ATTRS) and not server_sources(entry) \
            and not any(entry.get(k) for k in ("url", "youtube")):
        return ("nolink", None, None)  # vídeo o episodio sin enlace todavía
    yt = parse_youtube(entry.get("youtube") or entry.get("url", ""))
    if yt:
        return ("youtube", yt[0], yt[1])
    declared = (entry.get("type") or "").lower()
    url_low = entry.get("url", "").lower()
    if declared == "torrent" or url_low.startswith("magnet:") or _ext(entry.get("url", "")) == ".torrent":
        return ("torrent", None, None)
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
    """Lista de dicts {title, url, thumb, group} a partir de un M3U/M3U8."""
    items, title, thumb, group = [], None, "", ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            m = re.search(r'tvg-logo="([^"]*)"', line)
            thumb = m.group(1) if m else ""
            g = re.search(r'group-title="([^"]*)"', line)
            group = g.group(1).strip() if g else ""
            title = line.split(",", 1)[1].strip() if "," in line else None
        elif not line.startswith("#"):
            items.append({"title": title or line, "url": line, "thumb": thumb, "group": group})
            title, thumb, group = None, "", ""
    return items


def norm(text):
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).strip().lower()


_PRIORITY = ("nacionales", "informativos", "deportivos", "infantiles")
_COMMUNITIES = (
    ("andalucia",), ("aragon",), ("asturias",), ("balears", "baleares"), ("canarias",),
    ("cantabria",), ("castilla-la mancha", "castilla la mancha"), ("castilla y leon",),
    ("catalu",), ("ceuta",), ("valencian",), ("extremadura",), ("galicia",), ("rioja",),
    ("madrid",), ("melilla",), ("murcia",), ("navarra",), ("pais vasco", "euskadi"),
)


def group_sort_key(name):
    """Nacionales y temáticos primero; después las comunidades; el resto al final."""
    n = norm(name)
    for i, key in enumerate(_PRIORITY):
        if key in n:
            return (0, i, n)
    for i, keys in enumerate(_COMMUNITIES):
        if any(k in n for k in keys):
            return (1, i, n)
    return (2, 0, n)
