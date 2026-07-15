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
    const attributes = {};
    return {
        textContent: "",
        innerHTML: "",
        style: {},
        value: "",
        disabled: false,
        dataset: {},
        scrollTop: 0,
        cloneNode: () => createMockElement(),
        replaceWith: () => {},
        removeChild: () => {},
        setAttribute: (name, val) => { attributes[name] = val; },
        getAttribute: (name) => attributes[name],
        removeAttribute: (name) => { delete attributes[name]; },
        __listeners: {},
        classList: {
            add: (c) => classSet.add(c),
            remove: (c) => classSet.delete(c),
            contains: (c) => classSet.has(c),
            toggle: (c) => {
                if (classSet.has(c)) {
                    classSet.delete(c);
                } else {
                    classSet.add(c);
                }
            }
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

globalThis.elements = {};
globalThis.document = {
    body: createMockElement(),
    documentElement: createMockElement(),
    getElementById(id) {
        if (!globalThis.elements[id]) {
            globalThis.elements[id] = createMockElement();
        }
        return globalThis.elements[id];
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
        handlers.forEach(fn => {
            try { fn(event); } catch(e) { /* ignore in mock */ }
        });
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

// globalThis.escapeHTML = (str) => str;
globalThis.alert = (msg) => { globalThis.lastAlert = msg; };
globalThis.confirm = (msg) => { globalThis.lastConfirm = msg; return true; };
globalThis.formatFskLabel = (val) => `FSK ${val}`;

// Mock fetch with manual promise control
globalThis.fetchRequests = [];
globalThis.mockFetchResponse = null;
globalThis.autoResolveFetch = true;

const originalFetch = (url, options) => {
    let resolveFn;
    let rejectFn;
    const promise = new Promise((resolve, reject) => {
        resolveFn = resolve;
        rejectFn = reject;
    });

    const req = {
        url,
        options,
        resolve: (val) => {
            if (val && typeof val.json !== 'function') {
                const rawVal = val;
                val = {
                    ok: rawVal.ok !== false,
                    status: rawVal.status || 200,
                    json: async () => rawVal.json ? rawVal.json() : rawVal
                };
            }
            resolveFn(val);
        },
        reject: (err) => rejectFn(err)
    };

    globalThis.fetchRequests.push(req);

    if (globalThis.autoResolveFetch) {
        const configuredResponse = typeof globalThis.mockFetchResponse === "function"
            ? globalThis.mockFetchResponse(url, options)
            : globalThis.mockFetchResponse;
        if (configuredResponse) {
            resolveFn(configuredResponse);
        } else {
            resolveFn({
                ok: true,
                status: 200,
                json: async () => ({ projects: [] })
            });
        }
    }

    return promise;
};

globalThis.fetch = originalFetch;
globalThis.window.fetch = originalFetch;

globalThis.loadConversionRecommendations = () => {};
globalThis.triggerQualityHintUpdates = () => {};
globalThis.osBasename = (p) => p ? p.split(/[\\/]/).pop() : "";

globalThis.document.body = createMockElement();

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
globalThis.closeFskBatchModal = closeFskBatchModal;
globalThis.resolveSendPaths = resolveSendPaths;
globalThis.submitNfoAgentJob = submitNfoAgentJob;
globalThis.openNfoAgentModal = openNfoAgentModal;
globalThis.renderNfoAgentFiles = renderNfoAgentFiles;
globalThis.applyNfoAgentEditMode = applyNfoAgentEditMode;
globalThis.setNfoAgentEditMode = setNfoAgentEditMode;
globalThis.startNfoAgentLogStreaming = startNfoAgentLogStreaming;
globalThis.searchNfoAgentMetadata = searchNfoAgentMetadata;
globalThis.renderHealthStatus = renderHealthStatus;
globalThis.setFskBatchScope = (scope) => { currentFskBatchScope = scope; };
Object.defineProperty(globalThis, 'healthGroupMode', {
    get: () => window.healthGroupMode,
    set: (v) => { window.healthGroupMode = v; }
});
Object.defineProperty(globalThis, 'isFskBatchApplying', {
    get: () => isFskBatchApplying,
    set: (v) => { isFskBatchApplying = v; }
});
Object.defineProperty(globalThis, 'currentFskBatchPlan', {
    get: () => currentFskBatchPlan,
    set: (v) => { currentFskBatchPlan = v; }
});
Object.defineProperty(globalThis, 'currentFskBatchItems', {
    get: () => currentFskBatchItems,
    set: (v) => { currentFskBatchItems = v; }
});
Object.defineProperty(globalThis, 'currentFskBatchTarget', {
    get: () => currentFskBatchTarget,
    set: (v) => { currentFskBatchTarget = v; }
});
Object.defineProperty(globalThis, 'currentFskBatchScope', {
    get: () => currentFskBatchScope,
    set: (v) => { currentFskBatchScope = v; }
});
Object.defineProperty(globalThis, 'wasFskModalOpenForNfoAgent', {
    get: () => wasFskModalOpenForNfoAgent,
    set: (v) => { wasFskModalOpenForNfoAgent = v; }
});
Object.defineProperty(globalThis, 'nfoAgentJobSuccess', {
    get: () => nfoAgentJobSuccess,
    set: (v) => { nfoAgentJobSuccess = v; }
});
Object.defineProperty(globalThis, 'nfoAgentJobErrorMsg', {
    get: () => nfoAgentJobErrorMsg,
    set: (v) => { nfoAgentJobErrorMsg = v; }
});
Object.defineProperty(globalThis, 'nfoAgentEditContext', {
    get: () => nfoAgentEditContext,
    set: (v) => { nfoAgentEditContext = v; }
});
globalThis.setNfoAgentScanData = (value) => { nfoAgentScanData = value; };
globalThis.setNfoAgentCurrentPath = (value) => { nfoAgentCurrentPath = value; };
`;

eval(appJsContent);
globalThis.bindNfoAgentEvents = globalThis.window.bindNfoAgentEvents;
globalThis.bindHealthActionEvents = globalThis.window.bindHealthActionEvents;
const realOpenFskBatchModal = globalThis.openFskBatchModal;

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
    const targetSelect = document.getElementById("fsk-batch-target-select");

    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({ files: [], summary: {} })
    };

    globalThis.openFskBatchModal([{path: "/test.nfo"}], "12");

    assert.ok(modal.classList.contains("active"));
    assert.ok(!modal.classList.contains("hidden"));
    assert.strictEqual(targetSelect.value, "12");
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
    assert.deepStrictEqual(body.files, [{path: "/test.nfo", status: "ready", fingerprint: "abcd"}]);
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

test('No native Dialogs and Inline Error Rendering', async () => {
    // Reset call spies
    globalThis.lastAlert = null;
    globalThis.lastConfirm = null;

    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = {
        ok: false,
        status: 409,
        json: () => Promise.resolve({
            ok: false,
            message: "Integritätskonflikt"
        })
    };

    // FSK Preview laden (wird fehlschlagen)
    await globalThis.loadFskBatchPreview();
    await new Promise(r => setTimeout(r, 10));

    const errorEl = document.getElementById("fsk-batch-error-inline");
    assert.ok(errorEl.style.display !== "none");
    assert.ok(errorEl.textContent.includes("Integritätskonflikt"));
    assert.strictEqual(globalThis.lastAlert, null, "Native alert() was called");
});

test('Dynamic Button Text and Disabled State', async () => {
    const confirmBtn = document.getElementById("btn-fsk-batch-confirm");

    // Case 1: 0 ready files
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/test.nfo", fingerprint: "abcd", status: "unchanged", hierarchy: { type: "movie", movie: "Test" } }
            ],
            summary: { total: 1, ready: 0, unchanged: 1, skipped_missing: 0, skipped_problematic: 0 }
        })
    };

    globalThis.openFskBatchModal([{path: "/test.nfo"}], "12");
    await new Promise(r => setTimeout(r, 10));

    assert.strictEqual(confirmBtn.disabled, false);
    assert.ok(confirmBtn.innerHTML.includes("Fertig"), "Button text: " + confirmBtn.innerHTML);

    // Case 2: 2 ready files
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/test1.nfo", fingerprint: "abcd", status: "ready", hierarchy: { type: "movie", movie: "Test" } },
                { path: "/test2.nfo", fingerprint: "efgh", status: "ready", hierarchy: { type: "movie", movie: "Test" } }
            ],
            summary: { total: 2, ready: 2, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
        })
    };

    globalThis.openFskBatchModal([{path: "/test1.nfo"}, {path: "/test2.nfo"}], "16");
    await new Promise(r => setTimeout(r, 10));

    assert.strictEqual(confirmBtn.disabled, false);
    assert.ok(confirmBtn.innerHTML.includes("2 NFOs auf FSK 16 ändern"), "Button text: " + confirmBtn.innerHTML);
});

test('Apply payload includes status field', async () => {
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

    // Simulate Apply Fetch
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
    await new Promise(r => setTimeout(r, 10));

    const applyReq = globalThis.fetchRequests.find(req => req.url.includes("fsk-batch/apply"));
    assert.ok(applyReq);

    const body = JSON.parse(applyReq.options.body);
    // Verifizieren, dass 'status' Teil der payload files ist (wichtig für skipped_missing Checks)
    assert.deepStrictEqual(body.files, [{path: "/test.nfo", status: "ready", fingerprint: "abcd"}]);
});

test('show-group-fsk-btn click - triggers openFskBatchModal and fetches series scope', () => {
    globalThis.fetchRequests = [];
    globalThis.healthGroupMode = "media";

    const container = document.getElementById("view-library");
    const issuesEl = document.getElementById("health-issues");

    let boundBtn = null;
    const originalQuerySelectorAll = globalThis.document.querySelectorAll;
    globalThis.document.querySelectorAll = (sel) => {
        if (sel === "#health-issues .show-group-fsk-btn") {
            const btn = createMockElement();
            btn.setAttribute("data-path", "/Serien/My Show");
            btn.getAttribute = (name) => {
                if (name === "data-path") return "/Serien/My Show";
                return null;
            };
            const mockSelect = createMockElement();
            mockSelect.value = "16";
            btn.previousElementSibling = mockSelect;
            boundBtn = btn;
            return [btn];
        }
        return [];
    };

    const testData = {
        issues: [{ severity: "warning", category: "FSK", message: "FSK fehlt", path: "/Serien/My Show" }],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "missing_fsk",
                current_fsk: "",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/Ep1.mkv", fsk_status: "missing_fsk", current_fsk: "" },
                        { name: "Episode 2", path: "/Serien/My Show/Season 1/Ep2.mkv", fsk_status: "missing_fsk", current_fsk: "" }
                    ]
                }]
            }],
            movies: []
        }
    };
    globalThis.renderHealthStatus(testData);

    assert.ok(boundBtn);
    boundBtn.dispatchEvent({ type: 'click' });

    assert.deepStrictEqual(globalThis.currentFskBatchItems, [{ series_path: "/Serien/My Show", path: "/Serien/My Show", media_kind: "series" }]);
    assert.strictEqual(globalThis.currentFskBatchTarget, "16");
    assert.strictEqual(globalThis.currentFskBatchScope, "series");

    globalThis.document.querySelectorAll = originalQuerySelectorAll;
});

test('season-group-fsk-btn click - triggers openFskBatchModal and fetches season scope', () => {
    globalThis.fetchRequests = [];
    globalThis.healthGroupMode = "media";

    const container = document.getElementById("view-library");
    const issuesEl = document.getElementById("health-issues");

    let boundBtn = null;
    const originalQuerySelectorAll = globalThis.document.querySelectorAll;
    globalThis.document.querySelectorAll = (sel) => {
        if (sel === "#health-issues .season-group-fsk-btn") {
            const btn = createMockElement();
            btn.setAttribute("data-path", "/Serien/My Show/Season 1");
            btn.setAttribute("data-series-path", "/Serien/My Show");
            btn.getAttribute = (name) => {
                if (name === "data-path") return "/Serien/My Show/Season 1";
                if (name === "data-series-path") return "/Serien/My Show";
                return null;
            };
            const mockSelect = createMockElement();
            mockSelect.value = "6";
            btn.previousElementSibling = mockSelect;
            boundBtn = btn;
            return [btn];
        }
        return [];
    };

    const testData = {
        issues: [{ severity: "warning", category: "FSK", message: "FSK fehlt", path: "/Serien/My Show" }],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "missing_fsk",
                current_fsk: "",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/Ep1.mkv", fsk_status: "missing_fsk", current_fsk: "" },
                        { name: "Episode 2", path: "/Serien/My Show/Season 1/Ep2.mkv", fsk_status: "missing_fsk", current_fsk: "" }
                    ]
                }]
            }],
            movies: []
        }
    };
    globalThis.renderHealthStatus(testData);

    assert.ok(boundBtn);
    boundBtn.dispatchEvent({ type: 'click' });

    assert.deepStrictEqual(globalThis.currentFskBatchItems, [{
        season_path: "/Serien/My Show/Season 1",
        series_path: "/Serien/My Show",
        path: "/Serien/My Show/Season 1",
        media_kind: "series"
    }]);
    assert.strictEqual(globalThis.currentFskBatchTarget, "6");
    assert.strictEqual(globalThis.currentFskBatchScope, "season");

    globalThis.document.querySelectorAll = originalQuerySelectorAll;
});

test('Out-of-order preview requests are correctly discarded', async () => {
    globalThis.fetchRequests = [];
    globalThis.autoResolveFetch = false;
    globalThis.currentFskBatchItems = [{ path: "/test.nfo" }];
    globalThis.currentFskBatchScope = "single";
    globalThis.currentFskBatchTarget = "12";

    const p1 = globalThis.loadFskBatchPreview();
    const p2 = globalThis.loadFskBatchPreview();

    const req2 = globalThis.fetchRequests[1];
    assert.ok(req2);
    req2.resolve({
        ok: true,
        json: async () => ({
            files: [{ path: "/test.nfo", status: "ready", fingerprint: "req2", hierarchy: { show: null, season: null, episode: null } }],
            summary: { total: 1, ready: 1, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
        })
    });
    await p2;

    const req1 = globalThis.fetchRequests[0];
    assert.ok(req1);
    req1.resolve({
        ok: true,
        json: async () => ({
            files: [{ path: "/test.nfo", status: "ready", fingerprint: "req1", hierarchy: { show: null, season: null, episode: null } }],
            summary: { total: 1, ready: 1, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
        })
    });
    await p1;

    assert.strictEqual(globalThis.currentFskBatchPlan.files[0].fingerprint, "req2");
    globalThis.autoResolveFetch = true;
});

test('Modal direct scope and prevent dual requests', () => {
    globalThis.fetchRequests = [];
    globalThis.currentFskBatchPlan = null;
    globalThis.autoResolveFetch = true;
    globalThis.openFskBatchModal = realOpenFskBatchModal;

    const item = { path: "/Serien/My Show", series_path: "/Serien/My Show" };
    globalThis.openFskBatchModal([item], "12", "series");

    assert.strictEqual(globalThis.fetchRequests.length, 1);
    const body = JSON.parse(globalThis.fetchRequests[0].options.body || "{}");
    assert.strictEqual(body.scope, "series");
});

test('409 Conflict keeps error message visible after preview load', async () => {
    globalThis.fetchRequests = [];
    globalThis.autoResolveFetch = false;
    globalThis.currentFskBatchPlan = {
        files: [{ path: "/test.nfo", status: "ready", fingerprint: "old" }],
        summary: { total: 1, ready: 1, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
    };
    globalThis.currentFskBatchItems = [{ path: "/test.nfo" }];
    globalThis.currentFskBatchScope = "single";
    globalThis.currentFskBatchTarget = "12";

    const errorEl = document.getElementById("fsk-batch-error-inline");
    assert.ok(errorEl);

    // 1. Apply triggeren
    const pApply = globalThis.applyFskBatch();

    await new Promise(r => setTimeout(r, 10));

    // 2. Simuliere 409-Antwort
    const applyReq = globalThis.fetchRequests.find(req => req.url.includes("fsk-batch/apply"));
    assert.ok(applyReq);
    applyReq.resolve({
        status: 409,
        ok: false,
        json: async () => ({ message: "Datei wurde modifiziert." })
    });
    await pApply;

    await new Promise(r => setTimeout(r, 10));
    // 3. Das nachfolgende loadFskBatchPreview(true) annehmen
    const previewReq = globalThis.fetchRequests.find(req => req.url.includes("fsk-batch/preview"));
    assert.ok(previewReq);
    previewReq.resolve({
        ok: true,
        json: async () => ({
            files: [{ path: "/test.nfo", status: "ready", fingerprint: "new", hierarchy: { show: null, season: null, episode: null } }],
            summary: { total: 1, ready: 1, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
        })
    });
    await new Promise(r => setTimeout(r, 20));

    // 4. Verifizieren, dass die 409-Fehlermeldung weiterhin im Element sichtbar ist und nicht gelöscht wurde
    assert.strictEqual(errorEl.style.display, "block");
    assert.ok(errorEl.textContent.includes("Konflikt/Race-Condition"));

    // Cleanup
    globalThis.autoResolveFetch = true;
});

test('Apply-Lock blocks closeFskBatchModal', async () => {
    const modal = document.getElementById("modal-fsk-batch-preview");
    assert.ok(modal);
    modal.classList.add("active");

    // 1. Lock setzen und close aufrufen
    globalThis.isFskBatchApplying = true;
    globalThis.closeFskBatchModal();

    // 2. Modal muss weiterhin aktiv bleiben
    assert.ok(modal.classList.contains("active"));

    // 3. Lock lösen und close aufrufen
    globalThis.isFskBatchApplying = false;
    globalThis.closeFskBatchModal();
    assert.ok(!modal.classList.contains("active"));
});

test('Single vs Group button visibility and kanonische FSK states in Media View', () => {
    // Hilfsfunktionen für präzise HTML-Prüfungen
    const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const hasButtonWithClassAndPath = (html, className, path) => {
        const regex = new RegExp(`<button[^>]*class="[^"]*${escapeRegExp(className)}[^"]*"[^>]*data-path="${escapeRegExp(path)}"`, 'i');
        return regex.test(html);
    };

    const container = document.createElement("div");
    container.id = "view-library";
    globalThis.elements["view-library"] = container;
    document.body.appendChild(container);

    const issuesEl = document.createElement("div");
    issuesEl.id = "health-issues";
    globalThis.elements["health-issues"] = issuesEl;
    container.appendChild(issuesEl);

    globalThis.healthGroupMode = "media";

    // 1. Testfall: Nur genau 1 Befund in der Serie (Ep 1 hat healthy, Ep 2 hat missing_fsk)
    const testDataSingle = {
        issues: [{ type: "missing_age_rating", severity: "warning", path: "/Serien/My Show/Season 1/S01E02.nfo", category: "serien" }],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "healthy",
                current_fsk: "FSK 12",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "My Show - S01E01", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "healthy", current_fsk: "FSK 12" },
                        { name: "My Show - S01E02", path: "/Serien/My Show/Season 1/S01E02.nfo", fsk_status: "missing_fsk", current_fsk: "Keine" }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataSingle);

    // Erwartetes Verhalten:
    // - Serien-Gruppenaktion (.show-group-fsk-btn) darf NICHT existieren (nur 1 Befund)
    // - Staffel-Gruppenaktion (.season-group-fsk-btn) darf NICHT existieren (nur 1 Befund)
    // - Einzelbutton (.health-fix-fsk) an Episode 2 MUSS existieren
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "show-group-fsk-btn", "/Serien/My Show"));
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "season-group-fsk-btn", "/Serien/My Show/Season 1"));
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E02.nfo"));

    // 2. Testfall: Mehrfachgruppe (Ep 1 und Ep 2 haben missing_fsk)
    const testDataGroup = {
        issues: [
            { type: "missing_age_rating", severity: "warning", path: "/Serien/My Show/Season 1/S01E01.nfo", category: "serien" },
            { type: "missing_age_rating", severity: "warning", path: "/Serien/My Show/Season 1/S01E02.nfo", category: "serien" }
        ],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "healthy",
                current_fsk: "FSK 12",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "My Show - S01E01", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "missing_fsk", current_fsk: "Keine" },
                        { name: "My Show - S01E02", path: "/Serien/My Show/Season 1/S01E02.nfo", fsk_status: "missing_fsk", current_fsk: "Keine" }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataGroup);

    // Erwartetes Verhalten:
    // - Serien-Gruppenaktion (.show-group-fsk-btn) MUSS existieren (2 Befunde)
    // - Staffel-Gruppenaktion (.season-group-fsk-btn) MUSS existieren (2 Befunde in Staffel)
    // - Einzelbuttons (.health-fix-fsk) bei den Episoden MÜSSEN ausgeblendet sein (doppelte Bedienwege unterdrückt)
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "show-group-fsk-btn", "/Serien/My Show"));
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "season-group-fsk-btn", "/Serien/My Show/Season 1"));
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E02.nfo"));

    // Cleanup
    document.body.removeChild(container);
});

test('Media summary stays calm and exposes exact actions only in details', () => {
    const container = document.createElement("div");
    container.id = "view-library";
    globalThis.elements["view-library"] = container;
    document.body.appendChild(container);

    const issuesEl = document.createElement("div");
    issuesEl.id = "health-issues";
    globalThis.elements["health-issues"] = issuesEl;
    container.appendChild(issuesEl);

    globalThis.healthGroupMode = "media";
    const showPath = "/Serien/Serie ohne tvshow";
    const seasonPath = `${showPath}/Staffel 01`;
    const tvshowKey = `health:missing_nfo:${showPath}`;
    const seasonPosterKey = `health:missing_season_poster:${seasonPath}`;

    globalThis.renderHealthStatus({
        status: "done",
        issues: [
            { key: tvshowKey, type: "missing_nfo", severity: "warning", path: showPath, agent_path: showPath, message: "tvshow.nfo fehlt" },
            { key: seasonPosterKey, type: "missing_season_poster", severity: "warning", path: seasonPath, agent_path: seasonPath, message: "Staffelposter fehlt" }
        ],
        summary: { critical: 0, warning: 2, info: 0 },
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "Serie ohne tvshow",
                path: showPath,
                has_nfo: false,
                fsk_status: "nfo_missing",
                current_fsk: "",
                issue_keys: [tvshowKey],
                seasons: [{
                    name: "Staffel 01",
                    path: seasonPath,
                    issue_keys: [seasonPosterKey],
                    episodes: [{
                        name: "S01E01.nfo",
                        path: `${seasonPath}/S01E01.nfo`,
                        fsk_status: "healthy",
                        current_fsk: "FSK 12",
                        issue_keys: []
                    }]
                }]
            }],
            movies: []
        }
    });

    const html = issuesEl.innerHTML;
    const summaryHtml = html.match(/<summary class="health-media-summary">[\s\S]*?<\/summary>/)?.[0] || "";
    assert.ok(summaryHtml.includes("Metadaten: prüfen"));
    assert.ok(summaryHtml.includes("FSK: Serien-NFO prüfen"));
    assert.ok(summaryHtml.includes("Artwork: 1 fehlen"));
    assert.ok(summaryHtml.includes("Details anzeigen"));
    assert.ok(!summaryHtml.includes("health-nfo-agent"));
    assert.strictEqual((html.match(/health-nfo-agent/g) || []).length, 1);
    assert.ok(html.includes("📄 tvshow.nfo"));
    assert.ok(html.includes('class="health-media-file"'));
    assert.ok(html.includes("Fehlende Metadaten"));
    assert.ok(html.includes("Metadaten bearbeiten"));
    assert.ok(!html.includes("FSK noch nicht setzbar"));
    assert.ok(!html.includes("NFO und FSK bearbeiten"));
    assert.ok(html.includes("Fehlendes Staffelposter"));
    assert.ok(html.includes(`data-path="${showPath}"`));
    assert.ok(html.includes('data-edit-mode="series"'));

    document.body.removeChild(container);
});

test('Media-oriented movie summary keeps explicit FSK status visible', () => {
    const container = document.createElement("div");
    container.id = "view-library";
    globalThis.elements["view-library"] = container;
    document.body.appendChild(container);

    const issuesEl = document.createElement("div");
    issuesEl.id = "health-issues";
    globalThis.elements["health-issues"] = issuesEl;
    container.appendChild(issuesEl);

    globalThis.healthGroupMode = "media";
    const moviePath = "/Filme/Film mit ungültiger FSK";
    const issueKey = `health:invalid_age_rating:${moviePath}`;
    globalThis.renderHealthStatus({
        status: "done",
        issues: [{
            key: issueKey,
            type: "invalid_age_rating",
            severity: "warning",
            path: moviePath,
            message: "Ungültige Altersfreigabe"
        }],
        summary: { critical: 0, warning: 1, info: 0 },
        ignored_count: 0,
        media_structure: {
            series: [],
            movies: [{
                name: "Film mit ungültiger FSK",
                path: moviePath,
                nfo_path: `${moviePath}/movie.nfo`,
                fsk_status: "invalid_fsk",
                current_fsk: "FSK 99",
                issue_keys: [issueKey]
            }]
        }
    });

    const summaryHtml = issuesEl.innerHTML.match(/<summary class="health-media-summary">[\s\S]*?<\/summary>/)?.[0] || "";
    assert.ok(summaryHtml.includes("Metadaten: prüfen"));
    assert.ok(summaryHtml.includes("FSK: 99 ungültig"));
    assert.ok(issuesEl.innerHTML.includes("Metadaten bearbeiten"));
    assert.ok(issuesEl.innerHTML.includes('class="health-media-file"'));
    assert.ok(!issuesEl.innerHTML.includes("FSK bearbeiten"));

    document.body.removeChild(container);
});

test('nfo_missing visibility and action suppression', () => {
    // Hilfsfunktionen für präzise HTML-Prüfungen
    const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const hasButtonWithClassAndPath = (html, className, path) => {
        const regex = new RegExp(`<button[^>]*class="[^"]*${escapeRegExp(className)}[^"]*"[^>]*data-path="${escapeRegExp(path)}"`, 'i');
        return regex.test(html);
    };
    const hasSelectWithClass = (html, className) => {
        const regex = new RegExp(`<select[^>]*class="[^"]*${escapeRegExp(className)}[^"]*"`, 'i');
        return regex.test(html);
    };

    const container = document.createElement("div");
    container.id = "view-library";
    globalThis.elements["view-library"] = container;
    document.body.appendChild(container);

    const issuesEl = document.createElement("div");
    issuesEl.id = "health-issues";
    globalThis.elements["health-issues"] = issuesEl;
    container.appendChild(issuesEl);

    globalThis.healthGroupMode = "media";

    // 1. Episode mit nfo_missing
    const missingEpisodeKey = "health:missing_nfo:/Serien/My Show/Season 1/S01E01.nfo";
    const testData = {
        issues: [{ key: missingEpisodeKey, type: "missing_nfo", severity: "warning", path: "/Serien/My Show/Season 1/S01E01.nfo", agent_path: "/Serien/My Show/Season 1", category: "serien" }],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "healthy",
                current_fsk: "FSK 12",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "nfo_missing", current_fsk: "", issue_keys: [missingEpisodeKey] }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testData);

    // Serie muss sichtbar sein
    assert.ok(issuesEl.innerHTML.includes("📺 My Show"));
    // Episode 1 muss sichtbar sein
    assert.ok(issuesEl.innerHTML.includes("Episode 1"));
    // NFO-Problem wird aggregiert; der vorhandene Serien-FSK-Status bleibt sichtbar.
    assert.ok(issuesEl.innerHTML.includes("Metadaten: prüfen"));
    assert.ok(issuesEl.innerHTML.includes("FSK: 12"));
    // FSK-Label muss rot ("text-danger") sein und "NFO fehlt" heißen
    assert.ok(issuesEl.innerHTML.includes('class="text-danger"'));
    assert.ok(issuesEl.innerHTML.includes('NFO fehlt'));
    // Genau zu dieser Episode gehört ein NFO-Agent, aber keine FSK-Aktion.
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "health-nfo-agent", "/Serien/My Show/Season 1"));
    assert.ok(issuesEl.innerHTML.includes('data-edit-mode="episode"'));
    assert.ok(issuesEl.innerHTML.includes('data-episode-file="Episode 1"'));
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));

    // 2. Mehrere fehlende NFOs erzeugen keine Gruppenaktionen
    const testDataMultiple = {
        issues: [
            { key: "missing-1", type: "nfo_missing", severity: "warning", path: "/Serien/My Show/Season 1/S01E01.nfo", agent_path: "/Serien/My Show/Season 1", category: "serien" },
            { key: "missing-2", type: "nfo_missing", severity: "warning", path: "/Serien/My Show/Season 1/S01E02.nfo", agent_path: "/Serien/My Show/Season 1", category: "serien" }
        ],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "healthy",
                current_fsk: "FSK 12",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "nfo_missing", current_fsk: "", issue_keys: ["missing-1"] },
                        { name: "Episode 2", path: "/Serien/My Show/Season 1/S01E02.nfo", fsk_status: "nfo_missing", current_fsk: "", issue_keys: ["missing-2"] }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataMultiple);

    // Keine Gruppenbuttons oder Selects
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "show-group-fsk-btn", "/Serien/My Show"));
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "season-group-fsk-btn", "/Serien/My Show/Season 1"));
    assert.ok(!hasSelectWithClass(issuesEl.innerHTML, "show-group-fsk-select"));
    assert.ok(!hasSelectWithClass(issuesEl.innerHTML, "season-group-fsk-select"));

    // 3. Mischfall 1: tvshow.nfo fehlt + Episode mit missing_fsk
    const testDataMisch1 = {
        issues: [
            { type: "nfo_missing", severity: "danger", path: "/Serien/My Show", category: "serien" },
            { type: "missing_age_rating", severity: "warning", path: "/Serien/My Show/Season 1/S01E01.nfo", category: "serien" }
        ],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: false,
                fsk_status: "nfo_missing",
                current_fsk: "",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "missing_fsk", current_fsk: "" }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataMisch1);

    // NFO Agent Button für Serie vorhanden
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "health-nfo-agent", "/Serien/My Show"));
    // FSK setzen für Episode vorhanden
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));
    // Keine Gruppenaktion vorhanden
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "show-group-fsk-btn", "/Serien/My Show"));

    // 4. Mischfall 2: Vorhandene tvshow.nfo mit missing_fsk + Episode mit missing_fsk
    const testDataMisch2 = {
        issues: [
            { type: "missing_age_rating", severity: "warning", path: "/Serien/My Show/tvshow.nfo", category: "serien" },
            { type: "missing_age_rating", severity: "warning", path: "/Serien/My Show/Season 1/S01E01.nfo", category: "serien" }
        ],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "missing_fsk",
                current_fsk: "",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "missing_fsk", current_fsk: "" }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataMisch2);

    // FSK bleibt im Detail bedienbar und in der Zusammenfassung ausdrücklich sichtbar.
    assert.ok(issuesEl.innerHTML.includes("Metadaten: prüfen"));
    assert.ok(issuesEl.innerHTML.includes("FSK: Serie + 1 Folge prüfen"));
    // Seriengruppenaktion vorhanden
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "show-group-fsk-btn", "/Serien/My Show"));
    // Einzel-FSK-Button für tvshow.nfo ausgeblendet
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show"));
    // Einzel-FSK-Button für Episode ausgeblendet
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));

    // 5. Episode mit unreadable NFO
    const unreadableKey = "health:unreadable_nfo:/Serien/My Show/Season 1/S01E01.nfo";
    const testDataUnreadable = {
        issues: [{ key: unreadableKey, type: "unreadable_nfo", severity: "critical", path: "/Serien/My Show/Season 1/S01E01.nfo", agent_path: "/Serien/My Show/Season 1", category: "serien" }],
        ignored_count: 0,
        media_structure: {
            series: [{
                name: "My Show",
                path: "/Serien/My Show",
                has_nfo: true,
                fsk_status: "healthy",
                current_fsk: "FSK 12",
                seasons: [{
                    name: "Season 1",
                    path: "/Serien/My Show/Season 1",
                    episodes: [
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "unreadable", current_fsk: "", issue_keys: [unreadableKey] }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataUnreadable);

    // Sichtbar
    assert.ok(issuesEl.innerHTML.includes("Episode 1"));
    assert.ok(issuesEl.innerHTML.includes("Metadaten: prüfen"));
    assert.ok(issuesEl.innerHTML.includes("FSK: 12"));
    // Label
    assert.ok(issuesEl.innerHTML.includes('class="text-danger"'));
    assert.ok(issuesEl.innerHTML.includes('NFO unlesbar'));
    // Kein FSK-Button, aber ein dateibezogener NFO-Agent.
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "health-nfo-agent", "/Serien/My Show/Season 1"));

    // Cleanup
    document.body.removeChild(container);
});

test('Film-Rendering in FSK Modal uses media_kind', async () => {
    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/Filme/Ein Film/movie.nfo", fingerprint: "abcd", status: "ready", media_kind: "movie", hierarchy: { show: "Ein Film (2024)" } }
            ],
            summary: { total: 1, ready: 1, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
        })
    };
    globalThis.openFskBatchModal([{path: "/Filme/Ein Film/movie.nfo", media_kind: "movie"}], "16", "single", "movie");
    await new Promise(r => setTimeout(r, 10));
    const container = document.getElementById("fsk-batch-tree-container");
    const html = container.innerHTML;
    assert.ok(html.includes("🎬 Filme"));
    assert.ok(html.includes("Ein Film (2024)"));
    assert.ok(!html.includes("📺 Serie:"));
    assert.strictEqual(document.getElementById("fsk-batch-modal-title").textContent, "FSK-Altersfreigabe setzen");
    assert.strictEqual(document.getElementById("fsk-batch-scope-field").style.display, "none");
    assert.ok(document.getElementById("btn-fsk-batch-confirm").innerHTML.includes("1 NFO auf FSK 16 ändern"));
});

test('Successful apply leaves one terminal action and refreshes health immediately', async () => {
    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = (url) => {
        if (url.includes("fsk-batch/preview")) {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    files: [{
                        path: "/Filme/Ein Film/movie.nfo",
                        fingerprint: "abcd",
                        status: "ready",
                        media_kind: "movie",
                        hierarchy: { show: "Ein Film (2024)" }
                    }],
                    summary: { total: 1, ready: 1, unchanged: 0, skipped_missing: 0, skipped_problematic: 0 }
                })
            };
        }
        if (url.includes("fsk-batch/apply")) {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    ok: true,
                    status: "success",
                    results: [{ path: "/Filme/Ein Film/movie.nfo", status: "success" }],
                    summary: { success: 1, failed: 0, unchanged: 0 }
                })
            };
        }
        if (url.includes("health-status")) {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    status: "done",
                    issues: [],
                    summary: { critical: 0, warning: 0, info: 0 },
                    ignored_count: 0,
                    media_structure: { series: [], movies: [] }
                })
            };
        }
        return null;
    };

    globalThis.openFskBatchModal([{ path: "/Filme/Ein Film/movie.nfo", media_kind: "movie" }], "12", "single", "movie");
    await new Promise(r => setTimeout(r, 10));
    await globalThis.applyFskBatch();

    assert.ok(globalThis.fetchRequests.some((request) => request.url.includes("/api/nas/health-status")));
    assert.strictEqual(document.getElementById("btn-fsk-batch-confirm").style.display, "none");
    assert.strictEqual(document.getElementById("btn-fsk-batch-refresh").style.display, "none");
    assert.strictEqual(document.getElementById("btn-fsk-batch-cancel").textContent, "Fertig");
});

test('NFO-Agent rendered in skipped_missing', async () => {
    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/Filme/Fehlend/movie.nfo", fingerprint: "abcd", status: "skipped_missing", media_kind: "movie", agent_path: "/Filme/Fehlend", hierarchy: {} }
            ],
            summary: { ready: 0, skipped_missing: 1 }
        })
    };
    globalThis.openFskBatchModal([{path: "/Filme/Fehlend/movie.nfo"}], "16");
    await new Promise(r => setTimeout(r, 10));
    const container = document.getElementById("fsk-batch-tree-container");
    const html = container.innerHTML;
    assert.ok(html.includes("Metadaten bearbeiten"));
    assert.ok(html.includes("/Filme/Fehlend"));
});

test('Fertig-Klick bei ready=0 schliesst Modal', async () => {
    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: "/test.nfo", fingerprint: "abcd", status: "unchanged", media_kind: "movie", hierarchy: {} }
            ],
            summary: { ready: 0, unchanged: 1 }
        })
    };
    globalThis.openFskBatchModal([{path: "/test.nfo"}], "16");
    await new Promise(r => setTimeout(r, 10));
    const btn = document.getElementById("btn-fsk-batch-confirm");
    btn.dispatchEvent({ type: 'click' });
    await new Promise(r => setTimeout(r, 10));
    const applyReq = globalThis.fetchRequests.find(req => req.url.includes("fsk-batch/apply"));
    assert.ok(!applyReq);
});

test('NFO Agent Lifecycle wertet done, error, cancelled und fehlende Queue-Jobs aus', async () => {
    const originalSetInterval = globalThis.setInterval;
    const originalClearInterval = globalThis.clearInterval;
    let intervalCallback = null;

    globalThis.setInterval = (callback) => {
        intervalCallback = callback;
        return 42;
    };
    globalThis.clearInterval = () => {};
    globalThis.bindNfoAgentEvents();
    globalThis.bindNfoAgentEvents();
    assert.strictEqual(
        document.getElementById("btn-nfo-agent-done").__listeners.click.length,
        1,
        "NFO-Agent events must not be bound twice"
    );

    const cases = [
        {
            status: "done",
            jobs: [{ id: "task-1", status: "done", progress: 100 }],
            expectsPreview: true,
            errorText: null
        },
        {
            status: "error",
            jobs: [{ id: "task-1", status: "error", message: "Metadata lookup failed" }],
            expectsPreview: false,
            errorText: "Fehler beim NFO-Agent: Metadata lookup failed"
        },
        {
            status: "cancelled",
            jobs: [{ id: "task-1", status: "cancelled" }],
            expectsPreview: false,
            errorText: "NFO-Agent wurde abgebrochen."
        },
        {
            status: "missing",
            jobs: [],
            expectsPreview: false,
            errorText: "Das Ergebnis des NFO-Agenten ist nicht mehr abrufbar."
        }
    ];

    try {
        for (const lifecycleCase of cases) {
            const modal = document.getElementById("modal-nfo-agent");
            modal.classList.add("active");
            modal.classList.remove("hidden");
            document.getElementById("modal-fsk-batch-preview").classList.add("active");
            document.getElementById("modal-fsk-batch-preview").classList.remove("hidden");
            document.getElementById("btn-nfo-agent-done").style.display = "none";
            document.getElementById("fsk-batch-error-inline").style.display = "none";
            document.getElementById("fsk-batch-error-inline").textContent = "";
            globalThis.wasFskModalOpenForNfoAgent = true;
            globalThis.nfoAgentJobSuccess = false;
            globalThis.nfoAgentJobErrorMsg = null;
            globalThis.fetchRequests = [];
            intervalCallback = null;
            globalThis.mockFetchResponse = (url) => ({
                ok: true,
                status: 200,
                json: async () => url === "/api/queue"
                    ? { jobs: lifecycleCase.jobs }
                    : { files: [], summary: { ready: 0 } }
            });

            globalThis.startNfoAgentLogStreaming("task-1");
            assert.strictEqual(typeof intervalCallback, "function", `${lifecycleCase.status}: polling interval missing`);
            intervalCallback();
            await new Promise(resolve => setTimeout(resolve, 0));

            assert.ok(
                globalThis.fetchRequests.some(request => request.url === "/api/queue"),
                `${lifecycleCase.status}: production queue endpoint was not polled`
            );
            assert.strictEqual(document.getElementById("btn-nfo-agent-done").style.display, "inline-flex");

            document.getElementById("btn-nfo-agent-done").dispatchEvent({ type: "click" });
            await new Promise(resolve => setTimeout(resolve, 0));

            const previewRequested = globalThis.fetchRequests.some(request => request.url.includes("fsk-batch/preview"));
            assert.strictEqual(previewRequested, lifecycleCase.expectsPreview, `${lifecycleCase.status}: preview result mismatch`);
            assert.ok(modal.classList.contains("hidden"), `${lifecycleCase.status}: agent modal stayed open`);

            const errorElement = document.getElementById("fsk-batch-error-inline");
            if (lifecycleCase.errorText) {
                assert.strictEqual(errorElement.style.display, "block");
                assert.strictEqual(errorElement.textContent, lifecycleCase.errorText);
            } else {
                assert.notStrictEqual(errorElement.style.display, "block");
            }
        }
    } finally {
        globalThis.setInterval = originalSetInterval;
        globalThis.clearInterval = originalClearInterval;
        globalThis.mockFetchResponse = null;
    }
});

test('Escaping-Sicherheit bei NFO-Agent-Event-Delegation', async () => {
    const problemPath = '/Serien/My Show/Season 1/Täst & "quoted" \'file\'.nfo';

    globalThis.fetchRequests = [];
    globalThis.mockFetchResponse = {
        ok: true,
        status: 200,
        json: () => Promise.resolve({
            files: [
                { path: problemPath, fingerprint: "abcd", status: "skipped_missing", media_kind: "movie", agent_path: problemPath, hierarchy: {} }
            ],
            summary: { ready: 0, skipped_missing: 1 }
        })
    };
    globalThis.openFskBatchModal([{path: problemPath}], "16");
    await new Promise(r => setTimeout(r, 10));

    const container = document.getElementById("fsk-batch-tree-container");
    const html = container.innerHTML;

    const escapedPath = problemPath.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#039;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    assert.ok(html.includes(`data-path="${escapedPath}"`), "The data-path must be properly escaped in the HTML output");

    const clickListenerCount = (globalThis.document.__listeners.click || []).length;
    globalThis.bindHealthActionEvents();
    globalThis.bindHealthActionEvents();
    assert.strictEqual(
        globalThis.document.__listeners.click.length,
        clickListenerCount + 1,
        "Health action delegation must not be bound twice"
    );
    const button = createMockElement();
    button.setAttribute("data-path", problemPath);
    globalThis.fetchRequests = [];
    globalThis.document.dispatchEvent({
        type: "click",
        target: {
            closest: selector => selector === ".health-nfo-agent" ? button : null
        }
    });

    const fetchCall = globalThis.fetchRequests.find(req => req.url.includes("scan-project?project="));
    assert.ok(fetchCall, "A fetch call should have been made to open the NFO Agent modal");
    const encodedPath = encodeURIComponent(problemPath);
    assert.ok(fetchCall.url.includes(`project=${encodedPath}`), "Event delegation should pass the exact unescaped path to openNfoAgentModal, which then encodes it for the request");
});

test('NFO Agent switches between entry context and whole-series editing', () => {
    const originalQuerySelectorAll = globalThis.document.querySelectorAll;
    const mediaType = document.getElementById("nfo-agent-media-type");
    mediaType.value = "tvshow";
    globalThis.setNfoAgentScanData({
        main_nfo_status: { exists: true },
        file_nfo_statuses: {}
    });

    const createEpisodeRow = (file, mapping) => {
        const row = createMockElement();
        const select = createMockElement();
        const overrideContainer = createMockElement();
        select.value = "skip";
        row.setAttribute("data-file", file);
        row.setAttribute("data-default-mapping", mapping);
        row.querySelector = (selector) => selector === ".nfo-agent-ep-mapping-select" ? select : overrideContainer;
        return { row, select, overrideContainer };
    };
    const first = createEpisodeRow("Show S01E01.mkv", "S1E1");
    const second = createEpisodeRow("Show S01E02.mkv", "S1E2");
    globalThis.document.querySelectorAll = (selector) => selector === "#nfo-agent-episodes-list .nfo-episode-row"
        ? [first.row, second.row]
        : [];

    globalThis.nfoAgentEditContext = { originMode: "episode", mode: "episode", episodeFile: "Show S01E02.nfo" };
    globalThis.renderNfoAgentFiles({
        files: [],
        main_nfo_status: { exists: true, parseable: true, complete: true },
        file_nfo_statuses: {}
    });
    globalThis.applyNfoAgentEditMode();

    assert.strictEqual(document.getElementById("nfo-agent-edit-mode-title").textContent, "Folge S01E02 bearbeiten");
    assert.strictEqual(document.getElementById("nfo-agent-main-nfo-section").style.display, "none");
    assert.strictEqual(first.row.style.display, "none");
    assert.strictEqual(second.row.style.display, "flex");
    assert.strictEqual(second.select.value, "S1E2");
    assert.strictEqual(document.getElementById("btn-nfo-agent-edit-whole-series").style.display, "inline-flex");

    globalThis.setNfoAgentEditMode("full");
    assert.strictEqual(document.getElementById("nfo-agent-edit-mode-title").textContent, "Ganze Serie bearbeiten");
    assert.strictEqual(document.getElementById("nfo-agent-main-nfo-section").style.display, "block");
    assert.strictEqual(first.row.style.display, "flex");
    assert.strictEqual(document.getElementById("btn-nfo-agent-edit-back").style.display, "inline-flex");

    globalThis.setNfoAgentEditMode(globalThis.nfoAgentEditContext.originMode);
    assert.strictEqual(document.getElementById("nfo-agent-edit-mode-title").textContent, "Folge S01E02 bearbeiten");

    globalThis.document.querySelectorAll = originalQuerySelectorAll;
});

test('NFO Agent episode mode submits only the selected episode', () => {
    const originalQuerySelectorAll = globalThis.document.querySelectorAll;
    const originalQuerySelector = globalThis.document.querySelector;
    globalThis.CSS = { escape: value => value };

    const values = {
        "nfo-agent-provider": "manual",
        "nfo-agent-media-type": "tvshow",
        "nfo-agent-metadata-id": "",
        "nfo-agent-season": "1",
        "nfo-agent-show-title": "Show",
        "nfo-agent-show-year": "2026",
        "nfo-agent-show-plot": "Plot",
        "nfo-agent-show-genres": "Drama",
        "nfo-agent-show-fsk": "12"
    };
    Object.entries(values).forEach(([id, value]) => { document.getElementById(id).value = value; });
    document.getElementById("nfo-agent-overwrite-nfo").checked = false;
    document.getElementById("nfo-agent-show-nfo-action").value = "process";

    const createMapping = (file, value) => {
        const element = createMockElement();
        element.value = value;
        element.setAttribute("data-file", file);
        return element;
    };
    const createTitle = (file, value) => {
        const element = createMockElement();
        element.value = value;
        element.setAttribute("data-file", file);
        return element;
    };
    const mappings = [createMapping("Show S01E01.mkv", "S1E1"), createMapping("Show S01E02.mkv", "S1E2")];
    const titles = [createTitle("Show S01E01.mkv", "First changed"), createTitle("Show S01E02.mkv", "Second changed")];
    const plotByFile = Object.fromEntries(titles.map(input => {
        const element = createMockElement();
        element.value = `${input.value} plot`;
        return [input.getAttribute("data-file"), element];
    }));
    const fskByFile = Object.fromEntries(titles.map(input => {
        const element = createMockElement();
        element.value = "12";
        return [input.getAttribute("data-file"), element];
    }));

    globalThis.document.querySelectorAll = (selector) => {
        if (selector === ".nfo-agent-ep-mapping-select") return mappings;
        if (selector === ".nfo-agent-ep-override-title") return titles;
        return [];
    };
    globalThis.document.querySelector = (selector) => {
        const file = selector.match(/data-file="([^"]+)"/)?.[1];
        return selector.includes("override-plot") ? plotByFile[file] : fskByFile[file];
    };

    globalThis.setNfoAgentCurrentPath("/media/Serien/Show/Staffel 1");
    globalThis.setNfoAgentScanData({
        metadata_name: "Show",
        metadata_year: "2026",
        metadata_plot: "Plot",
        metadata_genres: ["Drama"],
        metadata_fsk: "12",
        main_nfo_status: { exists: true, fingerprint: { hash: "main" } },
        file_nfo_statuses: {
            "Show S01E01.mkv": { title: "First", plot: "First plot", fsk: "6", fingerprint: { hash: "one" } },
            "Show S01E02.mkv": { title: "Second", plot: "Second plot", fsk: "6", fingerprint: { hash: "two" } }
        }
    });
    globalThis.nfoAgentEditContext = { originMode: "episode", mode: "episode", episodeFile: "Show S01E02.nfo" };
    globalThis.fetchRequests = [];

    globalThis.submitNfoAgentJob();

    const request = globalThis.fetchRequests.find(item => item.url === "/api/process");
    assert.ok(request);
    const payload = JSON.parse(request.options.body);
    assert.strictEqual(payload.write_show_nfo, false);
    assert.deepStrictEqual(payload.mappings, { "Show S01E02.mkv": "S1E2" });
    assert.deepStrictEqual(payload.episode_fingerprints, { "Show S01E02.mkv": { hash: "two" } });
    assert.deepStrictEqual(Object.keys(payload.nfo_overrides.episodes), ["Show S01E02.mkv"]);
    assert.deepStrictEqual(payload.nfo_overrides.show, {});

    globalThis.nfoAgentEditContext = { originMode: "series", mode: "series", episodeFile: "" };
    globalThis.fetchRequests = [];
    globalThis.submitNfoAgentJob();
    const seriesRequest = globalThis.fetchRequests.find(item => item.url === "/api/process");
    const seriesPayload = JSON.parse(seriesRequest.options.body);
    assert.strictEqual(seriesPayload.write_show_nfo, true);
    assert.deepStrictEqual(seriesPayload.mappings, {});
    assert.deepStrictEqual(seriesPayload.nfo_overrides.episodes, {});

    globalThis.document.querySelectorAll = originalQuerySelectorAll;
    globalThis.document.querySelector = originalQuerySelector;
});

test('NFO Agent uses concise mode controls and clear missing-source copy', () => {
    const indexHtml = fs.readFileSync(path.resolve(__dirname, '../../gui/static/index.html'), 'utf8');
    assert.ok(indexHtml.includes('id="btn-nfo-agent-edit-whole-series"'));
    assert.ok(indexHtml.includes('>Ganze Serie bearbeiten</button>'));
    assert.ok(indexHtml.includes('>Zur vorherigen Ansicht</button>'));
    assert.ok(!indexHtml.includes("Änderungen werden nur auf ausgewählte"));
    assert.ok(!indexHtml.includes(">nicht verfügbar</small>"));
    assert.ok(appJsContent.includes('metadata_provider_missing: "Metadatensuche liefert keine Angabe"'));
});

test('Type-oriented episode findings preserve the focused episode context', () => {
    const issuesEl = document.getElementById("health-issues");
    globalThis.healthGroupMode = "type";
    globalThis.renderHealthStatus({
        status: "done",
        issues: [{
            key: "episode-incomplete",
            type: "incomplete_nfo",
            severity: "warning",
            category: "Serien",
            path: "/Serien/Show/Staffel 1/Show S01E02.nfo",
            agent_path: "/Serien/Show/Staffel 1",
            media_kind: "episode",
            episode_file: "Show S01E02.mkv",
            message: "Episoden-NFO unvollständig"
        }],
        summary: { critical: 0, warning: 1, info: 0 },
        ignored_count: 0,
        media_structure: { series: [], movies: [] }
    });

    assert.ok(issuesEl.innerHTML.includes('data-path="/Serien/Show/Staffel 1"'));
    assert.ok(issuesEl.innerHTML.includes('data-edit-mode="episode"'));
    assert.ok(issuesEl.innerHTML.includes('data-episode-file="Show S01E02.mkv"'));
});
