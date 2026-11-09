import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { renderPreviewData, collectPreviewSelection } from '../../gui/static/js/preview_render.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
const indexHtmlPath = path.resolve(__dirname, '../../gui/static/index.html');

function decodeHtmlEntities(str) {
    if (!str) return '';
    return String(str)
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
}

function matchesSelector(el, sel) {
    if (!sel || !el) return false;
    sel = sel.trim();
    if (sel.includes(':checked')) {
        const baseSel = sel.replace(':checked', '').trim();
        return (!baseSel || matchesSelector(el, baseSel)) && Boolean(el.checked);
    }
    if (sel.startsWith('#')) return el.id === sel.slice(1);
    if (sel.startsWith('.')) return el.classList && el.classList.contains(sel.slice(1));
    return Boolean(el.tagName && el.tagName.toLowerCase() === sel.toLowerCase());
}

function findDescendants(node, parts) {
    if (!parts || parts.length === 0) return [];
    const [firstPart, ...remaining] = parts;
    const matches = [];
    function walk(curr) {
        if (!curr || !curr.__children) return;
        for (const child of curr.__children) {
            if (matchesSelector(child, firstPart)) {
                if (remaining.length === 0) matches.push(child);
                else matches.push(...findDescendants(child, remaining));
            }
            walk(child);
        }
    }
    walk(node);
    return matches;
}

const VOID_TAGS = new Set(['img', 'input', 'br', 'hr', 'source', 'meta', 'link', 'path', 'circle', 'line', 'polygon']);

function parseHtmlIntoElement(rootEl, html) {
    rootEl.__children.length = 0;
    rootEl.__textParts = [];
    if (!html) return;

    const stack = [rootEl];
    const tokenRegex = /<(\/?)([a-z0-9\-]+)([^>]*)>|([^<]+)/gi;
    let match;

    while ((match = tokenRegex.exec(html)) !== null) {
        if (match[4] !== undefined) {
            stack[stack.length - 1].__textParts.push(decodeHtmlEntities(match[4]));
            continue;
        }
        const isClosing = match[1] === '/';
        const tagName = match[2].toLowerCase();
        const attrStr = match[3] || '';

        if (isClosing) {
            for (let i = stack.length - 1; i > 0; i--) {
                if (stack[i].tagName.toLowerCase() === tagName) {
                    stack.length = i;
                    break;
                }
            }
            continue;
        }

        const el = createMockElement(tagName);
        const classMatch = attrStr.match(/class=["']([^"']+)["']/i);
        if (classMatch) el.className = classMatch[1];

        const idMatch = attrStr.match(/id=["']([^"']+)["']/i);
        if (idMatch) {
            el.id = idMatch[1];
            if (globalThis.__currentElementsById) globalThis.__currentElementsById[idMatch[1]] = el;
        }

        const dataRegex = /data-([a-z0-9\-]+)=["']([^"']*)["']/gi;
        let dMatch;
        while ((dMatch = dataRegex.exec(attrStr)) !== null) {
            el.setAttribute(`data-${dMatch[1]}`, decodeHtmlEntities(dMatch[2]));
        }

        if (/\bchecked\b/i.test(attrStr)) el.checked = true;
        if (/\bdisabled\b/i.test(attrStr)) el.disabled = true;
        if (/\bopen\b/i.test(attrStr)) el.setAttribute('open', '');

        stack[stack.length - 1].appendChild(el);
        if (!VOID_TAGS.has(tagName) && !/\/\s*$/.test(attrStr)) stack.push(el);
    }
}

