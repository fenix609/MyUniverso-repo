# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, tmdb


host = 'https://en.yts-official.com'


per_page = '20'


url_base_movie = '?api=torrents&mode=movie&name=%s&year=%s&quality=all'
url_base_tv = '?api=tv_details&id=%s'


def do_downloadpage(url, post=None, headers=None):
    data = httptools.downloadpage(url, post=post, headers=headers).data

    return data


def mainlist(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar ...', action = 'search', search_type = 'all', text_color = 'yellow' ))

    itemlist.append(item.clone( title = 'Películas', action = 'mainlist_pelis', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Series', action = 'mainlist_series', text_color = 'hotpink' ))

    return itemlist


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + '?api=popular&mode=movie&sort=primary_release_date.desc&page=1', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Novedades', action = 'list_all', url = host + '?api=now_playing&mode=movie&sort=primary_release_date.desc&page=1', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Más valoradas', action = 'list_all', url = host + '?api=top_rated&mode=movie&sort=primary_release_date.desc&page=1', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Más vistas', action = 'list_all', url = host + '?api=trending&mode=movie&sort=primary_release_date.desc&time=week&page=1', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'secciones', url = host, extra = 'Genres', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por país', action = 'secciones', url = host, extra = 'Countries', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por plataforma', action = 'secciones', url = host, extra = 'Streaming', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por estudio', action = 'secciones', url = host, extra = 'Studios', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por colección', action = 'secciones', url = host, extra = 'Collections', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow', text_color = 'hotpink' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + '?api=popular&mode=tv&sort=primary_release_date.desc&page=1', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Novedades', action = 'list_all', url = host + '?api=on_the_air&mode=tv&sort=primary_release_date.desc&page=1', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Más valoradas', action = 'list_all', url = host + '?api=top_rated&mode=tv&sort=primary_release_date.desc&page=1', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Más vistas', action = 'list_all', url = host + '?api=trending&mode=tv&sort=primary_release_date.desc&time=week&page=1', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por género', action = 'secciones', extra = 'Genres', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Por país', action = 'secciones', url = host, extra = 'Countries', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Por plataforma', action = 'secciones', url = host, extra = 'Networks', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'tvshow' ))

    return itemlist


def secciones(item):
    logger.info()
    itemlist = []

    # ~ Ademas si venimos de la Opcion Generos del Menu Principal del Addon
    only_one_genre = False
    if item.filter:
        if item.extra == 'Genres': only_one_genre = True

    url_sec_movie = host + '?api=discover&mode=movie&sort=primary_release_date.desc'
    url_sec_tv = host + '?api=discover&mode=tv&sort=primary_release_date.desc'

    url_sec_col = host + '?api=collection&mode=movie&sort=primary_release_date.desc'

    patron_section = r'(?:)var\s*MENU\s*=\s*({[^;]+});'

    extras = {'Géneros': ['Genres', 'genres', 'discover'], 'Idiomas': ['Countries', 'origin', 'discover'], 
              'Estudios': ['Studios', 'company', 'discover'], 'Networks': ['Networks', 'network', 'discover'],
              'Colecciones': ['Collections', 'id', 'collection'], 'Paises': ['Countries', 'origin', 'discover']}

    if item.search_type == 'movie':
        url_sec = url_sec_movie
        text_color = 'deepskyblue'
    else:
        url_sec = url_sec_tv
        text_color = 'hotpink'

    data = do_downloadpage(host)

    if not data: return itemlist

    data = scrapertools.find_single_match(data, patron_section)

    if item.search_type == 'movie':
       data = scrapertools.find_single_match(data, "tv:.*?movie:(.*?)title:'Best Of'")
    else:
       data = scrapertools.find_single_match(data, "tv:(.*?)movie:")

    if not data: return itemlist

    bloque = scrapertools.find_single_match(data,"title:'" + item.extra + "'(.*?)}]},")

    matches = scrapertools.find_multiple_matches(bloque, "l:'(.*?)'.*?p:.*?:(.*?)}")

    for tit, url in matches:
        if not url or not tit: continue

        url = url.replace("'", '').strip()
        if item.extra == 'Genres': url = url_sec + '&genres=' + url
        elif item.extra == 'Countries': url = url_sec + '&origin=' + url
        elif item.extra == 'Streaming': url = url_sec + '&provider=' + url
        elif item.extra == 'Networks': url = url_sec + '&network=' + url
        elif item.extra == 'Studios': url = url_sec + '&company=' + url
        else: url = url_sec_col + '&id=' + url

        url = url + '&page=1'

        if only_one_genre:
            if not tit == item.filter : continue

            item.url = url
            itemlist = list_all(item)
            return itemlist

        itemlist.append(item.clone( title = tit, url = url, action = 'list_all', filter = tit, text_color = text_color ))

    return sorted(itemlist, key=lambda x: x.title)


def generos(item):
    # ~ Solo venimos desde las opciones de Grupos Menu Principal del Addon
    logger.info()

    if item.search_type == 'movie': pass
    elif item.search_type == 'tvshow': pass
    else: return

    item.extra = 'Genres'

    return secciones(item)


def anios(item):
    logger.info()
    itemlist = []

    val = platformtools.dialog_numeric(0, "Indicar el año a buscar", default="")
    if not val: return

    if not len(val) == 4:
        platformtools.dialog_notification('YtsOficial', '[COLOR red][B]Año Incorrecto[/B][/COLOR]')
        return

    if item.search_type == 'movie':
        item.url = host + '?api=discover&mode=movie&sort=primary_release_date.desc&genre=0&year=' + str(val) + '&page=1'
        item.search_type = 'movie'
        itemlist = list_all(item)
    else:
        item.url = host + '?api=discover&mode=tv&sort=primary_release_date.desc&genre=0&year=' + str(val) + '&page=1'
        item.search_type = 'tvshow'
        itemlist = list_all(item)

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    data = data.replace('}],', ',{"')

    matches = scrapertools.find_multiple_matches(str(data), '"id":(.*?),{"')

    num_matches = len(matches)

    for match in matches:
        match = match.replace('\\/', '/')

        _id = scrapertools.find_single_match(match, '(.*?),"')

        title = scrapertools.find_single_match(match, '"title":"(.*?)"')

        if not title:
            title = scrapertools.find_single_match(match, '"original_title":"(.*?)"')

            if not title: title = scrapertools.find_single_match(match, '"name":"(.*?)"')

            if not title: title = scrapertools.find_single_match(match, '"original_name":"(.*?)"')

        title = clean_title(title)

        title = title.replace('&#8217;', "'").replace('&#038;', '&').strip()

        if not _id or not title: continue

        thumb = scrapertools.find_single_match(match, '"backdrop_path":"(.*?)"')

        lang = scrapertools.find_single_match(match, '"original_language":"(.*?)"')

        lang = lang.capitalize()

        year = scrapertools.find_single_match(match, '"release_date":"(.*?)-').strip()
        if not year: year = scrapertools.find_single_match(match, '"first_air_date":"(.*?)-').strip()

        if not year: year = scrapertools.find_single_match(match, '"year":"(.*?)-').strip()

        if not year: year = '-'

        _titulo = title

        _year = year
        if _year == '-': _year = 0

        tipo = 'movie' if 'mode=movie' in item.url else 'tvshow'
        sufijo = '' if item.search_type != 'all' else tipo

        if tipo == 'movie':
            if item.search_type != 'all':
                if item.search_type == 'tvshow': continue

            url = host + url_base_movie % (_titulo, _year)

            itemlist.append(item.clone( action = 'findvideos', url = url, title = title, _id = _id,
                                        thumbnail = thumb, languages = lang, fmt_sufijo = sufijo,
                                        contentType = 'movie', contentTitle = _titulo, infoLabels = {'year': year} ))

        if tipo == 'tvshow':
            if item.search_type != 'all':
                if item.search_type == 'movie': continue

            url = host + url_base_tv % _id

            itemlist.append(item.clone( action = 'temporadas', url = url, title = title, _id = _id, _year = _year,
                                        thumbnail = thumb, languages = lang, fmt_sufijo = sufijo,
                                        contentType = 'tvshow', contentSerieName = _titulo, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if item.search_type == 'all':
        if '?api=search' in item.url:
            return itemlist

    if itemlist:
        if str(num_matches) == per_page:
            if '"page":' in data:
                ant_pag = scrapertools.find_single_match(item.url, '&page=(.*?)$')

                if ant_pag:
                    ant_url = scrapertools.find_single_match(item.url, '(.*?)&page=')

                    next_page = int(ant_pag)
                    next_page = next_page + 1

                    next_url = ant_url + '&page=' + str(next_page)

                    itemlist.append(item.clone( title='Siguientes ...', url=next_url, action='list_all', text_color='coral' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    bloque = scrapertools.find_single_match(data, '"seasons":(.*?)$')

    matches = re.compile('"season_number":(.*?),', re.DOTALL).findall(bloque)

    for title in matches:
        numtempo = title

        title = 'Temporada ' + title.strip()

        if numtempo == '0':
            if config.get_setting('channels_especiales', default=True): continue

        if len(matches) == 1:
            if config.get_setting('channels_seasons', default=True):
                platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'solo Temporada [COLOR tan]' + title + '[/COLOR]')

            item.page = 0
            item.title = title
            item.contentType = 'season'
            item.contentSeason = numtempo
            itemlist = episodios(item)
            return itemlist

        itemlist.append(item.clone( action = 'episodios', title = title, page = 0, contentType = 'season', contentSeason = numtempo, text_color = 'tan' ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def episodios(item):
    logger.info()
    itemlist = []

    if not item.page: item.page = 0
    if not item.perpage: item.perpage = 50

    data = do_downloadpage(host + '/?api=season_details&id=' + item._id + '&season=' + str(item.contentSeason))
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    data = data + '<FINAL>'

    bloque = scrapertools.find_single_match(data, '"episodes":(.*?)<FINAL>')

    matches = scrapertools.find_multiple_matches(str(bloque), '"air_date":(.*?)}]}')

    if item.page == 0 and item.perpage == 50:
        sum_parts = len(matches)

        try:
            tvdb_id = scrapertools.find_single_match(str(item), "'tvdb_id': '(.*?)'")
            if not tvdb_id: tvdb_id = scrapertools.find_single_match(str(item), "'tmdb_id': '(.*?)'")
        except: tvdb_id = ''

        if config.get_setting('channels_charges', default=True):
            item.perpage = sum_parts
            if sum_parts >= 100:
                platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
        elif tvdb_id:
            if sum_parts > 50:
                platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando Todos los elementos[/COLOR]')
                item.perpage = sum_parts
        else:
            item.perpage = sum_parts

            if sum_parts >= 1000:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]500[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando 500 elementos[/COLOR]')
                    item.perpage = 500

            elif sum_parts >= 500:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]250[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando 250 elementos[/COLOR]')
                    item.perpage = 250

            elif sum_parts >= 250:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]125[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando 125 elementos[/COLOR]')
                    item.perpage = 125

            elif sum_parts >= 125:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]75[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando 75 elementos[/COLOR]')
                    item.perpage = 75

            elif sum_parts > 50:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos [COLOR cyan][B]Todos[/B][/COLOR] de una sola vez ?'):
                    platformtools.dialog_notification('YtsOficial', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
                    item.perpage = sum_parts
                else: item.perpage = 50

    for match in matches[item.page * item.perpage:]:
        match = match.replace('\\/', '/')

        epis = scrapertools.find_single_match(match, '"episode_number":(.*?),')

        if not epis: continue

        _id = scrapertools.find_single_match(match, '"id":(.*?),')

        title = scrapertools.find_single_match(match, '"title":"(.*?)"')

        if not title:
            title = scrapertools.find_single_match(match, '"original_title":"(.*?)"')

            if not title: title = scrapertools.find_single_match(match, '"name":"(.*?)"')

            if not title: title = scrapertools.find_single_match(match, '"original_name":"(.*?)"')

        title = clean_title(title)

        title = title.replace('&#8217;', "'").replace('&#038;', '&').strip()

        if not _id or not title: continue

        thumb = scrapertools.find_single_match(match, '"still_path":"(.*?)"')

        thumb = host + thumb

        titulo = '%sx%s' % (str(item.contentSeason), str(epis)) + ' ' + title

        url = host + '?api=torrents&mode=tv&name=' + str(item.contentSerieName) + '&year=' + item._year + '&id=' + _id

        itemlist.append(item.clone( action='findvideos', title = titulo, url = url, thumbnail = thumb,
                                    contentType = 'episode', contentSeason = item.contentSeason, contentEpisodeNumber = epis ))

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

    patron_qlty = ('(?i)(?:%s\)*\]*|4k|imax|2160|1080|720|webrip)([^$]*$)' % item.infoLabels.get('year', ''))

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    data = data.replace('}],', '},')

    matches = re.compile('"title":(.*?)"},', re.DOTALL).findall(str(data))

    ses = 0

    for match in matches:
        ses += 1

        _title = scrapertools.find_single_match(match, '"(.*?)"')

        url = scrapertools.find_single_match(match, '"magnetUrl":"(.*?)"')

        if url.startswith("magnet:"): pass
        elif url.endswith(".torrent"): pass
        else: url = ''

        if url:
            qlty = scrapertools.find_single_match(_title, patron_qlty)

            other = ''
            if url.startswith("magnet:"): other = 'Magnet'

            itemlist.append(Item( channel = item.channel, action = 'play', title = '', url = url, server = 'torrent',
                                  language = item.languages, quality = qlty, other = other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def clean_title(title):
    logger.info()

    title = title.replace('\\u00e1', 'a').replace('\\u00c1', 'a').replace('\\u00e9', 'e').replace('\\u00ed', 'i').replace('\\u00f3', 'o').replace('\\u00fa', 'u')
    title = title.replace('\\u00f1', 'ñ').replace('\\u00bf', '¿').replace('\\u00a1', '¡').replace('\\u00ba', 'º')
    title = title.replace('\\u00eda', 'a').replace('\\u00f3n', 'o').replace('\\u00fal', 'u').replace('\\u00e0', 'a')

    title = title.replace('\\u00da', 'u')

    title = title.replace('\\u2019', "'").replace('\\u00e3o', 'o').replace('\\u010c', 'c').replace('\\u00c9', 'v').replace('\\u00da', 't').replace('\\u0113', 'i').replace('\\u014d', 'v').replace('\\u00d4', '').replace('\\u0130', '').replace('\\u00e8', ' ')

    title = title.replace('\\u2126', 'Ω')

    title = title.replace('\\u2013', '-').replace('\\u00d6', 'Ö')

    return title


def _news(item):
    logger.info()

    item.url = host + '?api=now_playing&mode=movie&sort=primary_release_date.desc&page=1'
    item.group = 'lasts'
    item.search_type = 'movie'

    return list_all(item)


def search(item, texto):
    logger.info()

    itemlist1 = []
    itemlist2 = []

    try:
       if item.search_type == 'all':
           item.url = host + '?api=search&mode=movie&q=' + texto.replace(" ", "+") + '&page=1'
           itemlist1 = list_all(item)

           item.url = host + '?api=search&mode=tv&q=' + texto.replace(" ", "+") + '&page=1'
           itemlist2 = list_all(item)

           itemlist = itemlist1 + itemlist2
           return itemlist

       elif item.search_type == 'movie':
           item.url = host + '?api=search&mode=movie&q=' + texto.replace(" ", "+") + '&page=1'
       else:
           item.url = host + '?api=search&mode=tv&q=' + texto.replace(" ", "+") + '&page=1'

       return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
