import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { createFilmWizard } from '../../gui/static/js/film_wizard.js';
import { renderPreviewData, collectPreviewSelection } from '../../gui/static/js/preview_render.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function decodeEntities(str) {
    if (!str) return '';
    return String(str)
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
}

const VOID_TAGS = new Set(['img', 'input', 'br', 'hr', 'source', 'meta', 'link']);

function createWizardMockDom() {
    const byId = new Map();
    const docListeners = {};

    function registerRecursive(node) {
        if (!node) return;
        if (node.id) byId.set(node.id, node);
        if (Array.isArray(node.children)) {
            node.children.forEach(registerRecursive);
        }
    }

    function matchesSelector(el, sel) {
        if (!sel || !el) return false;
        const s = sel.trim();
        if (s.includes(':checked')) {
            const base = s.replace(':checked', '').trim();
            return (!base || matchesSelector(el, base)) && Boolean(el.checked);
        }
        if (s.startsWith('#')) return el.id === s.slice(1);
        if (s.startsWith('.')) return el.classList && el.classList.contains(s.slice(1));
        return Boolean(el.tagName && el.tagName.toLowerCase() === s.toLowerCase());
    }

    function findDescendants(root, parts) {
        if (!parts || parts.length === 0) return [];
        const [first, ...rest] = parts;
        const matches = [];
        function walk(curr) {
            if (!curr || !Array.isArray(curr.children)) return;
            for (const child of curr.children) {
                if (matchesSelector(child, first)) {
                    if (rest.length === 0) matches.push(child);
                    else matches.push(...findDescendants(child, rest));
                }
                walk(child);
            }
        }
        walk(root);
        return matches;
    }

    function parseHtmlInto(rootEl, html) {
        rootEl.children.length = 0;
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
                    if (stack[i].tagName.toLowerCase() === tagName) {
                        stack.length = i;
                        break;
                    }
                }
                continue;
            }
            const el = makeElement(tagName);
            el.ownerDocument = rootEl.ownerDocument;
            const clsMatch = attrStr.match(/class=["']([^"']+)["']/i);
            if (clsMatch) el.className = clsMatch[1];
            const idMatch = attrStr.match(/id=["']([^"']+)["']/i);
            if (idMatch) el.id = idMatch[1];
            const dataRegex = /data-([a-z0-9\-]+)=["']([^"']*)["']/gi;
            let dMatch;
            while ((dMatch = dataRegex.exec(attrStr)) !== null) {
                el.setAttribute(`data-${dMatch[1]}`, decodeEntities(dMatch[2]));
            }
            if (/\bchecked\b/i.test(attrStr)) el.checked = true;
            if (/\bdisabled\b/i.test(attrStr)) el.disabled = true;
            if (/\bopen\b/i.test(attrStr)) el.setAttribute('open', '');
            stack[stack.length - 1].appendChild(el);
            if (!VOID_TAGS.has(tagName) && !/\/\s*$/.test(attrStr)) {
                stack.push(el);
            }
        }
    }

    function collectText(el) {
        let out = (el._textParts || []).join('');
        for (const ch of el.children || []) out += collectText(ch);
        return out;
    }

    function makeElement(tagName) {
        const classes = new Set();
        const attrs = new Map();
        const listeners = {};
        const dataset = {};
        let idVal = '';
        let classStr = '';
        let innerHtmlVal = '';

        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '',
            value: '',
            checked: false,
            disabled: false,
            placeholder: '',
            rows: 0,
            style: {},
            children: [],
            _textParts: [],
            dataset,
            ownerDocument: null,
            get id() {
                return idVal;
            },
            set id(v) {
                idVal = String(v || '');
                if (idVal) byId.set(idVal, el);
            },
            get textContent() {
                return collectText(el);
            },
            set textContent(v) {
                const str = String(v ?? '');
                innerHtmlVal = str;
                el.children.length = 0;
                el._textParts = [str];
            },
            get className() {
                return Array.from(classes).join(' ');
            },
            set className(v) {
                classStr = String(v || '');
                classes.clear();
                classStr.split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
            },
            classList: {
                add: (...names) => names.forEach((n) => n && classes.add(n)),
                remove: (...names) => names.forEach((n) => classes.delete(n)),
                contains: (n) => classes.has(n),
                toggle: (n, force) => {
                    const add = force !== undefined ? Boolean(force) : !classes.has(n);
                    if (add) classes.add(n);
                    else classes.delete(n);
                    return add;
                },
            },
            setAttribute(k, v) {
                attrs.set(k, String(v));
                if (k === 'id') el.id = String(v);
                if (k.startsWith('data-')) dataset[k.slice(5)] = String(v);
            },
            getAttribute(k) {
                return attrs.has(k) ? attrs.get(k) : null;
            },
            hasAttribute(k) {
                return attrs.has(k);
            },
            removeAttribute(k) {
                attrs.delete(k);
            },
            appendChild(child) {
                el.children.push(child);
                registerRecursive(child);
                return child;
            },
            addEventListener(type, fn) {
                listeners[type] = listeners[type] || [];
                listeners[type].push(fn);
            },
            click() {
                if (el.disabled) return;
                (listeners.click || []).forEach((fn) => fn({ type: 'click', preventDefault() {} }));
            },
            dispatchEvent(evt) {
                (listeners[evt.type] || []).forEach((fn) => fn(evt));
            },
            querySelectorAll(sel) {
                return findDescendants(el, String(sel || '').trim().split(/\s+/));
            },
            querySelector(sel) {
                return el.querySelectorAll(sel)[0] || null;
            },
        };

        Object.defineProperty(el, 'innerHTML', {
            get() {
                return innerHtmlVal;
            },
            set(v) {
                innerHtmlVal = String(v ?? '');
                parseHtmlInto(el, innerHtmlVal);
            },
        });
        return el;
    }

    const doc = {
        cookie: '',
        documentElement: {
            scrollTop: 0,
            style: {
                setProperty() {},
                removeProperty() {},
            },
        },
        body: null,
        createElement(tag) {
            const el = makeElement(tag);
            el.ownerDocument = doc;
            return el;
        },
        getElementById(id) {
            return byId.get(id) || null;
        },
        querySelectorAll(sel) {
            return doc.body ? doc.body.querySelectorAll(sel) : [];
        },
        querySelector(sel) {
            return doc.querySelectorAll(sel)[0] || null;
        },
        addEventListener(type, fn) {
            docListeners[type] = docListeners[type] || [];
            docListeners[type].push(fn);
        },
        dispatchEvent(evt) {
            (docListeners[evt.type] || []).forEach((fn) => {
                try {
                    fn(evt);
                } catch (_) {}
            });
        },
        dispatchKeydown(key) {
            let prevented = false;
            const evt = {
                key,
                preventDefault() {
                    prevented = true;
                },
            };
            (docListeners.keydown || []).forEach((fn) => fn(evt));
            return prevented;
        },
    };
    doc.body = doc.createElement('body');
    return { doc, byId };
}

test('E1-AK1: film_wizard switches between 4 step panels via CSS classes, preserves inputs on Back, allows skipping Step 3, and closes on ESC only in Step 1', async () => {
    const { doc } = createWizardMockDom();

    const mockFetch = async (url) => {
        if (url.startsWith('/api/search')) {
            return {
                ok: true,
                status: 200,
                json: async () => [{ id: '603', name: 'Matrix (1999)', provider: 'tmdb' }],
            };
        }
        if (url.startsWith('/api/metadata/fetch')) {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    title: 'Matrix',
                    year: '1999',
                    plot: 'Neo entdeckt die Wahrheit.',
                    fsk: '16',
                    genres: ['Action', 'Sci-Fi'],
                }),
            };
        }
        if (url === '/api/preview_process') {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    destination: '/mnt/nas/Filme/Matrix Reloaded Custom (1999)',
                    renames: [{ old: 'matrix.mkv', new: 'Matrix Reloaded Custom (1999).mkv' }],
                    subs: [],
                    junk: [],
                }),
            };
        }
        throw new Error(`Unexpected URL: ${url}`);
    };

    const wizard = createFilmWizard({
        document: doc,
        fetch: mockFetch,
    });

    const step1 = doc.getElementById('mw-wizard-step-1');
    const step2 = doc.getElementById('mw-wizard-step-2');
    const step3 = doc.getElementById('mw-wizard-step-3');
    const step4 = doc.getElementById('mw-wizard-step-4');

    wizard.open({ query: 'Matrix', autoSearch: false });
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);
    assert.equal(step1.classList.contains('active'), true);
    assert.equal(step2.classList.contains('hidden'), true);

    // ESC in Step 1 closes the modal
    doc.dispatchKeydown('Escape');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);

    // Re-open and select movie -> transitions to Step 2
    wizard.open({ query: 'Matrix', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '603', name: 'Matrix (1999)', provider: 'tmdb' });
    assert.equal(wizard.getCurrentStep(), 2);
    assert.equal(step1.classList.contains('hidden'), true);
    assert.equal(step2.classList.contains('active'), true);
    assert.equal(step2.classList.contains('hidden'), false);

    // ESC in Step 2 must NOT close the modal
    doc.dispatchKeydown('Escape');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // Modify fields in Step 2
    wizard.nfoEditor.elements.title.value = 'Matrix Reloaded Custom';
    wizard.nfoEditor.elements.fsk.value = '18';
    wizard.nfoEditor.elements.genres.value = 'Sci-Fi, Action, Kult';

    // Advance to Step 3
    doc.getElementById('mw-wizard-btn-next').click();
    assert.equal(wizard.getCurrentStep(), 3);
    assert.equal(step2.classList.contains('hidden'), true);
    assert.equal(step3.classList.contains('active'), true);

    // ESC in Step 3 must NOT close the modal
    doc.dispatchKeydown('Escape');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // Go Back to Step 2 -> inputs must be preserved
    doc.getElementById('mw-wizard-btn-back').click();
    assert.equal(wizard.getCurrentStep(), 2);
    assert.equal(wizard.nfoEditor.elements.title.value, 'Matrix Reloaded Custom');
    assert.equal(wizard.nfoEditor.elements.fsk.value, '18');
    assert.equal(wizard.nfoEditor.elements.genres.value, 'Sci-Fi, Action, Kult');

    // Go to Step 3 again and skip Step 3 -> lands on Step 4
    doc.getElementById('mw-wizard-btn-next').click();
    assert.equal(wizard.getCurrentStep(), 3);
    doc.getElementById('mw-wizard-btn-skip').click();
    assert.equal(wizard.getCurrentStep(), 4);
    assert.equal(wizard.isArtworkSkipped(), true);
    assert.equal(step3.classList.contains('hidden'), true);
    assert.equal(step4.classList.contains('active'), true);
    assert.equal(doc.getElementById('mw-wizard-btn-execute').classList.contains('hidden'), false);
    assert.equal(doc.getElementById('mw-wizard-btn-handover'), null);

    // ESC in Step 4 must NOT close the modal
    doc.dispatchKeydown('Escape');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // E3-AK3: handover helpers are removed; buildMovieBasePayload delivers 5-key nfo_overrides.movie and wizard_overrides flag
    assert.equal(wizard.triggerHandover, undefined);
    assert.equal(wizard.getHandoverPayload, undefined);
    const basePayload = wizard.buildMovieBasePayload();
    assert.ok(basePayload);
    assert.equal(basePayload.wizard_overrides, true);
    assert.deepEqual(basePayload.nfo_overrides, {
        movie: {
            title: 'Matrix Reloaded Custom',
            year: '1999',
            plot: 'Neo entdeckt die Wahrheit.',
            fsk: '18',
            genres: ['Sci-Fi', 'Action', 'Kult'],
        },
    });
});

