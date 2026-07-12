import test from 'node:test';
import assert from 'node:assert';
import { osBasename, formatFskLabel } from '../../gui/static/js/fsk_batch.js';

test('osBasename - extracts filename correctly', () => {
    // Unix paths
    assert.strictEqual(osBasename('/Nas/Serien/Dracula/Staffel 1/S01E01.nfo'), 'S01E01.nfo');
    assert.strictEqual(osBasename('S01E01.nfo'), 'S01E01.nfo');
    
    // Windows paths
    assert.strictEqual(osBasename('C:\\Nas\\Serien\\Dracula\\Staffel 1\\S01E01.nfo'), 'S01E01.nfo');
    
    // Empty path
    assert.strictEqual(osBasename(''), '');
    assert.strictEqual(osBasename(null), '');
});

test('formatFskLabel - formats FSK labels correctly', () => {
    // Raw numbers
    assert.strictEqual(formatFskLabel(0), 'FSK 0');
    assert.strictEqual(formatFskLabel(6), 'FSK 6');
    assert.strictEqual(formatFskLabel('12'), 'FSK 12');
    
    // Already formatted
    assert.strictEqual(formatFskLabel('FSK 16'), 'FSK 16');
    assert.strictEqual(formatFskLabel('  FSK 18  '), 'FSK 18');
    
    // Missing/None ratings
    assert.strictEqual(formatFskLabel(null), 'Keine');
    assert.strictEqual(formatFskLabel(undefined), 'Keine');
});
