import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { createFilmWizard } from '../../gui/static/js/film_wizard.js';
import { renderPreviewData, collectPreviewSelection } from '../../gui/static/js/preview_render.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
const filmWizardJsPath = path.resolve(__dirname, '../../gui/static/js/film_wizard.js');
const indexHtmlPath = path.resolve(__dirname, '../../gui/static/index.html');
const styleCssPath = path.resolve(__dirname, '../../gui/static/style.css');
const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);

function decodeEntities(str) {
    return String(str || '')
        .replace(/&quot;/g, '"').replace(/&#039;/g, "'").replace(/&#127916;/g, '🎬')
        .replace(/&rarr;/g, '→').replace(/&times;/g, '×').replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

function createMockDom() {
    const docListeners = {};
    function findById(root, targetId) {
        if (!root || !targetId) return null;
        if (root.id === targetId) return root;
        if (Array.isArray(root.children)) {
            for (const child of root.children) {
                const found = findById(child, targetId);
                if (found) return found;
            }
        }
        return null;
    }
    function matchesSingleSelector(el, sel) {
        if (!sel || !el) return false;
        const s = sel.trim();
        if (s.includes(':checked')) {
            const base = s.replace(':checked', '').trim();
            return (!base || matchesSingleSelector(el, base)) && Boolean(el.checked);
        }
        if (s.startsWith('[') && s.endsWith(']')) {
            const inner = s.slice(1, -1);
            const eqIdx = inner.indexOf('=');
            if (eqIdx !== -1) {
                const attrName = inner.slice(0, eqIdx).trim();
                const val = inner.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
                return el.getAttribute(attrName) === val;
            }
            return el.hasAttribute(inner);
        }
        if (s.includes('[')) {
            const idx = s.indexOf('[');
            return matchesSingleSelector(el, s.slice(0, idx)) && matchesSingleSelector(el, s.slice(idx));
        }
        if (s.startsWith('#')) return el.id === s.slice(1);
        if (s.startsWith('.')) return Boolean(el.classList && el.classList.contains(s.slice(1)));
        return Boolean(el.tagName && el.tagName.toLowerCase() === s.toLowerCase());
    }
    function splitSelectorParts(sel) {
        const parts = [];
        let curr = '', inBracket = false, inQuote = false, qChar = '';
        for (const ch of String(sel || '')) {
            if (inQuote) { curr += ch; if (ch === qChar) inQuote = false; }
            else if (ch === '"' || ch === "'") { inQuote = true; qChar = ch; curr += ch; }
            else if (ch === '[') { inBracket = true; curr += ch; }
            else if (ch === ']') { inBracket = false; curr += ch; }
            else if (/\s/.test(ch) && !inBracket) { if (curr.trim()) { parts.push(curr.trim()); curr = ''; } }
            else curr += ch;
        }
        if (curr.trim()) parts.push(curr.trim());
        return parts;
    }
    function findDescendants(root, parts) {
        if (!parts || parts.length === 0) return [];
        const [first, ...rest] = parts;
        const matches = [];
        const walk = (curr) => {
            if (!curr || !Array.isArray(curr.children)) return;
            for (const child of curr.children) {
                if (matchesSingleSelector(child, first)) {
                    if (rest.length === 0) matches.push(child);
                    else matches.push(...findDescendants(child, rest));
                }
                walk(child);
            }
        };
        walk(root);
        return matches;
    }
    function detachChildren(el) {
        if (!el || !Array.isArray(el.children)) return;
        for (const c of el.children) {
            if (c) c.parentNode = null;
        }
        el.children.length = 0;
    }
    function parseHtmlInto(rootEl, html) {
        detachChildren(rootEl);
        rootEl._textParts = [];
        if (!html) return;
        const stack = [rootEl];
        const tokenRegex = /<(\/?)([a-z0-9\-]+)([^>]*)>|([^<]+)/gi;
        let match;
        while ((match = tokenRegex.exec(html)) !== null) {
            if (match[4] !== undefined) {
                stack[stack.length - 1]._textParts.push(decodeEntities(match[4]));
                continue;
            }
            const isClosing = match[1] === '/';
            const tagName = match[2].toLowerCase();
            const attrStr = match[3] || '';
            if (isClosing) {
                for (let i = stack.length - 1; i > 0; i--) {
                    if (stack[i].tagName.toLowerCase() === tagName) { stack.length = i; break; }
                }
                continue;
            }
            const el = makeElement(tagName);
            el.ownerDocument = rootEl.ownerDocument;
            const clsMatch = attrStr.match(/class=["']([^"']+)["']/i);
            if (clsMatch) el.className = clsMatch[1];
            const idMatch = attrStr.match(/id=["']([^"']+)["']/i);
            if (idMatch) el.id = idMatch[1];
            const attrRegex = /([a-z0-9\-]+)=["']([^"']*)["']/gi;
            let aMatch;
            while ((aMatch = attrRegex.exec(attrStr)) !== null) {
                const k = aMatch[1].toLowerCase();
                if (k !== 'class' && k !== 'id') el.setAttribute(k, decodeEntities(aMatch[2]));
            }
            if (/\bchecked\b/i.test(attrStr)) el.checked = true;
            if (/\bdisabled\b/i.test(attrStr)) el.disabled = true;
            if (/\bhidden\b/i.test(attrStr)) el.setAttribute('hidden', '');
            stack[stack.length - 1].appendChild(el);
            if (!VOID_TAGS.has(tagName) && !/\/\s*$/.test(attrStr)) stack.push(el);
        }
    }
    const collectText = (el) => (el._textParts || []).join('') + (el.children || []).map(collectText).join('');
    function makeElement(tagName) {
        const classes = new Set(), attrs = new Map(), listeners = {}, dataset = {};
        let idVal = '', innerHtmlVal = '';
        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '', value: '', checked: false, disabled: false, placeholder: '', rows: 0,
            style: {}, children: [], _textParts: [], dataset, ownerDocument: null, parentNode: null, onclick: null,
            get id() { return idVal; },
            set id(v) { idVal = String(v || ''); },
            get textContent() { return collectText(el); },
            set textContent(v) {
                const str = String(v ?? '');
                innerHtmlVal = str; detachChildren(el); el._textParts = [str];
            },
            get className() { return Array.from(classes).join(' '); },
            set className(v) {
                classes.clear();
                String(v || '').split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
            },
            classList: {
                add: (...names) => names.forEach((n) => n && classes.add(n)),
                remove: (...names) => names.forEach((n) => classes.delete(n)),
                contains: (n) => classes.has(n),
                toggle: (n, force) => {
                    const add = force !== undefined ? Boolean(force) : !classes.has(n);
                    if (add) classes.add(n); else classes.delete(n);
                    return add;
                },
            },
            setAttribute(k, v) {
                attrs.set(k, String(v));
                if (k === 'id') el.id = String(v);
                if (k.startsWith('data-')) dataset[k.slice(5)] = String(v);
            },
            getAttribute: (k) => (attrs.has(k) ? attrs.get(k) : null),
            hasAttribute: (k) => attrs.has(k),
            removeAttribute: (k) => attrs.delete(k),
            appendChild(child) {
                if (child && child.parentNode && Array.isArray(child.parentNode.children)) {
                    const idx = child.parentNode.children.indexOf(child);
                    if (idx !== -1) child.parentNode.children.splice(idx, 1);
                }
                if (child) child.parentNode = el;
                el.children.push(child);
                return child;
            },
            removeChild(child) {
                const idx = el.children.indexOf(child);
                if (idx !== -1) { el.children.splice(idx, 1); child.parentNode = null; }
                return child;
            },
            addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
            click() {
                if (el.disabled) return;
                const evt = { type: 'click', target: el, currentTarget: el, preventDefault() {}, stopPropagation() {} };
                if (typeof el.onclick === 'function') el.onclick(evt);
                (listeners.click || []).forEach((fn) => fn(evt));
            },
            dispatchEvent(evt) {
                const eventObj = { target: el, currentTarget: el, preventDefault() {}, stopPropagation() {}, ...evt };
                (listeners[eventObj.type] || []).forEach((fn) => fn(eventObj));
            },
            querySelectorAll: (sel) => findDescendants(el, splitSelectorParts(sel)),
            querySelector: (sel) => el.querySelectorAll(sel)[0] || null,
        };
        Object.defineProperty(el, 'innerHTML', {
            get: () => innerHtmlVal,
            set(v) { innerHtmlVal = String(v ?? ''); parseHtmlInto(el, innerHtmlVal); },
        });
        return el;
    }
    const doc = {
        cookie: '',
        documentElement: { scrollTop: 0, style: { setProperty() {}, removeProperty() {} } },
        body: null,
        createElement(tag) { const el = makeElement(tag); el.ownerDocument = doc; return el; },
        getElementById: (id) => findById(doc.body, id),
        querySelectorAll: (sel) => (doc.body ? doc.body.querySelectorAll(sel) : []),
        querySelector: (sel) => doc.querySelectorAll(sel)[0] || null,
        addEventListener(type, fn) { (docListeners[type] = docListeners[type] || []).push(fn); },
    };
    doc.body = doc.createElement('body');
    return { doc };
}

function createFakeTimers() {
    let now = 0;
    let nextId = 1;
    const timers = new Map();
    return {
        setTimeout(fn, delay = 0) {
            const id = nextId++;
            const numericDelay = Number(delay) || 0;
            timers.set(id, { id, fn, delay: numericDelay, dueAt: now + numericDelay });
            return id;
        },
        clearTimeout(id) {
            timers.delete(id);
        },
        pendingCount() {
            return timers.size;
        },
        advanceBy(ms) {
            now += Number(ms) || 0;
            while (true) {
                const due = Array.from(timers.values())
                    .filter((t) => t.dueAt <= now)
                    .sort((a, b) => a.dueAt - b.dueAt || a.id - b.id);
                if (due.length === 0) break;
                const next = due[0];
                timers.delete(next.id);
                next.fn();
            }
        },
    };
}

function setupInboxAndWizardHarness({ fetchImpl } = {}) {
    const { doc } = createMockDom();
    const ensureEl = (id, tag = 'div') => {
        let el = doc.getElementById(id);
        if (!el) { el = doc.createElement(tag); el.id = id; doc.body.appendChild(el); }
        return el;
    };
    const cardInbox = ensureEl('card-smart-inbox', 'div');
    const groupBanner = doc.createElement('div'); groupBanner.id = 'smart-inbox-group-banner'; cardInbox.appendChild(groupBanner);
    const sortBar = doc.createElement('div'); sortBar.id = 'smart-inbox-sort-bar'; cardInbox.appendChild(sortBar);
    const bulkActions = doc.createElement('div'); bulkActions.id = 'smart-inbox-bulk-actions'; sortBar.appendChild(bulkActions);
    const inboxList = doc.createElement('div'); inboxList.id = 'smart-inbox-list'; cardInbox.appendChild(inboxList);
    ['modal-film-wizard', 'console-pulse', 'current-project-title', 'current-project-path',
     'project-stats-container', 'stats-badges-container', 'files-table-body', 'view-folder',
     'folder-mode-selector', 'recursive-mode-notice', 'mode-series', 'mode-movie',
     'context-movie', 'context-series', 'context-tools'].forEach((id) => ensureEl(id, 'div'));
    ensureEl('movie-nas-destination', 'select').value = '1';
    ensureEl('movie-pcloud-destination', 'select').value = '1';
    ensureEl('movie-search-query', 'input').value = '';
    ensureEl('movie-option-convert', 'input').checked = true;
    ensureEl('movie-option-delete', 'input').checked = true;
    ensureEl('movie-option-copy-nas', 'input').checked = true;
    ensureEl('movie-option-copy-pcloud', 'input').checked = false;
    ensureEl('movie-quality-slider', 'input').value = '60';

    const activeFetch = fetchImpl || (async () => ({ ok: true, status: 200, json: async () => [] }));
    const wizard = createFilmWizard({
        document: doc,
        fetch: activeFetch,
        confirm: () => true,
    });

    let cleanAppJs = fs.readFileSync(appJsPath, 'utf8').replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '');
    cleanAppJs = `
const cleanSeriesName = (s) => (s || '').replace(/\\.[a-z0-9]{2,4}$/i, '').replace(/[._]+/g, ' ').trim();
const formatBytes = (b) => String(b || 0) + ' B';
const fetchStats = async () => ({});
const fetchYoutubeSubscriptions = async () => [];
const fetchSmartInboxSuggestions = async () => [];
const loadConversionRecommendations = async () => {};
const triggerQualityHintUpdates = () => {};
const updateMwDataPanel = () => {};
const prepareSeriesPayload = (s, p) => p;
const setupMaskedInput = () => {};
const setMaskedInputValue = () => {};
const validateAllMaskedFields = () => true;
const initFilmWizard = () => globalThis.__wizardInstance;
const openFilmWizard = (opts) => globalThis.__wizardInstance.open(opts);
const renderNfoEditor = () => ({});
const buildMovieNfoOverrides = () => ({});
const buildWizardMovieOverrides = () => ({});
const normalizeFsk = (v) => v;
const parseGenres = (v) => v;
` + cleanAppJs + `
globalThis.renderSmartInboxList = renderSmartInboxList;
globalThis.scanProject = scanProject;
globalThis.selectProject = selectProject;
globalThis.initViews = initViews;
globalThis.selectedInboxMovieProjects = selectedInboxMovieProjects;
globalThis.updateBulkActionsBarUI = updateBulkActionsBarUI;
globalThis.getProjectFiles = () => projectFiles.slice();
`;

    const sandbox = {
        document: doc,
        window: { fetch: activeFetch, scrollTo: () => {}, addEventListener: () => {}, goHome: () => {} },
        fetch: activeFetch,
        Event: class { constructor(type) { this.type = type; } },
        localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 0; },
        clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {},
        queueMicrotask: (fn) => { if (typeof fn === 'function') fn(); },
        alert: () => {},
        confirm: () => true,
        console: { log: () => {}, warn: () => {}, error: () => {} },
        EventSource: class { close() {} },
        AbortController, renderPreviewData, collectPreviewSelection, __wizardInstance: wizard,
    };
    sandbox.globalThis = sandbox;
    vm.runInNewContext(cleanAppJs, sandbox);
    sandbox.initViews();
    return { doc, wizard, sandbox };
}

