import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');

// Functional localStorage mock in module scope (survives second eval in AK3, no auto-clear in setupTestEnvironment)
let localStore = {};
const mockLocalStorage = {
    getItem: (key) => (key in localStore ? localStore[key] : null),
    setItem: (key, val) => { localStore[key] = String(val); },
    removeItem: (key) => { delete localStore[key]; },
    clear: () => { localStore = {}; }
};

// Functional sessionStorage mock with read/write counters for AK7
let sessionStore = {};
let sessionIgnoreReads = 0;
let sessionWrites = 0;
const mockSessionStorage = {
    getItem: (key) => {
        if (String(key).startsWith('smart-inbox-ignore-group-')) {
            sessionIgnoreReads++;
        }
        return key in sessionStore ? sessionStore[key] : null;
    },
    setItem: (key, val) => {
        sessionWrites++;
        sessionStore[key] = String(val);
    },
    removeItem: (key) => {
        sessionWrites++;
        delete sessionStore[key];
    },
    clear: () => {
        sessionStore = {};
        sessionIgnoreReads = 0;
        sessionWrites = 0;
    },
    resetCounters: () => {
        sessionIgnoreReads = 0;
        sessionWrites = 0;
    },
    getReads: () => sessionIgnoreReads,
    getWrites: () => sessionWrites
};

// Test-side variable controlling the pre-eval triggerQualityHintUpdates stub (AK9 / F1 / AK13)
let shouldThrowInQualityHint = false;

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

        const tagName = rawTag;
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

        const roleMatch = attrStr.match(/role=["']([^"']+)["']/i);
        if (roleMatch) {
            el.setAttribute('role', roleMatch[1]);
        }

        const styleMatch = attrStr.match(/style=["']([^"']*)["']/i);
        if (styleMatch) {
            el.style.cssText = styleMatch[1];
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

        if (stack.length > 0) {
            stack[stack.length - 1].el.__children.push(el);
        } else {
            topElements.push(el);
        }

        const isSelfClosing = VOID_TAGS.has(tagName) || /\/\s*$/.test(attrStr);
        if (!isSelfClosing) {
            stack.push({ el, contentStart: match.index + match[0].length });
        }
    }
    return topElements;
}

function decodeHtmlEntities(str) {
    return String(str)
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
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
            textContentVal = decodeHtmlEntities(innerHtmlVal.replace(/<[^>]*>/g, '').trim());
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
            textContentVal = decodeHtmlEntities(innerHtmlVal.replace(/<[^>]*>/g, '').trim());
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
    // Note: mockLocalStorage is intentionally NOT auto-cleared here so AK3 can test persistence across a fresh eval
    globalThis.localStorage = mockLocalStorage;
    globalThis.sessionStorage = mockSessionStorage;
    mockSessionStorage.resetCounters();
    shouldThrowInQualityHint = false;

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
    const seriesSearchResults = getOrCreateElement('series-search-results');
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

    // Pre-eval stub for triggerQualityHintUpdates controlled by test-only variable (AK9 / F1 / AK13)
    globalThis.triggerQualityHintUpdates = () => {
        if (shouldThrowInQualityHint) {
            throw new Error('Injected workflow start failure');
        }
    };

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
        seriesSearchResults,
        deletedProjects,
        alerts,
        consoleLogs,
        consoleErrors,
        consoleWarns,
        getOrCreateElement,
        viewEmpty,
        viewFolder,
        folderModeSelector
    };
}

