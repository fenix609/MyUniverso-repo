# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb


# ~  29/10/2026  las búsquedas dan CloudFlare Protection

host = 'https://ver.pelisonline.ws/'


def do_downloadpage(url, post=None, headers=None):
    # ~ por si viene de enlaces guardados
    ant_hosts = ['https://pelisonline.ws/']

    for ant in ant_hosts:
        url = url.replace(ant, host)

    data = httptools.downloadpage(url, post=post, headers=headers).data

    if config.get_setting('developer_team'):
        if '/?s=' in url:
            if '<title>Just a moment...</title>' in data:
                platformtools.dialog_notification('Team - PeliculasOnline', '[COLOR red][B]CloudFlare[COLOR orangered] Protection[/B][/COLOR]')
                return ''

    return data


def acciones(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( channel='submnuctext', action='_test_webs', title='Test Web del canal [COLOR yellow][B] ' + host + '[/B][/COLOR]',
                                from_channel='peliculasonline', folder=False, text_color='chartreuse' ))

    itemlist.append(Item( channel='helper', action='show_help_peliculasonline', title='[COLOR aquamarine][B]Aviso[/COLOR] [COLOR green]Información[/B][/COLOR] canal', thumbnail=config.get_thumb('peliculasonline') ))

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

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'peliculas/', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow', text_color = 'hotpink' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'series/', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host + 'generos/')

    bloque = scrapertools.find_single_match(data, '>Generos</h1>(.*?)</ul>')

    matches = re.compile('href="(.*?)".*?<strong>(.*?)</strong>', re.DOTALL).findall(bloque)

    for url, title in matches:
        if 'Series' in title: continue

        title = title.replace('&amp;', '&')

        title = title.strip()

        if title == 'Estreno': continue
        elif title == 'Recomendada': continue
        elif title == 'News': continue

        itemlist.append(item.clone( action = 'list_all', title = title, url = url, text_color = 'deepskyblue' ))

    return sorted(itemlist, key=lambda it: it.title)


def anios(item):
    logger.info()
    itemlist = []

    if item.search_type == 'movie':
        text_color = 'deepskyblue'
        limit_year = 1939
        url_any = host + 'release/'
    else:
        text_color = 'hotpink'
        limit_year = 1959
        url_any = host + 'release/'

    from datetime import datetime
    current_year = int(datetime.today().year)

    for x in range(current_year, limit_year, -1):
        url = url_any + str(x) + '/'
        itemlist.append(item.clone( title = str(x), url = url, action = 'list_all', text_color=text_color ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    matches = scrapertools.find_multiple_matches(data, '<article(.*?)</article>')
    if not matches: matches = scrapertools.find_multiple_matches(data, '<a class="gn-card gn-card--grid"(.*?)</span></a>')

    for match in matches:
        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        title = scrapertools.find_single_match(match, '<h2 class="entry-title">(.*?)</h2>')
        if not title: title = scrapertools.find_single_match(match, 'alt="(.*?)"')
        if not title: title = scrapertools.find_single_match(match, 'title="(.*?)"')

        if not url or not title: continue

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        year = scrapertools.find_single_match(match, '<span class="gn-card__y">(.*?)</span>')

        if year: title = title.replace('(' + year + ')', '').strip()
        else: year = '-'

        langs = []
        if 'CAS"' in match: langs.append('Esp')
        if 'LAT' in match: langs.append('Lat')
        if 'SUB' in match: langs.append('Vose')

        tipo = 'tvshow' if '/series/' in url else 'movie'
        sufijo = '' if item.search_type != 'all' else tipo

        if tipo == 'movie':
            if not item.search_type == "all":
                if item.search_type == "tvshow": continue

            itemlist.append(item.clone( action = 'findvideos', url = url, title=title, thumbnail=thumb,
                                        fmt_sufijo=sufijo, languages=', '.join(langs),
                                        contentType = 'movie', contentTitle = title, infoLabels={'year': year} ))

        if tipo == 'tvshow':
            if not item.search_type == "all":
                if item.search_type == "movie": continue

            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb,
                                        fmt_sufijo=sufijo, languages=', '.join(langs),
                                        contentType='tvshow', contentSerieName=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        next_page = scrapertools.find_single_match(data, '<nav class="navigation.*?class="page-numbers current">.*?href="(.*?)".*?</a>')

        if next_page:
            if '/page/' in next_page:
                itemlist.append(item.clone( title = 'Siguientes ...', url = next_page, action = 'list_all', text_color='coral' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    matches = re.compile('<div class="item-season">.*?Temporada (.*?)</div>', re.DOTALL).findall(data)

    for tempo in matches:
        tempo = tempo.strip()

        title = 'Temporada ' + tempo

        if len(matches) == 1:
            if config.get_setting('channels_seasons', default=True):
                platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'solo [COLOR tan]' + title + '[/COLOR]')

                item.page = 0
                item.contentType = 'season'
                item.contentSeason = tempo
                itemlist = episodios(item)
                return itemlist

        itemlist.append(item.clone( action='episodios', title=title, page = 0, contentType='season', contentSeason=tempo, text_color = 'tan' ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def episodios(item):
    logger.info()
    itemlist=[]

    if not item.page: item.page = 0
    if not item.perpage: item.perpage = 50

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '<div class="item-season">.*?Temporada ' + str(item.contentSeason) + '(.*?)</div></div>')

    matches = re.compile('<a href="(.*?)".*?</i>(.*?)</a>', re.DOTALL).findall(bloque)

    if item.page == 0 and item.perpage == 50:
        sum_parts = len(matches)

        try:
            tvdb_id = scrapertools.find_single_match(str(item), "'tvdb_id': '(.*?)'")
            if not tvdb_id: tvdb_id = scrapertools.find_single_match(str(item), "'tmdb_id': '(.*?)'")
        except: tvdb_id = ''

        if config.get_setting('channels_charges', default=True):
            item.perpage = sum_parts
            if sum_parts >= 100:
                platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
        elif tvdb_id:
            if sum_parts > 50:
                platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando Todos los elementos[/COLOR]')
                item.perpage = sum_parts
        else:
            item.perpage = sum_parts

            if sum_parts >= 1000:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]500[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando 500 elementos[/COLOR]')
                    item.perpage = 500

            elif sum_parts >= 500:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]250[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando 250 elementos[/COLOR]')
                    item.perpage = 250

            elif sum_parts >= 250:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]125[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando 125 elementos[/COLOR]')
                    item.perpage = 125

            elif sum_parts >= 125:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]75[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando 75 elementos[/COLOR]')
                    item.perpage = 75

            elif sum_parts > 50:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos [COLOR cyan][B]Todos[/B][/COLOR] de una sola vez ?'):
                    platformtools.dialog_notification('PeliculasOnline', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
                    item.perpage = sum_parts
                else: item.perpage = 50

    for url, epis in matches[item.page * item.perpage:]:
        epis = epis.replace('capitulo', '').strip()
        if not epis: epis = 1

        titulo = str(item.contentSeason) + 'x' + str(epis) + ' ' + item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'")

        itemlist.append(item.clone( action='findvideos', url = url, title = titulo,
                                    contentType = 'episode', contentSeason = item.contentSeason, contentEpisodeNumber=epis ))

        if len(itemlist) >= item.perpage:
            break

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        if len(matches) > (item.page + 1) * item.perpage:
            itemlist.append(item.clone( title="Siguientes ...", action="episodios", page = item.page + 1, perpage = item.perpage, text_color='coral' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    bloque = scrapertools.find_single_match(data, '<div class="gn-player__servers is-active"(.*?)</section>')

    matches = re.compile('href="(.*?)"', re.DOTALL).findall(bloque)

    ses = 0

    # ~ players
    for _url in matches:
        ses += 1

        _url = _url.replace('&amp;#038;', '&').replace('&#038;', '&').replace('&amp;', '&')

        datat = do_downloadpage(_url)

        link = scrapertools.find_single_match(datat, '<iframe.*?src="(.*?)</iframe>')

        if not link: continue

        srv = servertools.get_server_from_url(link)

        if not srv == 'directo':
            lang = item.languages

            other = ''
            if srv == 'various': other = servertools.corregir_other(link)
            elif srv == 'zures': other = servertools.corregir_zures(link)

            itemlist.append(Item( channel = item.channel, action = 'play', server = srv, url = link,
                                  language = lang, other = other ))

            continue

        datap = do_downloadpage(link)

        links = scrapertools.find_multiple_matches(str(datap), 'data-src="(.*?)"')

        for url in links:
            if '/ul.' in url: continue
            elif '/1fichier.' in url: continue
            elif '/rapidgator' in url: continue
            elif '/katfile' in url: continue
            elif '/nitro' in url: continue
            elif '/filecrypt.' in url: continue
            elif '/filepv.' in url: continue
            elif '/ddownload.' in url: continue

            elif '/multiup.' in url: continue
            elif '/filemirage.' in url: continue

            elif '/powvideo.' in url: continue
            elif '/streamplay.' in url: continue

            elif '/viewsb.' in url: continue
            elif '/www.fembed.' in url: continue
            elif '/fembed.' in url: continue
            elif '.fembed.' in url: continue

            elif '/uptobox' in url: continue
            elif '/formatearwindows' in url: continue

            elif 'embed.mystream' in url: continue

            lang = '?'

            if '#lang=LAT' in url: lang = 'Lat'
            elif '#lang=CAS' in url: lang = 'Esp'
            elif '#lang=VOS' in url: lang = 'Vose'
            elif '#lang=SUB' in url: lang = 'Vose'

            if '/waaw.in/' in url: url = url.replace('/waaw.in/', '/waaw.to/')

            elif '/player.cuevana.ac/' in url: url = url.replace('/player.cuevana.ac/', '/waaw.to/')
            elif '/player.cuevana3.ac/' in url: url = url.replace('/player.cuevana.ac/', '/waaw.to/')
            elif '/player.cuevana.one/' in url: url = url.replace('/player.cuevana3.one/', '/waaw.to/')
            elif '/player.cuevana3.one/' in url: url = url.replace('/player.cuevana3.one/', '/waaw.to/')

            elif '/player.fiuxy2.com/' in url: url = url.replace('/player.fiuxy2.com/', '/waaw.to/')

            servidor = servertools.get_server_from_url(url)

            if servertools.is_server_available(servidor):
                if not servertools.is_server_enabled(servidor): continue
                else:
                   if not config.get_setting('developer_mode', default=False): continue

            other = ''
            if servidor == 'various': other = servertools.corregir_other(url)
            elif servidor == 'zures': other = servertools.corregir_zures(url)

            itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, url = url,
                                  language = lang, other = other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist
#####################################################################################################
    # ~ Series
    if not itemlist:
        bloque = scrapertools.find_single_match(str(data), 'var video =(.*?)</script>')

        matches = scrapertools.find_multiple_matches(str(bloque), '>video.*?<iframe.*?src="(.*?)"')

        for url in matches:
            ses += 1

            if '/ul.' in url: continue
            elif '/1fichier.' in url: continue
            elif '/rapidgator' in url: continue
            elif '/katfile' in url: continue
            elif '/nitro' in url: continue
            elif '/filecrypt.' in url: continue
            elif '/multiup.' in url: continue
            elif '/filemirage.' in url: continue
            elif '/powvideo.' in url: continue

            elif '/viewsb.' in url: continue

            elif '.fembed.' in url: continue
            elif '/fembed.' in url: continue

            elif '/feurl.' in url: continue

            servidor = servertools.get_server_from_url(url)

            if servertools.is_server_available(servidor):
                if not servertools.is_server_enabled(servidor): continue
            else:
                if not config.get_setting('developer_mode', default=False): continue

            other = ''
            if servidor == 'various': other = servertools.corregir_other(url)
            elif servidor == 'zures': other = servertools.corregir_zures(url)

            if '(Castellano)' in data: lang = 'Esp'
            elif '(Latino)' in data: lang = 'Lat'
            elif '(Substitulado)' in data: lang = 'Vose'
            else: lang = '?'

            itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, url = url, language = lang, other = other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def search(item, texto):
    logger.info()
    try:
       if item.search_type == 'movie': url_search = host + 'peliculas/?s='
       elif item.search_type == 'tvshow': url_search = host + 'series/?s='
       else: url_search = host + '?s='

       item.url = url_search + texto.replace(" ", "+")
       return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []

