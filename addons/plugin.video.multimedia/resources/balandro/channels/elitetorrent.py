# -*- coding: utf-8 -*-

import sys

PY3 = False
if sys.version_info[0] >= 3: PY3 = True


import os, base64

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, tmdb

from lib import decrypters


host = 'https://www.elitetorrent.com/'


# ~ por si viene de enlaces guardados
ant_hosts = ['https://elitetorrent.app/', 'https://elitetorrent.la/', 'https://www.elitetorrent.wtf/',
             'https://www.elitetorrent.dev/']


domain = config.get_setting('dominio', 'elitetorrent', default='')

if domain:
    if domain == host: config.set_setting('dominio', '', 'elitetorrent')
    elif domain in str(ant_hosts): config.set_setting('dominio', '', 'elitetorrent')
    else: host = domain


def item_configurar_proxies(item):
    color_list_proxies = config.get_setting('channels_list_proxies_color', default='red')

    color_avis = config.get_setting('notification_avis_color', default='yellow')
    color_exec = config.get_setting('notification_exec_color', default='cyan')

    context = []

    tit = '[COLOR %s]Información proxies[/COLOR]' % color_avis
    context.append({'title': tit, 'channel': 'helper', 'action': 'show_help_proxies'})

    if config.get_setting('channel_elitetorrent_proxies', default=''):
        tit = '[COLOR %s][B]Quitar los proxies del canal[/B][/COLOR]' % color_list_proxies
        context.append({'title': tit, 'channel': item.channel, 'action': 'quitar_proxies'})

    tit = '[COLOR %s]Ajustes categoría proxies[/COLOR]' % color_exec
    context.append({'title': tit, 'channel': 'actions', 'action': 'open_settings'})

    plot = 'Es posible que para poder utilizar este canal necesites configurar algún proxy, ya que no es accesible desde algunos países/operadoras.'
    plot += '[CR]Si desde un navegador web no te funciona el sitio ' + host + ' necesitarás un proxy.'
    return item.clone( title = '[B]Configurar proxies a usar ...[/B]', action = 'configurar_proxies', folder=False, context=context, plot=plot, text_color='red' )

def quitar_proxies(item):
    from modules import submnuctext
    submnuctext._quitar_proxies(item)
    return True

def configurar_proxies(item):
    from core import proxytools
    return proxytools.configurar_proxies_canal(item.channel, host)


def do_downloadpage(url, post=None, headers=None):
    # ~ por si viene de enlaces guardados
    for ant in ant_hosts:
        url = url.replace(ant, host)

    raise_weberror = True
    if '/estreno/' in url: raise_weberror = False
    
    hay_proxies = False
    if config.get_setting('channel_eliteorrent_proxies', default=''): hay_proxies = True

    if not url.startswith(host):
        data = httptools.downloadpage(url, post=post, headers=headers, raise_weberror=raise_weberror).data
    else:
        if hay_proxies:
            data = httptools.downloadpage_proxy('elitetorrent', url, post=post, headers=headers, raise_weberror=raise_weberror).data
        else:
            data = httptools.downloadpage(url, post=post, headers=headers, raise_weberror=raise_weberror).data

        if not data:
            if not '/?s=' in url:
                if config.get_setting('channels_re_charges', default=True): platformtools.dialog_notification('EliteTorrent', '[COLOR cyan]Re-Intentando acceso[/COLOR]')

                timeout = config.get_setting('channels_repeat', default=30)

                if hay_proxies:
                    data = httptools.downloadpage_proxy('elitetorrent', url, post=post, headers=headers, raise_weberror=raise_weberror, timeout=timeout).data
                else:
                    data = httptools.downloadpage(url, post=post, headers=headers, raise_weberror=raise_weberror).data

    return data


