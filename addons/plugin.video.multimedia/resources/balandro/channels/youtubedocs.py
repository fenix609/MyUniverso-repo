# -*- coding: utf-8 -*-

import xbmc

from platformcode import logger, config
from core.item import Item
from core import httptools, scrapertools


host = 'https://www.youtube.com/'


def mainlist(item):
    logger.info()
    itemlist = []

    # ~ itemlist.append(item.clone( title = 'Buscar documental ...', action = 'search', search_type = 'documentary', text_color='cyan' ))

    itemlist.append(item.clone( channel='youtubetrailers', action='search', title= '[B][COLOR yellow]Buscar[/COLOR] Youtube[/B] ...', thumbnail=config.get_thumb('youtube'), text_color='darksalmon', search_special = 'youtube', search_type = 'all' ))

    itemlist.append(item.clone( title = 'Sub-Canales [B]YouTubeDocs:[/B]', action = '', text_color = 'darkcyan' ))

    itemlist.append(item.clone( title = '- [B]Academia Play[/B]', action = 'list_tubes', url = host + 'watch?v=99cd_dCl3pc&list=UULFv05qOuJ6Igbe-EyQibJgwQ', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Daniel Geohistoria[/B]', action = 'list_tubes', url = host + 'watch?v=XkpmWi9foUU&list=UULPGNk1YgQf8zeFX7uP04O_uw', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Dmax[/B]', action = 'list_tubes', url = host + 'watch?v=4mx89Gc-elY&list=PLXUXqAIy6K4-IAeAQp4PcP8xJHzfJu_jL', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Documental Z[/B]', action = 'list_tubes', url = host + 'watch?v=WX-FJ25QILI&list=UULFV5OEc-nA4Ge5tOLUPWosaQ', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Documentales Gratuitos[/B]', action = 'list_tubes', url = host + 'watch?v=wwsftALV284&list=UULF259MSTQbJjxYGzUM0SvYGA', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Dtom[/B]', action = 'list_tubes', url = host + 'watch?v=6PuaPBkYRXE&list=UULF_PkkoCXPpIH8Ip5RXUwccA', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Dw[/B]', action = 'list_tubes', url = host + 'watch?v=KQa4APEXnsQ&list=UULFQ1GpKa15ulyoQuxz7H4rng', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Explora Planet[/B]', action = 'list_tubes', url = host + 'watch?v=YfaCxrEaz9E&list=UULFwRvBitYM27PF-Yz2LSfABA', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Gran Misterio[/B]', action = 'list_tubes', url = host + 'watch?v=8fz92RfijrA&list=PL64vL0ABVyDhWJPIWUfrjopSaR-TUqmoF', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Historias Vivas[/B]', action = 'list_tubes', url = host + 'watch?v=F7EJdtHtF2c&list=UULPAx8AK17j6BKqdQefiHWGag', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Lethal Crysis[/B]', action = 'list_tubes', url = host + 'watch?v=ZUOHjzEGJPM&list=UULFJCen5xxTtU7cnVHe3n424A', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Misterios Ocultos[/B]', action = 'list_tubes', url = host + 'watch?v=0tWiCBpgql0&list=PLV108z4JVKq9qlcn3MJBkH-lB--T11G2E', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Pero Eso Es Otra Historia[/B]', action = 'list_tubes', url = host + 'watch?v=9kMhQU_ZIDw&list=UULFBIMW0ZhwULY_x7fdaPRPiQ', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Planet Doc[/B]', action = 'list_tubes', url = host + 'watch?v=NvjeAx0eqT4&list=UULF-cLXV_UA6EnqfjbpNoGaIw', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Rtve[/B]', action = 'list_tubes', url = host + 'watch?v=b9oq4medEiU&list=PLFLBjMW4wU7jWKp3V_k8pw8HH4d-AAy9M', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Rubén Villalobos[/B]', action = 'list_tubes', url = host + 'watch?v=Z2N9UtC-ppI&list=UULF0QO3TaHg14sRc3pPFmaXnQ&index=2', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Show Me The World[/B]', action = 'list_tubes', url = host + 'watch?v=_GcAK3xuuTM&list=UULF1W_Jc9UmyttYlSo0i5DzJg', text_color = 'cyan'))

    itemlist.append(item.clone( title = '- [B]Wild Stories[/B]', action = 'list_tubes', url = host + 'watch?v=2FVMl7zq9G4&list=UULFGtFh-sO0mpk5dgEXVzMhKw', text_color = 'cyan'))

    return itemlist


def list_tubes(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data

    bloque = scrapertools.find_single_match(str(data), '"playlist":.*?"playlist":.*?"title":(.*?)$')

    matches = scrapertools.find_multiple_matches(str(bloque), 'playlistPanelVideoRenderer":.*?simpleText":"(.*?)".*?"videoId":"(.*?)".*?"playlistId"')

    for title, _id in matches:
        if not _id or not title: continue

        title = title.replace('(Documental)', '').replace('(DOCUMENTAL COMPLETO)', '').replace('- Documental', '').replace('| DW Documental', '').replace('| HD Documental', '')
        title = title.replace('🇪🇦', '').replace('☠️', '').replace('🌎', '').replace('✅✅✅', '').strip()

        thumb = 'https://i.ytimg.com/vi/' + _id + '/hqdefault.jpg'

        url = 'https://www.youtube.com/watch?v=' + _id

        itemlist.append(item.clone( action = 'findvideos', title = title, url = url, thumbnail = thumb ))

    return itemlist


def findvideos(item):
    logger.info()
    itemlist = []

    itemlist.append(Item( channel = item.channel, action = 'play', server = 'youtube', language = 'Esp', url = item.url ))

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
