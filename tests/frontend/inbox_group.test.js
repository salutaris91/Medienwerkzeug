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

function matchesSelector(el, sel) {
    if (!sel || !el) return false;
    sel = sel.trim();

    if (sel.includes(':checked')) {
        const baseSel = sel.replace(':checked', '').trim();
        return (!baseSel || matchesSelector(el, baseSel)) && Boolean(el.checked);
    }

    if (sel.startsWith('[') && sel.endsWith(']')) {
        const inner = sel.slice(1, -1);
        if (inner.includes('=')) {
            const [attrName, rawVal] = inner.split('=');
            const val = rawVal ? rawVal.replace(/^["']|["']$/g, '') : '';
            return el.getAttribute(attrName) === val;
        } else {
            return el.hasAttribute(inner) || el[inner] === true;
        }
    }

    if (sel.includes('[')) {
        const attrStart = sel.indexOf('[');
        const prefix = sel.slice(0, attrStart);
        const attrPart = sel.slice(attrStart);
        return matchesSelector(el, prefix) && matchesSelector(el, attrPart);
    }

    if (sel.startsWith('#')) {
        return el.id === sel.slice(1);
    }

    if (sel.startsWith('.')) {
        const cls = sel.slice(1);
        return el.classList && el.classList.contains(cls);
    }

    if (el.tagName && el.tagName.toLowerCase() === sel.toLowerCase()) {
        return true;
    }

    return false;
}

function splitSelectorParts(sel) {
    if (!sel) return [];
    const parts = [];
    let current = '';
    let inBracket = false;
    let inQuote = false;
    let quoteChar = '';

    for (let i = 0; i < sel.length; i++) {
        const ch = sel[i];
        if (inQuote) {
            current += ch;
            if (ch === quoteChar) {
                inQuote = false;
            }
        } else if (ch === '"' || ch === "'") {
            inQuote = true;
            quoteChar = ch;
            current += ch;
        } else if (ch === '[') {
            inBracket = true;
            current += ch;
        } else if (ch === ']') {
            inBracket = false;
            current += ch;
        } else if (/\s/.test(ch)) {
            if (inBracket) {
                current += ch;
            } else {
                if (current.trim()) {
                    parts.push(current.trim());
                    current = '';
                }
            }
        } else {
            current += ch;
        }
    }
    if (current.trim()) {
        parts.push(current.trim());
    }
    return parts;
}

function findDescendants(node, parts) {
    if (!parts || parts.length === 0) return [];
    const firstPart = parts[0];
    const remaining = parts.slice(1);

    const matches = [];
    function walk(curr) {
        if (!curr || !curr.__children) return;
        for (const child of curr.__children) {
            if (matchesSelector(child, firstPart)) {
                if (remaining.length === 0) {
                    matches.push(child);
                } else {
                    matches.push(...findDescendants(child, remaining));
                }
            }
            walk(child);
        }
    }
    walk(node);
    return matches;
}

function parseHtmlToMockElements(html) {
    const elements = [];
    const tagRegex = /<([a-z0-9\-]+)([^>]*)>/gi;
    let match;
    let lastSelect = null;
    while ((match = tagRegex.exec(html)) !== null) {
        const tagName = match[1].toLowerCase();
        if (tagName.startsWith('/')) {
            if (tagName === '/select') lastSelect = null;
            continue;
        }
        const attrStr = match[2];
        const el = createMockElement(tagName);

        const classMatch = attrStr.match(/class=["']([^"']+)["']/i);
        if (classMatch) {
            el.className = classMatch[1];
        }

        const idMatch = attrStr.match(/id=["']([^"']+)["']/i);
        if (idMatch) {
            el.id = idMatch[1];
            if (globalThis.__currentElementsById) {
                globalThis.__currentElementsById[idMatch[1]] = el;
            }
        }

        const dataRegex = /data-([a-z0-9\-]+)=["']([^"']*)["']/gi;
        let dMatch;
        while ((dMatch = dataRegex.exec(attrStr)) !== null) {
            const rawVal = dMatch[2]
                .replace(/&quot;/g, '"')
                .replace(/&#039;/g, "'")
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>')
                .replace(/&amp;/g, '&');
            el.setAttribute(`data-${dMatch[1]}`, rawVal);
        }

        const valMatch = attrStr.match(/value=["']([^"']*)["']/i);
        if (valMatch) {
            el.value = valMatch[1]
                .replace(/&quot;/g, '"')
                .replace(/&#039;/g, "'")
                .replace(/&lt;/g, '<')
                .replace(/&gt;/g, '>')
                .replace(/&amp;/g, '&');
        }

        if (tagName === 'select') {
            lastSelect = el;
            el.options = [];
            el.selectedIndex = 0;
        } else if (tagName === 'option') {
            const innerMatch = html.slice(match.index).match(/>([^<]*)</);
            el.text = innerMatch ? innerMatch[1].trim() : el.value;
            if (lastSelect) {
                lastSelect.options.push(el);
                if (lastSelect.value === '' || /\bselected\b/i.test(attrStr)) {
                    lastSelect.value = el.value;
                    lastSelect.selectedIndex = lastSelect.options.length - 1;
                }
            }
        }

        const typeMatch = attrStr.match(/type=["']([^"']+)["']/i);
        if (typeMatch) {
            el.setAttribute('type', typeMatch[1]);
        }

        const ariaRegex = /aria-([a-z0-9\-]+)=["']([^"']*)["']/gi;
        let aMatch;
        while ((aMatch = ariaRegex.exec(attrStr)) !== null) {
            el.setAttribute(`aria-${aMatch[1]}`, aMatch[2]);
        }

        if (/\bchecked\b/i.test(attrStr)) {
            el.checked = true;
        }
        if (/\bdisabled\b/i.test(attrStr)) {
            el.disabled = true;
        }

        const closeTag = `</${tagName}>`;
        const rest = html.slice(match.index + match[0].length);
        const closeIndex = rest.indexOf(closeTag);
        if (closeIndex !== -1) {
            const innerChunk = rest.slice(0, closeIndex);
            el._setInnerHtmlDirect(innerChunk);
        }

        elements.push(el);
    }
    return elements;
}

function createMockElement(tagName = 'div', attributes = {}) {
    const classSet = new Set();
    const listeners = {};
    const children = [];
    const dataset = {};
    const attrs = { ...attributes };
    let innerHtmlVal = '';
    let textContentVal = '';

    const el = {
        tagName: tagName.toUpperCase(),
        id: attributes.id || '',
        value: '',
        checked: false,
        disabled: false,
        get textContent() {
            return textContentVal;
        },
        set textContent(val) {
            textContentVal = String(val);
            innerHtmlVal = String(val);
            children.length = 0;
        },
        _setInnerHtmlDirect: (val) => {
            innerHtmlVal = String(val);
            textContentVal = innerHtmlVal.replace(/<[^>]*>/g, '').trim();
        },
        options: [],
        selectedIndex: 0,
        text: '',
        get className() {
            return Array.from(classSet).join(' ');
        },
        set className(val) {
            classSet.clear();
            if (val) {
                String(val).split(/\s+/).filter(Boolean).forEach(c => classSet.add(c));
            }
        },
        get innerHTML() {
            return innerHtmlVal;
        },
        set innerHTML(val) {
            innerHtmlVal = String(val);
            textContentVal = innerHtmlVal.replace(/<[^>]*>/g, '').trim();
            children.length = 0;
            if (val) {
                const parsed = parseHtmlToMockElements(val);
                parsed.forEach(c => children.push(c));
            }
        },
        style: {
            display: '',
            get cssText() {
                return this._cssText || '';
            },
            set cssText(val) {
                this._cssText = String(val);
                const match = this._cssText.match(/\bdisplay\s*:\s*([^;]+)/i);
                if (match) {
                    this.display = match[1].trim();
                }
            }
        },
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
            if (name === 'disabled') {
                el.disabled = true;
            }
            if (name === 'checked') {
                el.checked = true;
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
        click: async function() {
            if (el.disabled) return;
            const handlers = listeners['click'] || [];
            for (const handler of handlers) {
                await handler.call(el, { type: 'click', target: el, currentTarget: el, preventDefault: () => {} });
            }
            if (typeof el.onclick === 'function') {
                await el.onclick.call(el, { type: 'click', target: el, currentTarget: el, preventDefault: () => {} });
            }
        },
        dispatchEvent: async function(event) {
            if (event.type === 'click' && el.disabled) return;
            if (!event.currentTarget) event.currentTarget = el;
            const handlers = listeners[event.type] || [];
            for (const handler of handlers) {
                await handler.call(el, event);
            }
        },
        querySelector: (sel) => {
            const parts = splitSelectorParts(sel);
            const res = findDescendants(el, parts);
            return res[0] || null;
        },
        querySelectorAll: (sel) => {
            const parts = splitSelectorParts(sel);
            return findDescendants(el, parts);
        },
        appendChild: (child) => {
            children.push(child);
        }
    };

    if (attributes['class']) {
        el.className = attributes['class'];
    }
    if (attributes['data-field']) {
        el.dataset.field = attributes['data-field'];
    }

    return el;
}

function setupTestEnvironment() {
    globalThis.sessionStorage = mockSessionStorage;
    mockSessionStorage.clear();

    const elementsById = {};
    globalThis.__currentElementsById = elementsById;

    function getOrCreateElement(id, tag = 'div') {
        if (!elementsById[id]) {
            elementsById[id] = createMockElement(tag, { id });
        }
        return elementsById[id];
    }

    const cardSmartInbox = getOrCreateElement('card-smart-inbox');
    const smartInboxList = getOrCreateElement('smart-inbox-list');
    const groupBanner = getOrCreateElement('smart-inbox-group-banner');
    const sortBar = getOrCreateElement('smart-inbox-sort-bar');
    const bulkBar = getOrCreateElement('smart-inbox-bulk-actions');

    const btnName = createMockElement('button', { class: 'btn btn-secondary btn-xs smart-inbox-sort-btn', 'data-field': 'name', 'aria-pressed': 'false' });
    btnName.textContent = 'Name';
    const btnDate = createMockElement('button', { class: 'btn btn-secondary btn-xs smart-inbox-sort-btn', 'data-field': 'date', 'aria-pressed': 'false' });
    btnDate.textContent = 'Datum';
    const btnSize = createMockElement('button', { class: 'btn btn-secondary btn-xs smart-inbox-sort-btn', 'data-field': 'size', 'aria-pressed': 'false' });
    btnSize.textContent = 'Größe';

    sortBar.appendChild(btnName);
    sortBar.appendChild(btnDate);
    sortBar.appendChild(btnSize);

    const viewEmpty = getOrCreateElement('view-empty');
    viewEmpty.className = 'view-panel active';

    const viewFolder = getOrCreateElement('view-folder');
    viewFolder.className = 'view-panel hidden';

    const folderModeSelector = getOrCreateElement('folder-mode-selector');
    folderModeSelector.className = '';

    const modeSeries = getOrCreateElement('mode-series');
    const modeMovie = getOrCreateElement('mode-movie');
    const seriesSearchQuery = getOrCreateElement('series-search-query', 'input');
    const seriesSeasonNum = getOrCreateElement('series-season-num', 'input');
    seriesSeasonNum.value = '1';

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

    globalThis.cleanSeriesName = function (name) {
        return (name || '').replace(/\.[^/.]+$/, '').replace(/[._]/g, ' ').trim();
    };

    globalThis.configureSmartInboxButton = (btn, projectName, isProcessing) => {
        if (!btn) return;
        btn.textContent = isProcessing ? 'In Bearbeitung...' : 'Auswählen';
    };

    let deletedProjects = [];
    globalThis.deleteProject = (p) => {
        deletedProjects.push(p);
    };

    globalThis.localStorage = {
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {}
    };

    const docListeners = {};
    globalThis.document = {
        cookie: '',
        documentElement: {
            scrollTop: 0,
            style: {
                setProperty: () => {},
                removeProperty: () => {}
            }
        },
        body: { scrollTop: 0 },
        getElementById: (id) => getOrCreateElement(id),
        createElement: (tag) => createMockElement(tag),
        querySelectorAll: (sel) => {
            const parts = splitSelectorParts(sel);
            if (parts.length > 0 && parts[0] === '#smart-inbox-list') {
                return findDescendants(smartInboxList, parts.slice(1));
            }
            const matchingContainer = elementsById['matching-panel-container'];
            if (matchingContainer) {
                const found = findDescendants(matchingContainer, parts);
                if (found.length > 0) return found;
            }
            const all = [];
            for (const root of Object.values(elementsById)) {
                if (matchesSelector(root, parts[0])) {
                    if (parts.length === 1) all.push(root);
                    else all.push(...findDescendants(root, parts.slice(1)));
                } else {
                    all.push(...findDescendants(root, parts));
                }
            }
            return all;
        },
        querySelector: (sel) => {
            if (sel.startsWith('#')) return getOrCreateElement(sel.slice(1));
            const all = globalThis.document.querySelectorAll(sel);
            return all[0] || null;
        },
        addEventListener: (event, handler) => {
            if (!docListeners[event]) docListeners[event] = [];
            docListeners[event].push(handler);
        },
        dispatchEvent: (eventObj) => {
            const list = docListeners[eventObj.type] || [];
            for (const handler of list) {
                try {
                    handler(eventObj);
                } catch (_) {
                    // ignore secondary DOM setup errors
                }
            }
        }
    };

    // Ensure common UI elements exist before app.js binds listeners
    getOrCreateElement('matching-panel-container');
    getOrCreateElement('series-execution-panel');
    getOrCreateElement('btn-preview-execute', 'button');
    getOrCreateElement('preview-modal-overlay');
    getOrCreateElement('preview-modal');
    getOrCreateElement('preview-destination');
    getOrCreateElement('preview-list-renames');
    getOrCreateElement('preview-list-subs');
    getOrCreateElement('preview-list-junk');
    getOrCreateElement('series-all-seasons', 'input');
    getOrCreateElement('series-option-convert', 'input');
    getOrCreateElement('series-option-delete', 'input');
    getOrCreateElement('series-option-copy-nas', 'input');
    getOrCreateElement('series-option-copy-pcloud', 'input');
    getOrCreateElement('series-nas-destination', 'select');
    getOrCreateElement('series-pcloud-destination', 'select');
    getOrCreateElement('btn-manual-series', 'button');
    getOrCreateElement('manual-series-container');
    getOrCreateElement('manual-series-title', 'input');
    getOrCreateElement('manual-series-plot', 'input');

    // Timer mocks ensuring no real timers run in tests
    globalThis.setTimeout = (fn) => { if (typeof fn === 'function') fn(); return 0; };
    globalThis.clearTimeout = () => {};
    globalThis.setInterval = () => 0;
    globalThis.clearInterval = () => {};

    const alerts = [];
    globalThis.alert = (msg) => { alerts.push(msg); };
    const consoleLogs = [];
    globalThis.appendConsoleLog = (msg) => { consoleLogs.push(msg); };
    globalThis.onConsoleLog = (msg) => { consoleLogs.push(msg); };

    globalThis.window = {
        fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
        scrollTo: () => {},
        addEventListener: () => {}
    };
    globalThis.fetch = globalThis.window.fetch;

    const appJsContent = fs.readFileSync(appJsPath, 'utf8');
    let cleanAppJs = appJsContent.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, "");
    cleanAppJs = cleanAppJs.replace(
        "function appendConsoleLog(line) {",
        "function appendConsoleLog(line) { if (globalThis.onConsoleLog) globalThis.onConsoleLog(line);"
    );
    cleanAppJs = `
const cleanSeriesName = globalThis.cleanSeriesName;
const prepareSeriesPayload = globalThis.prepareSeriesPayload || ((show, payload) => ({ ...payload }));
const updateMwDataPanel = globalThis.updateMwDataPanel || (() => {});
const triggerQualityHintUpdates = globalThis.triggerQualityHintUpdates || (() => {});
const loadConversionRecommendations = globalThis.loadConversionRecommendations || (() => {});
const applyTheme = globalThis.applyTheme || (() => {});
const setupMaskedInput = globalThis.setupMaskedInput || (() => {});
const setMaskedInputValue = globalThis.setMaskedInputValue || (() => {});
const validateAllMaskedFields = globalThis.validateAllMaskedFields || (() => true);
const osBasename = (p) => String(p || '').replace(/^.*[\\/\\\\]/, '');
const formatFskLabel = (f) => f;
const guessEpisodeNumber = (filename) => {
    const m = String(filename).match(/[eE](\d+)/);
    return m ? parseInt(m[1], 10) : 1;
};
const guessSeasonAndEpisode = (filename) => {
    const m = String(filename).match(/[sS](\d+)[eE](\d+)/);
    return m ? ('S' + String(parseInt(m[1], 10)).padStart(2, '0') + 'E' + String(parseInt(m[2], 10)).padStart(2, '0')) : null;
};
const cleanFilenameForManualTitle = (filename) => String(filename).replace(/\\.[^/.]+$/, '');
` + cleanAppJs;

    cleanAppJs += `
globalThis.extractStrictSeasonEpisode = extractStrictSeasonEpisode;
globalThis.detectInboxGroups = detectInboxGroups;
globalThis.buildGroupedInboxSuggestions = buildGroupedInboxSuggestions;
globalThis.updateGroupBannerUI = updateGroupBannerUI;
globalThis.updateBulkActionsBarUI = updateBulkActionsBarUI;
globalThis.startSeriesGroupWorkflow = startSeriesGroupWorkflow;
globalThis.selectedInboxProjects = selectedInboxProjects;
globalThis.unlockedMovieProjects = unlockedMovieProjects;
globalThis.appliedInboxGroups = appliedInboxGroups;
globalThis.expandedInboxGroups = expandedInboxGroups;
globalThis.activeSeriesGroupFiles = activeSeriesGroupFiles;
globalThis.renderSmartInboxList = renderSmartInboxList;
globalThis.sortInboxSuggestions = sortInboxSuggestions;
globalThis.getInboxSortState = getInboxSortState;
globalThis.setInboxSortState = setInboxSortState;
globalThis.executeSeriesWorkflow = executeSeriesWorkflow;
globalThis.openPreviewModal = openPreviewModal;
globalThis.renderMatchingMatrix = renderMatchingMatrix;
globalThis.setSelectedShow = (val) => { selectedShow = val; };
globalThis.getSelectedShow = () => selectedShow;
globalThis.setEpisodesData = (val) => { episodesData = val; };
globalThis.setCurrentPreviewPayload = (val) => { currentPreviewPayload = val; };
globalThis.getCurrentPreviewPayload = () => currentPreviewPayload;
globalThis.detectManualGroupSeriesName = detectManualGroupSeriesName;
globalThis.getActiveSeriesGroupName = () => activeSeriesGroupName;
globalThis.setActiveSeriesGroupName = (val) => { activeSeriesGroupName = val; };
globalThis.setActiveSeriesGroupFiles = (val) => { activeSeriesGroupFiles = val; };
globalThis.initEventListeners = initEventListeners;
`;

    eval(cleanAppJs);

    globalThis.document.dispatchEvent({ type: 'DOMContentLoaded' });
    try {
        if (typeof globalThis.initEventListeners === 'function') {
            globalThis.initEventListeners();
        }
    } catch (_) {}

    return {
        cardSmartInbox,
        smartInboxList,
        groupBanner,
        sortBar,
        bulkBar,
        modeSeries,
        modeMovie,
        seriesSearchQuery,
        deletedProjects,
        alerts,
        consoleLogs,
        getOrCreateElement,
        viewEmpty,
        viewFolder,
        folderModeSelector
    };
}

// --------------------------------------------------------------------------
// AK1: Strict SxxExx Detection Pattern
// --------------------------------------------------------------------------
test('AK1: Strict SxxExx pattern recognizes Show.S01E01.720p.mkv', () => {
    setupTestEnvironment();
    const res = globalThis.extractStrictSeasonEpisode('Show.S01E01.720p.mkv');
    assert.ok(res !== null, 'Show.S01E01.720p.mkv must match strict pattern');
    assert.strictEqual(res.season, 1);
    assert.strictEqual(res.episode, 1);
    assert.strictEqual(res.formatted, 'S01E01');

    const res2 = globalThis.extractStrictSeasonEpisode('Show_S02E15_1080p.mkv');
    assert.ok(res2 !== null);
    assert.strictEqual(res2.season, 2);
    assert.strictEqual(res2.episode, 15);
    assert.strictEqual(res2.formatted, 'S02E15');
});

test('AK1: Strict SxxExx pattern does NOT recognize Movie.1920x1080.x264.mkv, The Rock (1996).mkv, Show.1x05.mkv, Staffel 2 Folge 3 – Show.mkv', () => {
    setupTestEnvironment();
    assert.strictEqual(globalThis.extractStrictSeasonEpisode('Movie.1920x1080.x264.mkv'), null);
    assert.strictEqual(globalThis.extractStrictSeasonEpisode('The Rock (1996).mkv'), null);
    assert.strictEqual(globalThis.extractStrictSeasonEpisode('Show.1x05.mkv'), null);
    assert.strictEqual(globalThis.extractStrictSeasonEpisode('Staffel 2 Folge 3 – Show.mkv'), null);
});

// --------------------------------------------------------------------------
// AK2: Automatic Grouping & Pseudo-Entry
// --------------------------------------------------------------------------
test('AK2: Empty suggested_query and folder entries (is_dir: true) are never automatically grouped', () => {
    setupTestEnvironment();
    const suggestions = [
        {
            project: 'Staffel 2 Folge 3 – Show.mkv',
            suggested_query: '',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'Show.S01E01.Folder',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: true,
            video_count: 1
        },
        {
            project: 'Show.S01E02.Folder',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: true,
            video_count: 1
        }
    ];

    const groups = globalThis.detectInboxGroups(suggestions);
    assert.deepStrictEqual(groups, {}, 'Folder entries or empty suggested_query must never form automatic groups');
});

test('AK2: Groups require >= 2 matches and group pseudo-entry aggregates modified_at (max) and total_size (sum)', () => {
    setupTestEnvironment();
    const suggestions = [
        {
            project: 'Show.S01E02.720p.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            modified_at: 1000,
            total_size: 2000,
            video_count: 1
        },
        {
            project: 'Show.S01E01.720p.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            modified_at: 3000,
            total_size: 1500,
            video_count: 1
        },
        {
            project: 'Show.S02E01.720p.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            modified_at: 2000,
            total_size: 2500,
            video_count: 1
        }
    ];

    const applied = new Set(['Show']);
    const grouped = globalThis.buildGroupedInboxSuggestions(suggestions, applied);
    assert.strictEqual(grouped.length, 1, 'Applied group must replace member items with 1 pseudo-entry');
    const groupEntry = grouped[0];
    assert.strictEqual(groupEntry.is_group, true);
    assert.strictEqual(groupEntry.project, 'Show');
    assert.strictEqual(groupEntry.total_size, 6000, 'Sum of sizes must be 2000 + 1500 + 2500 = 6000');
    assert.strictEqual(groupEntry.modified_at, 3000, 'Max modified_at must be 3000');
    assert.strictEqual(groupEntry.video_count, 3);

    // Member ordering inside group: numerically sorted by (season, episode)
    assert.strictEqual(groupEntry.items[0].project, 'Show.S01E01.720p.mkv');
    assert.strictEqual(groupEntry.items[1].project, 'Show.S01E02.720p.mkv');
    assert.strictEqual(groupEntry.items[2].project, 'Show.S02E01.720p.mkv');
});

test('AK2: Group pseudo-entry participates in sortInboxSuggestions', () => {
    setupTestEnvironment();
    const items = [
        {
            is_group: true,
            project: 'B-Group',
            total_size: 5000,
            modified_at: 200
        },
        {
            project: 'A-Single',
            total_size: 9000,
            modified_at: 100
        },
        {
            project: 'C-Single',
            total_size: 1000,
            modified_at: 300
        }
    ];

    const sortedByName = globalThis.sortInboxSuggestions(items, 'name', 'asc');
    assert.strictEqual(sortedByName[0].project, 'A-Single');
    assert.strictEqual(sortedByName[1].project, 'B-Group');
    assert.strictEqual(sortedByName[2].project, 'C-Single');

    const sortedByDate = globalThis.sortInboxSuggestions(items, 'date', 'desc');
    assert.strictEqual(sortedByDate[0].project, 'C-Single');
    assert.strictEqual(sortedByDate[1].project, 'B-Group');
    assert.strictEqual(sortedByDate[2].project, 'A-Single');

    const sortedBySize = globalThis.sortInboxSuggestions(items, 'size', 'asc');
    assert.strictEqual(sortedBySize[0].project, 'C-Single');
    assert.strictEqual(sortedBySize[1].project, 'B-Group');
    assert.strictEqual(sortedBySize[2].project, 'A-Single');
});

// --------------------------------------------------------------------------
// AK3: Banner Proposal & Confirmation & Movie Lock
// --------------------------------------------------------------------------
test('AK3: Group banner appears above sort bar and grouping is only applied after confirmation click', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'Show.S01E01.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'Show.S01E02.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Banner must be displayed
    assert.strictEqual(env.groupBanner.style.display, 'flex');
    assert.ok(env.groupBanner.innerHTML.includes('Show'));
    assert.ok(env.groupBanner.innerHTML.includes('2 Folgen'));

    // Before clicking banner: items in smartInboxList are separate
    const initialGroupRows = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    assert.strictEqual(initialGroupRows.length, 0, 'Group row must not exist before confirmation');
    const initialItems = env.smartInboxList.querySelectorAll('.smart-inbox-item');
    assert.strictEqual(initialItems.length, 2);

    // Click banner confirmation button
    const applyBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    assert.ok(applyBtn, 'Banner must have .btn-banner-apply-group button');
    applyBtn.click();

    // After clicking banner: group pseudo-entry is now rendered
    const finalGroupRows = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    assert.strictEqual(finalGroupRows.length, 1, 'Group row must be rendered after confirmation');
    assert.strictEqual(finalGroupRows[0].getAttribute('data-group-key'), 'Show');
});

test('AK3: Banner "Ignorieren" saves to sessionStorage and hides banner for session', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'Show.S01E01.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'Show.S01E02.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());
    assert.strictEqual(env.groupBanner.style.display, 'flex');

    const ignoreBtn = env.groupBanner.querySelector('.btn-banner-ignore-group');
    assert.ok(ignoreBtn, 'Banner must have ignore button');
    ignoreBtn.click();

    assert.strictEqual(globalThis.sessionStorage.getItem('smart-inbox-ignore-group-Show'), 'true');
    assert.strictEqual(env.groupBanner.style.display, 'none', 'Banner must be hidden after ignore');
});

test('AK3 & AK13: Film entries show lock notice and "Als Serie / Folge behandeln" link', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'The Rock (1996).mkv',
            suggested_query: 'The Rock',
            media_type: 'movie',
            is_dir: false,
            video_count: 1
        }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());

    const item = env.smartInboxList.querySelector('.smart-inbox-item');
    assert.ok(item);
    assert.ok(item.innerHTML.includes('Film (für Serie gesperrt)'));
    const unlockLink = item.querySelector('.btn-unlock-movie-series');
    assert.ok(unlockLink, 'Must provide unlock link');
    assert.ok(unlockLink.innerHTML.includes('Als Serie / Folge behandeln'), 'Must show "Als Serie / Folge behandeln"');
    assert.strictEqual(unlockLink.innerHTML.includes('Trotzdem als Serie freigeben'), false, 'Must not show "Trotzdem als Serie freigeben"');
});

