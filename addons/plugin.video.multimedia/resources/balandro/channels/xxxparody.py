# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools


host = 'https://xxxparodyhd.net/'


def do_downloadpage(url, post=None, headers=None, raise_weberror=True):
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

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'movies/' ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host + 'most-viewed/' ))
    itemlist.append(item.clone( title = 'Más valorados', action = 'list_all', url = host + 'most-rating/' ))

    itemlist.append(item.clone( title = 'Por estudio', action = 'estudios', url = host + 'parody-studios/' ))

    itemlist.append(item.clone( title = 'Por estrella', action = 'pornstars', url = host + 'parody-pornstars' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', url = host ))

    return itemlist


def estudios(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', '', data)

    matches = re.compile('<a class="tcard".*?href="(.*?)".*?src="(.*?)".*?alt="(.*?)"', re.DOTALL).findall(data)

    for url, thumb, title in matches:
        title = title.replace('&amp;', '&').replace('#038;', '').strip()

        itemlist.append(item.clone (action='list_all', title=title, url=url, thumbnail=thumb, text_color='moccasin' ))

    if itemlist:
        next_page = scrapertools.find_single_match(data, 'class="page-numbers current">.*?href="(.*?)"')

        if next_page:
            if '?pg=' in next_page:
                itemlist.append(item.clone (action='estudios', title='Siguientes ...', url=next_page, text_color = 'coral') )

    return itemlist


def pornstars(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    matches = re.compile('<a class="tcard".*?href="(.*?)".*?src="(.*?)".*?alt="(.*?)"', re.DOTALL).findall(data)

    for url, thumb, title in matches:
        itemlist.append(item.clone (action='list_all', title=title, url=url, thumbnail=thumb, text_color='orange' ))

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
        url = host + 'release-year/' + str(x) + '/'

        itemlist.append(item.clone( title=str(x), url=url, action='list_all', text_color = 'orange' ))

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

        title = title.replace('&#8217;s', "'s").replace('&#8217;t', "'t").replace('&#8211;', '').replace('&amp;', '&').replace('&#038;', '').strip()

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        titulo = title

        time = scrapertools.find_single_match(match, '<span class="card__dur">(.*?)</span>').strip()

        if time: titulo = "[COLOR tan]%s[/COLOR] %s" % (time, title)

        itemlist.append(item.clone (action='findvideos', title=titulo, url=url, thumbnail=thumb,
                                    contentType = 'movie', contentTitle = title, contentExtra='adults') )

    if itemlist:
        if 'Previous<' in data:
            next_page = scrapertools.find_single_match(data, '"Pagination".*?Previous<.*?href="(.*?)"')
        else:
            next_page = scrapertools.find_single_match(data, '"Pagination".*?href="(.*?)"')

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

    bloque = scrapertools.find_single_match(data, 'data-servers="(.*?)</div></div></div>')

    matches = scrapertools.find_multiple_matches(bloque, '&quot;u&quot;:&quot;(.*?)&quot;')

    ses = 0

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
            itemlist.append(Item( channel = item.channel, action='play', title='', url=url, server=servidor, ref=ref,
                                  language = 'Vo', other = other.capitalize(), force_input=force_input ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def play(item):
    logger.info()
    itemlist = []

    url = item.url

    if url:
        if item.server == 'directo':
            new_server = servertools.corregir_other(url).lower()
            if new_server.startswith("http"):
                if not config.get_setting('developer_mode', default=False): return itemlist
            servidor = new_server

        itemlist.append(item.clone(url = url, server = item.server))

    return itemlist


def search(item, texto):
    logger.info()
    try:
        config.set_setting('search_last_video', texto)

        item.url = "%ssearch/%s" % (host, texto.replace(" ", "+"))
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


