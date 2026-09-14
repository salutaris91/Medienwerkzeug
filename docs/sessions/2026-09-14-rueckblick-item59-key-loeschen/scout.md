## 1. Kurzurteil

Die Umsetzung ist handwerklich solide und scope-treu: Zweistufigkeit (× → Inline-Confirm), W1-Erhalt, Escape-Reset, Revert-bei-Neueingabe und DOM-Struktur-Absicherung über alle 6 Felder sind korrekt und konsistent umgesetzt. Die Tests decken AK1–AK7 plus die interessanten Edge-Cases (Escape während Confirm, neue Eingabe nach Confirm, DOM-Struktur) ab. Backend und `persistence.py` wurden wie vorgesehen nicht angefasst. Keine Tests ausgeführt, kein Git-Status verifiziert — Belege obliegen dem Worker/Alex.

## 2. Chancen / positive Anschlussmöglichkeiten

1. **Generisches Inline-Confirm-Pattern.** Der `.masked-key-confirm`-Block ist ein wiederverwendbares UI-Idiom (destruktive Aktion mit Rückfrage). Falls später weitere „gefährliche" Aktionen dazukommen (z. B. „Alle Jobs zurücksetzen", „Rclone-Config löschen"), lässt sich das Muster als kleine Helfer-Funktion auskoppeln, ohne es jedes Mal neu zu erfinden.

2. **Tastatur- und Screenreader-Pfad sind schon mitgedacht.** `aria-label`, `aria-hidden`, `role="group"` auf dem Confirm-Container, `aria-live="polite"` am Error — das ist eine gute Basis. Anschlussmöglichkeit: Nach dem Öffnen des Confirm-Dialogs den Fokus programmatisch auf „Abbrechen" setzen (Fokus-Falle auf Zeit), damit Screenreader-User nicht erst suchen müssen.

3. **Integrationstest-Pfad sichtbar.** Die Frontend-Tests prüfen den DOM- und Validate-Pfad bis zum leeren `changedFields`-Eintrag. Ein schlanker Backend-Integrationstest (Python), der einen leeren String im Settings-Payload explizit als „Key entfernen" durch `persistence.py` jagt, würde die letzte Lücke schließen und dokumentieren, dass die Schnittstelle zwischen Frontend-Absicht und Backend-Semantik stabil ist.

4. **Theme-Fähigkeit ist angelegt.** Alle Danger-Farben laufen über `var(--danger, #ef4444)`. Wenn irgendwann ein Theme `--danger` überschreibt (z. B. für einen High-Contrast- oder Superfood-Light-Modus), zieht der Lösch-Confirm automatisch mit. Der scout-Hinweis aus Item #60 (kein Theme überschreibt `--danger` bisher) gilt hier ebenso — die Vorarbeit ist geleistet.

5. **Badge-Titel „Wird beim Speichern gelöscht" als UX-Anker.** Der Titel nach Confirm ist klarer als das alte „Wird entfernt" aus dem W1-Kontext. Das könnte als Formulierungsvorlage für künftige „pending save"-Zustände dienen (einheitliche Sprache über alle Feldtypen hinweg).

## 3. Ideen, die bewusst NICHT in diesem Item umgesetzt werden sollten

1. **Native `window.confirm()` statt Inline-Dialog.** Wäre eine Zeile Code, aber: nicht theme-fähig, browser-spezifisches Aussehen, blockierend, kein Escape-Hook, und bricht die visuelle Konsistenz mit dem Rest der Settings-UI. Die Inline-Lösung ist richtig; `window.confirm` wäre ein Rückschritt.

2. **Zweiter, separater API-Call nur für Löschen.** Man könnte einen dedizierten `DELETE /api/settings/<key>`-Endpunkt einführen. Das würde die Semantik „leerer Wert = löschen" nochmals explizit machen, aber: das Backend kann es bereits über den bestehenden Save-Pfad, und ein zweiter Endpunkt vergrößert die Angriffsfläche (Auth, Rate-Limit, Whitelist-Pflege in `system_api.py`) ohne neuen Nutzen. Bleibt besser bei „leerer Wert im bestehenden Payload".

3. **Touch-Target-Vergrößerung (22×22 → 44×44 px) in diesem Item.** Der ×-Button ist mit 22×22 px auf Desktop ausreichend, auf Mobile ggf. knapp. Aber: eine Größenänderung beeinflusst das Layout des `masked-key-input-wrapper` (Padding-right, Badge-Position) und sollte nicht nebenbei in einem Löschweg-Item passieren — eigenes UI/UX-Item mit visuellem Abgleich.

4. **Undo-Fenster nach dem Speichern.** „Key wurde gelöscht — Rückgängig (5 s)" wäre nett, ist aber ein eigenes Feature mit eigenem State-Management (Timer, Toast, Re-Save). Der aktuelle Confirm-vor-Lösch-Flow bietet bereits zwei Chancen gegen versehentliches Löschen (× + Bestätigen). Ein Undo danach wäre Over-Engineering für ein Ereignis, das statistisch selten und reversibel ist (Key neu eingeben oder `.env` editieren).

5. **`pendingDelete`-Flag konsolidieren.** `dataset.pendingDelete` wird gesetzt und gelesen, aber der einzige semantische Unterschied zu `dataset.deleted` ist, dass `pendingDelete` im `input`-Handler ebenfalls zurückgesetzt wird. Ob die zwei Flags beide nötig sind oder `pendingDelete` historisch aus einer früheren Iteration stammt, habe ich nicht vollständig aufgelöst — das ist eine Aufräumfrage, kein funktionales Defizit. Nicht in diesem Item anfassen.

## 4. Offene Fragen

- **Click-Target auf Mobile:** 22×22 px liegen unter den üblichen 44×44 px-Empfehlungen (WCAG 2.5.8 Target Size). Ist das ein bekannter Kompromiss, weil der Button nur bei `hasKey=true` sichtbar ist und die Nutzung auf Mobile selten sein dürfte, oder soll das ein eigenes CSS-Item werden?

- **`pendingDelete` vs. `deleted`:** Beide Flags werden in `isDeleted` gemeinsam ausgewertet (`||`). Gibt es einen Zustand, in dem nur eines von beiden `true` sein soll, oder ist `pendingDelete` ein Relikt, das man bei Gelegenheit auflösen könnte?

- **Progressive Enhancement ohne JS:** Die `style="display: none;"`-Attribute im HTML sind initial korrekt (Button versteckt ohne JS). Wenn JS lädt, übernimmt `updateMaskedInputState`. Ist das als bewusstes Progressive-Enhancement-Pattern gedacht und soll so bleiben, oder soll das CSS den Default setzen und die Inline-Styles entfernt werden?

- **Fokus-Management nach Confirm-Öffnung:** Nach Klick auf × springt der Confirm-Dialog auf, aber der Fokus bleibt auf dem (nun versteckten) ×-Button. Soll der Fokus auf „Abbrechen" oder „Löschen" gesetzt werden, oder ist das bewusst offen gelassen?