test('Delayed and swapped metadata responses: manual edits during request are preserved and stale responses from previous selection A are discarded', async () => {
    const { doc } = createWizardMockDom();
    const pendingResolvers = {};

    const mockFetch = (url) =>
        new Promise((resolve) => {
            if (url.includes('movie_id=100')) {
                pendingResolvers.movieA = resolve;
            } else if (url.includes('movie_id=200')) {
                pendingResolvers.movieB = resolve;
            }
        });

    const wizard = createFilmWizard({ document: doc, fetch: mockFetch });
    wizard.open({ query: 'Test', autoSearch: false });

    // 1. Select Movie A -> transitions to Step 2 immediately while request A is pending
    const promiseA = wizard.selectMovieInWizard({ id: '100', name: 'Film A (2001)', provider: 'tmdb' });
    assert.equal(wizard.getCurrentStep(), 2);

    // User goes Back to Step 1 and selects Movie B while A is still pending
    doc.getElementById('mw-wizard-btn-back').click();
    const promiseB = wizard.selectMovieInWizard({ id: '200', name: 'Film B (2022)', provider: 'tmdb' });
    assert.equal(wizard.getCurrentStep(), 2);

    // User manually edits title and FSK of Movie B while B's request is still in flight
    wizard.nfoEditor.elements.title.value = 'Film B - Manuell';
    wizard.nfoEditor.elements.fsk.value = '16';

    // B's metadata response arrives first (including FSK 0 in real fetch_movie_nfo_data format)
    pendingResolvers.movieB({
        ok: true,
        status: 200,
        json: async () => ({
            title: 'Film B Provider',
            plot: 'Plot von Film B.',
            year: '2022',
            fsk: '0',
            genres: ['Familie', 'Animation'],
        }),
    });
    await promiseB;

    // Manual edits on title & fsk are preserved; untouched year, plot, genres are populated from B; editor stays dirty
    assert.equal(wizard.nfoEditor.elements.title.value, 'Film B - Manuell');
    assert.equal(wizard.nfoEditor.elements.fsk.value, '16');
    assert.equal(wizard.nfoEditor.elements.year.value, '2022');
    assert.equal(wizard.nfoEditor.elements.plot.value, 'Plot von Film B.');
    assert.equal(wizard.nfoEditor.elements.genres.value, 'Familie, Animation');
    assert.equal(wizard.nfoEditor.isDirty(), true);

    // Now delayed response for Movie A arrives AFTER Movie B -> must be completely ignored
    pendingResolvers.movieA({
        ok: true,
        status: 200,
        json: async () => ({
            title: 'Veralteter Film A',
            plot: 'Veralteter Plot A',
            year: '2001',
            fsk: '18',
            genres: ['Horror'],
        }),
    });
    await promiseA;

    assert.equal(wizard.nfoEditor.elements.title.value, 'Film B - Manuell');
    assert.equal(wizard.nfoEditor.elements.year.value, '2022');
    assert.equal(wizard.nfoEditor.elements.plot.value, 'Plot von Film B.');
    assert.equal(wizard.nfoEditor.elements.fsk.value, '16');
    assert.equal(wizard.nfoEditor.elements.genres.value, 'Familie, Animation');
});

test('Immediate handover and failed metadata fetch do not send unloaded fields as empty, while explicitly cleared fields and FSK 0 are preserved', async () => {
    const { doc } = createWizardMockDom();
    let mode = 'pending';
    let resolvePending = null;

    const mockFetch = () => {
        if (mode === 'pending') {
            return new Promise((resolve) => {
                resolvePending = resolve;
            });
        }
        if (mode === 'error_payload') {
            return Promise.resolve({
                ok: true,
                status: 200,
                json: async () => ({
                    title: '',
                    plot: '',
                    year: '',
                    fsk: '',
                    genres: [],
                    error: 'TMDB-Filmmetadaten konnten nicht geladen werden: Timeout',
                }),
            });
        }
        return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({
                title: 'Chihiros Reise ins Zauberland',
                plot: 'Ein Mädchen gerät in eine Geisterwelt.',
                year: '2001',
                fsk: '0',
                genres: ['Animation', 'Fantasy'],
            }),
        });
    };

    const wizard = createFilmWizard({ document: doc, fetch: mockFetch });

    // 1. Pending metadata fetch: unloaded fields are NOT sent as empty
    mode = 'pending';
    wizard.open({ query: 'Chihiro', autoSearch: false });
    wizard.selectMovieInWizard({ id: '129', name: 'Chihiros Reise', provider: 'tmdb' });
    const immediatePayload = wizard.buildMovieBasePayload();
    assert.equal(immediatePayload.wizard_overrides, true);
    assert.deepEqual(immediatePayload.nfo_overrides, {
        movie: {
            title: 'Chihiros Reise',
        },
    });
    if (resolvePending) resolvePending({ ok: false, status: 500, json: async () => ({}) });

    // 2. Fehlerfall (metadata fetch returns error payload): unloaded fields are NOT sent as empty
    mode = 'error_payload';
    wizard.open({ query: 'Chihiro', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '129', name: 'Chihiros Reise', provider: 'tmdb' });
    assert.equal(doc.getElementById('mw-wizard-error-banner').classList.contains('hidden'), false);
    const errorPayload = wizard.buildMovieBasePayload();
    assert.deepEqual(errorPayload.nfo_overrides, {
        movie: {
            title: 'Chihiros Reise',
        },
    });

    // 3. Loaded FSK 0 is preserved, and explicitly clearing plot/genres sends empty values (D6c)
    mode = 'fsk_zero';
    wizard.open({ query: 'Chihiro', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '129', name: 'Chihiros Reise', provider: 'tmdb' });
    assert.equal(wizard.nfoEditor.elements.fsk.value, '0');
    wizard.nfoEditor.elements.plot.value = '';
    wizard.nfoEditor.elements.genres.value = '';
    const clearedPayload = wizard.buildMovieBasePayload();
    assert.deepEqual(clearedPayload.nfo_overrides, {
        movie: {
            title: 'Chihiros Reise ins Zauberland',
            year: '2001',
            plot: '',
            fsk: '0',
            genres: [],
        },
    });
});

test('D3 & Item 6: Dirty confirmation protects against accidental close in Step 1 after going Back, including on ESC', async () => {
    const { doc } = createWizardMockDom();
    let confirmCalls = 0;
    let allowConfirm = false;

    const wizard = createFilmWizard({
        document: doc,
        fetch: async () => ({
            ok: true,
            status: 200,
            json: async () => ({
                title: 'Inception',
                plot: 'Traum im Traum.',
                year: '2010',
                fsk: '12',
                genres: ['Sci-Fi'],
            }),
        }),
        confirm: () => {
            confirmCalls += 1;
            return allowConfirm;
        },
    });

    wizard.open({ query: 'Inception', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '27205', name: 'Inception', provider: 'tmdb' });
    assert.equal(wizard.getCurrentStep(), 2);

    // Edit title in Step 2 -> dirty
    wizard.nfoEditor.elements.title.value = 'Inception Director Cut';
    assert.equal(wizard.nfoEditor.isDirty(), true);

    // Navigate Back to Step 1
    doc.getElementById('mw-wizard-btn-back').click();
    assert.equal(wizard.getCurrentStep(), 1);

    // Pressing ESC in Step 1 when dirty must ask for confirmation; declining keeps modal open
    allowConfirm = false;
    doc.dispatchKeydown('Escape');
    assert.equal(confirmCalls, 1);
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // Clicking close button in Step 1 when dirty also asks for confirmation
    doc.getElementById('mw-wizard-close').click();
    assert.equal(confirmCalls, 2);
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // Accepting confirmation on ESC in Step 1 closes the modal
    allowConfirm = true;
    doc.dispatchKeydown('Escape');
    assert.equal(confirmCalls, 3);
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);
});

