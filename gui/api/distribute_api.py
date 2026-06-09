import os
import secrets
import logging
from collections import defaultdict
from time import time
from functools import wraps

from flask import Blueprint, request, jsonify, session, redirect

from gui.core.distribute.db import init_db
from gui.core.distribute import auth as auth_service
from gui.core.distribute.politicians import search_politicians, get_politician_by_id, get_available_platforms
from gui.core.distribute.moderation import moderate
from gui.core.distribute.connectors.x_connector import XConnector
from gui.core.distribute.connectors.mastodon_connector import MastodonConnector
from gui.core.distribute.connectors.bluesky_connector import BlueskyConnector
from gui.core.distribute.connectors.email_connector import EmailConnector

logger = logging.getLogger(__name__)

distribute_api = Blueprint('distribute_api', __name__)

init_db()

CONNECTORS = {
    'x': XConnector(),
    'mastodon': MastodonConnector(),
    'bluesky': BlueskyConnector(),
    'email': EmailConnector(),
}

_rate_limit_store: dict[str, list[float]] = defaultdict(list)


def _is_rate_limited(key: str, limit: int = 10, window: int = 60) -> bool:
    now = time()
    cutoff = now - window
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > cutoff]
    if len(_rate_limit_store[key]) >= limit:
        return True
    _rate_limit_store[key].append(now)
    return False


