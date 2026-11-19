# -*- coding: utf-8 -*-

import re

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb


# ~  26/10/2026  solo carga la Temporada 1 y las búsquedas dan CloudFlare Protection

host = 'https://ver.seriesgato.pw/'


def item_configurar_proxies(item):
    color_list_proxies = config.get_setting('channels_list_proxies_color', default='red')

    color_avis = config.get_setting('notification_avis_color', default='yellow')
    color_exec = config.get_setting('notification_exec_color', default='cyan')

    context = []

    tit = '[COLOR %s]Información proxies[/COLOR]' % color_avis
    context.append({'title': tit, 'channel': 'helper', 'action': 'show_help_proxies'})

    if config.get_setting('channel_seriesgato_proxies', default=''):
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
    ant_hosts = ['https://vip.seriesgato.pw']

    for ant in ant_hosts:
        url = url.replace(ant, host)

    hay_proxies = False
    if config.get_setting('channel_seriesgato_proxies', default=''): hay_proxies = True

    timeout = None
    if host in url:
        if hay_proxies: timeout = config.get_setting('channels_repeat', default=30)

    if not url.startswith(host):
        data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data
    else:
        if hay_proxies:
            data = httptools.downloadpage_proxy('seriesgato', url, post=post, headers=headers, timeout=timeout).data
        else:
            data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data

        if not data:
            if not '/?s=' in url:
                if config.get_setting('channels_re_charges', default=True): platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Re-Intentando acceso[/COLOR]')

                timeout = config.get_setting('channels_repeat', default=30)

                if hay_proxies:
                    data = httptools.downloadpage_proxy('seriesgato', url, post=post, headers=headers, timeout=timeout).data
                else:
                    data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data

    if config.get_setting('developer_team'):
        if '/?s=' in url:
            if '<title>Just a moment...</title>' in data:
                platformtools.dialog_notification('Team - SeriesGato', '[COLOR red][B]CloudFlare[COLOR orangered] Protection[/B][/COLOR]')
                return ''

    return data


def acciones(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( channel='submnuctext', action='_test_webs', title='Test Web del canal [COLOR yellow][B] ' + host + '[/B][/COLOR]',
                                from_channel='seriesgato', folder=False, text_color='chartreuse' ))

    itemlist.append(Item( channel='helper', action='show_help_seriesgato', title='[COLOR aquamarine][B]Aviso[/COLOR] [COLOR green]Información[/B][/COLOR] canal', thumbnail=config.get_thumb('seriesgato') ))

    itemlist.append(item_configurar_proxies(item))

    platformtools.itemlist_refresh()

    return itemlist


def mainlist(item):
    return mainlist_series(item)


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow', text_color = 'hotpink' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'series/', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Últimos episodios', action = 'last_epis', url = host + 'nuevos-episodios/', search_type = 'tvshow', text_color = 'cyan' ))

    return itemlist