const flushAsync = () => new Promise((r) => setTimeout(r, 0));

// ============================================================================
// AK 1: Dateinamen-Unterzeile im Film-Assistenten
// ============================================================================
test('ROADMAP #94 AK1: Wizard project subtitle displays folder + video filename(s), loose file, resets across sessions, updates in queue mode, and guards setProjectContext', () => {
    const { doc } = createMockDom();
    const wizard = createFilmWizard({
        document: doc,
        fetch: async () => ({ ok: true, status: 200, json: async () => [] }),
    });
    const subtitleEl = doc.getElementById('mw-wizard-project-subtitle');
    assert.ok(subtitleEl);
    assert.equal(subtitleEl.classList.contains('hidden'), true);

    // 1) Folder with 1 video file (e.g. cryptic folder EMwimA2000)
    wizard.open({
        projectName: 'EMwimA2000',
        query: 'EMwimA',
        isDir: true,
        videoFilenames: ['Ey.Mann.wo.is.mein.Auto.2000.mkv'],
        autoSearch: false,
    });
    assert.equal(subtitleEl.classList.contains('hidden'), false);
    assert.equal(subtitleEl.textContent, 'Ordner: EMwimA2000 · Datei: Ey.Mann.wo.is.mein.Auto.2000.mkv');

    // 2) setProjectContext guards against empty or mismatched project names, updates active project
    assert.equal(wizard.setProjectContext({ projectName: '', videoFilenames: ['x.mkv'] }), false);
    assert.equal(wizard.setProjectContext({ projectName: 'AnderesProjekt', videoFilenames: ['x.mkv'] }), false);
    assert.equal(
        wizard.setProjectContext({
            projectName: 'EMwimA2000',
            isDir: true,
            videoFilenames: ['CD1.mkv', 'CD2.mkv', 'Bonus.mkv'],
        }),
        true
    );
    assert.equal(subtitleEl.textContent, 'Ordner: EMwimA2000 · Dateien: CD1.mkv, CD2.mkv (+1 weitere)');

    // 3) Loose file (isDir: false)
    wizard.open({
        projectName: 'Solo.Film.2020.mkv',
        query: 'Solo Film',
        isDir: false,
        videoFilenames: [],
        autoSearch: false,
    });
    assert.equal(subtitleEl.textContent, 'Datei: Solo.Film.2020.mkv');

    // 4) Session isolation: next open() without isDir or videoFilenames must NOT stick to isDir: false
    wizard.open({
        projectName: 'NeuerOrdner',
        query: 'NeuerOrdner',
        autoSearch: false,
    });
    assert.equal(subtitleEl.textContent, 'Ordner: NeuerOrdner');

    // 5) Queue mode updates subtitle when advancing via skipQueueMovie()
    wizard.open({
        queue: [
            {
                projectName: 'EMwimA2000',
                query: 'EMwimA',
                isDir: true,
                videoFilenames: ['Ey.Mann.wo.is.mein.Auto.2000.mkv'],
            },
            {
                projectName: 'Solo.Sequel.2004.mkv',
                query: 'Solo Sequel',
                isDir: false,
                videoFilenames: [],
            },
        ],
        autoSearch: false,
    });
    assert.equal(subtitleEl.textContent, 'Ordner: EMwimA2000 · Datei: Ey.Mann.wo.is.mein.Auto.2000.mkv');
    wizard.skipQueueMovie();
    assert.equal(subtitleEl.textContent, 'Datei: Solo.Sequel.2004.mkv');

    wizard.close({ force: true });
    assert.equal(subtitleEl.classList.contains('hidden'), true);
    assert.equal(subtitleEl.textContent, '');
});