def _require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Nicht eingeloggt.'}), 401
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/auth/register', methods=['POST'])
def register():
    ip = request.remote_addr or 'unknown'
    if _is_rate_limited(f'register:{ip}', limit=5, window=300):
        return jsonify({'error': 'Zu viele Versuche. Bitte warte 5 Minuten.'}), 429

    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    try:
        user = auth_service.register_user(email, password)
        session['user_id'] = user['id']
        return jsonify({'user': {'id': user['id'], 'email': user['email']}}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except RuntimeError as e:
        logger.error("Registration error: %s", e)
        return jsonify({'error': str(e)}), 500


@distribute_api.route('/distribute/auth/login', methods=['POST'])
def login():
    ip = request.remote_addr or 'unknown'
    if _is_rate_limited(f'login:{ip}', limit=10, window=60):
        return jsonify({'error': 'Zu viele Login-Versuche. Bitte warte eine Minute.'}), 429

    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    user = auth_service.login_user(email, password)
    if not user:
        return jsonify({'error': 'E-Mail oder Passwort falsch.'}), 401

    session['user_id'] = user['id']
    return jsonify({'user': {'id': user['id'], 'email': user['email']}})


@distribute_api.route('/distribute/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'ok': True})


@distribute_api.route('/distribute/auth/me', methods=['GET'])
@_require_login
def me():
    user = auth_service.get_user_by_id(session['user_id'])
    if not user:
        session.pop('user_id', None)
        return jsonify({'error': 'Nutzer nicht gefunden.'}), 404

    connected = auth_service.get_connected_platforms(user['id'])
    return jsonify({'user': user, 'connected_platforms': connected})


# ---------------------------------------------------------------------------
# Settings endpoints
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/settings', methods=['GET'])
@_require_login
def get_settings():
    settings = auth_service.get_user_settings(session['user_id'])
    # Never return the raw API key to the frontend — only indicate if set
    has_key = bool(settings.get('ai_api_key'))
    return jsonify({
        'ai_provider': settings['ai_provider'],
        'ai_key_set': has_key,
        'ai_model': settings['ai_model'],
        'openrouter_model': settings['openrouter_model'],
    })


@distribute_api.route('/distribute/settings', methods=['PUT'])
@_require_login
def update_settings():
    data = request.get_json() or {}
    allowed = {'ai_provider', 'ai_api_key', 'ai_model', 'openrouter_model'}
    settings = {k: v for k, v in data.items() if k in allowed}

    if 'ai_provider' in settings and settings['ai_provider'] not in ('anthropic', 'openrouter'):
        return jsonify({'error': 'Ungültiger AI-Provider. Erlaubt: anthropic, openrouter'}), 400

    auth_service.save_user_settings(session['user_id'], settings)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# Platform connection management
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/platforms', methods=['GET'])
@_require_login
def get_platforms():
    connected = auth_service.get_connected_platforms(session['user_id'])
    platforms = []
    for platform_id, connector in CONNECTORS.items():
        token_config = auth_service.get_platform_token(session['user_id'], platform_id) or {}
        platforms.append({
            'id': platform_id,
            'name': connector.platform_name,
            'connected': platform_id in connected and connector.is_connected(token_config),
        })
    return jsonify({'platforms': platforms})


@distribute_api.route('/distribute/platforms/<platform_id>', methods=['DELETE'])
@_require_login
def disconnect_platform(platform_id: str):
    if platform_id not in CONNECTORS:
        return jsonify({'error': 'Unbekannte Plattform.'}), 404
    auth_service.delete_platform_token(session['user_id'], platform_id)
    return jsonify({'ok': True})


# Bluesky: app-password based (no OAuth redirect needed)
@distribute_api.route('/distribute/platforms/bluesky/connect', methods=['POST'])
@_require_login
def connect_bluesky():
    data = request.get_json() or {}
    handle = data.get('handle', '').strip().lstrip('@')
    app_password = data.get('app_password', '').strip()

    if not handle or not app_password:
        return jsonify({'error': 'Handle und App-Passwort erforderlich.'}), 400

    try:
        from atproto import Client
        client = Client()
        client.login(handle, app_password)
    except Exception as e:
        return jsonify({'error': f'Bluesky-Login fehlgeschlagen: {e}'}), 400

    auth_service.save_platform_token(session['user_id'], 'bluesky', {
        'handle': handle,
        'app_password': app_password
    })
    return jsonify({'ok': True})


# Email: SMTP settings (manual)
@distribute_api.route('/distribute/platforms/email/connect', methods=['POST'])
@_require_login
def connect_email():
    data = request.get_json() or {}
    required = ['smtp_host', 'smtp_user', 'smtp_password', 'from_address']
    missing = [f for f in required if not data.get(f, '').strip()]
    if missing:
        return jsonify({'error': f'Fehlende Felder: {", ".join(missing)}'}), 400

    config = {
        'smtp_host': data['smtp_host'].strip(),
        'smtp_port': int(data.get('smtp_port', 587)),
        'smtp_user': data['smtp_user'].strip(),
        'smtp_password': data['smtp_password'],
        'from_address': data['from_address'].strip(),
    }
    auth_service.save_platform_token(session['user_id'], 'email', config)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# OAuth: X (Twitter) — OAuth 2.0 PKCE
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/oauth/x/start', methods=['GET'])
@_require_login
def oauth_x_start():
    client_id = os.environ.get('X_CLIENT_ID')
    redirect_uri = os.environ.get('X_REDIRECT_URI')
    if not client_id or not redirect_uri:
        return jsonify({'error': 'X OAuth nicht konfiguriert. X_CLIENT_ID und X_REDIRECT_URI in .env setzen.'}), 503

    try:
        import tweepy
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
            client_secret=os.environ.get('X_CLIENT_SECRET'),
        )
        auth_url = oauth2_user_handler.get_authorization_url()
        # Store the handler's code_verifier in session for the callback
        session['x_oauth_state'] = oauth2_user_handler.state
        session['x_oauth_code_verifier'] = oauth2_user_handler.code_verifier
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        logger.error("X OAuth start failed: %s", e)
        return jsonify({'error': f'OAuth-Start fehlgeschlagen: {e}'}), 500


@distribute_api.route('/distribute/oauth/x/callback', methods=['GET'])
def oauth_x_callback():
    if 'user_id' not in session:
        return redirect('/?error=not_logged_in#/settings')

    code = request.args.get('code')
    state = request.args.get('state')

    if not code or state != session.get('x_oauth_state'):
        return redirect('/?error=oauth_invalid#/settings')

    client_id = os.environ.get('X_CLIENT_ID')
    redirect_uri = os.environ.get('X_REDIRECT_URI')

    try:
        import tweepy
        oauth2_user_handler = tweepy.OAuth2UserHandler(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
            client_secret=os.environ.get('X_CLIENT_SECRET'),
        )
        oauth2_user_handler.state = session.pop('x_oauth_state', None)
        oauth2_user_handler.code_verifier = session.pop('x_oauth_code_verifier', None)

        token_data = oauth2_user_handler.fetch_token(
            f"{redirect_uri}?code={code}&state={state}"
        )
        auth_service.save_platform_token(session['user_id'], 'x', {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
        })
        return redirect('/?success=x_connected#/settings')
    except Exception as e:
        logger.error("X OAuth callback failed: %s", e)
        return redirect(f'/?error=oauth_failed#/settings')


# ---------------------------------------------------------------------------
# OAuth: Mastodon — OAuth 2.0 per instance
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/oauth/mastodon/start', methods=['POST'])
@_require_login
def oauth_mastodon_start():
    data = request.get_json() or {}
    instance_url = data.get('instance_url', '').strip().rstrip('/')

    if not instance_url.startswith('https://'):
        return jsonify({'error': 'Instanz-URL muss mit https:// beginnen.'}), 400

    redirect_uri = os.environ.get('MASTODON_REDIRECT_URI')
    if not redirect_uri:
        return jsonify({'error': 'MASTODON_REDIRECT_URI in .env nicht gesetzt.'}), 503

    try:
        from mastodon import Mastodon
        from gui.core.distribute.db import get_connection

        with get_connection() as conn:
            row = conn.execute(
                "SELECT client_id, client_secret FROM mastodon_app_registrations WHERE instance_url = ?",
                (instance_url,)
            ).fetchone()

        if row:
            client_id, client_secret = row['client_id'], row['client_secret']
        else:
            client_id, client_secret = Mastodon.create_app(
                'Medienwerkzeug Kritik-Tool',
                api_base_url=instance_url,
                redirect_uris=redirect_uri,
                scopes=['read', 'write'],
            )
            with get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO mastodon_app_registrations (instance_url, client_id, client_secret) VALUES (?,?,?)",
                    (instance_url, client_id, client_secret)
                )

        mastodon = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=instance_url)
        auth_url = mastodon.auth_request_url(redirect_uris=redirect_uri, scopes=['read', 'write'])

        session['mastodon_oauth_instance'] = instance_url
        session['mastodon_oauth_client_id'] = client_id
        session['mastodon_oauth_client_secret'] = client_secret

        return jsonify({'auth_url': auth_url})
    except Exception as e:
        logger.error("Mastodon OAuth start failed: %s", e)
        return jsonify({'error': f'Mastodon OAuth-Start fehlgeschlagen: {e}'}), 500


