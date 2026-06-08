import os
import json
import hashlib
import time
import tempfile
from typing import Dict, List, Optional

SCAN_VERSION = 2

def get_cache_key(media_server: str) -> str:
    """Berechnet den Cache-Schlüssel basierend auf Scan-Version und Medienserver."""
    return f"{SCAN_VERSION}:{media_server}"

class HealthCacheManager:
    def __init__(self, cache_path: Optional[str] = None):
        if cache_path is None:
            # Standardpfad: <utils.DATA_DIR>/health_folder_cache.json
            from gui.core import utils
            self.cache_path = os.path.join(utils.DATA_DIR, "health_folder_cache.json")
        else:
            self.cache_path = cache_path
        self._cache = self._load_cache()
            
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
        abs_path = os.path.realpath(folder_path)
        entry = self._cache.get(abs_path)
        if entry and entry.get("cache_key") == cache_key:
            return entry
        return None

    def set_cached_entry(self, folder_path: str, cache_key: str, issues: list, state_data: Optional[dict] = None, files_checked: int = 0, hybrid_state: Optional[dict] = None, deep_hash: Optional[str] = None):
        """Speichert oder aktualisiert den Cache-Eintrag für einen Ordner mit separatem Hybrid- und Deep-Dive-Zustand."""
        abs_path = os.path.realpath(folder_path)
        entry = self._cache.get(abs_path) or {}
        
        new_hybrid = hybrid_state
        new_deep = deep_hash
        if state_data is not None:
            if isinstance(state_data, dict):
                new_hybrid = state_data
            elif isinstance(state_data, str):
                new_deep = state_data
                
        self._cache[abs_path] = {
            "cache_key": cache_key,
            "issues": issues,  # rohe Issues vor Ignore-Filter
            "state_data": new_hybrid if new_hybrid is not None else new_deep,
            "hybrid_state": new_hybrid if new_hybrid is not None else entry.get("hybrid_state"),
            "deep_hash": new_deep if new_deep is not None else entry.get("deep_hash"),
            "files_checked": files_checked,
            "timestamp": time.time()
        }

    def flush(self):
        """Schreibt den aktuellen Speicher-Cache dauerhaft auf die Festplatte."""
        self._save_cache(self._cache)

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
            poster_file = None
            patterns = []
            if hasattr(validator, 'get_movie_poster_names'):
                patterns = validator.get_movie_poster_names(video_file if video_file else "")
            for pattern in patterns:
                for entry in entries:
                    if validator.matches_artwork_name(entry, pattern):
                        poster_file = entry
                        break
                if poster_file:
                    break
            
            if poster_file:
                poster_path = os.path.join(abs_path, poster_file)
                try:
                    state["poster_mtime"] = os.path.getmtime(poster_path)
                except Exception:
                    pass

            # 4. Backdrop/Fanart suchen
            backdrop_file = None
            patterns = []
            if hasattr(validator, 'get_movie_backdrop_names'):
                patterns = validator.get_movie_backdrop_names(video_file if video_file else "")
            for pattern in patterns:
                for entry in entries:
                    if validator.matches_artwork_name(entry, pattern):
                        backdrop_file = entry
                        break
                if backdrop_file:
                    break
            if backdrop_file:
                try:
                    state["backdrop_mtime"] = os.path.getmtime(os.path.join(abs_path, backdrop_file))
                except Exception:
                    pass

            # 5. Logo suchen
            if validator.supports_logos:
                logo_file = None
                patterns = []
                if hasattr(validator, 'get_movie_logo_names'):
                    patterns = validator.get_movie_logo_names(video_file if video_file else "")
                for pattern in patterns:
                    for entry in entries:
                        if validator.matches_artwork_name(entry, pattern):
                            logo_file = entry
                            break
                    if logo_file:
                        break
                if logo_file:
                    try:
                        state["logo_mtime"] = os.path.getmtime(os.path.join(abs_path, logo_file))
                    except Exception:
                        pass

            # 6. Banner suchen
            if validator.supports_banners:
                banner_file = None
                patterns = []
                if hasattr(validator, 'get_movie_banner_names'):
                    patterns = validator.get_movie_banner_names(video_file if video_file else "")
                for pattern in patterns:
                    for entry in entries:
                        if validator.matches_artwork_name(entry, pattern):
                            banner_file = entry
                            break
                    if banner_file:
                        break
                if banner_file:
                    try:
                        state["banner_mtime"] = os.path.getmtime(os.path.join(abs_path, banner_file))
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
            poster_file = None
            patterns = []
            if hasattr(validator, 'get_series_poster_names'):
                patterns = validator.get_series_poster_names()
            for pattern in patterns:
                for entry in entries:
                    if validator.matches_artwork_name(entry, pattern):
                        poster_file = entry
                        break
                if poster_file:
                    break
            if poster_file:
                try:
                    state["series_poster_mtime"] = os.path.getmtime(os.path.join(abs_path, poster_file))
                except Exception:
                    pass

            # 3. Backdrop/Fanart suchen
            backdrop_file = None
            patterns = []
            if hasattr(validator, 'get_series_backdrop_names'):
                patterns = validator.get_series_backdrop_names()
            for pattern in patterns:
                for entry in entries:
                    if validator.matches_artwork_name(entry, pattern):
                        backdrop_file = entry
                        break
                if backdrop_file:
                    break
            if backdrop_file:
                try:
                    state["series_backdrop_mtime"] = os.path.getmtime(os.path.join(abs_path, backdrop_file))
                except Exception:
                    pass

            # 4. Logo suchen
            if validator.supports_logos:
                logo_file = None
                patterns = []
                if hasattr(validator, 'get_series_logo_names'):
                    patterns = validator.get_series_logo_names()
                for pattern in patterns:
                    for entry in entries:
                        if validator.matches_artwork_name(entry, pattern):
                            logo_file = entry
                            break
                    if logo_file:
                        break
                if logo_file:
                    try:
                        state["series_logo_mtime"] = os.path.getmtime(os.path.join(abs_path, logo_file))
                    except Exception:
                        pass

            # 5. Banner suchen
            if validator.supports_banners:
                banner_file = None
                patterns = []
                if hasattr(validator, 'get_series_banner_names'):
                    patterns = validator.get_series_banner_names()
                for pattern in patterns:
                    for entry in entries:
                        if validator.matches_artwork_name(entry, pattern):
                            banner_file = entry
                            break
                    if banner_file:
                        break
                if banner_file:
                    try:
                        state["series_banner_mtime"] = os.path.getmtime(os.path.join(abs_path, banner_file))
                    except Exception:
                        pass

            # 6. Staffel-Unterordner erfassen
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

            # 7. Staffel-Poster erfassen (sowohl im Serienordner als auch im Staffelordner)
            import re
            season_posters = {}
            for e in entries:
                if os.path.isdir(os.path.join(abs_path, e)) and not e.startswith('.'):
                    e_lower = e.lower()
                    if e_lower.startswith("staffel ") or e_lower.startswith("season ") or e_lower.startswith("specials"):
                        season_num = 1
                        if "specials" in e_lower:
                            season_num = 0
                        else:
                            m = re.search(r'\d+', e_lower)
                            if m:
                                season_num = int(m.group(0))
                                
                        sp_patterns = validator.get_season_poster_names(season_num)
                        for pattern in sp_patterns:
                            if "/" in pattern:
                                sp_path = os.path.join(abs_path, pattern)
                                if os.path.exists(sp_path):
                                    try:
                                        season_posters[pattern] = os.path.getmtime(sp_path)
                                    except Exception:
                                        pass
                            else:
                                if pattern in entries:
                                    try:
                                        season_posters[pattern] = os.path.getmtime(os.path.join(abs_path, pattern))
                                    except Exception:
                                        pass
            if season_posters:
                state["season_posters"] = season_posters

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
