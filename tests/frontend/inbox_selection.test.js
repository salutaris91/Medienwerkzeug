import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');

// In-memory sessionStorage mock
let sessionStore = {};
const mockSessionStorage = {
    getItem: (key) => (key in sessionStore ? sessionStore[key] : null),
    setItem: (key, val) => { sessionStore[key] = String(val); },
    removeItem: (key) => { delete sessionStore[key]; },
    clear: () => { sessionStore = {}; }
};

function validateSelector(sel) {
    if (typeof sel !== 'string') return;
    // Check for unbalanced quotes overall
    const doubleQuotes = (sel.match(/(?<!\\)"/g) || []).length;
    const singleQuotes = (sel.match(/(?<!\\)'/g) || []).length;
    if (doubleQuotes % 2 !== 0 || singleQuotes % 2 !== 0) {
        const err = new Error(`Failed to execute 'querySelector': '${sel}' is not a valid selector.`);
        err.name = 'SyntaxError';
        throw err;
    }
    // Check for unescaped quotes or unexpected tokens inside attribute selector
    const rawAttrs = sel.match(/\[[^\]]*\]/g) || [];
    for (const raw of rawAttrs) {
        const eqIdx = raw.indexOf('=');
        if (eqIdx !== -1) {
            const afterEq = raw.slice(eqIdx + 1, -1).trim();
            if (afterEq.startsWith('"')) {
                if (!/^"([^"\\]|\\.)*"\s*[is]?$/.test(afterEq)) {
                    const err = new Error(`Failed to execute 'querySelector': '${sel}' is not a valid selector.`);
                    err.name = 'SyntaxError';
                    throw err;
                }
            } else if (afterEq.startsWith("'")) {
                if (!/^'([^'\\]|\\.)*'\s*[is]?$/.test(afterEq)) {
                    const err = new Error(`Failed to execute 'querySelector': '${sel}' is not a valid selector.`);
                    err.name = 'SyntaxError';
                    throw err;
                }
            }
        }
    }
    const openBrackets = (sel.match(/\[/g) || []).length;
    const closeBrackets = (sel.match(/\]/g) || []).length;
    if (openBrackets !== closeBrackets) {
        const err = new Error(`Failed to execute 'querySelector': '${sel}' is not a valid selector.`);
        err.name = 'SyntaxError';
        throw err;
    }
}

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
    while ((match = tagRegex.exec(html)) !== null) {
        const tagName = match[1].toLowerCase();
        if (tagName.startsWith('/')) continue;
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

        const typeMatch = attrStr.match(/type=["']([^"']+)["']/i);
        if (typeMatch) {
            el.setAttribute('type', typeMatch[1]);
        }

        const ariaRegex = /aria-([a-z0-9\-]+)=["']([^"']*)["']/gi;
        let aMatch;
        while ((aMatch = ariaRegex.exec(attrStr)) !== null) {
            el.setAttribute(`aria-${aMatch[1]}`, aMatch[2]);
        }

        const titleMatch = attrStr.match(/title=["']([^"']*)["']/i);
        if (titleMatch) {
            el.setAttribute('title', titleMatch[1]);
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
            validateSelector(sel);
            const parts = splitSelectorParts(sel);
            const res = findDescendants(el, parts);
            return res[0] || null;
        },
        querySelectorAll: (sel) => {
            validateSelector(sel);
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
            validateSelector(sel);
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
            validateSelector(sel);
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
                } catch (_) {}
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

    // Timer mocks
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
    const m = String(filename).match(/[eE](\\d+)/);
    return m ? parseInt(m[1], 10) : 1;
};
const guessSeasonAndEpisode = (filename) => {
    const m = String(filename).match(/[sS](\\d+)[eE](\\d+)/);
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
globalThis.setActiveSeriesGroupName = (val) => { activeSeriesGroupName = val; if (typeof globalThis !== 'undefined') globalThis.activeSeriesGroupName = val; };
globalThis.setActiveSeriesGroupFiles = (val) => { activeSeriesGroupFiles = val; if (typeof globalThis !== 'undefined') globalThis.activeSeriesGroupFiles = val; };
globalThis.renderQueue = renderQueue;
globalThis.setCurrentProject = (val) => { currentProject = val; };
globalThis.getCurrentProject = () => currentProject;
globalThis.getActiveProjectsProcessing = () => activeProjectsProcessing;
globalThis.setCurrentQueueJobs = (val) => { currentQueueJobs = val; };
globalThis.getCurrentQueueJobs = () => currentQueueJobs;
globalThis.initEventListeners = initEventListeners;
globalThis.isInboxProjectEligibleForSelection = isInboxProjectEligibleForSelection;
globalThis.setCurrentSmartInboxRawSuggestions = (val) => { currentSmartInboxRawSuggestions = val; };
globalThis.getCurrentSmartInboxRawSuggestions = () => currentSmartInboxRawSuggestions;
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
// AK1: Auswahl {A, B}, Neuzeichnen mit Liste ohne B → Auswahl {A}, Zähler „1 ausgewählt“
// --------------------------------------------------------------------------
test('AK1: Neuzeichnen mit Liste ohne B entfernt B aus selectedInboxProjects und aktualisiert Zähler auf "1 ausgewählt"', () => {
    const env = setupTestEnvironment();

    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('ShowA.S01E01.mkv');
    globalThis.selectedInboxProjects.add('ShowB.S01E01.mkv');

    const suggestionsWithoutB = [
        { project: 'ShowA.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    globalThis.renderSmartInboxList(suggestionsWithoutB, new Set());

    assert.strictEqual(globalThis.selectedInboxProjects.has('ShowA.S01E01.mkv'), true, 'ShowA must remain selected');
    assert.strictEqual(globalThis.selectedInboxProjects.has('ShowB.S01E01.mkv'), false, 'ShowB must be removed from selectedInboxProjects');
    assert.strictEqual(globalThis.selectedInboxProjects.size, 1);

    const countEl = env.bulkBar.querySelector('#smart-inbox-bulk-count');
    assert.ok(countEl, 'Bulk count element must exist');
    assert.strictEqual(countEl.textContent, '1 ausgewählt');
});

// --------------------------------------------------------------------------
// AK2: Auswahl {A, B}, Neuzeichnen mit B in processingSet → Auswahl {A}; B's Kästchen nicht checked
// --------------------------------------------------------------------------
test('AK2: Neuzeichnen mit B in processingSet entfernt B aus Auswahl und B\'s Kästchen ist nicht checked', () => {
    const env = setupTestEnvironment();

    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('ShowA.S01E01.mkv');
    globalThis.selectedInboxProjects.add('ShowB.S01E01.mkv');

    const suggestions = [
        { project: 'ShowA.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'ShowB.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
    const processingSet = new Set(['ShowB.S01E01.mkv']);

    globalThis.renderSmartInboxList(suggestions, processingSet);

    assert.strictEqual(globalThis.selectedInboxProjects.has('ShowA.S01E01.mkv'), true, 'ShowA must remain selected');
    assert.strictEqual(globalThis.selectedInboxProjects.has('ShowB.S01E01.mkv'), false, 'ShowB must be removed from selection because it is processing');
    assert.strictEqual(globalThis.selectedInboxProjects.size, 1);

    const cbA = env.smartInboxList.querySelector('[data-project="ShowA.S01E01.mkv"] .smart-inbox-cb');
    assert.ok(cbA);
    assert.strictEqual(cbA.checked, true, 'ShowA checkbox must be checked');
    assert.strictEqual(cbA.disabled, false);

    const cbB = env.smartInboxList.querySelector('[data-project="ShowB.S01E01.mkv"] .smart-inbox-cb');
    assert.ok(cbB);
    assert.strictEqual(cbB.checked, false, 'ShowB checkbox must NOT be checked');
    assert.strictEqual(cbB.disabled, true, 'ShowB checkbox must be disabled');

    const countEl = env.bulkBar.querySelector('#smart-inbox-bulk-count');
    assert.ok(countEl);
    assert.strictEqual(countEl.textContent, '1 ausgewählt');
});

// --------------------------------------------------------------------------
// AK3: Auswahl enthält nur Einträge, die verschwunden sind → nach Neuzeichnen leer, Bulk-Leiste ausgeblendet
// --------------------------------------------------------------------------
test('AK3: Wenn alle ausgewählten Einträge verschwunden sind, ist die Auswahl nach Neuzeichnen leer und die Bulk-Leiste ausgeblendet', () => {
    const env = setupTestEnvironment();

    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Vanished1.mkv');
    globalThis.selectedInboxProjects.add('Vanished2.mkv');

    // Neuzeichnen mit leerer Liste
    globalThis.renderSmartInboxList([], new Set());

    assert.strictEqual(globalThis.selectedInboxProjects.size, 0, 'Selection must be completely cleared');
    assert.strictEqual(env.bulkBar.style.display, 'none', 'Bulk actions bar must be hidden when selection is empty');

    // Auch wenn andere Einträge vorhanden sind, aber keiner der verschwundenen:
    globalThis.selectedInboxProjects.add('Vanished1.mkv');
    const suggestionsOther = [
        { project: 'OtherShow.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
    globalThis.renderSmartInboxList(suggestionsOther, new Set());
    assert.strictEqual(globalThis.selectedInboxProjects.size, 0);
    assert.strictEqual(env.bulkBar.style.display, 'none');
});

// --------------------------------------------------------------------------
// AK4: Bulk-Klick mit {A, X}, X ohne Treffer in currentSmartInboxRawSuggestions (ohne vorheriges Neuzeichnen)
// --------------------------------------------------------------------------
test('AK4: Bulk-Klick mit {A, X} ohne Treffer für X: nur A wird an Workflow übergeben, 1 übersprungener Eintrag per Alert gemeldet, X nicht mehr ausgewählt', async () => {
    const env = setupTestEnvironment();

    // suggestions contains only A
    const rawSuggestions = [
        { project: 'ShowA.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
    globalThis.renderSmartInboxList(rawSuggestions, new Set());

    // Selection contains {A, X} without prior redraw, mimicking stale state
    globalThis.selectedInboxProjects.add('ShowA.S01E01.mkv');
    globalThis.selectedInboxProjects.add('FolderX');
    globalThis.updateBulkActionsBarUI();

    assert.strictEqual(globalThis.selectedInboxProjects.size, 2);

    globalThis.activeSeriesGroupFiles = null;
    globalThis.activeSeriesGroupName = null;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn, 'Bulk action button must exist');

    await bulkBtn.click();

    // startSeriesGroupWorkflow receives only A, not naked folder X
    assert.ok(globalThis.activeSeriesGroupFiles, 'startSeriesGroupWorkflow must be called');
    assert.deepStrictEqual(globalThis.activeSeriesGroupFiles, ['ShowA.S01E01.mkv']);
    assert.strictEqual(globalThis.activeSeriesGroupFiles.includes('FolderX'), false, 'Naked folder name FolderX must never be sent');

    // Alert mentions 1 skipped entry
    assert.strictEqual(env.alerts.length, 1, 'Exactly one alert must be shown');
    assert.ok(
        env.alerts[0].includes('1 Eintrag') && env.alerts[0].includes('übersprungen'),
        `Alert must mention 1 skipped entry, got: "${env.alerts[0]}"`
    );

    // X is no longer selected
    assert.strictEqual(globalThis.selectedInboxProjects.has('FolderX'), false, 'X must no longer be selected');
    assert.strictEqual(globalThis.selectedInboxProjects.has('ShowA.S01E01.mkv'), true, 'A must still be selected');
    assert.strictEqual(globalThis.selectedInboxProjects.size, 1);

    const countEl = env.bulkBar.querySelector('#smart-inbox-bulk-count');
    assert.ok(countEl);
    assert.strictEqual(countEl.textContent, '1 ausgewählt');
});

// --------------------------------------------------------------------------
// AK5: Bulk-Klick, alle Einträge ohne Treffer bzw. in Verarbeitung
// --------------------------------------------------------------------------
test('AK5: Bulk-Klick wenn alle Einträge ohne Treffer sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv', async () => {
    const env = setupTestEnvironment();

    globalThis.setCurrentSmartInboxRawSuggestions([]);
    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Missing1.mkv');
    globalThis.selectedInboxProjects.add('Missing2.mkv');
    globalThis.updateBulkActionsBarUI();

    globalThis.activeSeriesGroupFiles = null;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);

    await bulkBtn.click();

    assert.strictEqual(globalThis.activeSeriesGroupFiles, null, 'startSeriesGroupWorkflow must NOT be called when no valid items remain');
    assert.strictEqual(env.alerts.length, 1, 'Alert must be shown');
    assert.strictEqual(env.alerts[0], 'Keine der ausgewählten Dateien ist noch in der Inbox – nichts gestartet.');

    // Button is restored and enabled
    assert.strictEqual(bulkBtn.disabled, false, 'Button must be re-enabled');
    assert.ok(bulkBtn.innerHTML.includes('Ausgewählte als Serie verarbeiten'), 'Button text must be restored');

    // Selection has been cleared
    assert.strictEqual(globalThis.selectedInboxProjects.size, 0);
});

test('AK5: Bulk-Klick wenn alle Einträge in Verarbeitung sind: startSeriesGroupWorkflow wird nicht aufgerufen, Meldung erscheint, Knopf wieder aktiv', async () => {
    const env = setupTestEnvironment();

    const suggestions = [
        { project: 'ProcessingShow.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
    globalThis.setCurrentSmartInboxRawSuggestions(suggestions);

    // Active projects processing contains this item
    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('ProcessingShow.S01E01.mkv');
    globalThis.updateBulkActionsBarUI();

    // Mark as processing
    const processingSet = new Set(['ProcessingShow.S01E01.mkv']);
    globalThis.renderQueue = () => {};
    // Emulate activeProjectsProcessing in scope
    globalThis.getActiveProjectsProcessing().add('ProcessingShow.S01E01.mkv');

    globalThis.activeSeriesGroupFiles = null;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);

    await bulkBtn.click();

    assert.strictEqual(globalThis.activeSeriesGroupFiles, null, 'startSeriesGroupWorkflow must NOT be called when all items are in processing');
    assert.strictEqual(env.alerts.length, 1);
    assert.strictEqual(env.alerts[0], 'Keine der ausgewählten Dateien ist noch in der Inbox – nichts gestartet.');
    assert.strictEqual(bulkBtn.disabled, false);
    assert.strictEqual(globalThis.selectedInboxProjects.size, 0);
});

// --------------------------------------------------------------------------
// AK6: Unverändert: gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (single_video_relpath)
// --------------------------------------------------------------------------
test('AK6: Gültige Auswahl aus TV-Einzeldatei und Einzelvideo-Ordner (single_video_relpath) ruft startSeriesGroupWorkflow mit korrekten files auf, keine Meldung', async () => {
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
            project: 'Show.Folder.S01E02',
            suggested_query: 'Show',
            single_video_query: 'Show',
            media_type: 'tv',
            is_dir: true,
            single_video_relpath: 'Show.Folder.S01E02/video.mkv',
            video_count: 1
        }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());

    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Show.S01E01.mkv');
    globalThis.selectedInboxProjects.add('Show.Folder.S01E02');
    globalThis.updateBulkActionsBarUI();

    globalThis.activeSeriesGroupFiles = null;
    globalThis.activeSeriesGroupName = null;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);

    await bulkBtn.click();

    assert.ok(globalThis.activeSeriesGroupFiles, 'startSeriesGroupWorkflow must be called');
    assert.deepStrictEqual(
        globalThis.activeSeriesGroupFiles,
        ['Show.S01E01.mkv', 'Show.Folder.S01E02/video.mkv'],
        'Files must contain single_video_relpath for folder and project name for file'
    );
    assert.strictEqual(env.alerts.length, 0, 'No alert should be shown for completely valid selection');
});

// --------------------------------------------------------------------------
// R1(c): Ineligible items (multi-video folders or locked movies) are cleared on redraw
// --------------------------------------------------------------------------
test('R1(c): Auswählbarkeit - Nicht auswählbare Einträge (gesperrter Film, Multi-Video-Ordner) werden beim Neuzeichnen entfernt', () => {
    const env = setupTestEnvironment();

    const suggestions = [
        { project: 'EligibleShow.S01E01.mkv', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'LockedMovie.mkv', media_type: 'movie', is_dir: false, video_count: 1 },
        { project: 'MultiVideoFolder', media_type: 'tv', is_dir: true, video_count: 3 }
    ];

    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('EligibleShow.S01E01.mkv');
    globalThis.selectedInboxProjects.add('LockedMovie.mkv');
    globalThis.selectedInboxProjects.add('MultiVideoFolder');

    globalThis.renderSmartInboxList(suggestions, new Set());

    assert.strictEqual(globalThis.selectedInboxProjects.has('EligibleShow.S01E01.mkv'), true);
    assert.strictEqual(globalThis.selectedInboxProjects.has('LockedMovie.mkv'), false, 'Locked movie must be removed from selection');
    assert.strictEqual(globalThis.selectedInboxProjects.has('MultiVideoFolder'), false, 'Multi-video folder must be removed from selection');
    assert.strictEqual(globalThis.selectedInboxProjects.size, 1);

    // Unlocking movie makes it eligible
    globalThis.unlockedMovieProjects.add('LockedMovie.mkv');
    globalThis.selectedInboxProjects.add('LockedMovie.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());
    assert.strictEqual(globalThis.selectedInboxProjects.has('LockedMovie.mkv'), true, 'Unlocked movie is eligible and remains selected');
    assert.strictEqual(globalThis.selectedInboxProjects.size, 2);
});

// --------------------------------------------------------------------------
// AK9: Bulk-Klick mit {A, Show "X".mkv}, Name mit Anführungszeichen ohne Treffer
// --------------------------------------------------------------------------
test('AK9: Bulk-Klick mit {A, Show "X".mkv} ohne Treffer für den zweiten: maskiert/sicher gegen SyntaxError, nur A geht an Workflow, Meldung "1 Eintrag ...", Show "X".mkv abgewählt und Kästchen unchecked', async () => {
    const env = setupTestEnvironment();

    const projA = 'ShowA.S01E01.mkv';
    const projX = 'Show "X".mkv';

    // Initial render where both items exist so that checkboxes for both are created in the DOM
    const initialSuggestions = [
        { project: projA, media_type: 'tv', is_dir: false, video_count: 1 },
        { project: projX, media_type: 'tv', is_dir: false, video_count: 1 }
    ];
    globalThis.renderSmartInboxList(initialSuggestions, new Set());

    // Both are selected and checked in DOM
    globalThis.selectedInboxProjects.add(projA);
    globalThis.selectedInboxProjects.add(projX);

    const allCheckboxes = globalThis.document.querySelectorAll('.smart-inbox-cb');
    let cbX = null;
    let cbA = null;
    for (const cb of allCheckboxes) {
        if (cb.dataset?.project === projX) {
            cb.checked = true;
            cbX = cb;
        }
        if (cb.dataset?.project === projA) {
            cb.checked = true;
            cbA = cb;
        }
    }
    assert.ok(cbX, 'Checkbox for Show "X".mkv must exist in DOM');
    assert.strictEqual(cbX.checked, true, 'Checkbox for Show "X".mkv must initially be checked');
    assert.ok(cbA, 'Checkbox for ShowA must exist in DOM');
    assert.strictEqual(cbA.checked, true);

    // Stale state: currentSmartInboxRawSuggestions only contains A (X disappeared / no hit), without prior redraw
    globalThis.setCurrentSmartInboxRawSuggestions([
        { project: projA, media_type: 'tv', is_dir: false, video_count: 1 }
    ]);
    globalThis.updateBulkActionsBarUI();

    assert.strictEqual(globalThis.selectedInboxProjects.size, 2);

    globalThis.activeSeriesGroupFiles = null;
    globalThis.activeSeriesGroupName = null;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn, 'Bulk action button must exist');

    await bulkBtn.click();

    // 1. Kein Fehler, nur A geht an startSeriesGroupWorkflow
    assert.ok(globalThis.activeSeriesGroupFiles, 'startSeriesGroupWorkflow must be called');
    assert.deepStrictEqual(globalThis.activeSeriesGroupFiles, [projA]);

    // 2. Meldung „1 Eintrag …“
    assert.strictEqual(env.alerts.length, 1, 'Alert must be displayed');
    assert.ok(
        env.alerts[0].includes('1 Eintrag') && env.alerts[0].includes('übersprungen'),
        `Alert must mention 1 skipped entry, got: "${env.alerts[0]}"`
    );

    // 3. Show "X".mkv nicht mehr ausgewählt
    assert.strictEqual(globalThis.selectedInboxProjects.has(projX), false, 'Show "X".mkv must be removed from selectedInboxProjects');
    assert.strictEqual(globalThis.selectedInboxProjects.has(projA), true, 'ShowA must remain in selectedInboxProjects');
    assert.strictEqual(globalThis.selectedInboxProjects.size, 1);

    // 4. sein Kästchen nicht mehr checked
    assert.strictEqual(cbX.checked, false, 'Checkbox for Show "X".mkv must no longer be checked');
    assert.strictEqual(cbA.checked, true, 'Checkbox for ShowA must remain checked');

    // Zähler aktualisiert
    const countEl = env.bulkBar.querySelector('#smart-inbox-bulk-count');
    assert.ok(countEl);
    assert.strictEqual(countEl.textContent, '1 ausgewählt');
});

// --------------------------------------------------------------------------
// AK10: Test-Hintertüren wurden aus gui/static/app.js entfernt
// --------------------------------------------------------------------------
test('AK10: gui/static/app.js enthält weder setCurrentSmartInboxRawSuggestions noch getCurrentSmartInboxRawSuggestions', () => {
    const rawContent = fs.readFileSync(appJsPath, 'utf8');
    assert.strictEqual(
        rawContent.includes('setCurrentSmartInboxRawSuggestions'),
        false,
        'app.js must not contain setCurrentSmartInboxRawSuggestions'
    );
    assert.strictEqual(
        rawContent.includes('getCurrentSmartInboxRawSuggestions'),
        false,
        'app.js must not contain getCurrentSmartInboxRawSuggestions'
    );
});
