# -*- coding: utf-8 -*-
"""Lista el contenido de carpetas compartidas de Google Drive y Mega (fotos y vídeos).

Drive : con clave API (ajustes) usa la API oficial; sin clave lee la vista pública de la carpeta
        (la carpeta debe estar compartida como "Cualquier persona con el enlace").
Mega  : descifra el listado de la carpeta con la clave del enlace (mega.py).
"""
import json
import re
from html import unescape
from urllib.parse import quote, urlparse, parse_qs
from urllib.request import Request, urlopen

from . import media

IMAGE_EXT = media.IMAGE_EXT
VIDEO_EXT = (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".mpg", ".mpeg", ".ts", ".3gp")
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_ID = re.compile(r"^[A-Za-z0-9_-]{10,}$")


def kind_of(name, mime=""):
    """'image' | 'audio' | 'video' | '' según el nombre o el tipo MIME."""
    low = (name or "").lower()
    ext = "." + low.rsplit(".", 1)[-1] if "." in low else ""
    if (mime or "").startswith("image/") or ext in IMAGE_EXT:
        return "image"
    if (mime or "").startswith("audio/") or ext in media.AUDIO_EXT:
        return "audio"
    if (mime or "").startswith("video/") or ext in VIDEO_EXT:
        return "video"
    return ""


def drive_folder_id(ref):
    """ID de carpeta de Drive a partir de un enlace o del propio ID."""
    ref = (ref or "").strip()
    if "://" not in ref:
        return ref if _ID.match(ref) else ""
    parsed = urlparse(ref)
    q = parse_qs(parsed.query)
    if q.get("id"):
        return q["id"][0]
    parts = [p for p in parsed.path.split("/") if p]
    if "folders" in parts and parts.index("folders") + 1 < len(parts):
        return parts[parts.index("folders") + 1]
    return ""


def _get(url, timeout=25):
    return urlopen(Request(url, headers={"User-Agent": _UA, "Accept-Language": "es"}), timeout=timeout).read().decode("utf-8", "replace")


def _drive_api(folder_id, api_key):
    out, token = [], ""
    for _ in range(20):  # hasta 20 páginas de 1000
        url = ("https://www.googleapis.com/drive/v3/files?q={}&fields={}&pageSize=1000&orderBy=name&key={}"
               .format(quote("'{}' in parents and trashed=false".format(folder_id)),
                       quote("nextPageToken,files(id,name,mimeType)"), quote(api_key, safe="")))
        if token:
            url += "&pageToken=" + quote(token)
        data = json.loads(_get(url))
        for f in data.get("files", []):
            out.append({"id": f["id"], "name": f.get("name", ""), "folder": f.get("mimeType") == "application/vnd.google-apps.folder",
                        "mime": f.get("mimeType", "")})
        token = data.get("nextPageToken", "")
        if not token:
            break
    return out


_ENTRY = re.compile(r'<div class="flip-entry" id="entry-([\w-]+)"(.*?)<div class="flip-entry-title">(.*?)</div>', re.S)


def _drive_public(folder_id):
    html = _get("https://drive.google.com/embeddedfolderview?id={}#list".format(quote(folder_id, safe="")))
    out = []
    for fid, block, title in _ENTRY.findall(html):
        out.append({"id": fid, "name": unescape(re.sub(r"<[^>]+>", "", title)).strip(),
                    "folder": "/drive/folders/" in block, "mime": ""})
    return out


def drive_list(ref, api_key=""):
    """Contenido de una carpeta de Drive: [{id, name, folder, mime}] (carpetas primero, por nombre)."""
    fid = drive_folder_id(ref)
    if not fid:
        raise ValueError("Enlace de carpeta de Google Drive no válido")
    try:
        items = _drive_api(fid, api_key) if api_key else _drive_public(fid)
    except Exception as exc:
        if api_key:
            raise RuntimeError("Drive no dejó leer la carpeta (¿clave API incorrecta o carpeta privada?): {}".format(exc))
        raise RuntimeError("No se pudo leer la carpeta de Drive. Compártela como 'Cualquier persona con el enlace' "
                           "o pon una clave API de Drive en los ajustes ({})".format(exc))
    if not items and not api_key:
        raise RuntimeError("La carpeta de Drive salió vacía o Drive no dejó verla. Si no está vacía, pon una clave API de Drive en los ajustes")
    items.sort(key=lambda x: (not x["folder"], x["name"].lower()))
    return items
