import test from 'node:test';
import assert from 'node:assert';
import { cleanSeriesName } from '../../gui/static/js/utils.js';

test('cleanSeriesName - Leereingaben', () => {
    assert.strictEqual(cleanSeriesName(""), "");
    assert.strictEqual(cleanSeriesName(null), "");
    assert.strictEqual(cleanSeriesName(undefined), "");
});

test('cleanSeriesName - Unterstriche ersetzen', () => {
    assert.strictEqual(cleanSeriesName("Mein_Lieblingsfilm"), "Mein Lieblingsfilm");
    assert.strictEqual(cleanSeriesName("Eine_sehr_lange_Serie_mit_vielen_Worten"), "Eine sehr lange Serie mit vielen Worten");
});

test('cleanSeriesName - Mediathek- und URL-Sonderklammern entfernen', () => {
    assert.strictEqual(cleanSeriesName("Serie (Mediathek Serie aus URL)"), "Serie");
    assert.strictEqual(cleanSeriesName("Film (Mediathek Film aus URL)"), "Film");
    assert.strictEqual(cleanSeriesName("Dokumentation (Freie Mediathek-Suche)"), "Dokumentation");
    assert.strictEqual(cleanSeriesName("Show (fernsehserien.de URL)"), "Show");
    assert.strictEqual(cleanSeriesName("Nachrichten (3 Videos via URL)"), "Nachrichten");
    assert.strictEqual(cleanSeriesName("Konzert (Videos via URL)"), "Konzert");
});

test('cleanSeriesName - Kanal-Tags / Bracket-Tags am Ende entfernen (wiederholt)', () => {
    assert.strictEqual(cleanSeriesName("Serie [ARTE]"), "Serie");
    assert.strictEqual(cleanSeriesName("Serie [ARTE.DE]"), "Serie");
    assert.strictEqual(cleanSeriesName("Serie [TMDB_TV]"), "Serie");
    assert.strictEqual(cleanSeriesName("Serie [US]"), "Serie");
    assert.strictEqual(cleanSeriesName("Serie [ARTE][US]"), "Serie");
    assert.strictEqual(cleanSeriesName("Serie [ARTE][US][TMDB_TV]"), "Serie");
});

test('cleanSeriesName - Kombination und Trimming', () => {
    assert.strictEqual(cleanSeriesName("  Film_Name [TMDB_TV]  "), "Film Name");
    assert.strictEqual(cleanSeriesName("  Mein_Lieblingsfilm (Mediathek Serie aus URL) [ARTE][DE]  "), "Mein Lieblingsfilm");
});
