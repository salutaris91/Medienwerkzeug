"""Filme normalisieren: Zielstruktur Filme/<Film>/<Dateien> herstellen.

Zwei Operationen (nur Vorschlag/Plan; ausgeführt wird nur, was bestätigt wird):
- Genre-Ordner auflösen:   Filme/<Genre>/<Film>/  ->  Filme/<Film>/
- Lose Dateien einsammeln: lose Video-Datei (+ Begleitdateien) direkt in Filme/
                           ->  Filme/<Filmname>/

Sicherheit: es wird nie überschrieben, nur innerhalb der NAS-Root verschoben,
leere Genre-Ordner werden danach entfernt. Das eigentliche Verschieben passiert
ausschließlich über apply_moves() mit den vom Nutzer bestätigten Einträgen.
"""

import os
import re
import shutil

from gui.core import utils
from gui.core.transfers import ensure_nas_mounted
from gui.core.helpers import log_message
import gui.core.trash as trash

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.m4v', '.ts', '.mov', '.wmv'}


def _dir_has_video(directory):
    for dirpath, _dirs, filenames in os.walk(directory):
        for f in filenames:
            if not f.startswith('.') and os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS:
                return True
    return False


def _is_genre_container(path):
    """Genre-Sammelordner: kein Jahr im Namen, kein eigenes Video, aber Film-Unterordner."""
    name = os.path.basename(path)
    if re.search(r'(19|20)\d{2}', name):
        return False
    try:
        entries = [e for e in os.listdir(path) if not e.startswith('.')]
    except OSError:
        return False
    if any(os.path.splitext(e)[1].lower() in VIDEO_EXTENSIONS for e in entries):
        return False
    subdirs = [e for e in entries if os.path.isdir(os.path.join(path, e))]
    return any(_dir_has_video(os.path.join(path, sd)) for sd in subdirs)


def _movie_categories(settings):
    """Film-artige Sync-Kategorien (keine Serien)."""
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return []
    out = []
    for cat in settings.get("sync_categories", []):
        if "serie" in (cat.get("name", "")).lower():
            continue
        nas_sub = cat.get("nas_sub")
        if not nas_sub:
            continue
        cat_path = f"{nas_root}{nas_sub}"
        if os.path.isdir(cat_path):
            out.append((cat.get("name", ""), cat_path))
    return out


def build_plan(settings=None):
    """Erstellt den Verschiebe-Plan (verschiebt nichts)."""
    if settings is None:
        settings = utils.load_settings()
    plan = []
    for cat_name, cat_path in _movie_categories(settings):
        try:
            entries = sorted(os.listdir(cat_path))
        except OSError:
            continue

        # 1) Lose Dateien (direkt in der Kategorie liegende Videos + Begleitdateien)
        loose_files = [e for e in entries
                       if not e.startswith('.') and os.path.isfile(os.path.join(cat_path, e))]
        loose_videos = [e for e in loose_files if os.path.splitext(e)[1].lower() in VIDEO_EXTENSIONS]
        used = set()
        for v in loose_videos:
            stem = os.path.splitext(v)[0]
            members = [m for m in loose_files
                       if m not in used and (os.path.splitext(m)[0] == stem or m.startswith(stem))]
            used.update(members)
            dst = os.path.join(cat_path, stem)
            plan.append({
                "kind": "loose",
                "dst": dst,
                "files": [os.path.join(cat_path, m) for m in members],
                "conflict": os.path.exists(dst),
                "label": f"{len(members)} lose Datei(en) „{stem}“  →  {cat_name}/{stem}/",
            })

        # 2) Genre-Ordner auflösen
        for e in entries:
            p = os.path.join(cat_path, e)
            if e.startswith('.') or not os.path.isdir(p):
                continue
            if not _is_genre_container(p):
                continue
            try:
                sub = sorted(os.listdir(p))
            except OSError:
                continue
            for sd in sub:
                src = os.path.join(p, sd)
                if sd.startswith('.') or not os.path.isdir(src):
                    continue
                dst = os.path.join(cat_path, sd)

                is_nested = (os.path.dirname(src) == dst)
                conflict = False
                if is_nested:
                    try:
                        inner_files = {f for f in os.listdir(src) if not f.startswith('.')}
                        parent_files = {f for f in os.listdir(dst) if not f.startswith('.')}
                        parent_files.discard(sd)
                        if inner_files.intersection(parent_files):
                            conflict = True
                    except OSError:
                        conflict = True
                else:
                    conflict = os.path.exists(dst)

                label = f"{cat_name}/{e}/{sd}  →  {cat_name}/{sd}"
                if is_nested:
                    label = f"Verschachtelung auflösen: {cat_name}/{e}/{sd}  →  {cat_name}/{sd}/"

                plan.append({
                    "kind": "genre",
                    "src": src,
                    "dst": dst,
                    "genre_dir": p,
                    "conflict": conflict,
                    "label": label,
                })
    return plan


