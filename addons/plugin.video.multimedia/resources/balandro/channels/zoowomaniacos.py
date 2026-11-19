# -*- coding: utf-8 -*-

import re, base64

from platformcode import config, logger, platformtools
from core import httptools, scrapertools, servertools, jsontools, tmdb

from core.item import Item


host = 'https://zoowomaniacos.org/'


url_opts = host + 'alternativo3/server.php'

_ref = host + 'home/'

_opt_las_1001 = 'TGFzJTIwMTAwMQ=='


perpage = 10

limitant = 0


def do_downloadpage(url, post=None, headers=None):
    data = httptools.downloadpage(url, post=post, headers=headers).data

    return data


def mainlist(item):
    return mainlist_pelis(item)


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone (title = 'Buscar película ...', action = 'search', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone (title = 'Catálogo', action = 'list_all', url = url_opts,
                                ref = _ref,
                                post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo'},
                                ))

    itemlist.append(item.clone (title = 'Las 1001 que hay que ver', action= 'list_all', url = url_opts, text_color = 'cyan',
                                ref = host + 'home/1001.php',
                                post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o1]': _opt_las_1001},
                                ))

    itemlist.append(item.clone (title = 'Por género', action = 'generos' ))

    itemlist.append(item.clone (title = 'Por año', action = 'anios' ))

    itemlist.append(item.clone (title = 'Por país', action = 'paises' ))

    itemlist.append(item.clone ( title = '[B]Directores:[/B]', folder=False, text_color='moccasin' ))

    itemlist.append(item.clone (title = ' - Por director', action = 'directores', letra = 'Todos' ))

    itemlist.append(item.clone (title = ' - Por letra (A - Z)', action = 'alfabetico' ))

    itemlist.append(item.clone (title = ' - Buscar director ...', action = 'search', one_director=True, search_type = 'person' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    headers = {'Referer': _ref}

    post = {'metodo': 'getGenre'}

    data = do_downloadpage(url_opts, post = post, headers = headers)

    jdata = jsontools.load(data)

    matches = scrapertools.find_multiple_matches(str(jdata), "'id':.*?'(.*?)'.*?'val':.*?'(.*?)'")

    for genre, title in matches:
        title = title.replace('&amp;', '&').strip()

        if config.get_setting('descartar_xxx', default=False):
            if title == 'Animación para Adultos': continue
            elif title == 'Erótico': continue
            elif title == 'Pornografía': continue

        if title == 'Animación para Adultos': title = title + ' (+18)'
        elif title == 'Erótico': title = title + ' (+18)'
        elif title == 'Pornografía': title = title + ' (+18)'

        title = title.replace('África', 'Africa').replace('Émile', 'Emile').replace('Ópera', 'Opera')

        _genre = base64.b64encode(genre.encode("UTF-8")).decode("UTF-8")

        post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o1]': _genre}

        itemlist.append(item.clone (title = title, action = 'list_all',
                                    url = url_opts,
                                    ref = _ref,
                                    post = post,
                                    genre = genre,
                                    option = _genre,
                                    text_color = 'deepskyblue' ))

    return sorted(itemlist, key=lambda x: x.title)


def anios(item):
    logger.info()
    itemlist = []

    headers = {'Referer': _ref}

    post = {'metodo': 'getYear'}

    data = do_downloadpage(url_opts, post = post, headers = headers)

    jdata = jsontools.load(data)

    matches = scrapertools.find_multiple_matches(str(jdata), "'id':.*?'(.*?)'.*?'val':.*?'(.*?)'")

    for year, title in matches:
        _year = base64.b64encode(year.encode("UTF-8")).decode("UTF-8")

        post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o2]': _year}

        itemlist.append(item.clone (title = title, action = 'list_all',
                                    url = url_opts,
                                    ref = _ref,
                                    post = post,
                                    year = year,
                                    option = _year,
                                    text_color = 'deepskyblue' ))

    return sorted(itemlist, key=lambda x: x.title, reverse=True)


