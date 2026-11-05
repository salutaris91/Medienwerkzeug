# Rohoutput — produktberater (Akt 1, Planungs-Session "Ähnliche Titel", 2026-11-05)

> Beitrag ungekürzt archiviert (Transparenz-Pflicht). Eingabe-Brief: identischer
> Kontextbrief (Wunsch von Alex, verifizierter Ist-Zustand, Vorschläge A/B/C) wie in
> `synthese.md` beschrieben; Aufgabe an den produktberater: echten Nutzen klären,
> A/B/C auf Nutzen-vs-Komplexität bewerten, kleinstes MVP definieren, offene Fragen
> priorisieren. Schreibgeschützter Agent.

---

Hier meine vollständige Produktbewertung.

---

## 1) Nutzenanalyse — Zwei Use Cases, die auseinandergehalten werden müssen

Dein Wunsch „Du hast schon diese X-Men-Filme" enthält **zwei fundamental verschiedene Probleme**, die getrennt bewertet werden müssen:

### Use Case 1: Duplikatwarnung (echtes Problem)
**Szenario:** Alex kauft/lädt „X-Men (2000)" herunter, hat aber „X-Men - Der Film (2000)" bereits auf dem NAS. Gleicher Film, anderer Ordnername → kein Alarm bei der aktuellen exakten Namensprüfung → Gefahr von Doppelt-Bestand.

**Das ist das eigentliche Schmerzproblem.** Es ist konkret, actionably, und der Nutzer kann darauf reagieren („überspringen" oder „trotzdem verarbeiten").

### Use Case 2: Franchise-/Reihenübersicht (nice-to-have)
**Szenario:** Alex verarbeitet „X-Men: Apocalypse" und sieht eine Liste „Du hast schon: X-Men (2000), X2, X-Men: Days of Future Past …".

**Das ist kein Duplikat-Problem, sondern eine Bibliotheks-Exploration.** Es löst keinen Schmerz — es sei denn, Alex will bewusst eine vollständige Sammlung aufbauen und weiß nicht, was schon da ist. Das ist ein anderes Feature mit komplett anderer Datenmodellierung.

### Warum die Trennung entscheidend ist

Use Case 1 lässt sich mit **deterministischem ID-Abgleich** lösen — exakt, schnell, keine False Positives. Use Case 2 erfordert entweder eine TMDb-Collection-API (Franchise-Metadaten) oder aufwändiges Name-Clustering. Die Vermischung beider Use Cases in einem Feature ist der Hauptgrund, warum Vorschlag B (Franchise-Gruppierung) entsteht — und warum ich davor warne.

---

## 2) Bewertung der Vorschläge A/B/C

### Vorschlag A: Ähnlichkeits-Warning im Preview (Namens-Fuzzy)

**Nutzen:** Mittel bis hoch für Use Case 1.
**Komplexität:** Hoch — und zwar aus drei Gründen:

1. **False-Positive-Flut.** `calculate_match_score` (Jaccard + Jahresstrafe) ist für Such-Ranking gebaut, nicht für Deduplizierung. „X-Men" und „X-Men Origins: Wolverine" würden hoch matchen — sind aber unterschiedliche Filme. „Star Wars" und „Star Trek" matchen nicht, obwohl Remakes gleichen Titels möglich sind.
2. **Schwellenwert-Tuning.** Jeder Schwellenwert ist ein Kompromiss: zu niedrig → Lärm (nutzer ignoriert die Box), zu hoch → echte Duplikate rutschen durch. Das erfordert iteratives Testing an der realen Bibliothek.
3. **Performance.** Bei jedem Preview-Öffnen alle NAS-Filmordner scannen, Namen normalisieren, Scores berechnen. Bei hunderten Filmordnern spürbar.

**Mein Vorschlag:** Namens-Fuzzy durch ID-Abgleich ersetzen. Siehe Punkt 5.

### Vorschlag B: A + Jahr + Franchise-Gruppierung

