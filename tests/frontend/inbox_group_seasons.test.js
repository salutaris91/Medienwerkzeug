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
    mockLocalStorage.clear();
    mockSessionStorage.clear();
    globalThis.localStorage = mockLocalStorage;
    globalThis.sessionStorage = mockSessionStorage;
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
    let nextTimerId = 1;
    const pendingTimeouts = new Map();
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

function makeMultiSeasonSuggestions() {
    // Deliberately unsorted seasons (11, 1, 2) and episodes (E03, E01, E02), including a folder episode with single_video_relpath
    return [
        { project: 'MultiShow.S11E03.mkv', suggested_query: 'MultiShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'MultiShow.S01E02.mkv', suggested_query: 'MultiShow', media_type: 'tv', is_dir: false, video_count: 1 },
        {
            project: 'MultiShow.S11E02.Folder',
            suggested_query: 'MultiShow',
            single_video_query: 'MultiShow',
            media_type: 'tv',
            is_dir: true,
            single_video_relpath: 'MultiShow.S11E02.Folder/episode2.mkv',
            video_count: 1
        },
        { project: 'MultiShow.S02E01.mkv', suggested_query: 'MultiShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'MultiShow.S01E01.mkv', suggested_query: 'MultiShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'MultiShow.S11E01.mkv', suggested_query: 'MultiShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'MultiShow.S01E03.mkv', suggested_query: 'MultiShow', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
}

function makeSingleSeasonSuggestions() {
    return [
        { project: 'SingleShow.S01E01.mkv', suggested_query: 'SingleShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'SingleShow.S01E02.mkv', suggested_query: 'SingleShow', media_type: 'tv', is_dir: false, video_count: 1 }
    ];
}

// --------------------------------------------------------------------------
// E1-AK1: Staffel-Knöpfe bei Mehrstaffel-Gruppen, keine bei Einzelstaffel, Alle-Knopf "Alle verarbeiten"
// --------------------------------------------------------------------------
test('E1-AK1: Gruppenzeile mit >= 2 Staffeln trägt genau einen Knopf pro Staffel ("Staffel N (k)", aufsteigend); Einzelstaffel-Gruppe hat KEINE Staffel-Knopf-Reihe; Alle-Knopf heißt "Alle verarbeiten"', () => {
    const env = setupTestEnvironment();
    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions()
    ];

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.appliedInboxGroups.add('SingleShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRows = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    assert.strictEqual(groupRows.length, 2, 'Two group rows must be rendered');

    const multiRow = groupRows.find(r => r.getAttribute('data-group-key') === 'MultiShow');
    const singleRow = groupRows.find(r => r.getAttribute('data-group-key') === 'SingleShow');
    assert.ok(multiRow, 'MultiShow group row must exist');
    assert.ok(singleRow, 'SingleShow group row must exist');

    // MultiShow (>= 2 seasons): seasons bar between headerDiv and membersDiv
    const seasonsDiv = multiRow.querySelector('.smart-inbox-group-seasons');
    assert.ok(seasonsDiv, 'Multi-season group row must contain .smart-inbox-group-seasons');

    const headerIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-header'));
    const seasonsIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-seasons'));
    const membersIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-members'));
    assert.ok(headerIdx >= 0 && seasonsIdx > headerIdx && membersIdx > seasonsIdx, 'Seasons bar must be placed between headerDiv and membersDiv');

    const seasonBtns = seasonsDiv.querySelectorAll('button');
    assert.strictEqual(seasonBtns.length, 3, 'Must render exactly one button per distinct season (1, 2, 11)');
    assert.deepStrictEqual(
        seasonBtns.map(b => b.textContent),
        ['Staffel 1 (3)', 'Staffel 2 (1)', 'Staffel 11 (3)'],
        'Season buttons must have exact wording "Staffel N (k)" sorted ascending'
    );
    seasonBtns.forEach(btn => {
        assert.strictEqual(btn.getAttribute('type'), 'button');
        assert.ok(btn.classList.contains('btn') && btn.classList.contains('btn-secondary') && btn.classList.contains('btn-xs'));
    });

    const multiAllBtn = multiRow.querySelector('.btn-select-group');
    assert.ok(multiAllBtn, 'MultiShow must have .btn-select-group');
    assert.strictEqual(multiAllBtn.textContent, 'Alle verarbeiten', 'MultiShow all-button must be labeled "Alle verarbeiten"');
    assert.strictEqual(multiAllBtn.innerHTML.includes('Auswählen'), false);

    // SingleShow (1 season): NO seasons bar, all-button still "Alle verarbeiten"
    assert.strictEqual(singleRow.querySelector('.smart-inbox-group-seasons'), null, 'Single-season group row must NOT have .smart-inbox-group-seasons');
    const singleAllBtn = singleRow.querySelector('.btn-select-group');
    assert.ok(singleAllBtn, 'SingleShow must have .btn-select-group');
    assert.strictEqual(singleAllBtn.textContent, 'Alle verarbeiten', 'SingleShow all-button must be labeled "Alle verarbeiten"');
    assert.strictEqual(singleAllBtn.innerHTML.includes('Auswählen'), false);
});

// --------------------------------------------------------------------------
// E1-AK2: Klick auf "Staffel 11" übergibt genau die Folgen dieser Staffel (inkl. Ordner-Folge) + Ansichtswechsel
// --------------------------------------------------------------------------
test('E1-AK2: Klick auf "Staffel 11 (3)" übergibt startSeriesGroupWorkflow genau die Folgen dieser Staffel in Folgenreihenfolge (Ordner-Folge über single_video_relpath) und wechselt die Ansicht', async () => {
    const env = setupTestEnvironment();
    const suggestions = makeMultiSeasonSuggestions();

    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const seasonsDiv = multiRow.querySelector('.smart-inbox-group-seasons');
    assert.ok(seasonsDiv, 'Seasons bar must exist');

    const season11Btn = seasonsDiv.querySelectorAll('button').find(b => b.textContent === 'Staffel 11 (3)');
    assert.ok(season11Btn, 'Button "Staffel 11 (3)" must exist');

    await season11Btn.click();

    assert.strictEqual(globalThis.getActiveSeriesGroupName(), 'MultiShow');
    assert.deepStrictEqual(
        globalThis.getActiveSeriesGroupFiles(),
        [
            'MultiShow.S11E01.mkv',
            'MultiShow.S11E02.Folder/episode2.mkv',
            'MultiShow.S11E03.mkv'
        ],
        'Must pass only Season 11 episodes in episode order, using single_video_relpath for folder episode'
    );

    assert.strictEqual(env.viewFolder.classList.contains('hidden'), false, 'view-folder must not be hidden after season button click');
    assert.strictEqual(env.viewFolder.classList.contains('active'), true, 'view-folder must be active after season button click');
    assert.strictEqual(env.viewEmpty.classList.contains('hidden'), true, 'view-empty must be hidden after season button click');
    assert.strictEqual(env.viewEmpty.classList.contains('active'), false, 'view-empty must not be active after season button click');
    assert.strictEqual(env.modeSeries.classList.contains('active'), true, 'mode-series must be active after season button click');
});

// --------------------------------------------------------------------------
// E1-AK3: Umbenannter Alle-Knopf ("Alle verarbeiten") übergibt weiterhin alle Folgen der Gruppe
// --------------------------------------------------------------------------
test('E1-AK3: Klick auf "Alle verarbeiten" übergibt alle Folgen der Gruppe in Staffel-/Folgenreihenfolge und startet den Workflow', async () => {
    const env = setupTestEnvironment();
    const suggestions = makeMultiSeasonSuggestions();

    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const allBtn = multiRow.querySelector('.btn-select-group');
    assert.ok(allBtn);
    assert.strictEqual(allBtn.textContent, 'Alle verarbeiten');

    await allBtn.click();

    assert.strictEqual(globalThis.getActiveSeriesGroupName(), 'MultiShow');
    assert.deepStrictEqual(
        globalThis.getActiveSeriesGroupFiles(),
        [
            'MultiShow.S01E01.mkv',
            'MultiShow.S01E02.mkv',
            'MultiShow.S01E03.mkv',
            'MultiShow.S02E01.mkv',
            'MultiShow.S11E01.mkv',
            'MultiShow.S11E02.Folder/episode2.mkv',
            'MultiShow.S11E03.mkv'
        ],
        'All-button must pass all episodes of the group sorted by season and episode'
    );

    assert.strictEqual(env.viewFolder.classList.contains('hidden'), false);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true);
    assert.strictEqual(env.viewEmpty.classList.contains('hidden'), true);
    assert.strictEqual(env.viewEmpty.classList.contains('active'), false);
    assert.strictEqual(env.modeSeries.classList.contains('active'), true);
});

// --------------------------------------------------------------------------
// E1-AK4: Staffel-Knöpfe und Alle-Knopf nach erneutem renderSmartInboxList (6-s-Takt)
// --------------------------------------------------------------------------
test('E1-AK4: Nach erneutem renderSmartInboxList (6-s-Takt) existieren Staffel-Knöpfe und Alle-Knopf erneut und starten korrekt', async () => {
    const env = setupTestEnvironment();
    const suggestions = makeMultiSeasonSuggestions();

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    // Simulate 6s poll re-render
    globalThis.renderSmartInboxList(suggestions, new Set());

    let multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    let seasonsDiv = multiRow.querySelector('.smart-inbox-group-seasons');
    assert.ok(seasonsDiv, 'Seasons bar must exist after re-render');
    const seasonBtns = seasonsDiv.querySelectorAll('button');
    assert.deepStrictEqual(
        seasonBtns.map(b => b.textContent),
        ['Staffel 1 (3)', 'Staffel 2 (1)', 'Staffel 11 (3)']
    );

    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');
    globalThis.setActiveSeriesGroupFiles(null);

    // Click Season 2 button after re-render
    await seasonBtns[1].click();
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), ['MultiShow.S02E01.mkv']);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true);

    // Another 6s poll re-render, then click All button
    globalThis.renderSmartInboxList(suggestions, new Set());
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');
    globalThis.setActiveSeriesGroupFiles(null);

    multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const allBtn = multiRow.querySelector('.btn-select-group');
    assert.ok(allBtn && allBtn.textContent === 'Alle verarbeiten');
    await allBtn.click();
    assert.strictEqual(globalThis.getActiveSeriesGroupFiles().length, 7);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true);
});