@distribute_api.route('/distribute/oauth/mastodon/callback', methods=['GET'])
def oauth_mastodon_callback():
    if 'user_id' not in session:
        return redirect('/?error=not_logged_in#/settings')

    code = request.args.get('code')
    if not code:
        return redirect('/?error=oauth_invalid#/settings')

    instance_url = session.pop('mastodon_oauth_instance', None)
    client_id = session.pop('mastodon_oauth_client_id', None)
    client_secret = session.pop('mastodon_oauth_client_secret', None)
    redirect_uri = os.environ.get('MASTODON_REDIRECT_URI')

    if not all([instance_url, client_id, client_secret, redirect_uri]):
        return redirect('/?error=oauth_session_expired#/settings')

    try:
        from mastodon import Mastodon
        mastodon = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=instance_url)
        access_token = mastodon.log_in(
            code=code,
            redirect_uri=redirect_uri,
            scopes=['read', 'write']
        )
        auth_service.save_platform_token(session['user_id'], 'mastodon', {
            'access_token': access_token,
            'instance_url': instance_url,
        })
        return redirect('/?success=mastodon_connected#/settings')
    except Exception as e:
        logger.error("Mastodon OAuth callback failed: %s", e)
        return redirect('/?error=oauth_failed#/settings')


# ---------------------------------------------------------------------------
# Politicians
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/politicians', methods=['GET'])
def get_politicians():
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    politicians = search_politicians(query, category)
    return jsonify({'politicians': politicians})