// --------------------------------------------------------------------------
// AK13: Film-Ausnahme pro Eintrag
// --------------------------------------------------------------------------
test('AK13: Film exception works per entry, makes entry checkable, does not auto-group, and passes relative path', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'The Rock (1996).mkv',
            suggested_query: 'The Rock',
            media_type: 'movie',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'Matrix (1999).mkv',
            suggested_query: 'Matrix',
            media_type: 'movie',
            is_dir: false,
            video_count: 1
        }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Initially neither movie has a checkable checkbox
    let checkboxes = env.smartInboxList.querySelectorAll('.smart-inbox-cb');
    assert.strictEqual(checkboxes.length, 0);

    // Click unlock on first movie
    const unlockLinkFirst = env.smartInboxList.querySelector('[data-project="The Rock (1996).mkv"] .btn-unlock-movie-series');
    assert.ok(unlockLinkFirst);
    unlockLinkFirst.click();

    // Now first movie is unlocked, second remains locked
    const rockItem = env.smartInboxList.querySelector('[data-project="The Rock (1996).mkv"]');
    assert.ok(rockItem.innerHTML.includes('Als Serie freigegeben'));
    const rockCb = rockItem.querySelector('.smart-inbox-cb');
    assert.ok(rockCb, 'Unlocked movie must render checkbox');

    const matrixItem = env.smartInboxList.querySelector('[data-project="Matrix (1999).mkv"]');
    assert.ok(!matrixItem.innerHTML.includes('Als Serie freigegeben'), 'Second movie must remain locked');
    assert.strictEqual(matrixItem.querySelector('.smart-inbox-cb'), null);

    // Unlocking must NOT trigger auto-grouping
    const groups = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    assert.strictEqual(groups.length, 0);

    // Check unlocked movie and verify handover
    rockCb.checked = true;
    rockCb.dispatchEvent({ type: 'change', target: rockCb });

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);
    bulkBtn.click();

    assert.deepStrictEqual(globalThis.activeSeriesGroupFiles, ['The Rock (1996).mkv'], 'Handover of unlocked movie must contain relative file path');
});

