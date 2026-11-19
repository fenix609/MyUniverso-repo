# -*- coding: utf-8 -*-

import re, base64

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb


# ~  30/10/2026  las búsquedas dan CloudFlare Protection

host = 'https://ver.ikucomics.net/'


def item_configurar_proxies(item):
    color_list_proxies = config.get_setting('channels_list_proxies_color', default='red')

    color_avis = config.get_setting('notification_avis_color', default='yellow')
    color_exec = config.get_setting('notification_exec_color', default='cyan')

    context = []

    tit = '[COLOR %s]Información proxies[/COLOR]' % color_avis
    context.append({'title': tit, 'channel': 'helper', 'action': 'show_help_proxies'})

    if config.get_setting('channel_ikucomics_proxies', default=''):
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
    ant_hosts = ['https://vip.ikucomics.net/']

    for ant in ant_hosts:
        url = url.replace(ant, host)

    hay_proxies = False
    if config.get_setting('channel_ikucomics_proxies', default=''): hay_proxies = True

    timeout = None
    if host in url:
        if hay_proxies: timeout = config.get_setting('channels_repeat', default=30)

    if not url.startswith(host):
        data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data
    else:
        if hay_proxies:
            data = httptools.downloadpage_proxy('ikucomics', url, post=post, headers=headers, timeout=timeout).data
        else:
            data = httptools.downloadpage(url, post=post, headers=headers, timeout=timeout).data

        if not data:
            if not '/?s=' in url:
                if config.get_setting('channels_re_charges', default=True): platformtools.dialog_notification('IkuComics', '[COLOR cyan]Re-Intentando acceso[/COLOR]')

                timeout = config.get_setting('channels_repeat', default=30)

                if hay_proxies:
                    data = httptools.downloadpage_proxy('ikucomics', url, post=post, headers=headers, timeout=timeout).data
                else:
                    data = httptools.downloadpage(url, post=post, timeout=timeout).data

    if config.get_setting('developer_team'):
        if '/?s=' in url:
            if '<title>Just a moment...</title>' in data:
                platformtools.dialog_notification('Team - IkuComics', '[COLOR red][B]CloudFlare[COLOR orangered] Protection[/B][/COLOR]')
                return ''

    return data


def acciones(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( channel='submnuctext', action='_test_webs', title='Test Web del canal [COLOR yellow][B] ' + host + '[/B][/COLOR]',
                                from_channel='ikucomics', folder=False, text_color='chartreuse' ))

    itemlist.append(Item( channel='helper', action='show_help_ikucomics', title='[COLOR aquamarine][B]Aviso[/COLOR] [COLOR green]Información[/B][/COLOR] canal', thumbnail=config.get_thumb('ikucomics') ))

    itemlist.append(item_configurar_proxies(item))

    platformtools.itemlist_refresh()

    return itemlist