// --------------------------------------------------------------------------
// E1-AK5: Sonderzeichen im strengen validateSelector-Mock
// --------------------------------------------------------------------------
test('E1-AK5: Gruppenname mit ", \', < und & im strengen validateSelector-Mock: maskiert angezeigt, Staffel-Reihe gerendert, Staffel-Klick und Alle-Klick ohne Wurf', async () => {
    const env = setupTestEnvironment();
    const specialName = 'Show "Special" <\'Cut\' & Co>';

    const suggestions = [
        { project: 'Special.S01E01.mkv', suggested_query: specialName, media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Special.S02E01.mkv', suggested_query: specialName, media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'Special.S02E02.mkv', suggested_query: specialName, media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    globalThis.appliedInboxGroups.add(specialName);
    globalThis.renderSmartInboxList(suggestions, new Set());

    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow, 'Group row must be rendered');
    const headerDiv = groupRow.querySelector('.smart-inbox-group-header');
    assert.ok(headerDiv, 'Group header must be rendered');
    assert.ok(headerDiv.innerHTML.includes('Show &quot;Special&quot; &lt;&#039;Cut&#039; &amp; Co&gt;'), 'Group title must be escaped');
    assert.strictEqual(headerDiv.innerHTML.includes("<'Cut'"), false, 'Raw unescaped markup must not appear');

    const seasonsDiv = groupRow.querySelector('.smart-inbox-group-seasons');
    assert.ok(seasonsDiv, 'Seasons row must be rendered for special group');
    const seasonBtns = seasonsDiv.querySelectorAll('button');
    assert.deepStrictEqual(seasonBtns.map(b => b.textContent), ['Staffel 1 (1)', 'Staffel 2 (2)']);

    // Season click without SyntaxError
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');
    await assert.doesNotReject(async () => {
        await seasonBtns[1].click();
    });
    assert.strictEqual(globalThis.getActiveSeriesGroupName(), specialName);
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), ['Special.S02E01.mkv', 'Special.S02E02.mkv']);

    // Re-render and All-button click without SyntaxError
    globalThis.renderSmartInboxList(suggestions, new Set());
    const groupRow2 = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const allBtn = groupRow2.querySelector('.btn-select-group');
    assert.ok(allBtn);
    globalThis.setActiveSeriesGroupFiles(null);
    await assert.doesNotReject(async () => {
        await allBtn.click();
    });
    assert.strictEqual(globalThis.getActiveSeriesGroupName(), specialName);
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), ['Special.S01E01.mkv', 'Special.S02E01.mkv', 'Special.S02E02.mkv']);
});