@distribute_api.route('/distribute/politicians/<politician_id>', methods=['GET'])
def get_politician(politician_id: str):
    politician = get_politician_by_id(politician_id)
    if not politician:
        return jsonify({'error': 'Politiker nicht gefunden.'}), 404
    return jsonify({'politician': politician})


# ---------------------------------------------------------------------------
# Moderation check
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/moderate', methods=['POST'])
def check_moderation():
    ip = request.remote_addr or 'unknown'
    if _is_rate_limited(f'moderate:{ip}', limit=30, window=60):
        return jsonify({'error': 'Rate limit erreicht.'}), 429

    data = request.get_json() or {}
    text = data.get('text', '').strip()

    if not text:
        return jsonify({'error': 'Kein Text angegeben.'}), 400
    if len(text) > 2000:
        return jsonify({'error': 'Text zu lang (max. 2000 Zeichen).'}), 400

    user_settings = None
    if 'user_id' in session:
        user_settings = auth_service.get_user_settings(session['user_id'])

    result = moderate(text, user_settings)
    return jsonify(result)


# ---------------------------------------------------------------------------
# Send to platforms
# ---------------------------------------------------------------------------

@distribute_api.route('/distribute/send', methods=['POST'])
@_require_login
def send_to_platforms():
    ip = request.remote_addr or 'unknown'
    if _is_rate_limited(f'send:{session["user_id"]}', limit=5, window=60):
        return jsonify({'error': 'Zu viele Sendeanfragen. Bitte warte eine Minute.'}), 429

    data = request.get_json() or {}
    text = data.get('text', '').strip()
    politician_id = data.get('politician_id', '').strip()
    selected_platforms = data.get('platforms', [])

    if not text:
        return jsonify({'error': 'Kein Text angegeben.'}), 400
    if len(text) > 2000:
        return jsonify({'error': 'Text zu lang (max. 2000 Zeichen).'}), 400
    if not politician_id:
        return jsonify({'error': 'Kein Politiker ausgewählt.'}), 400
    if not selected_platforms:
        return jsonify({'error': 'Keine Plattformen ausgewählt.'}), 400

    user_settings = auth_service.get_user_settings(session['user_id'])
    mod_result = moderate(text, user_settings)
    if not mod_result['approved']:
        return jsonify({'error': 'Text nicht freigegeben.', 'moderation': mod_result}), 422

    politician = get_politician_by_id(politician_id)
    if not politician:
        return jsonify({'error': 'Politiker nicht gefunden.'}), 404

    results = []
    for platform_id in selected_platforms:
        connector = CONNECTORS.get(platform_id)
        if not connector:
            results.append({'success': False, 'platform': platform_id, 'message': 'Unbekannte Plattform.', 'url': None})
            continue

        platform_target = politician.get('platforms', {}).get(platform_id)
        if not platform_target:
            results.append({
                'success': False,
                'platform': connector.platform_name,
                'message': f'{politician["name"]} ist auf {connector.platform_name} nicht erreichbar.',
                'url': None
            })
            continue

        token_config = auth_service.get_platform_token(session['user_id'], platform_id) or {}
        result = connector.send(text, platform_target, token_config)
        results.append(result)
        logger.info("send result for user=%d platform=%s success=%s", session['user_id'], platform_id, result['success'])

    return jsonify({'results': results})
