# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools


host = 'https://watchpornfree.info/'


def do_downloadpage(url, post=None, headers=None):
    timeout = None
    if host in url: timeout = config.get_setting('channels_repeat', default=30)

    raise_weberror = True
    if 'release-year/' in url: raise_weberror = False

    data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout, raise_weberror=raise_weberror).data

    if not data:
        if url.startswith(host):
            if not '/?s' in url:
                if config.get_setting('channels_re_charges', default=True): platformtools.dialog_notification('WatchPornFree', '[COLOR cyan]Re-Intentanto acceso[/COLOR]')

                timeout = config.get_setting('channels_repeat', default=30)

                data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout, raise_weberror=raise_weberror).data

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

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host + 'most-popular' ))

    itemlist.append(item.clone( title = 'Más valorados', action = 'list_all', url = host + 'best-hd-porn' ))

    itemlist.append(item.clone( title = 'Películas', action = 'list_all', url = host + 'full-hd-movies', text_color = 'deepskyblue' ))

    itemlist.append(item.clone( title = 'Por estudio', url = host + 'porn-studios',action = 'estudios' ))

    itemlist.append(item.clone( title = 'Por estrella', url = host + 'porn-stars', action = 'pornstars' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios' ))

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
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', '', data)

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

    for x in range(current_year, 1999, -1):
        url = host + 'release-year/' + str(x)

        itemlist.append(item.clone( title = str(x), url = url, action = 'list_all', text_color='orange' ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    if not item.page: item.page = 0

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', '', data)

    matches = re.compile('<article(.*?)</article>', re.DOTALL).findall(data)

    for match in matches:
        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        title = scrapertools.find_single_match(match, 'alt="(.*?)"')

        if not url or not title: continue

        title = title.replace('Watch', '').replace('Porn Online Free', '').strip()

        title = title.replace('&amp;', '').strip()

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        titulo = title

        time = scrapertools.find_single_match(match, '<span class="card__dur">(.*?)</span>').strip()

        if time: titulo = "[COLOR tan]%s[/COLOR] %s" % (time, title)

        itemlist.append(item.clone (action='findvideos', title=titulo, url=url, thumbnail=thumb, contentType = 'movie', contentTitle = title, contentExtra='adults') )

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
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', '', data)

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
        elif 'vev.io' in url: continue
        elif '/rapidgator.' in url: continue
        elif '/uploaded.' in url: continue
        elif '/nitro.' in url: continue
        elif '/ddownload.' in url: continue
        elif '/nitroflare.' in url: continue
        elif '/katfile.' in url: continue
        elif '/fikper.' in url: continue
        elif '/turbobit.' in url: continue

        elif '/frdl.' in url: continue
        elif '/hitfile.' in url: continue

        url = url.replace('/filemoon.sx/download/', '/filemoon.sx/d/')

        servidor = servertools.get_server_from_url(url)

        other = ''

        if servidor == 'various': other = servertools.corregir_other(url)
        elif servidor == 'zures': other = servertools.corregir_zures(url)

        itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url,
                              language = 'Vo', other = other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def play(item):
    logger.info()
    itemlist = []

    url = item.url

    servidor = item.server

    if item.server == 'directo':
        data = do_downloadpage(item.url)

        url = scrapertools.find_single_match(data, '<source src="(.*?)"')

        if not url: return itemlist

        servidor = servertools.get_server_from_url(url)

    itemlist.append(item.clone(server = servidor, url = url))

    return itemlist


def search(item, texto):
    logger.info()
    try:
        config.set_setting('search_last_video', texto)

        item.url =  host + '?s=%s' % (texto.replace(" ", "+"))
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
