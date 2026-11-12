# -*- coding: utf-8 -*-
"""
Inicio de sesión con Google (OAuth 2.0 + PKCE, flujo "aplicación de escritorio").
La contraseña NUNCA pasa por el addon: se escribe en la página de Google.
Solo se guarda un token de acceso de SOLO LECTURA (drive.readonly) en el perfil.
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
PORT = 8765
REDIRECT = 'http://127.0.0.1:%d' % PORT

_PROFILE = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
_TOKEN_FILE = os.path.join(_PROFILE, 'token.json')
_MEM = {}


class AuthError(Exception):
    def __init__(self, msg, code=None):
        Exception.__init__(self, msg)
        self.code = code


# ------------------------------------------------------------ almacenamiento
def credentials():
    a = xbmcaddon.Addon()
    return a.getSetting('client_id').strip(), a.getSetting('client_secret').strip()


def _load():
    if 'tok' in _MEM:
        return _MEM['tok']
    try:
        with open(_TOKEN_FILE, 'r', encoding='utf-8') as f:
            _MEM['tok'] = json.load(f)
    except Exception:
        _MEM['tok'] = {}
    return _MEM['tok']


def _save(data):
    _MEM['tok'] = data
    if not os.path.isdir(_PROFILE):
        os.makedirs(_PROFILE)
    with open(_TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def is_logged_in():
    return bool(_load().get('refresh_token'))


def account_label():
    return _load().get('email', '')


def logout():
    _MEM.clear()
    try:
        os.remove(_TOKEN_FILE)
    except OSError:
        pass
    _MEM['tok'] = {}


# ------------------------------------------------------------ red
def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode('utf-8'))
        except Exception:
            err = {}
        raise AuthError(err.get('error_description') or err.get('error') or 'HTTP %d' % e.code,
                        err.get('error'))
    except urllib.error.URLError as e:
        raise AuthError('Sin conexión con Google: %s' % e.reason)


def get_token(min_valid=300):
    """Devuelve un access_token válido al menos `min_valid` segundos (lo renueva si hace falta)."""
    t = _load()
    if not t.get('refresh_token'):
        raise AuthError('No has iniciado sesión')
    remaining = t.get('expires_at', 0) - time.time()
    if t.get('access_token') and remaining > min_valid:
        return t['access_token']
    cid, sec = credentials()
    try:
        r = _post(TOKEN_URL, {'client_id': cid, 'client_secret': sec,
                              'refresh_token': t['refresh_token'],
                              'grant_type': 'refresh_token'})
    except AuthError as e:
        if e.code == 'invalid_grant':
            logout()
            raise AuthError('La sesión ha caducado o se revocó. Inicia sesión de nuevo.')
        if t.get('access_token') and remaining > 60:
            return t['access_token']      # fallo de red puntual: seguimos con el actual
        raise
    t['access_token'] = r['access_token']
    t['expires_at'] = time.time() + int(r.get('expires_in', 3600))
    _save(t)
    return t['access_token']


def _fetch_email(token):
    try:
        req = urllib.request.Request(
            'https://www.googleapis.com/drive/v3/about?fields=user(emailAddress,displayName)',
            headers={'Authorization': 'Bearer ' + token})
        with urllib.request.urlopen(req, timeout=20) as r:
            u = json.loads(r.read().decode('utf-8')).get('user', {})
            return u.get('emailAddress') or u.get('displayName') or ''
    except Exception:
        return ''


# ------------------------------------------------------------ login
def _pkce():
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge


def _open_browser(url):
    try:
        if xbmc.getCondVisibility('System.Platform.Android'):
            xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.VIEW","","%s")' % url)
        else:
            webbrowser.open(url)
    except Exception as e:
        xbmc.log('DriveLinks navegador: %s' % e, xbmc.LOGWARNING)


def _wait_local(url, state):
    """Abre el navegador y espera la redirección a 127.0.0.1. Devuelve el code o None."""
    class Handler(http.server.BaseHTTPRequestHandler):
        result = {}

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if 'code' in q or 'error' in q:
                Handler.result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('<html><body style="font-family:sans-serif;text-align:center;'
                             'margin-top:15%"><h2>Listo</h2><p>Ya puedes volver a Kodi.'
                             '</p></body></html>'.encode('utf-8'))

        def log_message(self, *a):
            pass

    try:
        srv = http.server.HTTPServer(('127.0.0.1', PORT), Handler)
    except OSError:
        return None
    srv.timeout = 1
    _open_browser(url)
    prog = xbmcgui.DialogProgress()
    prog.create('Iniciar sesión con Google',
                'Completa el inicio de sesión en el navegador.\n'
                'Pulsa Cancelar para pegar la dirección a mano.')
    start, total = time.time(), 240
    try:
        while (time.time() - start < total and not prog.iscanceled()
               and 'code' not in Handler.result and 'error' not in Handler.result):
            prog.update(int((time.time() - start) * 100 / total))
            srv.handle_request()
    finally:
        prog.close()
        srv.server_close()
    res = Handler.result
    if res.get('error'):
        raise AuthError('Google respondió: %s' % res['error'])
    if res.get('code') and res.get('state') == state:
        return res['code']
    return None


def _parse_pasted(text, state):
    text = (text or '').strip()
    if not text:
        return None
    if text.lower().startswith('http'):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
        if 'error' in q:
            raise AuthError('Google respondió: %s' % q['error'][0])
        if q.get('state') and q['state'][0] != state:
            raise AuthError('La dirección pegada no corresponde a este intento de inicio de sesión.')
        return (q.get('code') or [None])[0]
    return urllib.parse.unquote(text)


def login():
    """Flujo completo. Devuelve 'ok' o 'cancel'; lanza AuthError si falla."""
    cid, sec = credentials()
    if not cid or not sec:
        raise AuthError('Faltan el Client ID y el Client Secret en los ajustes.')
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + '?' + urllib.parse.urlencode({
        'client_id': cid, 'redirect_uri': REDIRECT, 'response_type': 'code',
        'scope': SCOPE, 'code_challenge': challenge, 'code_challenge_method': 'S256',
        'access_type': 'offline', 'prompt': 'consent', 'state': state})

    dlg = xbmcgui.Dialog()
    opt = dlg.select('Iniciar sesión con Google',
                     ['En este dispositivo (abre el navegador)',
                      'En otro dispositivo (móvil u ordenador)'])
    if opt < 0:
        return 'cancel'
    code = None
    if opt == 0:
        code = _wait_local(url, state)
        if not code and not dlg.yesno('Drive Links',
                                      'No se recibió respuesta.\n¿Quieres pegar la dirección a mano?'):
            return 'cancel'
    if not code:
        if opt == 1:
            dlg.textviewer('Iniciar sesión en otro dispositivo',
                           '1. En tu móvil u ordenador abre esta dirección:\n\n%s\n\n'
                           '2. Inicia sesión y acepta el permiso de SOLO LECTURA.\n'
                           '3. Al final la página dará un error ("no se puede conectar" o similar). '
                           'Es normal.\n'
                           '4. Copia la dirección COMPLETA de esa página (empieza por '
                           'http://127.0.0.1:8765/?state=...) y pégala en el siguiente cuadro.' % url)
        pasted = dlg.input('Pega la dirección completa (o solo el código)',
                           type=xbmcgui.INPUT_ALPHANUM)
        code = _parse_pasted(pasted, state)
    if not code:
        return 'cancel'

    r = _post(TOKEN_URL, {'code': code, 'client_id': cid, 'client_secret': sec,
                          'redirect_uri': REDIRECT, 'grant_type': 'authorization_code',
                          'code_verifier': verifier})
    if not r.get('refresh_token'):
        raise AuthError('Google no devolvió permiso persistente. Quita el acceso de la app en '
                        'myaccount.google.com/permissions y vuelve a intentarlo.')
    data = {'access_token': r['access_token'], 'refresh_token': r['refresh_token'],
            'expires_at': time.time() + int(r.get('expires_in', 3600))}
    data['email'] = _fetch_email(data['access_token'])
    _save(data)
    return 'ok'