def paises(item):
    logger.info()
    itemlist = []

    headers = {'Referer': _ref}

    post = {'metodo': 'getCountry'}

    data = do_downloadpage(url_opts, post = post, headers = headers)

    jdata = jsontools.load(data)

    matches = scrapertools.find_multiple_matches(str(jdata), "'id':.*?'(.*?)'.*?'val':.*?'(.*?)'")

    for country, title in matches:
        title = title.replace('&amp;', '&').strip()

        if title == 'u': title = title.replace('u', 'U')

        _country = base64.b64encode(country.encode("UTF-8")).decode("UTF-8")

        post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o3]': _country}

        itemlist.append(item.clone (title = title, action = 'list_all',
                                    url = url_opts,
                                    ref = _ref,
                                    post = post,
                                    country = country,
                                    option = _country,
                                    text_color = 'moccasin' ))

    return sorted(itemlist, key=lambda x: x.title)


def directores(item):
    logger.info()
    itemlist = []

    if not item.paginacion: item.paginacion = 0

    paginacion = 20000
    if item.letra == 'Todos': paginacion = 200

    if config.get_setting('channels_charges', default=True):
        if item.letra == 'Todos':
            platformtools.dialog_notification('ZoowoManiacos', '[COLOR blue]Cargando directores[/COLOR]')
        else:
            if not item.one_director:
                platformtools.dialog_notification('ZoowoManiacos', '[COLOR blue]Seleccionado directores[/COLOR]' + '  Letra: ' + item.letra.upper())
            else:
                platformtools.dialog_notification('ZoowoManiacos', '[COLOR blue]Buscando director[/COLOR]')

    headers = {'Referer': _ref}

    post = {'metodo': 'getDirector'}

    data = do_downloadpage(url_opts, post = post, headers = headers)

    jdata = jsontools.load(data)

    matches = scrapertools.find_multiple_matches(str(jdata), "'id':.*?'(.*?)'.*?'val':.*?'(.*?)'")

    num_matches = len(matches)

    for director, title in matches[item.paginacion * paginacion:]:
        if title == '5 minutes to live': continue

        if title == 'laho': title = 'Laho'
        elif title == 'passolini': title = 'Passolini'

        if item.letra:
            if not item.letra == 'Todos':
                letra_director = director[:1]

                if not letra_director.lower() == item.letra.lower(): continue
        elif item.one_director:
            if item.text_director:
                title_director = director

                if not item.text_director.lower() in title_director.lower(): continue

        title = title.replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')

        title = title.replace('&amp;', '&').strip()

        _director = base64.b64encode(director.encode("UTF-8")).decode("UTF-8")

        post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o4]': _director}

        itemlist.append(item.clone (title = title, action = 'list_all',
                                    url = url_opts,
                                    ref = _ref,
                                    post = post,
                                    director = director,
                                    option = _director,
                                    text_color = 'paleturquoise' ))

        if len(itemlist) > paginacion: break

    if itemlist:
        if num_matches > paginacion:
            hasta = ((item.paginacion * paginacion) + paginacion)

            if hasta < num_matches:
                itemlist.append(item.clone( title='Siguientes ...', paginacion = item.paginacion + 1, action='directores', text_color='coral' ))

    return sorted(itemlist, key=lambda x: x.title)


def alfabetico(item):
    logger.info()
    itemlist = []

    for letra in 'abcdefghijklmnopqrstuvwxyz':
        itemlist.append(item.clone ( title = letra.upper(), action = 'directores', letra = letra, text_color = 'paleturquoise' ))

    return itemlist


