# -*- coding: utf-8 -*-
"""Mi Centro - add-on base para Kodi 19+ (Python 3).

Menu:  Peliculas / Series  ->  Probar add-on  ->  pruebas de reproduccion.
Para anadir secciones, crea una funcion y registrala en ROUTES.
"""
import re
import sys
import time
import traceback
from urllib.parse import urlencode, parse_qsl, quote
from urllib.request import Request, urlopen

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
ADDON_NAME = "Mi Centro"

# ---------------------------------------------------------------------------
# Enlaces de prueba. Todos son videos de muestra publicos (Big Buck Bunny,
# Sintel...). "method" indica COMO se reproduce cada uno.
# ---------------------------------------------------------------------------
HTTP_MP4 = "http://download.blender.org/durian/trailer/sintel_trailer-480p.mp4"
SINTEL_MP4 = "https://download.blender.org/durian/trailer/sintel_trailer-480p.mp4"
HTTPS_WEBM = "https://test-videos.co.uk/vids/bigbuckbunny/webm/vp9/360/Big_Buck_Bunny_360_10s_1MB.webm"
NET_EXAMPLE = "smb://servidor/carpeta/video.mp4"
BBB_HLS = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
BBB_DASH = "https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps.mpd"
YOUTUBE_ID = "aqz-KE-bpKQ"  # Big Buck Bunny

TESTS = [
    {"title": "1. MP4 directo (HTTP)", "method": "resolve", "url": HTTP_MP4,
     "info": "Enlace directo a un .mp4 por HTTP."},
    {"title": "2. Video directo WebM (HTTPS)", "method": "resolve", "url": HTTPS_WEBM,
     "info": "Enlace directo a un .webm por HTTPS."},
    {"title": "3. HLS (.m3u8) con el reproductor nativo", "method": "resolve", "url": BBB_HLS,
     "info": "Streaming HLS reproducido por FFmpeg de Kodi."},
    {"title": "4. HLS (.m3u8) con inputstream.adaptive", "method": "adaptive_hls", "url": BBB_HLS,
     "needs": "inputstream.adaptive", "info": "HLS con calidad adaptativa."},
    {"title": "5. DASH (.mpd) con inputstream.adaptive", "method": "adaptive_mpd", "url": BBB_DASH,
     "needs": "inputstream.adaptive", "info": "Streaming DASH."},
    {"title": "6. Enlace con cabeceras (User-Agent / Referer)", "method": "headers", "url": SINTEL_MP4,
     "info": "Formato url|Cabecera=valor, habitual en add-ons de streaming."},
    {"title": "7. Reproducir con xbmc.Player().play()", "method": "player", "url": SINTEL_MP4,
     "info": "Lanza el reproductor directamente desde el codigo."},
    {"title": "8. Reproducir con PlayMedia()", "method": "builtin", "url": SINTEL_MP4,
     "info": "Usa la funcion integrada PlayMedia de Kodi."},
    {"title": "9. Enlace a otro add-on (YouTube)", "method": "resolve",
     "url": "plugin://plugin.video.youtube/play/?video_id=" + YOUTUBE_ID,
     "needs": "plugin.video.youtube", "check": False,
     "info": "Requiere tener instalado el add-on oficial de YouTube."},
    {"title": "10. Video con subtítulos externos (.srt)", "method": "subtitles", "url": SINTEL_MP4,
     "info": "Crea un .srt de ejemplo y lo carga junto al video. Activa los subtítulos en el reproductor."},
    {"title": "11. Archivo local (elige uno del dispositivo)", "method": "browse_local",
     "info": "Abre el explorador de Kodi para elegir un video de la memoria, USB o tarjeta SD."},
    {"title": "12. Recurso de red (SMB / NFS / HTTP)", "method": "network",
     "info": "Escribe una ruta como smb://servidor/carpeta/video.mp4 o nfs://192.168.1.10/video.mkv."},
]

# Lista M3U de ejemplo (formato habitual de listas de TV en directo)
SAMPLE_M3U = """#EXTM3U
#EXTINF:-1 tvg-id="prueba1" group-title="Pruebas",Prueba HLS 1 (Big Buck Bunny)
""" + BBB_HLS + """
#EXTINF:-1 tvg-id="prueba2" group-title="Pruebas",Prueba HLS 2 (Mux test stream)
https://test-streams.mux.dev/test_001/stream.m3u8
#EXTINF:-1 tvg-id="prueba3" group-title="Pruebas",Prueba MP4 (Sintel)
""" + SINTEL_MP4 + """
"""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def log(message, level=None):
    """Escribe en kodi.log con el prefijo [Mi Centro] (visible con el log en modo normal)."""
    xbmc.log("[Mi Centro] {0}".format(message), xbmc.LOGINFO if level is None else level)


def build_url(**params):
    return "{0}?{1}".format(BASE_URL, urlencode(params))


def has_addon(addon_id):
    return xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id))


