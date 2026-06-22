import test from 'node:test';
import assert from 'node:assert';
import { updateMwDataPanel, prepareSeriesPayload } from '../../gui/static/js/nfo_ui.js';

function createMockElement(classes = ['hidden']) {
    const classSet = new Set(classes);
    return {
        textContent: "",
        classList: {
            classes: classSet,
            remove(cls) {
                classSet.delete(cls);
            },
            add(cls) {
                classSet.add(cls);
            },
            contains(cls) {
                return classSet.has(cls);
            }
        },
        children: [],
        appendChild(child) {
            this.children.push(child);
        }
    };
}

function createMockLinkElement() {
    return {
        href: "",
        textContent: "",
        target: "",
        rel: "",
        style: {}
    };
}

test('updateMwDataPanel - with mw_data containing url and sync', () => {
    const container = createMockElement(['hidden']);
    const urlSpan = createMockElement(['hidden']);
    const syncSpan = createMockElement(['hidden']);
    
    const originalCreateElement = globalThis.document ? globalThis.document.createElement : null;
    globalThis.document = {
        createElement(tagName) {
            if (tagName === "a") {
                return createMockLinkElement();
            }
            return {};
        }
    };

    const mwData = {
        source_url: "https://example.com/playlist",
        last_sync: "2026-06-22T07:07:21"
    };

    try {
        updateMwDataPanel(container, urlSpan, syncSpan, mwData);

        assert.strictEqual(container.classList.contains("hidden"), false);
        assert.strictEqual(urlSpan.classList.contains("hidden"), false);
        assert.strictEqual(syncSpan.classList.contains("hidden"), false);
        
        assert.strictEqual(urlSpan.textContent, "Quell-URL: ");
        assert.strictEqual(urlSpan.children.length, 1);
        assert.strictEqual(urlSpan.children[0].href, "https://example.com/playlist");
        assert.strictEqual(urlSpan.children[0].target, "_blank");
        assert.strictEqual(urlSpan.children[0].rel, "noopener noreferrer");
        
        assert.match(syncSpan.textContent, /Letzter Sync: .*/);
    } finally {
        if (originalCreateElement) {
            globalThis.document.createElement = originalCreateElement;
        } else {
            delete globalThis.document;
        }
    }
});

test('updateMwDataPanel - without mw_data', () => {
    const container = createMockElement([]);
    const urlSpan = createMockElement([]);
    const syncSpan = createMockElement([]);

    updateMwDataPanel(container, urlSpan, syncSpan, null);

    assert.strictEqual(container.classList.contains("hidden"), true);
    assert.strictEqual(urlSpan.classList.contains("hidden"), true);
    assert.strictEqual(syncSpan.classList.contains("hidden"), true);
});

test('prepareSeriesPayload - with mw_data', () => {
    const selectedShow = {
        name: "Serengeti",
        id: "https://example.com/playlist",
        provider: "ytdlp",
        mw_data: {
            source_url: "https://example.com/playlist",
            resolved_topic: "Serengeti"
        }
    };
    const basePayload = {
        media_type: "tv",
        project_name: "Nature Doc"
    };

    const payload = prepareSeriesPayload(selectedShow, basePayload);

    assert.strictEqual(payload.source_url, "https://example.com/playlist");
    assert.strictEqual(payload.resolved_topic, "Serengeti");
    assert.deepStrictEqual(payload.mw_data, selectedShow.mw_data);
    assert.strictEqual(basePayload.source_url, undefined);
});

test('prepareSeriesPayload - without mw_data', () => {
    const selectedShow = {
        name: "Serengeti",
        id: "https://example.com/playlist",
        provider: "ytdlp"
    };
    const basePayload = {
        media_type: "tv",
        project_name: "Nature Doc"
    };

    const payload = prepareSeriesPayload(selectedShow, basePayload);

    assert.strictEqual(payload.source_url, undefined);
    assert.strictEqual(payload.resolved_topic, undefined);
    assert.strictEqual(payload.mw_data, undefined);
});
