# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools


host = 'https://pandamovies.org/'


def do_downloadpage(url, post=None, headers=None):
    # ~ por si viene de enlaces guardados
    ant_hosts = ['https://pandamovies.pw/']

    for ant in ant_hosts:
        url = url.replace(ant, host)

    raise_weberror = True
    if '/release-year/' in url: raise_weberror = False

    data = httptools.downloadpage(url, post=post, headers=headers, raise_weberror=raise_weberror).data

    return data


def mainlist(item):
    return mainlist_pelis(item)


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    if not config.get_setting('ses_pin'):
        if config.get_setting('adults_password'):
            from modules import actions
            if actions.adults_password(item) == False: return

        config.set_setting('ses_pin', True)

    itemlist.append(item.clone( title = 'Buscar vídeo ...', action = 'search', search_type = 'movie', search_video = 'adult', text_color = 'orange' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host  + 'movies' ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host  + 'most-viewed' ))

    itemlist.append(item.clone( title = 'Por canal', action = 'canales' ))
    itemlist.append(item.clone( title = 'Por categoría', action = 'categorias' ))

    itemlist.append(item.clone( title = 'Por estrella', action = 'pornstars', url = host + 'pornstars' ))

    itemlist.append(item.clone( title = 'Por año', action='anios' ))

    return itemlist


def canales(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host)

    bloque = scrapertools.find_single_match(data, '>Popular Genres<(.*?)</section>')

    matches = re.compile('href="(.*?)".*?>(.*?)</a>', re.DOTALL).findall(bloque)

    for url, title in matches:
        title = title.replace('&#038;', '&').replace('&#8217;s', "'s").replace('&#8217;', "'s").replace('&amp;', '&').strip()

        itemlist.append(item.clone (action='list_all', title=title, url=url, text_color = 'violet' ))

    return sorted(itemlist, key=lambda x: x.title)


def categorias(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host)

    bloque = scrapertools.find_single_match(data, '>Top Studios<(.*?)</section>')

    matches = re.compile('href="(.*?)".*?>(.*?)</a>', re.DOTALL).findall(bloque)

    for url, title in matches:
        title = title.replace('&amp;', '&').replace('#038;', '').strip()

        itemlist.append(item.clone (action='list_all', title=title, url=url, text_color = 'moccasin' ))

    return sorted(itemlist, key=lambda x: x.title)


def pornstars(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    bloque = scrapertools.find_single_match(data, '>Popular<(.*?)</nav>')

    matches = re.compile('href="(.*?)".*?src="(.*?)".*?alt="(.*?)"', re.DOTALL).findall(bloque)

    for url, thumb, title in matches:
        itemlist.append(item.clone( action = 'list_all', title=title, url=url, thumbnail=thumb, text_color='orange' ))

    if itemlist:
        next_page = scrapertools.find_single_match(data, 'class="page-numbers current">.*?href="(.*?)"')

        if next_page:
            if '?pg=' in next_page:
                itemlist.append(item.clone (action='pornstars', title='Siguientes ...', url=next_page, text_color = 'coral') )

    return itemlist


def anios(item):
    logger.info()
    itemlist = []

    from datetime import datetime
    current_year = int(datetime.today().year)

    for x in range(current_year, 1969, -1):
        url = host + 'release-year/' + str(x)

        itemlist.append(item.clone( title = str(x), url = url, action = 'list_all', text_color = 'orange' ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r"\n|\r|\t|&nbsp;|<br>|<br/>", "", data)

    matches = re.compile('<article(.*?)</article>', re.DOTALL).findall(data)

    for match in matches:
        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        title = scrapertools.find_single_match(match, 'alt="(.*?)"')

        if not url or not title: continue

        title = title.replace('Watch', '').replace('Porn Online Free', '').strip()

        title = title.replace('&#038;', '&').replace('&#8217;s', "'s").replace('&#8217;', "'s").replace('&#8211;', '').replace('&amp;', '').strip()

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        titulo = title

        time = scrapertools.find_single_match(match, '<span class="card__dur">(.*?)</span>').strip()

        if time: titulo = "[COLOR tan]%s[/COLOR] %s" % (time, title)

        itemlist.append(item.clone (action='findvideos', title=titulo, url=url, thumbnail=thumb,
                                    contentType = 'movie', contentTitle = title, contentExtra='adults' ))

    if itemlist:
        next_page = scrapertools.find_single_match(data, '"Pagination".*?class="page-numbers current">.*?href="(.*?)"')

        if next_page:
            if '/page/' in next_page:
                itemlist.append(item.clone (action='list_all', title='Siguientes ...', url=next_page, text_color = 'coral') )

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    if not config.get_setting('ses_pin'):
        if config.get_setting('adults_password'):
            from modules import actions
            if actions.adults_password(item) == False: return

        config.set_setting('ses_pin', True)

    data = do_downloadpage(item.url)
    data = re.sub(r"\n|\r|\t|&nbsp;|<br>|<br/>", "", data)

    ses = 0

    bloque = scrapertools.find_single_match(data, 'data-servers="(.*?)</div></div></div>')

    matches = scrapertools.find_multiple_matches(bloque, '&quot;u&quot;:&quot;(.*?)&quot;')

    for url in matches:
        ses += 1

        if 'link=' in url: url = scrapertools.find_single_match(url, 'link=(.*?)$')

        if not url: continue

        url = url.replace('\\/', '/')

        if '/?s=' in url: continue

        elif '/playmate.' in url: continue
        elif '/frdl.' in url: continue
        elif '/drivevideo.' in url: continue
        elif '/snowdayonline.' in url: continue
        elif '/freepopnews.' in url: continue
        elif '/filepv.' in url: continue

        elif '.seekplayer.' in url: continue
        elif '.streamkithmc.' in url: continue
        elif '.streamkitagg.' in url: continue
        elif '.cloudwarebrh.' in url: continue
        elif '.video-twimg.' in url: continue

        elif '/nitroflare.' in url: continue
        elif 'rapidgator.' in url: continue

        elif '/pooptv.' in url: continue
        elif '=pooptv.me' in url: continue

        elif '/director/' in url: continue
        elif '/actor/' in url: continue
        elif '/category/' in url: continue
        elif '/release-year/' in url: continue

        ref = url

        servidor = servertools.get_server_from_url(url)

        url = servertools.normalize_url(servidor, url)

        other = ''

        if servidor == 'various': other = servertools.corregir_other(url)
        elif servidor == 'zures': other = servertools.corregir_zures(url)

        force_input = ''
        if other == 'Lulustream': force_input = True

        if servidor == 'kinoger':
            if config.get_setting('developer_team'): other = url.replace('https://', '').strip()
        else: ref = ''

        if not servidor == 'directo':
            itemlist.append(Item( channel = item.channel, action='play', title='', server=servidor, url=url, ref=ref,
                                  language = 'Vo', other = other.capitalize(), force_input=force_input ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def search(item, texto):
    logger.info()
    try:
        config.set_setting('search_last_video', texto)

        item.url =  host + '?s=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
