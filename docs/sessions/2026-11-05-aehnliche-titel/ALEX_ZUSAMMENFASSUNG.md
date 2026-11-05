# Zusammenfassung für Alex — „Ähnliche Titel"-Hinweis (max. 1 Bildschirmseite)

## Was soll gebaut werden?
Kurz bevor du im Medienwerkzeug auf „Jetzt final verarbeiten" klickst, zeigt das Vorschau-Fenster künftig eine **Warnbox** (nur bei Filmen, nur auf dem NAS-Ziel, **blockiert nichts**):

1. **„Diesen Film hast du schon auf dem NAS"** — sicherer Treffer über die Film-ID (z. B. derselbe X-Men-Film unter anderem Ordnernamen).
2. **„Ähnliche Titel – gehören evtl. dazu"** — bewusste, großzügige Namenssuche nach deinem FP1-Wunsch („lieber mehr Fehlalarme als verpasste Treffer"); max. 10 Treffer, 5 sichtbar, Rest einklappt.

Dazu im selben Rutsch: Behebung eines **alten Anzeigefehlers** (Ordnernamen vom NAS werden heute an einer Stelle ungeschützt ins Browserfenster geschrieben — das könnte ein fremder Ordnername ausnutzen), sowie der übliche Cache-Buster. Aufgeteilt in 2 Arbeitsetappen (Backend, dann Frontend), jeweils klar abgegrenzte Dateien und Abbruchregeln.

## Warum?
Heute warnt das Tool nur, wenn der Zielordner **exakt gleich** heißt. „X-Men - Der Film" neben „X-Men (2000)" bleibt unbemerkt → Doppelt-Bestand. Die ID-Steckt schon überall (Download-Information und Film-Beschreibungsdateien), deshalb ist der sichere Teil praktisch geschenkt.

## Risiken in Klartext
- **Fehlalarme bei Stufe 2 sind gewollt** (deine Entscheidung) — die Box ist bewusst als „evtl." beschriftet; ein „sicher"-Label bekommt nur der ID-Treffer.
- **Hängendes NAS:** Ist das Laufwerk im Eimer, kann die Vorschau langsamer werden oder stehen. Verkleinert (nur Zielordner, 2 Ebenen), aber nicht beseitigt — steht als bekanntes Risiko auf der Roadmap.
- **Altbestand ohne ID** wird nur von der Namenssuche gefangen, nie von der sicheren Stufe.
- Dokumentationen/Anime/YouTube-Läufe bekommen **bewusst keinen** Hinweis (Nicht-Ziel, notiert).

## Geprüfte Abweichungen zur Planungs-Runde (korrigiert im Briefing)
Der ungeschützte Anzeigefehler betrifft **beide** angezeigten Namen, nicht nur einen; ein weiterer Anbieter („ofdb") muss beim ID-Vergleich übersprungen werden (fremde ID-Welt = falsche Treffer); Film-Beschreibungsdateien heißen auf dem NAS unterschiedlich — die Suche folgt dem bewährten Mechanismus aus dem Gesundheits-Check.

## Offene Entscheidungen beim finalen Planreview
1. **Freigabe des technischen Briefings** (Status draft → approved) — Basis: `docs/sessions/2026-11-05-aehnliche-titel/briefing.md`.
2. Wortlisten der Namenssuche (allgemeine Wörter wie „man/love/night", Release-Markierungen) sind **bewusst klein und änderbar** gestartet — OK so, oder willst du vorab andere Beispiele? dazu eine bewusste Grenzentscheidung: reine Zahlentitel wie „300" oder „1917" gelten als bedeutungsvoll und können sich gegenseitig finden (echter Duplikat-Fall) — OK so?
3. Hinweis, kein Widerspruch: Die Planungs-Runde war sich gegen Namens-Fuzzy einig; dein FP1-Vot hat dagegen entschieden — der Dissens ist im Briefing Abschnitt 10 dokumentiert.

## Stichproben-pflichtige Themen
Keine Geld-/Kaufentscheidungen. Außenwirkung/Registrierung betrifft nur die **V2-Idee „Filmreihen anzeigen"** (TMDb-Zugang, Nutzungsbedingungen ungeprüft) — vor jeder Umsetzung zu bewilligen. Rohoutputs der Planungs-Runde (ungekürzt): `docs/sessions/2026-11-05-aehnliche-titel/` (`scout.md`, `advocatus.md`, `produktberater.md`, `synthese.md`).

## Freigabefrage an dich
**Empfehlung:** Briefing freigeben und Umsetzung in Etappe E1 (Backend) starten — der sicherste, kleinste Teil zuerst; Engpass bleibt dein Review der Suchwort-Listen, nicht die Code-Menge.
**Alex, gibst du dieses Briefing frei (FP2: „Freigabe: Ja"), oder willst du vorher etwas ändern?**
