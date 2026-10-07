# Rohoutput produktberater — Kreativteam-Session 2026-10-06 (Akt 2)

Kontext: Konsultiert zum Scope-Bündel (#46-Clientfix + Namenskonflikt-Serverfix + Version-Bump + ROADMAP-Texte #64-#66) und den Akzeptanzkriterien. Prompt siehe 00-kickoff.md / Briefing-Auftrag.

Hinweis Claude Code (2026-10-07): Der Text unterhalb der nächsten Linie ist die wörtliche Subagent-Antwort aus der OpenCode-Sitzung (ceo-planner ses_eede285a6ffeLjfbSwIYSoRN4T, Subagent-Sitzung ses_eedd9c23bffeLyoYp0Ax7JwT7G; Quelle: opencode export, nur die <task>-Hülle entfernt). Wiederhergestellt nach Alex-Go, weil die zuvor archivierte Fassung vom Moderator bearbeitet worden war. Einzige Abweichung vom Export: Leerzeichen am Zeilenende von Zeile 82 (Leerzeile mit zwei Leerzeichen) entfernt, wegen des Whitespace-Checks im Pre-Commit-Hook (Alex-Go 2026-10-07).

---

<task_result>
## Scope-Wächter-Bewertung

Ich habe den Code verifiziert. Hier meine Bewertung:

---

### 1. PR-Bündelung: Sinnvoll oder trennen?

**Bewertung: Bündelung ist sinnvoll.**

**Begründung:**
- **Fix #46 (Dropdown-Refresh)**: 5–10 Zeilen in `app.js:10569-10591`. Selbstständiger Frontend-Change.
- **Bugfix Endlosschleife**: 10–15 Zeilen in `queue_api.py:750-762`. Backend-Change, unabhängig von #46.
- **Cache-Bump**: Mechanisch, erzwungen durch Test. 10 Stellen `?v=93` → `?v=94`.
- **ROADMAP-Texte**: Kein Code, nur Markdown. Explicitly "no implementation".

**Nutzer-Nutzen je Teil:**
- **#46**: Nutzer sieht nach Profil-Speichern sofort das neue Profil im Dropdown (bisher: manuell neu laden).
- **Bugfix**: Nutzer bleibt nicht in Endlosschleife hängen, wenn er "NAS-Name übernehmen" klickt.
- **Cache-Bump**: Keine direkte Sichtbarkeit, aber notwendig für Deployment.
- **ROADMAP**: Keine direkte Auswirkung, aber Dokumentation für zukünftige Arbeit.

**Trade-off bei Trennung:**
- 3 separate PRs = 3× Review-Overhead für Alex (Engpass).
- Alle Changes sind klein, nicht-konfliktär, und Teil derselben Session.
- ROADMAP-Texte sind explizit "no implementation" — die können trivial im selben PR mitreisen.

**Empfehlung:** **Ein PR.** Die Teile sind unabhängig, aber alle klein und Teil desselben Arbeitszyklus. Trennung würde Alex' Review-Zeit verschwenden, ohne Qualitätsgewinn.

---

### 2. Over-Engineering oder Scope-Creep?

**Bewertung: Kein Over-Engineering. Scope ist korrekt.**

**Verifikation:**
- **Dropdown-Refresh nur bei Save**: Ich habe geprüft, ob Profile gelöscht/umbenannt werden können.
  - `deleteProfileFromModal` (app.js:15039-15061) ruft **bereits** `populateLocalProfilesDropdown()` auf (Zeile 15052-15053). ✅
  - Profil-Rename/Edit existiert nicht (gegreppt: `renameProfile`, `editProfile`, `updateProfile`, `saveProfile` — keine Treffer). ✅
  - **Fazit:** Die Lücke ist nur im Save-on-Execute-Pfad (app.js:10569). Der Plan adressiert genau das. Kein Scope-Creep.

- **Endlosschleifen-Fix**: Die Regel ist minimal und klar:
  - Wenn `nas_show_folder` (nach Cleaning) == `nas_match_folder` ODER `metadata_show_name` → kein Hinweis.
  - Bei drittem Namen → Hinweis bleibt.
  - **Kein Over-Engineering.**

- **Ausführung läuft weiter**: Der aktuelle Code (app.js:10589-10591) fängt Fehler im `try/catch` ab, blockiert aber nicht. Die Ausführung geht bei Zeile 10596 weiter (`closePreviewModal()`). ✅ **Keine Änderung nötig.**

**Fehlt etwas Wesentliches?**
- **Nein.** Ich habe geprüft:
  - Dropdown-Refresh nach Löschung: bereits implementiert.
  - Dropdown-Refresh nach Änderung: keine Änderungsfunktion vorhanden.
  - Vorschau nach Namensübernahme: Der Plan adressiert die Endlosschleife. Weitere Änderungen (z. B. automatische Aktualisierung anderer Felder) sind nicht nötig — der Nutzer sieht den korrekten Namen im Hinweis und kann ihn übernehmen.

---

### 3. AK-Lücken

**Bewertung: AK sind MVP-tauglich, aber zwei Präzisierungen nötig.**

**Verifikation der AK:**

- **AK0 (Ausgangsmessung)**: ✅ Klar und notwendig.
- **AK1 (bestehende Tests grün)**: ✅ Klar. Ich habe die Tests gelesen (test_utils.py:3047-3181). Sie testen:
  - `test_find_folder_by_id_and_name_mismatch`: NAS-Ordner "Yu-Gi-Oh! (2000)" ≠ Metadaten-Name "Yu-Gi-Oh! Duel Monsters" → mismatch erwartet. ✅
  - `test_false_positive_show_name_mismatch_with_different_years`: Mocked `find_existing_series_folder_by_id` returns "Avatar - Der Herr der Elemente (2024)", NAS-Ordner ist "Avatar - Der Herr der Elemente (2005)", Metadaten-Name ist "Avatar - Der Herr der Elemente (2024)" → `nas_match_folder` == `metadata_show_name` → kein mismatch. ✅
  - **Beide Tests bleiben unverändert grün**, weil sie keine `nas_show_folder` im Payload haben.

- **AK2-AK4 (neue Backend-Tests)**: ✅ Die drei Szenarien sind korrekt:
  - AK2: `nas_show_folder` == `nas_match_folder` → kein mismatch.
  - AK3: `nas_show_folder` == `metadata_show_name` → kein mismatch.
  - AK4: `nas_show_folder` == dritter Name → mismatch bleibt.

  **Lücke:** Der Plan sagt, `nas_show_folder` soll "nach derselben Bereinigung wie in series_helper.py:44-46" verglichen werden. Das bedeutet: `limit_filename_length(clean_series_name_for_fs(str(nas_show_folder).strip()))`. Die AK sollten explizit testen, dass das Cleaning korrekt angewendet wird (z. B. wenn `nas_show_folder` trailing spaces oder Sonderzeichen hat). **Empfehlung:** Ein vierter Testfall, der prüft, dass `nas_show_folder` mit trailing spaces trotzdem als Match erkannt wird.

- **AK5-AK6 (Frontend-Tests)**: ⚠️ **Lücke erkannt.**
  - Der Plan sagt: "populateLocalProfilesDropdown() nur bei response.ok UND success:true; sonst appendConsoleLog-Fehlerhinweis".
  - **Aber:** Der aktuelle Code (app.js:10569-10588) prüft die Response **gar nicht**. Er ruft nur `await fetch(...)` auf und ignoriert das Ergebnis.
  - **Implikation:** Der Fix muss:
    1. `const response = await fetch(...)` speichern.
    2. `response.ok` UND `data.success` prüfen.
    3. Bei Erfolg: `populateLocalProfilesDropdown()` aufrufen.
    4. Bei Fehler: `appendConsoleLog()` mit Fehlermeldung aufrufen.
    5. Ausführung läuft in jedem Fall weiter.
  - **Lücke in AK:** Die AK sollten explizit testen:
    - **Fall A:** `response.ok = true`, `data.success = true` → `populateLocalProfilesDropdown()` aufgerufen.
    - **Fall B:** `response.ok = true`, `data.success = false` → `appendConsoleLog()` aufgerufen, `populateLocalProfilesDropdown()` **nicht** aufgerufen.
    - **Fall C:** `response.ok = false` → `appendConsoleLog()` aufgerufen, `populateLocalProfilesDropdown()` **nicht** aufgerufen.
    - **Fall D:** Netzwerkfehler (catch-Branch) → `appendConsoleLog()` aufgerufen, Ausführung läuft weiter.
  - **Empfehlung:** AK5-AK6 sollten diese vier Fälle explizit auflisten.

- **AK7 (Cache-Bump)**: ✅ Klar. Test erzwingt es.

- **AK8 (Abschlussmessung)**: ✅ Klar. Die Ausnahme `test_conversion_estimation_test_encode` ist dokumentiert.

---

### 4. Position

**FREIGEBEN MIT ÄNDERUNGEN**

**Begründung je Punkt:**

1. **PR-Bündelung:** ✅ **Freigegeben.** Alle Teile sind klein, nicht-konfliktär, und Teil desselben Arbeitszyklus. Trennung würde Alex' Review-Zeit verschwenden.

2. **Scope:** ✅ **Freigegeben.** Kein Over-Engineering. Dropdown-Refresh nur bei Save ist korrekt (Löschung bereits implementiert, Rename existiert nicht). Endlosschleifen-Fix ist minimal.

3. **AK:** ⚠️ **Freigegeben mit zwei Änderungen:**
   - **Änderung 1:** AK2-AK4 sollten um einen vierten Testfall ergänzt werden, der prüft, dass `nas_show_folder` mit trailing spaces trotzdem als Match erkannt wird (Cleaning-Verifikation).
   - **Änderung 2:** AK5-AK6 sollten explizit die vier Fälle (A-D, siehe oben) auflisten, insbesondere den Fall `response.ok = true` aber `data.success = false` (Backend liefert HTTP 200 mit `{"success": false}`).

**Begründung für Änderungen:**
- Die Cleaning-Verifikation stellt sicher, dass der Worker die Bereinigung korrekt umsetzt (nicht nur einfacher String-Vergleich).
- Die explizite Auflistung der vier Frontend-Fälle verhindert, dass der Worker den Fall `response.ok = true` aber `data.success = false` übersieht (das ist der subtilste Fall, weil das Backend bei fehlgeschlagener Speicherung HTTP 200 liefert).

---

### Zusammenfassung

| Aspekt | Urteil | Begründung |
|--------|--------|------------|
| PR-Bündelung | ✅ Freigegeben | Alle Teile klein, nicht-konfliktär, gleicher Zyklus |
| Scope | ✅ Freigegeben | Kein Over-Engineering, Lücken korrekt adressiert |
| AK | ⚠️ Freigegeben mit Änderungen | Cleaning-Verifikation + explizite Frontend-Fälle |

**Nächster Schritt:** Alex entscheidet über die zwei AK-Änderungen. Wenn akzeptiert, kann der Worker starten.
</task_result>
