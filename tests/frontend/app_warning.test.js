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
        dataset: {},
        __listeners: {},
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
        contains: () => true,
        appendChild: () => {},
        addEventListener(type) {
            this.__listeners[type] = (this.__listeners[type] || 0) + 1;
        },
        cloneNode() {
            return createMockElement();
        },
        replaceWith() {}
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
globalThis.renderQueue = renderQueue;
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

test('renderNormalizePlan - empty plan renders neutral empty state without emoji', () => {
    const statusEl = globalThis.document.getElementById("normalize-status");
    const planEl = globalThis.document.getElementById("normalize-plan");
    statusEl.textContent = "Alter Status";
    planEl.innerHTML = "<div>Alter Plan</div>";

    globalThis.renderNormalizePlan([]);

    assert.equal(statusEl.textContent, "Keine Auffälligkeiten gefunden.");
    assert.equal(planEl.innerHTML, "");
    assert.ok(!statusEl.textContent.includes("🎉"));
    assert.ok(!statusEl.textContent.includes("Alles sauber"));
});

test('renderQueue - pipeline step message uses existing HTML escaping helper', () => {
    const listEl = globalThis.document.getElementById("queue-list");
    const badgeEl = globalThis.document.getElementById("queue-badge");
    const headerBadgeEl = globalThis.document.getElementById("header-queue-badge");
    listEl.innerHTML = "";
    listEl.appendChild = (child) => {
        listEl.innerHTML += child.innerHTML || "";
    };
    badgeEl.textContent = "";
    headerBadgeEl.textContent = "";

    const jobs = [{
        id: "job-queue-message",
        name: "Queue Message Movie",
        type: "movie",
        status: "running",
        progress: 42,
        message: "Upload läuft",
        pipeline: {
            metadata: { status: "done", progress: 100 },
            convert: { status: "done", progress: 100 },
            nas: { status: "done", progress: 100, message: "Auf NAS gespeichert" },
            pcloud: { status: "running", progress: 0, message: '<script>alert("x")</script>' }
        }
    }];

    assert.doesNotThrow(() => globalThis.renderQueue(jobs));
    assert.ok(listEl.innerHTML.includes("alert"));
    assert.ok(listEl.innerHTML.includes("script"));
    assert.ok(!listEl.innerHTML.includes("<script"));
    assert.ok(!listEl.innerHTML.includes('<script>alert("x")</script>'));
});

test('renderHealthStatus - severity grouping renders severity groups and no checkboxes', () => {
    globalThis.window.healthGroupMode = "severity";
    const issuesEl = globalThis.document.getElementById("health-issues");
    issuesEl.innerHTML = "";

    const data = {
        status: "done",
        message: "Scan abgeschlossen",
        issues: [
            { key: "1", type: "missing_nfo", category: "Filme", severity: "critical", message: "Fehlende NFO", path: "/path/to/movie" }
        ],
        finished_at: 1719816000
    };

    globalThis.renderHealthStatus(data);

    // Sollte Details für Schweregrad rendern
    assert.ok(issuesEl.innerHTML.includes('data-sev="critical"'));
    // Sollte keinen Checkbox-Gruppenselector rendern
    assert.ok(!issuesEl.innerHTML.includes('class="health-group-select-all"'));
});

test('renderHealthStatus - type grouping renders type groups, checkboxes and tool-connectors', () => {
    globalThis.window.healthGroupMode = "type";
    const issuesEl = globalThis.document.getElementById("health-issues");
    issuesEl.innerHTML = "";

    const data = {
        status: "done",
        message: "Scan abgeschlossen",
        issues: [
            { key: "1", type: "missing_nfo", category: "Filme", severity: "critical", message: "Fehlende NFO", path: "/path/to/movie" }
        ],
        finished_at: 1719816000
    };

    globalThis.renderHealthStatus(data);

    // Sollte Details für Fehlertyp rendern
    assert.ok(issuesEl.innerHTML.includes('data-type-id="missing_nfo"'));
    // Sollte Checkboxen zur Sammel-Auswahl rendern
    assert.ok(issuesEl.innerHTML.includes('class="health-group-select-all"'));
    assert.ok(issuesEl.innerHTML.includes('class="health-item-select"'));
    // Sollte Empfehlung anzeigen
    assert.ok(issuesEl.innerHTML.includes("Empfehlung:"));
    // Sollte pro Befund einen NFO-Agent-Button rendern (kein Batch-Button mehr,
    // da jede Serie eine eigene Metadatenquelle/ID braucht)
    assert.ok(issuesEl.innerHTML.includes('health-nfo-agent'));
    assert.ok(!issuesEl.innerHTML.includes('data-tool="tool_nfo_agent"'));
});

