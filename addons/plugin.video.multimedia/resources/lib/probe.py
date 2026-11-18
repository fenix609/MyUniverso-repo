# -*- coding: utf-8 -*-
"""Comprobar enlaces, buscar sustitutos en archive.org y recordar los que funcionan."""
import json
import os
import urllib.request
from urllib.parse import quote, urlencode, urlparse

CACHE_NAME = "prueba_cache.json"
MAX_BYTES = 60 * 1024 * 1024
MIN_BYTES = 50 * 1024

# Extensión -> nombres de formato de archive.org (si un nombre no existe, simplemente no da resultados)
FORMATS = {
    ".mp4": ["MPEG4", "h.264"], ".mkv": ["Matroska"], ".avi": ["AVI"], ".webm": ["WebM"],
    ".ogv": ["Ogg Video"], ".flv": ["Flash Video"], ".mov": ["QuickTime"],
    ".wmv": ["Windows Media"], ".3gp": ["3GP"], ".mpeg": ["MPEG2", "MPEG1"], ".mpg": ["MPEG2", "MPEG1"],
}
EQUIVALENT = {".mpg": (".mpg", ".mpeg"), ".mpeg": (".mpeg", ".mpg")}


def ext_of(url):
    path = urlparse(url.split("|")[0]).path.lower()
    return path[path.rfind("."):] if "." in path else ""


def http_ok(url, timeout=15):
    """True si el enlace responde con datos válidos (no comprueba que Kodi lo decodifique)."""
    low = url.split("?")[0].lower()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1023"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(1024)
            if low.endswith(".m3u8"):
                return body.lstrip().startswith(b"#EXTM3U")
            if low.endswith(".mpd"):
                return b"<MPD" in body
            return resp.status in (200, 206) and len(body) > 0
    except Exception:
        return False


def search_url(formats):
    query = "mediatype:movies AND ({})".format(" OR ".join('format:"{}"'.format(f) for f in formats))
    params = [("q", query), ("fl[]", "identifier"), ("sort[]", "downloads desc"), ("rows", "25"),
              ("page", "1"), ("output", "json")]
    return "https://archive.org/advancedsearch.php?" + urlencode(params)


def pick_file(metadata, identifier, ext):
    wanted = EQUIVALENT.get(ext, (ext,))
    for f in metadata.get("files", []):
        name = f.get("name", "")
        if "/" in name or not name.lower().endswith(wanted):
            continue
        try:
            size = int(f.get("size", 0))
        except (TypeError, ValueError):
            continue
        if MIN_BYTES <= size <= MAX_BYTES:
            return "https://archive.org/download/{}/{}".format(identifier, quote(name))
    return None


def find_candidates(ext, fetch, limit=3, max_items=12):
    """Busca en archive.org vídeos con esa extensión. fetch(url) -> texto."""
    formats = FORMATS.get(ext)
    if not formats:
        return []
    ids = [d.get("identifier") for d in json.loads(fetch(search_url(formats))).get("response", {}).get("docs", [])]
    found = []
    for ident in [i for i in ids if i][:max_items]:
        try:
            meta = json.loads(fetch("https://archive.org/metadata/" + quote(ident)))
        except Exception:
            continue
        url = pick_file(meta, ident, ext)
        if url and url not in found:
            found.append(url)
        if len(found) >= limit:
            break
    return found


# ---------- caché de resultados ----------
def load_cache(folder):
    try:
        with open(os.path.join(folder, CACHE_NAME), encoding="utf-8") as fh:
            data = json.load(fh)
        return {"overrides": dict(data.get("overrides", {})), "last": dict(data.get("last", {}))}
    except Exception:
        return {"overrides": {}, "last": {}}


def save_cache(folder, cache):
    with open(os.path.join(folder, CACHE_NAME), "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2)


def apply_cache(data, cache):
    """Sustituye los enlaces reemplazados y marca cada vídeo con el resultado de la última prueba."""
    marks = {"OK": " [OK]", "ALT": " [OK]", "NUEVO": " [OK]", "FALLA": " [FALLA]", "OMITIDO": " [SIN ADDON]"}
    for grp in data["groups"]:
        for item in grp["items"]:
            key = item["title"]
            if key in cache["overrides"]:
                item["url"] = cache["overrides"][key]
            item["title"] = key + marks.get(cache["last"].get(key), "")
    return data
