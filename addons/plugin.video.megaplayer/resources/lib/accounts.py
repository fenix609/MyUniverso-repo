# -*- coding: utf-8 -*-
import xbmcaddon

MAX_ACCOUNTS = 5


def _key(i, field):
    # La cuenta 1 conserva los ajustes de versiones anteriores (email, password, mfa)
    if i == 1 and field != 'name':
        return field
    return 'acc%d_%s' % (i, field)


def get_accounts():
    a = xbmcaddon.Addon()
    out = []
    for i in range(1, MAX_ACCOUNTS + 1):
        email = a.getSetting(_key(i, 'email')).strip()
        if not email:
            continue
        out.append({
            'id': str(i),
            'name': a.getSetting(_key(i, 'name')).strip() or email,
            'email': email,
            'password': a.getSetting(_key(i, 'password')),
            'mfa': a.getSetting(_key(i, 'mfa')),
        })
    return out
