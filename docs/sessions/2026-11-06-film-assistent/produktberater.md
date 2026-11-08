# Produktberatung: Film-Assistent (#92) — Scope und Nutzen

**Rolle:** Produktberater (Scope-Wächter) im Kreativteam · 2026-11-06

> Archivierungsvermerk (Orchestrator, 2026-11-06): Beitrag unverändert übernommen; der Kopfblock „Rolle" wurde nur um das Datum der Sitzung ergänzt (stammte sinngemäß aus dem Beitrag).

## 1. Alltagsnutzen der vier Schritte

**Schritt 2 (Metadaten bearbeiten) bringt den schnellsten spürbaren Gewinn.** Hier liegt der aktuelle Schmerz: Alex muss nach dem Import manuell FSK, Genres, Episoden-Mappings und andere Felder nachtragen, oft in langen Scroll-Ansichten. Ein fokussierter Editor, der diese Felder strukturiert anbietet und direkt speichert, spart pro Film 2-5 Minuten manueller Arbeit. Bei typischerweise 3-10 Filmen pro Woche (Heimkino-Nutzung) sind das 30-50 Minuten/Woche.

**Schritt 1 (Quelle wählen) ist notwendig, aber allein kein Mehrwert.** Die Quelle zu wählen ist eine Voraussetzung, kein Nutzen an sich. Der Nutzen entsteht erst, wenn die gewählte Quelle gute Metadaten liefert — und die müssen dann in Schritt 2 bearbeitbar sein.

**Schritt 3 (Artwork wählen) ist "schön für Emby-Gefühl", aber verzichtbar für den Arbeitsfluss.** Artwork verbessert die Präsentation in Emby, aber ein fehlendes oder falsches Poster blockiert den Import nicht. Alex kann auch nachträglich Artwork manuell setzen. Der Nutzen ist ästhetisch, nicht funktional.

**Schritt 4 (Ergebnis + Datei-Aktionen) ist Konsolidierung, kein neuer Nutzen.** Die Datei-Aktionen (Umbenennen, Verschieben, NFO schreiben) laufen bereits heute — sie nur an einem Ort zu bündeln ist aufgeräumt, aber nicht kritisch.

**#91 (Ähnliche Titel-Hinweis) hat bereits live seit 2026-11-05 hohen Sofortnutzen**, weil es versehentliche Duplikate verhindert. Das ist kein Schritt im Assistenten, sondern eine Sicherheitsnetz-Funktion.

## 2. MVP-Definition: Kleinere erste Ausbaustufe

**Der 4-Schritte-Assistent ist kein MVP, sondern das Zielbild.** Eine kleinere erste Ausbaustufe, die den Alltag schon verbessert:

**MVP = Schritt 1 (Quelle wählen) + Schritt 2 reduziert auf "Bearbeiten" (nicht "Vergleichen").**

Der Unterschied ist wichtig:
- **Bearbeiten** = Ein Provider (z. B. TMDb), aber alle Felder manuell korrigierbar. Das ist der aktuelle Schmerzpunkt.
- **Vergleichen** = Mehrere Provider nebeneinander zeigen, manuell den besten auswählen. Das ist aufwändig (UI für Side-by-Side, Konfliktlösung, Provider-Badges) und bringt marginalen Zusatznutzen, weil Alex meist eh einen Standard-Provider bevorzugt.

**Was raus darf/bleiben kann:**
- Schritt 2 "Vergleich" als MVP-Anforderung → verschieben auf Etappe 2
- Schritt 3 "Artwork-Galerie mit mehreren Quellen" → erst mal ein Artwork pro Film (Default vom Provider), Rest später
- Schritt 4 "Ergebnis-Vorschau vor Ausführung" → kann entfallen, wenn die Aktionen ohnehin nur einen Ordner betreffen und leicht reversibel sind

## 3. Reihenfolge der Etappen

**Der Kickoff-Schnitt ist sinnvoll, aber ich würde Etappe 1 in zwei Teile zerlegen:**

**Etappe 1a: Schrittrahmen + Import-Pfad (Grundstruktur)**
- Wizard-Gerüst mit 2 Schritten (Quelle wählen + Metadaten bearbeiten)
- Inbox → "Film verarbeiten" öffnet Wizard
- NFO-Agent bleibt vorerst unverändert für Bestandsordner
- **Nutzen:** Alex hat einen klaren Import-Flow, aber noch keinen Editor