function makeThreeGroupsSuggestions() {
    return [
        { project: 'Alpha.S01E01.mkv', suggested_query: 'Alpha', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Alpha.S01E02.mkv', suggested_query: 'Alpha', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Beta.S01E01.mkv', suggested_query: 'Beta', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Beta.S01E02.mkv', suggested_query: 'Beta', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Gamma.S02E01.mkv', suggested_query: 'Gamma', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Gamma.S02E02.mkv', suggested_query: 'Gamma', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
}

// --------------------------------------------------------------------------
// AK1: Mehrere Gruppen — alle offenen Vorschläge erreichbar
// --------------------------------------------------------------------------
test('AK1: Drei erkannte Gruppen A, B, C -> A prominent in Zone 1, B und C unter "Weitere Vorschläge (2)" erreichbar; bei nur einer Gruppe kein "Weitere Vorschläge"-Bereich', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions();

    globalThis.renderSmartInboxList(suggestions, new Set());

    assert.strictEqual(env.groupBanner.style.display, 'flex');

    // Zone 1: Alpha prominent
    const primaryZone = env.groupBanner.querySelector('.smart-inbox-group-banner-primary');
    assert.ok(primaryZone, 'Primary zone (.smart-inbox-group-banner-primary) must exist');
    assert.ok(primaryZone.innerHTML.includes('Alpha'), 'Primary zone must show first group Alpha');
    const primaryApplyBtn = primaryZone.querySelector('.btn-banner-apply-group');
    const primaryIgnoreBtn = primaryZone.querySelector('.btn-banner-ignore-group');
    assert.ok(primaryApplyBtn && primaryApplyBtn.textContent === 'Als Serie gruppieren');
    assert.ok(primaryIgnoreBtn && primaryIgnoreBtn.textContent === 'Ignorieren');

    // Zone 2: Weitere Vorschläge (2) with Beta and Gamma
    const moreZone = env.groupBanner.querySelector('.smart-inbox-group-banner-more');
    assert.ok(moreZone, 'More proposals zone (.smart-inbox-group-banner-more) must exist');
    const moreToggle = moreZone.querySelector('.smart-inbox-group-banner-toggle');
    assert.ok(moreToggle, 'More zone must have a toggle button');
    assert.strictEqual(moreToggle.textContent, 'Weitere Vorschläge (2)');
    assert.strictEqual(moreToggle.getAttribute('aria-expanded'), 'false', 'More zone must start collapsed');

    const moreList = moreZone.querySelector('.smart-inbox-group-banner-more-list');
    assert.ok(moreList, 'More list container must exist');
    assert.strictEqual(moreList.style.display, 'none', 'More list must be hidden initially');

    // Expand Zone 2
    await moreToggle.click();
    assert.strictEqual(moreToggle.getAttribute('aria-expanded'), 'true', 'More zone must expand on click');
    assert.notStrictEqual(moreList.style.display, 'none', 'More list must be visible when expanded');

    const moreApplyBtns = moreZone.querySelectorAll('.btn-banner-apply-group');
    const moreIgnoreBtns = moreZone.querySelectorAll('.btn-banner-ignore-group');
    assert.strictEqual(moreApplyBtns.length, 2, 'More zone must have 2 apply buttons for Beta and Gamma');
    assert.strictEqual(moreIgnoreBtns.length, 2, 'More zone must have 2 ignore buttons for Beta and Gamma');
    assert.ok(moreApplyBtns.every(b => b.textContent === 'Als Serie gruppieren'));
    assert.ok(moreIgnoreBtns.every(b => b.textContent === 'Ignorieren'));
    assert.ok(moreZone.innerHTML.includes('Beta') && moreZone.innerHTML.includes('Gamma'));

    // Single open group -> no "Weitere Vorschläge" zone
    const singleGroupSuggestions = suggestions.slice(0, 2);
    globalThis.renderSmartInboxList(singleGroupSuggestions, new Set());
    assert.strictEqual(env.groupBanner.style.display, 'flex');
    assert.ok(env.groupBanner.querySelector('.smart-inbox-group-banner-primary'));
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-more'), null, 'No more-zone when only 1 group is open');
    assert.strictEqual(env.groupBanner.innerHTML.includes('Weitere Vorschläge'), false);
});

// --------------------------------------------------------------------------
// AK2: Ignorieren eines beliebigen Vorschlags
// --------------------------------------------------------------------------
test('AK2: "Ignorieren" bei nicht-prominentem Vorschlag B schreibt JSON in localStorage, entfernt B aus offenen Vorschlägen und zeigt "Ausgeblendete Vorschläge (1)"', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions();

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Click ignore on second proposal (Beta, index 1 across all ignore buttons)
    const ignoreBtns = env.groupBanner.querySelectorAll('.btn-banner-ignore-group');
    assert.strictEqual(ignoreBtns.length, 3);
    await ignoreBtns[1].click();

    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Beta'), '{"ignored":true}');

    // Alpha remains prominent, only Gamma in "Weitere Vorschläge (1)"
    const primaryZone = env.groupBanner.querySelector('.smart-inbox-group-banner-primary');
    assert.ok(primaryZone.innerHTML.includes('Alpha'));
    assert.strictEqual(primaryZone.innerHTML.includes('Beta'), false);

    const moreZone = env.groupBanner.querySelector('.smart-inbox-group-banner-more');
    assert.ok(moreZone, 'More zone must still exist for 1 remaining additional proposal (Gamma)');
    const moreToggle = moreZone.querySelector('.smart-inbox-group-banner-toggle');
    assert.strictEqual(moreToggle.textContent, 'Weitere Vorschläge (1)');
    assert.ok(moreZone.innerHTML.includes('Gamma'));
    assert.strictEqual(moreZone.innerHTML.includes('Beta'), false);

    // Zone 3: Ausgeblendete Vorschläge (1) – wieder anzeigen
    const ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone, 'Ignored zone (.smart-inbox-group-banner-ignored) must appear');
    const ignoredToggle = ignoredZone.querySelector('.smart-inbox-group-banner-toggle');
    assert.ok(ignoredToggle);
    assert.strictEqual(ignoredToggle.textContent, 'Ausgeblendete Vorschläge (1) – wieder anzeigen');
    assert.ok(ignoredZone.innerHTML.includes('Ausgeblendete Vorschläge (1)'));
});