// --------------------------------------------------------------------------
// E1-AK6: Banner-Split bei >= 2 Staffeln + Hinweiszeile vs. Sofortstart bei 1 Staffel
// --------------------------------------------------------------------------
test('E1-AK6: Banner bei >= 2 Staffeln zeigt Hinweiszeile und gruppiert bei Klick nur (kein Workflow-Start); bei 1 Staffel keine Hinweiszeile und Sofortstart inkl. Fehlerpfad', async () => {
    const env = setupTestEnvironment();
    const expectedHint = 'Diese Serie hat mehrere Staffeln – nach dem Gruppieren kannst du in der Liste eine einzelne Staffel oder alle Folgen verarbeiten.';

    let searchCalls = 0;
    globalThis.fetch = (url) => {
        if (String(url).includes('/api/search')) {
            searchCalls++;
        }
        return Promise.resolve({ ok: true, json: async () => [] });
    };

    // --- Part A: >= 2 seasons in banner ---
    const multiSuggestions = makeMultiSeasonSuggestions();
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    env.modeSeries.classList.remove('active');
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');

    globalThis.renderSmartInboxList(multiSuggestions, new Set());

    // Hint must be present in banner with exact wording (including en-dash U+2013)
    const primaryZone = env.groupBanner.querySelector('.smart-inbox-group-banner-primary');
    assert.ok(primaryZone, 'Primary banner zone must exist');
    assert.ok(
        primaryZone.innerHTML.includes(expectedHint),
        `Banner must show multi-season hint with exact text "${expectedHint}"`
    );

    const applyMultiBtn = primaryZone.querySelector('.btn-banner-apply-group');
    assert.ok(applyMultiBtn);
    await applyMultiBtn.click();

    // Must be added to appliedInboxGroups and rendered as group row in list
    assert.strictEqual(globalThis.appliedInboxGroups.has('MultiShow'), true, 'MultiShow must be added to appliedInboxGroups');
    const groupRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(groupRow, 'Group row must appear in smartInboxList after banner click');
    assert.ok(groupRow.querySelector('.smart-inbox-group-seasons'), 'Group row must show season buttons');

    // NO workflow start: view unchanged, activeSeriesGroupFiles untouched, no /api/search call
    assert.strictEqual(globalThis.getActiveSeriesGroupFiles(), null, 'activeSeriesGroupFiles must remain null (startSeriesGroupWorkflow not called)');
    assert.strictEqual(globalThis.getActiveSeriesGroupName(), '', 'activeSeriesGroupName must remain empty');
    assert.strictEqual(env.viewEmpty.classList.contains('active'), true, 'view-empty must remain active');
    assert.strictEqual(env.viewFolder.classList.contains('hidden'), true, 'view-folder must remain hidden');
    assert.strictEqual(env.modeSeries.classList.contains('active'), false, 'mode-series must not become active');
    assert.strictEqual(searchCalls, 0, 'No /api/search fetch must be triggered when grouping >= 2 seasons');

    // --- Part B: 1 season in banner (immediate start + error path) ---
    globalThis.appliedInboxGroups.clear();
    const singleSuggestions = makeSingleSeasonSuggestions();
    globalThis.renderSmartInboxList(singleSuggestions, new Set());

    const singlePrimary = env.groupBanner.querySelector('.smart-inbox-group-banner-primary');
    assert.ok(singlePrimary);
    assert.strictEqual(
        env.groupBanner.innerHTML.includes(expectedHint),
        false,
        'Single-season group in banner must NOT show multi-season hint'
    );
    assert.strictEqual(
        env.groupBanner.innerHTML.includes('Diese Serie hat mehrere Staffeln'),
        false,
        'Single-season group must not contain any multi-season hint text'
    );

    // Error path on 1-season banner apply
    shouldThrowInQualityHint = true;
    const applySingleBtnErr = singlePrimary.querySelector('.btn-banner-apply-group');
    await applySingleBtnErr.click();
    assert.strictEqual(globalThis.appliedInboxGroups.has('SingleShow'), false, 'Failed 1-season start must roll back appliedInboxGroups');
    assert.ok(env.groupBanner.querySelector('.smart-inbox-group-banner-error'), 'Failed 1-season start must show banner error');

    // Successful immediate start on 1-season banner apply
    shouldThrowInQualityHint = false;
    const applySingleBtnOk = env.groupBanner.querySelector('.btn-banner-apply-group');
    await applySingleBtnOk.click();
    assert.strictEqual(globalThis.appliedInboxGroups.has('SingleShow'), true, '1-season group must be applied');
    assert.strictEqual(globalThis.getActiveSeriesGroupName(), 'SingleShow', '1-season group must start workflow immediately');
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), ['SingleShow.S01E01.mkv', 'SingleShow.S01E02.mkv']);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true, 'view-folder must be active after 1-season banner click');
    assert.strictEqual(searchCalls, 1, '1-season banner click must trigger /api/search');
});

