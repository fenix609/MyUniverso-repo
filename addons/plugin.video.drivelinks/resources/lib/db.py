# -*- coding: utf-8 -*-
"""Biblioteca local (JSON) guardada en el perfil del addon."""
import json
import os
import xbmcaddon
import xbmcvfs

_ADDON = xbmcaddon.Addon()
_PROFILE = xbmcvfs.translatePath(_ADDON.getAddonInfo('profile'))
_FILE = os.path.join(_PROFILE, 'library.json')


def load():
    try:
        with open(_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save(items):
    if not os.path.isdir(_PROFILE):
        os.makedirs(_PROFILE)
    with open(_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)


def add_many(new_items):
    """Añade items nuevos (evita duplicados por id). Devuelve cuántos se añadieron."""
    items = load()
    known = {i['id'] for i in items}
    n = 0
    for it in new_items:
        if it['id'] not in known:
            items.append(it)
            known.add(it['id'])
            n += 1
    save(items)
    return n


def remove(file_id):
    save([i for i in load() if i['id'] != file_id])


def update(file_id, **fields):
    items = load()
    for i in items:
        if i['id'] == file_id:
            i.update(fields)
    save(items)


def remove_group(kind, key, value):
    """Borra todos los items de un tipo cuyo campo key == value (serie o álbum)."""
    save([i for i in load() if not (i['type'] == kind and i.get(key) == value)])


def get(file_id):
    for i in load():
        if i['id'] == file_id:
            return i
    return None


def add_sub(file_id, sub):
    items = load()
    for i in items:
        if i['id'] == file_id:
            subs = i.setdefault('subs', [])
            if sub['id'] not in {x['id'] for x in subs}:
                subs.append(sub)
    save(items)
