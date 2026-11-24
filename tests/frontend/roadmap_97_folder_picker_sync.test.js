import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
const filmWizardJsPath = path.resolve(__dirname, '../../gui/static/js/film_wizard.js');
const indexHtmlPath = path.resolve(__dirname, '../../gui/static/index.html');
const styleCssPath = path.resolve(__dirname, '../../gui/static/style.css');

function createMockDom() {
    const byId = new Map();
    const matches = (el, sel) => {
        if (!el || !sel) return false;
        if (sel.startsWith('#')) return el.id === sel.slice(1);
        if (sel.startsWith('.')) return el.classList.contains(sel.slice(1));
        return el.tagName === sel.toUpperCase();
    };
    function makeElement(tagName) {
        const classes = new Set(), attrs = new Map(), listeners = {}, dataset = {};
        let idVal = '', htmlVal = '', textVal = '';
        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '', value: '', checked: false, disabled: false, title: '',
            style: {}, children: [], dataset, parentNode: null, onclick: null,
            get id() { return idVal; },
            set id(v) { idVal = String(v || ''); if (idVal) byId.set(idVal, el); },
            get textContent() { return textVal + el.children.map((c) => c.textContent).join(''); },
            set textContent(v) { textVal = String(v ?? ''); htmlVal = textVal; el.children = []; },
            get innerHTML() { return htmlVal; },
            set innerHTML(v) {
                htmlVal = String(v ?? '');
                textVal = htmlVal.replace(/<[^>]*>/g, '');
                el.children = [];
            },
            get className() { return Array.from(classes).join(' '); },
            set className(v) {
                classes.clear();
                String(v || '').split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
            },
            classList: {
                add: (...ns) => ns.forEach((n) => n && classes.add(n)),
                remove: (...ns) => ns.forEach((n) => classes.delete(n)),
                contains: (n) => classes.has(n),
                toggle: (n, f) => {
                    const add = f !== undefined ? Boolean(f) : !classes.has(n);
                    if (add) classes.add(n); else classes.delete(n);
                    return add;
                },
            },
            setAttribute(k, v) {
                attrs.set(k, String(v));
                if (k === 'id') el.id = v;
                if (k.startsWith('data-')) {
                    dataset[k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(v);
                }
            },
            getAttribute: (k) => (attrs.has(k) ? attrs.get(k) : null),
            hasAttribute: (k) => attrs.has(k),
            removeAttribute: (k) => attrs.delete(k),
            appendChild(child) {
                if (child) {
                    child.parentNode = el;
                    if (child.id) byId.set(child.id, child);
                    if (child.tagName === 'OPTION' && !el.value) el.value = child.value;
                    el.children.push(child);
                }
                return child;
            },
            removeChild(child) {
                const i = el.children.indexOf(child);
                if (i !== -1) el.children.splice(i, 1);
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
                const e = { target: el, currentTarget: el, preventDefault() {}, stopPropagation() {}, ...evt };
                (listeners[e.type] || []).forEach((fn) => fn(e));
            },
            querySelectorAll(sel) {
                const out = [];
                const walk = (node) => {
                    for (const ch of node.children || []) {
                        if (matches(ch, sel)) out.push(ch);
                        walk(ch);
                    }
                };
                walk(el);
                return out;
            },
            querySelector(sel) { return el.querySelectorAll(sel)[0] || null; },
        };
        return el;
    }
    const body = makeElement('body');
    const doc = {
        cookie: '',
        documentElement: { scrollTop: 0, style: { setProperty() {}, removeProperty() {} } },
        body,
        createElement: (tag) => makeElement(tag),
        createTextNode: (t) => { const el = makeElement('#text'); el.textContent = t; return el; },
        getElementById(id) {
            if (!id) return null;
            if (!byId.has(id)) {
                const el = makeElement('div');
                el.id = id;
                body.appendChild(el);
            }
            return byId.get(id);
        },
        querySelectorAll: (sel) => body.querySelectorAll(sel),
        querySelector: (sel) => body.querySelector(sel),
        addEventListener: () => {},
    };
    return doc;
}

