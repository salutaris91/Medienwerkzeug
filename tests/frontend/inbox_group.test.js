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
            el.setAttribute(`data-${dMatch[1]}`, dMatch[2]);
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

    const el = {
        tagName: tagName.toUpperCase(),
        id: attributes.id || '',
        value: '',
        checked: false,
        disabled: false,
        textContent: '',
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
            children.length = 0;
            if (val) {
                const parsed = parseHtmlToMockElements(val);
                parsed.forEach(c => children.push(c));
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
        click: () => {
            if (listeners['click']) {
                listeners['click'].forEach(h => h.call(el, { type: 'click', target: el, preventDefault: () => {} }));
            }
            if (typeof el.onclick === 'function') {
                el.onclick.call(el, { type: 'click', target: el, preventDefault: () => {} });
            }
        },
        dispatchEvent: (event) => {
            const handlers = listeners[event.type] || [];
            handlers.forEach(h => h.call(el, event));
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

    globalThis.document = {
        cookie: '',
        documentElement: {
            style: {
                setProperty: () => {},
                removeProperty: () => {}
            }
        },
        getElementById: (id) => getOrCreateElement(id),
        createElement: (tag) => createMockElement(tag),
        querySelectorAll: (sel) => {
            const parts = splitSelectorParts(sel);
            if (parts.length > 0 && parts[0] === '#smart-inbox-list') {
                return findDescendants(smartInboxList, parts.slice(1));
            }
            return [];
        },
        querySelector: (sel) => {
            if (sel.startsWith('#')) return getOrCreateElement(sel.slice(1));
            return null;
        },
        addEventListener: () => {}
    };

    globalThis.window = {
        fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
        scrollTo: () => {},
        addEventListener: () => {}
    };
    globalThis.fetch = globalThis.window.fetch;

    const appJsContent = fs.readFileSync(appJsPath, 'utf8');
    let cleanAppJs = appJsContent.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, "");
    cleanAppJs = `
const cleanSeriesName = globalThis.cleanSeriesName;
` + cleanAppJs;

    cleanAppJs += `
globalThis.extractStrictSeasonEpisode = extractStrictSeasonEpisode;
globalThis.detectInboxGroups = detectInboxGroups;
globalThis.buildGroupedInboxSuggestions = buildGroupedInboxSuggestions;
globalThis.updateGroupBannerUI = updateGroupBannerUI;
globalThis.updateBulkActionsBarUI = updateBulkActionsBarUI;
globalThis.startSeriesGroupWorkflow = startSeriesGroupWorkflow;
globalThis.createSeriesGroupPayload = createSeriesGroupPayload;
globalThis.selectedInboxProjects = selectedInboxProjects;
globalThis.unlockedMovieProjects = unlockedMovieProjects;
globalThis.appliedInboxGroups = appliedInboxGroups;
globalThis.activeSeriesGroupFiles = activeSeriesGroupFiles;
globalThis.renderSmartInboxList = renderSmartInboxList;
globalThis.sortInboxSuggestions = sortInboxSuggestions;
globalThis.getInboxSortState = getInboxSortState;
globalThis.setInboxSortState = setInboxSortState;
`;

    eval(cleanAppJs);

    return {
        cardSmartInbox,
        smartInboxList,
        groupBanner,
        sortBar,
        bulkBar,
        modeSeries,
        modeMovie,
        seriesSearchQuery,
        deletedProjects
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

test('AK3 & AK13: Film entries show lock notice and "Trotzdem als Serie freigeben" link', () => {
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
    assert.ok(unlockLink, 'Must provide "Trotzdem als Serie freigeben" link');
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
// AK4: Workflow Handover & Key-Contract V1
// --------------------------------------------------------------------------
test('AK4: Both handover paths transition to series mode and create basePayload with matching files and mappings', () => {
    const env = setupTestEnvironment();
    const files = ['Show.S01E01.mkv', 'Show.S01E02.mkv'];

    globalThis.startSeriesGroupWorkflow('Show', files);
    assert.strictEqual(env.seriesSearchQuery.value, 'Show', 'Search input must be prefilled with group name');
    assert.deepStrictEqual(globalThis.activeSeriesGroupFiles, files);

    const payload = globalThis.createSeriesGroupPayload('Show', files);
    assert.strictEqual(payload.media_type, 'tv');
    assert.deepStrictEqual(payload.files, files);
    assert.deepStrictEqual(Object.keys(payload.mappings), files, 'Mappings keys must match files strings exactly (Contract V1)');
    assert.strictEqual(payload.mappings['Show.S01E01.mkv'], 'S01E01');
    assert.strictEqual(payload.mappings['Show.S01E02.mkv'], 'S01E02');
});