**Nutzen:** Franchise-Gruppierung ist Use Case 2 — nice-to-have, kein Schmerz.
**Komplexität:** Erheblich höher als A:

- TMDb-Collection-API abrufen ( zusätzlicher API-Call, Fehlerbehandlung, Rate Limiting)
- Collection-Daten in NFOs anreichern oder lokal cachen
- UI für Franchise-Anzeige designen (gruppierte Liste statt einfacher Hinweis)
- Edge Cases: Ein Film gehört zu mehreren Collections (MCU-Crossovers), Remakes innerhalb einer Collection, etc.

**Urteil:** **Gold-Plating für das MVP.** Franchise-Gruppierung ist ein eigenes Feature für die ROADMAP, kein Teil dieses MVPs.

### Vorschlag C: Eigener Bestätigungsdialog

**Bereits verworfen** — zu Recht. Unterbricht den Flow für jeden Lauf, auch wenn 95% der Fälle keine Ähnlichkeit haben.

### Zusammenfassung Bewertung

| | Nutzen | Komplexität | Urteil |
|---|---|---|---|
| A (fuzzy name) | mittel | hoch | ❌ ID-Abgleich bevorzugen |
| B (+ Franchise) | mittel+hoch | sehr hoch | ❌ Gold-Plating, ROADMAP |
| C (Extra-Dialog) | niedrig | mittel | ❌ bereits verworfen |
| **A' (ID-basiert)** | **hoch** | **niedrig** | **✅ MVP** |

---

## 3) MVP-Vorschlag — ID-basierter Duplikat-Hinweis für Filme

### Kernidee
Statt Namens-Raten: **TMDb-ID vergleichen**. Die ID liegt bereits im Preview-Payload (`movie_id`, `provider`) UND in jeder Film-NFO auf dem NAS (`<tmdbid>`). Exakter Treffer = gleicher Film. Basta.

### Warum das besser ist als Fuzzy

| Kriterium | Fuzzy Name | ID-Abgleich |
|---|---|---|
| False Positives | hoch (X-Men vs. X-Men Origins) | **null** (gleiche ID = gleicher Film) |
| False Negatives | mittel (Jahres-Abweichungen, Umlaute) | nur bei ID-Wechsel (selten) |
| Code-Umfang | ~150 Zeilen + Schwellenwert-Config | **~60 Zeilen** (eine Funktion + UI-Box) |
| Performance | O(n) mit String-Normalisierung | O(n) mit nur einem XML-Tag-Vergleich |
| Wartbarkeit | Schwellenwert-Tuning, Bug-Reports zu Falschtreffern | **kein Tuning nötig** |

### Konkreter MVP-Scope

**Medien-Typ:** Nur **Filme** (der Wunsch nennt ein Film-Beispiel; Serien haben bereits den `show_name_mismatch`-Hinweis bei ID-Treffer).

**Datenquelle:** `<tmdbid>` aus der Film-NFO auf dem NAS. Die Funktion `find_existing_series_folder_by_id` in `gui/core/series_helper.py` ist das Blaupause — eine äquivalente `find_existing_movie_folder_by_id` für Filme bauen.

**Ort:** Warnbox **im bestehenden Preview-Modal** (zwischen `preview-show-name-mismatch` und `preview-destination`), analog zur bestehenden `show_name_mismatch`-Box. Kein neuer Dialog, kein Unterbruch.

**Datenabgleich:**
1. `movie_id` + `provider` aus dem Preview-Payload nehmen
2. Nur wenn `provider` eine echte ID hat (`tmdb`, nicht `manual`/`mediathek`/`ytdlp`)
3. Ziel-Ordner auf dem NAS scannen (nur die Ziel-Kategorie, z.B. `Filme/`, nicht das gesamte NAS)
4. In jedem Unterordner die `.nfo` lesen, `<tmdbid>` extrahieren, mit `movie_id` vergleichen
5. Bei Treffer: `similar_existing: [{folder_name, tmdb_id}]` zurückgeben
6. Frontend zeigt: „⚠️ Du hast diesen Film bereits: **{folder_name}**" — reiner Hinweis, blockiert nichts