def acciones(item):
    logger.info()
    itemlist = []

    domain_memo = config.get_setting('dominio', 'elitetorrent', default='')

    if domain_memo: url = domain_memo
    else: url = host

    itemlist.append(item.clone( channel='actions', action='show_latest_domains', title='[COLOR moccasin][B]Últimos Cambios de Dominios[/B][/COLOR]', thumbnail=config.get_thumb('pencil') ))

    itemlist.append(item.clone( channel='helper', action='show_help_domains', title='[B]Información Dominios[/B]', thumbnail=config.get_thumb('help'), text_color='green' ))

    itemlist.append(item.clone( channel='domains', action='test_domain_elitetorrent', title='Test Web del canal [COLOR yellow][B] ' + url + '[/B][/COLOR]',
                                from_channel='elitetorrent', folder=False, text_color='chartreuse' ))

    if domain_memo: title = '[B]Modificar/Eliminar el dominio memorizado[/B]'
    else: title = '[B]Informar Nuevo Dominio manualmente[/B]'

    itemlist.append(item.clone( channel='domains', action='manto_domain_elitetorrent', title=title, desde_el_canal = True, folder=False, text_color='darkorange' ))

    itemlist.append(item_configurar_proxies(item))

    itemlist.append(item.clone( channel='actions', action='show_old_domains', title='[COLOR coral][B]Historial Dominios[/B][/COLOR]', channel_id = 'elitetorrent' ))

    platformtools.itemlist_refresh()

    return itemlist