test('AK13: Unlocked movie that isProcessing has checkbox disabled', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'The Rock (1996).mkv',
            suggested_query: 'The Rock',
            media_type: 'movie',
            is_dir: false,
            video_count: 1
        }
    ];

    globalThis.unlockedMovieProjects.add('The Rock (1996).mkv');
    const processingSet = new Set(['The Rock (1996).mkv']);
    globalThis.renderSmartInboxList(suggestions, processingSet);

    const cb = env.smartInboxList.querySelector('.smart-inbox-cb');
    assert.ok(cb);
    assert.strictEqual(cb.disabled, true, 'Checkbox must be disabled if project is processing');
});

// --------------------------------------------------------------------------
// AK12: Checkboxes, Selection State & Bulk Actions
// --------------------------------------------------------------------------
test('AK12: Checkboxes only appear on valid candidates (tv single files), not on folders, dokus, or processing', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        { project: 'ValidShow.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'FolderShow', media_type: 'tv', is_dir: true, video_count: 1 },
        { project: 'DokuFile.mkv', media_type: 'doku', is_dir: false, video_count: 1 },
        { project: 'ProcessingShow.S01E02.mkv', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    const processingSet = new Set(['ProcessingShow.S01E02.mkv']);
    globalThis.renderSmartInboxList(suggestions, processingSet);

    const validItem = env.smartInboxList.querySelector('[data-project="ValidShow.S01E01.mkv"]');
    const validCb = validItem.querySelector('.smart-inbox-cb');
    assert.ok(validCb && !validCb.disabled);

    const folderItem = env.smartInboxList.querySelector('[data-project="FolderShow"]');
    assert.strictEqual(folderItem.querySelector('.smart-inbox-cb'), null, 'Folders must not have checkboxes');

    const dokuItem = env.smartInboxList.querySelector('[data-project="DokuFile.mkv"]');
    assert.strictEqual(dokuItem.querySelector('.smart-inbox-cb'), null, 'Dokus must not have checkboxes');
    assert.strictEqual(dokuItem.querySelector('.btn-unlock-movie-series'), null, 'Dokus must not have unlock link');

    const procItem = env.smartInboxList.querySelector('[data-project="ProcessingShow.S01E02.mkv"]');
    const procCb = procItem.querySelector('.smart-inbox-cb');
    assert.ok(procCb);
    assert.strictEqual(procCb.disabled, true, 'Processing items must have disabled checkbox');
});

test('AK12: Selection state in Set persists across re-render and sort change, idempotent against duplicates', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        { project: 'ShowA.S01E01.mkv', media_type: 'tv', is_dir: false, modified_at: 100, total_size: 1000 },
        { project: 'ShowB.S01E01.mkv', media_type: 'tv', is_dir: false, modified_at: 200, total_size: 2000 }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());

    const cbA = env.smartInboxList.querySelector('[data-project="ShowA.S01E01.mkv"] .smart-inbox-cb');
    cbA.checked = true;
    cbA.dispatchEvent({ type: 'change', target: cbA });

    assert.ok(globalThis.selectedInboxProjects.has('ShowA.S01E01.mkv'));

    // Duplicate check is idempotent in Set
    globalThis.selectedInboxProjects.add('ShowA.S01E01.mkv');
    assert.strictEqual(Array.from(globalThis.selectedInboxProjects).length, 1);

    // Re-render
    globalThis.renderSmartInboxList(suggestions, new Set());
    const cbAAfter = env.smartInboxList.querySelector('[data-project="ShowA.S01E01.mkv"] .smart-inbox-cb');
    assert.strictEqual(cbAAfter.checked, true, 'Selection must persist across re-render');

    // Sort change
    const btnName = env.sortBar.querySelector('[data-field="name"]');
    btnName.click();
    const cbAAfterSort = env.smartInboxList.querySelector('[data-project="ShowA.S01E01.mkv"] .smart-inbox-cb');
    assert.strictEqual(cbAAfterSort.checked, true, 'Selection must persist across sort click');
});