// ============================================================================
// AK 2: Dateinamen-Unterzeile in der Smart Inbox & scanProject-Rennfreiheit
// ============================================================================
test('ROADMAP #94 AK2: Smart Inbox renders .smart-inbox-filename-sub only when folder video filename differs, escapes HTML, and resolves wizard context race-free', async () => {
    let scanResolvers = {};
    const { doc, sandbox } = setupInboxAndWizardHarness({
        fetchImpl: async (url) => {
            if (String(url).startsWith('/api/scan-project')) {
                const proj = decodeURIComponent(String(url).split('project=')[1] || '');
                return new Promise((resolve) => {
                    scanResolvers[proj] = resolve;
                });
            }
            return { ok: true, status: 200, json: async () => [] };
        },
    });

    const suggestions = [
        {
            project: 'EMwimA2000',
            suggested_query: 'EMwimA',
            media_type: 'movie',
            is_dir: true,
            video_count: 1,
            video_filenames: ['Ey.Mann.wo.is.mein.Auto.2000.mkv'],
        },
        {
            project: 'Matrix (1999)',
            suggested_query: 'Matrix',
            media_type: 'movie',
            is_dir: true,
            video_count: 1,
            video_filenames: ['Matrix (1999).mkv'],
        },
        {
            project: 'Solo.Film.2020.mkv',
            suggested_query: 'Solo Film',
            media_type: 'movie',
            is_dir: false,
            video_count: 1,
            video_filenames: [],
        },
        {
            project: 'XssFolder',
            suggested_query: 'XssFolder',
            media_type: 'movie',
            is_dir: true,
            video_count: 3,
            video_filenames: ['<img src=x onerror=1>.mkv', 'Part2&3.mkv', 'Part4.mkv'],
        },
    ];

    sandbox.renderSmartInboxList(suggestions, new Set());

    const rowEm = doc.querySelector('.smart-inbox-item[data-project="EMwimA2000"]');
    const subEm = rowEm.querySelector('.smart-inbox-filename-sub');
    assert.ok(subEm, 'Cryptic folder with differing video filename must show subtitle');
    assert.equal(subEm.textContent, 'Datei: Ey.Mann.wo.is.mein.Auto.2000.mkv');

    const rowMatrix = doc.querySelector('.smart-inbox-item[data-project="Matrix (1999)"]');
    assert.equal(rowMatrix.querySelector('.smart-inbox-filename-sub'), null, 'Identical folder/file name must not show redundant subtitle');

    const rowSolo = doc.querySelector('.smart-inbox-item[data-project="Solo.Film.2020.mkv"]');
    assert.equal(rowSolo.querySelector('.smart-inbox-filename-sub'), null, 'Loose single file must not show folder subtitle');

    const rowXss = doc.querySelector('.smart-inbox-item[data-project="XssFolder"]');
    const subXss = rowXss.querySelector('.smart-inbox-filename-sub');
    assert.ok(subXss);
    assert.equal(subXss.textContent, 'Dateien: <img src=x onerror=1>.mkv, Part2&3.mkv (+1 weitere)');
    assert.equal(subXss.querySelector('img'), null, 'HTML tags in filename must be escaped');

    // Race-free context resolution: clicking "Auswählen" on EMwimA2000 BEFORE /api/scan-project finishes
    const selectBtn = rowEm.querySelector('.btn-select-smart');
    selectBtn.click();
    const subtitleEl = doc.getElementById('mw-wizard-project-subtitle');
    assert.equal(subtitleEl.textContent, 'Ordner: EMwimA2000 · Datei: Ey.Mann.wo.is.mein.Auto.2000.mkv');

    // Direct sidebar project selection where scan finishes AFTER wizard opens, plus stale scan guard
    sandbox.renderSmartInboxList([], new Set());
    sandbox.selectProject('SidebarOld');
    sandbox.selectProject('SidebarNew');
    doc.getElementById('mode-movie').click();
    assert.equal(subtitleEl.textContent, 'Ordner: SidebarNew');

    const pathEl = doc.getElementById('current-project-path');
    const tbodyEl = doc.getElementById('files-table-body');

    // Active response for SidebarNew arrives first -> updates wizard subtitle, path, and projectFiles
    scanResolvers['SidebarNew']({
        ok: true,
        status: 200,
        json: async () => ({
            current_dir: '/inbox/SidebarNew',
            files: ['Real.Movie.Title.2024.mkv'],
            video_filenames: ['Real.Movie.Title.2024.mkv'],
            is_single_file: false,
        }),
    });
    await flushAsync();
    assert.equal(subtitleEl.textContent, 'Ordner: SidebarNew · Datei: Real.Movie.Title.2024.mkv');
    assert.equal(pathEl.textContent, 'Pfad: /inbox/SidebarNew');
    assert.deepEqual(sandbox.getProjectFiles(), ['Real.Movie.Title.2024.mkv']);
    assert.match(tbodyEl.textContent, /Real\.Movie\.Title\.2024\.mkv/);

    // Out-of-order response for SidebarOld arrives AFTER SidebarNew -> must be completely discarded
    scanResolvers['SidebarOld']({
        ok: true,
        status: 200,
        json: async () => ({
            current_dir: '/inbox/SidebarOld',
            files: ['OldFile.mkv'],
            video_filenames: ['OldFile.mkv'],
            is_single_file: false,
        }),
    });
    await flushAsync();
    assert.equal(subtitleEl.textContent, 'Ordner: SidebarNew · Datei: Real.Movie.Title.2024.mkv');
    assert.equal(pathEl.textContent, 'Pfad: /inbox/SidebarNew');
    assert.deepEqual(sandbox.getProjectFiles(), ['Real.Movie.Title.2024.mkv']);
    assert.doesNotMatch(tbodyEl.textContent, /OldFile\.mkv/);
});