// --------------------------------------------------------------------------
// E1-AK7: Gemeinsame Sperre an allen vier Startstellen
// --------------------------------------------------------------------------
test('E1-AK7: Gemeinsame Sperre weist Zweitstarts von allen vier Startstellen (Banner-Apply, Alle-Knopf, Staffel-Knopf, Bulk-Leiste) still ab', async () => {
    const env = setupTestEnvironment();
    await new Promise(r => setImmediate(r));

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions(),
        { project: 'LooseEp.S01E01.mkv', suggested_query: 'LooseEp', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    let searchCalls = 0;
    let pendingResolvers = [];
    globalThis.fetch = (url) => {
        if (String(url).includes('/api/search')) {
            searchCalls++;
            return new Promise(resolve => {
                pendingResolvers.push(() => resolve({ ok: true, json: async () => [] }));
            });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
    };

    function resetBoard() {
        globalThis.appliedInboxGroups.clear();
        globalThis.appliedInboxGroups.add('MultiShow'); // MultiShow in list (has All-button + Season-buttons), SingleShow open in banner
        globalThis.selectedInboxProjects.clear();
        globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv'); // Bulk bar active
        globalThis.renderSmartInboxList(suggestions, new Set());
        searchCalls = 0;
        pendingResolvers = [];
        env.consoleErrors.length = 0;
        env.alerts.length = 0;
    }

    function getControls() {
        const multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
        const allBtn = multiRow.querySelector('.btn-select-group');
        const seasonsDiv = multiRow.querySelector('.smart-inbox-group-seasons');
        const seasonBtns = seasonsDiv ? seasonsDiv.querySelectorAll('button') : [];
        const bannerApplyBtn = env.groupBanner.querySelector('.btn-banner-apply-group');
        const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
        return {
            season1Btn: seasonBtns[0] || null,
            season2Btn: seasonBtns[1] || null,
            allBtn,
            bannerApplyBtn,
            bulkBtn
        };
    }

    // Start order begins with allBtn so even without seasonsDiv it directly tests the shared lock against baseline
    const starters = ['allBtn', 'bulkBtn', 'bannerApplyBtn', 'season1Btn'];

    for (const starterKey of starters) {
        resetBoard();
        const ctrls = getControls();
        const firstBtn = ctrls[starterKey];
        assert.ok(firstBtn, `Starter button ${starterKey} must exist`);

        const firstPromise = firstBtn.click();
        assert.strictEqual(searchCalls, 1, `${starterKey} must have started exactly 1 search request`);

        const activeCtrls = getControls();
        const candidates = [
            { key: 'bulkBtn', btn: activeCtrls.bulkBtn, expectedText: 'Ausgewählte als Serie verarbeiten' },
            { key: 'allBtn', btn: activeCtrls.allBtn, expectedText: 'Alle verarbeiten' },
            { key: 'season2Btn', btn: activeCtrls.season2Btn, expectedText: 'Staffel 2 (1)' }
        ];
        if (starterKey !== 'bannerApplyBtn') {
            candidates.push({ key: 'bannerApplyBtn', btn: activeCtrls.bannerApplyBtn, expectedText: 'Als Serie gruppieren' });
        } else {
            candidates.push({ key: 'season1Btn', btn: activeCtrls.season1Btn, expectedText: 'Staffel 1 (3)' });
        }

        for (const cand of candidates) {
            if (cand.key === starterKey) continue;
            assert.ok(cand.btn, `Candidate button ${cand.key} must exist`);
            const clickPromise = cand.btn.click();
            if (searchCalls !== 1 || cand.btn.disabled !== false || cand.btn.textContent !== cand.expectedText) {
                while (pendingResolvers.length > 0) pendingResolvers.shift()();
                await clickPromise;
                await firstPromise;
            }
            assert.strictEqual(searchCalls, 1, `Second start via ${cand.key} while ${starterKey} is running must be rejected (no second fetch)`);
            assert.strictEqual(cand.btn.disabled, false, `Rejected button ${cand.key} must not become disabled`);
            assert.strictEqual(cand.btn.textContent, cand.expectedText, `Rejected button ${cand.key} must not change text to "wird gestartet…"`);
            await clickPromise;
        }

        assert.strictEqual(env.consoleErrors.length, 0, 'No console.error on silent lock rejection');
        assert.strictEqual(env.alerts.length, 0, 'No alert on silent lock rejection');
        assert.strictEqual(env.groupBanner.querySelector('.smart-inbox-group-banner-error'), null, 'No banner error on silent lock rejection');

        assert.strictEqual(pendingResolvers.length, 1);
        pendingResolvers.shift()();
        await firstPromise;
    }
});

// --------------------------------------------------------------------------
// E1-AK8: Freigabe in finally auch bei Erfolg
// --------------------------------------------------------------------------
test('E1-AK8: Nach erfolgreichem Abschluss des ersten Starts ist die Sperre frei (weiterer Start läuft) und Staffel-/Alle-Knöpfe sind nach Neuaufbau wieder aktiv', async () => {
    const env = setupTestEnvironment();

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions(),
        { project: 'LooseEp.S01E01.mkv', suggested_query: 'LooseEp', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    let searchCalls = 0;
    let pendingResolvers = [];
    globalThis.fetch = (url) => {
        if (String(url).includes('/api/search')) {
            searchCalls++;
            return new Promise(resolve => {
                pendingResolvers.push(() => resolve({ ok: true, json: async () => [] }));
            });
        }
        return Promise.resolve({ ok: true, json: async () => [] });
    };

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    const multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const seasonsDiv = multiRow.querySelector('.smart-inbox-group-seasons');
    assert.ok(seasonsDiv, 'Seasons bar must exist');
    const season1Btn = seasonsDiv.querySelectorAll('button')[0];
    const allBtn = multiRow.querySelector('.btn-select-group');
    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');

    // 1. Start via Season 1 button, then resolve pending fetch
    const firstPromise = season1Btn.click();
    assert.strictEqual(searchCalls, 1);
    assert.strictEqual(pendingResolvers.length, 1);
    pendingResolvers.shift()();
    await firstPromise;

    // 2. Lock is free -> start via All button runs
    const secondPromise = allBtn.click();
    assert.strictEqual(searchCalls, 2, 'All-button start must run after Season 1 start finished');
    assert.strictEqual(pendingResolvers.length, 1);
    pendingResolvers.shift()();
    await secondPromise;

    // 3. Lock is free -> start via Bulk button runs
    const thirdPromise = bulkBtn.click();
    assert.strictEqual(searchCalls, 3, 'Bulk start must run after All-button start finished');
    assert.strictEqual(pendingResolvers.length, 1);
    pendingResolvers.shift()();
    await thirdPromise;

    // 4. After re-render (6s poll), Season and All buttons are active again and clickable
    globalThis.renderSmartInboxList(suggestions, new Set());
    const refreshedRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    const refreshedSeasonBtns = refreshedRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button');
    const refreshedAllBtn = refreshedRow.querySelector('.btn-select-group');

    assert.strictEqual(refreshedSeasonBtns[0].disabled, false);
    assert.strictEqual(refreshedSeasonBtns[0].textContent, 'Staffel 1 (3)');
    assert.strictEqual(refreshedAllBtn.disabled, false);
    assert.strictEqual(refreshedAllBtn.textContent, 'Alle verarbeiten');

    const fourthPromise = refreshedSeasonBtns[0].click();
    assert.strictEqual(searchCalls, 4, 'Refreshed Season 1 button must start workflow');
    pendingResolvers.shift()();
    await fourthPromise;
});

// --------------------------------------------------------------------------
// E2-AK1: Fehler aus dem Alle-Knopf
// --------------------------------------------------------------------------
test('E2-AK1: Erzwungener Start-Fehler aus dem Alle-Knopf zeigt sichtbare Inline-Meldung in der betroffenen Gruppenzeile, ruft console.error auf, hält Knopf nach Neuaufbau benutzbar und gibt die Sperre frei', async () => {
    const env = setupTestEnvironment();
    const expectedErrorText = 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.';

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions(),
        { project: 'OtherShow.S01E01.mkv', suggested_query: 'OtherShow', media_type: 'tv', is_dir: false, video_count: 1 },
        { project: 'OtherShow.S01E02.mkv', suggested_query: 'OtherShow', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.appliedInboxGroups.add('SingleShow');
    globalThis.appliedInboxGroups.add('OtherShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    shouldThrowInQualityHint = true;

    // 1. Trigger error on MultiShow (with seasons bar) via Alle-Knopf
    const multiRowBefore = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    assert.ok(multiRowBefore);
    const multiAllBtn = multiRowBefore.querySelector('.btn-select-group');
    await multiAllBtn.click();

    const rowsAfterMulti = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    const multiRow = rowsAfterMulti.find(r => r.getAttribute('data-group-key') === 'MultiShow');
    const singleRow = rowsAfterMulti.find(r => r.getAttribute('data-group-key') === 'SingleShow');
    const otherRow = rowsAfterMulti.find(r => r.getAttribute('data-group-key') === 'OtherShow');

    const multiErrorEl = multiRow.querySelector('.smart-inbox-group-banner-error');
    assert.ok(multiErrorEl, 'Inline error div .smart-inbox-group-banner-error must be rendered in MultiShow row');
    assert.strictEqual(multiErrorEl.tagName, 'DIV');
    assert.strictEqual(multiErrorEl.getAttribute('role'), 'alert');
    assert.strictEqual(multiErrorEl.getAttribute('aria-live'), 'polite');
    assert.strictEqual(multiErrorEl.textContent, expectedErrorText);

    // Placement in multi-season row: after seasonsDiv, before membersDiv
    const mHeaderIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-header'));
    const mSeasonsIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-seasons'));
    const mErrorIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-banner-error'));
    const mMembersIdx = multiRow.__children.findIndex(c => c.classList.contains('smart-inbox-group-members'));
    assert.ok(mHeaderIdx >= 0 && mSeasonsIdx > mHeaderIdx && mErrorIdx > mSeasonsIdx && mMembersIdx > mErrorIdx, 'In multi-season group row, error must be placed after seasonsDiv and before membersDiv');

    // Other group rows must NOT show an error
    assert.strictEqual(singleRow.querySelector('.smart-inbox-group-banner-error'), null, 'Unrelated SingleShow row must not show error yet');
    assert.strictEqual(otherRow.querySelector('.smart-inbox-group-banner-error'), null, 'Unrelated OtherShow row must not show error');

    // console.error must be called with cause
    assert.ok(env.consoleErrors.length >= 1, 'console.error must be called');
    assert.ok(
        env.consoleErrors.some(msg => msg.includes('Injected workflow start failure')),
        `console.error must include failure cause, got: ${JSON.stringify(env.consoleErrors)}`
    );

    // 2. Trigger error on SingleShow (without seasons bar) via Alle-Knopf: placement directly after headerDiv
    env.consoleErrors.length = 0;
    const singleAllBtn = singleRow.querySelector('.btn-select-group');
    await singleAllBtn.click();

    const rowsAfterSingle = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    const singleRowAfter = rowsAfterSingle.find(r => r.getAttribute('data-group-key') === 'SingleShow');
    const otherRowAfter = rowsAfterSingle.find(r => r.getAttribute('data-group-key') === 'OtherShow');
    const singleErrorEl = singleRowAfter.querySelector('.smart-inbox-group-banner-error');
    assert.ok(singleErrorEl, 'Inline error div must be rendered in SingleShow row');
    assert.strictEqual(singleErrorEl.getAttribute('role'), 'alert');
    assert.strictEqual(singleErrorEl.getAttribute('aria-live'), 'polite');
    assert.strictEqual(singleErrorEl.textContent, expectedErrorText);

    const sHeaderIdx = singleRowAfter.__children.findIndex(c => c.classList.contains('smart-inbox-group-header'));
    const sErrorIdx = singleRowAfter.__children.findIndex(c => c.classList.contains('smart-inbox-group-banner-error'));
    const sMembersIdx = singleRowAfter.__children.findIndex(c => c.classList.contains('smart-inbox-group-members'));
    assert.strictEqual(singleRowAfter.querySelector('.smart-inbox-group-seasons'), null);
    assert.ok(sHeaderIdx >= 0 && sErrorIdx === sHeaderIdx + 1 && sMembersIdx > sErrorIdx, 'In single-season group row (no seasons bar), error must be placed directly after headerDiv');
    assert.strictEqual(otherRowAfter.querySelector('.smart-inbox-group-banner-error'), null, 'OtherShow row must remain without error');
    assert.ok(env.consoleErrors.length >= 1, 'console.error must be called for SingleShow error');

    // 3. Button usable after rebuild & lock is free (subsequent successful start runs)
    globalThis.renderSmartInboxList(suggestions, new Set());
    const rebuiltMultiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    const rebuiltAllBtn = rebuiltMultiRow.querySelector('.btn-select-group');
    assert.strictEqual(rebuiltAllBtn.disabled, false, 'Alle-Knopf must be enabled after rebuild');
    assert.strictEqual(rebuiltAllBtn.textContent, 'Alle verarbeiten');

    shouldThrowInQualityHint = false;
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');

    await rebuiltAllBtn.click();
    assert.strictEqual(globalThis.getActiveSeriesGroupName(), 'MultiShow', 'Second start must run because lock is free');
    assert.strictEqual(globalThis.getActiveSeriesGroupFiles().length, 7);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true);
});

// --------------------------------------------------------------------------
// E2-AK2: Fehler aus dem Staffel-Knopf
// --------------------------------------------------------------------------
test('E2-AK2: Erzwungener Start-Fehler aus einem Staffel-Knopf zeigt Meldung in derselben Gruppenzeile, ruft console.error auf, gibt Sperre frei und lässt appliedInboxGroups unverändert', async () => {
    const env = setupTestEnvironment();
    const expectedErrorText = 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.';

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions()
    ];

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.appliedInboxGroups.add('SingleShow');
    globalThis.renderSmartInboxList(suggestions, new Set());

    shouldThrowInQualityHint = true;

    const multiRowBefore = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    const season11Btn = multiRowBefore.querySelector('.smart-inbox-group-seasons').querySelectorAll('button').find(b => b.textContent === 'Staffel 11 (3)');
    assert.ok(season11Btn);

    await season11Btn.click();

    // appliedInboxGroups must remain UNCHANGED (no rollback like in banner)
    assert.strictEqual(globalThis.appliedInboxGroups.has('MultiShow'), true, 'MultiShow must remain in appliedInboxGroups after season button failure');
    assert.strictEqual(globalThis.appliedInboxGroups.has('SingleShow'), true, 'SingleShow must remain in appliedInboxGroups');
    assert.strictEqual(globalThis.appliedInboxGroups.size, 2);

    const rowsAfter = env.smartInboxList.querySelectorAll('.smart-inbox-group-row');
    const multiRow = rowsAfter.find(r => r.getAttribute('data-group-key') === 'MultiShow');
    const singleRow = rowsAfter.find(r => r.getAttribute('data-group-key') === 'SingleShow');
    assert.ok(multiRow, 'MultiShow group row must still be rendered in list');

    const errorEl = multiRow.querySelector('.smart-inbox-group-banner-error');
    assert.ok(errorEl, 'Inline error must appear in MultiShow group row');
    assert.strictEqual(errorEl.getAttribute('role'), 'alert');
    assert.strictEqual(errorEl.getAttribute('aria-live'), 'polite');
    assert.strictEqual(errorEl.textContent, expectedErrorText);
    assert.strictEqual(singleRow.querySelector('.smart-inbox-group-banner-error'), null, 'SingleShow row must not have error');

    // console.error called
    assert.ok(env.consoleErrors.length >= 1, 'console.error must be called');
    assert.ok(env.consoleErrors.some(msg => msg.includes('Injected workflow start failure')));

    // Season button restored and usable, lock is free
    const retrySeason11Btn = multiRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button').find(b => b.textContent === 'Staffel 11 (3)');
    assert.ok(retrySeason11Btn);
    assert.strictEqual(retrySeason11Btn.disabled, false);

    shouldThrowInQualityHint = false;
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.setActiveSeriesGroupName('');

    await retrySeason11Btn.click();
    assert.strictEqual(globalThis.getActiveSeriesGroupName(), 'MultiShow');
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), [
        'MultiShow.S11E01.mkv',
        'MultiShow.S11E02.Folder/episode2.mkv',
        'MultiShow.S11E03.mkv'
    ]);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true);
});

