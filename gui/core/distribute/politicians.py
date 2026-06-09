import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'politicians.json')


def load_politicians() -> list[dict]:
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('politicians', [])
    except FileNotFoundError:
        logger.error("politicians.json not found at %s", DB_PATH)
        return []
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Politiker-Datenbank ungültig: {e}")


def search_politicians(query: str = '', category: str = '') -> list[dict]:
    politicians = load_politicians()

    if query:
        query_lower = query.lower()
        politicians = [
            p for p in politicians
            if query_lower in p['name'].lower()
            or query_lower in p.get('party', '').lower()
            or query_lower in p.get('position', '').lower()
        ]

    if category:
        politicians = [p for p in politicians if p.get('position_category') == category]

    return politicians


def get_politician_by_id(politician_id: str) -> Optional[dict]:
    for politician in load_politicians():
        if politician['id'] == politician_id:
            return politician
    return None


def get_available_platforms(politician: dict) -> list[str]:
    """Returns platform IDs the politician is reachable on."""
    available = []
    for platform_id, data in politician.get('platforms', {}).items():
        if data is not None:
            available.append(platform_id)
    return available