test('AK12: Bulk actions bar displays count, "Auswahl aufheben" resets, and group button transfers selection', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        { project: 'ShowA.S01E01.mkv', media_type: 'tv', is_dir: false },
        { project: 'ShowB.S01E01.mkv', media_type: 'tv', is_dir: false }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());
    assert.strictEqual(env.bulkBar.style.display, 'none');

    // Check first item
    const cbA = env.smartInboxList.querySelector('[data-project="ShowA.S01E01.mkv"] .smart-inbox-cb');
    cbA.checked = true;
    cbA.dispatchEvent({ type: 'change', target: cbA });

    assert.strictEqual(env.bulkBar.style.display, 'flex');
    assert.ok(env.bulkBar.innerHTML.includes('1 ausgewählt'));

    // Check second item
    const cbB = env.smartInboxList.querySelector('[data-project="ShowB.S01E01.mkv"] .smart-inbox-cb');
    cbB.checked = true;
    cbB.dispatchEvent({ type: 'change', target: cbB });
    assert.ok(env.bulkBar.innerHTML.includes('2 ausgewählt'));

    // Test selection transfer via Sammelknopf
    const bulkGroupBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    bulkGroupBtn.click();
    assert.deepStrictEqual(globalThis.activeSeriesGroupFiles.sort(), ['ShowA.S01E01.mkv', 'ShowB.S01E01.mkv'].sort());

    // Test deselect button
    const deselectBtn = env.bulkBar.querySelector('#btn-bulk-deselect');
    deselectBtn.click();
    assert.strictEqual(globalThis.selectedInboxProjects.size, 0);
    assert.strictEqual(env.bulkBar.style.display, 'none');
});