test('E1-AK5 & E1-AK6: index.html preserves #context-movie and uses only CSS variables / .mw-wizard-* without new inline-style-NN classes', () => {
    const indexHtml = fs.readFileSync(path.join(__dirname, '../../gui/static/index.html'), 'utf8');
    const styleCss = fs.readFileSync(path.join(__dirname, '../../gui/static/style.css'), 'utf8');

    // #context-movie is preserved for Doku and handover (E1-AK5)
    assert.match(indexHtml, /id="context-movie"/);
    assert.match(indexHtml, /id="modal-film-wizard"/);

    // Extract #modal-film-wizard markup and verify no inline-style-NN or style="..." attributes (E1-AK6)
    const wizardSection = indexHtml.slice(indexHtml.indexOf('id="modal-film-wizard"'));
    assert.doesNotMatch(wizardSection, /inline-style-\d+/);
    assert.doesNotMatch(wizardSection, /\sstyle="/);
    assert.doesNotMatch(wizardSection, /id="mw-wizard-btn-handover"/);
    assert.match(wizardSection, /id="mw-wizard-btn-execute"/);

    // Verify .mw-wizard-* rules exist in style.css and use CSS variables
    assert.match(styleCss, /\.mw-wizard-modal\s*\{/);
    assert.match(styleCss, /\.mw-wizard-stepper\s*\{/);
    assert.match(styleCss, /var\(--bg-card\)/);
    assert.match(styleCss, /var\(--border-glass\)/);
});

test('Numeric TMDb movie.id from /api/search is normalized to string in handover so renderProviderInfo never crashes, and loading/manual badge states are shown', async () => {
    const { doc } = createWizardMockDom();
    let resolveMeta = null;

    const wizard = createFilmWizard({
        document: doc,
        fetch: () =>
            new Promise((resolve) => {
                resolveMeta = resolve;
            }),
    });

    wizard.open({ query: 'Alien', autoSearch: false });
    const selectPromise = wizard.selectMovieInWizard({ id: 348, name: 'Alien (1979)', provider: 'tmdb' });

    // While metadata is loading, badge indicates loading state
    const badge = doc.getElementById('mw-wizard-provider-badge');
    assert.match(badge.textContent, /Lade Metadaten/);

    resolveMeta({
        ok: true,
        status: 200,
        json: async () => ({
            title: 'Alien - Das unheimliche Wesen aus einer fremden Welt',
            year: '1979',
            plot: 'WIZARD-PLOT-F5',
            fsk: '16',
            genres: ['Horror', 'Science Fiction'],
        }),
    });
    await selectPromise;
    assert.equal(badge.textContent, 'TMDB');

    wizard.nfoEditor.elements.fsk.value = '18';
    const basePayload = wizard.buildMovieBasePayload();
    assert.equal(typeof basePayload.movie_id, 'string');
    assert.equal(basePayload.movie_id, '348');
    assert.equal(basePayload.nfo_overrides.movie.title, 'Alien - Das unheimliche Wesen aus einer fremden Welt');
    assert.equal(basePayload.nfo_overrides.movie.year, '1979');
    assert.equal(basePayload.nfo_overrides.movie.plot, 'WIZARD-PLOT-F5');
    assert.equal(basePayload.nfo_overrides.movie.fsk, '18');

    // Manual button shows "Metadaten manuell eintragen"
    wizard.open({ query: 'Das Boot', autoSearch: false });
    doc.getElementById('mw-wizard-manual-btn').click();
    assert.equal(badge.textContent, 'Metadaten manuell eintragen');
});

test('E2 (1 & 2): Step 4 calls /api/preview_process, renders destination, renames, subs, junk, and #91 hint, and "Jetzt final verarbeiten" sends /api/process exactly once (with double-click guard)', async () => {
    const { doc } = createWizardMockDom();
    let capturedPreviewPayload = null;
    const processCalls = [];
    let resolveProcess = null;
    let successCallbackCalls = 0;

    const mockFetch = async (url, opts = {}) => {
        if (url.startsWith('/api/metadata/fetch')) {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    title: 'X-Men',
                    year: '2000',
                    plot: 'Mutanten kämpfen um ihre Zukunft.',
                    fsk: '12',
                    genres: ['Action', 'Sci-Fi'],
                }),
            };
        }
        if (url === '/api/preview_process') {
            capturedPreviewPayload = JSON.parse(opts.body);
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    destination: '/mnt/nas/Filme/X-Men (2000)\n/pCloud/Filme/<script>alert(1)</script>',
                    renames: [
                        { old: 'xmen-cd1.mkv', new: 'X-Men (2000) - CD1.mkv' },
                        { old: 'xmen-sample.mkv', new: 'X-Men (2000) - Sample.mkv' },
                    ],
                    subs: [{ old: 'xmen.srt', new: 'X-Men (2000).de.srt' }],
                    junk: ['RARBG.txt', 'keep-notes.txt'],
                    similar_existing: {
                        exact: [{ folder: 'X-Men (2000)', relative_path: 'Action/X-Men (2000)' }],
                        similar: [{ folder: 'X-Men 2 (2003)', relative_path: 'Action/X-Men 2 (2003)', overlap: 2 }],
                    },
                }),
            };
        }
        if (url === '/api/process') {
            processCalls.push(JSON.parse(opts.body));
            return new Promise((resolve) => {
                resolveProcess = resolve;
            });
        }
        throw new Error(`Unexpected URL: ${url}`);
    };

    const wizard = createFilmWizard({
        document: doc,
        fetch: mockFetch,
        onProcessSuccess: () => {
            successCallbackCalls += 1;
        },
    });

    wizard.open({ query: 'X-Men', projectName: 'X-Men.2000.1080p', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '36657', name: 'X-Men (2000)', provider: 'tmdb' });
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));

    // Verify /api/preview_process payload
    assert.ok(capturedPreviewPayload);
    assert.equal(capturedPreviewPayload.media_type, 'movie');
    assert.equal(capturedPreviewPayload.project_name, 'X-Men.2000.1080p');
    assert.equal(capturedPreviewPayload.movie_name, 'X-Men (2000)');
    assert.equal(capturedPreviewPayload.movie_id, '36657');
    assert.equal(capturedPreviewPayload.provider, 'tmdb');
    assert.equal(capturedPreviewPayload.wizard_overrides, true);

    // Verify rendered destination (escaped + <br>), lists, and #91 hint (E2-AK1, E2-AK2, E2-AK4)
    const destEl = doc.getElementById('mw-wizard-destination');
    assert.match(destEl.innerHTML, /\/mnt\/nas\/Filme\/X-Men \(2000\)<br>\/pCloud\/Filme\/&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
    assert.equal(destEl.querySelectorAll('script').length, 0);

    const similarBox = doc.getElementById('mw-wizard-similar-existing');
    assert.equal(similarBox.classList.contains('hidden'), false);
    assert.ok(doc.getElementById('mw-wizard-similar-exact').textContent.includes('X-Men (2000)'));
    assert.ok(doc.getElementById('mw-wizard-similar-fuzzy').textContent.includes('X-Men 2 (2003)'));

    const renameCbs = doc.getElementById('mw-wizard-list-renames').querySelectorAll('.preview-cb-renames');
    const subCbs = doc.getElementById('mw-wizard-list-subs').querySelectorAll('.preview-cb-subs');
    const junkCbs = doc.getElementById('mw-wizard-list-junk').querySelectorAll('.preview-cb-junk');
    assert.equal(renameCbs.length, 2);
    assert.equal(subCbs.length, 1);
    assert.equal(junkCbs.length, 2);

    // Uncheck second rename and second junk item
    renameCbs[1].checked = false;
    junkCbs[1].checked = false;

    // Click "Jetzt final verarbeiten" twice rapidly -> double-click guard allows only 1 POST /api/process
    const executeBtn = doc.getElementById('mw-wizard-btn-execute');
    executeBtn.click();
    executeBtn.click();
    assert.equal(processCalls.length, 1);
    assert.equal(executeBtn.disabled, true);

    resolveProcess({ ok: true, status: 200, json: async () => ({ status: 'started' }) });
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(processCalls.length, 1);
    assert.deepEqual(processCalls[0].explicit_renames, [{ old: 'xmen-cd1.mkv', new: 'X-Men (2000) - CD1.mkv' }]);
    assert.deepEqual(processCalls[0].explicit_subs, [{ old: 'xmen.srt', new: 'X-Men (2000).de.srt' }]);
    assert.deepEqual(processCalls[0].explicit_junk, ['RARBG.txt']);
    assert.deepEqual(processCalls[0].nfo_overrides, {
        movie: {
            title: 'X-Men',
            year: '2000',
            plot: 'Mutanten kämpfen um ihre Zukunft.',
            fsk: '12',
            genres: ['Action', 'Sci-Fi'],
        },
    });
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);
    assert.equal(successCallbackCalls, 1);
});

