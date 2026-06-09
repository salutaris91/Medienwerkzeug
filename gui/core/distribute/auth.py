import json
import logging
from typing import Optional
import bcrypt
from gui.core.distribute.db import get_connection

logger = logging.getLogger(__name__)


def register_user(email: str, password: str) -> dict:
    if not email or not password:
        raise ValueError("E-Mail und Passwort sind erforderlich.")
    if len(password) < 8:
        raise ValueError("Passwort muss mindestens 8 Zeichen haben.")

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email.lower().strip(), password_hash)
            )
            user_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO user_settings (user_id) VALUES (?)",
                (user_id,)
            )
        logger.info("New user registered: %s (id=%d)", email, user_id)
        return {"id": user_id, "email": email.lower().strip()}
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise ValueError("Diese E-Mail-Adresse ist bereits registriert.")
        raise RuntimeError(f"Registrierung fehlgeschlagen: {e}")


def login_user(email: str, password: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.lower().strip(),)
        ).fetchone()

    if not row:
        return None

    if not bcrypt.checkpw(password.encode('utf-8'), row['password_hash'].encode('utf-8')):
        return None

    return {"id": row['id'], "email": row['email']}


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_platform_token(user_id: int, platform: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT config_json FROM platform_tokens WHERE user_id = ? AND platform = ?",
            (user_id, platform)
        ).fetchone()
    return json.loads(row['config_json']) if row else None


def save_platform_token(user_id: int, platform: str, config: dict) -> None:
    config_json = json.dumps(config)
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO platform_tokens (user_id, platform, config_json)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, platform) DO UPDATE SET
                config_json = excluded.config_json,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, platform, config_json))


def delete_platform_token(user_id: int, platform: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM platform_tokens WHERE user_id = ? AND platform = ?",
            (user_id, platform)
        )


def get_connected_platforms(user_id: int) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT platform FROM platform_tokens WHERE user_id = ?",
            (user_id,)
        ).fetchall()
    return [row['platform'] for row in rows]


def get_user_settings(user_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ai_provider, ai_api_key, ai_model, openrouter_model FROM user_settings WHERE user_id = ?",
            (user_id,)
        ).fetchone()
    if not row:
        return {"ai_provider": "anthropic", "ai_api_key": None, "ai_model": "claude-haiku-4-5-20251001", "openrouter_model": "anthropic/claude-haiku"}
    return dict(row)


def save_user_settings(user_id: int, settings: dict) -> None:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO user_settings (user_id, ai_provider, ai_api_key, ai_model, openrouter_model)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                ai_provider = excluded.ai_provider,
                ai_api_key = excluded.ai_api_key,
                ai_model = excluded.ai_model,
                openrouter_model = excluded.openrouter_model
        """, (
            user_id,
            settings.get('ai_provider', 'anthropic'),
            settings.get('ai_api_key'),
            settings.get('ai_model', 'claude-haiku-4-5-20251001'),
            settings.get('openrouter_model', 'anthropic/claude-haiku')
        ))
