import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
const indexHtmlPath = path.resolve(__dirname, '../../gui/static/index.html');

// In-memory sessionStorage mock
let sessionStore = {};
const mockSessionStorage = {
    getItem: (key) => (key in sessionStore ? sessionStore[key] : null),
    setItem: (key, val) => { sessionStore[key] = String(val); },
    removeItem: (key) => { delete sessionStore[key]; },
    clear: () => { sessionStore = {}; }
};

// Simple DOM element mock
function createMockElement(tagName = 'div', attributes = {}) {
    const classSet = new Set();
    const listeners = {};
    const children = [];
    const dataset = {};
    const attrs = { ...attributes };

    let innerHtmlVal = '';

    const el = {
        tagName: tagName.toUpperCase(),
        id: attributes.id || '',
        className: attributes.class || attributes.className || '',
        value: '',
        checked: false,
        textContent: '',
        get innerHTML() {
            return innerHtmlVal;
        },
        set innerHTML(val) {
            innerHtmlVal = String(val);
            if (val === '') {
                children.length = 0;
            }
        },
        style: {},
        dataset,
        __listeners: listeners,
        __children: children,
        classList: {
            add: (cls) => classSet.add(cls),
            remove: (cls) => classSet.delete(cls),
            contains: (cls) => classSet.has(cls)
        },
        setAttribute: (name, val) => {
            attrs[name] = String(val);
            if (name === 'class' || name === 'className') {
                el.className = String(val);
            }
            if (name.startsWith('data-')) {
                dataset[name.slice(5)] = String(val);
            }
        },
        getAttribute: (name) => attrs[name] || null,
        removeAttribute: (name) => {
            delete attrs[name];
            if (name.startsWith('data-')) {
                delete dataset[name.slice(5)];
            }
        },
        hasAttribute: (name) => name in attrs,
        addEventListener: (event, handler) => {
            if (!listeners[event]) listeners[event] = [];
            listeners[event].push(handler);
        },
        click: () => {
            if (listeners['click']) {
                listeners['click'].forEach(h => h.call(el, { type: 'click', target: el }));
            }
            if (typeof el.onclick === 'function') {
                el.onclick.call(el, { type: 'click', target: el });
            }
        },
        querySelector: (sel) => {
            if (sel.startsWith('.')) {
                const cls = sel.slice(1);
                for (const c of children) {
                    if (c.className && c.className.split(/\s+/).includes(cls)) return c;
                    const nested = c.querySelector(sel);
                    if (nested) return nested;
                }
            }
            return null;
        },
        querySelectorAll: (sel) => {
            const results = [];
            if (sel.startsWith('.')) {
                const cls = sel.slice(1);
                for (const c of children) {
                    if (c.className && c.className.split(/\s+/).includes(cls)) results.push(c);
                    results.push(...c.querySelectorAll(sel));
                }
            }
            return results;
        },
        appendChild: (child) => {
            children.push(child);
        }
    };

    if (attributes['data-field']) {
        el.dataset.field = attributes['data-field'];
    }

    return el;
}

