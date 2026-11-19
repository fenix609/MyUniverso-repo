# -*- coding: utf-8 -*-

import re, base64

from platformcode import config, logger, platformtools
from core.item import Item
from core import httptools, scrapertools, servertools, tmdb


from lib.pyberishaes import GibberishAES
from lib import decrypters


host = 'https://repelis28.org/'


def do_downloadpage(url, post=None, headers=None):
    data = httptools.downloadpage(url, post=post, headers=headers).data

    return data


def mainlist(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar ...', action = 'search', search_type = 'all', text_color = 'yellow' ))

    itemlist.append(item.clone( title = 'Películas', action = 'mainlist_pelis', text_color = 'deepskyblue' ))
    itemlist.append(item.clone( title = 'Series', action = 'mainlist_series', text_color = 'hotpink' ))

    if not config.get_setting('descartar_anime', default=False):
        itemlist.append(item.clone( title='Animes', action = 'mainlist_animes', text_color='springgreen' ))

    return itemlist


def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie', text_color = 'deepskyblue' ))

    itemlist.append(item.clone( title = 'Catálogo', action = 'list_all', url = host + 'peliculas', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host + 'peliculas/populares', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'movie' ))

    return itemlist


def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow', text_color = 'hotpink' ))

    itemlist.append(item.clone( title = 'Catalogo', action = 'list_all', url = host + 'series', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host + 'series/populares', search_type = 'tvshow' ))

    if not config.get_setting('descartar_anime', default=False):
        itemlist.append(item.clone( title='Animes', action = 'mainlist_animes', text_color='springgreen' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios', search_type = 'tvshow' ))

    return itemlist


def mainlist_animes(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Buscar anime ...', action = 'search', search_type = 'tvshow', text_color = 'springgreen' ))

    itemlist.append(item.clone( title = 'Catalogo', action = 'list_all', url = host + 'animes', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Más populares', action = 'list_all', url = host + 'animes/populares', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', tipo = 'Animes', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anios', tipo = 'Animes', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    if item.search_type == 'movie': text_color = 'deepskyblue'
    else:
       if item.tipo == 'Animes': text_color = 'springgreen'
       else: text_color = 'hotpink'

    data = do_downloadpage(host)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '>Géneros(.*?)</div>')

    matches = scrapertools.find_multiple_matches(bloque, '<a href="(.*?)".*?>(.*?)</a>')

    for url, title in matches:
        url = host[:-1] + url

        itemlist.append(item.clone( action = 'list_all', title = title, url = url, text_color = text_color ))

    return sorted(itemlist, key=lambda x: x.title)


def anios(item):
    logger.info()
    itemlist = []

    if item.search_type == 'movie': text_color = 'deepskyblue'
    else:
       if item.tipo == 'Animes': text_color = 'springgreen'
       else: text_color = 'hotpink'

    if item.search_type == 'movie': limit_year = 1929
    else: limit_year = 1959

    from datetime import datetime
    current_year = int(datetime.today().year)

    for x in range(current_year, limit_year, -1):
        itemlist.append(item.clone( title = str(x), url = host + 'year/' + str(x), action = 'list_all', text_color=text_color ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, '<div class="nfx-grid">(.*?)</main>')

    matches = re.compile('<a(.*?)</a>', re.DOTALL).findall(bloque)

    for article in matches:
        title = scrapertools.find_single_match(article, '<h2 class="entry-title">(.*?)</h2>').strip()
        if not title: title = scrapertools.find_single_match(article, 'alt="(.*?)"')

        url = scrapertools.find_single_match(article, 'href="(.*?)"')

        if not url or not title: continue

        title = title.replace('Ver ', '').replace('online en HD', '').replace('- Película completa', '').replace('- Serie completa', '').replace('- Anime completa', '').strip()

        title = title.replace('&#039;m', "'m").replace('&#039;s', "'s").replace('&#038;', '&').replace('&#8211;', '').replace('&#8217;s', "'s").replace('&#8217;', '').replace('&#8230;', '').replace('&#039;', "'").replace('&#39;', "'").replace('&amp;', '').strip()

        thumb = scrapertools.find_single_match(article, 'src="(.*?)"')

        year = scrapertools.find_single_match(article, '<span class="year">(.*?)</span>').strip()
        if not year: year = scrapertools.find_single_match(article, '<span class=Year>(.*?)</span>').strip()
        if not year: year = scrapertools.find_single_match(article, '<span class="Date">(.*?)</span>').strip()

        if not year: year = scrapertools.find_single_match(article, '<small>(.*?)</small>')

        if year:
            title = title.replace('(' + year + ')', '').strip()
            c_year = scrapertools.find_single_match(title, '(\d{4})')
            if c_year: title = title.replace('(' + c_year + ')', '').strip()
        else:
            year = scrapertools.find_single_match(title, '(\d{4})')
            if year: title = title.replace('(' + year + ')', '').strip()

        if not year: year = '-'

        url = host[:-1] + url

        tipo = 'tvshow' if '/serie/' in url or '/anime/' in url else 'movie'
        sufijo = '' if item.search_type != 'all' else tipo

        if tipo == 'movie':
            if not item.search_type == "all":
                if item.search_type == "tvshow": continue

            title = title.replace('Pelicula', '').strip()

            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels={'year': year} ))

        if tipo == 'tvshow':
            if not item.search_type == "all":
                if item.search_type == "movie": continue

            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName=title, infoLabels={'year': year} ))

    tmdb.set_infoLabels(itemlist)

    if itemlist:
        next_page = ''

        if '<nav class="nfx-pagination">' in data:
            next_page = scrapertools.find_single_match(data, '<nav class="nfx-pagination">.*?</span>.*?href="(.*?)"')

        if next_page:
            if '?page=' in next_page:
                next_page = host[:-1] + next_page

                itemlist.append(item.clone( title = 'Siguientes ...', url = next_page, action = 'list_all', text_color='coral' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    matches = re.compile('onclick="showS(.*?)".*?>T(.*?)</button>', re.DOTALL).findall(data)

    for id, tempo in matches:
        tempo = tempo.strip()

        title = 'Temporada ' + tempo

        id = id.replace('(', '').replace(')', '').strip()

        if len(matches) == 1:
            if config.get_setting('channels_seasons', default=True):
                platformtools.dialog_notification(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), 'solo [COLOR tan]' + title + '[/COLOR]')

                item.page = 0
                item.contentType = 'season'
                item.contentSeason = tempo
                item.id = id
                itemlist = episodios(item)
                return itemlist

        itemlist.append(item.clone( action='episodios', title=title, page = 0, id = id, contentType='season', contentSeason=tempo, text_color = 'tan' ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


def episodios(item):
    logger.info()
    itemlist=[]

    if not item.page: item.page = 0
    if not item.perpage: item.perpage = 50

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|\s{2}|&nbsp;', '', data)

    bloque = scrapertools.find_single_match(data, 'id="sg' + str(item.id) + '"(.*?)</div>')

    matches = re.compile('<a href="(.*?)".*?<span class="nfx-ep-num">(.*?)</span>.*?<span class="nfx-ep-title">(.*?)</span>', re.DOTALL).findall(bloque)

    if item.page == 0 and item.perpage == 50:
        sum_parts = len(matches)

        try:
            tvdb_id = scrapertools.find_single_match(str(item), "'tvdb_id': '(.*?)'")
            if not tvdb_id: tvdb_id = scrapertools.find_single_match(str(item), "'tmdb_id': '(.*?)'")
        except: tvdb_id = ''

        if config.get_setting('channels_charges', default=True):
            item.perpage = sum_parts
            if sum_parts >= 100:
                platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
        elif tvdb_id:
            if sum_parts > 50:
                platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando Todos los elementos[/COLOR]')
                item.perpage = sum_parts
        else:
            item.perpage = sum_parts

            if sum_parts >= 1000:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]500[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando 500 elementos[/COLOR]')
                    item.perpage = 500

            elif sum_parts >= 500:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]250[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando 250 elementos[/COLOR]')
                    item.perpage = 250

            elif sum_parts >= 250:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]125[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando 125 elementos[/COLOR]')
                    item.perpage = 125

            elif sum_parts >= 125:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos en bloques de [COLOR cyan][B]75[/B][/COLOR] elementos ?'):
                    platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando 75 elementos[/COLOR]')
                    item.perpage = 75

            elif sum_parts > 50:
                if platformtools.dialog_yesno(item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'"), '¿ Hay [COLOR yellow][B]' + str(sum_parts) + '[/B][/COLOR] elementos disponibles, desea cargarlos [COLOR cyan][B]Todos[/B][/COLOR] de una sola vez ?'):
                    platformtools.dialog_notification('RePelis28', '[COLOR cyan]Cargando ' + str(sum_parts) + ' elementos[/COLOR]')
                    item.perpage = sum_parts
                else: item.perpage = 50

    for url, epis, title in matches[item.page * item.perpage:]:
        if not epis: epis = 1

        if url.startswith("/"): url = host[:-1] + url

        if not epis: epis = 1

        titulo = str(item.contentSeason) + 'x' + epis + ' ' + title.replace(str(item.contentSeason) + 'x' + epis, '').strip()

        titulo = titulo.replace('T1', '[COLOR tan]Temp.1[/COLOR]').replace('T2', '[COLOR tan]Temp.2[/COLOR]').replace('T3', '[COLOR tan]Temp.3[/COLOR]').replace('T4', '[COLOR tan]Temp.4[/COLOR]').replace('T5', '[COLOR tan]Temp.5[/COLOR]').replace('T6', '[COLOR tan]Temp.6[/COLOR]').replace('T7', '[COLOR tan]Temp.7[/COLOR]').replace('T8', '[COLOR tan]Temp.8[/COLOR]').replace('T9', '[COLOR tan]Temp.9[/COLOR]')

        if 'episodie' in titulo.lower() or 'episodio' in titulo.lower() or 'capítulo' in titulo.lower() or 'capitulo' in titulo.lower():
            titulo = titulo + ' ' + item.contentSerieName.replace('&#038;', '&').replace('&#8217;', "'")

        titulo = titulo.replace('Episode', '[COLOR goldenrod]Epis.[/COLOR]').replace('episode', '[COLOR goldenrod]Epis.[/COLOR]')
        titulo = titulo.replace('Episodio', '[COLOR goldenrod]Epis.[/COLOR]').replace('episodio', '[COLOR goldenrod]Epis.[/COLOR]')
        titulo = titulo.replace('Capítulo', '[COLOR goldenrod]Epis.[/COLOR]').replace('capítulo', '[COLOR goldenrod]Epis.[/COLOR]').replace('Capitulo', '[COLOR goldenrod]Epis.[/COLOR]').replace('capitulo', '[COLOR goldenrod]Epis.[/COLOR]')

        itemlist.append(item.clone( action='findvideos', url = url, title = titulo,
                                    contentType = 'episode', contentSeason = item.contentSeason, contentEpisodeNumber=epis ))

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

    data = do_downloadpage(item.url)
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', "", data)

    matches = scrapertools.find_multiple_matches(data, 'id="player-option-(.*?)</li>')
    if not matches: matches = scrapertools.find_multiple_matches(data, "id='player-option-(.*?)</li>")

    ses = 0

    for match in matches:
        # ~ dtype, dpost, dnume
        dtype = scrapertools.find_single_match(match, ' data-type="(.*?)"')
        if not dtype: dtype = scrapertools.find_single_match(match, " data-type='(.*?)'")

        dpost = scrapertools.find_single_match(match, ' data-post="(.*?)"')
        if not dpost: dpost = scrapertools.find_single_match(match, " data-post='(.*?)'")

        dnume = scrapertools.find_single_match(match, ' data-nume="(.*?)"')
        if not dnume: dnume = scrapertools.find_single_match(match, " data-nume='(.*?)'")

        if dtype and dpost and dnume:
            data1 = do_downloadpage(host + '/wp-json/dooplayer/v2/' + dpost + '/' + dtype + '/' + dnume +'/')

            embed = scrapertools.find_single_match(str(data1), '"embed_url":.*?"(.*?)"')

            if embed:
                ses += 1

                if not dnume == 'trailer':
                    embed = embed.replace('\\/', '/')

                    if embed.startswith('//'): embed = 'https:' + embed
                    elif embed.startswith("/"): embed = host + embed

                    if not 'http' in embed: continue

                    if not '/pelisplay.' in embed:
                        servidor = servertools.get_server_from_url(embed)

                        lang = scrapertools.find_single_match(match, '<span class="title">(.*?)</span>')
                        if not lang: lang = scrapertools.find_single_match(match, "<span class='title'>(.*?)</span>")

                        if 'Latino' in lang: lang = 'Lat'
                        elif 'Castellano' in lang or 'Español' in lang: lang = 'Esp'
                        elif 'Subtitulado' in lang or 'VOSE' in lang or 'Vose' in lang: lang = 'Vose'
                        elif 'Inglés' in lang: lang = 'Vo'
                        else: lang = '?'

                        other = ''
                        if servidor == 'various': other = servertools.corregir_other(embed)

                        itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = embed,
                                              language = lang, other = other ))
                    else:
                        data2 = do_downloadpage(embed)

                        links = scrapertools.find_multiple_matches(data2, '<li class="linkserver".*?data-video="(.*?)"')
                        if not links: links = scrapertools.find_multiple_matches(data2,"'<li class='linkserver'.*?data-video='(.*?)'")

                        if links:
                            for url in links:
                                ses += 1

                                if '/hydrax.' in url: continue
                                elif '/xupalace.' in url: continue
                                elif '/uploadfox.' in url: continue

                                if url.startswith('//'): url = 'https:' + url
                                elif url.startswith("/"): url = host + url

                                if not 'http' in url: continue

                                servidor = servertools.get_server_from_url(url)

                                lang = scrapertools.find_single_match(match, '<span class="title">(.*?)</span>')
                                if not lang: lang = scrapertools.find_single_match(match, "<span class='title'>(.*?)</span>")

                                if 'Latino' in lang: lang = 'Lat'
                                elif 'Castellano' in lang or 'Español' in lang: lang = 'Esp'
                                elif 'Subtitulado' in lang or 'VOSE' in lang or 'Vose' in lang: lang = 'Vose'
                                elif 'Inglés' in lang: lang = 'Vo'
                                else: lang = '?'

                                other = ''
                                if servidor == 'various': other = servertools.corregir_other(url)

                                itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url,
                                                      language = lang, other = other ))

            continue

        # ~ iframes
        links = scrapertools.find_multiple_matches(data, '<div id="options-' + opt + '.*?<iframe.*?src="(.*?)"')

        if not links: continue

        opt = scrapertools.find_single_match(match, '(.*?)"')

        srv = scrapertools.find_single_match(match, '<span class="server">(.*?)-').strip()
        lng = scrapertools.find_single_match(match, '<span class="server">.*?-(.*?)</span>').strip()

        srv = srv.lower().strip()

        if 'youtube' in srv: continue

        if 'Latino' in lng: lang = 'Lat'
        elif 'Castellano' in lng or 'Español' in lng: lang = 'Esp'
        elif 'Subtitulado' in lng or 'VOSE' in lng or 'Vose' in lng: lang = 'Vose'
        elif 'Inglés' in lng: lang = 'Vo'
        else: lang = '?'

        servidor = servertools.corregir_servidor(srv)

        for url in links:
            ses += 1

            trembed = url.replace('&#038;', '&').replace('&amp;', '&').replace('#038;', '')

            data3 = do_downloadpage(trembed)

            vid = scrapertools.find_single_match(data3, '<iframe.*?src="([^"]+)')
            if not vid: vid = scrapertools.find_single_match(data3, '<IFRAME.*?SRC="([^"]+)')

            if vid:
                if vid.startswith('//'): vid = 'https:' + vid
                elif vid.startswith("/"): vid = host + vid

                if not 'http' in vid: continue

                if '/play?' in vid or '/streamhd?' in vid:
                    vid = vid.replace('&#038;', '&').replace('&amp;', '&').replace('#038;', '')

                    data4 = do_downloadpage(vid)

                    vids = scrapertools.find_multiple_matches(data4, 'data-video="(.*?)"')

                    if vids:
                        for url in vids:
                            ses += 1

                            if url:
                                if '/hydrax.' in url: continue
                                elif '/xupalace.' in url: continue
                                elif '/uploadfox' in url: continue

                                if url.startswith('//'): url = 'https:' + url
                                elif url.startswith("/"): url = host + url

                                if not 'http' in url: continue

                                servidor = servertools.get_server_from_url(url)

                                other = ''
                                if servidor == 'various': other = servertools.corregir_other(url)

                                itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url,
                                                      language = lang, other = other ))

                    embed = scrapertools.find_single_match(str(data), "sources:.*?'(.*?)'")

                    if embed:
                        ses += 1

                        if embed.startswith('//'): embed = 'https:' + embed
                        elif embed.startswith("/"): embed = host + embed

                        if not 'http' in embed: continue

                        itemlist.append(Item( channel = item.channel, action = 'play', server = 'directo', title = '', url = embed, language = lang ))

                else:
                    url = scrapertools.find_single_match(data, '<iframe.*?src="([^"]+)')
                    if not url: url = scrapertools.find_single_match(data, '<IFRAME.*?SRC="([^"]+)')

                    if url:
                        ses += 1

                        if '/hydrax.' in url: continue
                        elif '/xupalace.' in url: continue
                        elif '/uploadfox.' in url: continue

                        elif '/media.esplay.one' in url: continue

                        if url.startswith('//'): url = 'https:' + url
                        elif url.startswith("/"): url = host + url

                        if not 'http' in url: continue

                        servidor = servertools.get_server_from_url(url)

                        other = ''
                        if servidor == 'various': other = servertools.corregir_other(url)

                        itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url,
                                              language = lang, other = other ))

            else:
                other = srv

                if servidor == srv: other = ''
                elif not servidor == 'directo':
                   if not servidor == 'various': other = ''

                if url.startswith('//'): url = 'https:' + url
                elif url.startswith("/"): url = host + url

                if not 'http' in url: continue

                itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url,
                                      language = lang, other = other.capitalize() ))

        continue

    # ~ iframes 2do
    matches2 = []

    matches1 = scrapertools.find_multiple_matches(data, '<iframe src="(.*?)"')
    if not matches1: matches2 = scrapertools.find_multiple_matches(data, '<iframe.*?src="(.*?)"')

    matches = matches1 + matches2

    for url in matches:
        if not url: continue

        ses += 1

        url = url.replace('&#038;', '&').replace('&amp;', '&').replace('#038;', '')

        if 'Latino' in data: lang = 'Lat'
        elif 'Castellano' in data or 'Español' in data: lang = 'Esp'
        elif 'Subtitulado' in data or 'VOSE' in data or 'Vose' in data: lang = 'Vose'
        elif 'Inglés' in data: lang = 'Vo'
        else: lang = '?'

        if url.startswith('//'): url = 'https:' + url
        elif url.startswith("/"): url = host + url

        if not 'http' in url: continue

        data5 = do_downloadpage(url)

        matches5 = scrapertools.find_multiple_matches(data5, '<iframe.*?src="(.*?)"')

        for match in matches5:
            if match.startswith('//'): match = 'https:' + match
            elif match.startswith("/"): match = host + match

            if not 'http' in match: continue

            data6 = do_downloadpage(match)

            links = scrapertools.find_multiple_matches(data6, '<li class="linkserver".*?data-video="(.*?)"')

            if links:
                for url in links:
                    if '/hydrax.' in url: continue
                    elif '/xupalace.' in url: continue
                    elif '/uploadfox.' in url: continue

                    if url.startswith('//'): url = 'https:' + url
                    elif url.startswith("/"): url = host + url

                    if not 'http' in url: continue

                    servidor = servertools.get_server_from_url(url)

                    other = ''
                    if servidor == 'various': other = servertools.corregir_other(url)

                    itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url,
                                          language = lang, other = other ))

                continue

        if not '/embed69.' in url and not '/xupalace.' in url and not '/vidurl/' in url:
            servidor = servertools.get_server_from_url(url)

            other = ''
            if servidor == 'various': other = servertools.corregir_other(url)

            itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url, language = lang, other = other ))

    # ~ iframes src
    matches = scrapertools.find_multiple_matches(data, '<iframe src="(.*?)"')
    if not matches: matches = scrapertools.find_multiple_matches(data, '<iframe.*?src="(.*?)"')

    for match in matches:
        lang = '?'

        if match.startswith("//"): match = 'https:' + match
        elif match.startswith("/"): match = host + match

        if not 'http' in match: continue

        if '/embed69.' in match or '/vidurl/' in match:
            ses += 1

            datae = do_downloadpage(match)

            dataLink = scrapertools.find_single_match(datae, 'const dataLink =(.*?);')
            if not dataLink: dataLink = scrapertools.find_single_match(datae, 'dataLink(.*?);')

            e_bytes = scrapertools.find_single_match(datae, "const bytes =.*?'(.*?)'")
            if not e_bytes: e_bytes = scrapertools.find_single_match(datae, "const safeServer =.*?'(.*?)'")

            e_links = dataLink.replace(']},', '"type":"file"').replace(']}]', '"type":"file"')

            age = ''
            if not dataLink or not e_bytes: age = 'crypto'

            langs = scrapertools.find_multiple_matches(str(e_links), '"video_language":(.*?)"type":"file"')

            for lang in langs:
                ses += 1

                lang = lang + '"type":"video"'

                links = scrapertools.find_multiple_matches(str(lang), '"servername":"(.*?)","link":"(.*?)".*?"type":"video"')

                if 'SUB' in lang: lang = 'Vose'
                elif 'LAT' in lang: lang = 'Lat'
                elif 'ESP' in lang: lang = 'Esp'
                else: lang = '?'

                for srv, link in links:
                    srv = srv.lower().strip()

                    if not srv: continue

                    if host in link: continue

                    elif '1fichier.' in srv: continue
                    elif 'plustream' in srv: continue
                    elif 'embedsito' in srv: continue
                    elif 'disable2' in srv: continue
                    elif 'disable' in srv: continue
                    elif 'xupalace' in srv: continue
                    elif 'uploadfox' in srv: continue

                    elif srv == 'download': continue
                    elif srv == 'up2box': continue

                    servidor = servertools.corregir_servidor(srv)

                    if servertools.is_server_available(servidor):
                        if not servertools.is_server_enabled(servidor): continue
                    else:
                        if not config.get_setting('developer_mode', default=False): continue

                    other = ''
                    cpow = ''

                    if servidor == 'various': other = servertools.corregir_other(srv)

                    if '.eyJs' in link: age = ''

                    elif 'POW_CHALLENGE' in datae:
                       cpow = scrapertools.find_single_match(datae, "POW_CHALLENGE\s*=\s*'([^']+)';" +
                                                                    "\s*\w*\s*POW_DIFFICULTY\s*=\s*(\d+);" +
                                                                    "\s*\w*\s*POW_SALT\s*=\s*'([^']+)';")
                       if cpow: age = ''

                    itemlist.append(Item( channel = item.channel, action = 'play', server=servidor, title = '',
                                          crypto=link, bytes=e_bytes, age=age, cpow=cpow, language=lang, other=other ))

            continue

        elif '/xupalace.' in match:
            ses += 1

            if 'php?id=' in match:
                datax = do_downloadpage(match)

                url = scrapertools.find_single_match(datax, '<iframe src="(.*?)"')

                if url:
                    servidor = servertools.get_server_from_url(url)

                    if servertools.is_server_available(servidor):
                        if not servertools.is_server_enabled(servidor): continue
                    else:
                        if not config.get_setting('developer_mode', default=False): continue

                    itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = url, language = lang ))

                continue

            elif '/video/' in match:
                datax = do_downloadpage(match)

                matchesx = scrapertools.find_multiple_matches(datax, "go_to_playerVast.*?'(.*?)'(.*?)</span>")

                for matchx, restox in matchesx:
                    if '/embedsito.' in matchx: continue
                    elif '/player-cdn.' in matchx: continue
                    elif '/1fichier.' in matchx: continue
                    elif '/hydrax.' in matchx: continue
                    elif '/xupalace.' in matchx: continue
                    elif '/uploadfox.' in matchx: continue

                    if 'data-lang="0"' in restox: lang = 'Lat'
                    elif 'data-lang="1"' in restox: lang = 'Esp'
                    elif 'data-lang="2"' in restox: lang = 'Vose'
                    elif 'data-lang="3"' in restox: lang = 'Jap'
                    else: lang = '?'

                    servidor = servertools.get_server_from_url(matchx)

                    if servertools.is_server_available(servidor):
                        if not servertools.is_server_enabled(servidor): continue
                    else:
                        if not config.get_setting('developer_mode', default=False): continue

                    other = ''
                    if servidor == 'various': other = servertools.corregir_other(matchx)

                    itemlist.append(Item( channel = item.channel, action = 'play', server = servidor, title = '', url = matchx,
                                         language = lang, other = other ))

                continue

            else: continue

    # ~ data servers
    match = scrapertools.find_single_match(data, 'data-server="(.*?)"')

    if match:
        ses += 1

        datam = do_downloadpage(match)

        d_links = scrapertools.find_single_match(datam, 'const dataLink =(.*?);')
        d_bytes = scrapertools.find_single_match(datam, "const bytes =.*?'(.*?)'")

        if d_links:
            ses += 1

            langs = scrapertools.find_multiple_matches(str(d_links), '"video_language":(.*?)"type":"file"')

            for lang in langs:
                lang = lang + '"type":"video"'

                links = scrapertools.find_multiple_matches(str(lang), '"servername":"(.*?)","link":"(.*?)".*?"type":"video"')

                if 'SUB' in lang: lang = 'Vose'
                elif 'LAT' in lang: lang = 'Lat'
                elif 'ESP' in lang: lang = 'Esp'
                else: lang = '?'

                for srv, link in links:
                    srv = srv.lower().strip()

                    if not srv: continue
                    elif srv == '#': continue

                    if host in link: continue

                    elif 'fembed' in srv: continue
                    elif 'streamsb' in srv: continue
                    elif 'playersb' in srv: continue
                    elif 'sbembed' in srv: continue

                    elif 'player-cdn' in srv: continue

                    elif '1fichier.' in srv: continue
                    elif 'short' in srv: continue
                    elif 'plustream' in srv: continue
                    elif 'disable2' in srv: continue
                    elif 'disable' in srv: continue
                    elif 'embedsito' in srv: continue
                    elif 'xupalace' in srv: continue
                    elif 'uploadfox' in srv: continue

                    elif srv == 'download': continue
                    elif srv == 'up2box': continue

                    servidor = servertools.corregir_servidor(srv)

                    if servertools.is_server_available(servidor):
                        if not servertools.is_server_enabled(servidor): continue
                    else:
                        if not config.get_setting('developer_mode', default=False): continue

                    other = ''

                    if servidor == 'various': other = servertools.corregir_other(srv)

                    age = 'crypto'
                    cpow = ''

                    if '.eyJs' in link: age = ''

                    elif 'POW_CHALLENGE' in datam:
                       cpow = scrapertools.find_single_match(datam, "POW_CHALLENGE\s*=\s*'([^']+)';" +
                                                                    "\s*\w*\s*POW_DIFFICULTY\s*=\s*(\d+);" +
                                                                    "\s*\w*\s*POW_SALT\s*=\s*'([^']+)';")
                       if cpow: age = ''

                    itemlist.append(Item( channel = item.channel, action = 'play', server=servidor, title = '',
                                          crypto=link, bytes=e_bytes, age=age, cpow=cpow, language=lang, other=other ))

                continue

    matches = scrapertools.find_multiple_matches(data, 'onclick="go_to_player.*?' + "'(.*?)'")
    if not matches: matches = scrapertools.find_multiple_matches(data, "onclick='go_to_player.*?" + "'(.*?)'")

    langs = []
    if 'data-lang="1"' in data: langs.append('Esp')
    if 'data-lang="0"' in data: langs.append('Lat')
    if 'data-lang="2"' in data: langs = langs.append('Vose')

    if ',' in str(langs): lang = ",".join(langs)
    else: lang = str(langs).replace('[', '').replace("'", '').replace(']', '').strip()

    if not langs: lang = '?'

    for url in matches:
        if not url: continue

        ses += 1

        if 'player-cdn' in url: continue

        elif '/1fichier.' in url: continue
        elif '/short.' in url: continue
        elif '/plustream.' in url: continue
        elif 'embedsito' in url: continue
        elif 'disable2' in url: continue
        elif 'disable' in url: continue
        elif 'xupalace' in url: continue
        elif 'uploadfox' in url: continue

        servidor = servertools.get_server_from_url(url)

        if servertools.is_server_available(servidor):
            if not servertools.is_server_enabled(servidor): continue
        else:
            if not config.get_setting('developer_mode', default=False): continue

        other = ''

        if servidor == 'various': other = servertools.corregir_other(url)

        elif servidor == 'filemooon':
            servidor = 'filemoon'
            url = url.replace('filemooon', 'filemoon')

        elif servidor == 'netu': servidor = 'waaw'

        itemlist.append(Item(channel = item.channel, action = 'play', server = servidor, title = '', url = url, language = lang, other = other ))

    if not itemlist:
        if not ses == 0:
            platformtools.dialog_notification(config.__addon_name, '[COLOR tan][B]Sin enlaces Soportados[/B][/COLOR]')
            return

    return itemlist


