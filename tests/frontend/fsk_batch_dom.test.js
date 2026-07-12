import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// DOM Mocking helper
function createMockElement() {
    const classSet = new Set();
    const children = [];
    return {
        textContent: "",
        innerHTML: "",
        style: {},
        value: "",
        disabled: false,
        dataset: {},
        scrollTop: 0,
        __listeners: {},
        classList: {
            add: (c) => classSet.add(c),
            remove: (c) => classSet.delete(c),
            contains: (c) => classSet.has(c)
        },
        addEventListener(event, fn) {
            if (!this.__listeners[event]) this.__listeners[event] = [];
            this.__listeners[event].push(fn);
        },
        dispatchEvent(event) {
            const handlers = this.__listeners[event.type] || [];
            handlers.forEach(fn => fn(event));
        },
        appendChild(child) {
            children.push(child);
        },
        // für closest und co
        querySelectorAll: () => [],
        querySelector: () => null
    };
}

const elements = {};
globalThis.document = {
    getElementById(id) {
        if (!elements[id]) {
            elements[id] = createMockElement();
        }
        return elements[id];
    },
    createElement() {
        return createMockElement();
    },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    __listeners: {},
    addEventListener(event, fn) {
        if (!this.__listeners[event]) this.__listeners[event] = [];
        this.__listeners[event].push(fn);
    },
    dispatchEvent(event) {
        const handlers = this.__listeners[event.type] || [];
        handlers.forEach(fn => fn(event));
    }
};

globalThis.localStorage = {
    getItem: () => null,
    setItem: () => {}
};
globalThis.window = {
    scrollTo: () => {},
    addEventListener: () => {},
    localStorage: globalThis.localStorage
};

globalThis.escapeHTML = (str) => str;
globalThis.alert = (msg) => { globalThis.lastAlert = msg; };
globalThis.confirm = (msg) => { globalThis.lastConfirm = msg; return true; };
globalThis.formatFskLabel = (val) => `FSK ${val}`;

// Mock fetch
const originalFetch = (url, options) => {
    globalThis.fetchRequests.push({ url, options });
    if (globalThis.mockFetchResponse) {
        return Promise.resolve(globalThis.mockFetchResponse);
    }
    return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ projects: [] })
    });
};

globalThis.fetch = originalFetch;
globalThis.window.fetch = originalFetch;
globalThis.fetchRequests = [];
globalThis.mockFetchResponse = null;

globalThis.loadConversionRecommendations = () => {};
globalThis.triggerQualityHintUpdates = () => {};
globalThis.osBasename = (p) => p ? p.split(/[\\/]/).pop() : "";

// Load app.js
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
let appJsContent = fs.readFileSync(appJsPath, 'utf8');
appJsContent = appJsContent.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, "");
appJsContent = appJsContent.replace(/"DOMContentLoaded"/g, '"never-fire"');
appJsContent = appJsContent.replace(/setInterval\(pollHealthStatus,\s*5000\);/g, "");

appJsContent += `
globalThis.openFskBatchModal = openFskBatchModal;
globalThis.loadFskBatchPreview = loadFskBatchPreview;
globalThis.applyFskBatch = applyFskBatch;
globalThis.resolveSendPaths = resolveSendPaths;
globalThis.setFskBatchScope = (scope) => { currentFskBatchScope = scope; };
`;

eval(appJsContent);
globalThis.document.dispatchEvent({ type: 'DOMContentLoaded' });

// Tests
test('resolveSendPaths - resolves hierarchy properly', () => {
    const items = [
        { path: "/a/b.mkv", season_path: "/a", series_path: "/a/.." }
    ];
    assert.deepStrictEqual(resolveSendPaths(items, "single"), ["/a/b.mkv"]);
    assert.deepStrictEqual(resolveSendPaths(items, "season"), ["/a"]);
    assert.deepStrictEqual(resolveSendPaths(items, "series"), ["/a/.."]);

    // Null targets fallback safety
    const items2 = [
        { path: "/x/y.mkv" }
    ];
    assert.deepStrictEqual(resolveSendPaths(items2, "series"), []);
});

test('openFskBatchModal - opens modal and sets up state', () => {
    const modal = document.getElementById("modal-fsk-batch-preview");
    const targetVal = document.getElementById("fsk-batch-target-val");

    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({ files: [], summary: {} })
    };

    globalThis.openFskBatchModal([{path: "/test.nfo"}], "12");

    assert.ok(modal.classList.contains("active"));
    assert.ok(!modal.classList.contains("hidden"));
    assert.strictEqual(targetVal.textContent, "FSK 12");
});