// --------------------------------------------------------------------------
// AK11: R6 Security & Quarantine Isolation
// --------------------------------------------------------------------------
test('AK11: Group row has own class, data-group-key, NO data-project, NO quarantine button', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        { project: 'Show.S01E01.mkv', suggested_query: 'Show', media_type: 'tv', is_dir: false },
        { project: 'Show.S01E02.mkv', suggested_query: 'Show', media_type: 'tv', is_dir: false },
        { project: 'Show', media_type: 'tv', is_dir: true } // Real folder with same name "Show"
    ];

    globalThis.appliedInboxGroups.add('Show');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow, 'Group row must exist');
    assert.strictEqual(groupRow.classList.contains('smart-inbox-item'), false, 'Group row must NOT have class smart-inbox-item');
    assert.strictEqual(groupRow.getAttribute('data-project'), null, 'Group row must NOT have data-project');
    assert.strictEqual(groupRow.getAttribute('data-group-key'), 'Show');
    assert.strictEqual(groupRow.querySelector('.btn-delete-smart'), null, 'Group row must NOT render quarantine button');

    // Real folder item has data-project and delete button
    const folderItem = env.smartInboxList.querySelector('.smart-inbox-item[data-project="Show"]');
    assert.ok(folderItem);
    assert.ok(folderItem.querySelector('.btn-delete-smart'));

    // Collision check: deleteProject must never be invoked for group row
    assert.strictEqual(env.deletedProjects.length, 0);
});

test('AK11: Sentinel values ("" and "__inbox_recursive__") are never automatically grouped', () => {
    setupTestEnvironment();
    const suggestions = [
        { project: 'FileA.S01E01.mkv', suggested_query: '', media_type: 'tv', is_dir: false },
        { project: 'FileB.S01E01.mkv', suggested_query: '__inbox_recursive__', media_type: 'tv', is_dir: false }
    ];

    const groups = globalThis.detectInboxGroups(suggestions);
    assert.strictEqual(Object.keys(groups).length, 0);
});

// --------------------------------------------------------------------------
// H2 (B2 / AK4): Productive Workflow Handover & Key-Contract V1
// --------------------------------------------------------------------------
test('H2 (B2/AK4): Productive series workflow handover via executeSeriesWorkflow creates request body with files + mappings + media_type "tv", mappings-Schlüssel ⊆ files, and correctly escaped quotes in data-file', async () => {
    const env = setupTestEnvironment();
    const files = ['Show.S01E01.mkv', 'Show.S01E02."Special".mkv'];

    globalThis.startSeriesGroupWorkflow('Show', files);
    assert.strictEqual(env.seriesSearchQuery.value, 'Show', 'Search input must be prefilled with group name');
    assert.deepStrictEqual(globalThis.activeSeriesGroupFiles, files);

    globalThis.setSelectedShow({ name: 'Show', id: '123', provider: 'tvdb' });
    globalThis.setEpisodesData({ '1': { title: 'Episode 1' }, '2': { title: 'Episode 2' } });

    // Render matrix from projectFiles
    globalThis.renderMatchingMatrix();

    // Verify rows rendered and data-file attribute escaped correctly
    const rows = globalThis.document.querySelectorAll('.matching-row');
    assert.strictEqual(rows.length, 2, 'Two matching rows must be rendered');
    assert.strictEqual(rows[0].getAttribute('data-file'), 'Show.S01E01.mkv');
    assert.strictEqual(rows[1].getAttribute('data-file'), 'Show.S01E02."Special".mkv', 'data-file must not be truncated by quotes');

    // Intercept fetch for /api/preview_process
    let capturedUrl = null;
    let capturedBody = null;
    globalThis.fetch = (url, options) => {
        capturedUrl = url;
        if (options && options.body) {
            capturedBody = JSON.parse(options.body);
        }
        return Promise.resolve({
            ok: true,
            json: async () => ({ destination: 'Show', renames: [], subs: [], junk: [] })
        });
    };

    await globalThis.executeSeriesWorkflow();

    assert.strictEqual(capturedUrl, '/api/preview_process', 'executeSeriesWorkflow must call /api/preview_process');
    assert.ok(capturedBody, 'Captured request body must exist');
    assert.strictEqual(capturedBody.media_type, 'tv', 'media_type must be "tv"');
    assert.deepStrictEqual(capturedBody.files, files, 'files must contain activeSeriesGroupFiles');
    assert.ok(capturedBody.mappings && typeof capturedBody.mappings === 'object', 'mappings must be an object');

    // Verify mappings-Schlüssel ⊆ files
    const mappingKeys = Object.keys(capturedBody.mappings);
    assert.ok(mappingKeys.length > 0, 'mappings must not be empty');
    for (const key of mappingKeys) {
        assert.ok(capturedBody.files.includes(key), `Mapping key "${key}" must be in files[]`);
    }

    // Explicitly verify the quote-containing filename is a key in mappings intact
    assert.ok('Show.S01E02."Special".mkv' in capturedBody.mappings, 'Filename with quotes must be present as mapping key intact');
});