test('E2 (3): Wizard and legacy executeMovieWorkflow produce identical /api/process payloads for identical inputs (E2-AK2)', async () => {
    const sharedPreviewResponse = {
        destination: '/mnt/nas/Filme/Blade Runner (1982)',
        renames: [{ old: 'bladerunner.mkv', new: 'Blade Runner (1982).mkv' }],
        subs: [{ old: 'bladerunner.srt', new: 'Blade Runner (1982).de.srt' }],
        junk: ['RARBG.nfo'],
    };

    // 1. Capture payload from Wizard Step 4
    const { doc: wizDoc } = createWizardMockDom();
    let wizardProcessPayload = null;
    const wizard = createFilmWizard({
        document: wizDoc,
        fetch: async (url, opts = {}) => {
            if (url === '/api/preview_process') {
                return { ok: true, status: 200, json: async () => sharedPreviewResponse };
            }
            if (url === '/api/process') {
                wizardProcessPayload = JSON.parse(opts.body);
                return { ok: true, status: 200, json: async () => ({ status: 'started' }) };
            }
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    title: 'Blade Runner',
                    year: '1982',
                    plot: 'Replikanten in Los Angeles.',
                    fsk: '16',
                    genres: ['Sci-Fi', 'Thriller'],
                }),
            };
        },
    });

    wizard.open({
        query: 'Blade Runner',
        projectName: 'Blade.Runner.1982',
        autoSearch: false,
        options: {
            convert: true,
            quality: 65,
            delete_original: false,
            copy_to_nas: true,
            copy_to_pcloud: true,
            nas_destination_id: '1',
            pcloud_destination_id: '4',
        },
    });
    await wizard.selectMovieInWizard({ id: '78', name: 'Blade Runner (1982)', provider: 'tmdb' });
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    await wizard.executeStep4Process();

    // 2. Capture payload from legacy executeMovieWorkflow -> openPreviewModal -> #btn-preview-execute in app.js
    const { doc: appDoc } = createWizardMockDom();
    appDoc.documentElement = appDoc.createElement('html');
    const origGetEl = appDoc.getElementById.bind(appDoc);
    const ensureEl = (id, tag = 'div') => {
        let el = origGetEl(id);
        if (!el) {
            el = appDoc.createElement(tag);
            el.id = id;
            appDoc.body.appendChild(el);
        }
        return el;
    };
    appDoc.getElementById = (id) => origGetEl(id) || ensureEl(id);

    ensureEl('movie-option-convert', 'input').checked = true;
    ensureEl('movie-option-delete', 'input').checked = false;
    ensureEl('movie-option-copy-nas', 'input').checked = true;
    ensureEl('movie-option-copy-pcloud', 'input').checked = true;
    ensureEl('movie-nas-destination', 'select').value = '1';
    ensureEl('movie-pcloud-destination', 'select').value = '4';
    ensureEl('movie-quality-slider', 'input').value = '65';
    ensureEl('movie-nfo-title', 'input').value = 'Blade Runner';
    ensureEl('movie-nfo-year', 'input').value = '1982';
    ensureEl('movie-nfo-plot', 'textarea').value = 'Replikanten in Los Angeles.';
    ensureEl('btn-preview-execute', 'button');

    let legacyProcessPayload = null;
    const mockFetch = async (url, opts = {}) => {
        if (url === '/api/preview_process') {
            return { ok: true, status: 200, json: async () => sharedPreviewResponse };
        }
        if (url === '/api/process') {
            legacyProcessPayload = JSON.parse(opts.body);
            return { ok: true, status: 200, json: async () => ({ status: 'started' }) };
        }
        return { ok: true, status: 200, json: async () => ({}) };
    };

    const appJsRaw = fs.readFileSync(path.join(__dirname, '../../gui/static/app.js'), 'utf8');
    const cleanAppJs = `
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
const osBasename = (p) => String(p || '');
const formatFskLabel = (f) => f;
const guessEpisodeNumber = () => 1;
const guessSeasonAndEpisode = () => null;
const cleanFilenameForManualTitle = (f) => f;
const fetchStats = () => Promise.resolve();
const fetchYoutubeSubscriptions = () => Promise.resolve();
const fetchSmartInboxSuggestions = () => Promise.resolve();
` + appJsRaw.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '') + `
globalThis.__runLegacyMovie = async () => {
    currentProject = 'Blade.Runner.1982';
    selectedMovie = { id: '78', name: 'Blade Runner (1982)', provider: 'tmdb' };
    await executeMovieWorkflow();
};
`;

    const sandbox = {
        document: appDoc,
        window: { fetch: mockFetch, scrollTo: () => {}, addEventListener: () => {} },
        fetch: mockFetch,
        localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 0; },
        clearTimeout: () => {},
        setInterval: () => 0,
        clearInterval: () => {},
        alert: () => {},
        console: { log: () => {}, warn: () => {}, error: () => {} },
        EventSource: class { close() {} },
        renderPreviewData,
        collectPreviewSelection,
    };
    sandbox.globalThis = sandbox;
    vm.runInNewContext(cleanAppJs, sandbox);
    appDoc.dispatchEvent({ type: 'DOMContentLoaded' });
    await sandbox.__runLegacyMovie();
    await new Promise((r) => setTimeout(r, 0));
    appDoc.getElementById('btn-preview-execute').click();
    await new Promise((r) => setTimeout(r, 0));

    assert.ok(wizardProcessPayload);
    assert.ok(legacyProcessPayload);
    assert.equal(wizardProcessPayload.wizard_overrides, true);
    assert.equal(legacyProcessPayload.wizard_overrides, undefined);
    const { wizard_overrides: _wo, nfo_overrides: wizNfo, ...wizRest } = wizardProcessPayload;
    const { nfo_overrides: legNfo, ...legRest } = legacyProcessPayload;
    assert.deepEqual(wizRest, legRest);
    assert.equal(wizNfo.movie.title, legNfo.movie.title);
    assert.equal(wizNfo.movie.year, legNfo.movie.year);
    assert.equal(wizNfo.movie.plot, legNfo.movie.plot);
});

test('E2 (4): Error and pending states of /api/preview_process block execution while keeping Retry/Back active, /api/process errors re-enable execution, and option changes discard stale preview responses', async () => {
    const { doc } = createWizardMockDom();
    const logs = [];
    let previewMode = 'error';
    let processMode = 'error';
    const processPayloads = [];
    const pendingPreviewResolvers = [];

    const mockFetch = (url, opts = {}) => {
        if (url === '/api/preview_process') {
            if (previewMode === 'error') {
                return Promise.resolve({
                    ok: false,
                    status: 500,
                    json: async () => ({ error: 'NAS-Zielpfad nicht erreichbar' }),
                });
            }
            if (previewMode === 'race') {
                return new Promise((resolve) => {
                    pendingPreviewResolvers.push(resolve);
                });
            }
            return Promise.resolve({
                ok: true,
                status: 200,
                json: async () => ({
                    destination: '/mnt/nas/Filme/Dune (2021)',
                    renames: [{ old: 'dune.mkv', new: 'Dune (2021).mkv' }],
                    subs: [],
                    junk: [],
                }),
            });
        }
        if (url === '/api/process') {
            processPayloads.push(JSON.parse(opts.body));
            if (processMode === 'error') {
                return Promise.resolve({
                    ok: false,
                    status: 500,
                    json: async () => ({ error: 'Worker ausgelastet' }),
                });
            }
            return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'started' }) });
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    };

    const wizard = createFilmWizard({
        document: doc,
        fetch: mockFetch,
        onLog: (msg) => logs.push(msg),
    });

    wizard.open({ query: 'Dune', projectName: 'Dune.2021', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '438631', name: 'Dune', year: '2021', provider: 'manual' }, false);

    // 1. /api/preview_process error -> visible error banner, executeBtn disabled, Retry & Back remain active
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));

    const errorBanner = doc.getElementById('mw-wizard-error-banner');
    const errorText = doc.getElementById('mw-wizard-error-text');
    const executeBtn = doc.getElementById('mw-wizard-btn-execute');
    const retryBtn = doc.getElementById('mw-wizard-error-retry');
    const backBtn = doc.getElementById('mw-wizard-btn-back');
    assert.equal(errorBanner.classList.contains('hidden'), false);
    assert.match(errorText.textContent, /NAS-Zielpfad nicht erreichbar/);
    assert.equal(executeBtn.disabled, true);
    assert.equal(retryBtn.disabled, false);
    assert.equal(backBtn.disabled, false);
    assert.equal(backBtn.classList.contains('hidden'), false);

    // Clicking execute or calling executeStep4Process after preview error must not call /api/process
    executeBtn.click();
    assert.equal(await wizard.executeStep4Process(), null);
    assert.equal(processPayloads.length, 0);

    // 2. Retry succeeds -> executeBtn enabled; then /api/process error -> visible error banner, executeBtn re-enabled
    previewMode = 'ok';
    retryBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(errorBanner.classList.contains('hidden'), true);
    assert.equal(doc.getElementById('mw-wizard-destination').innerHTML, '/mnt/nas/Filme/Dune (2021)');
    assert.equal(executeBtn.disabled, false);

    executeBtn.click();
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(processPayloads.length, 1);
    assert.equal(errorBanner.classList.contains('hidden'), false);
    assert.match(errorText.textContent, /Worker ausgelastet/);
    assert.equal(executeBtn.disabled, false);
    assert.equal(executeBtn.textContent, 'Jetzt final verarbeiten');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);
    assert.ok(logs.some((l) => l.includes('Worker ausgelastet')));

    // 3. Changing destination option in Step 4 disables executeBtn while pending and discards stale earlier response
    previewMode = 'race';
    const optPcloud = doc.getElementById('mw-wizard-option-copy-pcloud');
    optPcloud.checked = true;
    optPcloud.dispatchEvent({ type: 'change' });
    assert.equal(executeBtn.disabled, true);
    executeBtn.click();
    assert.equal(await wizard.executeStep4Process(), null);
    assert.equal(processPayloads.length, 1);

    optPcloud.checked = false;
    optPcloud.dispatchEvent({ type: 'change' });
    assert.equal(pendingPreviewResolvers.length, 2);

    // Resolve second (newest) request first, then stale first request afterwards
    pendingPreviewResolvers[1]({
        ok: true,
        status: 200,
        json: async () => ({
            destination: '/mnt/nas/Filme/Dune (2021) [aktuell]',
            renames: [],
            subs: [],
            junk: [],
        }),
    });
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(doc.getElementById('mw-wizard-destination').innerHTML, '/mnt/nas/Filme/Dune (2021) [aktuell]');
    assert.equal(executeBtn.disabled, false);

    pendingPreviewResolvers[0]({
        ok: true,
        status: 200,
        json: async () => ({
            destination: '/mnt/nas/Filme/Dune (2021) [veraltet]',
            renames: [],
            subs: [],
            junk: [],
        }),
    });
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(doc.getElementById('mw-wizard-destination').innerHTML, '/mnt/nas/Filme/Dune (2021) [aktuell]');
});