// --------------------------------------------------------------------------
// E2-AK3: Fehler aus der Bulk-Leiste
// --------------------------------------------------------------------------
test('E2-AK3: Erzwungener Start-Fehler aus der Bulk-Leiste zeigt Inline-Meldung (width: 100% zwischen Info und Buttons, kein alert()), ruft console.error auf, hält Knopf benutzbar und gibt Sperre frei', async () => {
    const env = setupTestEnvironment();
    const expectedErrorText = 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.';

    const suggestions = makeMultiSeasonSuggestions();
    globalThis.selectedInboxProjects.add('MultiShow.S01E01.mkv');
    globalThis.selectedInboxProjects.add('MultiShow.S01E02.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    shouldThrowInQualityHint = true;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(bulkBtn);
    await bulkBtn.click();

    // No alert()
    assert.strictEqual(env.alerts.length, 0, 'Start error in bulk bar must NOT call alert()');

    // Inline error in bulkBar between .smart-inbox-bulk-info and .smart-inbox-bulk-buttons with width: 100%
    const errorEl = env.bulkBar.querySelector('.smart-inbox-group-banner-error');
    assert.ok(errorEl, 'Bulk bar must contain .smart-inbox-group-banner-error');
    assert.strictEqual(errorEl.tagName, 'DIV');
    assert.strictEqual(errorEl.getAttribute('role'), 'alert');
    assert.strictEqual(errorEl.getAttribute('aria-live'), 'polite');
    assert.strictEqual(errorEl.textContent, expectedErrorText);
    assert.ok(errorEl.style.cssText.includes('width: 100%'), `Error element must have width: 100%, got: "${errorEl.style.cssText}"`);

    const infoIdx = env.bulkBar.__children.findIndex(c => c.classList.contains('smart-inbox-bulk-info'));
    const errIdx = env.bulkBar.__children.findIndex(c => c.classList.contains('smart-inbox-group-banner-error'));
    const btnsIdx = env.bulkBar.__children.findIndex(c => c.classList.contains('smart-inbox-bulk-buttons'));
    assert.ok(infoIdx >= 0 && errIdx > infoIdx && btnsIdx > errIdx, 'Bulk error div must be placed between .smart-inbox-bulk-info and .smart-inbox-bulk-buttons');

    // console.error called
    assert.ok(env.consoleErrors.length >= 1, 'console.error must be called');
    assert.ok(env.consoleErrors.some(msg => msg.includes('Injected workflow start failure')));

    // Button enabled and usable again, lock free
    const retryBulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    assert.ok(retryBulkBtn);
    assert.strictEqual(retryBulkBtn.disabled, false);
    assert.strictEqual(retryBulkBtn.textContent, 'Ausgewählte als Serie verarbeiten');

    shouldThrowInQualityHint = false;
    env.viewEmpty.className = 'view-panel active';
    env.viewFolder.className = 'view-panel hidden';
    globalThis.setActiveSeriesGroupFiles(null);

    await retryBulkBtn.click();
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), ['MultiShow.S01E01.mkv', 'MultiShow.S01E02.mkv']);
    assert.strictEqual(env.viewFolder.classList.contains('active'), true);
});