function collectTextContent(el) {
    let out = (el.__textParts || []).join('');
    for (const child of el.__children || []) out += collectTextContent(child);
    return out;
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
        __children: children,
        __listeners: listeners,
        __textParts: [],
        dataset,
        parentNode: null,
        style: { display: '' },
        get textContent() { return collectTextContent(el); },
        set textContent(val) {
            const str = String(val ?? '');
            innerHtmlVal = str;
            children.length = 0;
            el.__textParts = [str];
        },
        get innerHTML() { return innerHtmlVal; },
        set innerHTML(val) {
            innerHtmlVal = String(val ?? '');
            parseHtmlIntoElement(el, innerHtmlVal);
        },
        get className() { return Array.from(classSet).join(' '); },
        set className(val) {
            classSet.clear();
            if (val) String(val).split(/\s+/).filter(Boolean).forEach(c => classSet.add(c));
        },
        classList: {
            add: (c) => classSet.add(c),
            remove: (c) => classSet.delete(c),
            contains: (c) => classSet.has(c)
        },
        setAttribute: (name, val) => {
            attrs[name] = String(val);
            if (name.startsWith('data-')) dataset[name.slice(5)] = String(val);
        },
        getAttribute: (name) => (name in attrs ? attrs[name] : null),
        hasAttribute: (name) => name in attrs,
        addEventListener: (event, handler) => {
            if (!listeners[event]) listeners[event] = [];
            listeners[event].push(handler);
        },
        cloneNode: () => createMockElement(tagName, { ...attrs }),
        replaceChild: (newChild, oldChild) => {
            const idx = children.indexOf(oldChild);
            if (idx !== -1) children[idx] = newChild;
            newChild.parentNode = el;
        },
        appendChild: (child) => {
            child.parentNode = el;
            children.push(child);
        },
        click: async function () {
            if (el.disabled) return;
            for (const handler of listeners['click'] || []) {
                await handler.call(el, { type: 'click', target: el, currentTarget: el, preventDefault: () => {} });
            }
        },
        querySelectorAll: (sel) => findDescendants(el, sel.trim().split(/\s+/)),
        querySelector: (sel) => findDescendants(el, sel.trim().split(/\s+/))[0] || null
    };

    if (attributes.class) el.className = attributes.class;
    return el;
}

function setupTestEnvironment() {
    const elementsById = {};
    globalThis.__currentElementsById = elementsById;

    function getOrCreateElement(id, tag = 'div') {
        if (!elementsById[id]) elementsById[id] = createMockElement(tag, { id });
        return elementsById[id];
    }

    const overlay = getOrCreateElement('preview-modal-overlay');
    const modal = getOrCreateElement('preview-modal');
    const warningBox = getOrCreateElement('preview-season-warning');
    const warningText = getOrCreateElement('preview-season-warning-text');
    warningBox.appendChild(warningText);

    const mismatchBox = getOrCreateElement('preview-show-name-mismatch');
    const mismatchText = getOrCreateElement('preview-show-name-mismatch-text');
    const btnAdoptNas = getOrCreateElement('btn-preview-adopt-nas-name', 'button');
    const btnAdoptMeta = getOrCreateElement('btn-preview-adopt-metadata-name', 'button');
    mismatchBox.appendChild(mismatchText);
    mismatchBox.appendChild(btnAdoptNas);
    mismatchBox.appendChild(btnAdoptMeta);

    const similarBox = getOrCreateElement('preview-similar-existing');
    similarBox.className = 'hidden';
    const similarText = getOrCreateElement('preview-similar-existing-text');
    similarBox.appendChild(similarText);

    const dest = getOrCreateElement('preview-destination');
    const listRenames = getOrCreateElement('preview-list-renames');
    const listSubs = getOrCreateElement('preview-list-subs');
    const listJunk = getOrCreateElement('preview-list-junk');
    const executeBtn = getOrCreateElement('btn-preview-execute', 'button');

    [warningBox, mismatchBox, similarBox, dest, listRenames, listSubs, listJunk, executeBtn].forEach(el => modal.appendChild(el));
    overlay.appendChild(modal);

    const docListeners = {};
    globalThis.document = {
        cookie: '',
        documentElement: { scrollTop: 0, style: { setProperty: () => {}, removeProperty: () => {} } },
        body: { scrollTop: 0 },
        getElementById: (id) => getOrCreateElement(id),
        createElement: (tag) => createMockElement(tag),
        querySelectorAll: (sel) => findDescendants(overlay, sel.trim().split(/\s+/)),
        querySelector: (sel) => findDescendants(overlay, sel.trim().split(/\s+/))[0] || null,
        addEventListener: (event, handler) => {
            if (!docListeners[event]) docListeners[event] = [];
            docListeners[event].push(handler);
        },
        dispatchEvent: (eventObj) => {
            for (const handler of docListeners[eventObj.type] || []) {
                try { handler(eventObj); } catch (_) {}
            }
        }
    };

    globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
    globalThis.sessionStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {}, clear: () => {} };
    globalThis.setTimeout = (fn) => { if (typeof fn === 'function') fn(); return 0; };
    globalThis.clearTimeout = () => {};
    globalThis.setInterval = () => 0;
    globalThis.clearInterval = () => {};
    globalThis.alert = () => {};

    globalThis.window = {
        fetch: () => Promise.resolve({ ok: true, json: async () => ({ projects: [], categories: [] }) }),
        scrollTo: () => {},
        addEventListener: () => {}
    };
    globalThis.fetch = globalThis.window.fetch;

    const appJsContent = fs.readFileSync(appJsPath, 'utf8');
    let cleanAppJs = appJsContent.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '');
    cleanAppJs = `
const cleanSeriesName = (n) => n || '';
const formatBytes = () => '0 B';
const prepareSeriesPayload = (s, p) => ({ ...p });
const updateMwDataPanel = () => {};
const triggerQualityHintUpdates = () => {};
const loadConversionRecommendations = () => {};
const applyTheme = () => {};
const setupMaskedInput = () => {};
const setMaskedInputValue = () => {};
const validateAllMaskedFields = () => true;
const osBasename = (p) => String(p || '').replace(/^.*[\\/\\\\]/, '');
const formatFskLabel = (f) => f;
const guessEpisodeNumber = () => 1;
const guessSeasonAndEpisode = () => null;
const cleanFilenameForManualTitle = (f) => f;
const fetchStats = () => Promise.resolve();
const fetchYoutubeSubscriptions = () => Promise.resolve();
const fetchSmartInboxSuggestions = () => Promise.resolve();
` + cleanAppJs + `
globalThis.openPreviewModal = openPreviewModal;
`;

    const origError = console.error;
    console.error = () => {};
    try {
        eval(cleanAppJs);
        globalThis.document.dispatchEvent({ type: 'DOMContentLoaded' });
    } finally {
        console.error = origError;
    }

    return { getOrCreateElement, similarBox, similarText, mismatchBox, mismatchText, executeBtn };
}