test('E2 (5): Collapsible groups in Step 4 start open for 1-3 items, collapsed for 0 or > 3 items, and toggle on header click', async () => {
    const { doc } = createWizardMockDom();

    const wizard = createFilmWizard({
        document: doc,
        fetch: async () => ({
            ok: true,
            status: 200,
            json: async () => ({
                destination: '/mnt/nas/Filme/Avatar (2009)',
                renames: [
                    { old: 'a1.mkv', new: 'Avatar (2009) - Part 1.mkv' },
                    { old: 'a2.mkv', new: 'Avatar (2009) - Part 2.mkv' },
                ],
                subs: [
                    { old: 's1.srt', new: 'Avatar.de.srt' },
                    { old: 's2.srt', new: 'Avatar.en.srt' },
                    { old: 's3.srt', new: 'Avatar.fr.srt' },
                    { old: 's4.srt', new: 'Avatar.es.srt' },
                ],
                junk: [],
            }),
        }),
    });

    wizard.open({ query: 'Avatar', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '19995', name: 'Avatar', year: '2009', provider: 'manual' }, false);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));

    const groupRenames = doc.getElementById('mw-wizard-group-renames');
    const headerRenames = doc.getElementById('mw-wizard-group-header-renames');
    const listRenames = doc.getElementById('mw-wizard-list-renames');

    const groupSubs = doc.getElementById('mw-wizard-group-subs');
    const headerSubs = doc.getElementById('mw-wizard-group-header-subs');
    const listSubs = doc.getElementById('mw-wizard-list-subs');

    const groupJunk = doc.getElementById('mw-wizard-group-junk');
    const listJunk = doc.getElementById('mw-wizard-list-junk');

    // Renames (2 <= 3) starts open; Subs (4 > 3) and empty Junk (0) start collapsed (handtest decision 2026-11-09)
    assert.equal(doc.getElementById('mw-wizard-group-title-renames').textContent, 'Umbenennungen (2)');
    assert.equal(groupRenames.classList.contains('collapsed'), false);
    assert.equal(headerRenames.getAttribute('aria-expanded'), 'true');
    assert.equal(listRenames.classList.contains('hidden'), false);

    assert.equal(doc.getElementById('mw-wizard-group-title-subs').textContent, 'Untertitel & Extras (4)');
    assert.equal(groupSubs.classList.contains('collapsed'), true);
    assert.equal(headerSubs.getAttribute('aria-expanded'), 'false');
    assert.equal(listSubs.classList.contains('hidden'), true);

    assert.equal(doc.getElementById('mw-wizard-group-title-junk').textContent, 'Junk-Dateien (0)');
    assert.equal(groupJunk.classList.contains('collapsed'), true);
    assert.equal(listJunk.classList.contains('hidden'), true);

    // Clicking collapsed Subs header opens it
    headerSubs.click();
    assert.equal(groupSubs.classList.contains('collapsed'), false);
    assert.equal(headerSubs.getAttribute('aria-expanded'), 'true');
    assert.equal(listSubs.classList.contains('hidden'), false);
});

test('E2-AK3 Regression (Finding 1): With both Wizard and legacy Preview Modal in the same document, closing Wizard and executing Series/Doku preview does not leak Wizard checkboxes into legacy payload', async () => {
    const { doc } = createWizardMockDom();
    const origGetEl = doc.getElementById.bind(doc);
    const ensureEl = (id, tag = 'div') => {
        let el = origGetEl(id);
        if (!el) {
            el = doc.createElement(tag);
            el.id = id;
            doc.body.appendChild(el);
        }
        return el;
    };
    doc.getElementById = (id) => origGetEl(id) || ensureEl(id);

    ensureEl('btn-preview-execute', 'button');
    ensureEl('series-option-no-profile', 'input').checked = true;

    const processPayloads = [];
    const mockFetch = async (url, opts = {}) => {
        if (url === '/api/preview_process') {
            const reqBody = JSON.parse(opts.body);
            if (reqBody.media_type === 'movie') {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        destination: '/mnt/nas/Filme/Matrix (1999)',
                        renames: [{ old: 'matrix-movie.mkv', new: 'Matrix (1999).mkv' }],
                        subs: [{ old: 'matrix-movie.srt', new: 'Matrix (1999).de.srt' }],
                        junk: ['movie-junk.txt'],
                    }),
                };
            }
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    destination: '/mnt/nas/Serien/Dark/Staffel 01',
                    renames: [{ old: 'dark-s01e01.mkv', new: 'Dark - S01E01.mkv' }],
                    subs: [{ old: 'dark-s01e01.srt', new: 'Dark - S01E01.de.srt' }],
                    junk: ['series-junk.nfo'],
                }),
            };
        }
        if (url === '/api/process') {
            processPayloads.push(JSON.parse(opts.body));
            return { ok: true, status: 200, json: async () => ({ status: 'started' }) };
        }
        return { ok: true, status: 200, json: async () => ({}) };
    };

    // 1. Mount Wizard in the shared document, load Step 4 movie preview, and close Wizard (checked movie items stay in DOM)
    const wizard = createFilmWizard({ document: doc, fetch: mockFetch });
    wizard.open({ query: 'Matrix', projectName: 'Matrix.1999', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '603', name: 'Matrix', year: '1999', provider: 'manual' }, false);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(doc.getElementById('mw-wizard-list-renames').querySelectorAll('.preview-cb-renames').length, 1);
    wizard.close({ force: true });
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);

    // 2. Run app.js in the SAME document, open legacy preview modal for Series, and execute
    const appJsRaw = fs.readFileSync(path.join(__dirname, '../../gui/static/app.js'), 'utf8');
    const cleanAppJs = `
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
const osBasename = (p) => String(p || '');
const formatFskLabel = (f) => f;
const guessEpisodeNumber = () => 1;
const guessSeasonAndEpisode = () => null;
const cleanFilenameForManualTitle = (f) => f;
const fetchStats = () => Promise.resolve();
const fetchYoutubeSubscriptions = () => Promise.resolve();
const fetchSmartInboxSuggestions = () => Promise.resolve();
` + appJsRaw.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '') + `
globalThis.__openLegacySeriesPreview = openPreviewModal;
`;

    const sandbox = {
        document: doc,
        window: { fetch: mockFetch, scrollTo: () => {}, addEventListener: () => {} },
        fetch: mockFetch,
        localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 0; },
        clearTimeout: () => {},
        setInterval: () => 0,
        clearInterval: () => {},
        alert: () => {},
        console: { log: () => {}, warn: () => {}, error: () => {} },
        EventSource: class { close() {} },
        renderPreviewData,
        collectPreviewSelection,
    };
    sandbox.globalThis = sandbox;
    vm.runInNewContext(cleanAppJs, sandbox);
    doc.dispatchEvent({ type: 'DOMContentLoaded' });

    await sandbox.__openLegacySeriesPreview({
        media_type: 'tv',
        project_name: 'Dark.S01',
        show_name: 'Dark (2017)',
        show_id: '70523',
        provider: 'tmdb',
    });
    await new Promise((r) => setTimeout(r, 0));

    doc.getElementById('btn-preview-execute').click();
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(processPayloads.length, 1);
    assert.equal(processPayloads[0].media_type, 'tv');
    assert.deepEqual(processPayloads[0].explicit_renames, [{ old: 'dark-s01e01.mkv', new: 'Dark - S01E01.mkv' }]);
    assert.deepEqual(processPayloads[0].explicit_subs, [{ old: 'dark-s01e01.srt', new: 'Dark - S01E01.de.srt' }]);
    assert.deepEqual(processPayloads[0].explicit_junk, ['series-junk.nfo']);
});