**Kein Fuzzy, kein Schwellenwert, keine Franchise.**

**Edge Cases im MVP:**
- **Genre-Sammelordner** (z.B. `Filme/Action/X-Men (2000)/`): Die Funktion muss rekursiv arbeiten (2 Ebenen), weil Filme in Genre-Ordnern liegen können. `_is_genre_container` aus `health.py` zeigt, dass diese Struktur bekannt ist.
- **Filme ohne TMDb-ID** (Mediathek, manual, ytdlp): Kein ID-Abgleich möglich → kein Hinweis (silent skip). Das ist korrekt — diese Filme haben keine stabile ID.
- **Outbox:** Im MVP weglassen. Outbox ist flüchtig; der NAS ist die authoritative Quelle.

**UI-Text im MVP:**
```
⚠️ Film bereits vorhanden
Du hast diesen Film bereits auf dem NAS im Ordner „X-Men (2000)".
```

### Was NICHT im MVP ist (bewusst zurückgestellt)
- Franchise-/Reihen-Anzeige (Use Case 2)
- Fuzzy-Name-Matching als Fallback für ID-lose Filme
- Outbox-Scan
- Serien-Erweiterung (existiert bereits als `show_name_mismatch`)
- Qualitätsvergleich bei ID-Treffer (existiert bereits als Kollisionswarnung bei exaktem Namens-Treffer)

---

## 4) Priorisierte Fragen an Alex

### Frage 1 (entscheidend für MVP): ID-Abgleich statt Fuzzy?
**Empfehlung:** Ja, ID-Abgleich. Begründung: null False Positives, 60 statt 150 Zeilen Code, kein Schwellenwert-Tuning, deterministisch testbar. Trade-off: Funktioniert nur für Filme mit TMDb-ID (Mediathek/manual/ytdlp werden nicht erkannt — aber das ist korrekt, denn ohne ID können wir nicht wissen, ob es derselbe Film ist).
**Alex-Entscheidung:** Bist du einverstanden mit ID-Abgleich als MVP, oder willst du trotzdem Fuzzy?

### Frage 2 (Scope-Frage): Nur Filme, oder auch Serien?
**Empfehlung:** Nur Filme. Serien haben bereits `show_name_mismatch` (queue_api.py:764-785), der bei ID-Treffer mit abweichendem Ordnernamen warnt. Die Lücke ist nur bei Filmen.
**Alex-Entscheidung:** Soll die Serien-Logik erweitert werden, oder reichen Filme für den ersten Wurf?

### Frage 3 (später entscheidbar): Franchise-Gruppung als V2?
**Empfehlung:** Als ROADMAP-Item parken, nicht im MVP. Wenn du es später willst, ist die TMDb-Collection-API (`belongs_to_collection` ist bereits im Movie-API-Response, wird nur nicht in der NFO gespeichert) der richtige Weg — nicht Name-Clustering.
**Alex-Entscheidung:** Willst du Franchise-Anzeige als separates V2-Feature auf die ROADMAP setzen?

### Frage 4 (Implementierungsdetail, später): Performance bei großer Bibliothek?
**Empfehlung:** MVP scannt nur den Ziel-Kategorie-Ordner (z.B. `NAS/Filme/`), nicht das gesamte NAS. Das sind typisch 100-500 Ordner, jeder braucht einen NFO-Read. Sollte unter 1 Sekunde liegen. Falls später zu langsam: Health-Cache wiederverwenden (der hat bereits `media_structure.movies[]` mit `nfo_path`).
**Alex-Entscheidung:** Reicht der Ziel-Kategorie-Scan, oder brauchst du NAS-weit?

