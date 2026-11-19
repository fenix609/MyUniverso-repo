# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools


host = 'https://www.cumlouder.com'


def do_downloadpage(url, post=None, headers=None):
    timeout = None
    if host in url: timeout = config.get_setting('channels_repeat', default=30)

    data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data

    if not data:
        if url.startswith(host):
            if not '/search?q=' in url:
                if config.get_setting('channels_re_charges', default=True): platformtools.dialog_notification('CumLouder', '[COLOR cyan]Re-Intentanto acceso[/COLOR]')

                timeout = config.get_setting('channels_repeat', default=30)

                httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data

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

    itemlist.append(item.clone( title = 'Buscar vídeo ...', action = 'search', search_type = 'movie', search_video = 'adult', text_color='orange' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all' ))

    itemlist.append(item.clone( title = 'Últimos', action = 'list_all', url = host + '/2/', page = 1, text_color = 'cyan' ))

    itemlist.append(item.clone( title = 'Por colección', action = 'colecciones' ))

    itemlist.append(item.clone( title = 'Por canal', action = 'canales' ))
    itemlist.append(item.clone( title = 'Por categoría', action = 'categorias' ))
    itemlist.append(item.clone( title = 'Por estrella', action = 'pornstars', ))

    return itemlist


def colecciones(item):
    logger.info()
    itemlist = []

    if not item.page:
        item.page = 0
        item.url = host + '/series/'

    data = do_downloadpage(item.url)

    patron = '<div itemprop="itemListElement".*?href="([^"]+)".*?data-src="([^"]+)".*?h2 itemprop="name">([^<]+).*?p>'

    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, thumb, title, in matches:
        title = title.lower().capitalize()

        itemlist.append(item.clone( action = 'list_all', url = url, thumbnail = thumb, title = title, page = 1, text_color = 'pink' ))

    if itemlist:
        next_url = scrapertools.find_single_match(data, '<a class="btn-pagination".*?itemprop="name".*?href="(.*?)"')

        if next_url:
            next_url = host + next_url

            itemlist.append(item.clone( title = 'Siguientes ...', url = next_url, page = item.page + 1, action = 'colecciones', text_color = 'coral' ))

    return itemlist


def canales(item):
    logger.info()
    itemlist = []

    if not item.page:
        item.page = 0
        item.url = host + '/channels/'

    data = do_downloadpage(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)

    patron = '<a channel-url=.*?href="([^"]+)".*?data-src="([^"]+)".*?alt="([^"]+)"'

    matches = scrapertools.find_multiple_matches(data, patron)

    for url, thumb, title, in matches:
        url = host + url + '?show=channels'

        if not thumb.startswith('http'): thumb = 'https:' + thumb

        itemlist.append(item.clone( action = 'list_all', url = url, title = title, thumbnail = thumb, page = 1, text_color = 'violet' ))

    if itemlist:
        next_url = scrapertools.find_single_match(data, '<a class="btn-pagination".*?temprop="name".*?href="(.*?)"')

        if next_url:
            next_url = host + next_url

            itemlist.append(item.clone( title = 'Siguientes ...', url = next_url, page = item.page + 1, action = 'canales', text_color = 'coral' ))

    return itemlist


def categorias(item):
    logger.info()
    itemlist = []

    if not item.page:
        item.page = 0
        item.url = host + '/categories/'

    data = do_downloadpage(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)

    patron = '<a tag-url=.*?href="([^"]+)".*?data-src="([^"]+)".*?alt="([^"]+)"'

    matches = scrapertools.find_multiple_matches(data, patron)

    for url, thumb, title in matches:
        url = host + url

        if not thumb.startswith('http'): thumb = 'https:' + thumb

        itemlist.append(item.clone( action = 'list_all', url = url, title = title, thumbnail = thumb, page = 1, text_color='moccasin' ))

    if itemlist:
        next_url = scrapertools.find_single_match(data, '<a class="btn-pagination".*?itemprop="name".*?href="(.*?)"')

        if next_url:
            next_url = host + next_url

            itemlist.append(item.clone( title = 'Siguientes ...', url = next_url, page = item.page + 1, action = 'categorias', text_color = 'coral' ))

    return itemlist


def pornstars(item):
    logger.info()
    itemlist = []

    if not item.page:
        item.page = 0
        item.url = host + '/girls/'

    data = do_downloadpage(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)

    patron = 'class="muestra-escena muestra-pornostar show-girl" href="([^"]+)".*?data-src="([^"]+)".*?alt="([^"]+)"'

    matches = scrapertools.find_multiple_matches(data, patron)

    for url, thumb, title in matches:
        url = host + url

        itemlist.append(item.clone( action = 'list_all', url = url, thumbnail = thumb, title = title, page = 1, text_color='orange' ))

    if itemlist:
        next_url = scrapertools.find_single_match(data, '<a class="btn-pagination".*?itemprop="name".*?href="(.*?)"')

        if next_url:
            next_url = host + next_url

            itemlist.append(item.clone( title = 'Siguientes ...', url = next_url, page = item.page + 1, action = 'pornstars', text_color = 'coral' ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    if not item.page:
        item.page = 0
        item.url = host + '/porn/'

    data = do_downloadpage(item.url)
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)

    patron = '<a class="muestra-escena" href="([^"]+)".*?data-src="([^"]+)".*?alt="([^"]+)".*?<span class="ico-minutos sprite"></span>([^<]+)</span>(.*?)</a>'

    matches = scrapertools.find_multiple_matches(data, patron)

    for url, thumb, title, time, qlty in matches:
        url = host + url

        if not thumb.startswith('http'): thumb = 'https:' + thumb

        thumb = thumb.replace('ep1.jpg', 'ep.jpg')

        title = title.replace('&#039;s', "'s").strip()

        time = time.replace(' m', '').strip()

        titulo = "[COLOR tan]%s[/COLOR] %s" % (time, title)

        itemlist.append(item.clone( action = 'findvideos', url = url, title = titulo, thumbnail = thumb, quality = qlty,
                                    contentType = 'movie', contentTitle = title, contentExtra='adults' ))

    if itemlist:
        next_url = scrapertools.find_single_match(data, '<a class="btn-pagination".*?itemprop="name".*?href="(.*?)"')

        if next_url:
            next_url = host + next_url

            itemlist.append(item.clone( title = 'Siguientes ...', url = next_url, page = item.page + 1, action = 'list_all', text_color = 'coral' ))

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

    patron = '''<source src="([^"]+).*?res='([^']+)'''

    matches = scrapertools.find_multiple_matches(data, patron)
    if not matches: matches = scrapertools.find_multiple_matches(data, '<source src="(.*?)".*?res="(.*?)"')

    for url, qlty in matches:
        url = url.replace("&amp;", "&")

        itemlist.append(Item( channel = item.channel, action = 'play', server = 'directo', quality = qlty, url = url, language = 'Vo' ))

    return itemlist


def _lasts(item):
    logger.info()

    item.url = host + '/2/'
    item.page = 1

    return list_all(item)


def search(item, texto):
    logger.info()
    try:
        config.set_setting('search_last_video', texto)

        item.url =  host + "/es/buscar/?q=%s" % (texto.replace(" ", "+"))
        item.page = 1
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