// --------------------------------------------------------------------------
// H1 (B1): Video Extension Coverage (.ts, .m2ts, .flv, .3gp, .wmv)
// --------------------------------------------------------------------------
test('H1 (B1): Matching matrix includes all 10 video extensions (.ts, .m2ts, etc.) matching server GROUP_VIDEO_EXTENSIONS', () => {
    setupTestEnvironment();
    const files = [
        'Show.S01E01.ts',
        'Show.S01E02.m2ts',
        'Show.S01E03.flv',
        'Show.S01E04.3gp',
        'Show.S01E05.wmv',
        'Show.S01E06.mp4',
        'Show.S01E07.mkv',
        'Show.S01E08.avi',
        'Show.S01E09.webm',
        'Show.S01E10.mov'
    ];

    globalThis.startSeriesGroupWorkflow('Show', files);
    globalThis.setSelectedShow({ name: 'Show', id: '123', provider: 'tvdb' });
    globalThis.setEpisodesData({
        '1': 'Ep 1', '2': 'Ep 2', '3': 'Ep 3', '4': 'Ep 4', '5': 'Ep 5',
        '6': 'Ep 6', '7': 'Ep 7', '8': 'Ep 8', '9': 'Ep 9', '10': 'Ep 10'
    });

    globalThis.renderMatchingMatrix();

    const rows = globalThis.document.querySelectorAll('.matching-row');
    assert.strictEqual(rows.length, 10, 'All 10 video files must be rendered in matching matrix');
    const renderedFiles = rows.map(r => r.getAttribute('data-file'));
    assert.deepStrictEqual(renderedFiles, files, 'All extensions including .ts and .m2ts must be preserved in matrix');
});

// --------------------------------------------------------------------------
// H3 (B3): Preserving Expanded State of Groups Across Re-Render
// --------------------------------------------------------------------------
test('H3 (B3): Group row expanded state persists across 6-second re-render (renderSmartInboxList)', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        { project: 'Show.S01E01.mkv', suggested_query: 'Show', media_type: 'tv', is_dir: false },
        { project: 'Show.S01E02.mkv', suggested_query: 'Show', media_type: 'tv', is_dir: false }
    ];

    globalThis.appliedInboxGroups.add('Show');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow, 'Group row must be rendered');
    const toggleBtn = groupRow.querySelector('.smart-inbox-group-toggle');
    const membersDiv = groupRow.querySelector('.smart-inbox-group-members');
    assert.ok(toggleBtn && membersDiv);

    // Initial state: collapsed
    assert.strictEqual(toggleBtn.getAttribute('aria-expanded'), 'false');
    assert.strictEqual(membersDiv.style.display, 'none');

    // Expand
    toggleBtn.click();
    assert.strictEqual(toggleBtn.getAttribute('aria-expanded'), 'true');
    assert.strictEqual(membersDiv.style.display, 'flex');
    assert.ok(globalThis.expandedInboxGroups.has('Show'), 'Show must be in expandedInboxGroups');

    // Simulate 6-second poll rebuild (renderSmartInboxList)
    globalThis.renderSmartInboxList(suggestions, new Set());

    const reRenderedGroupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const reToggleBtn = reRenderedGroupRow.querySelector('.smart-inbox-group-toggle');
    const reMembersDiv = reRenderedGroupRow.querySelector('.smart-inbox-group-members');

    // State must persist!
    assert.strictEqual(reToggleBtn.getAttribute('aria-expanded'), 'true', 'aria-expanded must remain true after re-render');
    assert.strictEqual(reMembersDiv.style.display, 'flex', 'Members list must remain visible after re-render');

    // Collapse
    reToggleBtn.click();
    assert.strictEqual(reToggleBtn.getAttribute('aria-expanded'), 'false');
    assert.strictEqual(reMembersDiv.style.display, 'none');
    assert.strictEqual(globalThis.expandedInboxGroups.has('Show'), false);

    // Re-render again: remains collapsed
    globalThis.renderSmartInboxList(suggestions, new Set());
    const collapsedRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.strictEqual(collapsedRow.querySelector('.smart-inbox-group-toggle').getAttribute('aria-expanded'), 'false');
    assert.strictEqual(collapsedRow.querySelector('.smart-inbox-group-members').style.display, 'none');
});

// --------------------------------------------------------------------------
// H4 (B4): Reading 400 Error Message Bodies
// --------------------------------------------------------------------------
test('H4 (B4): /preview_process HTTP 400 response body (error/message) is visibly displayed', async () => {
    const env = setupTestEnvironment();
    const serverErrorMessage = "Ungültiger Mapping-Schlüssel 'Broken': Nicht in files[] enthalten.";

    globalThis.fetch = () => Promise.resolve({
        ok: false,
        status: 400,
        json: async () => ({ status: 'error', error: serverErrorMessage, message: serverErrorMessage })
    });

    const payload = {
        media_type: 'tv',
        project_name: '',
        show_name: 'Show',
        files: ['Show.S01E01.mkv'],
        mappings: { 'Broken': 1 }
    };

    await globalThis.openPreviewModal(payload);

    assert.ok(
        env.alerts.some(a => a.includes(serverErrorMessage)),
        `Alert must visibly contain server error message. Alerts: ${JSON.stringify(env.alerts)}`
    );
});

test('H4 (B4): /process HTTP 400 response body (error/message) is visibly displayed in console and alert', async () => {
    const env = setupTestEnvironment();
    const serverErrorMessage = "files[] wird nur für media_type 'tv' unterstützt.";

    globalThis.fetch = () => Promise.resolve({
        ok: false,
        status: 400,
        json: async () => ({ status: 'error', error: serverErrorMessage, message: serverErrorMessage })
    });

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        project_name: '',
        show_name: 'Show',
        files: ['Show.S01E01.mkv'],
        mappings: { 'Show.S01E01.mkv': 1 }
    });

    const noProfileCb = env.getOrCreateElement('series-option-no-profile', 'input');
    noProfileCb.checked = true;

    const previewExecuteBtn = env.getOrCreateElement('btn-preview-execute');
    assert.ok(previewExecuteBtn, 'btn-preview-execute element must exist');

    await previewExecuteBtn.dispatchEvent({ type: 'click' });

    assert.ok(
        env.consoleLogs.some(log => log.includes(serverErrorMessage)),
        `Console log must visibly contain server message. Logs: ${JSON.stringify(env.consoleLogs)}`
    );
    assert.ok(
        env.alerts.some(a => a.includes(serverErrorMessage)),
        `Alert must visibly contain server message. Alerts: ${JSON.stringify(env.alerts)}`
    );
});

// --------------------------------------------------------------------------
// F1 & F2: Lauf B Nachbesserungen (View-Umschaltung & Beschriftungen)
// --------------------------------------------------------------------------
test('F1: nach Klick auf Gruppenzeilen-Knopf, Sammelknopf und Banner ist view-folder sichtbar (nicht hidden), die Startseiten-Ansicht ausgeblendet und mode-series aktiv', async () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'Show.S01E01.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'Show.S01E02.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        }
    ];

    // --- Case 1: Gruppenzeilen-Knopf ---
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');

    globalThis.appliedInboxGroups.add('Show');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow, 'Group row must be rendered');
    const groupSelectBtn = groupRow.querySelector('.btn-select-group');
    assert.ok(groupSelectBtn, 'Group row must have .btn-select-group button');
    await groupSelectBtn.click();

    assert.strictEqual(env.viewFolder.classList.contains('hidden'), false, 'view-folder must not be hidden after group row click');
    assert.strictEqual(env.viewFolder.classList.contains('active'), true, 'view-folder must be active after group row click');
    assert.strictEqual(env.viewEmpty.classList.contains('hidden'), true, 'view-empty must be hidden after group row click');
    assert.strictEqual(env.viewEmpty.classList.contains('active'), false, 'view-empty must not be active after group row click');
    assert.strictEqual(env.modeSeries.classList.contains('active'), true, 'mode-series must be active after group row click');

    // --- Case 2: Sammelknopf ---
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');

    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Show.S01E01.mkv');
    globalThis.selectedInboxProjects.add('Show.S01E02.mkv');
    globalThis.updateBulkActionsBarUI();

    const bulkGroupBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkGroupBtn, 'Bulk bar must have group series button');
    await bulkGroupBtn.click();

    assert.strictEqual(env.viewFolder.classList.contains('hidden'), false, 'view-folder must not be hidden after bulk button click');
    assert.strictEqual(env.viewFolder.classList.contains('active'), true, 'view-folder must be active after bulk button click');
    assert.strictEqual(env.viewEmpty.classList.contains('hidden'), true, 'view-empty must be hidden after bulk button click');
    assert.strictEqual(env.viewEmpty.classList.contains('active'), false, 'view-empty must not be active after bulk button click');
    assert.strictEqual(env.modeSeries.classList.contains('active'), true, 'mode-series must be active after bulk button click');

    // --- Case 3: Banner ---
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');

    globalThis.appliedInboxGroups.clear();
    globalThis.renderSmartInboxList(suggestions, new Set());

    const bannerBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    assert.ok(bannerBtn, 'Banner must have apply button');
    await bannerBtn.click();

    assert.strictEqual(env.viewFolder.classList.contains('hidden'), false, 'view-folder must not be hidden after banner click');
    assert.strictEqual(env.viewFolder.classList.contains('active'), true, 'view-folder must be active after banner click');
    assert.strictEqual(env.viewEmpty.classList.contains('hidden'), true, 'view-empty must be hidden after banner click');
    assert.strictEqual(env.viewEmpty.classList.contains('active'), false, 'view-empty must not be active after banner click');
    assert.strictEqual(env.modeSeries.classList.contains('active'), true, 'mode-series must be active after banner click');
});

