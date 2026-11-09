import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createFilmWizard } from '../../gui/static/js/film_wizard.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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

    function makeElement(tagName) {
        const classes = new Set();
        const attrs = new Map();
        const listeners = {};
        let idVal = '';
        let classStr = '';

        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '',
            value: '',
            placeholder: '',
            textContent: '',
            rows: 0,
            children: [],
            ownerDocument: null,
            get id() {
                return idVal;
            },
            set id(v) {
                idVal = String(v || '');
                if (idVal) byId.set(idVal, el);
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
            },
            getAttribute(k) {
                return attrs.has(k) ? attrs.get(k) : null;
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
                (listeners.click || []).forEach((fn) => fn({ type: 'click', preventDefault() {} }));
            },
            dispatchEvent(evt) {
                (listeners[evt.type] || []).forEach((fn) => fn(evt));
            },
        };

        Object.defineProperty(el, 'innerHTML', {
            get() {
                return '';
            },
            set(v) {
                if (v === '') el.children.length = 0;
            },
        });
        return el;
    }

    const doc = {
        body: null,
        createElement(tag) {
            const el = makeElement(tag);
            el.ownerDocument = doc;
            return el;
        },
        getElementById(id) {
            return byId.get(id) || null;
        },
        addEventListener(type, fn) {
            docListeners[type] = docListeners[type] || [];
            docListeners[type].push(fn);
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
    let handoverResult = null;

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
        throw new Error(`Unexpected URL: ${url}`);
    };

    const wizard = createFilmWizard({
        document: doc,
        fetch: mockFetch,
        onHandover: (payload) => {
            handoverResult = payload;
        },
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

    // ESC in Step 4 must NOT close the modal
    doc.dispatchKeydown('Escape');
    assert.equal(wizard.modalOverlay.classList.contains('hidden'), false);

    // Handover delivers 5-key nfo_overrides.movie and wizard_overrides flag
    doc.getElementById('mw-wizard-btn-handover').click();
    assert.ok(handoverResult);
    assert.equal(handoverResult.wizard_overrides, true);
    assert.deepEqual(handoverResult.nfo_overrides, {
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
            // Real fetch_movie_nfo_data error format in mw_metadata.py (HTTP 200 with error key and empty fields)
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
        // Real fetch_movie_nfo_data success format with FSK 0
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

    // 1. Sofort-Übergabe while metadata fetch is still pending: unloaded fields are NOT sent as empty
    mode = 'pending';
    wizard.open({ query: 'Chihiro', autoSearch: false });
    wizard.selectMovieInWizard({ id: '129', name: 'Chihiros Reise', provider: 'tmdb' });
    const immediatePayload = wizard.triggerHandover();
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
    const errorPayload = wizard.triggerHandover();
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
    const clearedPayload = wizard.triggerHandover();
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
    const handover = wizard.getHandoverPayload();
    assert.equal(typeof handover.movie.id, 'string');
    assert.equal(handover.movie.id, '348');
    assert.equal(handover.nfo_overrides.movie.title, 'Alien - Das unheimliche Wesen aus einer fremden Welt');
    assert.equal(handover.nfo_overrides.movie.year, '1979');
    assert.equal(handover.nfo_overrides.movie.plot, 'WIZARD-PLOT-F5');
    assert.equal(handover.nfo_overrides.movie.fsk, '18');

    // Manual button shows "Metadaten manuell eintragen"
    wizard.open({ query: 'Das Boot', autoSearch: false });
    doc.getElementById('mw-wizard-manual-btn').click();
    assert.equal(badge.textContent, 'Metadaten manuell eintragen');
});