// Setup environment and eval app.js
function setupEnvironment() {
    globalThis.sessionStorage = mockSessionStorage;
    mockSessionStorage.clear();

    globalThis.window = {
        fetch: (url, options) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
        scrollTo: () => {},
        addEventListener: () => {}
    };

    globalThis.fetch = globalThis.window.fetch;

    globalThis.formatBytes = function (bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = 2;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    };

    globalThis.escapeHTML = function (str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };

    globalThis.configureSmartInboxButton = () => {};
    globalThis.activeProjectsProcessing = new Set();
    globalThis.deleteProject = () => {};

    // Setup mock document
    const elementsById = {};

    const cardSmartInbox = createMockElement('div', { id: 'card-smart-inbox' });
    const smartInboxList = createMockElement('div', { id: 'smart-inbox-list' });
    const sortBar = createMockElement('div', { id: 'smart-inbox-sort-bar', role: 'toolbar' });

    const btnName = createMockElement('button', { class: 'btn btn-secondary btn-xs smart-inbox-sort-btn', 'data-field': 'name', 'aria-pressed': 'false' });
    btnName.className = 'smart-inbox-sort-btn';
    btnName.textContent = 'Name';

    const btnDate = createMockElement('button', { class: 'btn btn-secondary btn-xs smart-inbox-sort-btn', 'data-field': 'date', 'aria-pressed': 'false' });
    btnDate.className = 'smart-inbox-sort-btn';
    btnDate.textContent = 'Datum';

    const btnSize = createMockElement('button', { class: 'btn btn-secondary btn-xs smart-inbox-sort-btn', 'data-field': 'size', 'aria-pressed': 'false' });
    btnSize.className = 'smart-inbox-sort-btn';
    btnSize.textContent = 'Größe';

    sortBar.appendChild(btnName);
    sortBar.appendChild(btnDate);
    sortBar.appendChild(btnSize);

    elementsById['card-smart-inbox'] = cardSmartInbox;
    elementsById['smart-inbox-list'] = smartInboxList;
    elementsById['smart-inbox-sort-bar'] = sortBar;

    globalThis.document = {
        cookie: '',
        documentElement: {
            style: {
                setProperty: () => {},
                removeProperty: () => {}
            }
        },
        getElementById: (id) => {
            if (!elementsById[id]) {
                elementsById[id] = createMockElement('div', { id });
            }
            return elementsById[id];
        },
        createElement: (tag) => createMockElement(tag),
        querySelectorAll: (sel) => {
            if (sel === '#smart-inbox-list .smart-inbox-item') {
                return smartInboxList.querySelectorAll('.smart-inbox-item');
            }
            return [];
        },
        querySelector: (sel) => null,
        addEventListener: () => {}
    };

    const appJsContent = fs.readFileSync(appJsPath, 'utf8');
    let cleanAppJs = appJsContent.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, "");

    cleanAppJs += `
globalThis.sortInboxSuggestions = sortInboxSuggestions;
globalThis.getInboxSortState = getInboxSortState;
globalThis.setInboxSortState = setInboxSortState;
globalThis.formatDateDe = formatDateDe;
globalThis.renderSmartInboxList = renderSmartInboxList;
globalThis.updateSmartInboxSortBarUI = updateSmartInboxSortBarUI;
globalThis.initSmartInboxSortBar = initSmartInboxSortBar;
`;

    eval(cleanAppJs);

    return {
        cardSmartInbox,
        smartInboxList,
        sortBar,
        btnName,
        btnDate,
        btnSize
    };
}

// --------------------------------------------------------------------------
// AK3: Pure function sortInboxSuggestions
// --------------------------------------------------------------------------
test('AK3: sortInboxSuggestions sorts by name using German numeric/base localeCompare', () => {
    setupEnvironment();
    const items = [
        { project: 'Show.S01E10' },
        { project: 'Show.S01E2' },
        { project: 'Bahn' },
        { project: 'Ärger' }
    ];

    const sortedAsc = globalThis.sortInboxSuggestions(items, 'name', 'asc');
    // Numeric: S01E2 before S01E10; German locale: Ärger before Bahn
    assert.strictEqual(sortedAsc[0].project, 'Ärger');
    assert.strictEqual(sortedAsc[1].project, 'Bahn');
    assert.strictEqual(sortedAsc[2].project, 'Show.S01E2');
    assert.strictEqual(sortedAsc[3].project, 'Show.S01E10');

    const sortedDesc = globalThis.sortInboxSuggestions(items, 'name', 'desc');
    assert.strictEqual(sortedDesc[0].project, 'Show.S01E10');
    assert.strictEqual(sortedDesc[1].project, 'Show.S01E2');
    assert.strictEqual(sortedDesc[2].project, 'Bahn');
    assert.strictEqual(sortedDesc[3].project, 'Ärger');
});

test('AK3: sortInboxSuggestions sorts by date (modified_at) and places null at the end for BOTH asc and desc', () => {
    setupEnvironment();
    const items = [
        { project: 'Middle', modified_at: 1700000500 },
        { project: 'NoDateB', modified_at: null },
        { project: 'Oldest', modified_at: 1700000100 },
        { project: 'Newest', modified_at: 1700000900 },
        { project: 'NoDateA', modified_at: null }
    ];

    const sortedAsc = globalThis.sortInboxSuggestions(items, 'date', 'asc');
    assert.strictEqual(sortedAsc[0].project, 'Oldest');
    assert.strictEqual(sortedAsc[1].project, 'Middle');
    assert.strictEqual(sortedAsc[2].project, 'Newest');
    // null entries at end, tied by project name ascending
    assert.strictEqual(sortedAsc[3].project, 'NoDateA');
    assert.strictEqual(sortedAsc[4].project, 'NoDateB');

    const sortedDesc = globalThis.sortInboxSuggestions(items, 'date', 'desc');
    assert.strictEqual(sortedDesc[0].project, 'Newest');
    assert.strictEqual(sortedDesc[1].project, 'Middle');
    assert.strictEqual(sortedDesc[2].project, 'Oldest');
    // null entries still at end for desc
    assert.strictEqual(sortedDesc[3].project, 'NoDateA');
    assert.strictEqual(sortedDesc[4].project, 'NoDateB');
});