def list_all(item): 
    logger.info()
    itemlist = []

    if not item.pags: item.pags = 1

    option = str(item.option)

    post = item.post

    headers = {'Referer': item.ref}

    data = do_downloadpage(item.url, post = post, headers = headers)

    jdata = jsontools.load(data)

    matches = scrapertools.find_multiple_matches(str(jdata), "'a1':(.*?)'total':")

    for match in matches:
        _id = scrapertools.find_single_match(str(match), "'(.*?)',")

        title = scrapertools.find_single_match(str(match), "'a2': '(.*?)',")

        if not _id or not title: continue

        direccion = scrapertools.find_single_match(str(match), "'a3': '(.*?)',")

        titulo = title + ' - ' + direccion

        year = scrapertools.find_single_match(str(match), "'a4': '(.*?)',")
        if not year: year = '-'

        thumb = scrapertools.find_single_match(str(match), "'a8': '(.*?)',")

        if thumb: thumb = host + 'wp-content/uploads/' + thumb

        plot = scrapertools.find_single_match(str(match), "'a100': '(.*?)',")

        itemlist.append(item.clone (action='findvideos', _match = match, title = titulo, thumbnail = thumb,
                                    contentType='movie', contentTitle=title, infoLabels={'year': year, 'plot': plot} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        if not item.limit: limit = perpage
        else: limit = int(item.limit) * perpage

        limitant = int(item.pags) * perpage

        if option:
            if item.tex_search:
                post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o5]': option}

            elif item.year:
                post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o2]': option}

            elif item.country:
                post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o3]': option}

            elif item.director:
                post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o4]': option}

            else:
                post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o1]': option}

        elif '1001.php' in item.ref:
            post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o1]': _opt_las_1001}

        else:
            post = {'order': 1, 'limit': limit, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo'}

        itemlist.append(item.clone (title = 'Siguientes ...', action = 'list_all', text_color='coral',
                                    url = item.url,
                                    ref = item.ref,
                                    pags = item.pags + 1,
                                    limit = limit,
                                    limitant = limitant,
                                    post = post,
                                    option = option ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    IDIOMAS = {
            'es': 'Esp',
            'ar': 'Lat',
            'co': 'Lat',
            'cl': 'Lat',
            'pe': 'Lat',
            'mx': 'Lat',
            'en': 'Ing',
            'gb': 'Ing',
            'vose': 'Vose',
            'vo': 'VO',
            'it': 'IT',
            'de': 'DE',
            'fr': 'FR',
            'jp': 'JP',
            'td': 'RO',
            'se': 'SE',
            'br': 'BR',
            'ru': 'RU',
            'kr': 'KR',
            'pt': 'PT',
            'cn': 'HK',
            'pl': 'PL',
            'in': 'IN',
            'tr': 'TR',
            'nl': 'NL'
            }

    if not item._match: return

    ses = 0

    matches = scrapertools.find_multiple_matches(str(item._match), '{"name":(.*?)}')

    for match in matches:
        ses += 1

        lang = scrapertools.find_single_match(str(match), '"idioma":"(.*?)"')

        if not lang:
            if '"VOSE' in match: lang = 'vose'
            elif '"SPA' in match: lang = 'es'
            else: lang = '?'

        lang = IDIOMAS.get(lang, lang)

        url = scrapertools.find_single_match(str(match), '"url":"(.*?)"')

        url = url.replace('\\/', '/')

        servidor = servertools.get_server_from_url(url)

        url = servertools.normalize_url(servidor, url)

        itemlist.append(Item( channel = item.channel, action = 'play', title = '', server=servidor, url=url, language=lang ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def _las1001(item):
    logger.info()

    item.url = url_opts
    item.ref = host + 'home/1001.php'

    item.post = {'order': 1, 'limit': perpage, 'limitant': 0, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o1]': _opt_las_1001}

    return list_all(item)


def search(item, texto):
    logger.info()
    try:
        item.tex_search = texto.replace(" ", "+")

        _option = item.tex_search = base64.b64encode(item.tex_search.encode("UTF-8")).decode("UTF-8")

        item.option = _option

        if not item.one_director:
            post = {'order': 1, 'limit': perpage, 'limitant': limitant, 'metodo': 'ObtenerListaTotalAlternativo', 'options[o5]': _option}

            item.url = url_opts
            item.post = post
            return list_all(item)

        item.text_director = texto
        return directores(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []

