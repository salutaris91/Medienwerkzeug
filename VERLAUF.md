# Projektverlauf – Historie

Hier befindet sich die kumulative Historie des Projektfortschritts, ausgelagert aus `STAND.md`.

---

## Stand am 30.06.2026 (Phase 2.2e – Hauptflächen Emoji/UI-Polish)

- **Emoji-Polish der primären Ansichten, YouTube-Module, FAQ und Einstellungen (Branch: feature/phase2-main-surface-emoji-polish):**
  - **Login- & Einstellungsbereich:** Emojis bei Aktionen wie `🔒` (Passwort ändern), `🔓` (Abmelden), `💾` (Einstellungen speichern) und `🔓` (Anmelden) durch professionelle inline Lucide-SVGs (`lock`, `log-out`, `save`, `log-in`) ersetzt.
  - **YouTube-Abonnements & Details:**
    - Emojis in den Transferziel-Badges (`📁 NAS`, `☁️ pCloud`, `💻 Lokal`) sowie im Modus (`⚙️`), der Aktualisierung (`🔄`), Ausschlusskriterien (`🚫`), dem deutschen Sprachfilter (`🇩🇪`) und dem letzten Check (`⏱️`) durch passende inline Lucide-SVGs (`server`, `cloud`, `monitor`, `settings`, `refresh-cw`, `ban`, `clock`) bzw. neutralen Text ersetzt.
    - Die Buttons `Abo hinzufügen` (`➕`), `Jetzt alle prüfen` (`🔄`) und `Ignorieren` (`⌛`) auf SVGs umgerüstet.
  - **Smart-Inbox-Vorschläge:** Emojis in Medien-Typen-Badges (`🎬 Film`, `📺 Serie`, `🌿 Doku`, `🌸 Anime`) durch inline Lucide-SVGs (`film`, `tv`, `leaf`, `sparkles`) ersetzt.
  - **Ordnerauswahl, Statusmeldungen & Logs:**
    - Bereinigung verbleibender Emojis in der Normalisierungsvorschau (Ersetzen von `📂` und `📄` durch reinen Text) und im Dubletten-Vergleich (`💾 Auf NAS vorhanden` durch `server`-SVG ersetzt).
    - Entfernung von Emojis aus System-Erfolgsprotokollen in der Entwicklerkonsole (z. B. bei der Bereinigung, dem Import und dem Ordner-Merge).
  - **Software-Updates & Abhängigkeiten:** Update-Prüfbutton (`🔄 Auf Aktualisierung prüfen`) und Ladeindikatoren mit einheitlichen Lucide-SVGs (`refresh-cw`, `loader-2`) ausgestattet.

---

## Stand am 30.06.2026 (Phase 2.2c)

- **Inbox-Projekt-Cleanup & Sidebar-Entschlackung (Branch: feature/phase2-inbox-project-cleanup):**
  - **Startseite entschlackt:** Entfernung der kleinteiligen `Bereinigen`-Buttons neben Inbox und Outbox. Es verbleibt ein einziger, globaler `BEREINIGEN`-Button, der standardmäßig beides scannt.
  - **Quarantäne-Shortcut für Projekte:** Hinzufügen einer direkten Quarantäne-Aktion (`Quarantäne`-Button mit Papierkorb-SVG) an jedem erkannten Projekt in der Smart-Inbox-Vorschlagsliste der Startseite.
  - **Sichere Quarantäne:** Klick auf den Quarantäne-Button löst nach Bestätigung den Aufruf des bestehenden Endpunkts `/api/delete-project` aus, wodurch das Projektverzeichnis sicher in die Quarantäne verschoben wird.
  - **Sidebar-Entschlackung:** Die redundante Sidebar-Sektion `Projektordner` (`section-project-folders`) wurde komplett ausgeblendet, um Doppelungen zu vermeiden und Platz zu schaffen.
  - **Nullguards:** Robustheits-Guards im JavaScript sichern ab, dass keine Fehler auftreten, wenn die Sidebar-Elemente nicht gerendert oder ausgeblendet sind.

---

## Stand am 30.06.2026 (Phase 2.2b)