test('AK3: sortInboxSuggestions sorts by size (total_size) and places null at the end for BOTH directions', () => {
    setupEnvironment();
    const items = [
        { project: 'Medium', total_size: 5000 },
        { project: 'NoSize', total_size: null },
        { project: 'Small', total_size: 1000 },
        { project: 'Large', total_size: 9000 }
    ];

    const sortedAsc = globalThis.sortInboxSuggestions(items, 'size', 'asc');
    assert.strictEqual(sortedAsc[0].project, 'Small');
    assert.strictEqual(sortedAsc[1].project, 'Medium');
    assert.strictEqual(sortedAsc[2].project, 'Large');
    assert.strictEqual(sortedAsc[3].project, 'NoSize');

    const sortedDesc = globalThis.sortInboxSuggestions(items, 'size', 'desc');
    assert.strictEqual(sortedDesc[0].project, 'Large');
    assert.strictEqual(sortedDesc[1].project, 'Medium');
    assert.strictEqual(sortedDesc[2].project, 'Small');
    assert.strictEqual(sortedDesc[3].project, 'NoSize');
});

test('AK3: sortInboxSuggestions resolves ties deterministically by project name', () => {
    setupEnvironment();
    const items = [
        { project: 'Zebra', modified_at: 1700000000, total_size: 2000 },
        { project: 'Alpha', modified_at: 1700000000, total_size: 2000 },
        { project: 'Beta', modified_at: 1700000000, total_size: 2000 }
    ];

    const sortedByDate = globalThis.sortInboxSuggestions(items, 'date', 'desc');
    assert.strictEqual(sortedByDate[0].project, 'Alpha');
    assert.strictEqual(sortedByDate[1].project, 'Beta');
    assert.strictEqual(sortedByDate[2].project, 'Zebra');

    const sortedBySize = globalThis.sortInboxSuggestions(items, 'size', 'asc');
    assert.strictEqual(sortedBySize[0].project, 'Alpha');
    assert.strictEqual(sortedBySize[1].project, 'Beta');
    assert.strictEqual(sortedBySize[2].project, 'Zebra');
});

// --------------------------------------------------------------------------
// AK4 & AK7: Sort Bar UI and Default State
// --------------------------------------------------------------------------
test('AK4 & AK7: Default sort state without sessionStorage is date desc', () => {
    const env = setupEnvironment();
    const defaultState = globalThis.getInboxSortState();
    assert.strictEqual(defaultState.field, 'date');
    assert.strictEqual(defaultState.direction, 'desc');
});

test('AK4: index.html contains #smart-inbox-sort-bar with Name, Datum, Größe buttons', () => {
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    assert.ok(indexHtml.includes('id="smart-inbox-sort-bar"'), 'index.html must contain #smart-inbox-sort-bar');
    assert.ok(indexHtml.includes('data-field="name"'), 'sort bar must have Name button');
    assert.ok(indexHtml.includes('data-field="date"'), 'sort bar must have Datum button');
    assert.ok(indexHtml.includes('data-field="size"'), 'sort bar must have Größe button');
});

test('AK4: Clicking inactive sort button activates it (asc), clicking active toggles asc<->desc', () => {
    const env = setupEnvironment();
    const rawSuggestions = [
        { project: 'ProjA', modified_at: 100, total_size: 1000, video_count: 1 },
        { project: 'ProjB', modified_at: 200, total_size: 2000, video_count: 1 }
    ];

    // Initial render: default is date desc
    globalThis.renderSmartInboxList(rawSuggestions);
    assert.strictEqual(env.btnDate.getAttribute('aria-pressed'), 'true');
    assert.ok(env.btnDate.innerHTML.includes('▼'), 'Active date desc button should have ▼ indicator');
    assert.strictEqual(env.btnName.getAttribute('aria-pressed'), 'false');
    assert.strictEqual(env.btnSize.getAttribute('aria-pressed'), 'false');

    // Click inactive button "name" -> should activate with asc
    env.btnName.click();
    assert.strictEqual(env.btnName.getAttribute('aria-pressed'), 'true');
    assert.ok(env.btnName.innerHTML.includes('▲'), 'Newly activated name button should have ▲ indicator');
    assert.strictEqual(env.btnDate.getAttribute('aria-pressed'), 'false');

    // Click active button "name" again -> toggles to desc
    env.btnName.click();
    assert.strictEqual(env.btnName.getAttribute('aria-pressed'), 'true');
    assert.ok(env.btnName.innerHTML.includes('▼'), 'Toggled name button should have ▼ indicator');

    // Click active button "name" again -> toggles back to asc
    env.btnName.click();
    assert.strictEqual(env.btnName.getAttribute('aria-pressed'), 'true');
    assert.ok(env.btnName.innerHTML.includes('▲'), 'Toggled name button should have ▲ indicator');
});