def _within(path, root):
    try:
        return os.path.commonpath([root, os.path.realpath(path)]) == root
    except Exception:
        return False


def apply_moves(items, on_progress=None):
    """Führt die ausgewählten Plan-Einträge aus. Gibt {moved, skipped, errors} zurück.

    on_progress(index, total, label) wird nach jedem Eintrag aufgerufen.
    """
    settings = utils.load_settings()
    nas_root = settings.get("nas_root", "")
    if not nas_root:
        return {"moved": 0, "skipped": 0, "errors": ["NAS-Root ist nicht konfiguriert."]}
    nas_root = os.path.realpath(nas_root)
    if not ensure_nas_mounted():
        return {"moved": 0, "skipped": 0, "errors": ["NAS nicht verfügbar."]}

    results = {"moved": 0, "skipped": 0, "errors": []}
    genre_dirs = set()
    total = len(items or [])

    for idx, it in enumerate(items or []):
        kind = it.get("kind")
        label = it.get("label", "")
        if on_progress:
            on_progress(idx, total, label)
        try:
            if kind == "genre":
                src = it.get("src")
                dst = it.get("dst")
                if not src or not dst or not _within(src, nas_root) or not _within(os.path.dirname(dst), nas_root):
                    results["errors"].append(f"Außerhalb NAS-Root: {label}")
                    continue

                is_nested = (os.path.dirname(src) == dst)
                if is_nested:
                    if not os.path.isdir(src) or not os.path.isdir(dst):
                        results["skipped"] += 1
                        continue
                    try:
                        for item in os.listdir(src):
                            if item.startswith('.'):
                                continue
                            item_src = os.path.join(src, item)
                            item_dst = os.path.join(dst, item)
                            if os.path.exists(item_dst):
                                raise Exception(f"Datei im Elternordner existiert bereits: {item}")
                            shutil.move(item_src, item_dst)
                        # Den nun leeren inneren Ordner löschen
                        trash.send_to_trash(src)
                        results["moved"] += 1
                    except Exception as e:
                        results["errors"].append(f"{label}: {e}")
                else:
                    if os.path.exists(dst) or not os.path.isdir(src):
                        results["skipped"] += 1
                        continue
                    shutil.move(src, dst)
                    results["moved"] += 1
                    if it.get("genre_dir"):
                        genre_dirs.add(it["genre_dir"])

            elif kind == "loose":
                dst = it.get("dst")
                files = it.get("files", [])
                if not dst or not _within(os.path.dirname(dst), nas_root):
                    results["errors"].append(f"Außerhalb NAS-Root: {label}")
                    continue
                if os.path.exists(dst):
                    results["skipped"] += 1
                    continue
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    if _within(f, nas_root) and os.path.isfile(f):
                        shutil.move(f, os.path.join(dst, os.path.basename(f)))
                results["moved"] += 1
            else:
                results["skipped"] += 1
        except Exception as e:
            results["errors"].append(f"{label}: {e}")

    # Leere Genre-Ordner entfernen (auch wenn nur versteckte Dateien wie .DS_Store übrig)
    for g in genre_dirs:
        try:
            if os.path.isdir(g) and _within(g, nas_root):
                rest = [e for e in os.listdir(g) if not e.startswith('.')]
                if not rest:
                    try:
                        trash.send_to_trash(g)
                    except trash.TrashError as e:
                        log_message(f"⚠️ Konnte leeren Genre-Ordner {g} nicht in Quarantäne verschieben: {e}")
        except Exception:
            pass

    if on_progress:
        on_progress(total, total, "Fertig")

    log_message(f"🎬 [Filme normalisieren] {results['moved']} verschoben, "
                f"{results['skipped']} übersprungen, {len(results['errors'])} Fehler.")
    return results