// --------------------------------------------------------------------------
// E2-AK4: Meldung überlebt den 6-s-Neuaufbau
// --------------------------------------------------------------------------
test('E2-AK4: Fehlermeldungen in Gruppenzeile (Alle-Knopf / Staffel-Knopf) und Bulk-Leiste überleben erneutes renderSmartInboxList und updateBulkActionsBarUI', async () => {
    const env = setupTestEnvironment();
    const expectedErrorText = 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.';

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions(),
        { project: 'LooseEp.S01E01.mkv', suggested_query: 'LooseEp', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.appliedInboxGroups.add('SingleShow');
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    shouldThrowInQualityHint = true;

    // 1. Trigger error via Staffel-Knopf on MultiShow
    let multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    const season1Btn = multiRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button')[0];
    await season1Btn.click();

    // 2. Trigger error via Alle-Knopf on SingleShow
    let singleRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow');
    const singleAllBtn = singleRow.querySelector('.btn-select-group');
    await singleAllBtn.click();

    // 3. Trigger error via Bulk-Leiste
    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    await bulkBtn.click();

    const multiErrBefore = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow').querySelector('.smart-inbox-group-banner-error');
    const singleErrBefore = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow').querySelector('.smart-inbox-group-banner-error');
    const bulkErrBefore = env.bulkBar.querySelector('.smart-inbox-group-banner-error');
    assert.ok(multiErrBefore && singleErrBefore && bulkErrBefore);

    // Simulate 6s poll rebuild via renderSmartInboxList
    globalThis.renderSmartInboxList(suggestions, new Set());

    multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    singleRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow');
    const multiErrAfter = multiRow.querySelector('.smart-inbox-group-banner-error');
    const singleErrAfter = singleRow.querySelector('.smart-inbox-group-banner-error');
    assert.ok(multiErrAfter, 'MultiShow error must survive renderSmartInboxList');
    assert.notStrictEqual(multiErrAfter, multiErrBefore, 'Must be freshly rendered from module state');
    assert.strictEqual(multiErrAfter.textContent, expectedErrorText);
    assert.strictEqual(multiErrAfter.getAttribute('role'), 'alert');
    assert.strictEqual(multiErrAfter.getAttribute('aria-live'), 'polite');

    assert.ok(singleErrAfter, 'SingleShow error must survive renderSmartInboxList');
    assert.notStrictEqual(singleErrAfter, singleErrBefore, 'Must be freshly rendered from module state');
    assert.strictEqual(singleErrAfter.textContent, expectedErrorText);

    // Simulate standalone updateBulkActionsBarUI rebuild (full innerHTML replacement)
    globalThis.updateBulkActionsBarUI();
    const bulkErrAfter = env.bulkBar.querySelector('.smart-inbox-group-banner-error');
    assert.ok(bulkErrAfter, 'Bulk error must survive updateBulkActionsBarUI');
    assert.notStrictEqual(bulkErrAfter, bulkErrBefore, 'Bulk error must be freshly rendered from module state');
    assert.strictEqual(bulkErrAfter.textContent, expectedErrorText);
    assert.strictEqual(bulkErrAfter.getAttribute('role'), 'alert');
    assert.strictEqual(bulkErrAfter.getAttribute('aria-live'), 'polite');
    assert.ok(bulkErrAfter.style.cssText.includes('width: 100%'));
});

// --------------------------------------------------------------------------
// E2-AK5: Leeren beim nächsten Erfolg und bei "Auswahl aufheben" / Verschwinden der Leiste
// --------------------------------------------------------------------------
test('E2-AK5: Erfolgreicher Start derselben Stelle löscht die Fehlermeldung (jeder Startknopf derselben Gruppenzeile bzw. nächste erfolgreiche Bulk-Verarbeitung); "Auswahl aufheben" und Verschwinden der Leiste löschen die Bulk-Meldung', async () => {
    const env = setupTestEnvironment();

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions(),
        { project: 'LooseEp.S01E01.mkv', suggested_query: 'LooseEp', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.appliedInboxGroups.add('SingleShow');
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    // 1. Error on MultiShow via Alle-Knopf -> cleared by successful Staffel-Knopf click on MultiShow
    shouldThrowInQualityHint = true;
    let multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    await multiRow.querySelector('.btn-select-group').click();
    multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    assert.ok(multiRow.querySelector('.smart-inbox-group-banner-error'), 'MultiShow must show error after failed Alle-Knopf click');

    shouldThrowInQualityHint = false;
    const season1Btn = multiRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button')[0];
    await season1Btn.click();
    multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    assert.strictEqual(multiRow.querySelector('.smart-inbox-group-banner-error'), null, 'Successful Season 1 start on same group must clear group error');
    globalThis.renderSmartInboxList(suggestions, new Set());
    multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    assert.strictEqual(multiRow.querySelector('.smart-inbox-group-banner-error'), null, 'Group error must stay cleared after re-render');

    // 2. Error on MultiShow via Staffel-Knopf -> cleared by successful Alle-Knopf click on MultiShow (while SingleShow error stays until SingleShow succeeds)
    shouldThrowInQualityHint = true;
    await multiRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button')[1].click();
    let singleRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow');
    await singleRow.querySelector('.btn-select-group').click();

    multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    singleRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow');
    assert.ok(multiRow.querySelector('.smart-inbox-group-banner-error'));
    assert.ok(singleRow.querySelector('.smart-inbox-group-banner-error'));

    shouldThrowInQualityHint = false;
    await multiRow.querySelector('.btn-select-group').click();
    multiRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'MultiShow');
    singleRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow');
    assert.strictEqual(multiRow.querySelector('.smart-inbox-group-banner-error'), null, 'Successful Alle-Knopf start on MultiShow must clear MultiShow error');
    assert.ok(singleRow.querySelector('.smart-inbox-group-banner-error'), 'SingleShow error must remain until SingleShow succeeds');

    await singleRow.querySelector('.btn-select-group').click();
    singleRow = env.smartInboxList.querySelectorAll('.smart-inbox-group-row').find(r => r.getAttribute('data-group-key') === 'SingleShow');
    assert.strictEqual(singleRow.querySelector('.smart-inbox-group-banner-error'), null, 'Successful start on SingleShow clears SingleShow error');

    // 3. Bulk error -> cleared by next successful Bulk start
    shouldThrowInQualityHint = true;
    await env.bulkBar.querySelector('#btn-bulk-group-series').click();
    assert.ok(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), 'Bulk error must be shown after failed bulk start');

    shouldThrowInQualityHint = false;
    await env.bulkBar.querySelector('#btn-bulk-group-series').click();
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null, 'Successful bulk start must clear bulk error');
    globalThis.updateBulkActionsBarUI();
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null, 'Bulk error must remain cleared after updateBulkActionsBarUI');

    // 4. Bulk error -> cleared by "Auswahl aufheben" (#btn-bulk-deselect)
    shouldThrowInQualityHint = true;
    await env.bulkBar.querySelector('#btn-bulk-group-series').click();
    assert.ok(env.bulkBar.querySelector('.smart-inbox-group-banner-error'));

    const deselectBtn = env.bulkBar.querySelector('#btn-bulk-deselect');
    assert.ok(deselectBtn);
    await deselectBtn.click();
    assert.strictEqual(globalThis.selectedInboxProjects.size, 0);
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null);

    // Re-selecting an item must NOT bring back the old bulk error
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.updateBulkActionsBarUI();
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null, 'Bulk error must not reappear when selecting again after deselect');

    // 5. Bulk error -> cleared when bulk bar disappears (count === 0)
    await env.bulkBar.querySelector('#btn-bulk-group-series').click();
    assert.ok(env.bulkBar.querySelector('.smart-inbox-group-banner-error'));
    globalThis.selectedInboxProjects.clear();
    globalThis.updateBulkActionsBarUI();
    assert.strictEqual(env.bulkBar.style.display, 'none');
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.updateBulkActionsBarUI();
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null, 'Bulk error must be cleared when bar disappears at count 0');
});

