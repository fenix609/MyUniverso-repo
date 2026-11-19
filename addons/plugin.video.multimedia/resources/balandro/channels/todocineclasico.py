# -*- coding: utf-8 -*-

import re, base64

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, tmdb, servertools


host = 'https://leyendasdelcine.com/'


def do_downloadpage(url, post=None, headers=None):
    data = httptools.downloadpage(url, post=post, headers=headers).data

    if '<title>Just a moment...</title>' in data:
        if not '/search_elastic?s=' in url:
            platformtools.dialog_notification(config.__addon_name, '[COLOR red][B]CloudFlare[COLOR orangered] Protection[/B][/COLOR]')
        return ''

    return data


def mainlist(item):
    return mainlist_pelis(item)

def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone ( title = 'Buscar película ...', action = 'search', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone ( title = 'Catálogo', action = 'list_all', url = host + 'movies', search_type = 'movie' ))

    itemlist.append(item.clone ( title = 'Últimas', action = 'list_all', url = host + 'collections/ultimas-películas/1', search_type = 'movie', text_color = 'cyan' ))

    itemlist.append(item.clone ( title = 'Más populares', action = 'list_all', url = host + 'collections/películas-más-populares/5', search_type = 'movie' ))

    itemlist.append(item.clone ( title = 'Lo más antiguo', action = 'list_all', url = host + 'movies?filter=old', search_type = 'movie' ))

    itemlist.append(item.clone ( title = 'Por idioma', action = 'idiomas', search_type = 'movie' ))

    itemlist.append(item.clone ( title = 'Por género', action = 'generos', search_type = 'movie' ))

    itemlist.append(item.clone ( title = 'Por país', action = 'paises', search_type = 'movie' ))

    itemlist.append(item.clone ( title = 'Listas:', search_type = 'movie', text_color = 'moccasin' ))

    itemlist.append(item.clone ( title = ' - Orden alfabético', action = 'list_all', url = host + 'movies?filter=alpha', search_type = 'movie' ))
    itemlist.append(item.clone ( title = ' - Orden aleatorio', action = 'list_all', url = host + 'movies?filter=rand', search_type = 'movie' ))

    return itemlist


def idiomas(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Castellano', action = 'list_all', url = host + 'movies?lang_id=8', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Francés', action = 'list_all', url = host + 'movies?lang_id=4', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Inglés', action = 'list_all', url = host + 'movies?lang_id=2', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Latino', action = 'list_all', url = host + 'movies?lang_id=12', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Mudo', action = 'list_all', url = host + 'movies?lang_id=10', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Subtitulado', action = 'list_all', url = host + 'movies?lang_id=9', text_color = 'deepskyblue' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host + 'movies')
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Géneros<(.*?)</select>')

    matches = scrapertools.find_multiple_matches(bloque, '<option value="(.*?)".*?>(.*?)</option>')

    for url, title in matches:
        if title == 'Tráilers de Películas': continue

        elif title == 'Series': continue
        elif title == 'Blu-ray': continue
        elif title == 'DVD': continue

        elif title == 'Rusia': continue
        elif title == 'Italia': continue
        elif title == 'Francia': continue
        elif title == 'España': continue
        elif title == 'Alemania': continue
        elif title == 'Suecia': continue
        elif title == 'Mexico': continue
        elif title == 'Reino Unido': continue
        elif title == 'Estados Unidos': continue
        elif title == 'Argentina': continue
        elif title == 'Indonesia': continue
        elif title == 'Japón': continue
        elif title == 'Jordania': continue
        elif title == 'Noruega': continue
        elif title == 'Grecia': continue
        elif title == 'Australia': continue
        elif title == 'Islandia': continue
        elif title == 'Checoslovaquia': continue
        elif title == 'Palestina': continue
        elif title == 'China': continue
        elif title == 'Túnez': continue
        elif title == 'Polonia': continue

        title = title.replace('Épico', 'Epico')

        itemlist.append(item.clone( action='list_all', title=title, url=url, text_color = 'deepskyblue' ))

    return sorted(itemlist, key = lambda it: it.title)


