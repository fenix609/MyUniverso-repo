# -*- coding: utf-8 -*-
"""
ESTRUCTURA DE MENÚS DE "mi addon"
=================================
Tipos de nodo:

  Carpeta (submenú):
    {"id": "accion", "label": "Acción", "children": [ ... ]}

  Vídeo / stream:
    {"id": "x", "label": "Nombre", "url": "...", "plot": "...", "icon": "..."}
    "url" puede ser:
      - http(s) mp4/mkv/ts ...        reproducción directa
      - .m3u8                         HLS (inputstream.adaptive)
      - .mpd                          DASH (inputstream.adaptive)
      - rtmp://...                    inputstream.rtmp
      - magnet:?xt=...  o .torrent    se envía a Elementum o Torrest
      - plugin://...                  se pasa tal cual a otro addon (YouTube, etc.)
    Opciones extra (todas opcionales):
      "live": True                    canal en directo (usa ffmpegdirect si hace falta)
      "headers": "User-Agent=X&Referer=Y"
      "license_type": "com.widevine.alpha", "license_key": "https://lic|headers|R{SSM}|"

  YouTube (requiere el addon oficial de YouTube; admite ID o URL completa):
    {"id": "v1", "label": "Vídeo",    "youtube_video":    "aqz-KE-bpKQ"}
    {"id": "p1", "label": "Lista",    "youtube_playlist": "PLxxxxxxxx"}   # carpeta con la lista
    {"id": "c1", "label": "Canal",    "youtube_channel":  "UCxxxxxxxx"}   # ID del canal (empieza por UC)
    {"id": "s1", "label": "Búsqueda", "youtube_search":   "recetas fáciles"}
    Además, cualquier "url" de youtube.com / youtu.be se reproduce con ese addon.

  Lista M3U (canales IPTV, se agrupan por group-title):
    {"id": "tv", "label": "Mis canales", "m3u": "https://.../lista.m3u"}
    (también vale una ruta local, p. ej. "special://home/userdata/lista.m3u")

Reglas: "id" único dentro de su carpeta y sin "/".
"""

MENU = [
    {
        "id": "peliculas",
        "label": "Películas",
        "icon": "DefaultMovies.png",
        "children": [
            {
                "id": "ejemplo",
                "label": "Ejemplo: Big Buck Bunny",
                "url": "https://download.blender.org/peach/bigbuckbunny_movies/BigBuckBunny_320x180.mp4",
                "plot": "Vídeo de prueba de la Blender Foundation (licencia CC).",
            },
            {
                "id": "ejemplo_youtube",
                "label": "Ejemplo YouTube: Big Buck Bunny",
                "youtube_video": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
                "plot": "Canal oficial de Blender en YouTube.",
            },
            {
                "id": "ejemplo_torrent",
                "label": "Ejemplo torrent: Sintel (requiere Elementum/Torrest)",
                "url": "magnet:?xt=urn:btih:08ada5a7a6183aae1e09d831df6748d566095a10&dn=Sintel",
                "plot": "Película libre de la Blender Foundation.",
            },
        ],
    },
    {"id": "series", "label": "Series", "icon": "DefaultTVShows.png", "children": []},
    {"id": "deportes", "label": "Deportes", "icon": "DefaultAddonGame.png", "children": []},
    {
        "id": "television",
        "label": "Televisión",
        "icon": "DefaultAddonPVRClient.png",
        "children": [
            # {"id": "lista1", "label": "Mi lista M3U", "m3u": "https://.../lista.m3u"},
        ],
    },
    {
        "id": "cocina",
        "label": "Cocina",
        "icon": "DefaultAddonLookAndFeel.png",
        "children": [
            {"id": "buscar", "label": "Buscar recetas en YouTube", "youtube_search": "recetas de cocina fáciles"},
        ],
    },
    {"id": "varios", "label": "Varios", "icon": "DefaultFolder.png", "children": []},
]
