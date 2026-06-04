import os
import hashlib
from flask import request, session, abort, redirect
from gui.core.persistence import load_settings

def auth_before_request():
    settings = load_settings()
    onboarded = settings.get("onboarded", False)

    # 1. Allowlist exceptions that bypass onboarding-block completely
    is_allowlist = (
        request.endpoint == 'static' or
        request.path == '/' or
        request.path == '/favicon.ico' or
        request.path.startswith('/api/onboarding/') or
        request.path == '/api/keys' or
        request.path == '/api/system/capabilities' or
        request.path == '/api/check-dependencies' or
        request.path == '/api/auth/login' or
        request.path == '/api/auth/status'
    )

    if not is_allowlist and not onboarded:
        abort(403, "Setup erforderlich")

    # 2. Check if authentication is active (password_hash is set)
    password_hash = settings.get("password_hash", "")

    if password_hash:
        # Bypassed routes for auth when password is active
        if request.path in ('/api/auth/login', '/api/onboarding/set-password', '/api/auth/status'):
            return

        # Check session authentication state
        authenticated = session.get('authenticated', False)

        # Calculate current hash fingerprint
        current_version = hashlib.sha256(password_hash.encode('utf-8')).hexdigest()
        session_version = session.get('auth_version')

        if not authenticated or session_version != current_version:
            # Session is invalid or expired
            session.clear()
            if request.path.startswith('/api/'):
                abort(401, "Authentication required")
            else:
                return redirect('/')

        # 3. CSRF Token Validation for state-changing requests
        # (POST, PUT, DELETE) when authentication is active
        if request.method in ('POST', 'PUT', 'DELETE'):
            csrf_token = request.headers.get('X-CSRF-Token')
            csrf_hash = session.get('csrf_hash')

            if not csrf_token or not csrf_hash:
                abort(400, "CSRF validation failed: Missing token or session hash")

            # Verify SHA-256 hash match
            computed_hash = hashlib.sha256(csrf_token.encode('utf-8')).hexdigest()
            if computed_hash != csrf_hash:
                abort(400, "CSRF validation failed: Invalid token")
    else:
        # No password set: Allowlist routes bypass everything completely
        if is_allowlist:
            return