function setupAppHarness({ fetchImpl, openLocalFolder = false, settings = {} } = {}) {
    const doc = createMockDom();
    const alerts = [], confirms = [], prompts = [];
    let confirmReturn = true, promptReturn = 'cat1';
    const activeFetch = fetchImpl || (async () => ({ ok: true, status: 200, json: async () => ({}) }));

    const stubs = `
const applyTheme = () => {}, cleanSeriesName = (s) => String(s || ''), formatBytes = (b) => b + ' B';
const guessSeasonAndEpisode = () => null, guessEpisodeNumber = () => 1, cleanFilenameForManualTitle = (f) => f;
const osBasename = (p) => String(p || ''), formatFskLabel = (f) => f, fetchStats = async () => ({});
const fetchYoutubeSubscriptions = async () => [], fetchSmartInboxSuggestions = async () => [];
const loadConversionRecommendations = async () => {}, triggerQualityHintUpdates = () => {}, updateMwDataPanel = () => {};
const prepareSeriesPayload = (s, p) => p, setupMaskedInput = () => {}, setMaskedInputValue = () => {};
const validateAllMaskedFields = () => true, initFilmWizard = () => ({}), openFilmWizard = () => {};
const renderNfoEditor = () => ({}), buildMovieNfoOverrides = () => ({}), buildWizardMovieOverrides = () => ({});
const normalizeFsk = (v) => v, parseGenres = (v) => v, renderPreviewData = () => {}, collectPreviewSelection = () => ({});
`;
    const cleanAppJs = stubs + fs.readFileSync(appJsPath, 'utf8').replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '') + `
globalThis.__setSettings = (s) => { currentSettings = s; };
globalThis.__getSettings = () => currentSettings;
globalThis.__setCurrentProject = (p) => { currentProject = p; };
globalThis.__getCurrentProject = () => currentProject;
globalThis.__setRawSuggestions = (arr) => { currentSmartInboxRawSuggestions = arr; };
globalThis.__getActiveProcessing = () => activeProjectsProcessing;
globalThis.getConfiguredPickerRoots = getConfiguredPickerRoots;
globalThis.normalizePickerPath = normalizePickerPath;
globalThis.isPathWithinRoot = isPathWithinRoot;
globalThis.openToolRunnerModal = openToolRunnerModal;
globalThis.initViews = initViews;
globalThis.initEventListeners = initEventListeners;
globalThis.initHealthDashboard = initHealthDashboard;
`;
    const win = {
        fetch: activeFetch, scrollTo: () => {}, addEventListener: () => {}, goHome: () => {},
        AppCapabilities: { runtime: openLocalFolder ? 'desktop' : 'docker', dev_mode: false, capabilities: { open_local_folder: openLocalFolder } },
    };
    const sandbox = {
        document: doc, window: win, fetch: activeFetch,
        Event: class { constructor(type) { this.type = type; } },
        localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        sessionStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 0; },
        clearTimeout: () => {}, setInterval: () => 0, clearInterval: () => {},
        queueMicrotask: (fn) => { if (typeof fn === 'function') fn(); },
        alert: (msg) => { alerts.push(String(msg)); },
        confirm: (msg) => { confirms.push(String(msg)); return confirmReturn; },
        prompt: (msg, def) => { prompts.push({ msg: String(msg), def }); return promptReturn; },
        console: { log: () => {}, warn: () => {}, error: () => {} },
        EventSource: class { close() {} }, AbortController,
    };
    sandbox.globalThis = sandbox;
    vm.runInNewContext(cleanAppJs, sandbox);

    win.AppCapabilities = {
        runtime: openLocalFolder ? 'desktop' : 'docker',
        dev_mode: false,
        capabilities: { open_local_folder: openLocalFolder },
    };

    doc.getElementById('folder-picker-roots').classList.add('hidden');
    doc.getElementById('view-library').className = 'view-panel hidden';
    doc.getElementById('view-tools').className = 'view-panel hidden';
    sandbox.__setSettings(settings);
    sandbox.initViews();
    sandbox.initEventListeners();
    sandbox.initHealthDashboard();

    return {
        doc, win, sandbox, alerts, confirms, prompts,
        setConfirmReturn: (val) => { confirmReturn = Boolean(val); },
        setPromptReturn: (val) => { promptReturn = val; },
    };
}