// --------------------------------------------------------------------------
// AK3: Persistenz über frischen Modulzustand
// --------------------------------------------------------------------------
test('AK3: Ignorierter Vorschlag bleibt nach zweitem eval mit frischem Modulzustand bei gleichem localStorage ausgeblendet', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env1 = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions();

    globalThis.renderSmartInboxList(suggestions, new Set());
    const ignoreBtns1 = env1.groupBanner.querySelectorAll('.btn-banner-ignore-group');
    await ignoreBtns1[1].click(); // Ignore Beta
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Beta'), '{"ignored":true}');

    // Second eval: fresh module state, same localStorage content
    const env2 = setupTestEnvironment();
    globalThis.renderSmartInboxList(suggestions, new Set());

    const openApplyBtns = env2.groupBanner.querySelectorAll('.btn-banner-apply-group');
    assert.strictEqual(openApplyBtns.length, 2, 'Only Alpha and Gamma must be open after fresh module load');
    assert.strictEqual(
        openApplyBtns.some(btn => btn.getAttribute('data-group-key') === 'Beta'),
        false,
        'Beta must remain ignored after fresh module load'
    );

    const ignoredZone = env2.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone, 'Restore zone must be rendered on fresh module load');
    const ignoredToggle = ignoredZone.querySelector('.smart-inbox-group-banner-toggle');
    assert.strictEqual(ignoredToggle.textContent, 'Ausgeblendete Vorschläge (1) – wieder anzeigen');
});

// --------------------------------------------------------------------------
// AK4: Wiederanzeigen einzeln und "alle"
// --------------------------------------------------------------------------
test('AK4: "Wieder anzeigen" entfernt einzelnen Schlüssel und stellt Vorschlag wieder her; "Alle wieder anzeigen" stellt alle aktuell erkannten Gruppen wieder her', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions();

    // Ignore Beta and Gamma
    mockLocalStorage.setItem('smart-inbox-ignore-group-Beta', '{"ignored":true}');
    mockLocalStorage.setItem('smart-inbox-ignore-group-Gamma', '{"ignored":true}');
    globalThis.renderSmartInboxList(suggestions, new Set());

    let ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone);
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (2) – wieder anzeigen'
    );

    // Single restore: click "Wieder anzeigen" for Beta
    const unignoreBtns = ignoredZone.querySelectorAll('.btn-banner-unignore-group');
    assert.strictEqual(unignoreBtns.length, 2);
    assert.strictEqual(unignoreBtns[0].textContent, 'Wieder anzeigen');
    await unignoreBtns[0].click();

    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Beta'), null, 'Beta key must be removed');
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Gamma'), '{"ignored":true}', 'Gamma key must remain');

    // Beta is open again (in Weitere Vorschläge (1)), counter drops to 1
    const moreZoneAfterSingle = env.groupBanner.querySelector('.smart-inbox-group-banner-more');
    assert.ok(moreZoneAfterSingle);
    assert.strictEqual(
        moreZoneAfterSingle.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Weitere Vorschläge (1)'
    );
    assert.ok(moreZoneAfterSingle.innerHTML.includes('Beta'));

    ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone);
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (1) – wieder anzeigen'
    );

    // Ignore Alpha as well so 2 groups (Alpha, Gamma) are ignored, then click "Alle wieder anzeigen"
    const primaryIgnoreBtn = env.groupBanner.querySelector('.smart-inbox-group-banner-primary .btn-banner-ignore-group');
    await primaryIgnoreBtn.click();
    ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (2) – wieder anzeigen'
    );

    const unignoreAllBtn = ignoredZone.querySelector('.btn-banner-unignore-all');
    assert.ok(unignoreAllBtn, '"Alle wieder anzeigen" button must exist');
    assert.strictEqual(unignoreAllBtn.textContent, 'Alle wieder anzeigen');
    await unignoreAllBtn.click();

    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Alpha'), null);
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Beta'), null);
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Gamma'), null);
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-ignored'), null, 'Restore zone must disappear when 0 groups are ignored');
    assert.strictEqual(env.groupBanner.querySelectorAll('.btn-banner-apply-group').length, 3, 'All 3 groups must be open again');
});

