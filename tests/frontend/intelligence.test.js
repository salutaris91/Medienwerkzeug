import test from 'node:test';
import assert from 'node:assert';
import { updateHintElement } from '../../gui/static/js/intelligence.js';

function createMockElement() {
    const classes = new Set(['hidden']);
    return {
        textContent: "",
        classList: {
            classes,
            remove(cls) {
                classes.delete(cls);
            },
            add(cls) {
                classes.add(cls);
            },
            contains(cls) {
                return classes.has(cls);
            }
        }
    };
}

test('updateHintElement - recInfo is null', () => {
    const el = createMockElement();
    updateHintElement(el, 60, null);

    assert.strictEqual(el.textContent, "💡 Noch keine historischen Daten für diesen Inhaltstyp vorhanden. Standardempfehlung ist CRF 60.");
    assert.strictEqual(el.classList.contains("hidden"), false);
});

test('updateHintElement - recInfo is undefined', () => {
    const el = createMockElement();
    updateHintElement(el, 60, undefined);

    assert.strictEqual(el.textContent, "💡 Noch keine historischen Daten für diesen Inhaltstyp vorhanden. Standardempfehlung ist CRF 60.");
    assert.strictEqual(el.classList.contains("hidden"), false);
});

test('updateHintElement - currentVal equals optimal', () => {
    const el = createMockElement();
    const recInfo = { optimal_quality: 62 };
    updateHintElement(el, 62, recInfo);

    assert.strictEqual(el.textContent, "✅ Optimaler Wert für diesen Inhaltstyp basierend auf deiner Historie (CRF 62).");
    assert.strictEqual(el.classList.contains("hidden"), false);
});

test('updateHintElement - currentVal is greater than optimal', () => {
    const el = createMockElement();
    const recInfo = { optimal_quality: 58 };
    updateHintElement(el, 64, recInfo);

    assert.strictEqual(el.textContent, "💡 Deine Historie zeigt, dass dieser Inhaltstyp auch mit CRF 58 ohne sichtbaren Qualitätsverlust gut komprimiert wird (spart mehr Platz).");
    assert.strictEqual(el.classList.contains("hidden"), false);
});

test('updateHintElement - currentVal is less than optimal', () => {
    const el = createMockElement();
    const recInfo = { optimal_quality: 65 };
    updateHintElement(el, 60, recInfo);

    assert.strictEqual(el.textContent, "⚠️ Dieser Wert liegt unter dem empfohlenen Optimum von CRF 65. Es könnte zu sichtbaren Kompressionsartefakten kommen.");
    assert.strictEqual(el.classList.contains("hidden"), false);
});