def paises(item):
    logger.info()
    itemlist = []

    logger.info()
    itemlist = []

    data = do_downloadpage(host + 'movies')
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Géneros<(.*?)</select>')

    matches = scrapertools.find_multiple_matches(bloque, '<option value="(.*?)".*?>(.*?)</option>')

    for url, title in matches:
        if title == 'Rusia': pass
        elif title == 'Italia': pass
        elif title == 'Francia': pass
        elif title == 'España': pass
        elif title == 'Alemania': pass
        elif title == 'Suecia': pass
        elif title == 'Mexico': pass
        elif title == 'Reino Unido': pass
        elif title == 'Estados Unidos': pass
        elif title == 'Argentina': pass
        elif title == 'Indonesia': pass
        elif title == 'Japón': pass
        elif title == 'Jordania': pass
        elif title == 'Noruega': pass
        elif title == 'Grecia': pass
        elif title == 'Australia': pass
        elif title == 'Islandia': pass
        elif title == 'Checoslovaquia': pass
        elif title == 'Palestina': pass
        elif title == 'China': pass
        elif title == 'Túnez': pass
        elif title == 'Polonia': pass

        else: continue

        itemlist.append(item.clone( action='list_all', title=title, url=url, text_color = 'deepskyblue' ))

    return sorted(itemlist, key = lambda it: it.title)


def list_all(item): 
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    if '/collections/' in item.url or '/search_elastic' in item.url:
        matches = re.compile('<div class="single-video">(.*?)</div></a></div>', re.DOTALL).findall(data)
    else:
        matches = re.compile('<div class="single-video">(.*?)</div></div>', re.DOTALL).findall(data)

    for match in matches:
        url = scrapertools.find_single_match(match, ' href="(.*?)"')

        title = scrapertools.find_single_match(match, 'title="(.*?)"')

        if not url or not title: continue

        title = title.replace('&#8211;', '').replace('\&#039;s', "'s").strip()

        thumb = scrapertools.find_single_match(match, ' src="(.*?)"')

        year = scrapertools.find_single_match(title, '(\d{4})')
        if year: title = title.replace(('(' + year + ')'), '').strip()
        else: year = '-'

        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb,
                                    contentType='movie', contentTitle=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        next_page = scrapertools.find_single_match(data, '<div class="nav-links">.*?<li class=" active">.*?<li class="">.*?href="(.*?)".*?</nav>')

        if next_page:
            next_page = next_page.replace('&amp;', '&')

            if '?page=' in next_page or '&page=' in next_page:
                itemlist.append(item.clone( title = 'Siguientes ...', url = next_page, action = 'list_all', text_color = 'coral' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    links = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    if '?lang_id=8' in data: lang = 'Esp'
    elif '?lang_id=4' in data: lang = 'Fr'
    elif '?lang_id=2' in data: lang = 'Ing'
    elif '?lang_id=10' in data: lang = 'Vo'
    elif '?lang_id=9' in data: lang = 'Vose'
    else: lang = '?'

    lnk = item.url.replace('/details/', '/watch/')

    data = do_downloadpage(lnk)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    matches = scrapertools.find_multiple_matches(data, '<iframe.*?src="(.*?)".*?</iframe>')

    if not matches: matches = scrapertools.find_multiple_matches(data, '{source:"(.*?)"')

    ses = 0

    for url in matches:
        ses += 1

        if url.startswith("//"): url = 'https:' + url

        if not 'http' in url:
            url = url.replace('encrypt:' , '').strip()

            url = base64.b64decode(url).decode("utf-8")
 
        servidor = servertools.get_server_from_url(url)

        if servertools.is_server_available(servidor):
            if not servertools.is_server_enabled(servidor): continue
        else:
            if not config.get_setting('developer_mode', default=False): continue

        other = ''
        if servidor == 'directo':
            if not config.get_setting('developer_mode', default=False): continue
            other = url.replace('https://', '').strip()

        elif servidor == 'youtube': other = 'Tráiler'

        url = servertools.normalize_url(servidor, url)

        if url in str(links): continue

        links.append(url)

        itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url, language = lang, other = other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def _news(item):
    logger.info()

    item.url = host + 'collections/ultimas-películas/1'
    item.search_type = 'movie'

    return list_all(item)


def search(item, texto):
    logger.info()
    try:
        item.url = host + 'search_elastic?s=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