test('Regression (Finding 3): Unchecked renames, subs, and junk checkboxes are preserved across Step 4 preview refreshes when destination options change', async () => {
    const { doc } = createWizardMockDom();
    const processPayloads = [];
    let previewCallCount = 0;

    const wizard = createFilmWizard({
        document: doc,
        fetch: async (url, opts = {}) => {
            if (url === '/api/preview_process') {
                previewCallCount += 1;
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        destination: previewCallCount === 1
                            ? '/mnt/nas/Filme/Arrival (2016)'
                            : '/mnt/nas/Filme/Arrival (2016)\n/pCloud/Filme/Arrival (2016)',
                        renames: [
                            { old: 'arrival-main.mkv', new: 'Arrival (2016).mkv' },
                            { old: 'arrival-sample.mkv', new: 'Arrival (2016) - Sample.mkv' },
                        ],
                        subs: [
                            { old: 'arrival-de.srt', new: 'Arrival (2016).de.srt' },
                            { old: 'arrival-en.srt', new: 'Arrival (2016).en.srt' },
                        ],
                        junk: ['RARBG.txt', 'keep-notes.txt'],
                    }),
                };
            }
            if (url === '/api/process') {
                processPayloads.push(JSON.parse(opts.body));
                return { ok: true, status: 200, json: async () => ({ status: 'started' }) };
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    wizard.open({ query: 'Arrival', projectName: 'Arrival.2016', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '329865', name: 'Arrival', year: '2016', provider: 'manual' }, false);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(previewCallCount, 1);

    // Explicitly uncheck 1 rename, 1 sub, and 1 junk item
    doc.getElementById('mw-wizard-list-renames').querySelectorAll('.preview-cb-renames')[1].checked = false;
    doc.getElementById('mw-wizard-list-subs').querySelectorAll('.preview-cb-subs')[1].checked = false;
    doc.getElementById('mw-wizard-list-junk').querySelectorAll('.preview-cb-junk')[1].checked = false;

    // Change pCloud option -> triggers a fresh /api/preview_process
    const optPcloud = doc.getElementById('mw-wizard-option-copy-pcloud');
    optPcloud.checked = true;
    optPcloud.dispatchEvent({ type: 'change' });
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(previewCallCount, 2);

    // Verify checkbox states after re-render
    const renamesAfter = doc.getElementById('mw-wizard-list-renames').querySelectorAll('.preview-cb-renames');
    const subsAfter = doc.getElementById('mw-wizard-list-subs').querySelectorAll('.preview-cb-subs');
    const junkAfter = doc.getElementById('mw-wizard-list-junk').querySelectorAll('.preview-cb-junk');
    assert.equal(renamesAfter[0].checked, true);
    assert.equal(renamesAfter[1].checked, false);
    assert.equal(subsAfter[0].checked, true);
    assert.equal(subsAfter[1].checked, false);
    assert.equal(junkAfter[0].checked, true);
    assert.equal(junkAfter[1].checked, false);

    // Execute process and verify unchecked items are excluded from explicit_* arrays
    doc.getElementById('mw-wizard-btn-execute').click();
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(processPayloads.length, 1);
    assert.deepEqual(processPayloads[0].explicit_renames, [{ old: 'arrival-main.mkv', new: 'Arrival (2016).mkv' }]);
    assert.deepEqual(processPayloads[0].explicit_subs, [{ old: 'arrival-de.srt', new: 'Arrival (2016).de.srt' }]);
    assert.deepEqual(processPayloads[0].explicit_junk, ['RARBG.txt']);
});

test('Regression (Finding 4): Pending /api/process -> Close -> Reopen blocks closing without force, prevents concurrent second /api/process, and ignores delayed completion of stale session', async () => {
    const { doc } = createWizardMockDom();
    const processCalls = [];
    const processResolvers = [];

    const wizard = createFilmWizard({
        document: doc,
        fetch: async (url, opts = {}) => {
            if (url === '/api/preview_process') {
                const body = JSON.parse(opts.body);
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({
                        destination: `/mnt/nas/Filme/${body.movie_name}`,
                        renames: [{ old: 'video.mkv', new: `${body.movie_name}.mkv` }],
                        subs: [],
                        junk: [],
                    }),
                };
            }
            if (url === '/api/process') {
                processCalls.push(JSON.parse(opts.body));
                return new Promise((resolve) => {
                    processResolvers.push(resolve);
                });
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    // Session 1: Open, go to Step 4, and start /api/process (stays pending)
    wizard.open({ query: 'Film Eins', projectName: 'Film.Eins', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '1', name: 'Film Eins', year: '2020', provider: 'manual' }, false);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));

    const executeBtn = doc.getElementById('mw-wizard-btn-execute');
    executeBtn.click();
    assert.equal(processCalls.length, 1);
    assert.equal(executeBtn.disabled, true);

    // Normal close() and close button click must be blocked while /api/process is running
    assert.equal(wizard.close(), false);
    doc.getElementById('mw-wizard-close').click();
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // Even if force-closed and reopened for Session 2 while Session 1's /api/process is still pending:
    wizard.close({ force: true });
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);
    wizard.open({ query: 'Film Zwei', projectName: 'Film.Zwei', autoSearch: false });
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);
    await wizard.selectMovieInWizard({ id: '2', name: 'Film Zwei', year: '2021', provider: 'manual' }, false);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));

    // Execute button in Session 2 must remain disabled while Session 1's /api/process is still in flight
    assert.equal(executeBtn.disabled, true);
    executeBtn.click();
    assert.equal(await wizard.executeStep4Process(), null);
    assert.equal(processCalls.length, 1);

    // Now Session 1's delayed /api/process response arrives: must NOT close Session 2's wizard, and must unlock executeBtn for Session 2
    processResolvers[0]({ ok: true, status: 200, json: async () => ({ status: 'started' }) });
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);
    assert.equal(executeBtn.disabled, false);
    assert.equal(executeBtn.textContent, 'Jetzt final verarbeiten');

    // Now Session 2 can execute its own /api/process and closes upon completion
    executeBtn.click();
    assert.equal(processCalls.length, 2);
    assert.equal(processCalls[1].movie_name, 'Film Zwei (2021)');
    processResolvers[1]({ ok: true, status: 200, json: async () => ({ status: 'started' }) });
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), true);
});

test('Handtest 2026-11-09: options group is open with a header summary that follows changes, and long plots are clamped with a toggle', async () => {
    const { doc } = createWizardMockDom();
    const wizard = createFilmWizard({
        document: doc,
        fetch: async () => ({
            ok: true,
            status: 200,
            json: async () => ({ destination: '/mnt/nas/Filme/Jaws (1975)', renames: [], subs: [], junk: [] }),
        }),
    });

    wizard.open({ query: 'Jaws', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '578', name: 'Der weiße Hai', year: '1975', provider: 'manual' }, false);
    wizard.nfoEditor.elements.plot.value = 'Ein weißer Hai terrorisiert eine Badeinsel. '.repeat(6);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));

    // Options are visible without an extra click
    assert.equal(doc.getElementById('mw-wizard-group-options').classList.contains('collapsed'), false);
    assert.equal(doc.getElementById('mw-wizard-options-content').classList.contains('hidden'), false);

    // Header summary reflects the current choices and follows changes
    const summary = doc.getElementById('mw-wizard-options-summary');
    const optDelete = doc.getElementById('mw-wizard-option-delete');
    optDelete.checked = true;
    optDelete.dispatchEvent({ type: 'change' });
    assert.match(summary.textContent, /Original löschen/);
    optDelete.checked = false;
    optDelete.dispatchEvent({ type: 'change' });
    assert.match(summary.textContent, /Original behalten/);

    // Long plot is clamped; the toggle expands and collapses it again
    const plotEl = doc.getElementById('mw-wizard-summary-plot');
    const toggle = doc.getElementById('mw-wizard-summary-plot-toggle');
    assert.equal(plotEl.classList.contains('clamped'), true);
    toggle.click();
    assert.equal(plotEl.classList.contains('clamped'), false);
    assert.equal(toggle.textContent, 'weniger');
    toggle.click();
    assert.equal(plotEl.classList.contains('clamped'), true);
});