// ============================================================================
// AK 3: Debounced Live-Suche, AbortController, kein verwaister Ladeindikator & Wiederholsuche
// ============================================================================
test('ROADMAP #94 AK3: Debounced typeahead search coalesces typing, aborts in-flight requests cleanly without error banner or stale loading spinner, and supports re-search after step navigation', async () => {
    const { doc } = createMockDom();
    const timers = createFakeTimers();
    const searchCalls = [];

    const wizard = createFilmWizard({
        document: doc,
        setTimeout: timers.setTimeout,
        clearTimeout: timers.clearTimeout,
        fetch: async (url, opts = {}) => {
            if (String(url).startsWith('/api/search')) {
                const q = decodeURIComponent(String(url).split('q=')[1] || '');
                const record = { q, signal: opts.signal || null };
                searchCalls.push(record);
                return new Promise((resolve, reject) => {
                    record.resolve = resolve;
                    record.reject = reject;
                    if (opts.signal) {
                        opts.signal.addEventListener('abort', () => {
                            const abortErr = new Error('The operation was aborted.');
                            abortErr.name = 'AbortError';
                            reject(abortErr);
                        });
                    }
                });
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    wizard.open({
        projectName: 'EMwimA2000',
        query: 'EMwimA',
        isDir: true,
        videoFilenames: ['Ey.Mann.wo.is.mein.Auto.2000.mkv'],
        autoSearch: false,
    });

    const searchInput = doc.getElementById('mw-wizard-search-input');
    const searchResults = doc.getElementById('mw-wizard-search-results');
    const errorBanner = doc.getElementById('mw-wizard-error-banner');

    // 1) Fast typing before 380ms debounce expires triggers 0 requests
    searchInput.value = 'W';
    searchInput.dispatchEvent({ type: 'input' });
    assert.equal(timers.pendingCount(), 0);

    for (const text of ['Wo', 'Wo ist', 'Wo ist mein Auto']) {
        timers.advanceBy(100);
        searchInput.value = text;
        searchInput.dispatchEvent({ type: 'input' });
    }
    assert.equal(searchCalls.length, 0);
    assert.equal(timers.pendingCount(), 1);

    // At 379ms after the last input event, debounce timer has NOT fired yet
    timers.advanceBy(379);
    assert.equal(searchCalls.length, 0);
    assert.equal(timers.pendingCount(), 1);

    // At 380ms (+1ms), debounce timer fires -> exactly 1 request for "Wo ist mein Auto"
    timers.advanceBy(1);
    assert.equal(searchCalls.length, 1);
    assert.equal(searchCalls[0].q, 'Wo ist mein Auto');
    assert.ok(searchResults.querySelector('.mw-wizard-loading'), 'Loading indicator shown while request in flight');

    // 2) Typing < 2 chars ("W") aborts the in-flight request without error banner and removes loading indicator
    searchInput.value = 'W';
    searchInput.dispatchEvent({ type: 'input' });
    await flushAsync();
    assert.equal(searchCalls[0].signal.aborted, true);
    assert.equal(errorBanner.classList.contains('hidden'), true, 'Aborted search must not trigger error banner');
    assert.equal(searchResults.querySelector('.mw-wizard-loading'), null, 'Loading indicator must be cleared on abort');

    // 3) Step change during in-flight search aborts request, removes loading spinner, and allows re-searching same query after prevStep()
    searchInput.value = 'Wo ist mein Auto';
    searchInput.dispatchEvent({ type: 'input' });
    timers.advanceBy(380);
    assert.equal(searchCalls.length, 2);
    assert.ok(searchResults.querySelector('.mw-wizard-loading'));

    // Navigate to Step 2 via nextStep() while search is still in flight
    wizard.nextStep();
    await flushAsync();
    assert.equal(wizard.getCurrentStep(), 2);
    assert.equal(searchCalls[1].signal.aborted, true);
    assert.equal(searchResults.querySelector('.mw-wizard-loading'), null, 'No orphaned loading indicator after step change');

    // Return to Step 1 via prevStep() and trigger live search for the SAME query -> must NOT be blocked by lastExecutedSearchQuery
    wizard.prevStep();
    assert.equal(wizard.getCurrentStep(), 1);
    searchInput.value = 'Wo ist mein Auto';
    searchInput.dispatchEvent({ type: 'input' });
    timers.advanceBy(380);
    assert.equal(searchCalls.length, 3, 'Same query must re-run after previous attempt was aborted');
    searchCalls[2].resolve({
        ok: true,
        status: 200,
        json: async () => [{ id: '8859', name: 'Ey Mann, wo is’ mein Auto? (2000)', provider: 'tmdb' }],
    });
    await flushAsync();
    assert.equal(searchResults.querySelectorAll('.mw-wizard-search-item').length, 1);

    // Duplicate input event with identical trimmed text after successful response does not re-fetch
    searchInput.value = 'Wo ist mein Auto   ';
    searchInput.dispatchEvent({ type: 'input' });
    timers.advanceBy(380);
    assert.equal(searchCalls.length, 3);

    // 4) IME composition guard & explicit 1-char Enter search
    searchInput.value = 'M';
    searchInput.dispatchEvent({ type: 'keydown', key: 'Enter', isComposing: true });
    assert.equal(searchCalls.length, 3, 'Enter during IME composition must be ignored');

    searchInput.dispatchEvent({ type: 'keydown', key: 'Enter', isComposing: false });
    assert.equal(searchCalls.length, 4, 'Explicit Enter searches 1-char query immediately');
    assert.equal(searchCalls[3].q, 'M');
});

// ============================================================================
// AK 4: Statische HTML/CSS- & Cache-Busting-Prüfung
// ============================================================================
test('ROADMAP #94 AK4: Static HTML/CSS and synchronous cache-busting across index.html, app.js, and film_wizard.js', () => {
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const appJs = fs.readFileSync(appJsPath, 'utf8');
    const filmWizardJs = fs.readFileSync(filmWizardJsPath, 'utf8');
    const styleCss = fs.readFileSync(styleCssPath, 'utf8');

    assert.match(indexHtml, /id="mw-wizard-project-subtitle"\s+class="mw-wizard-project-subtitle hidden"/);
    assert.match(
        indexHtml,
        /id="mw-wizard-search-input"[^>]*aria-label="Filmtitel oder Suchbegriff"[^>]*autocorrect="off"[^>]*autocapitalize="none"[^>]*spellcheck="false"/
    );

    const appVerMatch = indexHtml.match(/src="app\.js\?v=(\d+)"/);
    assert.ok(appVerMatch, 'index.html must include app.js?v=<number>');
    const expectedJsVersion = appVerMatch[1];

    const appImports = [...appJs.matchAll(/from\s+['"]\.\/js\/[^'"]+\?v=(\d+)['"]/g)];
    assert.ok(appImports.length >= 10);
    for (const m of appImports) {
        assert.equal(m[1], expectedJsVersion, `app.js import ${m[0]} must match v=${expectedJsVersion}`);
    }

    const wizImports = [...filmWizardJs.matchAll(/from\s+['"]\.\/[^'"]+\?v=(\d+)['"]/g)];
    assert.equal(wizImports.length, 3, 'film_wizard.js must have 3 versioned relative imports');
    for (const m of wizImports) {
        assert.equal(m[1], expectedJsVersion, `film_wizard.js import ${m[0]} must match v=${expectedJsVersion}`);
    }

    for (const selector of ['.mw-wizard-project-subtitle', '.smart-inbox-filename-sub']) {
        const idx = styleCss.indexOf(selector);
        assert.ok(idx > 0, `${selector} must exist in style.css`);
        const ruleEnd = styleCss.indexOf('}', idx);
        const ruleBlock = styleCss.slice(idx, ruleEnd + 1);
        assert.match(ruleBlock, /var\(--text-muted\)/);
        assert.doesNotMatch(ruleBlock, /#[0-9a-fA-F]{3,8}/);
    }
});