// --------------------------------------------------------------------------
// E2-AK6: Bulk-Auswahl bleibt nach einem Start-Fehler unverändert gesetzt
// --------------------------------------------------------------------------
test('E2-AK6: selectedInboxProjects, Zähler und Checkboxen bleiben nach einem Start-Fehler aus der Bulk-Leiste unverändert gesetzt, während die Inline-Fehlermeldung angezeigt wird', async () => {
    const env = setupTestEnvironment();

    const suggestions = makeMultiSeasonSuggestions();
    globalThis.selectedInboxProjects.add('MultiShow.S01E01.mkv');
    globalThis.selectedInboxProjects.add('MultiShow.S01E02.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    shouldThrowInQualityHint = true;

    const bulkBtn = env.bulkBar.querySelector('#btn-bulk-group-series');
    await bulkBtn.click();

    // Error message is rendered inline in bulkBar
    const errorEl = env.bulkBar.querySelector('.smart-inbox-group-banner-error');
    assert.ok(errorEl, 'Bulk error message must be rendered inline');
    assert.strictEqual(errorEl.textContent, 'Serien-Start fehlgeschlagen. Bitte erneut versuchen.');

    // Selection remains intact
    assert.deepStrictEqual(
        Array.from(globalThis.selectedInboxProjects),
        ['MultiShow.S01E01.mkv', 'MultiShow.S01E02.mkv'],
        'selectedInboxProjects must remain unchanged after bulk start error'
    );
    const countEl = env.bulkBar.querySelector('#smart-inbox-bulk-count');
    assert.ok(countEl);
    assert.strictEqual(countEl.textContent, '2 ausgewählt');

    const checkedCbs = env.smartInboxList.querySelectorAll('.smart-inbox-cb:checked');
    assert.strictEqual(checkedCbs.length, 2, 'Both checkboxes in list must remain checked');
});

// --------------------------------------------------------------------------
// E2-AK7: Bestand unverändert (alert()-Pfade im Bulk-Handler + appliedInboxGroups-Invariante)
// --------------------------------------------------------------------------
test('E2-AK7: Bestehende alert()-Pfade im Bulk-Handler bleiben unverändert und Staffel-/Alle-/Bulk-Fehlerpfade ändern appliedInboxGroups niemals', async () => {
    const env = setupTestEnvironment();

    const suggestions = [
        ...makeMultiSeasonSuggestions(),
        ...makeSingleSeasonSuggestions(),
        { project: 'LooseEp.S01E01.mkv', suggested_query: 'LooseEp', media_type: 'tv', is_dir: false, video_count: 1 }
    ];

    // MultiShow is applied; SingleShow is NOT applied
    globalThis.appliedInboxGroups.add('MultiShow');
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.renderSmartInboxList(suggestions, new Set());

    shouldThrowInQualityHint = true;

    // 1. Staffel-Knopf error -> appliedInboxGroups unchanged, error shown
    let multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    await multiRow.querySelector('.smart-inbox-group-seasons').querySelectorAll('button')[0].click();
    assert.deepStrictEqual(Array.from(globalThis.appliedInboxGroups), ['MultiShow']);
    multiRow = env.smartInboxList.querySelector('.smart-inbox-group-row');
    assert.ok(multiRow.querySelector('.smart-inbox-group-banner-error'), 'Staffel error must render inline error');

    // 2. Alle-Knopf error -> appliedInboxGroups unchanged
    await multiRow.querySelector('.btn-select-group').click();
    assert.deepStrictEqual(Array.from(globalThis.appliedInboxGroups), ['MultiShow']);

    // 3. Bulk-Knopf error -> appliedInboxGroups unchanged, inline error in bulkBar
    await env.bulkBar.querySelector('#btn-bulk-group-series').click();
    assert.deepStrictEqual(Array.from(globalThis.appliedInboxGroups), ['MultiShow']);
    assert.ok(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), 'Bulk error must render inline error');

    // 4. Existing alert() path: partial skip (1 missing entry + 1 valid entry)
    shouldThrowInQualityHint = false;
    env.alerts.length = 0;
    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('LooseEp.S01E01.mkv');
    globalThis.selectedInboxProjects.add('Vanished.S01E01.mkv');
    globalThis.updateBulkActionsBarUI();

    await env.bulkBar.querySelector('#btn-bulk-group-series').click();
    assert.strictEqual(env.alerts.length, 1, 'Partial skip must trigger existing alert()');
    assert.strictEqual(env.alerts[0], '1 Eintrag ist nicht mehr in der Inbox und wurde übersprungen.');
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null, 'Successful partial skip start must clear/not show inline start error');
    assert.deepStrictEqual(globalThis.getActiveSeriesGroupFiles(), ['LooseEp.S01E01.mkv']);

    // 5. Existing alert() path: all selected entries missing
    env.alerts.length = 0;
    globalThis.setActiveSeriesGroupFiles(null);
    globalThis.selectedInboxProjects.clear();
    globalThis.selectedInboxProjects.add('Vanished1.S01E01.mkv');
    globalThis.selectedInboxProjects.add('Vanished2.S01E02.mkv');
    globalThis.updateBulkActionsBarUI();

    const bulkBtnEmpty = env.bulkBar.querySelector('#btn-bulk-group-series');
    await bulkBtnEmpty.click();
    await new Promise(r => queueMicrotask(r));
    assert.strictEqual(env.alerts.length, 1, 'All-missing selection must trigger existing alert()');
    assert.strictEqual(env.alerts[0], 'Keine der ausgewählten Dateien ist noch in der Inbox – nichts gestartet.');
    assert.strictEqual(globalThis.getActiveSeriesGroupFiles(), null);
    assert.strictEqual(bulkBtnEmpty.disabled, false);
    assert.strictEqual(env.bulkBar.querySelector('.smart-inbox-group-banner-error'), null);
});