const flushAsync = () => new Promise((r) => setTimeout(r, 0));

// ============================================================================
// AK 1: Multi-Root-Umschalter, Pfad-Kanonisierung & Wurzel-Deduplizierung
// ============================================================================
test('ROADMAP #97 AK1: Multi-root switcher filters invalid/cloud paths, canonicalizes slashes, deduplicates import/download roots, and switches roots cleanly', async () => {
    const requestedPaths = [];
    const subMap = {
        '/media/inbox': ['IncomingA'],
        '/media/outbox': ['Serien', 'Filme'],
        '/media/nas': ['Filme', 'Serien'],
        '/media/nas/Filme': ['Matrix (1999)'],
    };

    const { doc, sandbox } = setupAppHarness({
        openLocalFolder: false,
        settings: {
            inbox_dir: '/media/inbox/',
            outbox_dir: '/media/outbox',
            nas_root: '',
            import_sources: ['', '   ', 'smb://nas.local/share'],
            local_download_folders: [{ name: 'Leer', path: '   ' }],
            storage_targets: [
                { id: 'nas', name: 'Speicherziel 1 (NAS)', type: 'nas', root_path: '/media/nas/', enabled: true },
                { id: 'pcloud', name: 'pCloud Backup', type: 'pcloud', root_path: '/Users/alex/pCloud', enabled: true },
                { id: 'disabled_target', name: 'Aus', type: 'nas', root_path: '/media/disabled', enabled: false },
            ],
            sync_categories: [{ id: '1', name: 'Filme', nas_sub: '/Filme' }],
        },
        fetchImpl: async (url) => {
            if (String(url).startsWith('/api/list-subfolders')) {
                const p = new URL(url, 'http://localhost').searchParams.get('path');
                requestedPaths.push(p);
                return { ok: true, status: 200, json: async () => ({ subfolders: subMap[p] || [] }) };
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    // 1) Parametrized normalizePickerPath checks (including embedded repeated slashes)
    for (const [raw, expected] of [
        ['', ''],
        ['   ', ''],
        ['/', '/'],
        ['///', '/'],
        ['/media/nas///', '/media/nas'],
        ['/media//nas', '/media/nas'],
        ['//media///nas//', '/media/nas'],
        ['smb://nas.local/share/', 'smb://nas.local/share'],
    ]) {
        assert.equal(sandbox.normalizePickerPath(raw), expected, `normalizePickerPath(${JSON.stringify(raw)})`);
    }

    // 2) getConfiguredPickerRoots with valid import_sources, local_download_folders, legacy nas_root & deduplication
    const richRoots = sandbox.getConfiguredPickerRoots({
        inbox_dir: '/media/inbox',
        outbox_dir: '/media/outbox/',
        nas_root: '/media/legacy_nas/',
        storage_targets: [{ id: 'nas', name: 'NAS 1', type: 'nas', root_path: '/media/nas', enabled: true }],
        import_sources: ['/media/import_usb/', { path: '/media/import_sd' }, '/media//import_usb', '/media/inbox', 'smb://host/share', '/'],
        local_download_folders: ['/media/dl_raw/', { name: 'JD2', path: '/media/jd2/' }, { name: 'Dup', path: '/media//jd2' }],
    }, false);
    assert.deepEqual(
        JSON.parse(JSON.stringify(richRoots.map((r) => ({ label: r.label, path: r.path })))),
        [
            { label: 'Input-Ordner', path: '/media/inbox' },
            { label: 'Output-Ordner', path: '/media/outbox' },
            { label: 'NAS 1', path: '/media/nas' },
            { label: 'NAS', path: '/media/legacy_nas' },
            { label: 'Import: import_usb', path: '/media/import_usb' },
            { label: 'Import: import_sd', path: '/media/import_sd' },
            { label: 'Download: dl_raw', path: '/media/dl_raw' },
            { label: 'JD2', path: '/media/jd2' },
        ]
    );

    // 3) Open tool_manual_sync -> pre-fills /media/outbox -> click Browse
    sandbox.openToolRunnerModal('tool_manual_sync', 'Speicherziel-Syncing', 'Sync');
    const targetInput = doc.getElementById('tool-modal-target-path');
    assert.equal(targetInput.value, '/media/outbox');

    doc.getElementById('btn-browse-tool-modal-path').click();
    await flushAsync();

    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/outbox');
    const rootsContainer = doc.getElementById('folder-picker-roots');
    assert.equal(rootsContainer.classList.contains('hidden'), false);
    const rootBtns = rootsContainer.querySelectorAll('.folder-picker-root-btn');
    assert.equal(rootBtns.length, 3);
    assert.deepEqual(rootBtns.map((b) => b.getAttribute('aria-pressed')), ['false', 'true', 'false']);

    const upBtn = doc.getElementById('folder-picker-up-btn');
    assert.equal(upBtn.disabled, true);

    // 4) Switch to "Speicherziel 1 (NAS)" -> drill into Filme -> select folder
    rootBtns[2].click();
    await flushAsync();
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/nas');
    assert.equal(upBtn.disabled, true, 'upBtn disabled at /media/nas root to prevent 403 on /media');

    doc.getElementById('folder-picker-list').querySelectorAll('li')[0].click(); // 'Filme'
    await flushAsync();
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/nas/Filme');
    assert.equal(upBtn.disabled, false);

    doc.getElementById('folder-picker-select-btn').click();
    assert.equal(targetInput.value, '/media/nas/Filme');
    assert.ok(!requestedPaths.includes('/media'));
});

// ============================================================================
// AK 2: Verschachtelte Docker-Standard-Wurzeln (NAS=/media, Output=/media/Output)
// ============================================================================
test('ROADMAP #97 AK2: Nested Docker roots (NAS=/media, Input=/media/Input, Output=/media/Output) highlight deepest root without locking upBtn at /media/Output', async () => {
    const subMap = { '/media': ['Input', 'Output', 'Filme'], '/media/Output': ['FertigFilm (2024)'] };
    const { doc, win } = setupAppHarness({
        openLocalFolder: false,
        settings: {
            inbox_dir: '/media/Input',
            outbox_dir: '/media/Output',
            storage_targets: [{ id: 'nas', name: 'NAS', type: 'nas', root_path: '/media', enabled: true }],
        },
        fetchImpl: async (url) => {
            const p = new URL(url, 'http://localhost').searchParams.get('path');
            return { ok: true, status: 200, json: async () => ({ subfolders: subMap[p] || [] }) };
        },
    });

    win.openFolderPicker('/media', '', null, 'Ordner wählen', () => {}, { multiRoot: true });
    await flushAsync();

    const upBtn = doc.getElementById('folder-picker-up-btn');
    const rootsContainer = doc.getElementById('folder-picker-roots');
    assert.equal(upBtn.disabled, true);

    const outputLi = doc.getElementById('folder-picker-list').querySelectorAll('li').find((li) => li.textContent.includes('Output'));
    outputLi.click();
    await flushAsync();

    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/Output');
    const btns = rootsContainer.querySelectorAll('.folder-picker-root-btn');
    assert.equal(btns.find((b) => b.dataset.rootPath === '/media/Output').getAttribute('aria-pressed'), 'true');
    assert.equal(upBtn.disabled, false, 'upBtn MUST remain enabled on /media/Output because parent /media is in allowedRoots');

    upBtn.click();
    await flushAsync();
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media');
    assert.equal(upBtn.disabled, true);
});

// ============================================================================
// AK 3: Präfix-Kollisionsschutz, Fehler-Fallbacks & Async-Request-Generation
// ============================================================================
test('ROADMAP #97 AK3: Segment boundary check, single-root fallback, unreachable fallback root error, and stale async response protection', async () => {
    const requested = [];
    const pendingResolvers = {};
    let mode = 'default';

    const { doc, win, sandbox } = setupAppHarness({
        openLocalFolder: false,
        settings: {
            inbox_dir: '/media/inbox',
            outbox_dir: '/media/outbox',
            storage_targets: [{ id: 'nas', name: 'NAS', type: 'nas', root_path: '/media/nas/', enabled: true }],
        },
        fetchImpl: (url) => {
            const p = new URL(url, 'http://localhost').searchParams.get('path');
            requested.push(p);
            if (mode === 'delayed' && (p === '/media/outbox/Geloescht' || p === '/media/inbox')) {
                return new Promise((resolve) => { pendingResolvers[p] = resolve; });
            }
            if (mode === 'both_fail') {
                return Promise.resolve({ ok: true, status: 200, json: async () => ({ error: `Fehler auf ${p}` }) });
            }
            if (p === '/media/outbox/Geloescht') {
                return Promise.resolve({ ok: true, status: 200, json: async () => ({ error: 'Der angegebene Pfad existiert nicht.' }) });
            }
            return Promise.resolve({ ok: true, status: 200, json: async () => ({ subfolders: p === '/media/nas' ? ['Filme', 'Serien'] : ['Sub1'] }) });
        },
    });

    // 1) Segment boundary check (including repeated slashes)
    assert.equal(sandbox.isPathWithinRoot('/media/inbox', '/media/inbox'), true);
    assert.equal(sandbox.isPathWithinRoot('/media//inbox/sub', '/media/inbox'), true);
    assert.equal(sandbox.isPathWithinRoot('/media/inbox2', '/media/inbox'), false);
    assert.equal(sandbox.isPathWithinRoot('/media/inbox2/sub', '/media/inbox'), false);

    // 2) Single-root mode with colliding prefix "/media/inbox2/sub" -> falls back to "/media/inbox"
    win.openFolderPicker('/media/inbox2/sub', '/media/inbox', null, 'Single Root Test', () => {});
    await flushAsync();
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/inbox');
    assert.equal(doc.getElementById('folder-picker-roots').classList.contains('hidden'), true);
    assert.equal(doc.getElementById('folder-picker-up-btn').disabled, true);

    // 3) One-time fallback when start subfolder is deleted
    requested.length = 0;
    win.openFolderPicker('/media/outbox/Geloescht', '', null, 'Fallback Test', () => {}, { multiRoot: true });
    await flushAsync();
    assert.deepEqual(requested, ['/media/outbox/Geloescht', '/media/outbox']);
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/outbox');
    assert.equal(doc.getElementById('folder-picker-error').classList.contains('hidden'), true);

    // 4) Unreachable fallback root itself fails -> no infinite loop, shows error
    mode = 'both_fail';
    requested.length = 0;
    win.openFolderPicker('/media/outbox/Geloescht', '', null, 'Unreachable Root Test', () => {}, { multiRoot: true });
    await flushAsync();
    assert.deepEqual(requested, ['/media/outbox/Geloescht', '/media/outbox']);
    assert.equal(doc.getElementById('folder-picker-error').classList.contains('hidden'), false);
    assert.equal(doc.getElementById('folder-picker-error').textContent, 'Fehler auf /media/outbox');

    // 5) Async race protection: open with delayed /media/outbox/Geloescht AND delayed /media/inbox, then switch to NAS (/media/nas)
    mode = 'delayed';
    requested.length = 0;
    win.openFolderPicker('/media/outbox/Geloescht', '', null, 'Race Test', () => {}, { multiRoot: true });
    const rootBtns = doc.getElementById('folder-picker-roots').querySelectorAll('.folder-picker-root-btn');
    rootBtns[0].click(); // /media/inbox (also delayed)
    rootBtns[2].click(); // /media/nas (resolves immediately)
    await flushAsync();

    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/nas');
    assert.deepEqual(doc.getElementById('folder-picker-list').querySelectorAll('li').map((li) => li.textContent), ['Filme', 'Serien']);

    // Now resolve the stale error for /media/outbox/Geloescht and stale success for /media/inbox
    pendingResolvers['/media/outbox/Geloescht']({ ok: true, status: 200, json: async () => ({ error: 'Stale error' }) });
    pendingResolvers['/media/inbox']({ ok: true, status: 200, json: async () => ({ subfolders: ['StaleInboxSub'] }) });
    await flushAsync();

    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/nas', 'Stale error must not trigger fallback to /media/outbox');
    assert.equal(doc.getElementById('folder-picker-error').classList.contains('hidden'), true);
    assert.deepEqual(doc.getElementById('folder-picker-list').querySelectorAll('li').map((li) => li.textContent), ['Filme', 'Serien']);
});

// ============================================================================
// AK 4: Hauptordner- & Punktpfad-Sperre (inkl. // und tool_pcloud_sync / Confirm-Tools)
// ============================================================================
test('ROADMAP #97 AK4: Root & dot-path safety stop blocks canonical and double-slash roots for both sync tools, requires confirm for batch/clean/pull tools, and guards duplicate runs', async () => {
    const apiCalls = [];
    const { doc, sandbox, alerts, confirms, setConfirmReturn, setPromptReturn } = setupAppHarness({
        openLocalFolder: false,
        settings: {
            inbox_dir: '/media/inbox',
            outbox_dir: '/media/outbox',
            import_sources: ['/media/import_usb'],
            local_download_folders: [{ name: 'JD2', path: '/media/jd2' }],
            storage_targets: [
                { id: 'nas', name: 'Haupt-NAS', type: 'nas', root_path: '/media/nas', enabled: true },
                { id: 'pcloud', name: 'pCloud', type: 'pcloud', root_path: '/cloud', enabled: true },
            ],
            sync_categories: [{ id: 'cat1', name: 'Filme', nas_sub: '/Filme' }],
        },
        fetchImpl: async (url, opts = {}) => {
            if (url === '/api/process' || url === '/api/preview_clean') {
                apiCalls.push({ url, body: JSON.parse(opts.body) });
            }
            return { ok: true, status: 200, json: async () => ({ status: 'ok', groups: {} }) };
        },
    });

    const modal = doc.getElementById('modal-tool-runner');
    const pathInput = doc.getElementById('tool-modal-target-path');
    const executeBtn = doc.getElementById('btn-tool-modal-execute');

    // 1) Both sync tools (tool_manual_sync & tool_pcloud_sync): prefill, shortcuts, hard block on all roots (incl. //) & dot-paths, allow subfolder
    const blockedSyncPaths = [
        '/media/nas', '/media//nas', '//media///nas//',
        '/media/outbox', '/media//outbox/',
        '/media/inbox', '/media//inbox',
        '/media/import_usb', '/media/jd2', '/cloud',
        '/', '///', '.', '..', './..', '/media/nas/..', '/media//nas//..',
    ];
    for (const syncTool of ['tool_manual_sync', 'tool_pcloud_sync']) {
        sandbox.openToolRunnerModal(syncTool, 'Sync', 'Desc');
        assert.equal(modal.classList.contains('active'), true);
        assert.equal(pathInput.value, '/media/outbox');

        const shortcutBtns = doc.getElementById('tool-modal-target-shortcuts').querySelectorAll('.tool-modal-shortcut-target-btn');
        assert.equal(shortcutBtns.length, 1);
        shortcutBtns[0].click();
        assert.equal(pathInput.value, '/media/nas');

        for (const blockedPath of blockedSyncPaths) {
            alerts.length = 0;
            pathInput.value = blockedPath;
            executeBtn.click();
            await flushAsync();
            assert.equal(alerts.length, 1, `${syncTool} with "${blockedPath}" must trigger safety alert`);
            assert.match(alerts[0], /Sicherheits-Stopp/);
            assert.equal(modal.classList.contains('active'), true);
            assert.equal(apiCalls.length, 0);
        }

        // Valid subfolder succeeds for both tool_manual_sync and tool_pcloud_sync
        setPromptReturn('cat1');
        pathInput.value = '/media/nas/Filme/Matrix (1999)';
        executeBtn.click();
        await flushAsync();
        assert.equal(apiCalls.length, 1);
        assert.equal(apiCalls[0].body.media_type, syncTool);
        assert.equal(apiCalls[0].body.project_name, '/media/nas/Filme/Matrix (1999)');
        assert.equal(modal.classList.contains('active'), false);
        apiCalls.length = 0;
    }

    // 2) Parametrized confirmation check on canonical & double-slash roots for tool_pull_files, tool_batch_convert, tool_clean
    for (const [toolType, rootCandidate, expectedUrl] of [
        ['tool_pull_files', '/media//inbox', '/api/process'],
        ['tool_batch_convert', '/media///nas//', '/api/process'],
        ['tool_clean', '/media//outbox', '/api/preview_clean'],
    ]) {
        confirms.length = 0;
        apiCalls.length = 0;
        sandbox.openToolRunnerModal(toolType, 'Tool', 'Desc', toolType === 'tool_batch_convert');
        pathInput.value = rootCandidate;

        setConfirmReturn(false);
        executeBtn.click();
        await flushAsync();
        assert.equal(confirms.length, 1, `${toolType} on ${rootCandidate} must ask confirm`);
        assert.equal(modal.classList.contains('active'), true);
        assert.equal(apiCalls.length, 0);

        setConfirmReturn(true);
        executeBtn.click();
        await flushAsync();
        assert.equal(confirms.length, 2);
        assert.equal(modal.classList.contains('active'), false);
        assert.equal(apiCalls.length, 1);
        assert.equal(apiCalls[0].url, expectedUrl);
    }

    // 3) Duplicate processing guard checks relative, canonical and double-slash inbox paths
    sandbox.__getActiveProcessing().add('MyMovieFolder');
    sandbox.openToolRunnerModal('tool_pull_files', 'Pull', 'Pull');
    pathInput.value = '/media//inbox//MyMovieFolder';
    alerts.length = 0;
    executeBtn.click();
    await flushAsync();
    assert.equal(alerts.length, 1);
    assert.match(alerts[0], /bereits verarbeitet/);
    sandbox.__getActiveProcessing().clear();
});

// ============================================================================
// AK 5: #btn-lib-tools-browse (Docker vs. Desktop) & currentProject-Hygiene
// ============================================================================
test('ROADMAP #97 AK5: #btn-lib-tools-browse respects Docker vs. Desktop mode, openLibraryView clears currentProject, and single-file / __inbox_recursive__ paths resolve safely', async () => {
    const requestedUrls = [];
    const { doc, win, sandbox } = setupAppHarness({
        openLocalFolder: false,
        settings: {
            inbox_dir: '/media/inbox',
            outbox_dir: '/media/outbox',
            storage_targets: [{ id: 'nas', name: 'NAS', type: 'nas', root_path: '/media/nas', enabled: true }],
        },
        fetchImpl: async (url) => {
            requestedUrls.push(String(url));
            if (String(url).startsWith('/api/browse-folder')) {
                return { ok: true, status: 200, json: async () => ({ status: 'ok', path: '/Users/alex/Movies/Picked' }) };
            }
            return { ok: true, status: 200, json: async () => ({ subfolders: ['Archive'] }) };
        },
    });

    sandbox.__setCurrentProject('__inbox_recursive__');
    sandbox.openToolRunnerModal('tool_pull_files', 'Pull', 'Desc');
    assert.equal(doc.getElementById('tool-modal-target-path').value, '/media/inbox');

    sandbox.__setCurrentProject('LooseMovie.2024.mkv');
    sandbox.__setRawSuggestions([{ project: 'LooseMovie.2024.mkv', is_dir: false }]);
    sandbox.openToolRunnerModal('tool_pull_files', 'Pull', 'Desc');
    assert.equal(doc.getElementById('tool-modal-target-path').value, 'LooseMovie.2024.mkv');

    doc.getElementById('btn-browse-tool-modal-path').click();
    await flushAsync();
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/inbox');
    win.closeFolderPicker();

    win.openLibraryView();
    assert.equal(sandbox.__getCurrentProject(), '');
    sandbox.openToolRunnerModal('tool_pull_files', 'Pull', 'Desc');
    assert.equal(doc.getElementById('tool-modal-target-path').value, '/media/nas');

    const libInput = doc.getElementById('lib-tools-manual-path');
    libInput.value = '';
    doc.getElementById('btn-lib-tools-browse').click();
    await flushAsync();
    assert.equal(doc.getElementById('folder-picker-current-path').textContent, '/media/nas');
    win.closeFolderPicker();

    win.AppCapabilities.capabilities.open_local_folder = true;
    libInput.value = '/Users/alex/Movies';
    doc.getElementById('btn-lib-tools-browse').click();
    await flushAsync();
    assert.ok(requestedUrls.includes('/api/browse-folder?default_path=%2FUsers%2Falex%2FMovies'));
    assert.equal(libInput.value, '/Users/alex/Movies/Picked');
});

// ============================================================================
// AK 6: Statische Rückbau-, A11y- & Cache-Busting-Prüfung
// ============================================================================
test('ROADMAP #97 AK6: Static verification of legacy removal (#sync-modal-overlay, tool_nfo_agent branch), button types, CSS variables, and synchronous cache-busting (v=126 / style.css?v=70)', () => {
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const appJs = fs.readFileSync(appJsPath, 'utf8');
    const filmWizardJs = fs.readFileSync(filmWizardJsPath, 'utf8');
    const styleCss = fs.readFileSync(styleCssPath, 'utf8');

    assert.doesNotMatch(indexHtml, /id="sync-modal-overlay"/);
    assert.doesNotMatch(indexHtml, /id="btn-sync-execute"/);
    assert.doesNotMatch(appJs, /else if\s*\(\s*toolType\s*===\s*["']tool_nfo_agent["']\s*\)/);

    assert.match(indexHtml, /id="tool-modal-target-shortcuts"\s+class="tool-modal-target-shortcuts"/);
    assert.match(indexHtml, /id="folder-picker-roots"\s+class="folder-picker-roots hidden"\s+role="group"\s+aria-label="Verfügbare Wurzelordner"/);

    for (const btnId of ['btn-browse-tool-modal-path', 'btn-tool-modal-cancel', 'btn-tool-modal-execute', 'folder-picker-up-btn', 'folder-picker-select-btn']) {
        const re = new RegExp(`<button[^>]*id="${btnId}"[^>]*type="button"|<button[^>]*type="button"[^>]*id="${btnId}"`);
        assert.match(indexHtml, re, `Button #${btnId} must have explicit type="button"`);
    }
    assert.match(indexHtml, /<button[^>]*type="button"[^>]*onclick="closeFolderPicker\(\)"/);

    assert.match(indexHtml, /href="style\.css\?v=70"/);
    assert.match(indexHtml, /src="app\.js\?v=126"/);

    const appImports = [...appJs.matchAll(/from\s+['"]\.\/js\/[^'"]+\?v=(\d+)['"]/g)];
    assert.equal(appImports.length, 12);
    appImports.forEach((m) => assert.equal(m[1], '126'));

    const wizImports = [...filmWizardJs.matchAll(/from\s+['"]\.\/[^'"]+\?v=(\d+)['"]/g)];
    assert.equal(wizImports.length, 3);
    wizImports.forEach((m) => assert.equal(m[1], '126'));

    for (const selector of ['.tool-modal-shortcuts-row', '.tool-modal-target-shortcuts', '.folder-picker-roots', '.folder-picker-root-btn']) {
        const idx = styleCss.indexOf(selector);
        assert.ok(idx > 0, `${selector} must exist in style.css`);
        const ruleBlock = styleCss.slice(idx, styleCss.indexOf('}', idx) + 1);
        assert.doesNotMatch(ruleBlock, /#[0-9a-fA-F]{3,8}/, `${selector} must not contain raw hex colors`);
    }
});