**Etappe 1b: NFO-Agent andocken (Metadaten-Editor)**
- Schritt 2 bekommt den Editor (FSK, Genre, Episoden-Mapping, Felder korrigierbar)
- NFO-Agent kann parallel weiterlaufen für Health-Checks
- **Nutzen:** Sofortige Verbesserung des Alltags, manuelle Nacharbeit entfällt

**Etappe 2: Provider-Vergleich (#55)**
- Side-by-Side-Ansicht TMDb vs. OFDb vs. IMDB
- Provider-Badges, Konfliktlösung
- **Nutzen:** Bessere Metadaten-Qualität, aber nicht kritisch

**Etappe 3: Artwork (#51)**
- **Erst nach Rechtsklärung** (welche Quellen sind rechtssicher?)
- Default: Ein Artwork vom Provider, manuell austauschbar
- **Nutzen:** Ästhetisch, nicht funktional

**Etappe 4: Reihen-Schleife (#69)**
- Vorab-Queue statt Schleife im Dialog (siehe Punkt 4)
- **Nutzen:** Kommt auf die Häufigkeit an (siehe Punkt 4)

**Alternative "erst Vergleich ohne Wizard" wäre falsch**, weil der Vergleich den Rahmen braucht — wo soll die Side-by-Side-Ansicht sonst leben? **Alternative "erst Artwork" wäre falsch**, weil Artwork ohne Metadaten sinnlos ist (ein Poster ohne korrekte Metadaten nützt nichts).

## 4. Einzelfilm vs. Reihe (#69)

**Reihen-Import ist wahrscheinlich seltener als Einzelfilm-Import.** Alex schaut als Heimkino-Nutzer eher Filme als Serien (typisches Nutzungsmuster). Wenn Reihen-Import nur 1-2x pro Monat vorkommt, ist #69 niedrigere Priorität.

**MVP-taugliche Vereinfachung: Vorab-Queue statt Schleife im Dialog.**

- **Vorab-Queue:** Alex wählt in der Inbox mehrere Einträge einer Reihe aus, startet den Assistenten einmal, und die Queue wird Film für Film abgearbeitet. Vorteil: Übersicht (wie viele Filme noch?), Abbruch möglich ohne Fortschritt zu verlieren, kein "Hin und Her" im Dialog.
- **Schleife im Dialog:** Nach jedem Film zurück zu Schritt 1, neuer Film auswählen. Nachteil: Unklar wie viele Filme noch, Abbruch verwirrend, Fortschritt nicht sichtbar.

**Empfehlung:** Erst Einzelfilm perfektionieren (Etappe 1a+1b), dann Vorab-Queue für Reihen (Etappe 4). Schleife im Dialog nicht bauen.

## 5. Zusammenspiel NFO-Agent und Inbox

**Inbox bekommt den Assistenten zuerst.** Der natürliche Flow ist: Neuer Film landet in Inbox → Alex wählt aus → "Film verarbeiten" → Assistent. Das ist der häufigste Pfad.

**NFO-Agent bleibt vorübergehend parallel laufen.** Der NFO-Agent hat zwei Funktionen:
1. Health-Einstieg: Bestandsordner nachpflegen (Metadaten nachträglich korrigieren)
2. Filmverarbeitung: Kann auch einzelne Filme bearbeiten

Für Funktion 1 (Health) braucht Alex den NFO-Agenten weiterhin, bis alle Bestandsordner gepflegt sind. Das kann Wochen dauern. **Big-Bang vermeiden:** NFO-Agent und Assistent laufen parallel, bis Alex entscheidet, dass der NFO-Agent obsolet ist (weil alle Bestandsordner gepflegt sind oder der Assistent auch Health-Checks übernimmt).

**Migrationspfad:** Wenn der Assistent stabil läuft, kann der NFO-Agent schrittweise Funktionen abgeben (z. B. erst "Einzel-Film bearbeiten", dann "Health-Check"). Kein Zwang zur sofortigen Ablösung.

## 6. Zeit-Schätzung (getrennt)

**KI-Umsetzung (schnell):**
- Etappe 1a (Rahmen + Import-Pfad): 2-3 Tage
- Etappe 1b (Metadaten-Editor): 2-3 Tage
- Etappe 2 (Provider-Vergleich): 1-2 Tage
- Etappe 3 (Artwork): 1 Tag (nach Rechtsklärung)
- Etappe 4 (Reihen-Queue): 1-2 Tage
- **Summe KI: 7-11 Tage** (bei voller Fokus, unrealistisch)

**Alex-Engpass (langsam, kritisch):**
- Review + Handtest auf NAS: Pro Etappe 3-5 Tage (Alex muss testen, Feedback geben, KI iteriert)
- Freigaben: Pro Etappe 1-2 Tage Wartezeit (Alex hat andere Verpflichtungen)
- Rechtsklärung Bildquellen (Etappe 3): 1-3 Wochen (externe Abhängigkeit, nicht steuerbar)
- **Summe Alex: 6-10 Wochen** (bei paralleler Arbeit, realistisch)

**Gesamt: 7-12 Wochen bis Etappe 4 produktiv läuft.** Engpass ist Alex (Review, Test, Freigaben), nicht die KI-Umsetzung. **Konsequenz:** Etappen so schneiden, dass Alex zwischendurch nutzbare Inkremente bekommt (nicht 3 Monate warten bis erster Nutzen).

## 7. Streichungsliste

**Was ich aus dem Plan kippen würde:**

1. **Schritt 2 "Vergleich" als MVP-Anforderung** → Bearbeiten reicht für MVP. Vergleich ist aufwändig (Side-by-Side-UI, Konfliktlösung, Provider-Badges) und bringt marginalen Zusatznutzen. Alex bevorzugt meist eh einen Standard-Provider. Vergleich kann später als "Nice-to-have" kommen.

2. **Artwork-Galerie mit mehreren Quellen (MVP)** → Erst mal ein Artwork pro Film (Default vom Provider), manuell austauschbar. Galerie mit TMDb + OFDb + Fanart.tv ist aufwändig und rechtlich unklar. Nach Rechtsklärung kann eine einfache Galerie kommen.

3. **Schleife im Dialog für Reihen (#69)** → Vorab-Queue ist übersichtlicher, abbruchfreundlich und einfacher zu testen. Schleife im Dialog ist verwirrend (wie viele Filme noch?) und fehleranfällig (Abbruch verliert Fortschritt).

4. **NFO-Agent sofort umbauen (Big-Bang)** → Paralleler Betrieb ist sicherer. Alex kann den Assistenten für neue Filme nutzen, den NFO-Agenten für Bestandsordner. Migration schrittweise, wenn der Assistent stabil ist.

5. **Schritt 4 "Ergebnis-Vorschau vor Ausführung" als Pflicht** → Kann entfallen, wenn die Aktionen (Umbenennen, Verschieben, NFO schreiben) nur einen Ordner betreffen und leicht reversibel sind. Vorschau ist "nice-to-have", nicht kritisch.

---

## Empfehlung

**Starte mit Etappe 1a+1b (Schrittrahmen + Metadaten-Editor) als MVP.** Das bringt sofortigen Alltagsnutzen (manuelle Nacharbeit entfällt), ist in 4-6 Tagen KI-Umsetzung + 2-3 Wochen Alex-Engpass fertig, und liefert ein nutzbares Inkrement. Vergleich, Artwork und Reihen sind Erweiterungen, die später kommen können — aber erst, wenn der Editor stabil läuft. NFO-Agent bleibt parallel für Bestandsordner, kein Big-Bang. #91 (Ähnliche Titel) ist bereits live und muss nicht Teil des Assistenten sein.

## Die 3 wichtigsten offenen Entscheidungen für Alex

1. **Wie häufig importiert Alex Reihen vs. Einzelfilme?** Wenn Reihen-Import nur 1-2x pro Monat vorkommt, ist #69 niedrigere Priorität und kann nach Etappe 2 (Vergleich) kommen. Wenn Reihen-Import häufig ist (z. B. wöchentlich), muss #69 früher kommen.

2. **Rechtsklärung Artwork: Welche Quellen sind rechtssicher?** TMDb, OFDb, Fanart.tv haben unterschiedliche Lizenzen. Bevor Etappe 3 (Artwork) startet, muss geklärt sein, welche Quellen genutzt werden dürfen. Das kann 1-3 Wochen dauern und blockiert Etappe 3.

3. **MVP-Definition: Reicht Schritt 1+2 reduziert auf "Bearbeiten" (nicht "Vergleichen") als erste Ausbaustufe?** Wenn ja, kann Etappe 1a+1b sofort starten. Wenn Alex den Vergleich von Anfang an will, verschiebt sich der Nutzen um 1-2 Wochen (Etappe 2 muss vorziehen).
