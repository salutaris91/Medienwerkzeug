# Zusammenfassung für Alex: Inbox-Banner zeigt alle Serien-Vorschläge, „Ignorieren" lässt sich rückgängig machen

## Was wird gemacht?
Der Vorschlags-Banner über der Inbox zeigt künftig alle erkannten Serien-Gruppen auf einmal (der wichtigste oben, die übrigen in einer ausklappbaren Liste). Was du mit „Ignorieren" ausblendest, verschwindet nicht mehr für immer: ein Bereich „Ausgeblendete Vorschläge" hält sie fest, und du kannst einzelne oder alle wieder zurückholen — auch nach dem Neu Laden der Seite. Alle Knopf- und Listentexte sind jetzt in einer verbindlichen Tabelle im technischen Briefing mit exakten Umlauten festgeschrieben, damit nichts falsch abschreibt.

## Warum?
Genau das war dein Wunsch aus dem Handtest: alle „Zusammenziehvorschläge" sehen, und eine Serie, die du „erstmal raushaben" willst weil noch Folgen fehlen, später zurückholen können. Mitgenommen wird zusätzlich nur die Banner-Fehlerstelle aus #80: wenn der Start aus dem Banner wegen eines internen Fehlers nicht durchläuft, siehst du künftig eine Meldung statt „nichts passiert".

## Risiken in Klartext
- **Nur Oberfläche, kein Datenrisiko:** Es ändert sich nichts an Dateien auf der Festplatte, am Server oder an deinen Medien. Der „merkt sich, was du ausgeblendet hast"-Zustand liegt nur im Browser deines Geräts.
- **Falsch gesetzter Knopf drückt dich nicht aus der Bahn:** Ein kaputter Button im neuen Menü könnte theoretisch einen Start verhindern; dafür gibt es einen speziellen Test, der genau diese „Sonderzeichen im Seriennamen"-Fälle abfängt (die war in #77 tatsächlich aufgetreten).
- **Die Banner-Fehlermeldung greift nur bei internen Fehlern (Korrektur F1):** Netzwerk- oder Backend-Probleme der Suche zeigt sie gerade nicht — die meldet die Suche wie bisher „Suchfehler" unten im Suchbereich, und die Gruppe bleibt als angewendet stehen. Das ist unverändertes Altverhalten und als späterer Prüfungspunkt notiert. Weil du diese Banner-Meldung im normalen Betrieb nicht selbst auslösen kannst, ist sie aus deinem Handtest herausgenommen: Claude Code weist sie mit einer nur lokal gepatchten Kopie nach (Foto + Protokoll für dich), die nicht in den Code eingezogen wird.
- **Automatisch zurückholen gibt es noch nicht:** Wie von dir entschieden (Q1 = C), holst du ausgeblendete Vorschläge nur per Klick zurück. „Neue Folge da → Vorschlag taucht wieder auf" wird ein eigener späterer Punkt in der Roadmap (Eintrag schreibt Claude Code).
- **Stichproben-pflichtige Themen:** Keine — es geht um kein Geld, keine Registrierung, keine Rechtstexte und keine Kaufentscheidung.
- **Deine beiden Sonderpunkte sind angenommen** (wörtlich, 2026-10-17: „Ja, Akt 2b mit F1–F3 wie empfohlen starten; Apply-Sperre und Bestandstest-Anpassung nehme ich an."): 1. *Doppelstart-Sperre* — mehrere „Als Serie gruppieren"-Knöpfe können nicht parallel starten. 2. *Ein alter Test wird angepasst* — an genau benannter Stelle auf das neue Verhalten umgeschrieben, gleichwertig geprüft, nicht abgeschwächt.

## Offene Fragen an dich
1. Nur noch Freigabepunkt 2 auf das überarbeitete technische Briefing. Nach deiner Freigabe läuft die Kette: Ausgangsmessung → ein KI-Ausführungslauf → Rückkanal → dein Handtest (~15 min mit vorbereiteten Testdaten; ohne Fehlerfall-Schritt, siehe oben) → Push/PR → dein Merge.
2. Rohoutputs der Berater (Runde 1) liegen ungekürzt im Session-Ordner: `docs/sessions/2026-10-16-roadmap75-inbox-vorschlaege/`.

## Deine Entscheidung
- [ ] Freigabe — weiter zur Ausführung
- [ ] Rückfragen — Session geht in eine weitere Runde