test('F2: Beschriftungen - Gruppenzeile "Auswählen", Banner "Als Serie gruppieren", Sammelknopf "Ausgewählte als Serie verarbeiten", gesperrte Filme "Als Serie / Folge behandeln"', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        {
            project: 'Show.S01E01.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'Show.S01E02.mkv',
            suggested_query: 'Show',
            media_type: 'tv',
            is_dir: false,
            video_count: 1
        },
        {
            project: 'LockedMovie.mkv',
            suggested_query: 'Locked Movie',
            media_type: 'movie',
            is_dir: false,
            video_count: 1
        }
    ];

    // (b) Banner: "Als Serie gruppieren"
    globalThis.appliedInboxGroups.clear();
    globalThis.renderSmartInboxList(suggestions, new Set());
    const bannerBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    assert.ok(bannerBtn);
    assert.ok(bannerBtn.innerHTML.includes('Als Serie gruppieren'), 'Banner button must retain text "Als Serie gruppieren"');

    // (b) Gruppenzeile: "Auswählen" statt "Als Serie gruppieren"
    globalThis.appliedInboxGroups.add('Show');
    globalThis.renderSmartInboxList(suggestions, new Set());
    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow);
    const groupSelectBtn = groupRow.querySelector('.btn-select-group');
    assert.ok(groupSelectBtn);
    assert.ok(groupSelectBtn.innerHTML.includes('Auswählen'), 'Group row button must be labeled "Auswählen"');
    assert.strictEqual(groupSelectBtn.innerHTML.includes('Als Serie gruppieren'), false, 'Group row button must NOT be labeled "Als Serie gruppieren"');

    // (b) Sammelknopf: "Ausgewählte als Serie verarbeiten"
    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Show.S01E01.mkv');
    globalThis.updateBulkActionsBarUI();
    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);
    assert.ok(bulkBtn.innerHTML.includes('Ausgewählte als Serie verarbeiten'), 'Bulk button must have text "Ausgewählte als Serie verarbeiten"');
    assert.strictEqual(bulkBtn.innerHTML.includes('Ausgewählte als Serie gruppieren'), false, 'Bulk button must NOT have old text "Ausgewählte als Serie gruppieren"');

    // (a) Link 'Als Serie / Folge behandeln' bei gesperrten Filmen
    const movieItem = env.smartInboxList.querySelector('[data-project="LockedMovie.mkv"]');
    assert.ok(movieItem);
    const unlockLink = movieItem.querySelector('.btn-unlock-movie-series');
    assert.ok(unlockLink);
    assert.ok(unlockLink.innerHTML.includes('Als Serie / Folge behandeln'), 'Locked movie link must be "Als Serie / Folge behandeln"');
    assert.strictEqual(unlockLink.innerHTML.includes('Trotzdem als Serie freigeben'), false, 'Locked movie link must NOT be "Trotzdem als Serie freigeben"');
});

// --------------------------------------------------------------------------
// Lauf B Nachbesserung (Alex Handtest 2026-10-11): Tasks 1 - 4
// --------------------------------------------------------------------------

