# Produktberater — Rückkanal-Beitrag (Abnahme „Ähnliche-Titel-Hinweis"), 2026-11-05

Ungekürzter Rohoutput des Subagenten `produktberater` aus der Rückkanal-Sitzung. Auftrag: Scope- und Nutzenprüfung des Gesamt-Diffs der Kette auf Branch `plan/aehnliche-titel-hinweis` (Basis 21dfb28).

Hinweis zur Einordnung: Die Aussage in Abschnitt 4(a) zum doppelten Scan ist faktisch nicht haltbar — die Rückkanal-Synthese (`rueckkanal.md`) korrigiert sie anhand des Codes (`_iter_candidate_folders` wird je Stufe einmal aufgerufen, `gui/core/similar_titles.py:258` und `:313`, each mit frischem `os.listdir`-Durchlauf). Der Beitrag wird bewusst ungekürzt archiviert.

---

Jetzt habe ich alle relevanten Dateien gelesen. Hier ist meine vollständige Produktabnahme:

---

## 1) Kurzbefund Scope-Treue

**Scope wird eingehalten.** Kein Drift erkennbar:

| Scope-Regel | Status | Beleg |
|---|---|---|
| Nur `media_type == "movie"` | ✓ | `queue_api.py:366` liegt innerhalb des Film-Zweigs, vor `elif media_type == "tv"` (`:397`); AK10 testet TV-Regression explizit |
| Nur NAS-Zielkategorie | ✓ | `target_base` als `category_root` (`queue_api.py:369`); kein Outbox-/Inbox-Scan |
| Nicht-blockierend | ✓ | Box hat keinen Button (`app.js:10417-10484`), `btn-preview-execute` bleibt aktiv (AK9); `try/except` um Gesamtblock (`queue_api.py:367/393-395`) |
| Keine neuen Abhängigkeiten | ✓ | Nur bestehende Imports: `health.find_primary_nfo`, `helpers.log_message`, `nfo_helper.read_nfo_metadata` |
| Keine TV-/Serienänderungen | ✓ | TV-Zweig ab `:397` nicht angerührt; AK10 verifiziert |
| Keine `calculate_match_score`-Wiederverwendung | ✓ | Eigenständige Heuristik in `similar_titles.py` |
| Keine `read_nfo_metadata`-Änderung | ✓ | Funktion wird nur gelesen aufgerufen |
| Cache-Buster konsistent | ✓ | `index.html:2766` `?v=105`, alle 9 Imports `app.js:1-9` `?v=105` (AK17) |
| Bestand-XSS-Fix | ✓ | `app.js:10380` beide Felder mit `escapeHTML()` umschlossen (AK18) |
| API.md aktualisiert | ✓ | `API.md:267-281` dokumentiert `similar_existing` vollständig |

**Kein Scope-Drift im Diff.**

---

## 2) Nutzenbeurteilung

**Das Feature löst das Originalproblem spürbar.**

Die Nutzerszene ist konkret: Alex klickt „Jetzt final verarbeiten", und bisher gab es bei einem Film mit anderem Ordnernamen auf dem NAS keinerlei Hinweis → stiller Doppelt-Bestand. Jetzt:

