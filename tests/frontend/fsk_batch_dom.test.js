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
        if (globalThis.mockFetchResponse) {
            resolveFn(globalThis.mockFetchResponse);
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
`;

eval(appJsContent);
globalThis.document.dispatchEvent({ type: 'DOMContentLoaded' });
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
    console.log("errorEl.textContent after apply:", errorEl.textContent);

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

    console.log("errorEl.textContent after preview load:", errorEl.textContent);

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
    const testData = {
        issues: [{ type: "nfo_missing", severity: "danger", path: "/Serien/My Show/Season 1/S01E01.mkv", category: "serien" }],
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
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.mkv", fsk_status: "nfo_missing", current_fsk: "" }
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
    // Betroffener Episodenzähler muss exakt "1 von 1 Ep. betroffen" sein
    assert.ok(issuesEl.innerHTML.includes("1 von 1 Ep. betroffen"));
    // FSK-Label muss rot ("text-danger") sein und "NFO fehlt" heißen
    assert.ok(issuesEl.innerHTML.includes('class="text-danger"'));
    assert.ok(issuesEl.innerHTML.includes('NFO fehlt'));
    // Kein Einzelbutton für diese Episode
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.mkv"));

    // 2. Mehrere fehlende NFOs erzeugen keine Gruppenaktionen
    const testDataMultiple = {
        issues: [
            { type: "nfo_missing", severity: "danger", path: "/Serien/My Show/Season 1/S01E01.mkv", category: "serien" },
            { type: "nfo_missing", severity: "danger", path: "/Serien/My Show/Season 1/S01E02.mkv", category: "serien" }
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
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.mkv", fsk_status: "nfo_missing", current_fsk: "" },
                        { name: "Episode 2", path: "/Serien/My Show/Season 1/S01E02.mkv", fsk_status: "nfo_missing", current_fsk: "" }
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

    // Seriengruppenaktion vorhanden
    assert.ok(hasButtonWithClassAndPath(issuesEl.innerHTML, "show-group-fsk-btn", "/Serien/My Show"));
    // Einzel-FSK-Button für tvshow.nfo ausgeblendet
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show"));
    // Einzel-FSK-Button für Episode ausgeblendet
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));

    // 5. Episode mit unreadable NFO
    const testDataUnreadable = {
        issues: [{ type: "unreadable_nfo", severity: "danger", path: "/Serien/My Show/Season 1/S01E01.nfo", category: "serien" }],
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
                        { name: "Episode 1", path: "/Serien/My Show/Season 1/S01E01.nfo", fsk_status: "unreadable", current_fsk: "" }
                    ]
                }]
            }],
            movies: []
        }
    };

    globalThis.renderHealthStatus(testDataUnreadable);

    // Sichtbar
    assert.ok(issuesEl.innerHTML.includes("Episode 1"));
    assert.ok(issuesEl.innerHTML.includes("1 von 1 Ep. betroffen"));
    // Label
    assert.ok(issuesEl.innerHTML.includes('class="text-danger"'));
    assert.ok(issuesEl.innerHTML.includes('NFO unlesbar'));
    // Kein Button
    assert.ok(!hasButtonWithClassAndPath(issuesEl.innerHTML, "health-fix-fsk", "/Serien/My Show/Season 1/S01E01.nfo"));

    // Cleanup
    document.body.removeChild(container);
});
