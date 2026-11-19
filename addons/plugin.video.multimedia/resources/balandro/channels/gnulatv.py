# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb


# ~  29/10/2026  las búsquedas dan CloudFlare Protection

host = 'https://ver.gnula.one/'


perpage = 21


def item_configurar_proxies(item):
    color_list_proxies = config.get_setting('channels_list_proxies_color', default='red')

    color_avis = config.get_setting('notification_avis_color', default='yellow')
    color_exec = config.get_setting('notification_exec_color', default='cyan')

    context = []

    tit = '[COLOR %s]Información proxies[/COLOR]' % color_avis
    context.append({'title': tit, 'channel': 'helper', 'action': 'show_help_proxies'})

    if config.get_setting('channel_gnulatv_proxies', default=''):
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


def do_downloadpage(url, post=None):
    # ~ por si viene de enlaces guardados
    ant_hosts = ['https://www2.gnula.one/']

    for ant in ant_hosts:
        url = url.replace(ant, host)

    hay_proxies = False
    if config.get_setting('channel_gnulatv_proxies', default=''): hay_proxies = True

    timeout = None
    if host in url:
        if hay_proxies: timeout = config.get_setting('channels_repeat', default=30)

    if not url.startswith(host):
        data = httptools.downloadpage(url, post=post, timeout=timeout).data
    else:
        if hay_proxies:
            data = httptools.downloadpage_proxy('gnulatv', url, post=post, timeout=timeout).data
        else:
            data = httptools.downloadpage(url, post=post, timeout=timeout).data

    if config.get_setting('developer_team'):
        if '/?s=' in url:
            if '<title>Just a moment...</title>' in data:
                platformtools.dialog_notification('Team - GnulaTv', '[COLOR red][B]CloudFlare[COLOR orangered] Protection[/B][/COLOR]')
                return ''

    return data


def acciones(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( channel='submnuctext', action='_test_webs', title='Test Web del canal [COLOR yellow][B] ' + host + '[/B][/COLOR]',
                                from_channel='GnulaTv', folder=False, text_color='chartreuse' ))

    itemlist.append(Item( channel='helper', action='show_help_gnulatv', title='[COLOR aquamarine][B]Aviso[/COLOR] [COLOR green]Información[/B][/COLOR] canal', thumbnail=config.get_thumb('gnulatv') ))

    itemlist.append(item_configurar_proxies(item))

    platformtools.itemlist_refresh()

    return itemlist


def mainlist(item):
    return mainlist_pelis(item)


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'peliculas/' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por idioma', action = 'idiomas', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host + 'generos/')
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Lista de géneros<(.*?)</ul>')

    matches = re.compile('<a href="(.*?)".*?<strong>(.*?)</strong>', re.DOTALL).findall(bloque)

    for url, title in matches:
        if 'Series' in title: continue

        title = title.replace('&amp;', '&')

        title = title.strip()

        if title == 'Estreno': continue
        elif title == 'Recomendada': continue
        elif title == 'News': continue

        itemlist.append(item.clone( title=title, url=url, action='list_all', genre = title, text_color = 'deepskyblue' ))

    return sorted(itemlist, key=lambda it: it.title)


def idiomas(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Castellano', action = 'list_all', url = host + 'peliculas/castellano/', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Latino', action = 'list_all', url = host + 'peliculas/latino/', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Subtitulado', action = 'list_all', url = host + 'peliculas/subtitulado/', text_color = 'deepskyblue' ))

    return itemlist


def anios(item):
    logger.info()
    itemlist = []

    from datetime import datetime
    current_year = int(datetime.today().year)

    for x in range(current_year, 1939, -1):
        url = host + 'release/' + str(x) + '/'

        itemlist.append(item.clone( title=str(x), url=url, action='list_all', any = str(x), text_color = 'deepskyblue' ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    if not item.page: item.page = 0

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Peliculas<(.*?)</section>')

    if not bloque:
        if item.any:
            bloque = scrapertools.find_single_match(data, '>Estrenos ' + str(item.any) + '(.*?)</section>')
        else:
            bloque = scrapertools.find_single_match(data, '>' + item.genre + '(.*?)</section>')

    matches = re.compile('<a(.*?)</span></a>', re.DOTALL).findall(bloque)

    num_matches = len(matches)

    for match in matches[item.page * perpage:]:
        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        title = scrapertools.find_single_match(match, 'alt="(.*?)"')

        if not title: title = scrapertools.find_single_match(match, 'title="(.*?)"')

        if not url or not title: continue

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        title = title.replace('&#8217;', "'")

        if " [" in title: title = title.split(" [")[0]

        title = title.strip()

        year = scrapertools.find_single_match(match, '<span class="gn-card__y">(.*?)</span>')
        if not year: year = '-'
        else:
           title = title.replace('(' + year + ')', '').strip()

        langs = []
        if 'CAS"' in match: langs.append('Esp')
        if 'LAT' in match: langs.append('Lat')
        if 'SUB' in match: langs.append('Vose')

        itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, languages=', '.join(langs),
                                    contentType='movie', contentTitle=title, infoLabels={'year': year} ))

        if len(itemlist) >= perpage: break

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        buscar_next = True
        if num_matches > ((item.page + 1) * perpage):
            itemlist.append(item.clone( title='Siguientes ...', page=item.page + 1, action='list_all', text_color='coral' ))
            buscar_next = False

        if buscar_next:
            next_page = scrapertools.find_single_match(data, '<nav class="navigation.*?class="page-numbers current">.*?href="(.*?)".*?</a>')

            if next_page:
                if '/page/' in next_page:
                    itemlist.append(item.clone( title = 'Siguientes ...', url = next_page, action = 'list_all',
                                                page = 0, text_color='coral' ))

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


def search(item, texto):
    logger.info()
    try:
        item.url = host + '?s=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