def notify(message, icon=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification(ADDON_NAME, message, icon, 4000)


def set_title(item, title, info=""):
    """Metadatos compatibles con Kodi 19, 20, 21 y posteriores."""
    tag = item.getVideoInfoTag()
    if hasattr(tag, "setTitle"):          # Kodi 20+
        tag.setTitle(title)
        if info and hasattr(tag, "setPlot"):
            tag.setPlot(info)
    else:                                  # Kodi 19
        item.setInfo("video", {"title": title, "plot": info})


def add_folder(label, **params):
    item = xbmcgui.ListItem(label=label)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**params), item, isFolder=True)


def add_playable(label, info="", art=None, **params):
    item = xbmcgui.ListItem(label=label)
    item.setProperty("IsPlayable", "true")
    set_title(item, label, info)
    if art:
        item.setArt({"thumb": art, "icon": art})
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**params), item, isFolder=False)


def add_action(label, **params):
    item = xbmcgui.ListItem(label=label)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(**params), item, isFolder=False)


# ---------------------------------------------------------------------------
# Menus
# ---------------------------------------------------------------------------
def main_menu(params):
    add_folder("Películas", action="movies")
    add_folder("Series", action="series")
    xbmcplugin.endOfDirectory(HANDLE)


def movies_menu(params):
    xbmcplugin.setPluginCategory(HANDLE, "Películas")
    xbmcplugin.setContent(HANDLE, "movies")
    add_folder("Probar add-on", action="test", section="Películas")
    xbmcplugin.endOfDirectory(HANDLE)


def series_menu(params):
    xbmcplugin.setPluginCategory(HANDLE, "Series")
    xbmcplugin.setContent(HANDLE, "tvshows")
    add_folder("Probar add-on", action="test", section="Series")
    xbmcplugin.endOfDirectory(HANDLE)


def test_menu(params):
    xbmcplugin.setPluginCategory(HANDLE, "Probar add-on")
    xbmcplugin.setContent(HANDLE, "videos")
    add_action("» Comprobar todos los enlaces (diagnóstico)", action="check_all")
    add_folder("» Lista M3U de ejemplo (TV en directo)", action="m3u")
    add_folder("» Abrir mi propia lista M3U (URL o archivo)", action="m3u_ask")
    for index, test in enumerate(TESTS):
        if test["method"] in ("player", "builtin"):
            # Estas pruebas lanzan el reproductor por su cuenta: no deben ser "reproducibles"
            add_action(test["title"], action="play", id=index)
        else:
            add_playable(test["title"], test.get("info", ""), action="play", id=index)
    xbmcplugin.endOfDirectory(HANDLE)


