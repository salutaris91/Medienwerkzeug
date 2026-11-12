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
const indexHtmlPath = path.resolve(__dirname, '../../gui/static/index.html');
const styleCssPath = path.resolve(__dirname, '../../gui/static/style.css');
const VOID_TAGS = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);

function decodeEntities(str) {
    return String(str || '')
        .replace(/&quot;/g, '"').replace(/&#039;/g, "'").replace(/&#127916;/g, '🎬')
        .replace(/&rarr;/g, '→').replace(/&times;/g, '×').replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}

// Lightweight DOM implementation for node:test (project runs without npm dependencies / jsdom; see briefing.md §4).
// Uses live tree traversal for getElementById so removed/detached nodes are never retained.
function createQueueDom() {
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
        dispatchKeydown(key) {
            let prevented = false;
            const evt = { type: 'keydown', key, preventDefault() { prevented = true; }, get defaultPrevented() { return prevented; } };
            (docListeners.keydown || []).forEach((fn) => fn(evt));
            return evt;
        },
    };
    doc.body = doc.createElement('body');
    return { doc };
}

function setupInboxAndWizardHarness({ fetchImpl, confirmImpl } = {}) {
    const { doc } = createQueueDom();
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
     'folder-mode-selector', 'recursive-mode-notice', 'mode-series', 'mode-movie'].forEach((id) => ensureEl(id, 'div'));
    ensureEl('movie-nas-destination', 'select').value = '1';
    ensureEl('movie-pcloud-destination', 'select').value = '1';
    ensureEl('movie-option-convert', 'input').checked = true;
    ensureEl('movie-option-delete', 'input').checked = true;
    ensureEl('movie-option-copy-nas', 'input').checked = true;
    ensureEl('movie-option-copy-pcloud', 'input').checked = false;
    ensureEl('movie-quality-slider', 'input').value = '60';

    const alerts = [], logs = [];
    let connectLogStreamCalls = 0;
    const activeFetch = fetchImpl || (async () => ({ ok: true, status: 200, json: async () => ({}) }));
    const wizard = createFilmWizard({
        document: doc, fetch: activeFetch, confirm: confirmImpl || (() => true), onLog: (msg) => logs.push(msg),
    });

    let cleanAppJs = fs.readFileSync(appJsPath, 'utf8').replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '');
    cleanAppJs = cleanAppJs.replace(
        'function connectLogStream() {',
        'function connectLogStream() { if (typeof globalThis.__onConnectLogStream === "function") globalThis.__onConnectLogStream();'
    );
    cleanAppJs = `
const cleanSeriesName = (s) => (s || '').replace(/\\.[a-z0-9]{2,4}$/i, '').replace(/[._]+/g, ' ').trim();
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
globalThis.updateBulkActionsBarUI = updateBulkActionsBarUI;
globalThis.selectedInboxProjects = selectedInboxProjects;
globalThis.selectedInboxMovieProjects = selectedInboxMovieProjects;
globalThis.unlockedMovieProjects = unlockedMovieProjects;
globalThis.unlockedSeriesAsMovieProjects = unlockedSeriesAsMovieProjects;
globalThis.scanProject = scanProject;
globalThis.setSelectShowStub = (fn) => { selectShow = fn; };
globalThis.getActiveProjectsProcessing = () => activeProjectsProcessing;
globalThis.setCurrentSmartInboxRawSuggestions = (arr) => { currentSmartInboxRawSuggestions = arr; };
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
        alert: (msg) => alerts.push(String(msg)),
        confirm: confirmImpl || (() => true),
        console: { log: () => {}, warn: () => {}, error: (msg) => logs.push(String(msg)) },
        EventSource: class { close() {} },
        AbortController, renderPreviewData, collectPreviewSelection, __wizardInstance: wizard,
        __onConnectLogStream: () => { connectLogStreamCalls += 1; },
        getConnectLogStreamCalls: () => connectLogStreamCalls,
    };
    sandbox.globalThis = sandbox;
    vm.runInNewContext(cleanAppJs, sandbox);
    return { doc, wizard, sandbox, alerts, logs };
}

const flushAsync = () => new Promise((r) => setTimeout(r, 0));

// ============================================================================
// E6-AK1: Inbox-Mehrfachauswahl -> "Als Filme einreihen" -> "Film X von N"
// ============================================================================
test('E6-AK1: Movie multi-select in Smart Inbox preserves #65 series lock, opens Vorab-Queue, carries options across movies, and processes Film 1..3 sequentially', async () => {
    const processPayloads = [];
    const mockFetch = async (url, options = {}) => {
        if (url.startsWith('/api/search')) {
            const q = decodeURIComponent(url.split('q=')[1] || '');
            return { ok: true, status: 200, json: async () => [{ id: `tmdb_${q}`, name: `${q} (2001)`, provider: 'tmdb' }] };
        }
        if (url.startsWith('/api/metadata/fetch')) {
            const movieId = decodeURIComponent((url.split('movie_id=')[1] || '').split('&')[0]);
            return {
                ok: true, status: 200,
                json: async () => ({ title: `Titel ${movieId}`, year: '2001', plot: `Plot ${movieId}`, fsk: '12', genres: ['Fantasy'] }),
            };
        }
        if (url === '/api/preview_process') {
            const body = JSON.parse(options.body || '{}');
            return {
                ok: true, status: 200,
                json: async () => ({
                    destination: `/mnt/nas/Filme/${body.movie_name}`,
                    renames: [{ old: `${body.project_name}.mkv`, new: `${body.movie_name}.mkv` }],
                    subs: [], junk: [],
                }),
            };
        }
        if (url === '/api/process') {
            processPayloads.push(JSON.parse(options.body || '{}'));
            return { ok: true, status: 200, json: async () => ({ status: 'queued' }) };
        }
        return { ok: true, status: 200, json: async () => ({}) };
    };

    const { doc, wizard, sandbox } = setupInboxAndWizardHarness({ fetchImpl: mockFetch });
    const inboxSuggestions = [
        { project: 'Herr.der.Ringe.1.2001', media_type: 'movie', is_dir: true, video_count: 1 },
        { project: 'Herr_der_Ringe_2_(2002).mkv', media_type: 'movie', is_dir: false, video_count: 1 },
        { project: 'Herr.der.Ringe.3.2003', media_type: 'movie', is_dir: true, video_count: 1 },
        { project: 'LooseEpisodeMovie.mkv', media_type: 'movie', is_dir: false, video_count: 1 },
    ];
    sandbox.renderSmartInboxList(inboxSuggestions, new Set());
    const inboxList = doc.getElementById('smart-inbox-list');

    // #65/#77 Regression: loose movie file is locked for series (.smart-inbox-cb absent), has .smart-inbox-movie-cb
    const looseRow = inboxList.querySelector('[data-project="LooseEpisodeMovie.mkv"]');
    assert.equal(looseRow.querySelector('.smart-inbox-cb'), null);
    const looseMovieCb = looseRow.querySelector('.smart-inbox-movie-cb');
    assert.ok(looseMovieCb);
    looseMovieCb.checked = true;
    looseMovieCb.dispatchEvent({ type: 'change' });
    assert.equal(sandbox.selectedInboxMovieProjects.has('LooseEpisodeMovie.mkv'), true);

    // Unlocking for series removes item from movie selection and renders .smart-inbox-cb
    looseRow.querySelector('.btn-unlock-movie-series').click();
    assert.equal(sandbox.selectedInboxMovieProjects.has('LooseEpisodeMovie.mkv'), false);
    const looseRowAfter = inboxList.querySelector('[data-project="LooseEpisodeMovie.mkv"]');
    assert.equal(looseRowAfter.querySelector('.smart-inbox-movie-cb'), null);
    assert.ok(looseRowAfter.querySelector('.smart-inbox-cb'));

    // Select the 3 movies and start Vorab-Queue
    for (const proj of ['Herr.der.Ringe.1.2001', 'Herr_der_Ringe_2_(2002).mkv', 'Herr.der.Ringe.3.2003']) {
        const cb = inboxList.querySelector(`[data-project="${proj}"] .smart-inbox-movie-cb`);
        cb.checked = true;
        cb.dispatchEvent({ type: 'change' });
    }
    assert.equal(doc.getElementById('smart-inbox-bulk-count').textContent, '3 Filme ausgewählt');
    const queueBtn = doc.getElementById('btn-bulk-queue-movies');
    assert.equal(queueBtn.textContent, 'Als Filmreihe verarbeiten (3)');
    queueBtn.click();
    await flushAsync();

    assert.equal(sandbox.selectedInboxMovieProjects.size, 0);
    const seriesCtx = doc.getElementById('mw-wizard-series-context');
    const queueLabel = doc.getElementById('mw-wizard-queue-label');
    const nextBtn = doc.getElementById('mw-wizard-btn-next');
    const skipStepBtn = doc.getElementById('mw-wizard-btn-skip');
    const executeBtn = doc.getElementById('mw-wizard-btn-execute');
    assert.equal(seriesCtx.classList.contains('hidden'), false);
    assert.equal(queueLabel.textContent, 'Film 1 von 3 · Herr.der.Ringe.1.2001');
    assert.equal(doc.getElementById('mw-wizard-search-input').value, 'Herr der Ringe 1');

    // Film 1: user clicks search result -> Step 2 -> Next -> Step 3 -> Skip -> Step 4, customizes options & clicks Execute
    doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item').click();
    await flushAsync();
    assert.equal(wizard.getCurrentStep(), 2);
    nextBtn.click();
    await flushAsync();
    assert.equal(wizard.getCurrentStep(), 3);
    skipStepBtn.click();
    await flushAsync();
    assert.equal(wizard.getCurrentStep(), 4);
    const optConvert = doc.getElementById('mw-wizard-option-convert');
    optConvert.checked = false;
    optConvert.dispatchEvent({ type: 'change' });
    assert.equal(executeBtn.textContent, 'Einreihen & nächster Film');
    executeBtn.click();
    await flushAsync();

    // Film 2 of 3 active in Step 1, onProcessSuccess (connectLogStream) fired immediately for Film 1
    assert.equal(processPayloads.length, 1);
    assert.equal(sandbox.getConnectLogStreamCalls(), 1);
    assert.equal(processPayloads[0].project_name, 'Herr.der.Ringe.1.2001');
    assert.equal(processPayloads[0].convert, false);
    assert.equal(wizard.getCurrentStep(), 1);
    assert.equal(queueLabel.textContent, 'Film 2 von 3 · Herr_der_Ringe_2_(2002).mkv');
    assert.equal(doc.getElementById('mw-wizard-search-input').value, 'Herr der Ringe 2');
    assert.match(doc.getElementById('mw-wizard-queue-status').textContent, /✓ 1 eingereiht/);

    // Film 2: user clicks search result -> Step 2 -> Next -> Step 3 -> Next -> Step 4 (carries over convert === false)
    doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item').click();
    await flushAsync();
    nextBtn.click();
    await flushAsync();
    nextBtn.click();
    await flushAsync();
    assert.equal(wizard.getCurrentStep(), 4);
    assert.equal(executeBtn.textContent, 'Einreihen & nächster Film');
    executeBtn.click();
    await flushAsync();

    assert.equal(processPayloads.length, 2);
    assert.equal(sandbox.getConnectLogStreamCalls(), 2);
    assert.equal(processPayloads[1].project_name, 'Herr_der_Ringe_2_(2002).mkv');
    assert.equal(processPayloads[1].convert, false);
    assert.equal(queueLabel.textContent, 'Film 3 von 3 · Herr.der.Ringe.3.2003');
    assert.match(doc.getElementById('mw-wizard-queue-status').textContent, /✓ 2 eingereiht/);

    // Film 3 (last): button label is "Jetzt final verarbeiten", modal closes after execution
    doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item').click();
    await flushAsync();
    nextBtn.click();
    await flushAsync();
    skipStepBtn.click();
    await flushAsync();
    assert.equal(executeBtn.textContent, 'Jetzt final verarbeiten');
    assert.equal(doc.getElementById('mw-wizard-queue-skip-btn').textContent, 'Film überspringen & schließen');
    executeBtn.click();
    await flushAsync();

    assert.equal(processPayloads.length, 3);
    assert.equal(sandbox.getConnectLogStreamCalls(), 3);
    assert.equal(processPayloads[2].project_name, 'Herr.der.Ringe.3.2003');
    assert.equal(processPayloads[2].convert, false);
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);
    assert.equal(wizard.getQueueState().active, false);
    assert.deepEqual(wizard.getQueueState().items.map((it) => it.status), ['queued', 'queued', 'queued']);
});

// ============================================================================
// E6-AK2: Abbruch bei Film k bewahrt 1..k-1 und lässt k..N unangetastet
// ============================================================================
test('E6-AK2: Aborting queue at Film 2 keeps Film 1 queued in backend (with immediate onProcessSuccess) and leaves Film 2 and Film 3 untouched in Inbox', async () => {
    const processPayloads = [];
    let allowConfirm = false, confirmCalls = 0;
    const mockFetch = async (url, options = {}) => {
        if (url.startsWith('/api/search')) return { ok: true, status: 200, json: async () => [{ id: '603', name: 'Matrix (1999)', provider: 'tmdb' }] };
        if (url.startsWith('/api/metadata/fetch')) return { ok: true, status: 200, json: async () => ({ title: 'Matrix', year: '1999', plot: 'Plot', fsk: '16', genres: ['Sci-Fi'] }) };
        if (url === '/api/preview_process') {
            const body = JSON.parse(options.body || '{}');
            return { ok: true, status: 200, json: async () => ({ destination: `/mnt/nas/Filme/${body.movie_name}`, renames: [{ old: 'a.mkv', new: 'b.mkv' }], subs: [], junk: [] }) };
        }
        if (url === '/api/process') {
            processPayloads.push(JSON.parse(options.body || '{}'));
            return { ok: true, status: 200, json: async () => ({ status: 'queued' }) };
        }
        return { ok: true, status: 200, json: async () => ({}) };
    };

    const { doc, wizard, sandbox } = setupInboxAndWizardHarness({
        fetchImpl: mockFetch, confirmImpl: () => { confirmCalls += 1; return allowConfirm; },
    });
    const inboxSuggestions = [
        { project: 'Matrix.1.1999', media_type: 'movie', is_dir: true, video_count: 1 },
        { project: 'Matrix.2.Reloaded.2003', media_type: 'movie', is_dir: true, video_count: 1 },
        { project: 'Matrix.3.Revolutions.2003', media_type: 'movie', is_dir: true, video_count: 1 },
    ];
    sandbox.renderSmartInboxList(inboxSuggestions, new Set());
    for (const item of inboxSuggestions) {
        const cb = doc.getElementById('smart-inbox-list').querySelector(`[data-project="${item.project}"] .smart-inbox-movie-cb`);
        cb.checked = true;
        cb.dispatchEvent({ type: 'change' });
    }
    doc.getElementById('btn-bulk-queue-movies').click();
    await flushAsync();

    // Queue Film 1 via user-facing clicks: search item -> Step 2 -> Next -> Step 3 -> Skip -> Step 4 -> Execute
    doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item').click();
    await flushAsync();
    doc.getElementById('mw-wizard-btn-next').click();
    await flushAsync();
    doc.getElementById('mw-wizard-btn-skip').click();
    await flushAsync();
    doc.getElementById('mw-wizard-btn-execute').click();
    await flushAsync();

    assert.equal(processPayloads.length, 1);
    assert.equal(processPayloads[0].project_name, 'Matrix.1.1999');
    assert.equal(sandbox.getConnectLogStreamCalls(), 1, 'onProcessSuccess must trigger connectLogStream immediately after Film 1');
    assert.equal(doc.getElementById('mw-wizard-queue-label').textContent, 'Film 2 von 3 · Matrix.2.Reloaded.2003');

    // Film 2: enter Step 2 via manual button, edit title -> dirty close confirmation declined -> stays open; then confirmed via ESC in Step 1
    doc.getElementById('mw-wizard-manual-btn').click();
    await flushAsync();
    assert.equal(wizard.getCurrentStep(), 2);
    const titleInput = doc.getElementById('mw-wizard-nfo-title');
    titleInput.value = 'Matrix Reloaded Custom';
    titleInput.dispatchEvent({ type: 'input' });

    allowConfirm = false;
    doc.getElementById('mw-wizard-close').click();
    assert.equal(confirmCalls, 1);
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    doc.getElementById('mw-wizard-btn-back').click();
    assert.equal(wizard.getCurrentStep(), 1);
    allowConfirm = true;
    doc.dispatchKeydown('Escape');
    assert.equal(confirmCalls, 2);
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);

    assert.equal(processPayloads.length, 1);
    assert.equal(sandbox.getConnectLogStreamCalls(), 1);
    assert.deepEqual(wizard.getQueueState().items.map((it) => it.status), ['queued', 'pending', 'pending']);
    const remainingProjects = doc.getElementById('smart-inbox-list').querySelectorAll('.smart-inbox-item').map((el) => el.getAttribute('data-project'));
    assert.ok(remainingProjects.includes('Matrix.2.Reloaded.2003'));
    assert.ok(remainingProjects.includes('Matrix.3.Revolutions.2003'));
});

// ============================================================================
// E6-AK3: Provider-Fehler bei Film k blockiert Queue nicht (inkl. Stale-Search-Schutz)
// ============================================================================
test('E6-AK3: Provider errors at Film k show error chip in queue header, ignore stale delayed search failures, and allow skipping, partial-success continuation, and manual completion', async () => {
    const processPayloads = [];
    let currentMovieStep = 1;
    let delayedFilm1Reject = null;
    const mockFetch = async (url, options = {}) => {
        if (url.startsWith('/api/search')) {
            if (url.includes('Delayed')) {
                return new Promise((_, reject) => { delayedFilm1Reject = reject; });
            }
            if (currentMovieStep === 1) throw new Error('Netzwerk-Timeout bei Suche');
            return {
                ok: true, status: 200,
                json: async () => [
                    { id: `tmdb_${currentMovieStep}`, name: `Film ${currentMovieStep} (2020)`, provider: 'tmdb' },
                    { id: `ofdb_${currentMovieStep}`, name: `Film ${currentMovieStep} (2020)`, provider: 'ofdb' },
                ],
            };
        }
        if (url.startsWith('/api/metadata/fetch')) {
            if (currentMovieStep === 2) {
                return {
                    ok: true, status: 200,
                    json: async () => ({
                        providers: {
                            tmdb: { provider: 'tmdb', movie_id: 'tmdb_2', status: 'ok', error: null, fields: { title: 'Dune Teil 2', year: '2024', plot: 'Arrakis', fsk: '12', genres: ['Sci-Fi'] } },
                            ofdb: { provider: 'ofdb', movie_id: 'ofdb_2', status: 'error', error: 'HTTP 503', fields: null },
                        },
                        provider_order: ['tmdb', 'ofdb'],
                    }),
                };
            }
            return {
                ok: true, status: 200,
                json: async () => ({
                    providers: {
                        tmdb: { provider: 'tmdb', movie_id: 'tmdb_3', status: 'error', error: 'Timeout', fields: null },
                        ofdb: { provider: 'ofdb', movie_id: 'ofdb_3', status: 'error', error: 'Timeout', fields: null },
                    },
                    provider_order: ['tmdb', 'ofdb'],
                }),
            };
        }
        if (url === '/api/preview_process') {
            const body = JSON.parse(options.body || '{}');
            return { ok: true, status: 200, json: async () => ({ destination: `/mnt/nas/Filme/${body.movie_name}`, renames: [{ old: 'a.mkv', new: 'b.mkv' }], subs: [], junk: [] }) };
        }
        if (url === '/api/process') {
            processPayloads.push(JSON.parse(options.body || '{}'));
            return { ok: true, status: 200, json: async () => ({ status: 'queued' }) };
        }
        return { ok: true, status: 200, json: async () => ({}) };
    };

    const { doc, wizard } = setupInboxAndWizardHarness({ fetchImpl: mockFetch });
    wizard.open({
        queue: [
            { projectName: 'Dune.1.2021', query: 'Dune 1' },
            { projectName: 'Dune.2.2024', query: 'Dune 2' },
            { projectName: 'Dune.3.Messiah', query: 'Dune 3' },
        ],
    });
    await flushAsync();

    // (a) Search error at Film 1 -> error chip in header; trigger an in-flight search on Film 1, then skip to Film 2
    assert.match(doc.getElementById('mw-wizard-queue-error-chip').textContent, /Provider-Suche fehlgeschlagen/);
    wizard.performSearch('Delayed Film 1');
    assert.equal(typeof delayedFilm1Reject, 'function');

    currentMovieStep = 2;
    doc.getElementById('mw-wizard-queue-skip-btn').click();
    await flushAsync();
    assert.equal(processPayloads.length, 0);
    assert.equal(doc.getElementById('mw-wizard-queue-label').textContent, 'Film 2 von 3 · Dune.2.2024');
    assert.match(doc.getElementById('mw-wizard-queue-status').textContent, /1 übersprungen/);
    assert.equal(doc.getElementById('mw-wizard-queue-error-chip'), null, 'detached error chip from Film 1 must not be present on Film 2');

    // Delayed rejection from Film 1 arrives AFTER Film 2's search already succeeded -> must be ignored!
    delayedFilm1Reject(new Error('Später Timeout von Film 1'));
    await flushAsync();
    assert.equal(doc.getElementById('mw-wizard-queue-error-chip'), null);
    assert.equal(wizard.getQueueState().items[1].hadError, false);
    assert.equal(doc.getElementById('mw-wizard-error-banner').classList.contains('hidden'), true);
    assert.ok(doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item'));

    // (b) Partial provider failure at Film 2 -> partial-success chip in header, continues via Next -> Skip -> Execute
    doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item').click();
    await flushAsync();
    assert.match(doc.getElementById('mw-wizard-queue-error-chip').textContent, /Teil-Erfolg \(OFDb nicht erreichbar\)/);
    assert.equal(doc.getElementById('mw-wizard-nfo-title').value, 'Dune Teil 2');
    doc.getElementById('mw-wizard-btn-next').click();
    await flushAsync();
    doc.getElementById('mw-wizard-btn-skip').click();
    await flushAsync();
    currentMovieStep = 3;
    doc.getElementById('mw-wizard-btn-execute').click();
    await flushAsync();
    assert.equal(processPayloads.length, 1);
    assert.equal(processPayloads[0].project_name, 'Dune.2.2024');
    assert.equal(doc.getElementById('mw-wizard-queue-label').textContent, 'Film 3 von 3 · Dune.3.Messiah');
    assert.equal(doc.getElementById('mw-wizard-queue-error-chip'), null);

    // (c) Full metadata failure at Film 3 -> error chip in header, manual input in Step 2 -> Next -> Skip -> Execute
    doc.getElementById('mw-wizard-search-results').querySelector('.mw-wizard-search-item').click();
    await flushAsync();
    assert.match(doc.getElementById('mw-wizard-queue-error-chip').textContent, /Metadaten-Abruf fehlgeschlagen/);
    doc.getElementById('mw-wizard-nfo-title').value = 'Dune Messiah';
    doc.getElementById('mw-wizard-nfo-title').dispatchEvent({ type: 'input' });
    doc.getElementById('mw-wizard-nfo-year').value = '2026';
    doc.getElementById('mw-wizard-nfo-year').dispatchEvent({ type: 'input' });
    doc.getElementById('mw-wizard-btn-next').click();
    await flushAsync();
    doc.getElementById('mw-wizard-btn-skip').click();
    await flushAsync();
    doc.getElementById('mw-wizard-btn-execute').click();
    await flushAsync();

    assert.equal(processPayloads.length, 2);
    assert.equal(processPayloads[1].project_name, 'Dune.3.Messiah');
    assert.equal(processPayloads[1].movie_name, 'Dune Messiah (2026)');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);
    assert.deepEqual(wizard.getQueueState().items.map((it) => it.status), ['skipped', 'queued', 'queued']);
});

// ============================================================================
// Inbox Edge Cases (#77 pruning, processing skip, exclusive locks, deselect) & Theme/DOM Sync
// ============================================================================
test('E6 Inbox Edge Cases & Theme Check: #77 unavailable and processing movie pruning, exclusive checkbox locks, and CSS variable-only styling', () => {
    const { doc, wizard, sandbox, alerts } = setupInboxAndWizardHarness();
    sandbox.renderSmartInboxList([
        { project: 'FilmA.2020', media_type: 'movie', is_dir: true, video_count: 1 },
        { project: 'Film "B".mkv', media_type: 'movie', is_dir: false, video_count: 1 },
        { project: 'FilmProcessing.mkv', media_type: 'movie', is_dir: false, video_count: 1 },
        { project: 'SerieA.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 },
    ], new Set());
    const inboxList = doc.getElementById('smart-inbox-list');
    const movieCbs = inboxList.querySelectorAll('.smart-inbox-movie-cb');
    const seriesCb = inboxList.querySelector('.smart-inbox-cb');

    // Selecting 1 movie shows singular button label without count and locks series checkbox
    movieCbs[0].checked = true;
    movieCbs[0].dispatchEvent({ type: 'change' });
    assert.equal(doc.getElementById('btn-bulk-queue-movies').textContent, 'Als Filmreihe verarbeiten');
    assert.equal(seriesCb.disabled, true);
    assert.equal(seriesCb.getAttribute('title'), 'Erst Filmreihe starten oder Auswahl aufheben');

    // Selecting all 3 movies shows count (3) on button
    for (const el of movieCbs.slice(1)) {
        el.checked = true;
        el.dispatchEvent({ type: 'change' });
    }
    assert.equal(doc.getElementById('smart-inbox-bulk-count').textContent, '3 Filme ausgewählt');
    assert.equal(doc.getElementById('btn-bulk-queue-movies').textContent, 'Als Filmreihe verarbeiten (3)');
    assert.equal(doc.getElementById('btn-bulk-group-series'), null);

    // Film "B".mkv disappears AND FilmProcessing.mkv enters activeProjectsProcessing before click -> both skipped with alert, only FilmA.2020 starts in queue
    sandbox.getActiveProjectsProcessing().add('FilmProcessing.mkv');
    sandbox.setCurrentSmartInboxRawSuggestions([
        { project: 'FilmA.2020', media_type: 'movie', is_dir: true, video_count: 1 },
        { project: 'FilmProcessing.mkv', media_type: 'movie', is_dir: false, video_count: 1 },
        { project: 'SerieA.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 },
    ]);
    doc.getElementById('btn-bulk-queue-movies').click();
    assert.equal(alerts.length, 1);
    assert.match(alerts[0], /2 Einträge sind nicht mehr in der Inbox und wurden übersprungen/);
    assert.equal(wizard.getQueueState().active, true);
    assert.equal(wizard.getQueueState().total, 1);
    assert.equal(wizard.getQueueState().items[0].projectName, 'FilmA.2020');

    // Queue start cleared movie selection -> series checkbox is unlocked again
    assert.equal(seriesCb.disabled, false);
    assert.equal(seriesCb.getAttribute('title'), null);

    // Selecting series checkbox locks movie checkboxes and shows new series button text
    seriesCb.checked = true;
    seriesCb.dispatchEvent({ type: 'change' });
    assert.equal(movieCbs[0].disabled, true);
    assert.equal(movieCbs[0].getAttribute('title'), 'Erst Serien-Auswahl starten oder Auswahl aufheben');
    assert.equal(doc.getElementById('btn-bulk-group-series').textContent, 'Ausgewählte Folgen als Serie verarbeiten');

    doc.getElementById('btn-bulk-deselect').click();
    assert.equal(sandbox.selectedInboxProjects.size, 0);
    assert.equal(sandbox.selectedInboxMovieProjects.size, 0);
    assert.equal(movieCbs[0].disabled, false);
    assert.equal(doc.getElementById('smart-inbox-bulk-actions').style.display, 'none');

    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const styleCss = fs.readFileSync(styleCssPath, 'utf8');
    assert.match(indexHtml, /id="mw-wizard-series-context"\s+class="mw-wizard-series-context hidden"/);
    assert.match(indexHtml, /id="mw-wizard-queue-label"/);
    assert.match(indexHtml, /id="mw-wizard-queue-status"/);
    assert.match(indexHtml, /id="mw-wizard-queue-skip-btn"/);

    const wizardCssStart = styleCss.indexOf('.mw-wizard-series-context');
    assert.ok(wizardCssStart > 0);
    const queueCssSlice = styleCss.slice(wizardCssStart, styleCss.indexOf('.mw-wizard-title', wizardCssStart));
    assert.match(queueCssSlice, /var\(--bg-surface\)/);
    assert.match(queueCssSlice, /var\(--accent\)/);
    assert.match(queueCssSlice, /var\(--danger\)/);
    assert.doesNotMatch(queueCssSlice, /#[0-9a-fA-F]{3,8}/);
});

// ============================================================================
// E6b (1)-(5): Bidirektionale Medienart-Korrektur (Film <-> Serie), Zero-Jump-Leiste & Superfood Light Kontrast
// ============================================================================
test('E6b: Bidirectional Film <-> Serie override for folders and files, NFO scanProject guard, zero-jump toolbar DOM, and Superfood Light contrast', async () => {
    let scanResponseData = { current_dir: '/inbox', files: ['video.mkv'] };
    const { doc, wizard, sandbox } = setupInboxAndWizardHarness({
        fetchImpl: async (url) => {
            if (String(url).startsWith('/api/scan-project')) {
                return { ok: true, status: 200, json: async () => scanResponseData };
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });
    const suggestions = [
        {
            project: 'Zurück in die Zukunft (1985)',
            suggested_query: 'Zurück in die Zukunft',
            media_type: 'movie',
            is_dir: true,
            video_count: 1,
            single_video_relpath: 'Zurück in die Zukunft (1985)/back1.mkv',
        },
        {
            project: 'Back.to.the.Future.2.1989.mkv',
            suggested_query: 'Back to the Future 2',
            media_type: 'movie',
            is_dir: false,
            video_count: 1,
        },
        {
            project: 'Breaking.Bad.S01E01.mkv',
            suggested_query: 'Breaking Bad',
            media_type: 'tv',
            is_dir: false,
            video_count: 1,
        },
        {
            project: 'Breaking.Bad.S01E03.Folder',
            suggested_query: 'Breaking Bad',
            media_type: 'tv',
            is_dir: true,
            video_count: 1,
            single_video_relpath: 'Breaking.Bad.S01E03.Folder/bb_s01e03.mkv',
        },
    ];
    sandbox.renderSmartInboxList(suggestions, new Set());
    const inboxList = doc.getElementById('smart-inbox-list');

    // (1a) Both movie folder AND loose movie file offer .btn-unlock-movie-series (without "Film (für Serie gesperrt)"), switch to Serie, and reset back to Film
    for (const movieProj of ['Zurück in die Zukunft (1985)', 'Back.to.the.Future.2.1989.mkv']) {
        const row = inboxList.querySelector(`[data-project="${movieProj}"]`);
        assert.ok(row, `Row for ${movieProj} must exist`);
        assert.equal(row.innerHTML.includes('Film (für Serie gesperrt)'), false);
        assert.ok(row.querySelector('.smart-inbox-movie-cb'));
        assert.equal(row.querySelector('.smart-inbox-cb'), null);
        assert.equal(row.querySelector('.btn-select-smart').getAttribute('data-media-type'), 'movie');
        const unlockBtn = row.querySelector('.btn-unlock-movie-series');
        assert.ok(unlockBtn, `${movieProj} must offer .btn-unlock-movie-series`);
        assert.equal(unlockBtn.textContent, 'Als Serie / Folge behandeln');

        unlockBtn.click();
        const rowUnlocked = inboxList.querySelector(`[data-project="${movieProj}"]`);
        assert.ok(rowUnlocked.querySelector('.smart-inbox-cb'), `${movieProj} unlocked as series must get .smart-inbox-cb`);
        assert.equal(rowUnlocked.querySelector('.smart-inbox-movie-cb'), null);
        assert.equal(rowUnlocked.querySelector('.btn-select-smart').getAttribute('data-media-type'), 'tv');
        const resetBtn = rowUnlocked.querySelector('.btn-reset-movie-series');
        assert.ok(resetBtn);
        assert.equal(resetBtn.textContent, 'Auf Film zurücksetzen');

        resetBtn.click();
        const rowReset = inboxList.querySelector(`[data-project="${movieProj}"]`);
        assert.ok(rowReset.querySelector('.smart-inbox-movie-cb'), `${movieProj} reset to movie must get .smart-inbox-movie-cb again`);
        assert.equal(rowReset.querySelector('.smart-inbox-cb'), null);
        assert.equal(rowReset.querySelector('.btn-select-smart').getAttribute('data-media-type'), 'movie');
    }

    // (1b) Both loose series episode AND series folder offer .btn-unlock-series-movie ("Als Film behandeln"), switch to Film, and reset back to Serie
    for (const seriesProj of ['Breaking.Bad.S01E01.mkv', 'Breaking.Bad.S01E03.Folder']) {
        const sRow = inboxList.querySelector(`[data-project="${seriesProj}"]`);
        assert.ok(sRow, `Row for ${seriesProj} must exist`);
        assert.ok(sRow.querySelector('.smart-inbox-cb'));
        assert.equal(sRow.querySelector('.smart-inbox-movie-cb'), null);
        assert.equal(sRow.querySelector('.btn-select-smart').getAttribute('data-media-type'), 'tv');
        const sUnlockBtn = sRow.querySelector('.btn-unlock-series-movie');
        assert.ok(sUnlockBtn, `${seriesProj} must offer .btn-unlock-series-movie`);
        assert.equal(sUnlockBtn.textContent, 'Als Film behandeln');

        sUnlockBtn.click();
        assert.equal(doc.getElementById('smart-inbox-group-banner').style.display, 'none', 'Single remaining episode must not trigger auto-group banner');
        const sRowAsMovie = inboxList.querySelector(`[data-project="${seriesProj}"]`);
        assert.ok(sRowAsMovie.querySelector('.smart-inbox-movie-cb'), `${seriesProj} unlocked as movie must get .smart-inbox-movie-cb`);
        assert.equal(sRowAsMovie.querySelector('.smart-inbox-cb'), null);
        assert.equal(sRowAsMovie.querySelector('.btn-select-smart').getAttribute('data-media-type'), 'movie');
        const sResetBtn = sRowAsMovie.querySelector('.btn-reset-series-movie');
        assert.ok(sResetBtn);
        assert.equal(sResetBtn.textContent, 'Auf Serie zurücksetzen');

        sResetBtn.click();
        const sRowReset = inboxList.querySelector(`[data-project="${seriesProj}"]`);
        assert.ok(sRowReset.querySelector('.smart-inbox-cb'), `${seriesProj} reset to series must get .smart-inbox-cb again`);
        assert.equal(sRowReset.querySelector('.smart-inbox-movie-cb'), null);
        assert.equal(sRowReset.querySelector('.btn-select-smart').getAttribute('data-media-type'), 'tv');
    }

    // (1c) scanProject respects explicit override even when folder contains conflicting NFO metadata
    const clickedModes = [];
    const selectedShows = [];
    doc.getElementById('mode-series').addEventListener('click', () => clickedModes.push('series'));
    doc.getElementById('mode-movie').addEventListener('click', () => clickedModes.push('movie'));
    sandbox.setSelectShowStub((meta) => selectedShows.push(meta));

    // Movie folder overridden as Serie, but existing NFO says tmdb_movie -> must stay 'series'
    inboxList.querySelector('[data-project="Zurück in die Zukunft (1985)"] .btn-unlock-movie-series').click();
    scanResponseData = {
        current_dir: '/inbox/Zurück in die Zukunft (1985)',
        files: ['back1.mkv'],
        metadata_provider: 'tmdb_movie',
        metadata_id: '105',
        metadata_name: 'Zurück in die Zukunft',
    };
    await sandbox.scanProject('Zurück in die Zukunft (1985)');
    assert.deepEqual(clickedModes, ['series'], 'Overridden movie->series must activate mode-series despite tmdb_movie NFO');
    assert.equal(selectedShows.length, 1);
    assert.equal(selectedShows[0].id, '105');
    inboxList.querySelector('[data-project="Zurück in die Zukunft (1985)"] .btn-reset-movie-series').click();

    // Series folder overridden as Film, but existing NFO says tvdb -> must stay 'movie'
    clickedModes.length = 0;
    selectedShows.length = 0;
    inboxList.querySelector('[data-project="Breaking.Bad.S01E03.Folder"] .btn-unlock-series-movie').click();
    scanResponseData = {
        current_dir: '/inbox/Breaking.Bad.S01E03.Folder',
        files: ['bb_s01e03.mkv'],
        metadata_provider: 'tvdb',
        metadata_id: '81189',
        metadata_name: 'Breaking Bad',
    };
    await sandbox.scanProject('Breaking.Bad.S01E03.Folder');
    assert.deepEqual(clickedModes, ['movie'], 'Overridden series->movie must activate mode-movie despite tvdb NFO');
    assert.equal(selectedShows.length, 0, 'Overridden series->movie must not invoke selectShow');
    inboxList.querySelector('[data-project="Breaking.Bad.S01E03.Folder"] .btn-reset-series-movie').click();

    // Queue unlocked series-as-movie together with regular movie folder into Filmreihe wizard
    inboxList.querySelector('[data-project="Breaking.Bad.S01E01.mkv"] .btn-unlock-series-movie').click();
    for (const proj of ['Zurück in die Zukunft (1985)', 'Breaking.Bad.S01E01.mkv']) {
        const cb = inboxList.querySelector(`[data-project="${proj}"] .smart-inbox-movie-cb`);
        cb.checked = true;
        cb.dispatchEvent({ type: 'change' });
    }
    assert.equal(doc.getElementById('btn-bulk-queue-movies').textContent, 'Als Filmreihe verarbeiten (2)');
    doc.getElementById('btn-bulk-queue-movies').click();
    await flushAsync();
    assert.equal(wizard.getQueueState().active, true);
    assert.deepEqual(
        wizard.getQueueState().items.map((it) => it.projectName),
        ['Zurück in die Zukunft (1985)', 'Breaking.Bad.S01E01.mkv']
    );

    // Reset series entry back to series -> gets .smart-inbox-cb again
    inboxList.querySelector('[data-project="Breaking.Bad.S01E01.mkv"] .btn-reset-series-movie').click();
    assert.ok(inboxList.querySelector('[data-project="Breaking.Bad.S01E01.mkv"] .smart-inbox-cb'));

    // (2), (3), (5) Zero-jump toolbar DOM parent-child nesting, sticky container hierarchy, and Superfood Light CSS checks
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const styleCss = fs.readFileSync(styleCssPath, 'utf8');

    const { doc: htmlDoc } = createQueueDom();
    htmlDoc.body.innerHTML = indexHtml.replace(/<!--[\s\S]*?-->/g, '').replace(/<!DOCTYPE[^>]*>/i, '');
    const sortBarDom = htmlDoc.getElementById('smart-inbox-sort-bar');
    const bulkActionsDom = htmlDoc.getElementById('smart-inbox-bulk-actions');
    const inboxListDom = htmlDoc.getElementById('smart-inbox-list');
    assert.ok(sortBarDom, '#smart-inbox-sort-bar must exist in index.html DOM');
    assert.ok(bulkActionsDom, '#smart-inbox-bulk-actions must exist in index.html DOM');
    assert.ok(inboxListDom, '#smart-inbox-list must exist in index.html DOM');
    assert.equal(
        bulkActionsDom.parentNode,
        sortBarDom,
        '#smart-inbox-bulk-actions must be a direct DOM child of #smart-inbox-sort-bar (not a sibling)'
    );
    assert.equal(
        sortBarDom.querySelector('#smart-inbox-bulk-actions'),
        bulkActionsDom,
        '#smart-inbox-sort-bar must contain #smart-inbox-bulk-actions as a descendant'
    );
    assert.equal(
        sortBarDom.parentNode,
        inboxListDom.parentNode,
        '#smart-inbox-sort-bar and #smart-inbox-list must share the same parent container so position: sticky spans the full inbox scroll range'
    );

    // Negative control: verify DOM check catches a sibling #smart-inbox-bulk-actions layout
    const { doc: legacyDoc } = createQueueDom();
    legacyDoc.body.innerHTML = '<div><div id="smart-inbox-sort-bar"></div><div id="smart-inbox-bulk-actions"></div><div id="smart-inbox-list"></div></div>';
    assert.notEqual(
        legacyDoc.getElementById('smart-inbox-bulk-actions').parentNode,
        legacyDoc.getElementById('smart-inbox-sort-bar'),
        'DOM parentNode check must reject sibling #smart-inbox-bulk-actions'
    );

    const sortBarRuleMatch = styleCss.match(/#smart-inbox-sort-bar\s*\{([^}]+)\}/);
    assert.ok(sortBarRuleMatch, '#smart-inbox-sort-bar rule must exist in style.css');
    assert.match(sortBarRuleMatch[1], /position:\s*sticky/);
    assert.match(sortBarRuleMatch[1], /top:\s*0/);
    assert.match(sortBarRuleMatch[1], /z-index:\s*10/);
    assert.match(sortBarRuleMatch[1], /flex-wrap:\s*nowrap/);
    assert.match(sortBarRuleMatch[1], /background:\s*var\(--bg-sticky/);

    const hoverRuleMatch = styleCss.match(/\.btn-unlock-movie-series:hover[\s\S]*?\{([^}]+)\}/);
    assert.ok(hoverRuleMatch, '.btn-unlock-movie-series:hover rule must exist');
    assert.match(hoverRuleMatch[1], /color:\s*var\(--text-main\)/);
    assert.match(hoverRuleMatch[1], /background:\s*var\(--bg-hover\)/);
    assert.doesNotMatch(hoverRuleMatch[1], /#fff(?:fff)?\b/i);

    assert.match(styleCss, /--text-on-primary:\s*#ffffff/);
    const btnPrimaryMatch = styleCss.match(/\.btn-primary\s*\{([^}]+)\}/);
    assert.ok(btnPrimaryMatch);
    assert.match(btnPrimaryMatch[1], /color:\s*var\(--text-on-primary\)/);
});