test('Scope-Change-Event - triggers new preview fetch', async () => {
    globalThis.fetchRequests = [];

    // Das Item muss season_path haben, damit das UI nicht auf single zurückfällt!
    globalThis.openFskBatchModal([{path: "/tvshow.nfo", season_path: "/season1"}], "12");
    await new Promise(r => setTimeout(r, 10)); // initial preview fetch

    globalThis.fetchRequests = []; // clear history

    const scopeSelect = document.getElementById("fsk-batch-scope-select");
    scopeSelect.value = "season";
    
    // Manuelles callen, da DOMContentLoaded-Listener unterdrückt ist
    globalThis.setFskBatchScope("season");
    await globalThis.loadFskBatchPreview();

    await new Promise(r => setTimeout(r, 10));

    const reqs = globalThis.fetchRequests.filter(req => req.url.includes("fsk-batch/preview"));
    assert.strictEqual(reqs.length, 1);
    
    const body = JSON.parse(reqs[0].options.body);
    assert.strictEqual(body.scope, "season");
    assert.deepStrictEqual(body.paths, ["/season1"]);
});

test('Null-Ziel-Sperre im DOM', async () => {
    globalThis.fetchRequests = [];

    // Items without season_path
    globalThis.openFskBatchModal([{path: "/test.nfo"}], "12");
    await new Promise(r => setTimeout(r, 10)); // Wait for initial fetch

    const scopeSelect = document.getElementById("fsk-batch-scope-select");
    scopeSelect.value = "season";
    
    // Manuelles callen, da DOMContentLoaded-Listener unterdrückt ist
    globalThis.setFskBatchScope("season");
    await globalThis.loadFskBatchPreview();

    await new Promise(r => setTimeout(r, 10));

    const container = document.getElementById("fsk-batch-tree-container");
    assert.ok(container.innerHTML.includes("Keine gültigen Zielpfade"));
});

test('Apply-Fetch-Payload and preview rendering', async () => {
    globalThis.fetchRequests = [];

    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/test.nfo", fingerprint: "abcd", status: "ready", hierarchy: { type: "movie", movie: "Test" } }
            ],
            summary: { ready: 1 }
        })
    };

    globalThis.openFskBatchModal([{path: "/test.nfo"}], "16");
    await new Promise(r => setTimeout(r, 10));
    
    const container = document.getElementById("fsk-batch-tree-container");
    assert.ok(container.innerHTML.includes("test.nfo"), "HTML war: " + container.innerHTML); // Test for file name
    
    // Now simulate apply
    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            ok: true,
            status: "success",
            results: [],
            summary: { success: 1, failed: 0 }
        })
    };
    
    await globalThis.applyFskBatch();
    
    const applyReq = globalThis.fetchRequests.find(req => req.url.includes("fsk-batch/apply"));
    assert.ok(applyReq);
    
    const body = JSON.parse(applyReq.options.body);
    assert.deepStrictEqual(body.root_paths, ["/test.nfo"]);
    assert.strictEqual(body.scope, "single");
    assert.strictEqual(body.new_fsk, "16");
    assert.deepStrictEqual(body.files, [{path: "/test.nfo", fingerprint: "abcd"}]);
});

test('Darstellung von partial und failed', async () => {
    globalThis.fetchRequests = [];
    
    // 1. Prepare Plan via Preview!
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/test1.nfo", fingerprint: "abcd", status: "ready", hierarchy: { type: "movie", movie: "Test 1" } },
                { path: "/test2.nfo", fingerprint: "efgh", status: "ready", hierarchy: { type: "movie", movie: "Test 2" } }
            ],
            summary: { ready: 2 }
        })
    };
    globalThis.openFskBatchModal([{path: "/test1.nfo"}, {path: "/test2.nfo"}], "16");
    await new Promise(r => setTimeout(r, 10));
    
    // 2. Apply and simulate partial failure
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            ok: true,
            status: "partial",
            results: [
                { path: "/test1.nfo", status: "success" },
                { path: "/test2.nfo", status: "failed", message: "Readonly" }
            ],
            summary: { success: 1, failed: 1, unchanged: 0 }
        })
    };
    
    await globalThis.applyFskBatch();
    await new Promise(r => setTimeout(r, 10));
    
    const summaryEl = document.getElementById("fsk-batch-summary");
    assert.ok(summaryEl.innerHTML.includes("Erfolgreich geändert: <strong>1</strong>"));
    assert.ok(summaryEl.innerHTML.includes("Fehlgeschlagen: <strong>1</strong>"));
    assert.ok(summaryEl.innerHTML.includes("Readonly"));
});