// --------------------------------------------------------------------------
// AK5: Verwaiste Schlüssel zählen und stören nicht
// --------------------------------------------------------------------------
test('AK5: Verwaister Schlüssel smart-inbox-ignore-group-GHOST zählt nicht, wird nicht gelistet und von "Alle wieder anzeigen" nicht entfernt', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();

    mockLocalStorage.setItem('smart-inbox-ignore-group-GHOST', '{"ignored":true}');
    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Only Alpha and Beta

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Neither Alpha nor Beta is ignored -> restore zone must not appear despite GHOST
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-ignored'), null);
    assert.strictEqual(env.groupBanner.innerHTML.includes('GHOST'), false);

    // Ignore Alpha -> counter must be (1), not (2)
    const ignoreBtn = env.groupBanner.querySelector('.btn-banner-ignore-group');
    await ignoreBtn.click();

    const ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone);
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (1) – wieder anzeigen'
    );
    assert.strictEqual(ignoredZone.innerHTML.includes('GHOST'), false);

    // Click "Alle wieder anzeigen" -> removes Alpha, leaves GHOST untouched
    const unignoreAllBtn = ignoredZone.querySelector('.btn-banner-unignore-all');
    await unignoreAllBtn.click();

    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Alpha'), null);
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-GHOST'), '{"ignored":true}', 'Orphan key GHOST must remain untouched');
});

// --------------------------------------------------------------------------
// AK6: Rückweg bleibt sichtbar / Banner leer bei null Gruppen
// --------------------------------------------------------------------------
test('AK6: Nach Ignorieren aller Gruppen bleibt Banner sichtbar (nur Rückweg-Zone); bei null erkannten Gruppen ist Banner ausgeblendet und leer', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Ignore Alpha, then Beta
    await env.groupBanner.querySelector('.btn-banner-ignore-group').click();
    await env.groupBanner.querySelector('.btn-banner-ignore-group').click();

    assert.strictEqual(env.groupBanner.style.display, 'flex', 'Banner must stay visible when all detected groups are ignored');
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-primary'), null, 'Primary zone must be absent when no open groups remain');
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-more'), null, 'More zone must be absent when no open groups remain');

    const ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone, 'Restore zone must be visible');
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (2) – wieder anzeigen'
    );

    // Zero detected groups (only single episodes / movies)
    const noGroupSuggestions = [
        { project: 'SingleEp.S01E01.mkv', suggested_query: 'SingleEp', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'SomeMovie.mkv', suggested_query: 'SomeMovie', media_type: 'movie', is_dir: false, video_count: 1 }
    ];
    globalThis.renderSmartInboxList(noGroupSuggestions, new Set());
    assert.strictEqual(env.groupBanner.style.display, 'none', 'Banner must be display:none when zero groups are detected');
    assert.strictEqual(env.groupBanner.innerHTML, '', 'Banner innerHTML must be empty when zero groups are detected');
});

// --------------------------------------------------------------------------
// AK7: Alte sessionStorage-Schlüssel wirken nicht mehr (Q2=A)
// --------------------------------------------------------------------------
test('AK7: Vorab gesetzter sessionStorage-Schlüssel blendet Vorschlag nicht aus; Ignorier-Pfad liest und schreibt kein sessionStorage', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();

    mockSessionStorage.setItem('smart-inbox-ignore-group-Alpha', 'true');
    mockSessionStorage.resetCounters();

    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta
    globalThis.renderSmartInboxList(suggestions, new Set());

    // Alpha must NOT be ignored
    const primaryZone = env.groupBanner.querySelector('.smart-inbox-group-banner-primary');
    assert.ok(primaryZone && primaryZone.innerHTML.includes('Alpha'), 'Alpha must remain open despite sessionStorage key');
    assert.strictEqual(mockSessionStorage.getReads(), 0, 'Banner render must not read from sessionStorage');

    // Click ignore on Beta
    const ignoreBtns = env.groupBanner.querySelectorAll('.btn-banner-ignore-group');
    await ignoreBtns[1].click();

    assert.strictEqual(mockSessionStorage.getReads(), 0, 'Ignore action must not read sessionStorage');
    assert.strictEqual(mockSessionStorage.getWrites(), 0, 'Ignore action must not write sessionStorage');
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-Beta'), '{"ignored":true}');
    assert.strictEqual(mockSessionStorage.getItem('smart-inbox-ignore-group-Beta'), null);
});