test('Handtest 2026-11-09 (2): existing NFO is offered as junk with a hint, NAS/pCloud targets sit next to the destination, and the size forecast follows the slider', async () => {
    const { doc } = createWizardMockDom();
    const calls = [];
    let estimateCalls = 0;
    const wizard = createFilmWizard({
        document: doc,
        fetch: async (url, opts) => {
            calls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
            if (url === '/api/estimate-conversion') {
                estimateCalls += 1;
                return { ok: true, status: 200, json: async () => ({ estimates: { 'Alien.1979.mkv': { size_in: 4000, size_out: 1000 } } }) };
            }
            if (url === '/api/process') return { ok: true, status: 200, json: async () => ({ success: true }) };
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    destination: 'NAS: /media/Filme/Alien (1979)',
                    renames: [{ old: 'Alien.1979.mkv', new: 'Alien (1979).mkv' }],
                    subs: [
                        { old: 'Alien.1979.nfo', new: 'Alien (1979).nfo' },
                        { old: 'Alien.1979.de.srt', new: 'Alien (1979).de.srt' },
                    ],
                    junk: [],
                }),
            };
        },
    });

    wizard.open({ query: 'Alien', projectName: 'Alien.1979', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '348', name: 'Alien', year: '1979', provider: 'manual' }, false);
    doc.getElementById('mw-wizard-option-convert').checked = true;
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));

    // NFO moved from extras to junk, with a visible hint; subtitles stay in "Untertitel & Extras"
    assert.equal(doc.getElementById('mw-wizard-group-title-subs').textContent, 'Untertitel & Extras (1)');
    assert.equal(doc.getElementById('mw-wizard-group-title-junk').textContent, 'Junk-Dateien (1)');
    assert.match(doc.getElementById('mw-wizard-junk-nfo-note').textContent, /automatisch durch die neue NFO/);

    // Targets are part of the summary card (next to the destination), not of the options group
    const optionsContent = doc.getElementById('mw-wizard-options-content');
    const targets = doc.getElementById('mw-wizard-targets');
    assert.ok(targets.querySelectorAll('#mw-wizard-option-copy-nas').length === 1);
    assert.equal(optionsContent.querySelectorAll('#mw-wizard-option-copy-nas').length, 0);

    // Size forecast ran with the video files from the preview and shows up in the header summary
    const estimateCall = calls.find((c) => c.url === '/api/estimate-conversion');
    assert.deepEqual(estimateCall.body.filenames, ['Alien.1979.mkv']);
    assert.equal(estimateCall.body.project_name, 'Alien.1979');
    assert.match(doc.getElementById('mw-wizard-size-estimate').textContent, /-75%/);
    assert.match(doc.getElementById('mw-wizard-options-summary').textContent, /~/);

    // Moving the slider does not re-estimate; releasing it does
    const slider = doc.getElementById('mw-wizard-quality-slider');
    slider.value = '40';
    slider.dispatchEvent({ type: 'input' });
    assert.equal(estimateCalls, 1);
    slider.dispatchEvent({ type: 'change' });
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(estimateCalls, 2);

    // Payload: NFO goes to explicit_junk, not to explicit_subs
    await wizard.executeStep4Process();
    const processCall = calls.find((c) => c.url === '/api/process');
    assert.deepEqual(processCall.body.explicit_junk, ['Alien.1979.nfo']);
    assert.deepEqual(processCall.body.explicit_subs, [{ old: 'Alien.1979.de.srt', new: 'Alien (1979).de.srt' }]);
});

function createEstimateHarness(estimateResponder) {
    const { doc } = createWizardMockDom();
    const legacySlider = doc.createElement('input');
    legacySlider.id = 'movie-quality-slider';
    let legacyChangeEvents = 0;
    legacySlider.addEventListener('change', () => { legacyChangeEvents += 1; });
    let legacyInputEvents = 0;
    legacySlider.addEventListener('input', () => { legacyInputEvents += 1; });
    doc.body.appendChild(legacySlider);

    const estimateCalls = [];
    const logs = [];
    let persistCalls = 0;
    let previewDestination = 'NAS: /media/Filme/Alien (1979)';
    const wizard = createFilmWizard({
        document: doc,
        onLog: (msg) => logs.push(msg),
        onPersistOptions: () => { persistCalls += 1; },
        fetch: async (url, opts) => {
            if (url === '/api/estimate-conversion') {
                const body = JSON.parse(opts.body);
                estimateCalls.push(body);
                return estimateResponder(body, estimateCalls.length);
            }
            return {
                ok: true,
                status: 200,
                json: async () => ({ destination: previewDestination, renames: [{ old: 'Alien.1979.ts', new: 'Alien (1979).ts' }], subs: [], junk: [] }),
            };
        },
    });
    const flush = () => new Promise((r) => setTimeout(r, 0));
    const enterStep4 = async () => {
        wizard.open({ query: 'Alien', projectName: 'Alien.1979', autoSearch: false });
        await wizard.selectMovieInWizard({ id: '348', name: 'Alien', year: '1979', provider: 'manual' }, false);
        doc.getElementById('mw-wizard-option-convert').checked = true;
        wizard.goToStep(4);
        await flush();
        await flush();
    };
    return {
        doc, wizard, estimateCalls, logs, flush, enterStep4,
        getLegacyChangeEvents: () => legacyChangeEvents,
        getLegacyInputEvents: () => legacyInputEvents,
        getPersistCalls: () => persistCalls,
        estimateEl: () => doc.getElementById('mw-wizard-size-estimate'),
    };
}

const okEstimate = (sizeIn, sizeOut) => ({ ok: true, status: 200, json: async () => ({ estimates: { 'Alien.1979.ts': { size_in: sizeIn, size_out: sizeOut } } }) });

test('Review R1: size forecast error paths are visible and never block execution; per-file errors show the reason', async (t) => {
    await t.test('HTTP error', async () => {
        const harness = createEstimateHarness(() => ({ ok: false, status: 500, json: async () => ({}) }));
        await harness.enterStep4();
        assert.deepEqual(harness.estimateCalls[0].filenames, ['Alien.1979.ts']);
        assert.match(harness.estimateEl().textContent, /Größenprognose fehlgeschlagen \(HTTP 500\)/);
        assert.ok(harness.logs.some((msg) => /Größenprognose im Film-Assistenten fehlgeschlagen/.test(msg)));
        assert.equal(harness.doc.getElementById('mw-wizard-btn-execute').disabled, false);
    });
    await t.test('per-file error', async () => {
        const harness = createEstimateHarness(() => ({ ok: true, status: 200, json: async () => ({ estimates: { 'Alien.1979.ts': { error: 'ffmpeg timeout' } } }) }));
        await harness.enterStep4();
        assert.equal(harness.estimateEl().textContent, 'Größenprognose nicht verfügbar (ffmpeg timeout).');
    });
    await t.test('H.265 off: no request, element hidden', async () => {
        const harness = createEstimateHarness(() => okEstimate(4000, 1000));
        await harness.enterStep4();
        const convert = harness.doc.getElementById('mw-wizard-option-convert');
        convert.checked = false;
        convert.dispatchEvent({ type: 'change' });
        await harness.flush();
        assert.equal(harness.estimateCalls.length, 1);
        assert.equal(harness.estimateEl().classList.contains('hidden'), true);
        assert.doesNotMatch(harness.doc.getElementById('mw-wizard-options-summary').textContent, /~/);
    });
});

test('Review R1: slider mirrors to the legacy slider without change events, forecasts are cached and stale answers discarded', async () => {
    let releaseFirst;
    const harness = createEstimateHarness((body, callNo) => {
        if (callNo === 1) return new Promise((resolve) => { releaseFirst = () => resolve(okEstimate(4000, 3000)); });
        return okEstimate(4000, 1000);
    });
    await harness.enterStep4();

    // Dragging: no mirror events, no persist, no new forecast
    const slider = harness.doc.getElementById('mw-wizard-quality-slider');
    slider.value = '40';
    slider.dispatchEvent({ type: 'input' });
    assert.equal(harness.getLegacyChangeEvents(), 0);
    assert.equal(harness.getPersistCalls(), 0);
    assert.equal(harness.estimateCalls.length, 1);

    // Release: value mirrored without change event (no legacy ffmpeg estimate), settings persisted, new forecast
    slider.dispatchEvent({ type: 'change' });
    await harness.flush();
    assert.equal(harness.doc.getElementById('movie-quality-slider').value, '40');
    assert.equal(harness.getLegacyChangeEvents(), 0);
    assert.equal(harness.getPersistCalls(), 1);
    // Legacy label/hints refresh via a single input event on release (no legacy estimate)
    assert.equal(harness.getLegacyInputEvents(), 1);
    assert.equal(harness.estimateCalls.length, 2);
    assert.match(harness.estimateEl().textContent, /-75%/);

    // The late answer of the first (60 %) forecast is discarded
    releaseFirst();
    await harness.flush();
    assert.match(harness.estimateEl().textContent, /-75%/);

    // Preview reload with unchanged project/files/quality reuses the cached forecast
    const nasDest = harness.doc.getElementById('mw-wizard-nas-destination');
    nasDest.dispatchEvent({ type: 'change' });
    await harness.flush();
    await harness.flush();
    assert.equal(harness.estimateCalls.length, 2);
    assert.match(harness.estimateEl().textContent, /-75%/);
});

test('Review R1: a forecast still running when the wizard closes does not leak into the next session', async () => {
    let releaseFirst;
    const harness = createEstimateHarness((body, callNo) => {
        if (callNo === 1) return new Promise((resolve) => { releaseFirst = () => resolve(okEstimate(4000, 2000)); });
        return { ok: false, status: 503, json: async () => ({}) };
    });
    await harness.enterStep4();
    harness.wizard.close({ force: true });
    harness.wizard.open({ query: 'Alien', projectName: 'Alien.1979', autoSearch: false });
    releaseFirst();
    await harness.flush();
    assert.equal(harness.estimateEl().textContent, '');
    assert.equal(harness.estimateEl().classList.contains('hidden'), true);
    assert.doesNotMatch(harness.doc.getElementById('mw-wizard-options-summary').textContent, /~/);
});

test('Handtest 2026-11-09 (3): closing the wizard or starting the process calls onClosed (back to the start page); an aborted close does not', async () => {
    const { doc } = createWizardMockDom();
    let closedCalls = 0;
    let confirmAnswer = false;
    const wizard = createFilmWizard({
        document: doc,
        confirm: () => confirmAnswer,
        onClosed: () => { closedCalls += 1; },
        fetch: async (url) => {
            if (url === '/api/process') return { ok: true, status: 200, json: async () => ({ success: true }) };
            return { ok: true, status: 200, json: async () => ({ destination: '/mnt/nas/Filme/Jaws (1975)', renames: [], subs: [], junk: [] }) };
        },
    });

    // Plain close via ×/ESC in step 1
    wizard.open({ query: 'Jaws', projectName: 'Jaws.1975', autoSearch: false });
    assert.equal(wizard.close(), true);
    assert.equal(closedCalls, 1);

    // Dirty close that the user cancels: stays open, no navigation
    wizard.open({ query: 'Jaws', projectName: 'Jaws.1975', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '578', name: 'Der weiße Hai', year: '1975', provider: 'manual' }, false);
    wizard.nfoEditor.elements.title.value = 'Geändert';
    confirmAnswer = false;
    assert.equal(wizard.close(), false);
    assert.equal(closedCalls, 1);

    // Successful process start closes the wizard and navigates
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    await wizard.executeStep4Process();
    assert.equal(closedCalls, 2);
});