def last_epis(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Nuevos episodios<(.*?)>&copy;')

    matches = re.compile('<article(.*?)</article>', re.DOTALL).findall(bloque)

    if not matches: matches = scrapertools.find_multiple_matches(bloque, '<a class="pw-ecard"(.*?)</a>')

    for match in matches:
        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        title = scrapertools.find_single_match(match, '<span class="pw-ecard__series">(.*?)</span>')

        if not url or not title: continue

        season = scrapertools.find_single_match(match, '<span class="pw-ecard__se">T(.*?)E').strip()
        if not season: season = 1

        epis = scrapertools.find_single_match(match, '<span class="pw-ecard__se">.*?E(.*?)</span>').strip()
        if not epis: epis = 1

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        tit_epis = scrapertools.find_single_match(match, '<span class="pw-ecard__title">(.*?)</span>')

        title = title.replace('Season', '[COLOR tan]Temp.[/COLOR]')

        titulo = '[COLOR goldenrod]Epis. [/COLOR]' + str(season) + 'x' + str(epis) + ' ' + title.replace('Capítulo ' + str(epis), '').replace('Capitulo ' + str(epis), '').strip()

        titulo += ' ' + tit_epis.replace('Episodio ', '[COLOR goldenrod]Epis. [/COLOR]').replace('episodio ','[COLOR goldenrod]Epis. [/COLOR]').replace('Capítulo ', '[COLOR goldenrod]Epis. [/COLOR]').replace('capítulo ','[COLOR goldenrod]Epis. [/COLOR]')

        itemlist.append(item.clone( action='findvideos', url = url, title = titulo, thumbnail=thumb,
                                    contentSerieName = title, contentType = 'episode',
                                    contentSeason = season, contentEpisodeNumber=epis, infoLabels={'year':'-'} ))

    if itemlist:
        next_page: next_page = scrapertools.find_single_match(data, '<nav class="pw-pagination".*?class="page-numbers current">.*?href="(.*?)".*?</main>')

        if next_page:
            if '/page/' in next_page:
                itemlist.append(item.clone( title = 'Siguientes ...', action='last_epis', url = next_page, text_color='coral' ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '</h1>(.*?)>&copy;')

    matches = scrapertools.find_multiple_matches(bloque, '<article(.*?)</article>')

    if not matches: matches = scrapertools.find_multiple_matches(bloque, '<a class="pw-card"(.*?)</a>')

    for match in matches:
        title = scrapertools.find_single_match(match, '<h3 class="Title">(.*?)</h3>').strip()

        if not title: title = scrapertools.find_single_match(match, '<span class="pw-card__title">(.*?)</span>')

        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        if not title or not url: continue

        thumb = scrapertools.find_single_match(match, '<img src="(.*?)"')

        if not thumb: thumb = scrapertools.find_single_match(match, 'data-src="(.*?)"')

        title = title.replace('&#8217;s', "'s").replace('&#039;', "'").replace('&#038;', '&').replace('&amp;', '&').strip()

        year = scrapertools.find_single_match(match, '<span class="Year">(.*?)</span>')
        if not year: year = '-'

        itemlist.append(item.clone( action='temporadas', url = url, title = title, thumbnail = thumb,
                                    contentType='tvshow', contentSerieName=title, infoLabels = {'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        next_page = scrapertools.find_single_match(data, '<div class="wp-pagenavi">.*?<a class="next page-numbers".*?href="(.*?)".*?</main>')

        if not next_page: next_page = scrapertools.find_single_match(data, '<nav class="pw-pagination".*?class="page-numbers current">.*?href="(.*?)".*?</main>')
        if next_page:
            if '/page/' in next_page:
                itemlist.append(item.clone( title = 'Siguientes ...', action='list_all', url = next_page, text_color='coral' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    matches = scrapertools.find_multiple_matches(data, 'data-pw-season="(.*?)"')

    if not matches: matches = scrapertools.find_multiple_matches(data, '<span class="pw-seasons__one">Temporada(.*?)</span>')

    for season in matches:
        season = season.strip()

        title = 'Temporada ' + season

        if len(matches) == 1:
            if config.get_setting('channels_seasons', default=True):
                platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'solo [COLOR tan]' + title + '[/COLOR]')

                item.page = 0
                item.contentType = 'season'
                item.contentSeason = season
                itemlist = episodios(item)
                return itemlist


        itemlist.append(item.clone( action = 'episodios', title = title, page = 0,
                                    contentType = 'season', contentSeason = season, text_color = 'tan' ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def episodios(item):
    logger.info()
    itemlist = []

    if not item.page: item.page = 0
    if not item.perpage: item.perpage = 50

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    _serie = scrapertools.find_single_match(data, 'data-series="(.*?)"')

    if not _serie: return itemlist

    if str(item.contentSeason) == '1':
        bloque = scrapertools.find_multiple_matches(data, 'data-season="(.*?)</section>')

        matches = scrapertools.find_multiple_matches(data, '<li class="pw-epitem">(.*?)</li>')
    else:
        headers = {'Referer': item.url}

        data = do_downloadpage(host + 'wp-json/pw/v1/season?series=' + _serie + '&s' + str(item.contentSeason), headers = headers)

        data = data.replace('}]}', '},')

        matches = scrapertools.find_multiple_matches(data, '"id":(.*?)},')

    if item.page == 0 and item.perpage == 50:
        sum_parts = len(matches)

        try:
            tvdb_id = scrapertools.find_single_match(str(item), "'tvdb_id': '(.*?)'")
            if not tvdb_id: tvdb_id = scrapertools.find_single_match(str(item), "'tmdb_id': '(.*?)'")
        except: tvdb_id = ''

        if config.get_setting('channels_charges', default=True):
            item.perpage = sum_parts
            if sum_parts >= 100:
                platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
        elif tvdb_id:
            if sum_parts > 50:
                platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando Todos los elementos[/COLOR]')
                item.perpage = sum_parts
        else:
            item.perpage = sum_parts

            if sum_parts >= 1000:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]500[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando 500 elementos[/COLOR]')
                    item.perpage = 500

            elif sum_parts >= 500:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]250[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando 250 elementos[/COLOR]')
                    item.perpage = 250

            elif sum_parts >= 250:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]125[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando 125 elementos[/COLOR]')
                    item.perpage = 125

            elif sum_parts >= 125:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]75[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando 75 elementos[/COLOR]')
                    item.perpage = 75

            elif sum_parts > 50:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos [COLOR cyan][B]Todos[/B][/COLOR] de una sola vez ?'):
                    platformtools.dialog_notification('SeriesGato', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
                    item.perpage = sum_parts
                else: item.perpage = 50

    for match in matches[item.page * item.perpage:]:
        url = scrapertools.find_single_match(match, '"url":"(.*?)"')

        if not url: url = scrapertools.find_single_match(match, '<a href="(.*?)"')

        if not url: continue

        url = url.replace('\\/', '/')

        title = scrapertools.find_single_match(match, '"name":"(.*?)"')

        if not title: title = scrapertools.find_single_match(match, '<strong class="pw-epitem__title">(.*?)</strong>')

        epis = scrapertools.find_single_match(match, '"label":"T.*?E(.*?)"')

        if not epis: epis = scrapertools.find_single_match(match, '<span class="pw-epitem__se">T.*?E(.*?)</span>')

        if not epis: epis = 1

        thumb = scrapertools.find_single_match(match, '"still":"(.*?)"')

        if not thumb: thumb = scrapertools.find_single_match(match, '<img src="(.*?)"')

        thumb = thumb.replace('\\/', '/')

        title = title.replace('Episodio ', '[COLOR goldenrod]Epis. [/COLOR]').replace('episodio ','[COLOR goldenrod]Epis. [/COLOR]')

        if 'Epis. ' in title: title = title + ' ' + item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'")

        titulo = str(item.contentSeason) + 'x' + str(epis) + ' ' + title

        itemlist.append(item.clone( action='findvideos', url = url, thumbnail = thumb, title = titulo,
                                    contentType = 'episode', contentSeason = item.contentSeason, contentEpisodeNumber = epis ))

        if len(itemlist) >= item.perpage:
            break

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        if len(matches) > ((item.page + 1) * item.perpage):
            itemlist.append(item.clone( title = "Siguientes ...", action = "episodios", page = item.page + 1, perpage = item.perpage, text_color='coral' ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    _player = scrapertools.find_single_match(data, 'data-player>.*?<iframe.*?src="(.*?)".*?</iframe>')

    if not _player: return itemlist

    data = do_downloadpage(_player)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    matches = scrapertools.find_multiple_matches(str(data), '<li>(.*?)</li>')

    ses = 0

    for match in matches:
        ses += 1

        if 'Castellano' in match: lang = 'Esp'
        elif 'Latino' in match: lang = 'Lat'
        elif 'Subtitulado' in match: lang = 'Vose'
        else: lang = '?'

        url = scrapertools.find_single_match(match, 'data-src="(.*?)"')

        if not url: continue

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


def _epis(item):
    logger.info()

    item.url = host + 'nuevos-episodios/'
    item.search_type = 'tvshow'

    return last_epis(item)


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
