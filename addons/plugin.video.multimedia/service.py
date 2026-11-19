# -*- coding: utf-8 -*-
"""Servicio de fondo: mantiene en marcha los proxies locales de Drive y de Mega mientras Kodi está abierto."""
import threading

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import driveproxy

try:
    from resources.lib import megaproxy  # necesita script.module.pycryptodome
except ImportError as _exc:
    megaproxy = None
    _MEGA_ERROR = str(_exc)

DRIVE_PROPERTY = "multimedia.drive_proxy_port"
MEGA_PROPERTY = "multimedia.mega_proxy_port"


def _log(msg, error=False):
    xbmc.log("[multimedia] {}".format(msg), xbmc.LOGERROR if error else xbmc.LOGINFO)


def main():
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(10000)
    addon = xbmcaddon.Addon()  # se crea aquí, en el hilo del servicio, y no en los hilos de los proxies
    running = []  # (servidor, propiedad)

    try:
        server = driveproxy.make_server(
            lambda: addon.getSetting("drive_api_key"),
            log=lambda msg: _log("Proxy Drive: {}".format(msg)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        home.setProperty(DRIVE_PROPERTY, str(server.server_address[1]))
        running.append((server, DRIVE_PROPERTY))
        _log("Proxy de Drive en 127.0.0.1:{}".format(server.server_address[1]))
    except OSError as exc:
        _log("No se pudo iniciar el proxy de Drive: {}".format(exc), error=True)

    if megaproxy is None:
        _log("Mega desactivado: {}".format(_MEGA_ERROR), error=True)
    else:
        try:
            server = megaproxy.make_server(log=lambda msg: _log("Proxy Mega: {}".format(msg)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            home.setProperty(MEGA_PROPERTY, str(server.server_address[1]))
            running.append((server, MEGA_PROPERTY))
            _log("Proxy de Mega en 127.0.0.1:{}".format(server.server_address[1]))
        except OSError as exc:
            _log("No se pudo iniciar el proxy de Mega: {}".format(exc), error=True)

    if not running:
        return
    while not monitor.abortRequested():
        if monitor.waitForAbort(2):
            break
    for server, prop in running:
        home.clearProperty(prop)
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