def mainlist(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar ...', action = 'search', search_type = 'all', text_color = 'yellow' ))

    itemlist.append(item.clone( title = 'Películas', action = 'mainlist_pelis', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Series', action = 'mainlist_series', text_color = 'hotpink' ))

    return itemlist


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'peliculas-16-1/', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Últimas', action = 'list_all', url = host + 'estrenos-23/', search_type = 'movie', text_color='cyan' ))

    itemlist.append(item.clone( title = 'Por idioma', action = 'idiomas', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por calidad', action = 'calidades',  search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow', text_color = 'hotpink' ))

    itemlist.append(item.clone( title = 'Catálogo episodios', action = 'list_all', url = host + 'series-20-1/', search_type = 'tvshow' ))

    return itemlist


def idiomas(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Castellano', action = 'list_all', url = host + 'idioma/castellano-17-1/', text_color='deepskyblue' ))
    itemlist.append(item.clone( title = 'Latino', action = 'list_all', url = host + 'idioma/espanol-latino-11-1/', text_color='deepskyblue' ))
    itemlist.append(item.clone( title = 'Inglés', action = 'list_all', url = host + 'idioma/ingles/', text_color='deepskyblue' ))
    itemlist.append(item.clone( title = 'Subtitulado', action = 'list_all', url = host + 'idioma/vose-3-1/', text_color='deepskyblue' ))

    return itemlist


def calidades(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'En 720', action = 'list_all', url = host + 'calidad/720p-2/', text_color='moccasin' ))
    itemlist.append(item.clone( title = 'En 1080', action = 'list_all', url = host + 'calidad/1080p-10-1/', text_color='moccasin' ))
    itemlist.append(item.clone( title = 'En DVD Rip', action = 'list_all', url = host + 'calidad/dvdrip-1/', text_color='moccasin' ))
    itemlist.append(item.clone( title = 'En HD Rip', action = 'list_all', url = host + 'calidad/hdrip-1/', text_color='moccasin' ))
    itemlist.append(item.clone( title = 'En Micro HD', action = 'list_all', url = host + 'peliculas-microhd-9/', text_color='moccasin' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host)

    bloque = scrapertools.find_single_match(data, '<ul id="cab-categorias">(.*?)</ul>')
    if not bloque: bloque = scrapertools.find_single_match(data, '<ul id=cab-categorias>(.*?)</ul>')

    matches = scrapertools.find_multiple_matches(bloque, 'href="(.*?)".*?title=.*?">(.*?)</a>')

    for url, title in matches:
        title = title.replace('&amp;', '&')

        if '/animacion-2' in url: title = title + '-2'

        itemlist.append(item.clone( action='list_all', title=title, url=url, text_color = 'deepskyblue' ))

    return sorted(itemlist,key=lambda x: x.title)


def anios(item):
    logger.info()
    itemlist = []

    from datetime import datetime
    current_year = int(datetime.today().year)

    for x in range(current_year, 1959, -1):
        itemlist.append(item.clone( title=str(x), url=host + 'estreno/' + str(x) + '/', action='list_all', any = str(x), text_color = 'deepskyblue' ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    if '/?s=' in item.url:
        if '<h1>No se han encontrado resultados para' in data: return itemlist

    matches = scrapertools.find_multiple_matches(data, '<div class="imagen">(.*?)<div class="meta">')
    if not matches: matches = scrapertools.find_multiple_matches(data, '<div class=imagen>(.*?)<div class=meta>')

    i = 0

    for match in matches:
        url = scrapertools.find_single_match(match, '<a href="(.*?)"')

        title = scrapertools.find_single_match(match, 'title="(.*?)"')

        if title == 'Peso de pelicula':
            title = scrapertools.find_single_match(match, "title=(.*?)alt=").strip()

        if not url or not title: continue

        title = title.replace('(720)', '').replace('(720p)', '').replace('(1080)', '').replace('(1080p)', '').replace('(microHD)', '').replace('(BR-Line)', '').strip()
        title = title.replace('(HDR)', '').replace('(HDRip)', '').replace('(DVDRip)', '').replace('(BR-SCREENER)', '').replace('(TS-SCREENER)', '').strip()

        title = title.replace('&#8217;', "'")

        thumb = scrapertools.find_single_match(match, 'data-src="(.*?)"')

        qlty = scrapertools.find_single_match(match, 'style=.*?<i>(.*?)</i>')
        if qlty == '---': qlty = ''

        lngs = []
        langs = scrapertools.find_multiple_matches(match, "data-src='.*?/images/(.*?).png'")

        for lang in langs:
            lng = ''

            if lang == 'espanol': lng = 'Esp'
            if lang == 'latino': lng = 'Lat'
            if lang == 'vose': lng = 'Vose'
            if lang == 'ingles': lng = 'Voi'

            if lng:
               if not lng in str(lngs):
                   if lng == 'Voi': lng = 'Vo'
                   lngs.append(lng)

        year = '-'
        if '/estreno/' in item.url: year = scrapertools.find_single_match(item.url, "/estreno/(.*?)/")

        tipo = 'movie' if '/peliculas/' in url else 'tvshow'
        sufijo = '' if item.search_type != 'all' else tipo

        title = title.replace('&#8211;', '').replace('&amp;', '').replace('&#8215;', ' ').replace('&#215;', 'x')

        if tipo == 'movie':
            if not item.search_type == 'all':
                if item.search_type == 'tvshow': continue

            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb,
                                        qualities=qlty, languages = ', '.join(lngs), fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels={'year': year} ))

        if tipo == 'tvshow':
            if not item.search_type == 'all':
                if item.search_type == 'movie': continue

            SerieName = url

            SerieName = SerieName.replace(host, '').replace('series/', '').strip()
            SerieName = SerieName.replace('-', ' ')

            if ' s0' in SerieName: SerieName = SerieName.split(" s0")[0]
            elif ' t0' in SerieName: SerieName = SerieName.split(" t0")[0]
            elif ' 1x' in SerieName: SerieName = SerieName.split(" 1x")[0]
            elif ' 2x' in SerieName: SerieName = SerieName.split(" 2x")[0]
            elif ' 3x' in SerieName: SerieName = SerieName.split(" 3x")[0]
            elif ' 4x' in SerieName: SerieName = SerieName.split(" 4x")[0]
            elif ' 5x' in SerieName: SerieName = SerieName.split(" 4x")[0]
            elif ' 01x' in SerieName: SerieName = SerieName.split(" 01x")[0]
            elif ' 02x' in SerieName: SerieName = SerieName.split(" 02x")[0]
            elif ' 03x' in SerieName: SerieName = SerieName.split(" 03x")[0]
            elif ' 04x' in SerieName: SerieName = SerieName.split(" 04x")[0]
            elif ' 05x' in SerieName: SerieName = SerieName.split(" 05x")[0]

            itemlist.append(item.clone( action='episodios', url=url, title=title, thumbnail=thumb,
                                        qualities=qlty, languages = ', '.join(lngs), fmt_sufijo=sufijo,
                                        contentExtra='3',
                                        contentSerieName = SerieName, contentType = 'tvshow', infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        next_url = scrapertools.find_single_match(data, '<span class="pagina pag_actual">.*?' + "<a href='(.*?)'")

        if next_url:
            if '/page/' in next_url:
                itemlist.append(item.clone( title='Siguientes ...', url=next_url, action='list_all', text_color='coral' ))

    return itemlist


def episodios(item):
    logger.info()
    itemlist = []

    if "temporada" in item.contentSerieName:
        SerieName = item.contentSerieName.split("temporada")[0]
        season = scrapertools.find_single_match(item.url, "-temporada-(.*?)-")
        episode = scrapertools.find_single_match(item.url, "-capitulo-(.*?)-")

    elif "S" in item.title:
        SerieName = item.title.split("S")[0]
        season = scrapertools.find_single_match(item.title, "S(.*?)E")
        episode = scrapertools.find_single_match(item.title, "E(.*?)$")

    else:
        SerieName = item.contentSerieName
        season = 0
        episode = 0

    itemlist.append(item.clone( action = 'findvideos', url = item.url, title = item.title, thumbnail = item.thumbnail, contentSerieName = SerieName,
                                contentExtra='',
                                contentSeason = season, contentType = 'episode', contentEpisodeNumber = episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    bloque = scrapertools.find_single_match(data, '<div class="enlace_descarga"(.*?)</center>')
    if not bloque: bloque = scrapertools.find_single_match(data, '<div class=enlace_descarga(.*?)<center>')

    links = scrapertools.find_multiple_matches(bloque, '<a href="(.*?)"')

    for link in links:
        if '/tienda/' in link: continue

        if link == '#': continue

        other = ''
        if 'magnet' in link: other = 'Magnet'

        if not other:
            magnets = scrapertools.find_multiple_matches(bloque, '<a href="(.*?)".*?">Descargar(.*?)</a>')

            for _link, _magnet in magnets:
                if _link == link:
                   if 'magnet' in _magnet: other = 'Magnet'

        itemlist.append(Item( channel = item.channel, action = 'play', title = '', url = link, server = 'torrent',
                              language = item.languages, quality = item.qualities, other = other))

    return itemlist


def play(item):
    logger.info()
    itemlist = []

    if item.url.startswith('/'): item.url = host[:-1] + item.url

    url = item.url

    if url.startswith('magnet:'):
        itemlist.append(item.clone( url = url, server = 'torrent' ))

    elif url.endswith('.torrent'):
          if config.get_setting('proxies', item.channel, default=''):
              if PY3:
                  from core import requeststools
                  data = requeststools.read(url, 'elitetorrent')
              else:
                  data = do_downloadpage(url)

              if str(data) == "b''":
                  return 'Archivo [COLOR red]Inexistente[/COLOR]'

              if data:
                  if 'Página no encontrada</title>' in str(data) or 'no encontrada</title>' in str(data) or '<h1>403 Forbidden</h1>' in str(data):
                      return 'Archivo [COLOR red]No encontrado[/COLOR]'
                  elif '<p>Por causas ajenas a ' in str(data):
                      if not config.get_setting('proxies', item.channel, default=''):
                          return 'Archivo [COLOR red]bloqueado[/COLOR] [COLOR yellow]Configure proxies a usar ...[/COLOR]'

                      return 'Archivo [COLOR red]bloqueado[/COLOR]'

                  file_local = os.path.join(config.get_data_path(), "temp.torrent")
                  with open(file_local, 'wb') as f: f.write(data); f.close()

                  itemlist.append(item.clone( url = file_local, server = 'torrent' ))

          else:
              new_url = base64.b64decode(item.url)

              if new_url.endswith('.torrent'):
                  itemlist.append(item.clone( url = new_url, server = 'torrent' ))
                  return itemlist

              if PY3:
                  from core import requeststools
                  data = requeststools.read(new_url, 'elitetorrent')
              else:
                  data = do_downloadpage(new_url)

              if str(data) == "b''":
                  return 'Archivo [COLOR red]Inexistente[/COLOR]'

              if data:
                  if 'Página no encontrada</title>' in str(data) or 'no encontrada</title>' in str(data) or '<h1>403 Forbidden</h1>' in str(data):
                      return 'Archivo [COLOR red]No encontrado[/COLOR]'
                  elif '<p>Por causas ajenas a ' in str(data):
                      if not config.get_setting('proxies', item.channel, default=''):
                         return 'Archivo [COLOR red]bloqueado[/COLOR] [COLOR yellow]Configure proxies a usar ...[/COLOR]'

                      return 'Archivo [COLOR red]bloqueado[/COLOR]'
                  else:
                      return 'Archivo [COLOR red]Inexistente[/COLOR]'

                  file_local = os.path.join(config.get_data_path(), "temp.torrent")
                  with open(file_local, 'wb') as f: f.write(data); f.close()

                  itemlist.append(item.clone( url = file_local, server = 'torrent' ))

          return itemlist

    else:
        host_torrent = host[:-1]
        url_base64 = decrypters.decode_url_base64(url, host_torrent)

        url_base64 = url_base64.replace('&amp;', '&').strip()

        url_base64 = url_base64.replace('&st=et', '').strip()

        if 'magnet:' in url_base64:
            if not url_base64.startswith('magnet:'):
                url_base64 = url_base64.split("magnet:")[1]
                url_base64 = 'magnet:' + url_base64

        if url_base64.startswith('magnet:'):
            itemlist.append(item.clone( url = url_base64, server = 'torrent' ))

        elif url_base64.endswith(".torrent"):
            if PY3:
                from core import requeststools
                data = requeststools.read(url_base64, 'elitetorrent')
            else:
                data = do_downloadpage(url_base64)

            if str(data) == "b''":
                return 'Archivo [COLOR red]Inexistente[/COLOR]'

            if data:
                if 'Página no encontrada</title>' in str(data) or 'no encontrada</title>' in str(data) or '<h1>403 Forbidden</h1>' in str(data):
                    return 'Archivo [COLOR red]No encontrado[/COLOR]'
                elif '<p>Por causas ajenas a ' in str(data):
                    if not config.get_setting('proxies', item.channel, default=''):
                        return 'Archivo [COLOR red]bloqueado[/COLOR] [COLOR yellow]Configure proxies a usar ...[/COLOR]'

                    return 'Archivo [COLOR red]bloqueado[/COLOR]'

                file_local = os.path.join(config.get_data_path(), "temp.torrent")
                with open(file_local, 'wb') as f: f.write(data); f.close()

                itemlist.append(item.clone( url = file_local, server = 'torrent' ))
            else:
                itemlist.append(item.clone( url = item.url, server = 'torrent' ))

    return itemlist


def _news(item):
    logger.info()

    item.url = host + 'estrenos-23/'
    item.search_type = 'movie'

    return list_all(item)


def search(item, texto):
    logger.info()
    try:
       item.url = host + '?s=' + texto.replace(" ", "+") + '&x=0&y=0'
       return list_all(item)
    except:
       import sys
       for line in sys.exc_info():
           logger.error("%s" % line)
       return []