# ---------------------------------------------------------------------------
# Reproduccion
# ---------------------------------------------------------------------------
def _play(params):
    try:
        test = TESTS[int(params.get("id", -1))]
    except (ValueError, IndexError):
        notify("Prueba desconocida", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    needs = test.get("needs")
    if needs and not has_addon(needs):
        notify("Falta el add-on: {0}".format(needs), xbmcgui.NOTIFICATION_WARNING)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    method = test["method"]
    url = test.get("url", "")
    log("play: {0} | metodo={1} | url={2}".format(test["title"], method, url))

    if method == "browse_local":
        url = xbmcgui.Dialog().browseSingle(1, "Elige un video", "video")
    elif method == "network":
        url = xbmcgui.Dialog().input("Ruta del video (smb://, nfs://, http://...)",
                                     defaultt=NET_EXAMPLE)
    if method == "network" and url == NET_EXAMPLE:
        notify("Escribe la ruta real de tu servidor (el ejemplo no existe)", xbmcgui.NOTIFICATION_WARNING)
        url = ""
    if not url:
        log("play: sin URL (cancelado o ruta de ejemplo)")
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return

    item = xbmcgui.ListItem(label=test["title"], path=url)
    set_title(item, test["title"], test.get("info", ""))

    if method in ("resolve", "browse_local", "network"):
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    elif method == "subtitles":
        srt = "special://temp/micentro_test.srt"
        subs = ("1\n00:00:01,000 --> 00:00:05,000\nSubtítulo de prueba 1: ¡funciona!\n\n"
                "2\n00:00:06,000 --> 00:00:10,000\nSubtítulo de prueba 2: Mi Centro\n\n"
                "3\n00:00:11,000 --> 00:00:15,000\nSubtítulo de prueba 3: fin de la prueba\n")
        handle = xbmcvfs.File(srt, "w")
        handle.write(subs)
        handle.close()
        item.setSubtitles([srt])
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    elif method == "headers":
        headers = urlencode({"User-Agent": "Mozilla/5.0 (Kodi MiCentro)",
                             "Referer": "https://example.com/"}, quote_via=quote)
        item.setPath(url + "|" + headers)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    elif method in ("adaptive_hls", "adaptive_mpd"):
        manifest = "hls" if method == "adaptive_hls" else "mpd"
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", manifest)
        item.setMimeType("application/x-mpegURL" if manifest == "hls"
                         else "application/dash+xml")
        item.setContentLookup(False)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    elif method == "player":
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        xbmc.Player().play(url, item)

    elif method == "builtin":
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        xbmc.executebuiltin("PlayMedia({0})".format(url))


def play(params):
    try:
        _play(params)
    except Exception as error:  # noqa: BLE001
        log("ERROR en play: {0}\n{1}".format(error, traceback.format_exc()), xbmc.LOGERROR)
        notify("Error al preparar la reproducción: {0}".format(error), xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())


# ---------------------------------------------------------------------------
# Listas M3U (TV en directo)
# ---------------------------------------------------------------------------
def parse_m3u(text):
    entries, name, logo = [], None, ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            name = line.split(",", 1)[1].strip() if "," in line else "Sin nombre"
            match = re.search(r'tvg-logo="([^"]*)"', line)
            logo = match.group(1) if match else ""
        elif line and not line.startswith("#"):
            entries.append({"name": name or line, "url": line, "logo": logo})
            name, logo = None, ""
    return entries


def load_text(source):
    if source.startswith("http"):
        request = Request(source, headers={"User-Agent": "Mozilla/5.0 (Kodi MiCentro)"})
        return urlopen(request, timeout=15).read().decode("utf-8", "replace")
    handle = xbmcvfs.File(source)
    data = handle.read()
    handle.close()
    return data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else data


def list_m3u(source):
    xbmcplugin.setPluginCategory(HANDLE, "Lista M3U")
    xbmcplugin.setContent(HANDLE, "videos")
    try:
        entries = parse_m3u(SAMPLE_M3U if source == "sample" else load_text(source))
    except Exception as error:  # noqa: BLE001
        notify("No se pudo leer la lista: {0}".format(error), xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    if not entries:
        notify("La lista no contiene canales", xbmcgui.NOTIFICATION_WARNING)
    for entry in entries:
        add_playable(entry["name"], art=entry["logo"], action="play_url", url=entry["url"])
    xbmcplugin.endOfDirectory(HANDLE)


def m3u_menu(params):
    list_m3u("sample")


def m3u_ask(params):
    source = xbmcgui.Dialog().input("URL o ruta de la lista M3U", defaultt="http://")
    if not source or source == "http://":
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    list_m3u(source)


def play_url(params):
    url = params.get("url", "")
    log("play_url: {0}".format(url))
    if not url:
        xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
        return
    xbmcplugin.setResolvedUrl(HANDLE, True, xbmcgui.ListItem(path=url))


# ---------------------------------------------------------------------------
# Diagnostico: comprueba que cada URL responde (sin reproducir)
# ---------------------------------------------------------------------------
def check_url(url, timeout=10):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (Kodi MiCentro)",
                                    "Range": "bytes=0-1"})
    start = time.time()
    try:
        response = urlopen(request, timeout=timeout)
        code = response.getcode()
        response.close()
        return True, "OK (HTTP {0}, {1} ms)".format(code, int((time.time() - start) * 1000))
    except Exception as error:  # noqa: BLE001
        log("check_url FALLO {0}: {1}".format(url, error))
        return False, "ERROR: {0}".format(error)


def check_all(params):
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    progress = xbmcgui.DialogProgress()
    progress.create(ADDON_NAME, "Comprobando enlaces...")
    lines, ok_count, total = [], 0, 0
    targets = list(TESTS) + [{"title": "M3U: " + e["name"], "url": e["url"]}
                             for e in parse_m3u(SAMPLE_M3U)]
    for index, test in enumerate(targets):
        if progress.iscanceled():
            break
        progress.update(int(index * 100 / len(targets)), test["title"])
        needs = test.get("needs")
        if needs and not has_addon(needs):
            lines.append("[AVISO] {0}\n    Falta el add-on: {1}\n".format(test["title"], needs))
            continue
        if not test.get("url", "").startswith("http"):
            lines.append("[SALTADO] {0}\n    Depende de tu dispositivo o de Kodi, se prueba reproduciendo.\n"
                         .format(test["title"]))
            continue
        total += 1
        ok, message = check_url(test["url"])
        ok_count += ok
        lines.append("[{0}] {1}\n    {2}\n".format("OK" if ok else "FALLO", test["title"], message))
    progress.close()
    lines.append("Resultado: {0} de {1} enlaces responden.".format(ok_count, total))
    xbmcgui.Dialog().textviewer("Diagnóstico de enlaces", "\n".join(lines))


ROUTES = {
    None: main_menu,
    "movies": movies_menu,
    "series": series_menu,
    "test": test_menu,
    "play": play,
    "check_all": check_all,
    "m3u": m3u_menu,
    "m3u_ask": m3u_ask,
    "play_url": play_url,
}


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    log("ruta: {0}".format(params))
    ROUTES.get(params.get("action"), main_menu)(params)


if __name__ == "__main__":
    router(sys.argv[2][1:])
