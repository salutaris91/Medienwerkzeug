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
    return {
        textContent: "",
        innerHTML: "",
        style: {},
        classList: {
            add: (c) => classSet.add(c),
            remove: (c) => classSet.delete(c),
            contains: (c) => classSet.has(c)
        },
        closest() {
            return createMockElement();
        },
        querySelectorAll: () => [],
        querySelector: () => null,
        appendChild: () => {}
    };
}

const elements = {};
globalThis.document = {
    documentElement: {
        style: {
            setProperty: () => {},
            removeProperty: () => {}
        }
    },
    getElementById(id) {
        if (!elements[id]) {
            elements[id] = createMockElement();
        }
        return elements[id];
    },
    createElement() {
        return createMockElement();
    },
    querySelectorAll() {
        return [];
    },
    querySelector() {
        return null;
    },
    addEventListener() {
        // Ignoriere Event-Registrierungen in der Testumgebung
    }
};

globalThis.window = {
    scrollTo: () => {},
    addEventListener: () => {}
};

globalThis.HEALTH_SEVERITY = {
    critical: { icon: "❌", label: "Kritisch", color: "#ef4444" },
    warning: { icon: "⚠️", label: "Warnung", color: "#f59e0b" },
    info: { icon: "ℹ️", label: "Info", color: "#3b82f6" }
};

globalThis.escapeHTML = (str) => str;
globalThis.renderIgnoredFooter = () => "";
globalThis.wireRestoreAll = () => {};

// Mock relative fetch during load
const originalFetch = globalThis.fetch;
globalThis.fetch = (url, options) => {
    if (typeof url === "string" && url.startsWith("/")) {
        return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ capabilities: { open_local_folder: true } })
        });
    }
    if (originalFetch) {
        return originalFetch(url, options);
    }
    return Promise.reject("Fetch mock error");
};

// Lade und evaluiere app.js
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
const appJsContent = fs.readFileSync(appJsPath, 'utf8');

// Wir entfernen nur native Browser-Imports, die in Node.js eval() einen Syntaxfehler werfen.
let cleanAppJs = appJsContent.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, "");

// Exponiere die Funktionen fuer die Testumgebung global
cleanAppJs += `
globalThis.renderHealthStatus = renderHealthStatus;
globalThis.renderDuplicateStatus = renderDuplicateStatus;
globalThis.loadNormalizePreview = loadNormalizePreview;
globalThis.renderNormalizePlan = renderNormalizePlan;
`;

eval(cleanAppJs);
globalThis.fetch = originalFetch;

test('renderHealthStatus - warning state renders warning alert, not success', () => {
    // Zurücksetzen
    const issuesEl = globalThis.document.getElementById("health-issues");
    const statusEl = globalThis.document.getElementById("health-scan-status");
    issuesEl.innerHTML = "";
    statusEl.textContent = "";

    const data = {
        status: "warning",
        message: "Scan nicht aussagekräftig",
        issues: []
    };

    globalThis.renderHealthStatus(data);

    assert.ok(statusEl.textContent.includes("Warnung:"));
    assert.ok(issuesEl.innerHTML.includes("Scan nicht aussagekräftig: keine Bibliotheksordner gefunden."));
    assert.ok(!issuesEl.innerHTML.includes("Keine Auffälligkeiten gefunden"));
});

test('renderDuplicateStatus - warning state renders warning alert, not success', () => {
    const groupsEl = globalThis.document.getElementById("duplicate-groups");
    const statusEl = globalThis.document.getElementById("duplicate-scan-status");
    groupsEl.innerHTML = "";
    statusEl.textContent = "";

    const data = {
        status: "warning",
        message: "Scan nicht aussagekräftig",
        groups: []
    };

    globalThis.renderDuplicateStatus(data);

    assert.ok(statusEl.textContent.includes("Warnung:"));
    assert.ok(groupsEl.innerHTML.includes("Scan nicht aussagekräftig: keine Bibliotheksordner gefunden."));
    assert.ok(!groupsEl.innerHTML.includes("Keine Duplikate gefunden"));
});

test('loadNormalizePreview - status 400 shows warning alert, not success', async () => {
    const statusEl = globalThis.document.getElementById("normalize-status");
    const planEl = globalThis.document.getElementById("normalize-plan");
    statusEl.innerHTML = "";
    planEl.innerHTML = "";

    // Mock global fetch for preview endpoint returning 400
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (url) => {
        if (url === "/api/nas/normalize-films/preview") {
            return Promise.resolve({
                ok: false,
                status: 400,
                json: () => Promise.resolve({ error: "Keine Bibliotheksordner gefunden." })
            });
        }
        return Promise.reject("Unexpected fetch");
    };

    try {
        await globalThis.loadNormalizePreview();

        assert.ok(statusEl.innerHTML.includes("Warnung:"));
        assert.ok(statusEl.innerHTML.includes("Keine Bibliotheksordner gefunden."));
        assert.ok(planEl.innerHTML.includes("Scan nicht aussagekräftig: keine Bibliotheksordner gefunden."));
        assert.ok(!statusEl.innerHTML.includes("Alles sauber"));
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('renderNormalizePlan - 1 item renders Singular "Vorschlag"', () => {
    const statusEl = globalThis.document.getElementById("normalize-status");
    statusEl.textContent = "";

    const plan = [
        { label: "Test Movie 1", kind: "genre", conflict: false }
    ];

    globalThis.renderNormalizePlan(plan);

    assert.ok(statusEl.textContent.includes("1 Vorschlag"));
    assert.ok(!statusEl.textContent.includes("Vorschläge"));
});

test('renderNormalizePlan - 2 items renders Plural "Vorschläge"', () => {
    const statusEl = globalThis.document.getElementById("normalize-status");
    statusEl.textContent = "";

    const plan = [
        { label: "Test Movie 1", kind: "genre", conflict: false },
        { label: "Test Movie 2", kind: "lose", conflict: false }
    ];

    globalThis.renderNormalizePlan(plan);

    assert.ok(statusEl.textContent.includes("2 Vorschläge"));
    assert.ok(!statusEl.textContent.includes("Vorschlag "));
});