// --------------------------------------------------------------------------
// AK8: Sonderzeichen im Gruppennamen im strengen Selektor-Mock
// --------------------------------------------------------------------------
test('AK8: Gruppenname mit ", \', < und & funktioniert im strengen Selektor-Mock ohne SyntaxError (Anzeige escaped, Apply, Ignorieren, Zähler, Wiederanzeigen)', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const specialName = 'Show "Special" <\'Cut\' & Co>';

    const suggestions = [
        { project: 'Special.S01E01.mkv', suggested_query: specialName, media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Special.S01E02.mkv', suggested_query: specialName, media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Normal.S01E01.mkv', suggested_query: 'Normal', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Normal.S01E02.mkv', suggested_query: 'Normal', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Escaped output in HTML (no raw <'Cut' tag injection)
    assert.ok(env.groupBanner.innerHTML.includes('Show &quot;Special&quot; &lt;&#039;Cut&#039; &amp; Co&gt;'));
    assert.strictEqual(env.groupBanner.innerHTML.includes("<'Cut'"), false);

    // Ignore specialName group
    const ignoreBtn = env.groupBanner.querySelector('.btn-banner-ignore-group');
    await ignoreBtn.click();

    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-' + specialName), '{"ignored":true}');
    const ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone);
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (1) – wieder anzeigen'
    );

    // Single restore ("Wieder anzeigen") for specialName group
    const unignoreBtn = ignoredZone.querySelector('.btn-banner-unignore-group');
    assert.ok(unignoreBtn);
    await unignoreBtn.click();
    assert.strictEqual(mockLocalStorage.getItem('smart-inbox-ignore-group-' + specialName), null);

    // Apply ("Als Serie gruppieren") for specialName group
    const applyBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    assert.ok(applyBtn);
    await applyBtn.click();

    assert.strictEqual(globalThis.appliedInboxGroups.has(specialName), true);
    assert.strictEqual(globalThis.activeSeriesGroupName, specialName);
});

// --------------------------------------------------------------------------
// AK9: Fehlerfall beim Start aus dem Banner + Suchfehler-Test + Apply-Sperre
// --------------------------------------------------------------------------
test('AK9: Synchroner Wurf beim Start (via triggerQualityHintUpdates-Stub) nimmt appliedInboxGroups zurück, zeigt Inline-Meldung, ruft console.error und lässt Gruppe offen', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta

    globalThis.renderSmartInboxList(suggestions, new Set());

    // Activate test-side throw in pre-eval triggerQualityHintUpdates stub
    shouldThrowInQualityHint = true;

    const applyBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    await applyBtn.click();

    // (a) appliedInboxGroups must NOT contain Alpha
    assert.strictEqual(globalThis.appliedInboxGroups.has('Alpha'), false, 'Alpha must be rolled back from appliedInboxGroups');

    // (b) Visible inline error message in re-rendered banner with exact wording
    assert.notStrictEqual(env.groupBanner.style.display, 'none', 'Banner must be visible');
    const errorEl = env.groupBanner.querySelector('.smart-inbox-group-banner-error');
    assert.ok(errorEl, 'Inline error element .smart-inbox-group-banner-error must be rendered');
    assert.strictEqual(errorEl.getAttribute('role'), 'alert');
    assert.strictEqual(errorEl.getAttribute('aria-live'), 'polite');
    assert.strictEqual(errorEl.textContent, 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.');

    // (c) console.error called with failure cause
    assert.ok(env.consoleErrors.length >= 1, 'console.error must be called');
    assert.ok(
        env.consoleErrors.some(msg => msg.includes('Injected workflow start failure')),
        `console.error must log error cause, got: ${JSON.stringify(env.consoleErrors)}`
    );

    // (d) Alpha is back as an open proposal in banner (and not grouped in list)
    const primaryZone = env.groupBanner.querySelector('.smart-inbox-group-banner-primary');
    assert.ok(primaryZone && primaryZone.innerHTML.includes('Alpha'), 'Alpha must remain open in primary zone');
    assert.strictEqual(env.smartInboxList.querySelectorAll('.smart-inbox-group-row').length, 0);

    // Subsequent successful retry clears the error message and applies the group
    shouldThrowInQualityHint = false;
    const retryBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    await retryBtn.click();

    assert.strictEqual(globalThis.appliedInboxGroups.has('Alpha'), true, 'Retry must apply Alpha');
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-error'), null, 'Error message must be cleared on retry');
});

