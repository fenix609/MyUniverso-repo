#!/usr/bin/env python3
"""Comprueba qué enlaces de una lista responden.
Uso:  python check_streams.py [Código/TDT.xml | Código/Prueba.xml | lista.m3u | URL]
- .m3u8 -> debe empezar por #EXTM3U      - .mpd -> debe contener <MPD
- resto (mp4, mkv, avi...) -> responde HTTP 200/206 y devuelve datos
Ejecútalo desde España: muchas emisiones solo funcionan con IP española."""
import re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

SRC = sys.argv[1] if len(sys.argv) > 1 else "Código/TDT.xml"
UA = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1023"}


def read(src):
    if src.startswith("http"):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    with open(src, encoding="utf-8") as fh:
        return fh.read()


def parse(text):
    if text.lstrip().startswith("<?xml") or "<tdt" in text[:600] or "<lista" in text[:600]:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(text.encode("utf-8"))
        return [(g.get("name", ""), c.get("name") or c.get("title", ""), c.get("url", ""))
                for g in root.findall("group") for c in list(g.findall("channel")) + list(g.findall("item"))]
    out, title, group = [], None, ""
    for line in (l.strip() for l in text.splitlines()):
        if line.startswith("#EXTINF"):
            g = re.search(r'group-title="([^"]*)"', line)
            group = g.group(1) if g else ""
            title = line.split(",", 1)[1].strip() if "," in line else None
        elif line and not line.startswith("#"):
            out.append((group, title or line, line))
            title, group = None, ""
    return out


def check(item):
    group, title, url = item
    low = url.split("?")[0].lower()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as resp:
            body = resp.read(1024)
            if low.endswith(".m3u8"):
                ok = body.lstrip().startswith(b"#EXTM3U")
            elif low.endswith(".mpd"):
                ok = b"<MPD" in body
            else:
                ok = resp.status in (200, 206) and len(body) > 0
            return ok, group, title, url, "OK" if ok else "respuesta no válida"
    except Exception as exc:
        return False, group, title, url, str(exc)[:70]


if __name__ == "__main__":
    channels = [c for c in parse(read(SRC)) if c[2]]
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(check, channels))
    for ok, group, title, url, msg in results:
        print("{}  [{}] {}  ->  {}".format("OK " if ok else "FALLA", group, title, msg))
    good = sum(1 for r in results if r[0])
    print("\n{} de {} enlaces responden".format(good, len(results)))
