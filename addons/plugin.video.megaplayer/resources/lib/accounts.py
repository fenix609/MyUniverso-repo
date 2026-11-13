# -*- coding: utf-8 -*-
"""Cuentas MEGA ilimitadas, guardadas en accounts.json dentro de la carpeta de datos del addon."""
import json, os
import xbmcaddon, xbmcvfs


def _path():
    d = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'accounts.json')


def _legacy():
    """Importa las cuentas 1-5 que tuvieras en los ajustes de versiones anteriores."""
    a = xbmcaddon.Addon()
    out = []
    for i in range(1, 6):
        def k(field):
            return field if (i == 1 and field != 'name') else 'acc%d_%s' % (i, field)
        email = a.getSetting(k('email')).strip()
        if email:
            out.append({'id': str(i), 'name': a.getSetting(k('name')).strip() or email, 'email': email,
                        'password': a.getSetting(k('password')), 'mfa': a.getSetting(k('mfa'))})
    return out


def _save(data):
    p = _path()
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def _load():
    p = _path()
    if os.path.exists(p):
        try:
            with open(p, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'next_id': 1000, 'accounts': _legacy()}
    accs = _legacy()
    data = {'next_id': (max(int(x['id']) for x in accs) + 1) if accs else 1, 'accounts': accs}
    _save(data)
    return data


def get_accounts():
    return _load()['accounts']


def add_account(name, email, password, mfa=''):
    data = _load()
    aid = str(data['next_id'])
    data['next_id'] += 1
    data['accounts'].append({'id': aid, 'name': name or email, 'email': email, 'password': password, 'mfa': mfa})
    _save(data)
    return aid


def update_account(aid, **fields):
    data = _load()
    for a in data['accounts']:
        if a['id'] == aid:
            a.update(fields)
    _save(data)


def delete_account(aid):
    data = _load()
    data['accounts'] = [a for a in data['accounts'] if a['id'] != aid]
    _save(data)