def mainlist(item):
    return mainlist_series(item)


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( action='acciones', title= '[B]Acciones[/B] [COLOR plum](si no hay resultados)[/COLOR]', text_color='goldenrod' ))

    itemlist.append(item.clone( title = 'Buscar anime ...', action = 'search', search_type = 'tvshow', text_color = 'springgreen' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'series/', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Últimos episodios', action = 'last_epis', url = host, search_type = 'tvshow', text_color = 'cyan' ))

    itemlist.append(item.clone( title = 'En emisión', action = 'list_all', url = host + 'directorio/?status=airing', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Finalizados', action = 'list_all', url = host + 'directorio/?status=finished', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Recientes', action = 'list_all', url = host + 'directorio/?sort=recent', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host + 'directorio/?sort=popular', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Más valorados', action = 'list_all', url = host + 'directorio/?sort=score', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Películas', action = 'list_all', url = host + 'movies/', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host + 'directorio/')

    bloque = scrapertools.find_single_match(data, '>Géneros</span>(.*?)</details>')

    matches = scrapertools.find_multiple_matches(bloque, 'value="(.*?)".*?data-name="(.*?)"')

    for val, title in matches:
        title = title.replace('&amp;', '&').strip()

        url = host + 'directorio' + '?genre=' + val

        itemlist.append(item.clone( action = 'list_all', title = title, url = url, text_color = 'springgreen' ))

    return itemlist


def anios(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(host + 'directorio/')

    bloque = scrapertools.find_single_match(data, '>Año<(.*?)</select>')

    matches = scrapertools.find_multiple_matches(bloque, '<option value="(.*?)"')

    for val in matches:
        if not val: continue

        url = host + 'directorio' + '?year=' + val

        itemlist.append(item.clone( action = 'list_all', title = val, url = url, text_color = 'springgreen' ))

    return itemlist


def last_epis(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Últimos capítulos</h2>(.*?)</section>')

    matches = re.compile('data-jk-ep="(.*?)</svg></span></a>', re.DOTALL).findall(bloque)

    for match in matches:
        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        title = scrapertools.find_single_match(match, 'aria-label="(.*?)"')

        if not url or not title: continue

        season = 1

        if 'Temporada' in title or 'Season' in title:
            if '2nd' in title: season = 2
            elif '3rd' in title: season = 3
            elif '4th' in title: season = 4
            elif '5th' in title: season = 5
            elif '6th' in title: season = 6
            elif '7th' in title: season = 7
            elif '8th' in title: season = 8
            elif '9th' in title: season = 9
            else:
               season = scrapertools.find_single_match(title, 'Temporada (.*?) ').strip()
               if not season: season = scrapertools.find_single_match(title, 'Season(.*?)Episodio').strip()
               if not season: season = scrapertools.find_single_match(title, 'Season(.*?)$').strip()

               if not season: season = 1

        SerieName = corregir_SerieName(title)

        epis = scrapertools.find_single_match(match, '<span class="jk-ecard__num">EP(.*?)</span>').strip()
        if not epis: epis = 1

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        title = title.replace('Season', '[COLOR tan]Temp.[/COLOR]')

        titulo = '[COLOR goldenrod]Epis. [/COLOR]' + str(season) + 'x' + str(epis) + ' ' + title.replace('Capítulo ' + str(epis), '').replace('Capitulo ' + str(epis), '').strip()

        if url:
            itemlist.append(item.clone( action='findvideos', url = url, title = titulo, thumbnail=thumb,
                                        contentSerieName = SerieName, contentType = 'episode',
                                        contentSeason = season, contentEpisodeNumber=epis, infoLabels={'year':'-'} ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '</h1>(.*?)>Explorar<')

    matches = scrapertools.find_multiple_matches(bloque, '<article(.*?)</article>')

    for match in matches:
        title =  scrapertools.find_single_match(match, 'aria-label="(.*?)"').strip()

        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        if not title or not url: continue

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        season = 1

        if 'Temporada' in title or 'Season' in title:
            if '2nd' in title: season = 2
            elif '3rd' in title: season = 3
            elif '4th' in title: season = 4
            elif '5th' in title: season = 5
            elif '6th' in title: season = 6
            elif '7th' in title: season = 7
            elif '8th' in title: season = 8
            elif '9th' in title: season = 9
            else:
               season = scrapertools.find_single_match(title, 'Temporada (.*?) ').strip()
               if not season: season = scrapertools.find_single_match(title, 'Season(.*?)Episodio').strip()
               if not season: season = scrapertools.find_single_match(title, 'Season(.*?)$').strip()

               if not season: season = 1

        title = title.replace('&#8217;s', "'s").replace('&#039;', "'").replace('&#038;', '&').replace('&amp;', '&').replace('&#8211;', '').strip()

        SerieName = corregir_SerieName(title)

        if '>Película' in match:
            year = scrapertools.find_single_match(match, '<p class="jk-card__meta">.*?·(.*?)</p>').strip()
        else:
            year = scrapertools.find_single_match(match, '<p class="jk-card__meta">.*?·(.*?)·').strip()

        if not year: year = '-'

        title = title.replace('Season', '[COLOR tan]Temp.[/COLOR]')

        tipo = 'movie' if '/movies/' in url else 'tvshow'
        sufijo = '' if item.search_type != 'all' else tipo

        if tipo == 'movie':
            if not item.search_type == "all":
                if item.search_type == "tvshow": continue

            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, fmt_sufijo=sufijo,
                                        contentType = 'movie', contentTitle = title, infoLabels={'year': year} ))

        if tipo == 'tvshow':
            if not item.search_type == "all":
                if item.search_type == "movie": continue

            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName = SerieName, contentSeason = season, infoLabels = {'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        next_page = scrapertools.find_single_match(data, '<nav class="jk-pagination".*?class="page-numbers current">.*?href="(.*?)".*?</nav>')

        if next_page:
            next_page = next_page.replace('&#038;', '&')

            if '/page/' in next_page or '/?pg=' in next_page or '&pg=' in next_page:
                itemlist.append(item.clone( title = 'Siguientes ...', action='list_all', url = next_page, text_color='coral' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    if not 'aria-label="Temporadas">' in data:
        numtempo = 1

        if not 'data-jk-spanel="' in data:
            platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'sin [COLOR tan]Temporadas[/COLOR]')
        else:
            if config.get_setting('channels_seasons', default=True):
                numtempo = str(item.contentSeason)

                if not numtempo: numtempo = scrapertools.find_single_match(data, 'data-jk-spanel="(.*?)"')

                platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'solo [COLOR tan]Temporada ' + str(numtempo) + '[/COLOR]')

        item.contentType = 'season'
        item.contentSeason = 1
        item.numtempo = numtempo
        itemlist = episodios(item)
        return itemlist

    matches = scrapertools.find_multiple_matches(data, '<a class="jk-tabs__tab".*?href="(.*?)".*?data-jk-stab="(.*?)"')

    for url, season in matches:
        title = 'Temporada ' + season

        if len(matches) == 1:
            if config.get_setting('channels_seasons', default=True):
                platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'solo [COLOR tan]' + title + '[/COLOR]')

                item.page = 0
                item.contentType = 'season'
                item.contentSeason = season
                itemlist = episodios(item)
                return itemlist


        itemlist.append(item.clone( action = 'episodios', title = title, url = url, page = 0,
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

    if 'aria-label="Temporadas">' in data:
        bloque = scrapertools.find_single_match(data, 'data-jk-spanel="' + str(item.contentSeason) + '"(.*?)</div></div>')

        matches = scrapertools.find_multiple_matches(bloque, '<article(.*?)</article>')
    else:
        bloque = data

        matches = scrapertools.find_multiple_matches(bloque, '<li><a class="jk-num"(.*?)</li>')

        if not matches:
            bloque = scrapertools.find_single_match(data, 'data-jk-spanel="' + str(item.contentSeason) + '"(.*?)</div></div>')

            matches = scrapertools.find_multiple_matches(bloque, '<article(.*?)</article>')

    if item.page == 0 and item.perpage == 50:
        sum_parts = len(matches)

        try:
            tvdb_id = scrapertools.find_single_match(str(item), "'tvdb_id': '(.*?)'")
            if not tvdb_id: tvdb_id = scrapertools.find_single_match(str(item), "'tmdb_id': '(.*?)'")
        except: tvdb_id = ''

        if config.get_setting('channels_charges', default=True):
            item.perpage = sum_parts
            if sum_parts >= 100:
                platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
        elif tvdb_id:
            if sum_parts > 50:
                platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando Todos los elementos[/COLOR]')
                item.perpage = sum_parts
        else:
            item.perpage = sum_parts

            if sum_parts >= 1000:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]500[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando 500 elementos[/COLOR]')
                    item.perpage = 500

            elif sum_parts >= 500:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]250[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando 250 elementos[/COLOR]')
                    item.perpage = 250

            elif sum_parts >= 250:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]125[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando 125 elementos[/COLOR]')
                    item.perpage = 125

            elif sum_parts >= 125:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]75[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando 75 elementos[/COLOR]')
                    item.perpage = 75

            elif sum_parts > 50:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos [COLOR cyan][B]Todos[/B][/COLOR] de una sola vez ?'):
                    platformtools.dialog_notification('IkuComics', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
                    item.perpage = sum_parts
                else: item.perpage = 50

    for match in matches[item.page * item.perpage:]:
        numtempo = item.contentSeason
        if item.numtempo: numtempo = item.numtempo

        title = scrapertools.find_single_match(match, '<td class="MvTbTtl">.*?">(.*?)</a>')

        if not title: title = scrapertools.find_single_match(match, 'aria-label="(.*?)"')
        if not title: title = scrapertools.find_single_match(match, 'title="(.*?)"')

        url = scrapertools.find_single_match(match, 'href="(.*?)"')

        if not url or not title: continue

        epis = scrapertools.find_single_match(match, '<td><span class="Num">(.*?)</span>')

        if not epis: epis = scrapertools.find_single_match(match, 'data-num="(.*?)"')
        if not epis: epis = scrapertools.find_single_match(match, '<span class="jk-ecard__num">EP(.*?)</span>').strip()

        if not epis: epis = 1

        thumb = scrapertools.find_single_match(match, 'src="(.*?)"')

        title = title.replace('Episodio ', '[COLOR goldenrod]Epis. [/COLOR]').replace('episodio ','[COLOR goldenrod]Epis. [/COLOR]')

        if 'Epis. ' in title: title = title + ' ' + item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'")

        titulo = str(numtempo) + 'x' + str(epis) + ' ' + title

        itemlist.append(item.clone( action='findvideos', url = url, title = titulo, thumbnail = thumb,
                                    contentType = 'episode', contentSeason = numtempo, contentEpisodeNumber = epis ))

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

    options = scrapertools.find_multiple_matches(data, 'data-src="(.*?)"')

    ses = 0

    for opt in options:
        ses += 1

        try: _url = base64.b64decode(opt).decode("utf-8")
        except: _url = opt

        _url = _url.replace('/links.todomega.net/', '/ver.fiuxy2.com/')

        if '/ver.fiuxy2.com/' in _url:
           datap = do_downloadpage(_url)

           matches = scrapertools.find_multiple_matches(datap, '<li>(.*?)</li>')

           for match in matches:
               url = scrapertools.find_single_match(match, 'data-src="([^"]+)')

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

               elif 'lvturbo' in url: continue
               elif 'vanfem' in url: continue
               elif 'fembed' in url: continue
               elif 'fcom' in url: continue

               lang = '?'
               if 'Castellano' in match: lang = 'Esp'
               elif 'Latino' in match: lang = 'Lat'
               elif 'Subtitulado' in match: lang = 'Vose'

               if '/waaw.in/' in url: url = url.replace('/waaw.in/', '/waaw.to/')

               elif '/player.cuevana.ac/' in url: url = url.replace('/player.cuevana.ac/', '/waaw.to/')
               elif '/player.cuevana3.ac/' in url: url = url.replace('/player.cuevana.ac/', '/waaw.to/')
               elif '/player.cuevana.one/' in url: url = url.replace('/player.cuevana3.one/', '/waaw.to/')
               elif '/player.cuevana3.one/' in url: url = url.replace('/player.cuevana3.one/', '/waaw.to/')

               elif '/player.fiuxy2.com/' in url: url = url.replace('/player.fiuxy2.com/', '/waaw.to/')
               elif '/play.fiuxy2.com/' in url: url = url.replace('/play.fiuxy2.com/', '/waaw.to/')

               servidor = servertools.get_server_from_url(url)

               if servertools.is_server_available(servidor):
                   if not servertools.is_server_enabled(servidor): continue
               else:
                   if not config.get_setting('developer_mode', default=False): continue

               url = servertools.normalize_url(servidor, url)

               other = ''
               if servidor == 'various': other = servertools.corregir_other(url)
               elif servidor == 'zures': other = servertools.corregir_zures(url)

               itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, url = url,
                                     language=lang, other=other ))

           continue

        url = _url

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

        elif 'lvturbo' in url: continue
        elif 'vanfem' in url: continue
        elif 'fembed' in url: continue
        elif 'fcom' in url: continue

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

        url = servertools.normalize_url(servidor, url)

        other = ''
        if servidor == 'various': other = servertools.corregir_other(url)
        elif servidor == 'zures': other = servertools.corregir_zures(url)

        itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, url = url,
                              language='?', other=other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def _epis(item):
    logger.info()

    item.url = host
    item.search_type = 'tvshow'

    return last_epis(item)


def corregir_SerieName(SerieName):
    logger.info()

    if 'Capítulo' in SerieName: SerieName = SerieName.split("Capítulo")[0]
    if 'Capitulo' in SerieName: SerieName = SerieName.split("Capitulo")[0]
    if 'Episodio' in SerieName: SerieName = SerieName.split("Episodio")[0]
    if 'episodio' in SerieName: SerieName = SerieName.split("episodio")[0]
    if 'Episode' in SerieName: SerieName = SerieName.split("Episode")[0]
    if 'episode' in SerieName: SerieName = SerieName.split("episode")[0]

    if 'Movie' in SerieName: SerieName = SerieName.split("Movie")[0]

    if '(Sin Relleno)' in SerieName: SerieName = SerieName.split("(Sin Relleno)")[0]

    if '(TV)' in SerieName: SerieName = SerieName.split("(TV)")[0]

    SerieName = re.sub(r"Sub |Español|Latino|Castellano|HD|Temporada \d+|\(\d{4}\)", "", SerieName).strip()
    SerieName = SerieName.replace('Español Latino HD', '').replace('Español Castellano HD', '').replace('Sub Español HD', '').strip()

    if 'Temporada' in SerieName: SerieName = SerieName.split("Temporada")[0]

    if 'Season' in SerieName: SerieName = SerieName.split("Season")[0]
    if 'season' in SerieName: SerieName = SerieName.split("season")[0]

    if ' S1 ' in SerieName: SerieName = SerieName.split(" S1 ")[0]
    elif ' S2 ' in SerieName: SerieName = SerieName.split(" S2 ")[0]
    elif ' S3 ' in SerieName: SerieName = SerieName.split(" S3 ")[0]
    elif ' S4 ' in SerieName: SerieName = SerieName.split(" S4 ")[0]
    elif ' S5 ' in SerieName: SerieName = SerieName.split(" S5 ")[0]
    elif ' S6 ' in SerieName: SerieName = SerieName.split(" S6 ")[0]
    elif ' S7 ' in SerieName: SerieName = SerieName.split(" S7 ")[0]
    elif ' S8 ' in SerieName: SerieName = SerieName.split(" S8 ")[0]
    elif ' S9 ' in SerieName: SerieName = SerieName.split(" S9 ")[0]

    if ' T1 ' in SerieName: SerieName = SerieName.split(" T1 ")[0]
    elif ' T2 ' in SerieName: SerieName = SerieName.split(" T2 ")[0]
    elif ' T3 ' in SerieName: SerieName = SerieName.split(" T3 ")[0]
    elif ' T4 ' in SerieName: SerieName = SerieName.split(" T4 ")[0]
    elif ' T5 ' in SerieName: SerieName = SerieName.split(" T5 ")[0]
    elif ' T6 ' in SerieName: SerieName = SerieName.split(" T6 ")[0]
    elif ' T7 ' in SerieName: SerieName = SerieName.split(" T7 ")[0]
    elif ' T8 ' in SerieName: SerieName = SerieName.split(" T8 ")[0]
    elif ' T9 ' in SerieName: SerieName = SerieName.split(" T9 ")[0]

    if '2nd' in SerieName: SerieName = SerieName.split("2nd")[0]
    if '3rd' in SerieName: SerieName = SerieName.split("3rd")[0]
    if '4th' in SerieName: SerieName = SerieName.split("4th")[0]
    if '5th' in SerieName: SerieName = SerieName.split("5th")[0]
    if '6th' in SerieName: SerieName = SerieName.split("6th")[0]
    if '7th' in SerieName: SerieName = SerieName.split("7th")[0]
    if '8th' in SerieName: SerieName = SerieName.split("8th")[0]
    if '9th' in SerieName: SerieName = SerieName.split("9th")[0]

    SerieName = SerieName.strip()

    return SerieName


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
