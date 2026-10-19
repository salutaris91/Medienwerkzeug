import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');

let localStore = {};
const mockLocalStorage = {
    getItem: (key) => (key in localStore ? localStore[key] : null),
    setItem: (key, val) => { localStore[key] = String(val); },
    removeItem: (key) => { delete localStore[key]; },
    clear: () => { localStore = {}; }
};

let sessionStore = {};
const mockSessionStorage = {
    getItem: (key) => (key in sessionStore ? sessionStore[key] : null),
    setItem: (key, val) => { sessionStore[key] = String(val); },
    removeItem: (key) => { delete sessionStore[key]; },
    clear: () => { sessionStore = {}; }
};

function validateSelector(sel) {
    if (typeof sel !== 'string') return;
    const doubleQuotes = (sel.match(/(?<!\\)"/g) || []).length;
    const singleQuotes = (sel.match(/(?<!\\)'/g) || []).length;
    if (doubleQuotes % 2 !== 0 || singleQuotes % 2 !== 0) {
        const err = new Error(`Failed to execute 'querySelector': '${sel}' is not a valid selector.`);
        err.name = 'SyntaxError';
        throw err;
    }
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

const VOID_TAGS = new Set([
    'input', 'img', 'br', 'hr', 'meta', 'link', 'polygon', 'polyline', 'path', 'line', 'rect', 'circle'
]);

function parseHtmlToMockElements(html) {
    const topElements = [];
    const stack = [];
    const tagRegex = /<(\/?[a-z0-9\-]+)([^>]*)>/gi;
    let match;
    while ((match = tagRegex.exec(html)) !== null) {
        const rawTag = match[1].toLowerCase();
        const attrStr = match[2];
        if (rawTag.startsWith('/')) {
            const closeName = rawTag.slice(1);
            for (let i = stack.length - 1; i >= 0; i--) {
                if (stack[i].el.tagName.toLowerCase() === closeName) {
                    const popped = stack.splice(i)[0];
                    const innerChunk = html.slice(popped.contentStart, match.index);
                    popped.el._setInnerHtmlDirect(innerChunk);
                    break;
                }
            }
            continue;
        }

        const isSelfClosing = attrStr.trim().endsWith('/') || VOID_TAGS.has(rawTag);
        const attrs = {};
        const attrRegex = /([a-z0-9\-_]+)(?:=(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/gi;
        let attrMatch;
        while ((attrMatch = attrRegex.exec(attrStr)) !== null) {
            const name = attrMatch[1];
            if (name === '/') continue;
            const val = attrMatch[2] !== undefined ? attrMatch[2]
                : (attrMatch[3] !== undefined ? attrMatch[3]
                    : (attrMatch[4] !== undefined ? attrMatch[4] : ''));
            attrs[name] = val;
        }

        const el = createMockElement(rawTag, attrs);
        if (attrs['id'] && globalThis.__currentElementsById) {
            globalThis.__currentElementsById[attrs['id']] = el;
        }
        if (stack.length > 0) {
            stack[stack.length - 1].el.appendChild(el);
        } else {
            topElements.push(el);
        }

        if (!isSelfClosing) {
            stack.push({ el, contentStart: tagRegex.lastIndex });
        }
    }
    return topElements;
}

function decodeHtmlEntities(str) {
    return String(str || '')
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
}

function createMockElement(tagName = 'div', attributes = {}) {
    const attrs = { ...attributes };
    const classSet = new Set((attributes.class || attributes.className || '').split(/\s+/).filter(Boolean));
    const dataset = {};
    const listeners = {};
    const children = [];
    let innerHTMLValue = '';
    let textContentValue = '';
    let checkedValue = 'checked' in attributes && attributes.checked !== false && attributes.checked !== 'false';
    let disabledValue = 'disabled' in attributes && attributes.disabled !== false && attributes.disabled !== 'false';

    Object.entries(attrs).forEach(([k, v]) => {
        if (k.startsWith('data-')) {
            const prop = k.slice(5).replace(/-([a-z])/g, (_, l) => l.toUpperCase());
            dataset[prop] = String(v);
        }
    });

    const el = {
        tagName: tagName.toUpperCase(),
        id: attrs.id || '',
        title: attrs.title || '',
        value: attrs.value || '',
        options: [],
        selectedIndex: 0,
        scrollIntoViewCalls: 0,
        scrollIntoView(arg) {
            el.scrollIntoViewCalls++;
            el.lastScrollIntoViewArg = arg;
        },
        get checked() { return checkedValue; },
        set checked(v) { checkedValue = Boolean(v); },
        get disabled() { return disabledValue; },
        set disabled(v) { disabledValue = Boolean(v); },
        get className() {
            return Array.from(classSet).join(' ');
        },
        set className(val) {
            classSet.clear();
            String(val || '').split(/\s+/).filter(Boolean).forEach(c => classSet.add(c));
        },
        _setInnerHtmlDirect(rawHtml) {
            innerHTMLValue = String(rawHtml || '');
            textContentValue = decodeHtmlEntities(innerHTMLValue.replace(/<[^>]+>/g, '')).trim();
        },
        get innerHTML() {
            return innerHTMLValue;
        },
        set innerHTML(val) {
            innerHTMLValue = String(val || '');
            textContentValue = decodeHtmlEntities(innerHTMLValue.replace(/<[^>]+>/g, '')).trim();
            children.length = 0;
            const parsed = parseHtmlToMockElements(innerHTMLValue);
            parsed.forEach(ch => children.push(ch));
        },
        get textContent() {
            if (children.length > 0 && !textContentValue) {
                return children.map(c => c.textContent).join('');
            }
            return textContentValue;
        },
        set textContent(val) {
            textContentValue = String(val === null || val === undefined ? '' : val);
            innerHTMLValue = textContentValue;
            children.length = 0;
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
                const prop = name.slice(5).replace(/-([a-z])/g, (_, l) => l.toUpperCase());
                dataset[prop] = String(val);
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
                const prop = name.slice(5).replace(/-([a-z])/g, (_, l) => l.toUpperCase());
                delete dataset[prop];
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
            if (!event.currentTarget) {
                try { event.currentTarget = el; } catch (_) {}
            }
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
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    globalThis.localStorage = mockLocalStorage;
    globalThis.sessionStorage = mockSessionStorage;

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
    const btnSearchSeries = getOrCreateElement('btn-search-series', 'button');
    const seriesSearchQuery = getOrCreateElement('series-search-query', 'input');
    const seriesSearchResults = getOrCreateElement('series-search-results');
    const seriesSeasonNum = getOrCreateElement('series-season-num', 'input');
    seriesSeasonNum.value = '1';
    const selectedShowPanel = getOrCreateElement('selected-show-panel');
    const selectedMoviePanel = getOrCreateElement('selected-movie-panel');

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

    globalThis.triggerQualityHintUpdates = () => {};

    const consoleErrors = [];
    const consoleWarns = [];
    console.error = (...args) => {
        consoleErrors.push(args.map(a => (a && a.message ? a.message : String(a))).join(' '));
    };
    console.warn = (...args) => {
        consoleWarns.push(args.map(a => (a && a.message ? a.message : String(a))).join(' '));
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
    getOrCreateElement('context-movie');
    getOrCreateElement('movie-search-query', 'input');

    // Controllable Fake-Timer-Queue with delay threshold >= 30000
    let nextTimerId = 1;
    const pendingTimeouts = new Map();
    const clearedTimerIds = [];
    globalThis.setTimeout = (fn, delay) => {
        if (typeof delay === 'number' && delay >= 30000) {
            const id = nextTimerId++;
            pendingTimeouts.set(id, { id, fn, delay });
            return id;
        }
        if (typeof fn === 'function') fn();
        return 0;
    };
    globalThis.clearTimeout = (id) => {
        clearedTimerIds.push(id);
        pendingTimeouts.delete(id);
    };
    globalThis.setInterval = () => 0;
    globalThis.clearInterval = () => {};

    const alerts = [];
    globalThis.alert = (msg) => { alerts.push(msg); };
    const consoleLogs = [];
    globalThis.appendConsoleLog = (msg) => { consoleLogs.push(msg); };
    globalThis.onConsoleLog = (msg) => { consoleLogs.push(msg); };

    globalThis.window = {
        fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve([]) }),
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
globalThis.searchSeries = searchSeries;
globalThis.extractStrictSeasonEpisode = extractStrictSeasonEpisode;
globalThis.inboxFilesEntryForItem = inboxFilesEntryForItem;
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
globalThis.getActiveSeriesGroupFiles = () => activeSeriesGroupFiles;
globalThis.getActiveSeriesGroupName = () => activeSeriesGroupName;
globalThis.setActiveSeriesGroupFiles = (val) => { activeSeriesGroupFiles = val; if (typeof globalThis !== 'undefined') globalThis.activeSeriesGroupFiles = val; };
globalThis.setActiveSeriesGroupName = (val) => { activeSeriesGroupName = val; if (typeof globalThis !== 'undefined') globalThis.activeSeriesGroupName = val; };
globalThis.renderSmartInboxList = renderSmartInboxList;
globalThis.sortInboxSuggestions = sortInboxSuggestions;
globalThis.getInboxSortState = getInboxSortState;
globalThis.setInboxSortState = setInboxSortState;
globalThis.initEventListeners = initEventListeners;
`;

    eval(cleanAppJs);

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
        btnSearchSeries,
        seriesSearchQuery,
        seriesSearchResults,
        selectedShowPanel,
        selectedMoviePanel,
        deletedProjects,
        alerts,
        consoleLogs,
        consoleErrors,
        consoleWarns,
        getOrCreateElement,
        viewEmpty,
        viewFolder,
        folderModeSelector,
        pendingTimeouts,
        clearedTimerIds,
        getPendingTimeoutCount: () => pendingTimeouts.size,
        getPendingTimeouts: () => Array.from(pendingTimeouts.values()),
        triggerNextTimeout: () => {
            const first = pendingTimeouts.values().next().value;
            if (!first) return false;
            pendingTimeouts.delete(first.id);
            if (typeof first.fn === 'function') first.fn();
            return true;
        },
        triggerTimeoutById: (id) => {
            const entry = pendingTimeouts.get(id);
            if (!entry) return false;
            pendingTimeouts.delete(id);
            if (typeof entry.fn === 'function') entry.fn();
            return true;
        },
        triggerAllTimeouts: () => {
            const entries = Array.from(pendingTimeouts.values());
            pendingTimeouts.clear();
            for (const entry of entries) {
                if (typeof entry.fn === 'function') entry.fn();
            }
            return entries.length;
        }
    };
}

/**
 * Browser-faithful fetch spy for /api/search:
 * Records each search request and rejects with an AbortError when the passed AbortSignal aborts.
 */
function installAbortAwareSearchFetch() {
    const searchCalls = [];
    globalThis.fetch = (url, options = {}) => {
        const urlStr = String(url);
        if (urlStr.includes('/api/search')) {
            const signal = options ? options.signal : undefined;
            let resolveFn;
            let rejectFn;
            const callRecord = {
                url: urlStr,
                options,
                signal,
                aborted: Boolean(signal && signal.aborted),
                settled: false,
                resolveWith: (data, ok = true, status = 200) => {
                    if (callRecord.settled) return;
                    callRecord.settled = true;
                    resolveFn({
                        ok,
                        status,
                        json: async () => data
                    });
                },
                rejectWith: (err) => {
                    if (callRecord.settled) return;
                    callRecord.settled = true;
                    rejectFn(err);
                }
            };
            const promise = new Promise((resolve, reject) => {
                resolveFn = resolve;
                rejectFn = reject;
                if (signal) {
                    const onAbort = () => {
                        callRecord.aborted = true;
                        if (callRecord.settled) return;
                        callRecord.settled = true;
                        const abortErr = new Error('The operation was aborted.');
                        abortErr.name = 'AbortError';
                        reject(abortErr);
                    };
                    if (signal.aborted) {
                        onAbort();
                    } else if (typeof signal.addEventListener === 'function') {
                        signal.addEventListener('abort', onAbort, { once: true });
                    }
                }
            });
            searchCalls.push(callRecord);
            return promise;
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    };
    return searchCalls;
}

function makeSuggestionsFixture() {
    return [
        { project: 'AlphaShow.S01E01.mkv', suggested_query: 'AlphaShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'AlphaShow.S01E02.mkv', suggested_query: 'AlphaShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'AlphaShow.S02E01.mkv', suggested_query: 'AlphaShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'BetaShow.S01E01.mkv', suggested_query: 'BetaShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'BetaShow.S01E02.mkv', suggested_query: 'BetaShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'LooseEp.S01E01.mkv', suggested_query: 'LooseEp', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
}

const EXPECTED_TIMEOUT_MESSAGE = 'Suchfehler: Zeitüberschreitung nach 30 Sekunden. Bitte erneut versuchen.';

// --------------------------------------------------------------------------
// E3-AK1: Frist bei hängender Suche
// --------------------------------------------------------------------------
test('E3-AK1: Hängende Suche wird nach Auslösen des 30-s-Frist-Timers abgebrochen (signal-Abbruch, sichtbare Fristmeldung in series-search-results, Sperre frei für nachfolgenden Start)', async () => {
    const env = setupTestEnvironment();
    const searchCalls = installAbortAwareSearchFetch();

    const suggestions = makeSuggestionsFixture();
    globalThis.appliedInboxGroups.add('AlphaShow');
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow, 'Group row for AlphaShow must exist');
    const allBtn = groupRow.querySelector('.btn-select-group');
    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');

    // Start workflow via Alle-Knopf -> fetch hangs
    const firstStartPromise = allBtn.click();
    assert.strictEqual(searchCalls.length, 1, 'First start must trigger /api/search');
    assert.ok(searchCalls[0].signal, 'fetch must receive an AbortSignal');
    assert.strictEqual(searchCalls[0].signal.aborted, false, 'Signal must not be aborted before deadline');
    assert.strictEqual(searchCalls[0].aborted, false);

    // 30 000 ms deadline timer must be queued
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'Exactly one 30s deadline timer must be registered in the queue');
    const queuedTimer = env.getPendingTimeouts()[0];
    assert.strictEqual(queuedTimer.delay, 30000, 'Deadline timer must use SERIES_SEARCH_TIMEOUT_MS = 30000');

    // While hanging, shared lock blocks other starts
    await bulkBtn.click();
    assert.strictEqual(searchCalls.length, 1, 'Lock must prevent second start while search is still hanging');

    // Trigger 30s deadline timer from queue
    const triggered = env.triggerNextTimeout();
    assert.strictEqual(triggered, true, 'Deadline timer must be triggered');
    await firstStartPromise;

    // 1. Signal aborted on fetch spy
    assert.strictEqual(searchCalls[0].aborted, true, 'fetch spy must observe signal abort');
    assert.strictEqual(searchCalls[0].signal.aborted, true, 'AbortSignal.aborted must be true after timeout');

    // 2. Visible timeout message in series-search-results (exact UI text & pattern :3212)
    assert.strictEqual(
        env.seriesSearchResults.innerHTML,
        `<p class="text-center text-danger">${EXPECTED_TIMEOUT_MESSAGE}</p>`,
        'series-search-results must render exact timeout markup following pattern :3212'
    );
    assert.strictEqual(
        env.seriesSearchResults.textContent,
        EXPECTED_TIMEOUT_MESSAGE,
        'series-search-results textContent must match UI text table exactly'
    );

    // 3. Queue cleaned up
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'Timeout queue must be empty after timeout settlement');

    // 4. Shared lock is free -> subsequent start succeeds immediately
    const secondStartPromise = bulkBtn.click();
    assert.strictEqual(searchCalls.length, 2, 'Subsequent start must run because lock was released after timeout');
    searchCalls[1].resolveWith([{ id: '1', name: 'LooseEp', provider: 'tmdb', media_type: 'tv' }]);
    await secondStartPromise;
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'Second search timer must be cleaned up after completion');
});

// --------------------------------------------------------------------------
// E3-AK2: Ablösung bleibt still (inkl. Seq-Guard bei spätem Frist-Timer)
// --------------------------------------------------------------------------
test('E3-AK2: Suche A hängt, Suche B startet -> A endet still ohne Meldung; selbst wenn A-Frist-Timer nach B-Start ausgelöst wird, bleibt A still (Seq-Guard) und B-Ergebnisse bleiben stehen', async () => {
    const env = setupTestEnvironment();
    const searchCalls = installAbortAwareSearchFetch();

    // --- Teil 1: Suche A hängt, Suche B startet und löst A ab ---
    env.seriesSearchQuery.value = 'ShowA';
    const searchAPromise = globalThis.searchSeries();
    assert.strictEqual(searchCalls.length, 1);
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'Search A must register a 30s deadline timer');
    const timerIdA = env.getPendingTimeouts()[0].id;

    // Search B starts while A is hanging
    env.seriesSearchQuery.value = 'ShowB';
    const searchBPromise = globalThis.searchSeries();
    assert.strictEqual(searchCalls.length, 2);

    // A was aborted by B via currentSearchSeriesController
    assert.strictEqual(searchCalls[0].signal.aborted, true, 'Search B must abort Search A');
    assert.strictEqual(searchCalls[1].signal.aborted, false, 'Search B signal must remain active');

    await searchAPromise;

    // A ended silently: B's spinner is still in series-search-results, A's timer was cleared in finally
    assert.strictEqual(
        env.seriesSearchResults.innerHTML,
        '<div class="loading-spinner"></div>',
        'Aborted Search A must remain silent and not overwrite Search B spinner'
    );
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'Search A finally must have cleared A timer, leaving only B timer');
    assert.ok(env.clearedTimerIds.includes(timerIdA), 'clearTimeout must have been called for Search A timer');

    // Resolve Search B with results
    searchCalls[1].resolveWith([{ id: '202', name: 'Show B Treffer', provider: 'tmdb', media_type: 'tv' }]);
    await searchBPromise;
    assert.ok(env.seriesSearchResults.innerHTML.includes('Show B Treffer'), 'Search B results must be rendered');
    assert.strictEqual(env.seriesSearchResults.innerHTML.includes('Zeitüberschreitung'), false);
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'Search B timer must be cleared after B resolves');

    // --- Teil 2: Seq-Guard & localController-Isolierung bei identischem Query-String, wenn A's Frist-Timer NACH B's Start feuert ---
    // Custom fetch spy where Call 1 (Search A2) delays its AbortError rejection until after A2's deadline timer is triggered after B2's start,
    // so A2's catch sees didTimeout === true AND identical query string ("Tatort") while seq !== searchSeriesRequestSeq!
    const lateAbortCalls = [];
    globalThis.fetch = (url, options = {}) => {
        const urlStr = String(url);
        if (urlStr.includes('/api/search')) {
            const signal = options ? options.signal : undefined;
            const callIdx = lateAbortCalls.length;
            let resolveFn;
            let rejectFn;
            const record = {
                signal,
                resolveWith: (data) => resolveFn({ ok: true, status: 200, json: async () => data }),
                rejectAbortNow: () => {
                    const abortErr = new Error('The operation was aborted.');
                    abortErr.name = 'AbortError';
                    rejectFn(abortErr);
                }
            };
            const promise = new Promise((resolve, reject) => {
                resolveFn = resolve;
                rejectFn = reject;
                if (signal && callIdx > 0) {
                    signal.addEventListener('abort', () => record.rejectAbortNow(), { once: true });
                }
            });
            lateAbortCalls.push(record);
            return promise;
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    };

    // Start Search A2 with query "Tatort"
    env.seriesSearchQuery.value = 'Tatort';
    const searchA2Promise = globalThis.searchSeries();
    assert.strictEqual(lateAbortCalls.length, 1);
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'Search A2 must register a 30s timer');
    const timerA2 = env.getPendingTimeouts()[0];

    // Start Search B2 with the IDENTICAL query "Tatort" (would bypass string guard query !== lastSearchSeriesQuery!)
    env.seriesSearchQuery.value = 'Tatort';
    const searchB2Promise = globalThis.searchSeries();
    assert.strictEqual(lateAbortCalls.length, 2);

    // Trigger A2's deadline timer AFTER B2 has started!
    timerA2.fn();

    // 1. A2's timer callback must ONLY abort A2's localController, NEVER B2's currentSearchSeriesController ([advocatus] F3.2)
    assert.strictEqual(lateAbortCalls[0].signal.aborted, true, 'A2 signal must be aborted');
    assert.strictEqual(lateAbortCalls[1].signal.aborted, false, 'A2 deadline callback must NOT abort B2 controller');

    // 2. While B2 is still loading, let A2's fetch reject with AbortError (now with didTimeout === true in A2!)
    lateAbortCalls[0].rejectAbortNow();
    await searchA2Promise;

    // Seq-Guard prevents A2 from overwriting B2's spinner despite didTimeout === true and identical query "Tatort"
    assert.strictEqual(
        env.seriesSearchResults.innerHTML,
        '<div class="loading-spinner"></div>',
        'Seq-Guard must keep A2 silent even when didTimeout is true and query string is identical'
    );

    // 3. Resolve B2 with results and fire A2's timer callback again after B2 rendered -> B2's results remain intact
    lateAbortCalls[1].resolveWith([{ id: '303', name: 'Tatort B2 Ergebnis', provider: 'thetvdb', media_type: 'tv' }]);
    await searchB2Promise;
    const b2Html = env.seriesSearchResults.innerHTML;
    assert.ok(b2Html.includes('Tatort B2 Ergebnis'), 'B2 results must be rendered');

    assert.doesNotThrow(() => timerA2.fn(), 'Timer callback itself must never throw');
    assert.strictEqual(env.seriesSearchResults.innerHTML, b2Html, 'B2 results must remain standing after late A2 timer');
    assert.strictEqual(env.seriesSearchResults.innerHTML.includes('Zeitüberschreitung'), false);
});

// --------------------------------------------------------------------------
// E3-AK3: Normale Suche unberührt + Frist-Timer in finally zurückgebaut
// --------------------------------------------------------------------------
test('E3-AK3: Suche, die vor der Frist auflöst, rendert Ergebnisse wie bisher, zeigt keine Frist-Meldung und baut den Frist-Timer im finally zurück (Queue danach leer)', async () => {
    const env = setupTestEnvironment();
    const searchCalls = installAbortAwareSearchFetch();

    env.seriesSearchQuery.value = 'NormalShow';
    const searchPromise = globalThis.searchSeries();

    // While search is in flight, the 30s deadline timer is registered in the queue
    assert.strictEqual(searchCalls.length, 1);
    assert.strictEqual(env.getPendingTimeoutCount(), 1, '30s deadline timer must be registered while search is running');
    const activeTimer = env.getPendingTimeouts()[0];
    assert.strictEqual(activeTimer.delay, 30000);

    // Resolve search before the deadline
    searchCalls[0].resolveWith([
        { id: '777', name: 'Normal Show Alpha', provider: 'tmdb', media_type: 'tv' },
        { id: '778', name: 'Normal Show Beta', provider: 'thetvdb', media_type: 'tv' }
    ]);
    await searchPromise;

    // 1. Results rendered as before
    const items = env.seriesSearchResults.querySelectorAll('.search-item');
    assert.strictEqual(items.length, 2, 'Both search result items must be rendered');
    assert.strictEqual(items[0].getAttribute('data-id'), '777');
    assert.strictEqual(items[0].getAttribute('data-name'), 'Normal Show Alpha');
    assert.ok(items[0].textContent.includes('Normal Show Alpha'));
    assert.ok(items[1].textContent.includes('Normal Show Beta'));

    // 2. No timeout or error message
    assert.strictEqual(env.seriesSearchResults.innerHTML.includes('Zeitüberschreitung'), false, 'No timeout message on normal search');
    assert.strictEqual(env.seriesSearchResults.innerHTML.includes('Suchfehler'), false, 'No error message on normal search');

    // 3. Deadline timer cleaned up in finally (queue is empty)
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'Queue must be empty after normal search completes');
    assert.ok(env.clearedTimerIds.includes(activeTimer.id), 'clearTimeout must have been called with the deadline timer id in finally');
});

// --------------------------------------------------------------------------
// E3-AK4: Pfadabdeckung (Manueller Pfad Klick/Enter UND Workflow-Pfad)
// --------------------------------------------------------------------------
test('E3-AK4: Pfadabdeckung für E3-AK1/AK2/AK3 auf manuellem Pfad (btn-search-series-Klick und Enter im Suchfeld) UND Workflow-Pfad (startSeriesGroupWorkflow -> searchSeries)', async () => {
    const env = setupTestEnvironment();
    const searchCalls = installAbortAwareSearchFetch();

    // =========================================================================
    // A. Manueller Pfad 1: btn-search-series Klick (:7564)
    // =========================================================================
    // AK1 (Timeout via btn-search-series click)
    env.seriesSearchQuery.value = 'ManualClickShow';
    const clickTimeoutPromise = env.btnSearchSeries.click();
    assert.strictEqual(searchCalls.length, 1, 'btn-search-series click must invoke searchSeries');
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'btn-search-series search must register 30s timer');
    env.triggerNextTimeout();
    await clickTimeoutPromise;
    assert.strictEqual(searchCalls[0].aborted, true, 'Manual click search must abort on timeout');
    assert.strictEqual(env.seriesSearchResults.textContent, EXPECTED_TIMEOUT_MESSAGE);
    assert.strictEqual(env.getPendingTimeoutCount(), 0);

    // =========================================================================
    // B. Manueller Pfad 2: Enter im Suchfeld (:7566)
    // =========================================================================
    // AK1 (Timeout via Enter keypress)
    env.seriesSearchQuery.value = 'ManualEnterShow';
    await env.seriesSearchQuery.dispatchEvent({ type: 'keypress', key: 'Enter' });
    assert.strictEqual(searchCalls.length, 2, 'Enter keypress on series-search-query must invoke searchSeries');
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'Enter keypress search must register 30s timer');
    env.triggerNextTimeout();
    await new Promise(r => setImmediate(r));
    assert.strictEqual(searchCalls[1].aborted, true, 'Manual Enter search must abort on timeout');
    assert.strictEqual(env.seriesSearchResults.textContent, EXPECTED_TIMEOUT_MESSAGE);
    assert.strictEqual(env.getPendingTimeoutCount(), 0);

    // AK2 + AK3 on manual paths (btn-search-series click superseded by Enter keypress, which resolves normally)
    env.seriesSearchQuery.value = 'ManualFirst';
    const manualAPromise = env.btnSearchSeries.click();
    assert.strictEqual(searchCalls.length, 3);
    assert.strictEqual(env.getPendingTimeoutCount(), 1);
    const manualATimer = env.getPendingTimeouts()[0];

    env.seriesSearchQuery.value = 'ManualSecond';
    await env.seriesSearchQuery.dispatchEvent({ type: 'keypress', key: 'Enter' });
    assert.strictEqual(searchCalls.length, 4);
    assert.strictEqual(searchCalls[2].aborted, true, 'Enter search B must abort button-click search A');
    await manualAPromise;

    searchCalls[3].resolveWith([{ id: '404', name: 'Manual Second Hit', provider: 'tmdb', media_type: 'tv' }]);
    await new Promise(r => setImmediate(r));
    // Trigger A's saved timer callback after B finished -> B's results remain
    manualATimer.fn();
    assert.ok(env.seriesSearchResults.textContent.includes('Manual Second Hit'));
    assert.strictEqual(env.seriesSearchResults.textContent.includes('Zeitüberschreitung'), false);
    assert.strictEqual(env.getPendingTimeoutCount(), 0);

    // =========================================================================
    // C. Workflow-Pfad: startSeriesGroupWorkflow -> searchSeries (:13184-13185)
    // =========================================================================
    const suggestions = makeSuggestionsFixture();
    globalThis.appliedInboxGroups.add('AlphaShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const seasonBtns = groupRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button');
    const allBtn = groupRow.querySelector('.btn-select-group');

    // C1: AK1 on Workflow path (Season 1 button hangs -> timeout aborts, shows message, releases lock)
    const wfTimeoutPromise = seasonBtns[0].click();
    assert.strictEqual(searchCalls.length, 5, 'Workflow start via Season 1 button must call /api/search');
    assert.strictEqual(env.getPendingTimeoutCount(), 1);
    env.triggerNextTimeout();
    await wfTimeoutPromise;
    assert.strictEqual(searchCalls[4].aborted, true);
    assert.strictEqual(env.seriesSearchResults.textContent, EXPECTED_TIMEOUT_MESSAGE);
    assert.strictEqual(env.getPendingTimeoutCount(), 0);

    // C2: AK2 on Workflow path (Workflow start A hangs, superseded by manual search B -> A ends silently & releases lock)
    const wfAPromise = allBtn.click();
    assert.strictEqual(searchCalls.length, 6, 'Workflow start via Alle-Knopf must run because lock was freed');
    const wfATimer = env.getPendingTimeouts()[0];

    env.seriesSearchQuery.value = 'AlphaShow';
    const manualSupersedePromise = env.btnSearchSeries.click();
    assert.strictEqual(searchCalls.length, 7);
    assert.strictEqual(searchCalls[5].aborted, true, 'Superseding search must abort hanging workflow search');
    await wfAPromise;

    searchCalls[6].resolveWith([{ id: '505', name: 'AlphaShow Supersede Hit', provider: 'tmdb', media_type: 'tv' }]);
    await manualSupersedePromise;
    wfATimer.fn();
    assert.ok(env.seriesSearchResults.textContent.includes('AlphaShow Supersede Hit'));
    assert.strictEqual(env.seriesSearchResults.textContent.includes('Zeitüberschreitung'), false);
    assert.strictEqual(env.getPendingTimeoutCount(), 0);

    // C3: AK3 on Workflow path (Normal workflow start via Season 2 button resolves before deadline & cleans up timer)
    const wfNormalPromise = seasonBtns[1].click();
    assert.strictEqual(searchCalls.length, 8, 'Lock must be free for Season 2 workflow start');
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'Workflow search must register 30s timer');
    searchCalls[7].resolveWith([{ id: '606', name: 'AlphaShow Season 2 Hit', provider: 'thetvdb', media_type: 'tv' }]);
    await wfNormalPromise;
    assert.ok(env.seriesSearchResults.textContent.includes('AlphaShow Season 2 Hit'));
    assert.strictEqual(env.seriesSearchResults.textContent.includes('Zeitüberschreitung'), false);
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'Workflow search timer must be cleared in finally');
});

// --------------------------------------------------------------------------
// E3-AK5: Timer-Harness (Delay-Schwelle >= 30000, scrollIntoView 200ms sofort, 4 Dateien umgestellt)
// --------------------------------------------------------------------------
test('E3-AK5: Steuerbare Fake-Timer-Queue registriert Frist-Timer (delay >= 30000) ohne Sofortausführung, führt kleinere Delays (scrollIntoView 200ms) sofort aus und ersetzt die Sofort-Stubs in allen vier Bestands-Testdateien', async () => {
    const env = setupTestEnvironment();
    const searchCalls = installAbortAwareSearchFetch();

    // 1. Direct queue mechanics: < 30000 runs immediately, >= 30000 queues until triggered or cleared
    let shortDelayRan = false;
    globalThis.setTimeout(() => { shortDelayRan = true; }, 200);
    assert.strictEqual(shortDelayRan, true, 'setTimeout with delay < 30000 (200ms) must execute immediately');
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'Short delay timer must not be queued');

    let deadlineRan = false;
    const customId = globalThis.setTimeout(() => { deadlineRan = true; }, 30000);
    assert.strictEqual(deadlineRan, false, 'setTimeout with delay >= 30000 must NOT execute immediately');
    assert.strictEqual(env.getPendingTimeoutCount(), 1, '30000ms timer must be queued');
    globalThis.clearTimeout(customId);
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'clearTimeout must remove queued timer');
    assert.strictEqual(env.triggerNextTimeout(), false);
    assert.strictEqual(deadlineRan, false, 'Cleared timer must never execute');

    // 2. Integration with searchSeries (30000ms queued & cleared) and .search-item click scrollIntoView (200ms immediate, :3194/:3201)
    env.seriesSearchQuery.value = 'ScrollShow';
    const searchPromise = globalThis.searchSeries();
    assert.strictEqual(env.getPendingTimeoutCount(), 1, 'searchSeries must queue its 30000ms deadline timer without firing it immediately');

    searchCalls[0].resolveWith([
        { id: '801', name: 'Scroll TV Show', provider: 'tmdb', media_type: 'tv' },
        { id: '802', name: 'Scroll Movie Item', provider: 'tmdb', media_type: 'movie' }
    ]);
    await searchPromise;
    assert.strictEqual(env.getPendingTimeoutCount(), 0, 'searchSeries must clear its 30000ms timer in finally');

    const resultItems = env.seriesSearchResults.querySelectorAll('.search-item');
    assert.strictEqual(resultItems.length, 2);

    // Click TV result -> triggers 200ms scrollIntoView timer (:3201) immediately
    env.selectedShowPanel.scrollIntoViewCalls = 0;
    await resultItems[0].click();
    assert.strictEqual(env.selectedShowPanel.scrollIntoViewCalls, 1, '200ms scrollIntoView timer (:3201) must execute immediately');
    assert.strictEqual(env.getPendingTimeoutCount(), 0);
    await new Promise(r => setImmediate(r));

    // Click Movie result -> triggers 200ms scrollIntoView timer (:3194) immediately
    env.selectedMoviePanel.scrollIntoViewCalls = 0;
    await resultItems[1].click();
    assert.strictEqual(env.selectedMoviePanel.scrollIntoViewCalls, 1, '200ms scrollIntoView timer (:3194) must execute immediately');
    assert.strictEqual(env.getPendingTimeoutCount(), 0);
    await new Promise(r => setImmediate(r));

    // 3. Verify all four existing test files replaced the unconditional immediate setTimeout stub with the delay >= 30000 queue
    const harnessFiles = [
        'inbox_group.test.js',
        'inbox_group_banner.test.js',
        'inbox_selection.test.js',
        'inbox_group_seasons.test.js'
    ];
    for (const fileName of harnessFiles) {
        const content = fs.readFileSync(path.resolve(__dirname, fileName), 'utf8');
        assert.strictEqual(
            content.includes('globalThis.setTimeout = (fn) => { if (typeof fn === \'function\') fn(); return 0; };'),
            false,
            `${fileName} must no longer contain the unconditional immediate setTimeout stub`
        );
        assert.ok(
            content.includes('delay >= 30000'),
            `${fileName} must use the fake-timer queue with delay >= 30000 threshold`
        );
    }
});
