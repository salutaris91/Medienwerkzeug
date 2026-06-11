import test from 'node:test';
import assert from 'node:assert';
import { formatBytes } from '../../gui/static/js/format.js';

test('formatBytes - Nullwert', () => {
    assert.strictEqual(formatBytes(0), '0 Bytes');
});

test('formatBytes - Werte unter 1 KB', () => {
    assert.strictEqual(formatBytes(1), '1 Bytes');
    assert.strictEqual(formatBytes(500), '500 Bytes');
    assert.strictEqual(formatBytes(1023), '1023 Bytes');
});

test('formatBytes - Einheiten und Schwellenwerte', () => {
    assert.strictEqual(formatBytes(1024), '1 KB');
    assert.strictEqual(formatBytes(2048), '2 KB');
    assert.strictEqual(formatBytes(1024 * 1024), '1 MB');
    assert.strictEqual(formatBytes(1024 * 1024 * 1024), '1 GB');
    assert.strictEqual(formatBytes(1024 * 1024 * 1024 * 1024), '1 TB');
});

test('formatBytes - Nachkommastellen und Rundung', () => {
    assert.strictEqual(formatBytes(1500), '1.46 KB');
    assert.strictEqual(formatBytes(1024 * 1024 * 1.5), '1.5 MB');
    assert.strictEqual(formatBytes(1024 * 1024 * 1024 * 1.756), '1.76 GB');
});