test('Handtest 2026-11-09 (4): completed steps show a check mark, active and open steps keep their number', async () => {
    const { doc } = createWizardMockDom();
    const wizard = createFilmWizard({ document: doc, fetch: async () => ({ ok: true, status: 200, json: async () => ({ destination: '', renames: [], subs: [], junk: [] }) }) });
    wizard.open({ query: 'Jaws', autoSearch: false });
    wizard.goToStep(3);
    const dots = doc.getElementById('mw-wizard-stepper').children.map((item) => item.children[0]);
    assert.deepEqual(dots.map((dot) => dot.textContent), ['✓', '✓', '3', '4']);
    assert.equal(dots[0].classList.contains('completed'), true);
    wizard.goToStep(1);
    assert.deepEqual(dots.map((dot) => dot.textContent), ['1', '2', '3', '4']);
});

test('Review R2: a preview reload while a forecast is running reuses the pending request instead of starting a second test run', async () => {
    let releaseFirst;
    const harness = createEstimateHarness(() => new Promise((resolve) => { releaseFirst = () => resolve(okEstimate(4000, 2000)); }));
    await harness.enterStep4();
    assert.equal(harness.estimateCalls.length, 1);
    assert.match(harness.estimateEl().textContent, /läuft/);

    harness.doc.getElementById('mw-wizard-nas-destination').dispatchEvent({ type: 'change' });
    await harness.flush();
    await harness.flush();
    assert.equal(harness.estimateCalls.length, 1);

    releaseFirst();
    await harness.flush();
    await harness.flush();
    assert.match(harness.estimateEl().textContent, /-50%/);
    assert.match(harness.doc.getElementById('mw-wizard-options-summary').textContent, /~/);
});

test('Review R3: closing while /api/process is still running is refused and does not navigate', async () => {
    const { doc } = createWizardMockDom();
    let closedCalls = 0;
    let releaseProcess;
    const wizard = createFilmWizard({
        document: doc,
        onClosed: () => { closedCalls += 1; },
        fetch: async (url) => {
            if (url === '/api/process') return new Promise((resolve) => { releaseProcess = () => resolve({ ok: true, status: 200, json: async () => ({ success: true }) }); });
            return { ok: true, status: 200, json: async () => ({ destination: '/mnt/nas/Filme/Jaws (1975)', renames: [], subs: [], junk: [] }) };
        },
    });
    wizard.open({ query: 'Jaws', projectName: 'Jaws.1975', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '578', name: 'Der weiße Hai', year: '1975', provider: 'manual' }, false);
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    const processPromise = wizard.executeStep4Process();
    assert.equal(wizard.close(), false);
    assert.equal(closedCalls, 0);
    releaseProcess();
    await processPromise;
    assert.equal(closedCalls, 1);
});

test('E3-AK3: #btn-open-film-wizard removed, #mode-movie keeps #context-movie hidden and opens Wizard for regular films while showing Doku view for Dokus, and scanProject only calls selectMovie for Dokus', async () => {
    const indexHtml = fs.readFileSync(path.join(__dirname, '../../gui/static/index.html'), 'utf8');
    assert.equal(indexHtml.includes('btn-open-film-wizard'), false, '#btn-open-film-wizard removed from index.html');
    assert.equal(indexHtml.includes('mw-wizard-context-bar'), false, '.mw-wizard-context-bar removed from index.html');
    assert.match(indexHtml, /<h3 id="context-movie-header" class="mt-0">Doku verarbeiten<\/h3>/);

    const { doc: appDoc } = createWizardMockDom();
    appDoc.documentElement = appDoc.createElement('html');
    const origGetEl = appDoc.getElementById.bind(appDoc);
    const ensureEl = (id, tag = 'div') => {
        let el = origGetEl(id);
        if (!el) {
            el = appDoc.createElement(tag);
            el.id = id;
            appDoc.body.appendChild(el);
        }
        return el;
    };
    appDoc.getElementById = (id) => origGetEl(id) || ensureEl(id);

    const modeMovieCard = ensureEl('mode-movie', 'div');
    const contextMovie = ensureEl('context-movie', 'div');
    contextMovie.classList.add('context-panel', 'hidden');
    ensureEl('context-movie-header', 'h3');
    ensureEl('movie-nas-destination', 'select');
    ensureEl('movie-pcloud-destination', 'select');
    ensureEl('movie-search-query', 'input');
    ensureEl('modal-film-wizard', 'div');
    ensureEl('files-tbody', 'tbody');

    const wizardCalls = [];
    const searchMovieCalls = [];
    let scanDataPayload = {
        type: 'movie',
        is_doku: false,
        suggested_query: 'Arrival',
        metadata_id: '329865',
        metadata_provider: 'tmdb_movie',
        metadata_name: 'Arrival',
        files: ['Arrival.2016.mkv'],
    };

    const mockFetch = async (url) => {
        if (url.startsWith('/api/scan-project')) {
            return { ok: true, status: 200, json: async () => scanDataPayload };
        }
        if (url.startsWith('/api/search')) {
            searchMovieCalls.push(url);
            return { ok: true, status: 200, json: async () => [] };
        }
        return { ok: true, status: 200, json: async () => ({}) };
    };

    const appJsRaw = fs.readFileSync(path.join(__dirname, '../../gui/static/app.js'), 'utf8');
    const cleanAppJs = `
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
const osBasename = (p) => String(p || '');
const formatFskLabel = (f) => f;
const guessEpisodeNumber = () => 1;
const guessSeasonAndEpisode = () => null;
const cleanFilenameForManualTitle = (f) => f;
const fetchStats = () => Promise.resolve();
const fetchYoutubeSubscriptions = () => Promise.resolve();
const fetchSmartInboxSuggestions = () => Promise.resolve();
` + appJsRaw.replace(/import\s+[\s\S]*?from\s+['"].*?['"];?/g, '') + `
globalThis.__initViews = initViews;
globalThis.__testScanProject = async (proj) => { currentProject = proj; return scanProject(proj); };
globalThis.__getSelectedMovie = () => selectedMovie;
globalThis.__resetSelectedMovie = () => { selectedMovie = null; };
`;

    const sandbox = {
        document: appDoc,
        window: { fetch: mockFetch, scrollTo: () => {}, addEventListener: () => {} },
        fetch: mockFetch,
        localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} },
        setTimeout: (fn) => { if (typeof fn === 'function') fn(); return 0; },
        clearTimeout: () => {},
        setInterval: () => 0,
        clearInterval: () => {},
        alert: () => {},
        console: { log: () => {}, warn: () => {}, error: () => {} },
        EventSource: class { close() {} },
        AbortController,
        openFilmWizard: (opts) => wizardCalls.push(opts),
        renderPreviewData,
        collectPreviewSelection,
    };
    sandbox.globalThis = sandbox;
    vm.runInNewContext(cleanAppJs, sandbox);
    sandbox.__initViews();

    // 1. Regular movie scanProject -> clicks #mode-movie, opens Film Wizard, keeps #context-movie hidden, does NOT call selectMovie or searchMovie
    wizardCalls.length = 0;
    searchMovieCalls.length = 0;
    sandbox.__resetSelectedMovie();
    await sandbox.__testScanProject('Arrival.2016');
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(contextMovie.classList.contains('hidden'), true, '#context-movie stays hidden for regular movies');
    assert.equal(wizardCalls.length, 1, 'openFilmWizard called for regular movie');
    assert.equal(wizardCalls[0].projectName, 'Arrival.2016');
    assert.equal(searchMovieCalls.length, 0, 'searchMovie on #context-movie not called for regular movie');
    assert.equal(sandbox.__getSelectedMovie(), null, 'selectMovie not called for regular movie in scanProject');

    // 2. Doku movie scanProject -> un-hides #context-movie, sets header to "Doku verarbeiten", calls searchMovie and selectMovie
    scanDataPayload = {
        type: 'movie',
        is_doku: true,
        suggested_query: 'Planet Erde Doku',
        metadata_id: '999',
        metadata_provider: 'tmdb_movie',
        metadata_name: 'Planet Erde Doku',
        files: ['Planet.Erde.Doku.mkv'],
    };
    wizardCalls.length = 0;
    searchMovieCalls.length = 0;
    await sandbox.__testScanProject('Planet.Erde.Doku');
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(contextMovie.classList.contains('hidden'), false, '#context-movie visible for Doku');
    assert.equal(appDoc.getElementById('context-movie-header').textContent, 'Doku verarbeiten');
    assert.equal(wizardCalls.length, 0, 'openFilmWizard not called for Doku');
    assert.ok(searchMovieCalls.length >= 1, 'searchMovie called for Doku');
    assert.ok(sandbox.__getSelectedMovie(), 'selectMovie called for Doku in scanProject');
    assert.equal(sandbox.__getSelectedMovie().id, '999');
});