### Frage 5 (Implementierungsdetail, später): Hinweis blockieren oder nur anzeigen?
**Empfehlung:** Nur anzeigen, nicht blockieren. Der „Jetzt final verarbeiten"-Button bleibt aktiv. Es ist ein Hinweis, keine Sperre — Alex entscheidet. Das ist konsistent mit allen anderen Hinweisen im Preview (show_name_mismatch, Kollisionswarnung).
**Alex-Entscheidung:** Einverstanden?

---

## 5) Komplexitäts-Warnungen

### Warnung 1: Fuzzy-Matching ist eine Falle
`calculate_match_score` aus `mw_metadata.py` ist für Such-Ranking gebaut (Jaccard + Jahresstrafe). Sie als Deduplizierungsfunktion zu verwenden, erzeugt systematisch False Positives bei:
- **Franchise-Filmen:** „X-Men" matcht „X-Men: Apocalypse" zu ~0.7 (hoher Jaccard, gleiche Wörter). Das ist kein Duplikat.
- **Gleicher Titel, anderer Film:** „The Fog" (1980) vs. „The Fog" (2005) — gleicher Name, verschiedene Filme. Nur das Jahr unterscheidet sie, und Jahres-Abweichungen sind im Fuzzy anfällig.
- **Umlaut-Schreibweisen:** „Ähre" vs. \"Aehre\" — die Normalisierung existiert, aber die Score-Differenz ist klein.

**Jeder False Positive untergräbt das Vertrauen in die Warnung.** Nach 3 Fehlalarmen ignoriert Alex die Box dauerhaft. ID-Abgleich hat dieses Problem nicht.

### Warnung 2: Franchise-Gruppierung ist ein eigenes Produkt
Um „alle X-Men-Filme" anzuzeigen, braucht man:
- TMDb-Collection-Data (API-Call + Cache)
- Ein Mapping: Collection-ID → lokale Ordner
- UI für gruppierte Anzeige
- Entscheidung: Zeige nur vorhandene Filme oder auch „fehlende" Filme der Collection?

Das ist ein eigenes Feature mit eigener Komplexität. **Nicht in dieses MVP mischen.**

### Warnung 3: Der Engpass ist Alex (Review), nicht Code
Die ID-basierte Lösung ist in ~60 Zeilen Backend + ~30 Zeilen Frontend implementierbar. Die Fuzzy-Lösung braucht ~150 Zeilen Backend + Schwellenwert-Config + iteratives Testing an der realen Bibliothek + Bug-Fixing für False Positives. Bei begrenzter Review-Kapazität ist die einfachere Lösung die bessere — nicht weil der Code teurer ist, sondern weil der Review-Aufwand für Fuzzy unverhältnismäßig steigt.

### Warnung 4: Genre-Ordner-Struktur
Die NAS-Filmstruktur nutzt Genre-Sammelordner (`Filme/Action/X-Men (2000)/`). Die Scan-Funktion muss 2 Ebenen tief suchen. Das ist kein Showstopper, aber im Code explizit zu behandeln — `os.listdir` auf einer Ebene reicht nicht. Die Funktion `find_existing_series_folder_by_id` (series_helper.py:5-33) ist hier die Blaupause — sie scannt ebenfalls eine Ebene. Für Filme muss sie um eine zweite Ebene (Genre-Ordner) erweitert werden.

---

## Zusammenfassung

**MVP-Empfehlung:** ID-basierter Duplikat-Hinweis für Filme im Preview-Modal. Kein Fuzzy, kein Fallback, keine Franchise. ~90 Zeilen Code insgesamt. Blockiert nichts, zeigt nur einen Hinweis.

**ROADMAP (als V2):** Franchise-Gruppierung über TMDb-Collection-API. Eigenes Feature, eigener PR.

**Veto:** Gegen Fuzzy-Name-Matching als primären Ansatz. Die ID ist da — sie zu nutzen ist einfacher, robuster und billiger als Namen zu raten.