test('AK9 (F1-Zusatztest): Suchfehler nach Apply (fetch {ok:false} für /api/search) lässt Gruppe angewendet, zeigt keine Banner-Meldung und zeigt "Suchfehler" im Suchbereich', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta

    globalThis.fetch = (url) => {
        if (String(url).includes('/api/search')) {
            return Promise.resolve({
                ok: false,
                status: 500,
                json: async () => ({ error: 'Backend nicht erreichbar' })
            });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
    };

    globalThis.renderSmartInboxList(suggestions, new Set());
    const applyBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
    await applyBtn.click();

    assert.strictEqual(globalThis.appliedInboxGroups.has('Alpha'), true, 'Group Alpha must remain applied on search error');
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-error'), null, 'No banner error must appear on search error');
    assert.ok(env.seriesSearchResults.innerHTML.includes('Suchfehler'), 'Search results area must show "Suchfehler"');
});

test('AK9 (Apply-Sperre): Zweiter Apply-Klick während laufendem Start löst keinen zweiten Workflow aus (groupWorkflowRunning)', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta

    let resolveSearch = null;
    let searchCalls = 0;
    globalThis.fetch = (url) => {
        if (String(url).includes('/api/search')) {
            searchCalls++;
            return new Promise(resolve => {
                resolveSearch = () => resolve({ ok: true, json: async () => [] });
            });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
    };

    globalThis.renderSmartInboxList(suggestions, new Set());

    // First click on Alpha starts workflow and awaits pending searchSeries promise
    const applyBtnAlpha = env.groupBanner.querySelector('.btn-banner-apply-group');
    const firstClickPromise = applyBtnAlpha.click();

    // Banner has already re-rendered with Beta as the new primary candidate
    const applyBtnBeta = env.groupBanner.querySelector('.btn-banner-apply-group');
    assert.ok(applyBtnBeta && applyBtnBeta.getAttribute('data-group-key') === 'Beta');

    // Second click on Beta while Alpha's start is still running -> must be blocked
    await applyBtnBeta.click();

    assert.strictEqual(globalThis.appliedInboxGroups.has('Beta'), false, 'Beta must not be applied while Alpha workflow is still starting');
    assert.strictEqual(globalThis.activeSeriesGroupName, 'Alpha', 'Active group workflow must remain Alpha');
    assert.strictEqual(searchCalls, 1, 'Only one search request must have been started');

    // Finish first workflow start
    assert.ok(resolveSearch);
    resolveSearch();
    await firstClickPromise;

    // Now clicking Beta works normally
    const applyBtnBetaAfter = env.groupBanner.querySelector('.btn-banner-apply-group');
    const secondClickPromise = applyBtnBetaAfter.click();
    resolveSearch();
    await secondClickPromise;

    assert.strictEqual(globalThis.appliedInboxGroups.has('Beta'), true, 'Beta can be applied after first workflow finished');
});