// 1. Vorschau-Fenster: Quoted / Brackets Filename Preservation & No HTML Injection
test('1: Vorschau-Fenster: Dateiname mit " (und mit < >) bleibt vom Rendern bis in explicit_renames/explicit_subs des /process-Requests vollständig erhalten; kein HTML wird eingeschleust', async () => {
    const env = setupTestEnvironment();
    const maliciousNameOld = 'Testserie.S02E07."Spezial".<script>alert(1)</script>.mkv';
    const specialNameNew = 'Testserie - S02E07 - "Spezial" & <Bonus>.mkv';
    const subNameOld = 'Testserie.S02E07."Spezial".<script>.de.srt';
    const subNameNew = 'Testserie - S02E07 - "Spezial" <Bonus>.de.srt';
    const junkNameOld = 'Testserie.S02E07."Spezial".<script>.nfo';

    let capturedProcessBody = null;
    globalThis.fetch = (url, options) => {
        if (url === '/api/preview_process') {
            return Promise.resolve({
                ok: true,
                json: async () => ({
                    destination: 'Serien/Testserie',
                    renames: [{ old: maliciousNameOld, new: specialNameNew }],
                    subs: [{ old: subNameOld, new: subNameNew }],
                    junk: [{ old: junkNameOld }]
                })
            });
        }
        if (url === '/api/process') {
            capturedProcessBody = JSON.parse(options.body);
            return Promise.resolve({
                ok: true,
                json: async () => ({ status: 'started' })
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    await globalThis.openPreviewModal({
        media_type: 'tv',
        project_name: '',
        show_name: 'Testserie',
        files: [maliciousNameOld, subNameOld, junkNameOld]
    });

    const renamesList = env.getOrCreateElement('preview-list-renames');
    // Verify no script tag was injected into DOM
    assert.strictEqual(renamesList.querySelectorAll('script').length, 0, 'No script elements must be injected into preview');

    // Verify checkbox rendered data-old and data-new
    const renameCb = renamesList.querySelector('.preview-cb-renames');
    assert.ok(renameCb, 'Rename checkbox must exist');
    assert.strictEqual(renameCb.getAttribute('data-old'), maliciousNameOld, 'data-old attribute must retain full name with quotes and brackets intact');
    assert.strictEqual(renameCb.getAttribute('data-new'), specialNameNew, 'data-new attribute must retain full name with quotes and brackets intact');

    const subsList = env.getOrCreateElement('preview-list-subs');
    const subCb = subsList.querySelector('.preview-cb-subs');
    assert.ok(subCb, 'Sub checkbox must exist');
    assert.strictEqual(subCb.getAttribute('data-old'), subNameOld);

    // Disable profile save to keep test focused
    const noProfileCb = env.getOrCreateElement('series-option-no-profile', 'input');
    noProfileCb.checked = true;

    // Click execute
    const executeBtn = env.getOrCreateElement('btn-preview-execute', 'button');
    await executeBtn.click();

    // Verify explicit_renames, explicit_subs, and explicit_junk in /process request
    assert.ok(capturedProcessBody, 'Request body to /process must be sent');
    assert.ok(Array.isArray(capturedProcessBody.explicit_renames));
    assert.strictEqual(capturedProcessBody.explicit_renames[0].old, maliciousNameOld, 'explicit_renames[0].old must retain quotes and angle brackets intact');
    assert.strictEqual(capturedProcessBody.explicit_renames[0].new, specialNameNew, 'explicit_renames[0].new must retain quotes and angle brackets intact');

    assert.ok(Array.isArray(capturedProcessBody.explicit_subs));
    assert.strictEqual(capturedProcessBody.explicit_subs[0].old, subNameOld, 'explicit_subs[0].old must retain quotes and angle brackets intact');
    assert.strictEqual(capturedProcessBody.explicit_subs[0].new, subNameNew, 'explicit_subs[0].new must retain quotes and angle brackets intact');

    assert.ok(Array.isArray(capturedProcessBody.explicit_junk));
    assert.strictEqual(capturedProcessBody.explicit_junk[0], junkNameOld, 'explicit_junk[0] must retain quotes and angle brackets intact');
});

// 2. Doppelstart-Schutz und sofortige Rückmeldung
test('2: Doppelstart-Schutz: zwei schnelle Klicks auf Ausführen -> genau ein /process-Request', async () => {
    const env = setupTestEnvironment();
    let processCalls = 0;
    let resolveProcessPromise = null;

    globalThis.fetch = (url) => {
        if (url === '/api/process') {
            processCalls++;
            return new Promise(resolve => {
                resolveProcessPromise = () => resolve({ ok: true, json: async () => ({ status: 'started' }) });
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        project_name: '',
        show_name: 'Testserie',
        files: ['file1.mkv']
    });

    const noProfileCb = env.getOrCreateElement('series-option-no-profile', 'input');
    noProfileCb.checked = true;

    const executeBtn = env.getOrCreateElement('btn-preview-execute', 'button');
    executeBtn.disabled = false;
    executeBtn.innerHTML = 'Jetzt final verarbeiten';

    // Click once
    const clickPromise1 = executeBtn.click();
    assert.strictEqual(executeBtn.disabled, true, 'Ausführen-Knopf must be disabled immediately on first click');
    assert.strictEqual(executeBtn.textContent, 'wird gestartet…', 'Ausführen-Knopf must show "wird gestartet…" immediately on first click');

    // Click second time while first is in-flight
    const clickPromise2 = executeBtn.click();

    // Now resolve the in-flight process request
    assert.ok(resolveProcessPromise, 'Process fetch must have been initiated');
    resolveProcessPromise();
    await Promise.all([clickPromise1, clickPromise2]);

    assert.strictEqual(processCalls, 1, 'Two fast clicks on Ausführen must result in exactly one /process request');
});

test('2: Doppelstart-Schutz: bei Fehler im /process-Request wird der Ausführen-Knopf wieder aktiv', async () => {
    const env = setupTestEnvironment();

    globalThis.fetch = (url) => {
        if (url === '/api/process') {
            return Promise.resolve({
                ok: false,
                status: 500,
                json: async () => ({ error: 'Serverfehler' })
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        project_name: '',
        show_name: 'Testserie',
        files: ['file1.mkv']
    });

    const noProfileCb = env.getOrCreateElement('series-option-no-profile', 'input');
    noProfileCb.checked = true;

    const executeBtn = env.getOrCreateElement('btn-preview-execute', 'button');
    executeBtn.disabled = false;
    executeBtn.innerHTML = 'Jetzt final verarbeiten';

    await executeBtn.click();

    // On error, executeBtn must be re-enabled and restored
    assert.strictEqual(executeBtn.disabled, false, 'Ausführen-Knopf must be re-enabled on error');
    assert.strictEqual(executeBtn.textContent, 'Jetzt final verarbeiten', 'Ausführen-Knopf text must be restored on error');
});

test('2: Doppelstart-Schutz: Banner-Knopf, Gruppenzeilen-Knopf und Sammelknopf werden beim ersten Klick deaktiviert und zeigen "wird gestartet…"', async () => {
    const env = setupTestEnvironment();
    const suggestions = [
        { project: 'Show.S01E05.mkv', suggested_query: 'Show', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Show.S01E06.mkv', suggested_query: 'Show', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    let searchResolve = null;
    globalThis.fetch = (url) => {
        if (url.includes('/api/search')) {
            return new Promise(resolve => {
                searchResolve = () => resolve({ ok: true, json: async () => [] });
            });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
    };

    // 1. Sammelknopf
    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Show.1x05.mkv');
    globalThis.selectedInboxProjects.add('Show.1x06.mkv');
    globalThis.updateBulkActionsBarUI();

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);
    const bulkPromise = bulkBtn.click();
    assert.strictEqual(bulkBtn.disabled, true, 'Sammelknopf must be disabled on click');
    assert.strictEqual(bulkBtn.textContent, 'wird gestartet…', 'Sammelknopf must show "wird gestartet…" on click');
    if (searchResolve) searchResolve();
    await bulkPromise;

    // 2. Gruppenzeilen-Knopf
    searchResolve = null;
    globalThis.appliedInboxGroups.add('Show');
    globalThis.renderSmartInboxList(suggestions, new Set());
    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const groupSelectBtn = groupRow.querySelector('.btn-select-group');
    assert.ok(groupSelectBtn);

    const groupPromise = groupSelectBtn.click();
    assert.strictEqual(groupSelectBtn.disabled, true, 'Gruppenzeilen-Knopf must be disabled on click');
    assert.strictEqual(groupSelectBtn.textContent, 'wird gestartet…', 'Gruppenzeilen-Knopf must show "wird gestartet…" on click');
    if (searchResolve) searchResolve();
    await groupPromise;
});

// 3. Alex-Entscheidungen: (b) Gruppenname bei manueller Auswahl
test('3(b): Gruppenname bei manueller Auswahl = gemeinsamer Namensanfang ohne Folgenkennung und ohne Trennzeichen am Ende; Fallback wie bisher', () => {
    setupTestEnvironment();

    // Case 1: 'Andere Show.1x05.mkv' + 'Andere Show.1x06.mkv' -> 'Andere Show'
    const name1 = globalThis.detectManualGroupSeriesName(
        ['Andere Show.1x05.mkv', 'Andere Show.1x06.mkv'],
        'Fallback'
    );
    assert.strictEqual(name1, 'Andere Show');

    // Case 2: SxxExx: 'Show.S01E05.720p.mkv' + 'Show.S01E06.1080p.mkv' -> 'Show'
    const name2 = globalThis.detectManualGroupSeriesName(
        ['Show.S01E05.720p.mkv', 'Show.S01E06.1080p.mkv'],
        'Fallback'
    );
    assert.strictEqual(name2, 'Show');

    // Case 3: 'Staffel 2 Folge 3'
    const name3 = globalThis.detectManualGroupSeriesName(
        ['Cool Series - Staffel 2 Folge 3.mkv', 'Cool Series - Staffel 2 Folge 4.mkv'],
        'Fallback'
    );
    assert.strictEqual(name3, 'Cool Series');

    // Case 4: Fallback if no common prefix
    const nameFallback = globalThis.detectManualGroupSeriesName(
        ['Alfa.mkv', 'Beta.mkv'],
        'Mein Fallback'
    );
    assert.strictEqual(nameFallback, 'Mein Fallback');
});

// 4. Name in der Warteschlange
test('4: Name in der Warteschlange: im manuellen Serien-Modus im Gruppen-Ablauf den Gruppennamen verwenden ("Testserie (Gruppe)"), sonst unverändert', async () => {
    const env = setupTestEnvironment();

    // 1. Start group workflow with groupName "Testserie"
    await globalThis.startSeriesGroupWorkflow('Testserie', ['Testserie.S01E01.mkv', 'Testserie.S01E02.mkv']);

    // Switch to manual series mode
    const btnManualSeries = env.getOrCreateElement('btn-manual-series', 'button');
    await btnManualSeries.click();

    // With manual-series-title empty: selectedShow.name must be "Testserie (Gruppe)"
    const manualTitleInput = env.getOrCreateElement('manual-series-title', 'input');
    manualTitleInput.value = '';
    await manualTitleInput.dispatchEvent({ type: 'input' });

    const showInGroup = globalThis.getSelectedShow();
    assert.ok(showInGroup, 'selectedShow must be set');
    assert.strictEqual(showInGroup.name, 'Testserie (Gruppe)', 'Group workflow manual mode must use "Testserie (Gruppe)" as show name');

    // With manual-series-title entered: uses the custom title
    manualTitleInput.value = 'Eigener Serientitel';
    await manualTitleInput.dispatchEvent({ type: 'input' });
    const showCustom = globalThis.getSelectedShow();
    assert.strictEqual(showCustom.name, 'Eigener Serientitel');

    // 2. Non-group workflow with currentProject empty
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');
    manualTitleInput.value = '';
    await manualTitleInput.dispatchEvent({ type: 'input' });
    const showNonGroup = globalThis.getSelectedShow();
    assert.strictEqual(showNonGroup.name, 'Manuelle Serie', 'Non-group workflow with empty project must fall back to "Manuelle Serie"');
});