test('DOM placement: #preview-similar-existing exists in index.html between mismatch box and destination', () => {
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const mismatchIdx = indexHtml.indexOf('id="preview-show-name-mismatch"');
    const similarIdx = indexHtml.indexOf('id="preview-similar-existing"');
    const destIdx = indexHtml.indexOf('id="preview-destination"');

    assert.ok(mismatchIdx !== -1 && similarIdx !== -1 && destIdx !== -1);
    assert.ok(mismatchIdx < similarIdx && similarIdx < destIdx, '#preview-similar-existing must be placed between mismatch box and destination');
});

test('AK8: Escaping in Stufe 1 and Stufe 2 renders HTML special chars only as text without executing elements', async () => {
    const env = setupTestEnvironment();
    const xssFolder1 = '<img src=x onerror=alert(1)>';
    const xssFolder2 = '<img src=x onerror=alert(2)>';
    const xssPath = 'Action/<script>alert(3)</script>';

    globalThis.fetch = (url) => {
        if (url === '/api/preview_process') {
            return Promise.resolve({
                ok: true,
                json: async () => ({
                    destination: '/nas/Filme/X-Men',
                    renames: [],
                    subs: [],
                    junk: [],
                    similar_existing: {
                        exact: [{ folder: xssFolder1, relative_path: xssPath }],
                        similar: [{ folder: xssFolder2, relative_path: xssFolder2, overlap: '<script>1</script>' }]
                    }
                })
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    await globalThis.openPreviewModal({ media_type: 'movie', project_name: 'X-Men', movie_name: 'X-Men' });

    assert.ok(!env.similarBox.classList.contains('hidden'), 'Similar box must be visible');
    assert.strictEqual(env.similarBox.querySelectorAll('img').length, 0, 'No <img> element may be created in DOM');
    assert.strictEqual(env.similarBox.querySelectorAll('script').length, 0, 'No <script> element may be created in DOM');

    const exactSection = env.getOrCreateElement('preview-similar-exact');
    const fuzzySection = env.getOrCreateElement('preview-similar-fuzzy');
    assert.ok(exactSection.textContent.includes(xssFolder1), 'Stufe 1 textContent must contain raw XSS string');
    assert.ok(exactSection.textContent.includes(xssPath), 'Stufe 1 textContent must contain raw relative_path string');
    assert.ok(fuzzySection.textContent.includes(xssFolder2), 'Stufe 2 textContent must contain raw XSS string');
});

test('AK9: Non-blocking hint keeps btn-preview-execute active and leaves /api/process payload unchanged', async () => {
    const env = setupTestEnvironment();
    let capturedProcessPayload = null;

    globalThis.fetch = (url, options) => {
        if (url === '/api/preview_process') {
            return Promise.resolve({
                ok: true,
                json: async () => ({
                    destination: '/nas/Filme/X-Men (2000)',
                    renames: [{ old: 'xmen.mkv', new: 'X-Men (2000).mkv' }],
                    subs: [],
                    junk: [],
                    similar_existing: {
                        exact: [{ folder: 'X-Men - Der Film', relative_path: 'X-Men - Der Film' }],
                        similar: [{ folder: 'X-Men 2', relative_path: 'X-Men 2', overlap: 2 }]
                    }
                })
            });
        }
        if (url === '/api/process') {
            capturedProcessPayload = JSON.parse(options.body);
            return Promise.resolve({ ok: true, json: async () => ({ status: 'started' }) });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    const basePayload = {
        media_type: 'movie',
        project_name: 'X-Men.2000',
        movie_name: 'X-Men (2000)',
        movie_id: '3409',
        provider: 'tmdb'
    };

    await globalThis.openPreviewModal(basePayload);

    assert.ok(!env.similarBox.classList.contains('hidden'), 'Warning box must be visible when matches exist');
    assert.strictEqual(env.similarBox.querySelectorAll('button').length, 0, 'Warning box must not contain any buttons');
    assert.strictEqual(env.executeBtn.disabled, false, 'btn-preview-execute must remain active');

    await env.executeBtn.click();

    assert.ok(capturedProcessPayload, '/api/process must be called on execute click');
    assert.strictEqual(capturedProcessPayload.media_type, 'movie');
    assert.strictEqual(capturedProcessPayload.project_name, 'X-Men.2000');
    assert.strictEqual(capturedProcessPayload.movie_name, 'X-Men (2000)');
    assert.strictEqual(capturedProcessPayload.movie_id, '3409');
    assert.strictEqual(capturedProcessPayload.provider, 'tmdb');
    assert.deepStrictEqual(capturedProcessPayload.explicit_renames, [{ old: 'xmen.mkv', new: 'X-Men (2000).mkv' }]);
    assert.strictEqual(capturedProcessPayload.similar_existing, undefined, 'similar_existing must not leak into execution payload');
});

test('AK15: UI capping shows first 5 Stufe-2 matches visibly and collapses remaining 2 in <details>; empty lists stay hidden', async () => {
    const env = setupTestEnvironment();
    const sevenSimilar = Array.from({ length: 7 }, (_, idx) => ({
        folder: `X-Men Teil ${idx + 1}`,
        relative_path: `X-Men Teil ${idx + 1}`,
        overlap: 7 - idx
    }));

    globalThis.fetch = (url) => {
        if (url === '/api/preview_process') {
            return Promise.resolve({
                ok: true,
                json: async () => ({
                    destination: '/nas/Filme/X-Men',
                    renames: [],
                    subs: [],
                    junk: [],
                    similar_existing: { exact: [], similar: sevenSimilar }
                })
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    await globalThis.openPreviewModal({ media_type: 'movie', project_name: 'X-Men', movie_name: 'X-Men' });

    const visibleList = env.getOrCreateElement('preview-similar-fuzzy-visible-list');
    const visibleItems = visibleList.querySelectorAll('li');
    assert.strictEqual(visibleItems.length, 5, 'First 5 Stufe-2 matches must be directly visible');
    assert.ok(visibleItems[0].textContent.includes('X-Men Teil 1'));
    assert.ok(visibleItems[4].textContent.includes('X-Men Teil 5'));

    const detailsEl = env.getOrCreateElement('preview-similar-more');
    assert.ok(detailsEl, '<details> element must exist for overflow matches');
    assert.strictEqual(detailsEl.hasAttribute('open'), false, '<details> must be collapsed by default');

    const summaryEl = detailsEl.querySelector('summary');
    assert.ok(summaryEl && summaryEl.textContent.includes('Weitere 2 Treffer anzeigen'), 'Summary must indicate 2 collapsed matches');

    const collapsedItems = detailsEl.querySelectorAll('li');
    assert.strictEqual(collapsedItems.length, 2, 'Remaining 2 matches must be inside collapsed <details>');
    assert.ok(collapsedItems[0].textContent.includes('X-Men Teil 6'));
    assert.ok(collapsedItems[1].textContent.includes('X-Men Teil 7'));

    // Empty lists -> box stays completely hidden
    globalThis.fetch = () => Promise.resolve({
        ok: true,
        json: async () => ({
            destination: '/nas/Filme/Unikat',
            renames: [],
            subs: [],
            junk: [],
            similar_existing: { exact: [], similar: [] }
        })
    });
    await globalThis.openPreviewModal({ media_type: 'movie', project_name: 'Unikat', movie_name: 'Unikat' });
    assert.ok(env.similarBox.classList.contains('hidden'), 'Box must remain hidden when both lists are empty');
});

test('AK16: Stage separation ensures a Stufe-1 folder never appears again in Stufe 2', async () => {
    const env = setupTestEnvironment();

    globalThis.fetch = (url) => {
        if (url === '/api/preview_process') {
            return Promise.resolve({
                ok: true,
                json: async () => ({
                    destination: '/nas/Filme/X-Men (2000)',
                    renames: [],
                    subs: [],
                    junk: [],
                    similar_existing: {
                        exact: [{ folder: 'X-Men - Der Film', relative_path: 'X-Men - Der Film' }],
                        similar: [
                            { folder: 'X-Men - Der Film', relative_path: 'X-Men - Der Film', overlap: 3 },
                            { folder: 'X-Men 2', relative_path: 'X-Men 2', overlap: 2 }
                        ]
                    }
                })
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    await globalThis.openPreviewModal({ media_type: 'movie', project_name: 'X-Men', movie_name: 'X-Men (2000)' });

    const exactSection = env.getOrCreateElement('preview-similar-exact');
    const fuzzySection = env.getOrCreateElement('preview-similar-fuzzy');

    assert.ok(exactSection.textContent.includes('X-Men - Der Film'), 'Stufe 1 must show exact match');
    assert.ok(!fuzzySection.textContent.includes('X-Men - Der Film'), 'Stufe 2 must not repeat Stufe-1 folder');
    assert.ok(fuzzySection.textContent.includes('X-Men 2'), 'Stufe 2 must still show remaining similar folder');
});

test('AK17: Cache-Buster version in index.html and all imports in app.js is >= 105 and consistent', () => {
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const appJs = fs.readFileSync(appJsPath, 'utf8');

    const indexMatch = indexHtml.match(/<script\s+[^>]*src=["']app\.js\?v=([^"']+)["']/);
    assert.ok(indexMatch);
    const version = indexMatch[1];
    assert.ok(Number(version) >= 105, `Expected app.js version >= 105, got ${version}`);

    const importRegex = /import\s+(?:\{[^}]*\}|\*\s+as\s+[^'"]+|[\w$]+)\s+from\s+['"](\.\/js\/[^'"]+)['"]/g;
    const imports = [];
    let match;
    while ((match = importRegex.exec(appJs)) !== null) {
        imports.push(match[1]);
    }
    assert.ok(imports.length >= 9, `Expected at least 9 imports in app.js, got ${imports.length}`);
    for (const imp of imports) {
        assert.ok(imp.endsWith(`?v=${version}`), `Expected ${imp} to end with ?v=${version}`);
    }
});

test('AK18: Existing show_name_mismatch box escapes both nas_name and metadata_name', async () => {
    const env = setupTestEnvironment();
    const maliciousNas = '<img src=x onerror=alert("nas")>';
    const maliciousMeta = '<script>alert("meta")</script>';

    globalThis.fetch = (url) => {
        if (url === '/api/preview_process') {
            return Promise.resolve({
                ok: true,
                json: async () => ({
                    destination: '/nas/Serien/Test',
                    renames: [],
                    subs: [],
                    junk: [],
                    show_name_mismatch: {
                        nas_name: maliciousNas,
                        metadata_name: maliciousMeta
                    }
                })
            });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
    };

    await globalThis.openPreviewModal({ media_type: 'tv', project_name: 'Test', show_name: 'Test' });

    assert.ok(!env.mismatchBox.classList.contains('hidden'), 'Mismatch box must be visible');
    assert.strictEqual(env.mismatchText.querySelectorAll('img').length, 0, 'nas_name must not inject <img>');
    assert.strictEqual(env.mismatchText.querySelectorAll('script').length, 0, 'metadata_name must not inject <script>');
    assert.ok(env.mismatchText.textContent.includes(maliciousNas), 'textContent must contain raw nas_name');
    assert.ok(env.mismatchText.textContent.includes(maliciousMeta), 'textContent must contain raw metadata_name');
});
