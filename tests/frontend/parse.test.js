import test from 'node:test';
import assert from 'node:assert';
import { guessSeasonAndEpisode, guessEpisodeNumber, cleanFilenameForManualTitle } from '../../gui/static/js/parse.js';

test('guessSeasonAndEpisode - S01E02-Format', () => {
    assert.strictEqual(guessSeasonAndEpisode("S01E02"), "S01E02");
    assert.strictEqual(guessSeasonAndEpisode("s01e02"), "S01E02");
    assert.strictEqual(guessSeasonAndEpisode("S1E2"), "S01E02");
    assert.strictEqual(guessSeasonAndEpisode("s1e2"), "S01E02");
});

test('guessSeasonAndEpisode - 1x05-Format', () => {
    assert.strictEqual(guessSeasonAndEpisode("1x05"), "S01E05");
    assert.strictEqual(guessSeasonAndEpisode("01x05"), "S01E05");
    assert.strictEqual(guessSeasonAndEpisode("1x5"), "S01E05");
});

test('guessSeasonAndEpisode - Deutsche Formate', () => {
    assert.strictEqual(guessSeasonAndEpisode("Staffel 2 Folge 3"), "S02E03");
    assert.strictEqual(guessSeasonAndEpisode("St 2 Ep 3"), "S02E03");
    assert.strictEqual(guessSeasonAndEpisode("s2 f3"), "S02E03");
    assert.strictEqual(guessSeasonAndEpisode("staffel 10 episode 12"), "S10E12");
});

test('guessSeasonAndEpisode - Kein Treffer', () => {
    assert.strictEqual(guessSeasonAndEpisode("irgendein_film.mkv"), null);
    assert.strictEqual(guessSeasonAndEpisode(""), null);
});

test('guessEpisodeNumber - Erkennung aus verschiedenen Formaten', () => {
    assert.strictEqual(guessEpisodeNumber("S01E05"), 5);
    assert.strictEqual(guessEpisodeNumber("1x05"), 5);
    assert.strictEqual(guessEpisodeNumber("ep 05"), 5);
    assert.strictEqual(guessEpisodeNumber("episode 5"), 5);
    assert.strictEqual(guessEpisodeNumber("Episode.12.mkv"), 12);
});

test('guessEpisodeNumber - Grenzwerte im Ziffern-Fallback-Pfad', () => {
    // Falls kein s/x/ep Muster matcht, greift der Ziffern-Fallback
    // Dieser prüft: val > 0 && val < 200
    assert.strictEqual(guessEpisodeNumber("Show 199.mkv"), 199);
    assert.strictEqual(guessEpisodeNumber("Show 200.mkv"), null);
    assert.strictEqual(guessEpisodeNumber("Show 0.mkv"), null);
});

test('cleanFilenameForManualTitle - Bereinigungen', () => {
    assert.strictEqual(cleanFilenameForManualTitle("titel.mkv"), "titel");
    assert.strictEqual(cleanFilenameForManualTitle("titel.s01e02"), "titel");
    assert.strictEqual(cleanFilenameForManualTitle("Mein.Lieblings-Film_Name.mkv"), "Mein Lieblings Film Name");
    assert.strictEqual(cleanFilenameForManualTitle("  tote   hose  "), "tote hose");
});

test('cleanFilenameForManualTitle - Leereingaben (Guard)', () => {
    assert.strictEqual(cleanFilenameForManualTitle(""), "");
    assert.strictEqual(cleanFilenameForManualTitle(null), "");
    assert.strictEqual(cleanFilenameForManualTitle(undefined), "");
});