- **Phase 2.2b – Sicherer Output-Cleanup:**
  - Status: Erfolgreich implementiert und in `main` gemergt.
  - Anpassungen:
    - **Größenanzeige im Arbeitsbereich:** Hinzufügen von Echtzeit-Größenanzeigen (`inbox-size-display` und `outbox-size-display`) in der Startseiten-Kachel.
    - **Robuste Belegungserkennung:** Übergabe der exakten Bytes (`inbox_bytes`, `outbox_bytes`) über die Status-API, um auch KB-große Dateien zuverlässig zu erfassen und farblich als "nicht leer" zu markieren.
    - **Fokus im Modal:** Optische Hervorhebung der Output-Option (Medien Output) im Bereinigungs-Auswahl-Modal (Phase 1) mittels Akzentrahmen und eines `Empfohlen`-Badges zur Lenkung der Aufmerksamkeit.
    - **Strukturierte Vorschau:** Die Dateiliste im Bereinigungs-Modal gruppiert die Dateien nun strukturiert nach ihren übergeordneten Projektordnern, was die Auswertung stark vereinfacht.
    - **Dynamische Quarantäne-Semantik:** Kennzeichnung jeder Datei mit einem optischen `Quarantäne`-Badge (rot). Bei Abwahl ändert sich das Badge interaktiv zu `Behalten` (grün), um das Sicherheitsmodell visuell transparent zu machen.
    - **Sicherer Quarantäne-Flow:** Der Flow verschiebt Dateien ausschließlich in Quarantäne (`send_to_trash`), ohne endgültige Löschungen oder Emojis in der Haupt-UI einzuführen.

---

## Älterer Projektverlauf (v1.3.0 und davor)

- **Phase 2.2a – Informationsarchitektur Startseite, Output & Bibliotheks-Wartung:**
  - Die Startseiten-Kachel `card-smart-inbox` wurde in **„Arbeitsbereich & Inbox“** umbenannt und ist nun standardmäßig permanent sichtbar.
  - Integration von Inbox (Input) und Outbox (Output) Pfaden oben in der Kachel mit Direktaktionen (`Input öffnen` und `Output öffnen`), die über `window.openFolder` geladen werden.
  - Dynamische Anpassung der Button-Texte (`Input ansehen` / `Output ansehen`) im Docker-Modus, da `window.openFolder` dort die Web-Ordneransicht anzeigt.
  - Der Startseiten-Button wurde in **`BEREINIGEN`** umbenannt und mit dem Danger-Stil (`btn-danger`) als visuelle Risikoaktion ausgewiesen.
  - Bei 0 Projekten in der Inbox wird ein informativer Platzhalter-Hinweis angezeigt, anstatt die Karte auszublenden.
  - Die `Bibliotheks-Wartung` wurde mit einer neuen Sektion **„Medienpflege-Werkzeuge“** ausgestattet, in die die Kacheln für *NFO Agent*, *H.265 Batch-Konvertierung*, *Ordner bereinigen* und *Speicherziel-Syncing* gespiegelt wurden.
  - Präzisierung der Kachel-Untertitel für *Ordner bereinigen* zu **„Junk-Dateien & leere Ordner“** (sowohl in der Bibliotheks-Wartung als auch im Werkzeuge-Dashboard).
  - Die Original-Einstiege im *Werkzeuge*-Tab bleiben stabil und funktionsfähig erhalten.

- **Phase 2.1 Navigation & Konsole:**
  - Der Sidebar-Eintrag "Warteschlange" wurde gelöscht. Der Einstieg erfolgt nun ausschließlich über die Topbar.
  - Sidebar-Labels: "Online-Medien" wurde in "Video-Downloader" und "Bibliothek" in "Bibliotheks-Wartung" umbenannt. UI-Ansichten blieben unverändert.
  - Konsolen-Steuerung (Dev-Mode): Die Konsole wird nur noch angezeigt und ist nur noch ansteuerbar, wenn die Umgebungsvariable `MW_DEV_MODE=true` (bzw. 1, yes, on) aktiv ist UND `show_console=true` in den Einstellungen gesetzt ist.
  - Console-Checkbox: Die Checkbox "Entwickler-Konsole dauerhaft einblenden" wird in den Einstellungen bei inaktivem Entwicklermodus ausgeblendet.
  - Sicherheit & Handler: Alle Toggle-/Klick- und Weiterleitungspfade wurden abgesichert, so dass die Konsole im Nicht-Entwicklermodus niemals eingeblendet wird.

- **Frontend Trust Reskin Phase 1:**
  - Default-Theme (`body.theme-deep-space` & `:root`) auf mattes Zink/Graphit-Farbschema umgestellt.
  - Eckenradien verringert, Hover-Glows/Cone-Effekte deaktiviert.
  - Emojis aus der Navigations-Sidebar durch inline-SVGs im Lucide-Stil ersetzt.
  - Emojis und Texte von Primär- und Risikoaktionen bereinigt.
  - Emojis von Warnbannern und Card-Headern durch Lucide-SVGs ersetzt.
  - Warteschlangen-Rendering komplett emoji-frei überarbeitet: nutzt nun Lucide-Stil SVGs.

- **Ältere Bugfixes & Features:**
  - Behebung von TVDB-Episoden-NFO-Problemen und fuzzy matching.
  - Implementierung von pro-Job-Logging.
  - Härtung der pCloud-FUSE-Integration und Normalisierung von Episodentiteln.
  - Implementierung des unique session cookie names.
  - Härtung des asynchronen Queue-Waitings.
