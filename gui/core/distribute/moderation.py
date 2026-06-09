import json
import logging
import requests
from typing import TypedDict

logger = logging.getLogger(__name__)

HARD_BLOCKLIST = [
    "arschloch", "wichser", "hurensohn", "drecksau", "scheißkerl",
    "vollidiot", "blödmann", "schwachkopf", "wichsvorlage",
    "dreckstück", "mistkerl", "dummkopf", "penner", "loser",
    "verpissdich", "verpiss dich", "fick dich", "fick euch",
    "zum teufel", "zur hölle", "geht zum teufel",
]

SOFT_WARNINGLIST = [
    "lügner", "lügt", "korrupt", "kriminell", "versager",
    "unfähig", "inkompetent", "betrüger", "heuchler", "verräter",
    "schande", "schämt euch", "schäm dich",
]


class ModerationResult(TypedDict):
    approved: bool
    reason: str
    severity: str
    flagged_terms: list[str]


def _check_wordlist(text: str) -> ModerationResult:
    text_lower = text.lower()

    flagged_hard = [term for term in HARD_BLOCKLIST if term in text_lower]
    if flagged_hard:
        return {
            'approved': False,
            'reason': f"Der Text enthält inakzeptable Ausdrücke: {', '.join(flagged_hard)}. Bitte sachlich formulieren.",
            'severity': 'blocked',
            'flagged_terms': flagged_hard
        }

    flagged_soft = [term for term in SOFT_WARNINGLIST if term in text_lower]
    if flagged_soft:
        return {
            'approved': True,
            'reason': f"Hinweis: Möglicherweise wertende Sprache erkannt ({', '.join(flagged_soft)}). Bitte nur verwenden wenn sachlich belegbar.",
            'severity': 'warning',
            'flagged_terms': flagged_soft
        }

    return {
        'approved': True,
        'reason': 'Text scheint sachlich.',
        'severity': 'ok',
        'flagged_terms': []
    }


def _check_with_anthropic(text: str, api_key: str, model: str) -> ModerationResult:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": _build_moderation_prompt(text)
            }]
        )
        return _parse_ai_response(message.content[0].text)
    except Exception as e:
        logger.warning("Anthropic moderation check failed: %s", e)
        return {'approved': True, 'reason': f'KI-Prüfung fehlgeschlagen: {e}', 'severity': 'ok', 'flagged_terms': []}


def _check_with_openrouter(text: str, api_key: str, model: str) -> ModerationResult:
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://medienwerkzeug.app",
                "X-Title": "Medienwerkzeug Kritik-Tool"
            },
            json={
                "model": model,
                "max_tokens": 256,
                "messages": [{"role": "user", "content": _build_moderation_prompt(text)}]
            },
            timeout=10
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        return _parse_ai_response(content)
    except Exception as e:
        logger.warning("OpenRouter moderation check failed: %s", e)
        return {'approved': True, 'reason': f'KI-Prüfung fehlgeschlagen: {e}', 'severity': 'ok', 'flagged_terms': []}


def _build_moderation_prompt(text: str) -> str:
    return f"""Prüfe diesen deutschen Text auf Beleidigungen, Hetze oder unangemessene Sprache.
Ziel: sachliche politische Kritik soll erlaubt sein, persönliche Angriffe nicht.
Antworte NUR mit JSON (kein Markdown, kein Text drumherum):
{{"approved": true, "reason": "kurze Begründung auf Deutsch", "severity": "ok"}}
oder
{{"approved": false, "reason": "was genau das Problem ist", "severity": "blocked"}}

Text: {text}"""


def _parse_ai_response(raw: str) -> ModerationResult:
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return {
            'approved': bool(result.get('approved', True)),
            'reason': str(result.get('reason', '')),
            'severity': str(result.get('severity', 'ok')),
            'flagged_terms': []
        }
    except Exception as e:
        logger.warning("Could not parse AI moderation response: %s — raw: %s", e, raw[:200])
        return {'approved': True, 'reason': 'KI-Antwort konnte nicht verarbeitet werden.', 'severity': 'ok', 'flagged_terms': []}


def moderate(text: str, user_settings: dict | None = None) -> ModerationResult:
    wordlist_result = _check_wordlist(text)

    if wordlist_result['severity'] == 'blocked':
        return wordlist_result

    settings = user_settings or {}
    api_key = settings.get('ai_api_key')
    provider = settings.get('ai_provider', 'anthropic')

    if not api_key:
        return wordlist_result

    if wordlist_result['severity'] == 'warning':
        if provider == 'openrouter':
            ai_result = _check_with_openrouter(text, api_key, settings.get('openrouter_model', 'anthropic/claude-haiku'))
        else:
            ai_result = _check_with_anthropic(text, api_key, settings.get('ai_model', 'claude-haiku-4-5-20251001'))

        if not ai_result['approved']:
            return ai_result
        return wordlist_result

    return wordlist_result
