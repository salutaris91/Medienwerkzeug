# Scout-Recherche: Geführter Film-Assistent — UI-Patterns, Wizard-Technik, Bildquellen-Rechte

**Rolle:** Scout · **Datum:** 2026-11-06 · **Auftrag:** ROADMAP #92
**Status:** Recherche abgeschlossen. Webzugriff war verfügbar — alle Quellen wurden am 2026-11-06 live verifiziert (URLs und Abrufdatum in Abschnitt 6).

> Archivierungsvermerk (Orchestrator, 2026-11-06): Beitrag unverändert übernommen; der Kopfblock („Rolle/Datum/Status") stammt vom Scout selbst.

---

## 1. Vorbilder / Patterns

### 1.1 Emby — „Identify" und „Edit Images"

Emby trennt die Aufgaben klar in zwei Dialoge:

- **Identify** (Quellen-Suche + Treffer-Auswahl): Ein Modal mit Suchfeldern (Titel, Jahr, TMDb/IMDb-ID), darunter eine Ergebnisliste mit Poster-Miniatur, Titel, Jahr und Provider-Badge. Der Nutzer wählt einen Treffer → Metadaten werden geladen. Das ist exakt das Muster für **Schritt 1** unseres Assistenten.
- **Edit Images** (Artwork wählen): Nach dem Identify oder separat über das „…"-Menü aufrufbar. Der Dialog zeigt den aktuellen Zustand (Poster, Backdrop, Logo, Thumb) als Karten mit „…"-Button pro Rolle. „Search" öffnet eine Grid-Ansicht aller verfügbaren Bilder eines Typs (von TMDb, Fanart.tv, IMDb) — große Vorschaubilder, Klick wählt aus. „Add" erlaubt URL-Eingabe oder Datei-Upload.

**Übertragbares Muster:** Die Trennung „Suche → Trefferliste → Bestätigung" statt alles in einem Wizzard. Emby macht *keinen* geführten Wizard — es sind einzelne kontextbezogene Modals. Für unseren Assistenten bedeutet das: Die vier Schritte als **Tabs oder Step-Indikator innerhalb eines einzigen Modals** zu bauen, geht über Emby hinaus — ist aber genau die Verbesserung, die Alex will („ähnlich wie bei Emby, aber geführt").

**Was überdimensioniert wäre:** Emby's „Refresh Metadata" mit Replace-Existing-Images-Checkbox ist ein Batch-Tool für ganze Bibliotheken. Unser Assistent ist Einzelfilm — diese Komplexität brauchen wir nicht.

### 1.2 Jellyfin — Tab-basierter Metadata-Editor

Jellyfin hat (Stand jellyfin-web) einen Metadata-Editor mit **vertikalen Tabs** (Desktop) bzw. horizontalen Tabs (Mobile):

1. **Main** — Titel, Originaltitel, Jahr, Sort-Titel, Overview
2. **Details** — FSK, Genres, Tags, Studios, IDs
3. **Cast & Crew** — Personenliste
4. **Images** — Bildauswahl