def play(item):
    logger.info()
    itemlist = []

    url = item.url.replace('&#038;', '&').replace('&amp;', '&').replace('#038;', '')

    if item.crypto:
        crypto = str(item.crypto)
        bytes = str(item.bytes)

        url = ''

        if not bytes:
            if '.eyJs' in item.crypto:
                url = scrapertools.find_single_match(item.crypto, '\.(eyJs.*?)\.')
                url += '='

                try:
                    url = base64.b64decode(url).decode()
                    url = scrapertools.find_single_match(url, '"link":"(.*?)"')
                except:
                    url = ''

            elif item.cpow:
                res_pow = {"challenge": item.cpow[0], "difficulty": int(item.cpow[1]), "salt": item.cpow[2]}

                resolve_pow = decrypters.decode_pow(res_pow)
                aes_clave = resolve_pow.get("aes_key", "")

                if aes_clave:
                    url = decrypters.decode_decipher(crypto, aes_clave)

        if not url:
            if bytes:
                try:
                   url = GibberishAES.dec(GibberishAES(), string = crypto, pass_ = bytes)
                except:
                    url = ''

            if not url:
                if bytes:
                    url = decrypters.decode_decipher(crypto, bytes)

            if not url:
                if crypto.startswith("http"):
                    url = crypto.replace('\\/', '/')

                if not url:
                    return '[COLOR cyan]No se pudo [COLOR goldenrod]Descifrar[/COLOR]'

            elif not url.startswith("http"):
                return '[COLOR cyan]No se pudo [COLOR goldenrod]Descifrar[/COLOR]'

    elif item.server == 'directo':
        item.url = url

        data = do_downloadpage(item.url)

        url = scrapertools.find_single_match(data, '<iframe.*?src="([^"]+)')
        if not url: url = scrapertools.find_single_match(data, '<IFRAME.*?SRC="([^"]+)')

        if not url:
            if '/hydrax.' in data or '/xupalace.' in data or '/uploadfox.' in data or '/embed69.' in data or '/pelisplay.' in data:
                return 'Servidor [COLOR goldenrod]No Soportado[/COLOR]'
            return itemlist

        if url:
            if '/hydrax.' in url or '/xupalace.' in url or '/uploadfox.' in url or '/embed69.' in url or '/pelisplay.' in url:
                return 'Servidor [COLOR goldenrod]No Soportado[/COLOR]'

            servidor = servertools.get_server_from_url(url)

            if servidor == 'directo':
                new_server = servertools.corregir_other(url).lower()
                if new_server.startswith("http"):
                    if not config.get_setting('developer_mode', default=False): return itemlist
                servidor = new_server

            itemlist.append(item.clone(server = servidor, url = url))

        return itemlist

    if url:
        if '/hydrax.' in url or '/xupalace.' in url or '/uploadfox.' in url:
            return 'Servidor [COLOR goldenrod]No Soportado[/COLOR]'

        servidor = servertools.get_server_from_url(url)

        url = servertools.normalize_url(servidor, url)

        if servidor == 'directo':
            new_server = servertools.corregir_other(url).lower()
            if new_server.startswith("http"):
                if not config.get_setting('developer_mode', default=False): return itemlist
            servidor = new_server

    itemlist.append(item.clone(server = servidor, url = url))

    return itemlist


def search(item, texto):
    logger.info()

    try:
        item.url = host + 'search?s=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []
