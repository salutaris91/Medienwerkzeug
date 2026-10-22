<!-- Mechanisch aus `opencode export ses_e9b6895a8ffebzKBFHJBvOFzrC` extrahiert (Claude Code, 2026-10-22, Rückkanal): alle Assistant-Textteile in Reihenfolge, ungekürzt, unverändert (nur Trailing Whitespace entfernt). Rohdatei: Kit scripts/gate-a2/logs/2026-10-22-roadmap89-sample-ordner/rueckkanal/export-produktberater-e9b6895a8ffe.json -->

Jetzt prüfe ich noch die TV-Vorschau-Sample-Behandlung in `queue_api.py` und die Frontend-Stellen, die im Briefing referenziert werden:



---

Hier ist meine Produktbewertung.

---

## (a) Nutzerwert-Urteil

**Der Fix löst das Lanterns-Problem vollständig auf der Erkennungs- und Verarbeitungsebene.** Die Kette wirkt an beiden Ursachen:

- **U1 (Erkennung):** `project_api.py:1508–1524` zählt jetzt `non_sample_group_videos` statt `group_video_files`. Für das Lanterns-Muster (1× ~2,7 GB + 1× ~68 MB Sample) ergibt das genau 1 Nicht-Sample-Video → `single_video_relpath` und `single_video_query` werden gesetzt → das Frontend (`app.js:12527`, `:12537`, `:13544`) macht den Ordner gruppierbar und versieht ihn mit einem Kästchen. **Das funktioniert für alle acht Lanterns-Ordner identisch**, weil `single_video_query` aus dem Dateinamen `lanterns.s01e0x….mkv` jeweils `"lanterns"` extrahiert wird (project_api.py:1528–1532) und das Frontend nach exakt diesem String als Gruppenschlüssel gruppiert (`app.js:12550`).

- **U2 (NFO-Abbruch):** `find_group_companion_files` (`helpers.py:937`) überspringt `.nfo`/`.sfv` → die Release-NFO wandert nicht als Begleitdatei mit → keine Kollision mit der vom Worker erzeugten Episoden-NFO → kein `RuntimeError`. AK8 belegt das End-to-End.

**Wo der Nutzerpfad trotzdem steinig bleibt:**

1. **Anzeige „2 Datei(en)"** — `video_count` zählt unverändert alle Videos (project_api.py:1347, inkl. Sample). Der Nutzer sieht also „2 Videos", obwohl nur 1 verarbeitet wird. Das Briefing verweist das explizit an #81. **Akzeptabel für MVP**, aber ein potenzieller Stolperer bei der Handprüfung.

2. **Reste in der Inbox** — Sample, Release-.nfo, .sfv und der Werbeordner bleiben nach der Verarbeitung in den Inbox-Ordnern liegen. Das ist bekannt (#81) und im Briefing explizit ausgeklammert. **Kein Blocker**, aber der Nutzer muss wissen, dass die Inbox nach dem Lauf nicht „leer" ist.

3. **Gruppenschlüssel kleingeschrieben** — `single_video_query` = `"lanterns"` (lowercase, aus dem Dateinamen). Die Gruppierung funktioniert (alle 8 Ordner haben denselben Schlüssel), aber der Banner zeigt „lanterns (8 Folgen)" statt „Lanterns (8 Folgen)". **Kosmetisch, kein Funktionsverlust.**

---

## (b) Vollständigkeits-Lücken

**1. `video_count`-Inkonsistenz zwischen 6er- und 10er-Extension-Set** — `project_api.py:1321` verwendet `video_exts` (6 Endungen) für `video_count`, während `project_api.py:1342` `GROUP_VIDEO_EXTENSIONS` (10 Endungen) für die Sample-Erkennung verwendet. Für .mkv-Dateien (Lanterns) ist das irrelevant, aber bei einem Ordner mit `.flv`-Sample und `.mkv`-Hauptvideo würde `video_count = 1` angezeigt, während die Sample-Erkennung korrekt 2 Videos sieht. **Kein Bug im Lanterns-Szenario, aber eine latente Inkonsistenz.** → ROADMAP-Kandidat.

**2. TV-Vorschau (non-files[]-Pfad) nutzt `find_sample_video_files` nicht explizit** — Im nicht-`files[]`-TV-Pfad (`queue_api.py:112`, `all_files = find_files_recursively(current_dir)`) werden alle Dateien rekursiv eingesammelt. Die Sample-Erkennung erfolgt hier implizit dadurch, dass Sample-Videos kein Mapping haben und als Junk enden. Das funktioniert, aber es gibt keinen expliziten Test, der das Lanterns-Muster im **non-files[]-TV-Vorschau**-Pfad prüft. AK6 testet nur den Movie-Pfad. **Keine Lücke im files[]-Arbeitsablauf (der für Lanterns verwendet wird), aber eine Testlücke für den alternativen Pfad.**

**3. `find_sample_video_files` — Pfadsegment-Erkennung auf Windows-Pfaden** — `helpers.py:819` ersetzt `\\` durch `/` vor dem Splitten, also korrekt für Windows. **Keine Lücke.**

**4. API.md-Dokumentation vollständig** — `API.md:146` beschreibt `single_video_relpath` mit beiden Kriterien, `API.md:270` beschreibt den `.nfo`/`.sfv`-Ausschluss. **AK9 erfüllt.**

---

## (c) Chancen / Folgepunkte

1. **Muster wirkt universell:** Die Sample-Erkennung wirkt auf **alle** Inbox-Ordner, nicht nur Lanterns. Jeder Ordner mit einer großen und einer kleinen Videodatei (ohne „sample" im Namen) wird jetzt als Einzelvideo-Ordner erkannt (AK3). Das ist ein **implizites Feature**, das bei anderen Release-Gruppen ebenfalls hilft — z. B. Ordner mit Bonus-Clips, Trailern oder Teasern neben der Hauptfolge.

2. **Falsch-Positive möglich:** Ein Ordner mit einer echten kleinen Episode (< 300 MB) neben einer großen Episode (> 300 MB) würde die kleine als Sample einstufen (Kriterium 2). Das ist in AK4/AK5 teilweise abgefedert (zwei kleine Videos → kein Kriterium 2), aber der Fall „eine große + eine echte kleine Folge" bleibt theoretisch. **In der Praxis selten** (Szene-Releases haben fast immer > 300 MB pro Folge), aber dokumentiert in ADR-89-2 als bekanntes Risiko.

3. **Profil-Zuordnung bei Kleinschreibung:** Der Fuzzy-Match (`project_api.py:1453–1458`) findet Profile case-insensitiv. Aber: Wenn Alex ein Profil „Lanterns" anlegt und die Inbox „lanterns" vorschlägt, funktioniert der Match. **Kein Folgepunkt, funktioniert bereits.**

4. **ROADMAP #81 wird dringlicher:** Nachdem die Erkennung jetzt funktioniert, bleiben Sample/Reste in der Inbox. Der Nutzer wird erwarten, dass die Inbox nach der Verarbeitung „sauber" ist. **#81 sollte als Nächstes kommen.**

---

## (d) Verworfene Alternativen — Bewertung

| Verworfene Alternative | Meine Einschätzung |
|---|---|
| **Release-.nfo als Episoden-NFO übernehmen** | **Korrekt verworfen.** Szene-NFOs sind ASCII-Art, kein `<episodedetails>`-XML. Medienwerkzeug erzeugt eigene NFOs. |
| **`.nfo` nur bei gesetztem Metadatendienst ausschließen (Variante A2)** | **Korrekt verworfen.** Die einfachere Regel (immer ausschließen) ist robuster und vermeidet eine bedingte Logik, die bei späteren Änderungen leicht übersehen wird. |
| **Sample/Werbe-Ordner aufräumen** | **Korrekt zurückgestellt.** #81 hat eine ungeklärte Ursache; das hier ist der akute Fix. |
| **`video_count` anpassen** | **Korrekt zurückgestellt.** Anzeigeänderung wäre ein separater Scope. |
| **Frontend-Änderungen** | **Korrekt: keine nötig.** Das Frontend reagiert bereits auf `single_video_relpath`. |
| **Kreativteam-Akte** | **Korrekt weggelassen.** Ursache und Lösung sind belegt; die schlanke Kette ist angemessen. |

**Keine der verworfenen Alternativen würde ich wieder einfordern.** Die Scope-Entscheidungen sind konsistent und begründet.

---

## (e) Gesamtempfehlung

**JA — Abnahme empfohlen.**

**Begründung:**

- Der Fix löst das Live-Problem (Lanterns-Gruppierung + NFO-Abbruch) vollständig und belegbar.
- Der Scope ist richtig gewählt: MVP mit minimaler Angriffsfläche, keine Frontend-Änderungen, shared helper function verhindert Drift.
- Die Testabdeckung ist umfangreich: AK1–AK8 decken alle Kriterien, Kollisionsschutz und End-to-End; die Rot-Probe gegen `f0a29a4` stellt sicher, dass die Tests den Fix tatsächlich Requiren.
- Die Belege (537 passed/1 deselected, Frontend 231/231, Rot-Probe, Probe-Instanz) sind plausibel vollständig und konsistent mit dem Code.
- Die bekannten Restriktionen (Kleinschreibung, Reste in Inbox, `video_count`) sind im Briefing explizit als nicht-im-Scope dokumentiert und in der ROADMAP (#81) als Folgepunkte verankert.

**Nicht durchgeführte Prüfungen (offen):**

- Ich habe die `ak0-ausgangsmessung.md` nicht gelesen (nicht im Auftrag spezifiziert, aber im Briefing als AK0 referenziert).
- Ich habe den `git diff --check`-Zustand nicht verifiziert (kein Shell-Zugriff).
- Ich habe die Probe-Instanz mit dem nachgebauten Lanterns-Ordner nicht live gesehen — die Belege dafür stammen aus der Claude-Code-Sitzung.
- Ich habe `test_movie_processing_fixes.py:160ff.` (Bestandsschutz AK6) nicht gelesen, sondern nur den Verweis im Briefing und Testcode geprüft.
- Ich habe nicht geprüft, ob `find_files_recursively` im non-files[]-TV-Pfad Sample-Unterordner korrekt durchläuft (das ist bestehendes Verhalten, nicht Teil dieses Fixes).