// --------------------------------------------------------------------------
// AK10: Speicher verweigert (localStorage wirft bei getItem, setItem, removeItem)
// --------------------------------------------------------------------------
test('AK10: Werfendes localStorage crasht nicht, blendet Gruppe per In-Memory-Fallback für die Sitzung aus und protokolliert den Speicherfehler', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    await new Promise(r => setImmediate(r));

    globalThis.localStorage = {
        getItem: () => { throw new Error('SecurityError: getItem blocked'); },
        setItem: () => { throw new Error('QuotaExceededError: setItem blocked'); },
        removeItem: () => { throw new Error('SecurityError: removeItem blocked'); }
    };

    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta

    // Render must not crash despite getItem throwing
    assert.doesNotThrow(() => {
        globalThis.renderSmartInboxList(suggestions, new Set());
    });
    assert.strictEqual(env.groupBanner.style.display, 'flex');
    assert.strictEqual(env.groupBanner.querySelectorAll('.btn-banner-apply-group').length, 2);

    // Clear logs before ignore click to verify setItem failure logging specifically
    env.consoleWarns.length = 0;
    env.consoleErrors.length = 0;

    // Click ignore on Alpha -> must not crash, must hide Alpha for the session via fallback Set
    const ignoreBtn = env.groupBanner.querySelector('.btn-banner-ignore-group');
    await assert.doesNotReject(async () => {
        await ignoreBtn.click();
    });

    assert.ok(
        env.consoleWarns.length > 0 || env.consoleErrors.length > 0,
        'Storage error must be logged via console.warn or console.error'
    );

    const openApplyBtns = env.groupBanner.querySelectorAll('.btn-banner-apply-group');
    assert.strictEqual(openApplyBtns.length, 1, 'Alpha must be hidden for the session via in-memory fallback');
    assert.strictEqual(openApplyBtns[0].getAttribute('data-group-key'), 'Beta');

    const ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone, 'Restore zone must show Alpha from in-memory fallback');
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (1) – wieder anzeigen'
    );

    // Restore Alpha -> must not crash despite removeItem throwing
    const unignoreBtn = ignoredZone.querySelector('.btn-banner-unignore-group');
    await assert.doesNotReject(async () => {
        await unignoreBtn.click();
    });
    assert.strictEqual(env.groupBanner.querySelectorAll('.btn-banner-apply-group').length, 2, 'Alpha must be restored in session');
    globalThis.localStorage = mockLocalStorage;
});

