import os
import json
import hashlib
import time
import tempfile
from typing import Dict, List, Optional

SCAN_VERSION = 1

def get_cache_key(media_server: str) -> str:
    """Berechnet den Cache-Schlüssel basierend auf Scan-Version und Medienserver."""
    return f"{SCAN_VERSION}:{media_server}"

class HealthCacheManager:
    def __init__(self, cache_path: Optional[str] = None):
        if cache_path is None:
            # Standardpfad: gui/data/health_folder_cache.json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            self.cache_path = os.path.join(data_dir, "health_folder_cache.json")
        else:
            self.cache_path = cache_path
            
    def _load_cache(self) -> dict:
        if not os.path.exists(self.cache_path):
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            # Fehler ausgeben, aber leeren Cache zurückgeben, um Abstürze zu verhindern
            print(f"Fehler beim Laden des Health-Caches: {e}")
            return {}

    def _save_cache(self, data: dict):
        # Sicherstellen, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        temp_fd = None
        temp_path = None
        try:
            # Atomares Schreiben über temporäre Datei im selben Verzeichnis
            dir_name = os.path.dirname(self.cache_path)
            temp_fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.cache_path)
        except Exception as e:
            print(f"Fehler beim Speichern des Health-Caches: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def get_cached_entry(self, folder_path: str, cache_key: str) -> Optional[dict]:
        """Liefert den Cache-Eintrag für einen Ordner, wenn der Cache-Key gültig ist."""
        cache = self._load_cache()
        abs_path = os.path.realpath(folder_path)
        entry = cache.get(abs_path)
        if entry and entry.get("cache_key") == cache_key:
            return entry
        return None

    def set_cached_entry(self, folder_path: str, cache_key: str, issues: list, state_data: dict, files_checked: int = 0):
        """Speichert oder aktualisiert den Cache-Eintrag für einen Ordner."""
        cache = self._load_cache()
        abs_path = os.path.realpath(folder_path)
        cache[abs_path] = {
            "cache_key": cache_key,
            "issues": issues,  # rohe Issues vor Ignore-Filter
            "state_data": state_data,
            "files_checked": files_checked,
            "timestamp": time.time()
        }
        self._save_cache(cache)

    def calculate_hybrid_state(self, folder_path: str, validator, is_movie: bool) -> dict:
        """Berechnet die mtimes und Größen der Kerndateien für Ansatz C."""
        abs_path = os.path.realpath(folder_path)
        if not os.path.exists(abs_path):
            return {}

        state = {
            "folder_mtime": os.path.getmtime(abs_path)
        }

        try:
            entries = os.listdir(abs_path)
        except Exception:
            return state

        if is_movie:
            # 1. Haupt-Videodatei suchen
            video_extensions = {'.mkv', '.mp4', '.avi', '.webm', '.mov', '.ts', '.m2ts'}
            video_file = None
            for e in sorted(entries):
                if not e.startswith('.') and os.path.splitext(e)[1].lower() in video_extensions:
                    video_file = e
                    break
            
            if video_file:
                video_path = os.path.join(abs_path, video_file)
                try:
                    state["video_mtime"] = os.path.getmtime(video_path)
                    state["video_size"] = os.path.getsize(video_path)
                except Exception:
                    pass

            # 2. NFO-Datei suchen
            nfo_file = None
            if video_file:
                stem = os.path.splitext(video_file)[0]
                possible_nfos = {f"{stem}.nfo", "movie.nfo"}
                for e in entries:
                    if e in possible_nfos:
                        nfo_file = e
                        break
            if not nfo_file:
                for e in entries:
                    if not e.startswith('.') and e.lower().endswith(".nfo"):
                        nfo_file = e
                        break
            if nfo_file:
                nfo_path = os.path.join(abs_path, nfo_file)
                try:
                    state["nfo_mtime"] = os.path.getmtime(nfo_path)
                except Exception:
                    pass

            # 3. Poster suchen
            preferred_poster = None
            if video_file and hasattr(validator, 'get_preferred_movie_poster_name'):
                preferred_poster = validator.get_preferred_movie_poster_name(video_file)
            
            poster_file = None
            if preferred_poster and preferred_poster in entries:
                poster_file = preferred_poster
            else:
                patterns = []
                if hasattr(validator, 'get_movie_poster_patterns'):
                    patterns = validator.get_movie_poster_patterns(video_file if video_file else "")
                for pattern in patterns:
                    if pattern in entries:
                        poster_file = pattern
                        break
            
            if poster_file:
                poster_path = os.path.join(abs_path, poster_file)
                try:
                    state["poster_mtime"] = os.path.getmtime(poster_path)
                except Exception:
                    pass

        else:
            # Serien-Ebene
            # 1. tvshow.nfo suchen
            if "tvshow.nfo" in entries:
                try:
                    state["tvshow_nfo_mtime"] = os.path.getmtime(os.path.join(abs_path, "tvshow.nfo"))
                except Exception:
                    pass

            # 2. Serienposter suchen
            preferred_poster = "poster.jpg"
            if hasattr(validator, 'get_preferred_series_poster_name'):
                preferred_poster = validator.get_preferred_series_poster_name()
            
            poster_file = None
            if preferred_poster in entries:
                poster_file = preferred_poster
            else:
                patterns = []
                if hasattr(validator, 'get_series_poster_patterns'):
                    patterns = validator.get_series_poster_patterns()
                for pattern in patterns:
                    if pattern in entries:
                        poster_file = pattern
                        break
            if poster_file:
                try:
                    state["series_poster_mtime"] = os.path.getmtime(os.path.join(abs_path, poster_file))
                except Exception:
                    pass

            # 3. Staffel-Unterordner erfassen
            season_dirs = {}
            for e in entries:
                if os.path.isdir(os.path.join(abs_path, e)) and not e.startswith('.'):
                    e_lower = e.lower()
                    if e_lower.startswith("staffel ") or e_lower.startswith("season ") or e_lower.startswith("specials"):
                        try:
                            season_dirs[e] = os.path.getmtime(os.path.join(abs_path, e))
                        except Exception:
                            pass
            if season_dirs:
                state["season_dirs"] = season_dirs

        return state

    def calculate_deep_hash(self, folder_path: str) -> str:
        """Berechnet einen MD5-Zustands-Hash aller relevanten Dateien in Ansatz B."""
        abs_path = os.path.realpath(folder_path)
        if not os.path.exists(abs_path):
            return ""

        file_infos = []
        try:
            for root, _, files in os.walk(abs_path):
                for f in files:
                    if f.startswith('.'):
                        continue
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, abs_path)
                    try:
                        stat = os.stat(full_path)
                        file_infos.append(f"{rel_path}:{stat.st_size}:{stat.st_mtime}")
                    except Exception:
                        pass
        except Exception:
            pass

        file_infos.sort()
        content = "|".join(file_infos)
        return hashlib.md5(content.encode("utf-8")).hexdigest()