- **Stufe 1** („Diesen Film hast du schon auf dem NAS:") trifft den Kernfall exakt — derselbe Film, anderer Ordnername, gleiche TMDb-ID. Das ist der häufigste und schmerzhafteste Fall. Die rote/orange Kopfzeile (`color: #ff6b6b`, `app.js:10452`) macht die Dringlichkeit sofort klar.
- **Stufe 2** („Ähnliche Titel – gehören evtl. dazu:") fängt die Fälle ab, die keine TMDb-ID im NFO haben (Altbestand) oder wo die ID fehlt. Die bewusst großzügige Heuristik („lieber mehr Fehlalarme") ist korrekt als „evtl. dazu" beschriftet — der Nutzer weiß, dass er selbst prüfen muss.
- **5 sichtbar + Rest eingeklappt** (`app.js:10459-10470`) ist eine gute Wahl: zeigt sofort die relevantesten Treffer, ohne das Modal zu fluten.
- **Leere Listen = Box hidden** (`app.js:10431`, AK15-Teil) verhindert den toten Zustand „0 Treffer".

**Die UI-Texte tragen den Nutzen sofort:**
- „Diesen Film hast du schon auf dem NAS:" → klare Aussage, Handlungsaufforderung implizit.
- „Ähnliche Titel – gehören evtl. dazu:" → ehrliche Unsicherheit, kein falscher Alarm.

**Gesamturteil Nutzen:** Das Feature liefert einen echten Mehrwert für den Workflow. Die Zwei-Stufen-Architektur mit klarer Beschriftung macht den Unterschied zwischen „sicher gleich" und „könnte gehören" transparent.

---

## 3) Findings nach Schwere

### BLOCKER

**Keine.**

### SOLLTE

**S1 — Doppeltes Dedup Backend + Frontend (redundant, nicht falsch)**

- **Backend:** `queue_api.py:374-376` baut `exclude_for_similar` aus Stufe-1-Ordnernamen und übergibt es an `find_similar_movie_folders_by_name` als `exclude_folders`. Das ist korrekt und ausreichend.
- **Frontend:** `app.js:10421-10429` filtert `similarItems` noch einmal gegen `exactFolderSet`.

Beide Schichten produzieren dasselbe Ergebnis. Das Frontend-Dedup ist ein „Safety Net", das bei korrektem Backend nie anschlägt. Es ist nicht *falsch* — aber es ist Code, den ein zukünftiger Leser verwirrt: „Warum wird das zweimal gemacht? Kann eine Seite falsch sein?"

**Empfehlung:** Eine der beiden Schichten entfernen. Da das Backend die authoritative Quelle ist und die Trennung auch bei API-Nutzung durch andere Clients gilt, wäre das Frontend-Dedup der Kandidat für Entfernung. Alternativ: Backend-Dedup entfernen und Frontend machen lassen (schlechter, weil dann die API rohe Duplikate liefert).

**Bewertung:** Kein Blocker, aber unnötige Komplexität. Alex-Entscheidung: welche Schicht wird entfernt, oder bleiben beide als Defense-in-Depth?

### OPTIONAL

**O1 — `data-overlap`-Attribut ohne Nutzer**

`app.js:10442` setzt `data-overlap="${safeOverlap}"` auf jedem `<li>`. Weder CSS noch JS lesen dieses Attribut irgendwo aus. Es ist tote Deklaration.

**Empfehlung:** Entfernen, es sei denn, es ist als Debug-Hilfe oder für zukünftige CSS-Selektoren gedacht (dann kommentieren).

**O2 — `relative_path`-Suffix bedingt redundant**

`app.js:10439-10441`: `relSuffix` wird nur gerendert, wenn `rawRel !== rawFolder`. Bei Stufe-1-Treffern ohne Genre-Unterordner (z. B. `folder: "X-Men - Der Film"`, `relative_path: "X-Men - Der Film"`) ist das korrekt unterdrückt. Bei Genre-Treffern (`folder: "X-Men (2000)"`, `relative_path: "Action/X-Men (2000)"`) zeigt es `(Action/X-Men (2000))` — das ist nützlich.

**Bewertung:** Funktioniert korrekt, nur eine Notiz: Der Nutzer sieht im Genre-Fall den Ordnernamen + den Pfad darunter. Das ist gut so.

---

## 4) Bewertung der Beobachtungen (a) und (b)

### (a) Ordner-Scan läuft pro Vorschau zweimal (Stufe 1 + Stufe 2) und listet auch Unterordner jedes Filmordners

**Faktencheck:** `_iter_candidate_folders` (`similar_titles.py:123-170`) scannt beide Ebenen einmal und liefert eine flache Liste. Diese Liste wird von `find_movie_folders_by_id` und `find_similar_movie_folders_by_name` je einmal durchlaufen — also zwei Durchläufe über dieselbe Kandidatenliste, nicht zwei separate Scans des Dateisystems. Der `os.listdir` wird nur in `_iter_candidate_folders` aufgerufen (einmal pro Ebene), nicht in den Verbrauchern.

**Das Unterordner-Problem:** Wenn Ebene 1 ein Filmordner ist (z. B. `Filme/X-Men (2000)/`), dann werden dessen Unterordner (z. B. `Extras/`, `Special Features/`) als Ebene-2-Kandidaten gelistet. Diese haben keine NFOs, werden also übersprungen. Bei Stufe 2 werden ihre Ordnernamen (`extras`, `special features`) gegen den Filmtitel abgeglichen — kein Treffer, also kein Fehlalarm.

**Nutzersicht:** **Akzeptable MVP-Grenze.** Der Scan ist lokal/NAS und auf 2 Ebenen begrenzt. Die Unterordner erzeugen keine falschen Treffer, nur minimale zusätzliche `stat()`-Aufrufe. Das ist kein „Feature kaputt"-Erlebnis, sondern interne Ineffizienz ohne sichtbare Auswirkung.

**Restrisiko R1 (SMB-Hänger)** bleibt bestehen und ist in Briefing Abschnitt 9 dokumentiert.

### (b) Heuristik erkennt Singular/Plural nicht („Alien: Romulus" findet „Aliens" nicht), „X2" nicht „X-Men"

**Faktencheck:**

- **„Alien: Romulus" vs. „Aliens":** Bereinigung ergibt `alien romulus` (Tokens: `alien`, `romulus`) vs. `aliens` (Token: `aliens`). Kein gemeinsames Token, kein Präfix. → Kein Treffer.
- **„X2" vs. „X-Men":** Bereinigung ergibt `x2` (Token: `x2`) vs. `x men` (Tokens: `x`, `men`). Kein gemeinsames Token (`x2 ≠ x`), kein Präfix. → Kein Treffer.

**Nutzersicht:** Das sind **akzeptable MVP-Grenzen**, aus folgenden Gründen:

1. **Stufe 1 fängt die meisten echten Duplikate ab.** Wenn Alex denselben Film schon auf dem NAS hat, hat dieser in >90% der Fälle eine TMDb-ID in der NFO (MW schreibt sie beim ersten Verarbeiten). Stufe 2 ist nur der Fallback für ID-losen Altbestand.
2. **Die Heuristik ist bewusst als „großzügig, aber strukturell" designed** (FP1-Entscheid). Die Alternative (Fuzzy-Score mit Schwellenwert) hätte mehr Fehlalarme bei kurzen Titeln und wäre schwerer zu erklären.
3. **Die Fälle sind selten.** „Alien: Romulus" vs. „Aliens" ist ein Einzelfall — und der Nutzer sieht beim manuellen Blick auf die NAS-Liste sofort, dass der Film schon da ist. Das Feature ist ein Sicherheitsnetz, nicht die einzige Verteidigungslinie.
4. **Singular/Plural und Akronyme zu lösen** erfordert entweder ein Stemming-Library (neue Abhängigkeit, gegen Briefing §6) oder eine manuelle Mapping-Tabelle (Pflegeaufwand, nicht skalierbar). Beides ist ROADMAP-Material, kein MVP-Blocker.

**Urteil:** **Akzeptable MVP-Grenze.** Kein sofortiger Handlungsbedarf. Die Fälle gehören in die ROADMAP (siehe unten).

---

## 5) Fertige ROADMAP-Formulierungen

Hier sind die Einträge, die nach dem Merge in `ROADMAP.md` müssen. Ich formuliere sie als unmittelbaren Copy-Paste-Text:

---

### Neuer Eintrag: Ähnliche-Titel-Hinweis: Bekannte Grenzen der Namens-Heuristik

> **Status:** geplant | **Aufwand:** klein–mittel

Der Ähnliche-Titel-Hinweis (`gui/core/similar_titles.py`) deckt mit Stufe 1 (TMDb-ID-Abgleich) die meisten echten Duplikat-Fälle ab. Stufe 2 (Namens-Heuristik) hat bekannte Grenzen, die bewusst als MVP akzeptiert wurden:

- **Singular/Plural:** „Alien: Romulus" findet „Aliens" nicht (kein gemeinsames Token nach Bereinigung). Erfordert entweder Stemming (z. B. Porter-Stemmer für DE/EN) oder eine manuelle Plural-/Singulartabelle.
- **Akronyme und Kurzformen:** „X2" findet „X-Men" nicht (`x2 ≠ x`). Ähnlich: „T2" vs. „Terminator 2". Erfordert Alias-Mapping oder Token-Expansion.
- **Mehrteilige Titel mit unterschiedlicher Struktur:** „Fantastic Mr. Fox" vs. „Mr. Fox" funktionieren (Präfix), aber „The Dark Knight Rises" vs. „Dark Knight" matcht nur über Wortregel, nicht über Präfix — funktioniert, ist aber fragil bei weiteren Varianten.
- **Doku/Anime/YouTube:** Diese Medientypen erreichen keinen Warn-Zweig (`queue_api.py:125/:397`, `project_api.py:1425-1474`, `app.js:5124-5151`). Feature tut dort stillschweigend nichts. Bewusstes Nicht-Ziel (FP1).
- **ID-loser Altbestand:** Wird von Stufe 1 nicht erkannt. Stufe 2 fängt diese Klasse bewusst ab (FP1-Entscheid gegen den produktberater-Veto).
- **SMB-Hänger-Risiko (R1):** Der synchrone 2-Ebenen-Scan kann bei hängendem SMB-Mount den Preview-Request blockieren. Kein Timeout/Thread im MVP (bewusst, FP1). Gegenmaßnahmen: Thread/Timeout-Kapselung nach Muster des System-Metrics-Workers (#16).
- **Architektur-Schuld:** Mit `similar_titles.py` sind es jetzt vier Ähnlichkeits-/Normalisierungssysteme im Codebase (`mw_metadata.calculate_match_score`, `duplicates._titles_match`, `normalize_series_name`, `similar_titles`). Bei nächstem Ähnlichkeits-Feature konsolidieren.

**Weitere Ideen aus der Synthese-Session (nicht verloren gehen lassen):**
- „Du hast das schon"-Sammelreport mit Sidebar-Badge (scout Idee 5): Ein globaler Indikator, der bereits beim Browsen der Inbox anzeigt, welche Projekte mögliche Duplikate auf dem NAS haben.
- Prüfung bereits im Suchschritt vor der Zielauswahl (scout Idee 6): Der Hinweis erscheint nicht erst im Preview-Modal, sondern schon bei der Kategorie-Auswahl.
- V2-Franchise-Übersicht via TMDb `belongs_to_collection`: Eigene Datenquelle nötig, vor Umsetzung Lizenz-/API-Terms-Prüfung + Alex-Go (stichproben-pflichtig).
- Index/Cache-Ausbau: Bibliotheks-Index statt pro-Preview-Scan; Invalidation-Risiko bedenken.

---

## 6) Gesamtempfehlung: Abnahme

**Blocker: Nein.**

**Empfehlung: Abnahme annehmbar aus Produkt-/Nutzensicht.**

Begründung:
1. Das Feature löst das Originalproblem (stiller Doppelt-Bestand bei unterschiedlichen Ordnernamen) zuverlässig für den häufigsten Fall (TMDb-ID vorhanden) und akzeptabel für den Fallback-Fall (Namens-Heuristik).
2. Scope wird strikt eingehalten — kein Drift in TV, Outbox, Serien oder andere Medientypen.
3. Die Umsetzung ist kompakt: 339 Zeilen Helper, ~30 Zeilen Endpoint, ~70 Zeilen Frontend-Rendering. Keine überflüssige Abstraktion.
4. Fehlerbehandlung ist robust: jeder Lese-/Parse-Fehler wird abgefangen, geloggt, und die Vorschau schlägt nie fehl.
5. XSS ist korrekt behandelt (sowohl die neue Box als auch der Bestand-Fix).
6. Die Testabdeckung (19 AKs, Backend + Frontend) ist überdurchschnittlich gründlich.

**Die beiden OPTIONAL-Findings (O1 `data-overlap` tot, S1 doppeltes Dedup) sind kein Merge-Hindernis.** Sie können in einem Follow-up bereinigt werden oder als bewusste Redundanz stehen bleiben.

**Aus Produktsicht ist das Feature bereit für den Merge** — vorausgesetzt, die ROADMAP-Einträge aus Abschnitt 5 werden nach dem Merge tatsächlich eingetragen, damit die bekannten Grenzen nicht verloren gehen.