// --------------------------------------------------------------------------
// AK15: Banner-Fehlermeldung wird beim Ignorieren und Wiederanzeigen (einzeln & alle) gelöscht (F-A)
// --------------------------------------------------------------------------
test('AK15: Nach gescheitertem Start, "Ignorieren" und "Wieder anzeigen" (einzeln sowie "Alle wieder anzeigen") steht keine Fehlermeldung mehr im Banner', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta

    globalThis.renderSmartInboxList(suggestions, new Set());

    // 1. Einzelnes "Wieder anzeigen": Trigger failed start on Alpha -> Ignore Alpha -> Unignore Alpha
    shouldThrowInQualityHint = true;
    const applyBtn1 = env.groupBanner.querySelector('.btn-banner-apply-group');
    await applyBtn1.click();

    let errorEl = env.groupBanner.querySelector('.smart-inbox-group-banner-error');
    assert.ok(errorEl, 'Inline error must appear after failed start');
    assert.strictEqual(errorEl.textContent, 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.');

    // Ignore Alpha
    const ignoreBtn1 = env.groupBanner.querySelector('.btn-banner-ignore-group');
    assert.strictEqual(ignoreBtn1.textContent, 'Ignorieren');
    await ignoreBtn1.click();
    assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-error'), null, 'No error must be shown while Alpha is ignored');

    // Unignore Alpha via single "Wieder anzeigen"
    const unignoreBtn = env.groupBanner.querySelector('.btn-banner-unignore-group');
    assert.ok(unignoreBtn);
    assert.strictEqual(unignoreBtn.textContent, 'Wieder anzeigen');
    await unignoreBtn.click();

    assert.strictEqual(
        env.groupBanner.querySelector('.smart-inbox-group-banner-error'),
        null,
        'Stale error message must not reappear after single "Wieder anzeigen"'
    );
    assert.strictEqual(
        env.groupBanner.innerHTML.includes('Serien-Start fehlgeschlagen. Bitte erneut versuchen.'),
        false,
        'Banner HTML must not contain stale error message after single "Wieder anzeigen"'
    );

    // 2. "Alle wieder anzeigen": Trigger failed start on Alpha -> Ignore Alpha -> Click "Alle wieder anzeigen"
    const applyBtn2 = env.groupBanner.querySelector('.btn-banner-apply-group');
    await applyBtn2.click();

    errorEl = env.groupBanner.querySelector('.smart-inbox-group-banner-error');
    assert.ok(errorEl, 'Inline error must appear after second failed start');
    assert.strictEqual(errorEl.textContent, 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.');

    const ignoreBtn2 = env.groupBanner.querySelector('.btn-banner-ignore-group');
    await ignoreBtn2.click();

    const unignoreAllBtn = env.groupBanner.querySelector('.btn-banner-unignore-all');
    assert.ok(unignoreAllBtn);
    assert.strictEqual(unignoreAllBtn.textContent, 'Alle wieder anzeigen');
    await unignoreAllBtn.click();

    assert.strictEqual(
        env.groupBanner.querySelector('.smart-inbox-group-banner-error'),
        null,
        'Stale error message must not reappear after "Alle wieder anzeigen"'
    );
    assert.strictEqual(
        env.groupBanner.innerHTML.includes('Serien-Start fehlgeschlagen. Bitte erneut versuchen.'),
        false,
        'Banner HTML must not contain stale error message after "Alle wieder anzeigen"'
    );

    // 3. Verify that "Ignorieren" alone and "Wieder anzeigen" (single & all) alone each clear the error
    await env.groupBanner.querySelector('.btn-banner-apply-group').click();
    assert.ok(env.groupBanner.querySelector('.smart-inbox-group-banner-error'));
    await env.groupBanner.querySelector('.btn-banner-ignore-group').click();
    mockLocalStorage.removeItem('smart-inbox-ignore-group-Alpha');
    globalThis.renderSmartInboxList(suggestions, new Set());
    assert.strictEqual(
        env.groupBanner.querySelector('.smart-inbox-group-banner-error'),
        null,
        'Ignorieren alone must already clear bannerApplyErrors for the group'
    );

    await env.groupBanner.querySelector('.btn-banner-apply-group').click();
    assert.ok(env.groupBanner.querySelector('.smart-inbox-group-banner-error'));
    mockLocalStorage.setItem('smart-inbox-ignore-group-Alpha', '{"ignored":true}');
    globalThis.renderSmartInboxList(suggestions, new Set());
    await env.groupBanner.querySelector('.btn-banner-unignore-group').click();
    assert.strictEqual(
        env.groupBanner.querySelector('.smart-inbox-group-banner-error'),
        null,
        'Single "Wieder anzeigen" alone must clear bannerApplyErrors for the group'
    );

    await env.groupBanner.querySelector('.btn-banner-apply-group').click();
    assert.ok(env.groupBanner.querySelector('.smart-inbox-group-banner-error'));
    mockLocalStorage.setItem('smart-inbox-ignore-group-Alpha', '{"ignored":true}');
    globalThis.renderSmartInboxList(suggestions, new Set());
    await env.groupBanner.querySelector('.btn-banner-unignore-all').click();
    assert.strictEqual(
        env.groupBanner.querySelector('.smart-inbox-group-banner-error'),
        null,
        '"Alle wieder anzeigen" alone must clear bannerApplyErrors for the group'
    );
});

// --------------------------------------------------------------------------
// AK16: localStorage === undefined blendet Gruppe für die Sitzung aus und ruft console.warn auf (F-G)
// --------------------------------------------------------------------------
test('AK16: Bei localStorage === undefined blendet "Ignorieren" die Gruppe für die Sitzung aus und ruft console.warn auf', async () => {
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    const env = setupTestEnvironment();
    await new Promise(r => setImmediate(r));

    globalThis.localStorage = undefined;

    const suggestions = makeThreeGroupsSuggestions().slice(0, 4); // Alpha and Beta
    globalThis.renderSmartInboxList(suggestions, new Set());

    env.consoleWarns.length = 0;

    const ignoreBtn = env.groupBanner.querySelector('.btn-banner-ignore-group');
    assert.strictEqual(ignoreBtn.textContent, 'Ignorieren');
    await ignoreBtn.click();

    assert.ok(
        env.consoleWarns.length > 0,
        'console.warn must be called when localStorage is undefined'
    );

    const openApplyBtns = env.groupBanner.querySelectorAll('.btn-banner-apply-group');
    assert.strictEqual(openApplyBtns.length, 1, 'Alpha must be hidden for the session when localStorage is undefined');
    assert.strictEqual(openApplyBtns[0].getAttribute('data-group-key'), 'Beta');

    const ignoredZone = env.groupBanner.querySelector('.smart-inbox-group-banner-ignored');
    assert.ok(ignoredZone, 'Restore zone must show Alpha from in-memory fallback');
    assert.strictEqual(
        ignoredZone.querySelector('.smart-inbox-group-banner-toggle').textContent,
        'Ausgeblendete Vorschläge (1) – wieder anzeigen'
    );

    globalThis.localStorage = mockLocalStorage;
});
