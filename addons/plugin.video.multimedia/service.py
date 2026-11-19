# -*- coding: utf-8 -*-
"""Servicio de fondo: mantiene en marcha el proxy local de Drive mientras Kodi está abierto."""
import threading

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib import driveproxy

PROPERTY = "multimedia.drive_proxy_port"


def main():
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(10000)
    addon = xbmcaddon.Addon()  # se crea aquí, en el hilo del servicio, y no en los hilos del proxy
    try:
        server = driveproxy.make_server(
            lambda: addon.getSetting("drive_api_key"),
            log=lambda msg: xbmc.log("[multimedia] Proxy Drive: {}".format(msg), xbmc.LOGINFO))
    except OSError as exc:
        xbmc.log("[multimedia] No se pudo iniciar el proxy de Drive: {}".format(exc), xbmc.LOGERROR)
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()
    home.setProperty(PROPERTY, str(server.server_address[1]))
    xbmc.log("[multimedia] Proxy de Drive en 127.0.0.1:{}".format(server.server_address[1]), xbmc.LOGINFO)
    while not monitor.abortRequested():
        if monitor.waitForAbort(2):
            break
    home.clearProperty(PROPERTY)
    server.shutdown()
    server.server_close()


if __name__ == "__main__":
    main()