test('renderHealthStatus - only nested_duplicate / structure issues displays tab specific empty state on media tab', () => {
    globalThis.window.healthGroupMode = "type";

    const issuesEl = globalThis.document.getElementById("health-issues");
    const structureIssuesEl = globalThis.document.getElementById("health-issues-structure");
    const structureContainer = globalThis.document.getElementById("structure-health-issues-container");

    issuesEl.innerHTML = "";
    structureIssuesEl.innerHTML = "";
    structureContainer.style.display = "none";

    const data = {
        status: "done",
        message: "Scan abgeschlossen",
        issues: [
            { key: "1", type: "nested_duplicate", category: "Filme", severity: "warning", message: "Verschachtelter Ordner", path: "/path/to/movie" }
        ],
        finished_at: 1719816000
    };

    globalThis.renderHealthStatus(data);

    // Der Medien-Sub-Tab darf keine globale Entwarnung anzeigen, sondern den Hinweis auf den Struktur-Tab
    assert.ok(issuesEl.innerHTML.includes("Keine Auffälligkeiten für einzelne Medien. Strukturprobleme findest du im Tab Struktur."));
    assert.ok(!issuesEl.innerHTML.includes("Keine Auffälligkeiten gefunden. 🎉"));

    // Der Struktur-Sub-Tab sollte das Problem gerendert haben
    assert.ok(structureIssuesEl.innerHTML.includes("Verschachtelter Ordner"));
    // Der Struktur-Container sollte eingeblendet sein
    assert.strictEqual(structureContainer.style.display, "block");

    // Neue Buttons müssen gerendert werden
    assert.ok(structureIssuesEl.innerHTML.includes('class="btn btn-secondary btn-sm health-structure-preview"'));
    assert.ok(structureIssuesEl.innerHTML.includes('class="btn btn-primary btn-sm health-structure-apply"'));
    // Alter Button darf nicht mehr gerendert werden
    assert.ok(!structureIssuesEl.innerHTML.includes('health-fix-flatten'));
});

test('renderHealthStatus - structure-only result wires structure batch button', () => {
    globalThis.window.healthGroupMode = "type";

    elements["btn-structure-batch-check"] = createMockElement();
    elements["view-library"] = createMockElement();
    const issuesEl = globalThis.document.getElementById("health-issues");
    const structureIssuesEl = globalThis.document.getElementById("health-issues-structure");
    const structureContainer = globalThis.document.getElementById("structure-health-issues-container");
    const libraryView = globalThis.document.getElementById("view-library");

    issuesEl.innerHTML = "";
    structureIssuesEl.innerHTML = "";
    structureContainer.style.display = "none";
    libraryView.dataset = {};
    libraryView.__listeners = {};

    const data = {
        status: "done",
        message: "Scan abgeschlossen",
        issues: [
            { key: "1", type: "nested_duplicate", category: "Filme", severity: "warning", message: "Verschachtelter Ordner", path: "/path/to/movie-a" },
            { key: "2", type: "genre_container", category: "Filme", severity: "warning", message: "Sammelordner", path: "/path/to/action" }
        ],
        finished_at: 1719816000
    };

    globalThis.renderHealthStatus(data);

    assert.ok(structureIssuesEl.innerHTML.includes('id="btn-structure-batch-check"'));
    assert.strictEqual(libraryView.dataset.structureFixDelegated, "true");
    assert.ok(libraryView.__listeners.click > 0);
});