test('AK4: Sort bar is hidden when suggestions list is empty', () => {
    const env = setupEnvironment();
    globalThis.renderSmartInboxList([]);
    assert.strictEqual(env.sortBar.style.display, 'none');
    assert.ok(env.smartInboxList.innerHTML.includes('Keine verarbeitbaren'), 'Empty state text rendered');
});

// --------------------------------------------------------------------------
// AK5: Persistence across Rerenders & sessionStorage defensive error handling
// --------------------------------------------------------------------------
test('AK5: Sort choice is persisted in sessionStorage and applied across renders', () => {
    const env = setupEnvironment();
    const rawSuggestions = [
        { project: 'Beta', modified_at: 100, total_size: 5000, video_count: 1 },
        { project: 'Alpha', modified_at: 200, total_size: 1000, video_count: 1 }
    ];

    // Initial render sets up sort bar and renders default date desc
    globalThis.renderSmartInboxList(rawSuggestions);

    // Select size asc
    env.btnSize.click();
    const savedJson = mockSessionStorage.getItem('smart-inbox-sort');
    assert.ok(savedJson, 'smart-inbox-sort must be in sessionStorage');
    const parsed = JSON.parse(savedJson);
    assert.strictEqual(parsed.field, 'size');
    assert.strictEqual(parsed.direction, 'asc');

    // Re-render simulates new fetch / refresh
    globalThis.renderSmartInboxList(rawSuggestions);
    const renderedItems = env.smartInboxList.__children;
    assert.strictEqual(renderedItems.length, 2);
    // Alpha has size 1000, Beta has size 5000 -> Alpha first in asc
    assert.strictEqual(renderedItems[0].getAttribute('data-project'), 'Alpha');
    assert.strictEqual(renderedItems[1].getAttribute('data-project'), 'Beta');
});

test('AK5: getInboxSortState handles corrupted sessionStorage defensively', () => {
    setupEnvironment();
    mockSessionStorage.setItem('smart-inbox-sort', '{ corrupted json ...');
    const state = globalThis.getInboxSortState();
    assert.strictEqual(state.field, 'date');
    assert.strictEqual(state.direction, 'desc');
});

// --------------------------------------------------------------------------
// AK6: Meta line formatting and null segment omission
// --------------------------------------------------------------------------
test('AK6: Meta line formats video_count, size, and German date with separator', () => {
    const env = setupEnvironment();
    const items = [
        { project: 'FullMeta', video_count: 3, total_size: 1548291000, modified_at: 1760000000 }
    ];

    globalThis.renderSmartInboxList(items);
    const itemEl = env.smartInboxList.__children[0];
    assert.ok(itemEl.innerHTML.includes('3 Datei(en)'));
    assert.ok(itemEl.innerHTML.includes('1.44 GB'));
    assert.ok(itemEl.innerHTML.includes('09.10.2025'));
    assert.ok(itemEl.innerHTML.includes('3 Datei(en) · 1.44 GB · 09.10.2025'));
});

test('AK6: Meta line cleanly omits null/missing size or date without empty delimiters', () => {
    const env = setupEnvironment();
    const items = [
        { project: 'NoDate', video_count: 2, total_size: 2048, modified_at: null },
        { project: 'NoSizeNoDate', video_count: 1, total_size: null, modified_at: null }
    ];

    globalThis.renderSmartInboxList(items);
    const item1 = env.smartInboxList.__children[0];
    assert.ok(item1.innerHTML.includes('2 Datei(en) · 2 KB'));
    assert.ok(!item1.innerHTML.includes('· ·'));

    const item2 = env.smartInboxList.__children[1];
    assert.ok(item2.innerHTML.includes('1 Datei(en)'));
    assert.ok(!item2.innerHTML.includes('1 Datei(en) ·'));
});
