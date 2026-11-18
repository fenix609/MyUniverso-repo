# -*- coding: utf-8 -*-
"""Prueba automática: reproduce cada vídeo; si falla, prueba alternativas y busca uno nuevo."""
import xbmc
import xbmcgui

from . import catalog, media, menu, player, probe, utils

PLAY_TIMEOUT = 20
TORRENT_TIMEOUT = 90  # los torrents tardan en conectar y llenar el búfer


class _ProbePlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)
        self.started = False
        self.error = False

    def onAVStarted(self):
        self.started = True

    def onPlayBackError(self):
        self.error = True


def play_ok(url, title, timeout=PLAY_TIMEOUT):
    """Reproduce en ventana y espera a que arranque el vídeo (o falle)."""
    pl = _ProbePlayer()
    monitor = xbmc.Monitor()
    pl.play(url, player.build_listitem(url, title, "video"), True)
    waited = 0.0
    while waited < timeout and not pl.started and not pl.error and not monitor.abortRequested():
        monitor.waitForAbort(0.5)
        waited += 0.5
    ok = pl.started and not pl.error
    if pl.isPlaying():
        pl.stop()
    monitor.waitForAbort(1)
    return ok


def is_torrent(url):
    return media.item_kind({"url": url})[0] == "torrent"


def works(url, title):
    if url.startswith("http") and not probe.http_ok(url):
        return False
    if is_torrent(url):
        target = player.torrent_url(url)
        return bool(target) and play_ok(target, title, TORRENT_TIMEOUT)
    return play_ok(url, title)


def _unique(urls):
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def test_item(item, cache):
    """Devuelve (estado, url): OK | ALT | NUEVO | FALLA | OMITIDO."""
    title = item["title"]
    if is_torrent(item["url"]) and not player.torrent_url("magnet:?"):
        return "OMITIDO", None  # no hay addon de torrents: no se puede probar
    candidates = _unique([cache["overrides"].get(title), item["url"]] + item.get("alts", []))
    for url in candidates:
        if works(url, title):
            return ("OK" if url == item["url"] else "ALT"), url
    try:
        found = probe.find_candidates(probe.ext_of(item["url"]), catalog.fetch_text)
    except Exception as exc:
        utils.log("Búsqueda de sustituto fallida: {}".format(exc))
        found = []
    for url in _unique(found):
        if url not in candidates and works(url, title):
            return "NUEVO", url
    return "FALLA", None


def run(file):
    data = menu.parse_list(catalog.load_code_text(file))
    items = [it for grp in data["groups"] for it in grp["items"]]
    if not items:
        utils.notify("No hay vídeos que probar", error=True)
        return
    folder = utils.profile_dir()
    cache = probe.load_cache(folder)
    dlg = xbmcgui.DialogProgress()
    dlg.create("Prueba automática", "")
    lines, good, skipped = [], 0, 0
    for i, item in enumerate(items):
        if dlg.iscanceled():
            break
        dlg.update(int(i * 100 / len(items)), "{} ({}/{})".format(item["title"], i + 1, len(items)))
        status, url = test_item(item, cache)
        title = item["title"]
        cache["last"][title] = status
        if status == "OK":
            cache["overrides"].pop(title, None)
            lines.append("[OK] {}: funciona".format(title))
        elif status in ("ALT", "NUEVO"):
            cache["overrides"][title] = url
            label = "enlace alternativo" if status == "ALT" else "enlace nuevo encontrado"
            lines.append("[{}] {}: {}\n      {}".format(status, title, label, url))
        elif status == "OMITIDO":
            skipped += 1
            lines.append("[OMITIDO] {}: instala Elementum, Torrest o Quasar para probarlo".format(title))
        else:
            lines.append("[FALLA] {}: no funciona y no se encontró sustituto".format(title))
        if status in ("OK", "ALT", "NUEVO"):
            good += 1
    dlg.close()
    probe.save_cache(folder, cache)
    header = "{} de {} funcionan".format(good, len(items))
    if skipped:
        header += " ({} sin probar)".format(skipped)
    xbmcgui.Dialog().textviewer("Prueba automática", header + "\n\n" + "\n".join(lines))
    xbmc.executebuiltin("Container.Refresh")
