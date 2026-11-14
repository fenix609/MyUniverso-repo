# -*- coding: utf-8 -*-
"""Mi Centro - add-on base para Kodi 19+ (Python 3).

Menu:  Peliculas / Series  ->  Probar add-on  ->  pruebas de reproduccion.
Para anadir secciones, crea una funcion y registrala en ROUTES.
"""
import json
import re
import sys
import threading
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

# Fuentes de la TDT de Espana (se prueban por orden). TDTChannels se actualiza solo y
# se basa en las senales oficiales de cada cadena; iptv-org es la copia de respaldo.
TDT_SOURCES = [
    "https://www.tdtchannels.com/lists/tv.m3u8",
    "https://iptv-org.github.io/iptv/countries/es.m3u",
]
TDT_CACHE = "special://temp/micentro_tdt_cache.json"
TDT_RESULTS = "special://temp/micentro_tdt_results.json"
TDT_CACHE_HOURS = 6
CHECK_THREADS = 8
CHECK_TIMEOUT = 8

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
    add_folder("TV en directo", action="tv")
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


def tv_menu(params):
    xbmcplugin.setPluginCategory(HANDLE, "TV en directo")
    xbmcplugin.setContent(HANDLE, "videos")
    add_folder("TDT (canales de España)", action="tdt")
    add_folder("Lista M3U de ejemplo", action="m3u")
    add_folder("Abrir mi propia lista M3U (URL o archivo)", action="m3u_ask")
    add_folder("Probar add-on", action="test", section="TV en directo")
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
HEADER_OPTS = {"http-user-agent": "User-Agent", "http-referrer": "Referer",
               "http-referer": "Referer", "http-origin": "Origin"}


def parse_m3u(text):
    """Devuelve [{name, url, logo, group, headers}]; entiende #EXTINF y #EXTVLCOPT."""
    entries, meta = [], None

    def new_meta():
        return {"name": None, "logo": "", "group": "", "headers": {}}

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            meta = new_meta()
            meta["name"] = line.split(",", 1)[1].strip() if "," in line else "Sin nombre"
            logo = re.search(r'tvg-logo="([^"]*)"', line)
            group = re.search(r'group-title="([^"]*)"', line)
            meta["logo"] = logo.group(1) if logo else ""
            meta["group"] = group.group(1).strip() if group else ""
        elif line.upper().startswith("#EXTVLCOPT:"):
            if meta is None:
                meta = new_meta()
            key, _, value = line.split(":", 1)[1].partition("=")
            header = HEADER_OPTS.get(key.strip().lower())
            if header and value.strip():
                meta["headers"][header] = value.strip()
        elif line and not line.startswith("#"):
            meta = meta or new_meta()
            entries.append({"name": meta["name"] or line, "url": line, "logo": meta["logo"],
                            "group": meta["group"], "headers": meta["headers"]})
            meta = None
    return entries


def with_headers(url, headers):
    """Anade cabeceras HTTP al enlace con el formato de Kodi: url|Cabecera=valor&..."""
    if not headers:
        return url
    return url + "|" + urlencode(headers, quote_via=quote)


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
        add_playable(entry["name"], art=entry["logo"], action="play_url",
                     url=with_headers(entry["url"], entry["headers"]))
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
# TDT de Espana
# ---------------------------------------------------------------------------
def read_text(path):
    handle = xbmcvfs.File(path)
    data = handle.read()
    handle.close()
    return data.decode("utf-8", "replace") if isinstance(data, (bytes, bytearray)) else data


def write_text(path, text):
    handle = xbmcvfs.File(path, "w")
    handle.write(text)
    handle.close()


def read_json(path):
    try:
        data = json.loads(read_text(path))
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def write_json(path, data):
    try:
        write_text(path, json.dumps(data))
    except Exception as error:  # noqa: BLE001
        log("No se pudo guardar {0}: {1}".format(path, error))


def get_tdt_entries(refresh=False):
    """Descarga (o lee de la cache) la lista de la TDT y devuelve solo enlaces http(s)."""
    cache = read_json(TDT_CACHE)
    now = time.time()
    text = None
    if cache and not refresh and now - cache.get("time", 0) < TDT_CACHE_HOURS * 3600:
        text = cache.get("text")
    if not text:
        for source in TDT_SOURCES:
            try:
                candidate = load_text(source)
                if "#EXTINF" in candidate:
                    text = candidate
                    log("TDT: lista descargada de {0}".format(source))
                    write_json(TDT_CACHE, {"time": now, "source": source, "text": text})
                    break
                log("TDT: {0} no devolvio una lista M3U valida".format(source))
            except Exception as error:  # noqa: BLE001
                log("TDT: fallo al descargar {0}: {1}".format(source, error))
        if not text and cache and cache.get("text"):
            text = cache["text"]
            notify("Sin conexión con la lista: usando la última copia guardada",
                   xbmcgui.NOTIFICATION_WARNING)
    if not text:
        notify("No se pudo descargar la lista de la TDT", xbmcgui.NOTIFICATION_ERROR)
        return []
    entries = [e for e in parse_m3u(text) if e["url"].lower().startswith(("http://", "https://"))]
    for entry in entries:
        entry["group"] = entry["group"] or "Otros"
    return entries


def load_results():
    data = read_json(TDT_RESULTS)
    return data.get("results", {}) if data else {}


def check_stream(url, headers=None, timeout=CHECK_TIMEOUT):
    """Comprueba que el enlace responde y, si es .m3u8, que devuelve una lista HLS valida."""
    import ssl
    request_headers = {"User-Agent": "Mozilla/5.0 (Kodi MiCentro)", "Range": "bytes=0-2047"}
    request_headers.update(headers or {})
    last_error = None
    for context in (None, ssl._create_unverified_context()):
        try:
            response = urlopen(Request(url, headers=request_headers), timeout=timeout, context=context)
            code = response.getcode()
            body = response.read(2048)
            kind = (response.headers.get("Content-Type") or "").lower()
            response.close()
            if code not in (200, 206):
                return False, "HTTP {0}".format(code)
            if (".m3u8" in url.lower() or "mpegurl" in kind) and b"#EXTM3U" not in body:
                return False, "no devuelve una lista HLS válida"
            return True, "OK"
        except ssl.SSLError as error:
            last_error = error
            continue
        except Exception as error:  # noqa: BLE001
            reason = getattr(error, "reason", None) or error
            if "CERTIFICATE" in str(reason).upper():
                last_error = error
                continue
            return False, str(reason)[:80]
    return False, str(last_error)[:80]


def run_checks(entries, progress=None):
    """Comprueba varios canales a la vez. Devuelve {url: {ok, msg}}."""
    pending, results, lock, stop = list(entries), {}, threading.Lock(), threading.Event()

    def worker():
        while not stop.is_set():
            with lock:
                if not pending:
                    return
                entry = pending.pop()
            ok, message = check_stream(entry["url"], entry["headers"])
            with lock:
                results[entry["url"]] = {"ok": ok, "msg": message}

    threads = [threading.Thread(target=worker) for _ in range(CHECK_THREADS)]
    for thread in threads:
        thread.daemon = True
        thread.start()
    total = max(len(entries), 1)
    while any(thread.is_alive() for thread in threads):
        time.sleep(0.2)
        if progress is not None:
            with lock:
                done = len(results)
            progress.update(int(done * 100 / total), "Canales comprobados: {0} de {1}".format(done, total))
            if progress.iscanceled():
                stop.set()
                break
    return results


def tdt_menu(params):
    xbmcplugin.setPluginCategory(HANDLE, "TDT")
    xbmcplugin.setContent(HANDLE, "videos")
    entries = get_tdt_entries(refresh=params.get("refresh") == "1")
    if not entries:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    results = load_results()
    working = sum(1 for e in entries if results.get(e["url"], {}).get("ok"))
    add_folder("Todos los canales ({0})".format(len(entries)), action="tdt_list", group="")
    counts = {}
    for entry in entries:
        counts[entry["group"]] = counts.get(entry["group"], 0) + 1
    for group in sorted(counts, key=lambda g: (g == "Otros", g.lower())):
        add_folder("{0} ({1})".format(group, counts[group]), action="tdt_list", group=group)
    if results:
        add_folder("Solo canales que funcionan ({0})".format(working), action="tdt_list",
                   group="", only_ok="1")
    add_action("» Comprobar todos los canales", action="tdt_check")
    add_folder("» Actualizar la lista de canales", action="tdt", refresh="1")
    xbmcplugin.endOfDirectory(HANDLE)


def tdt_list(params):
    group = params.get("group", "")
    only_ok = params.get("only_ok") == "1"
    xbmcplugin.setPluginCategory(HANDLE, group or "TDT")
    xbmcplugin.setContent(HANDLE, "videos")
    results = load_results()
    for entry in get_tdt_entries():
        if group and entry["group"] != group:
            continue
        status = results.get(entry["url"])
        if only_ok and not (status and status["ok"]):
            continue
        label = entry["name"]
        if status:
            label = ("[COLOR lime][OK][/COLOR] " if status["ok"] else "[COLOR red][X][/COLOR] ") + label
        add_playable(label, status["msg"] if status else "", art=entry["logo"],
                     action="play_url", url=with_headers(entry["url"], entry["headers"]))
    xbmcplugin.endOfDirectory(HANDLE)


def tdt_check(params):
    xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    entries = get_tdt_entries()
    if not entries:
        return
    progress = xbmcgui.DialogProgress()
    progress.create("Comprobando canales de la TDT", "Preparando...")
    log("TDT: comprobando {0} canales".format(len(entries)))
    results = run_checks(entries, progress)
    progress.close()
    write_json(TDT_RESULTS, {"time": time.time(), "results": results})

    names = {e["url"]: e["name"] for e in entries}
    good = [names[u] for u, r in results.items() if r["ok"]]
    bad = ["{0}: {1}".format(names[u], r["msg"]) for u, r in results.items() if not r["ok"]]
    skipped = len(entries) - len(results)
    lines = ["Canales que responden: {0} de {1}".format(len(good), len(entries))]
    if skipped:
        lines.append("Sin comprobar (cancelado): {0}".format(skipped))
    lines.append("")
    lines.append("--- NO RESPONDEN ({0}) ---".format(len(bad)))
    lines.extend(sorted(bad))
    lines.append("")
    lines.append("Nota: que un canal responda no garantiza que se vea bien, y algunos")
    lines.append("pueden fallar a ratos o solo funcionar en España.")
    log("TDT: {0} OK, {1} fallan".format(len(good), len(bad)))
    xbmcgui.Dialog().textviewer("Resultado: canales de la TDT", "\n".join(lines))
    xbmc.executebuiltin("Container.Refresh")


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
    "tv": tv_menu,
    "tdt": tdt_menu,
    "tdt_list": tdt_list,
    "tdt_check": tdt_check,
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