**Interessant für uns:** Das Lock-Icon-Pro-Field-Konzept (aus der jellyfin-vue-Diskussion #130): Jedes Feld hat ein „Auge"/Schloss-Icon, das steuert, ob ein Refresh-Metadata-Lauf dieses Feld überschreiben darf. Das ist für unseren Assistenten nicht direkt relevant (wir haben keinen Refresh-Lauf), aber das **Tab-Gruppierungsmuster** ist wertvoll: Es zeigt, wie man 30+ Felder in vier logische Gruppen aufteilt — genau unsere Schritt 2 (Metadaten).

**Was überdimensioniert wäre:** Jellyfin's Edit-Images-Tab ist relativ rudimentär — nur aktuelle Bilder mit Replace-Option. Die Grid-Auswahl aus mehreren Quellen fehlt weitgehend. Kein Vorbild für Schritt 3.

### 1.3 Stash — Tagger View (Side-by-Side-Vergleich)

Stash hat ein besonders interessantes Muster für **Metadaten-Vergleich**:

- **Tagger View**: Links die lokale Datei mit ihrem aktuellen Zustand, rechts die Treffer aus der Quelle (stash-box oder Scraper). Felder werden **paarweise** angezeigt: Originalwert → neuer Wert, mit Farbcode für Match-Qualität. Der Nutzer kann pro Feld entscheiden, ob er den neuen Wert übernehmen will.
- **Identify Task** (Batch): Feld-spezifische Strategien pro Feld: *Ignore* / *Overwrite* / *Merge*. Für jeden Feldtyp einzeln konfigurierbar.

**Übertragbares Muster für Schritt 2:** Die Side-by-Side-Darstellung „bisher → neu" mit **pro-Feld-Auswahl** (Checkbox oder Badge-Click). Das ist deutlich mächtiger als Emby/Jellyfin, aber für unseren „Metadaten vergleichen und bearbeiten"-Schritt ideal. Konkret: Jedes Feld zeigt den aktuellen Wert und den TMDb-Wert nebeneinander; der Nutzer klickt den gewünschten Wert an (oder tippt selbst). Die Multi-Provider-Feld-Badges (#55) passen perfekt dazu: Pro Feld zeigt ein Badge, von welchem Provider der Wert kommt.

### 1.4 MusicBrainz Picard — Zwei-Pane-Matching und Farbcode

Picard ist das Gold-Standard-Muster für **„Datei mit Datenbank abgleichen"**:

- **Zwei Panes**: Links „Unclustered Files" (lokale Dateien), rechts „Release" (Datenbank-Treffer).
- **Farbcode für Match-Qualität**: Grün = perfekt, Gelb = gut, Orange = fraglich, Rot = schlecht.
- **Original Values vs. New Values**: Unten eine Tabelle mit allen Feldern, paarweiser Vergleich.
- **Drag & Drop zum Korrigieren**: Wenn Picard falsch gematcht hat, zieht man den Track an die richtige Stelle.

**Übertragbares Muster:** Der **Farbcode für Datenqualität** ist brilliant für Schritt 2. Beispiel: Ein Feld wie „Plot" ist grün, wenn TMDb und lokale NFO übereinstimmen; gelb, wenn sie abweichen; rot, wenn lokal gar nichts steht. Das gibt dem Nutzer auf einen Blick Orientierung, wo Handlungsbedarf besteht.

**Was NICHT übertragbar ist:** Picard's Drag-and-Drop-Track-Matching ist für Audio-Dateien mit variabler Trackzahl — für einen Film mit festen Metadaten wäre das Overkill.

### 1.5 Kodi — „Choose Art" Dialog und Artwork-Downloade

Kodi's „Choose Art"-Dialog (aus dem Wiki dokumentiert):

1. Kontextmenü → „Choose Art"
2. **Artwork-Typ wählen**: Poster, Fanart, Banner, Thumb, Clearlogo, Disc, …
3. **Grid aller verfügbaren Bilder** dieses Typs (vom Scraper aus TMDb/TVDB/Fanart.tv)
4. Klick → Bild wird übernommen

**Artwork Downloader / Artwork Beef** (Kodi-Add-ons):
- Laden alle verfügbaren Bilder in lokalem Bulk-Download
- Zeigen bei mehreren Treffern einen **Auswahl-Dialog** mit Vorschaubildern
- Unterstützen „Multiple Images" pro Typ (extrafanart)

**Übertragbares Muster für Schritt 3:** Das **Grid mit Auswahl/Abwahl** ist genau das, was wir brauchen. Pro Artwork-Typ (Poster, Fanart) ein Grid; Klick auf ein Bild markiert es als „gewählt" (Häkchen-Overlay); ein weiteres Klick deselektiert. Das gewählte Bild wird beim „Übernehmen" heruntergeladen.

### 1.6 tinyMediaManager — Search & Scrape Dialog

tinyMediaManager (TMM) hat einen ähnlichen Workflow wie der, den wir bauen wollen:

1. Film auswählen → „Search & Scrape"
2. **Suchdialog**: Suchbegriff (vorbelegt), Trefferliste mit Postern
3. **Scrape-Dialog**: Checkboxen für jedes Metadata-Feld (was soll übernommen werden?)
4. **Artwork-Chooser**: Grid pro Typ, manuelle Auswahl

TMM's Stärke: **Completeness-Indikatoren** — grüne Haken für vollständige Metadata, fehlende Felder werden im Tooltip angezeigt.

**Übertragbares Muster:** Der **zistufige Ansatz** (erst Suche → Trefferliste, dann pro-Feld-Auswahl) und die Completeness-Anzeige.

### 1.7 Zusammenfassung: Was bauen wir?

| Vorbild | Muster für uns | Überdimensioniert |
|---|---|---|
| Emby | Identify-Suche → Trefferliste mit Postern | Batch-Refresh |
| Jellyfin | Tab-Gruppierung (Main/Details/Cast/Images) | Lock-per-Field |
| Stash | Side-by-Side-Vergleich „alt → neu" | Batch-Identify-Task |
| Picard | Farbcode für Match-Qualität | Drag-Drop-Track-Matching |
| Kodi | Artwork-Grid mit Auswahl/Abwahl pro Typ | Bulk-Downloader |
| TMM | Pro-Feld-Checkboxen, Completeness-Indikator | — |

**Empfehlung für den Assistenten:**
- **Schritt 1 (Quelle wählen):** Emby-Identify-Muster — Suchfeld, Trefferliste mit Poster+Titel+Jahr+Provider-Badge
- **Schritt 2 (Metadaten):** Stash/Picard-Side-by-Side mit Farbcode + TMM-Pro-Feld-Checkboxen + Jellyfin-Tab-Logik für FSK/Genre-Subsections
- **Schritt 3 (Artwork):** Kodi-Choose-Art-Grid mit Auswahl/Abwahl, gruppiert nach Typ (Poster / Fanart)
- **Schritt 4 (Bestätigung):** Zusammenfassung aller Änderungen mit Diff-Ansicht, „Übernehmen"-Button

---

## 2. Wizard-Muster im Web ohne Framework

### 2.1 Einfaches Pattern: CSS-Klassen umschalten

Das leichteste Muster für einen Schritt-Dialog in Vanilla JS:

```html
<div class="mw-modal" id="film-assistant">
  <div class="mw-modal__backdrop"></div>
  <div class="mw-modal__content">
    <!-- Fortschrittskopf -->
    <div class="wizard-header">
      <span class="wizard-step active" data-step="1">1. Quelle</span>
      <span class="wizard-step" data-step="2">2. Metadaten</span>
      <span class="wizard-step" data-step="3">3. Artwork</span>
      <span class="wizard-step" data-step="4">4. Bestätigen</span>
    </div>
    <!-- Schritt-Panels -->
    <div class="wizard-panel active" data-panel="1">…</div>
    <div class="wizard-panel" data-panel="2">…</div>
    <div class="wizard-panel" data-panel="3">…</div>
    <div class="wizard-panel" data-panel="4">…</div>
    <!-- Navigation -->
    <div class="wizard-footer">
      <button class="btn-prev">Zurück</button>
      <button class="btn-next">Weiter</button>
    </div>
  </div>
</div>
```

**CSS:**
```css
.wizard-panel { display: none; }
.wizard-panel.active { display: block; }
.wizard-step { opacity: 0.5; }
.wizard-step.active { opacity: 1; font-weight: bold; }
.wizard-step.completed { opacity: 0.8; }
```

**JS-Logik:** Ein einfaches State-Objekt hält den aktuellen Schritt und die gesammelten Daten:
```js
const wizard = {
  step: 1,
  data: { source: null, metadata: {}, artwork: {}, actions: {} },
  next() { this.step++; this.render(); },
  prev() { this.step--; this.render(); },
  render() { /* CSS-Klassen umschalten */ }
};
```

### 2.2 Bestehende Bibliotheken (framework-agnostic)

**SmartWizard** (`@smart-wizard/core`):
- TypeScript, zero Dependencies, framework-agnostic
- React- und Vue-Adapter verfügbar, aber **Vanilla-JS-Modus** funktioniert ohne Framework
- Themes: default, arrows, dots, progress
- Transition-Effekte: fade, slideHorizontal, slideVertical, css-custom
- Events: `sw:step-changed`, `sw:step-shown` — nützlich für Lazy-Loading von Artwork
- **Größe:** ~15 KB minified — akzeptabel für ein Vanilla-Projekt
- **Nachteil:** Eigene CSS-Klassen, die mit unserem Glasmorphismus-Design harmonieren müssen

**Empfehlung:** Für vier Schritte ist SmartWizard **Overkill**. Das CSS-Klassen-Pattern (Abschnitt 2.1) reicht völlig — kein externes Dependency, volle Kontrolle über das Design, und das bestehende `mw-modal`-Muster liefert bereits Backdrop, Close-Button und Fokus-Trap.

### 2.3 Fallstricke

| Problem | Beschreibung | Lösung |
|---|---|---|
| **Fokus-Management** | Beim Schrittwechsel muss der Fokus ins neue Panel (erstes Eingabefeld oder Heading). Sonst springt der Fokus beim Tabben ins unsichtbare Panel. | `panel.querySelector('input, button')?.focus()` nach jedem `render()`. |
| **Zurück-Navigation** | Nutzer klickt „Zurück" — sollen die Daten aus Schritt 2 noch da sein? | Ja: State-Objekt (Abschnitt 2.1) hält alle Daten. Panel-DOM wird nicht zerstört, nur `display: none`. |
| **Halbfertige Zustände** | Nutzer bricht bei Schritt 3 ab — was passiert mit den Daten aus Schritt 1+2? | **Zwei Optionen:** (a) „Abbrechen" verwirft alles (einfach, Modal wird geschlossen, kein State persistiert); (b) „Entwurf speichern" in `localStorage` (komfortabel, aber komplexer). Empfehlung für MVP: (a) — Entwerfe erst in einer späteren Ausbaustufe. |
| **Modal-Höhe** | Schritt 2 (Metadaten) hat viel mehr Felder als Schritt 4 (Bestätigung). Das Modal springt in der Höhe. | **Mindesthöhe** für das Modal festlegen (`min-height: 70vh`), oder alle Panels in einem Scroll-Container mit fester Höhe. |
| **Tastatur-Navigation** | Enter im Suchfeld sollte Suche auslösen, nicht „Weiter" zum nächsten Schritt. | `keydown`-Handler pro Panel; der globale „Weiter"-Button reagiert nur auf Klick, nicht auf Enter im Panel. |
| **ESC schließt Modal** | `mw-modal` fängt ESC zum Schließen ab. Im Wizard sollte ESC nur den aktuellen Schritt zurückgehen oder (bei Schritt 1) das Modal schließen. | Custom `keydown`-Handler im Wizard, der `event.stopPropagation()` aufruft, bevor das Modal-ESC greift. |

---

## 3. Nutzungsbedingungen Bildquellen

### 3.1 TMDb — API und Bilder

**Quellen:**
- API Terms of Use: https://www.themoviedb.org/documentation/api/terms-of-use (abgerufen 2026-11-06)
- Site Terms of Use: https://www.themoviedb.org/terms-of-use (abgerufen 2026-11-06)
- Logos & Attribution: https://www.themoviedb.org/about/logos-attribution (abgerufen 2026-11-06)
- API FAQ: https://developer.themoviedb.org/docs/faq (abgerufen 2026-11-06)

**(a) Anzeige in der eigenen Oberfläche:**

Die TMDb API Terms of Use (§1.A) erlauben die Nutzung für nicht-kommerzielle Zwecke mit Attribution. Die Site Terms of Use (§3.A) bestätigen: *„We grant You a non-exclusive license to use and copy the Materials and other users' Contributions solely for Your personal, non-commercial purposes."*

**Attribution ist Pflicht:**
1. **TMDb-Logo** muss in der App angezeigt werden (ein approved Logo aus der Logos-&-Attribution-Seite, z. B. das blaue SVG).
2. **Text-Hinweis** im About/Credits-Bereich: *„This product uses the TMDB API but is not endorsed or certified by TMDB."*
3. Der Hinweis muss „prominent" sein — also nicht in einem Unter-Menü versteckt.

**Cache-Limit:** API Terms §1.B: *„Cache, for longer than 6 months, any information obtained through or from TMDB or the TMDB APIs."* — Metadaten und Bild-URLs dürfen maximal 6 Monate zwischengespeichert werden.

**(b) Herunterladen und dauerhafte Speicherung im Medienarchiv:**

Hier wird es knifflig. Die Site Terms of Use (§3.B) enthalten ein explizites Verbot:

> *„You must not directly, or indirectly, copy, download, reproduce, duplicate, archive, scrape, distribute, upload, publish, modify, translate, broadcast, perform, display, sell, transfer, rent, sub-license, transmit or retransmit other users' Contributions or the Materials except as expressly permitted in Section 4.A for your personal, non-commercial purposes."*

Die Ausnahme in §4.A erlaubt die Nutzung für **persönliche, nicht-kommerzielle Zwecke**. Ein lokales Heimkino-Tool, das ein Poster herunterlädt und neben der Videodatei auf dem eigenen NAS speichert, fällt nach meiner Einschätzung unter diese Ausnahme — es ist rein privat, nicht öffentlich zugänglich, nicht kommerziell.

**Aber:** Die Bilder selbst sind urheberrechtlich geschützt (es sind Film-Poster von Studios). TMDb vermittelt nur die API-Zugänge zu den Bildern, die von Nutzern hochgeladen wurden. Die eigentliche urheberrechtliche Lage ist: Poster sind Marketing-Material der Filmstudios, das für Promotion geteilt wird — aber formal liegt das Urheberrecht bei den Studios.

**Risikoeinschätzung für unser Projekt:**
- TMDb-Bilder in der **Web-Oberfläche anzeigen** (Schritt 3): ✅ Klar erlaubt mit Attribution
- TMDb-Bilder **lokal auf NAS herunterladen** und neben Mediendateien ablegen: ⚠️ Grauzone — formal erlaubt unter §4.A (persönlich, nicht-kommerziell), aber die Terms sagen auch „archive" ist verboten. Die Ausnahme „except as permitted in 4.A" rettet uns vermutlich, da es unser eigenes NAS ist.
- **Kein Risiko** solange: (a) nicht-kommerziell, (b) nur eigenes NAS, (c) Attribution in der App, (d) keine Weitergabe der Bilder an Dritte

### 3.2 Fanart.tv — API und Bilder

**Quellen:**
- Terms & Conditions: https://fanart.tv/terms-and-conditions/ (abgerufen 2026-11-06)
- API-Dokumentation: https://api.fanart.tv/ (abgerufen 2026-11-06)
- API-Lizenzhinweis: „License: Creative Commons Attribution 3.0" (in der API-Doku, abgerufen 2026-11-06)

**(a) Anzeige in der eigenen Oberfläche:**

Die API-Dokumentation nennt als Lizenz **Creative Commons Attribution 3.0** (CC-BY-3.0). Das bedeutet: Anzeige ist erlaubt, sofern Fanart.tv als Quelle genannt wird.

Die Terms & Conditions sagen zusätzlich:
- *„All copyrights are retained by their respective owners"* — Fanart.tv beansprucht kein Urheberrecht an den Bildern.
- *„Most of the images on the site are PR / Promotional images, that the networks / studios / labels want shared as widely as possible"* — Fanart.tv argumentiert mit Fair Use und Promotion-Charakter.
- *„This site is about serving the community and any content you upload may be used in any way by us, or anyone, without any kind of attribution or royalty to you, the uploader."* — Das bezieht sich auf Uploads, nicht auf Downloads.

**Attribution:** CC-BY-3.0 verlangt Namensnennung. In der Praxis: Ein Hinweis „Artwork from fanart.tv" im About/Credits-Bereich.

**(b) Herunterladen und dauerhafte Speicherung:**

Die Terms & Conditions enthalten **kein explizites Download-Verbot** für Endnutzer. Im Gegenteil: Fanart.tv sieht sich als Dienst für Media-Center (Kodi, Emby, Jellyfin sind als Partner verlinkt). Die API liefert direkte Bild-URLs, und die Preview-URLs sind explizit für die Anzeige in UIs gedacht.

Die Terms sagen: *„please make sure you have the copyright owners permission before using an image in a way that may infringe on their copyright."* — Das schiebt die Verantwortung auf den Nutzer. Für Fanart-Bilder (Hintergrundbilder, Logos, Clearart) ist das Urheberrecht oft bei den Studios/Fotografen.

**Risikoeinschätzung:**
- Fanart.tv-Bilder in der **Web-Oberfläche anzeigen**: ✅ CC-BY-3.0 erlaubt mit Attribution
- **Herunterladen und lokal speichern**: ⚠️ Grauzone — Fanart.tv fördert die Nutzung in Media-Centern implizit, aber die Terms sagen nicht explizit „Download ist erlaubt". Das Fair-Use-Argument der Site (Promotion-Charakter) hilft.
- **CC-BY-3.0-Attribution** ist erfüllt durch „Artwork from fanart.tv" in der App

### 3.3 TVDB — API und Bilder

**Quellen:**
- Terms of Service: https://www.thetvdb.com/tos (abgerufen 2026-11-06)
- API Information: https://www.thetvdb.com/api-information (abgerufen 2026-11-06)
- GitHub README (Legal Usage): https://github.com/thetvdb/v4-api (abgerufen 2026-11-06)

**(a) Anzeige in der eigenen Oberfläche:**

Die TVDB Terms of Service (§2) sagen explizit:

> *„THE TERMS OF THE API LICENSE DO NOT GIVE YOU AUTHORIZATION TO USE OR DISPLAY IMAGES, TRAILERS OR PROGRAMMING ASSOCIATED WITH THE API; IF YOU CHOOSE TO USE IMAGES, TRAILERS OR PROGRAMMING, IT IS YOUR RESPONSIBILITY TO SECURE FROM AND PAY TO THE RELEVANT CONTENT OWNERS ANY AND ALL RIGHTS AND PAYMENTS YOU REQUIRE SPECIFIC TO YOUR PRODUCT."*

**Das ist ein klares Statement:** Die API-Lizenz erlaubt die Nutzung von **Metadata** (Text, IDs, Titel), aber **nicht** der Bilder. Wer TVDB-Bilder anzeigen will, muss die Rechte selbst klären.

**Attribution für Metadata:** TVDB verlangt: *„[Metadata provided by TheTVDB. Please consider adding missing information or subscribing.](https://thetvdb.com/subscribe)"* — mit direktem Link.

**(b) Herunterladen und dauerhafte Speicherung:**

Nach den TVDB-ToS ist das Herunterladen von Bildern **ohne separate Lizenzvereinbarung nicht gedeckt**. Die API liefert zwar Bild-URLs, aber die Lizenz zum Anzeigen/Speichern fehlt.

**Risikoeinschätzung:**
- TVDB-Metadaten (Text, IDs) nutzen: ✅ Erlaubt mit Attribution
- TVDB-Bilder in der **Web-Oberfläche anzeigen**: ❌ Nicht gedeckt durch die API-Lizenz
- TVDB-Bilder herunterladen und speichern: ❌ Nicht gedeckt

**Praktische Konsequenz:** Für TVDB-Bilder sollten wir **nicht als Quelle anbieten** — oder nur mit dem klaren Hinweis, dass die Rechtslage ungeklärt ist. Da TMDb und Fanart.tv für Bilder besser gedeckt sind, ist das kein echter Verlust.

### 3.4 Urheberrechtliche Einordnung: Poster und Cover

**Wichtig: Dies ist keine Rechtsberatung.** Die folgenden Punkte basieren auf Recherche, nicht auf juristischer Beratung. Alex sollte bei Unsicherheit einen Fachanwalt für Medienrecht fragen.

**Poster/Cover sind urheberrechtlich geschützt:**
- Film-Poster sind grafische Werke (§ 2 UrhG in Deutschland, 17 USC § 102 in den USA). Das Urheberrecht liegt beim Studio oder beim beauftragten Designer.
- Das Hochladen auf TMDb/Fanart.tv überträgt kein Urheberrecht an den Endnutzer.

**Argumente, die für die Nutzung sprechen:**
- Poster sind **Marketing-Material** — Studios wollen, dass sie geteilt werden (Promotion-Charakter).
- **Fair Use** (USA) / **Schrankenregelungen** (DE): Zitatrecht, Berichterstattung, private Kopie.
- TMDb und Fanart.tv stellen die Bilder **aktiv über APIs** bereit — sie wollen, dass Media-Center sie nutzen.

**Argumente, die dagegen sprechen:**
- Formale Rechtslage: Ohne explizite Lizenz des Urhebers ist jede Vervielfältigung grundsätzlich rechtswidrig.
- „Private Kopie" (DE § 53 UrhG) erlaubt das Kopieren für den persönlichen Gebrauch — das könnte das Speichern auf dem eigenen NAS decken, aber die Rechtsprechung ist hier nicht eindeutig für Bilder aus APIs.

**Praktisches Fazit für unser Projekt:**
- **Anzeige in der Web-Oberfläche** (temporär, aus der API geladen): Minimales Risiko, weil TMDb/Fanart.tv das aktiv fördern und Attribution leisten.
- **Dauerhaftes Speichern auf NAS** (Poster neben der Videodatei): Grauzone — formal nicht explizit erlaubt, aber durch Fair-Use/Promotion-Charakter/private-Kopie-Argument vertretbar. **Kein kommerzielles Risiko**, da rein privat.
- **Empfehlung:** TMDb als primäre Bildquelle nutzen (klarste Terms), Fanart.tv als Ergänzung. TVDB-Bilder vermeiden. Attribution in der App einbauen.

---

## 4. Hinweis zur Methodik

Webzugriff war verfügbar. Alle in Abschnitt 3 zitierten Quellen wurden am **2026-11-06** live abgerufen und verifiziert. Die Zitate stammen aus den Original-Texten der Terms of Use. Dennoch gilt: **Keine Rechtsberatung.** Alle Einschätzungen sind Recherche-Ergebnisse, keine juristischen Gutachten. Vor einer Implementierung mit Download-Funktionalität sollte Alex die Terms der genutzten Quellen selbst noch einmal lesen und bei Bedenken rechtlichen Rat einholen.

---

## 5. Optionen-Tabelle: Bildquellen-Kombinationen

| Option | Quellen | Pro | Contra | Risiko |
|---|---|---|---|---|
| **A: Nur TMDb** | Poster + Fanart aus TMDb | Einfachste Integration; klarste Terms (CC-BY-ähnlich für nicht-kommerziell); ein API-Key reicht; Attribution einmalig | Weniger Auswahl bei Nischen-Filmen; keine transparenten Logos (Clearart); Fanart-Qualität variabel | 🟢 Niedrig — TMDb Terms decken nicht-kommerzielle Nutzung mit Attribution ab |
| **B: TMDb + Fanart.tv** *(Empfehlung)* | Poster von TMDb, Logos/Backgrounds/Disc-Art von Fanart.tv | Beste Abdeckung: TMDb hat Poster in vielen Sprachen, Fanart.tv hat HD-Logos (PNG transparent), Clearart, Disc; beide APIs sind etabliert; zwei API-Keys | Zwei Attribution-Hinweise nötig; Fanart.tv-CC-BY-3.0 erfordert Nennung; etwas mehr Code für zwei Quellen | 🟡 Niedrig bis Mittel — Fanart.tv Terms sind weniger explizit als TMDb, aber CC-BY-3.0 und Promotion-Charakter sprechen dafür |
| **C: TMDb + Fanart.tv + OFDb-Cover** | Wie B, plus OFDb-Poster als Fallback für deutsche Cover | Deutsche Cover sind oft besser als TMDb (OFDb hat deutsche Kinoplakate); für Alex' Heimkino relevant | OFDb hat keine offizielle API; Scraping wäre nötig (rechtlich problematisch); zusätzliche Komplexität | 🔴 Mittel bis Hoch — Scraping ohne API ist rechtlich grau; OFDb-Nutzungsbedingungen prüfen |
| **D: Manuell (Upload)** | Nutzer lädt eigene Bilder hoch | Volle Kontrolle; keine Rechtsfragen (eigene Bilder oder gekaufte Lizenzen); kein API-Dependency | Hoher Aufwand für Alex; kein Automatisierungsgewinn; braucht Datei-Upload-UI | 🟢 Kein Quellen-Risiko — aber unpraktisch für den Alltag |

### Empfehlung

**Option B (TMDb + Fanart.tv)** ist die beste Balance aus Abdeckung, rechtlicher Vertretbarkeit und Aufwand:

- **TMDb** liefert Poster (auch in DE) und Backdrops — die Basis.
- **Fanart.tv** liefert die „schönen" Assets: HD-Logos (transparent), Clearart, Disc-Art, zusätzliche Fanarts — genau das, was ein Heimkino-Betrieb „gut aussehen" lässt.
- Beide APIs sind etabliert, haben freie Keys, CORS-Header für direktes Frontend-Fetching, und sind auf nicht-kommerzielle Nutzung ausgelegt.
- **Attribution** in der App: TMDb-Logo + „This product uses the TMDB API but is not endorsed or certified by TMDB." und „Artwork from fanart.tv (CC-BY-3.0)".
- **TVDB-Bilder** bewusst **nicht** als Quelle anbieten — die ToS verbieten die Bildnutzung ohne separate Lizenz.

**Offene Entscheidungen (Alex-Freigabepunkt):**
1. **Rechtsfreigabe Bild-Download:** Soll der Assistent Bilder dauerhaft auf dem NAS speichern dürfen? (Grauzone — Alex entscheidet nach eigener Risikobewertung.)
2. **Fanart.tv-Integration:** Ja/Nein? (Empfehlung: Ja, für die HD-Logos und Clearart.)
3. **OFDb-Option:** Später als optionale Erweiterung? (Empfehlung: Erstmal zurückstellen, bis eine offizielle API verfügbar ist.)

---

## 6. Quellen

| Quelle | URL | Abruf |
|---|---|---|
| TMDb API Terms of Use | https://www.themoviedb.org/documentation/api/terms-of-use | 2026-11-06 |
| TMDb Site Terms of Use | https://www.themoviedb.org/terms-of-use | 2026-11-06 |
| TMDb Logos & Attribution | https://www.themoviedb.org/about/logos-attribution | 2026-11-06 |
| TMDb API FAQ | https://developer.themoviedb.org/docs/faq | 2026-11-06 |
| Fanart.tv Terms & Conditions | https://fanart.tv/terms-and-conditions/ | 2026-11-06 |
| Fanart.tv API v3.2 Dokumentation | https://api.fanart.tv/ | 2026-11-06 |
| TheTVDB Terms of Service | https://www.thetvdb.com/tos | 2026-11-06 |
| TheTVDB API Information | https://www.thetvdb.com/api-information | 2026-11-06 |
| TheTVDB v4 API GitHub (Legal Usage) | https://github.com/thetvdb/v4-api | 2026-11-06 |
| Emby Learn: Media Artwork Roles | https://emby.media/learn/articles/metadata-discovery/artwork/Metadata-Artwork-Roles.html | 2026-11-06 |
| Emby Documentation: Metadata manager | https://emby.media/support/articles/Metadata-manager.html | 2026-11-06 |
| Jellyfin Vue Discussion #130 (Metadata Editor) | https://github.com/jellyfin/jellyfin-vue/discussions/130 | 2026-11-06 |
| Stash Docs: Metadata Scraping | https://docs.stashapp.cc/in-app-manual/scraping | 2026-11-06 |
| Stash Docs: Scene Tagger | https://docs.stashapp.cc/in-app-manual/tagger | 2026-11-06 |
| MusicBrainz Picard Quick Start | https://picard.musicbrainz.org/quick-start/ | 2026-11-06 |
| Kodi Wiki: Artwork/Changing | https://kodi.wiki/view/Artwork/Changing | 2026-11-06 |
| Kodi Wiki: Add-on Artwork Downloader | https://kodi.wiki/view/Add-on:Artwork_Downloader | 2026-11-06 |
| tinyMediaManager: Movie Panel | https://www.tinymediamanager.org/docs/movies/moviepanel | 2026-11-06 |
| tinyMediaManager: Quickstart | https://www.tinymediamanager.org/docs/quickstart | 2026-11-06 |
| SmartWizard (@smart-wizard/core) | https://github.com/nicjansma/smart-wizard (via NPM: @smart-wizard/core) | 2026-11-06 |
| CSS-Tricks: Multi-Step Forms Vanilla JS | https://css-tricks.com/how-to-create-multi-step-forms-with-vanilla-javascript-and-css | 2026-11-06 |
| cinedigest: TMDb Image Use (Terms-Zusammenfassung) | https://github.com/vasyapym/cinedigest/blob/main/docs/tmdb-image-use.md | 2026-11-06 |
