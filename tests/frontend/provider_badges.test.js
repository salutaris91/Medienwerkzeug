import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderNfoEditor } from '../../gui/static/js/nfo_editor.js';
import { createFilmWizard } from '../../gui/static/js/film_wizard.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function createMockDom() {
    const byId = new Map();

    function registerRecursive(node) {
        if (!node) return;
        if (node.id) byId.set(node.id, node);
        if (Array.isArray(node._childNodes)) node._childNodes.forEach(registerRecursive);
    }

    function matchesSelector(el, sel) {
        if (!sel || !el) return false;
        const s = sel.trim();
        if (s.startsWith('#')) return el.id === s.slice(1);
        if (s.startsWith('.')) return el.classList && el.classList.contains(s.slice(1));
        return Boolean(el.tagName && el.tagName.toLowerCase() === s.toLowerCase());
    }

    function findDescendants(root, parts) {
        if (!parts || parts.length === 0) return [];
        const [first, ...rest] = parts;
        const matches = [];
        function walk(curr) {
            if (!curr || !Array.isArray(curr._childNodes)) return;
            for (const child of curr._childNodes) {
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

    function collectText(el) {
        let out = (el._textParts || []).join('');
        for (const ch of el._childNodes || []) out += collectText(ch);
        return out;
    }

    function createHtmlCollectionView(childNodes) {
        return new Proxy(childNodes, {
            get(target, prop, receiver) {
                if (prop === 'length') return target.length;
                if (prop === 'item') return (idx) => target[idx] || null;
                if (prop === 'push' || prop === 'pop' || prop === 'splice' || prop === 'shift' || prop === 'unshift') {
                    return undefined;
                }
                const val = Reflect.get(target, prop, receiver);
                return typeof val === 'function' ? val.bind(target) : val;
            },
            set(_target, prop) {
                if (prop === 'length' || /^\d+$/.test(String(prop))) {
                    throw new TypeError(`Cannot assign to read only property '${String(prop)}' of object '#<HTMLCollection>'`);
                }
                return false;
            },
        });
    }

    function makeElement(tagName) {
        const classes = new Set();
        const attrs = new Map();
        const listeners = {};
        const dataset = {};
        const childNodes = [];
        const childrenView = createHtmlCollectionView(childNodes);
        let idVal = '';

        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '',
            value: '',
            checked: false,
            disabled: false,
            placeholder: '',
            rows: 0,
            style: {},
            _childNodes: childNodes,
            _textParts: [],
            dataset,
            ownerDocument: null,
            get children() {
                return childrenView;
            },
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
                childNodes.length = 0;
                el._textParts = [str];
            },
            get className() {
                return Array.from(classes).join(' ');
            },
            set className(v) {
                classes.clear();
                String(v || '')
                    .split(/\s+/)
                    .filter(Boolean)
                    .forEach((c) => classes.add(c));
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
            appendChild(child) {
                childNodes.push(child);
                registerRecursive(child);
                return child;
            },
            addEventListener(type, fn) {
                listeners[type] = listeners[type] || [];
                listeners[type].push(fn);
            },
            click() {
                if (el.disabled) return;
                (listeners.click || []).forEach((fn) => fn({ type: 'click', target: el, preventDefault() {}, stopPropagation() {} }));
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
                return '';
            },
            set(v) {
                if (v === '') {
                    childNodes.length = 0;
                    el._textParts = [];
                }
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
        querySelectorAll(sel) {
            return doc.body ? doc.body.querySelectorAll(sel) : [];
        },
        querySelector(sel) {
            return doc.querySelectorAll(sel)[0] || null;
        },
        addEventListener() {},
    };
    doc.body = doc.createElement('body');
    return { doc };
}

test('E4-AK1 & Option 2A: setProviderComparison renders per-provider badges, marks empty fields ("TMDb: keine FSK", "OFDb: keine Daten"), fills gaps, unites genres, and switches values on click', () => {
    const { doc } = createMockDom();
    const container = doc.createElement('div');
    const editor = renderNfoEditor(container);

    editor.setProviderComparison({
        providers: {
            tmdb: {
                provider: 'tmdb',
                movie_id: '1200320',
                status: 'ok',
                error: null,
                fields: {
                    title: 'Killing Faith',
                    year: '2025',
                    plot: 'Ein Arzt begleitet eine Mutter durch die Wüste.',
                    fsk: '',
                    genres: ['Western', 'Drama'],
                },
            },
            ofdb: {
                provider: 'ofdb',
                movie_id: 'ofdb_391234_Killing-Faith',
                status: 'ok',
                error: null,
                fields: {
                    title: 'Killing Faith - Die letzte Versuchung',
                    year: '2025',
                    plot: '',
                    fsk: '16',
                    genres: ['Thriller', 'Drama'],
                },
            },
        },
        provider_order: ['tmdb', 'ofdb'],
    });

    // Gap filling (Option 2A): Plot from TMDb, FSK 16 filled from OFDb, Genres united from both
    const values = editor.getValues();
    assert.equal(values.title, 'Killing Faith');
    assert.equal(values.year, '2025');
    assert.equal(values.plot, 'Ein Arzt begleitet eine Mutter durch die Wüste.');
    assert.equal(values.fsk, '16');
    assert.deepEqual(values.genres, ['Western', 'Drama', 'Thriller']);

    // Check empty vs selected badges (ROADMAP #55)
    const fskTmdbBadge = editor.providerBadges.fsk.tmdb;
    const fskOfdbBadge = editor.providerBadges.fsk.ofdb;
    assert.equal(fskTmdbBadge.classList.contains('empty'), true);
    assert.equal(fskTmdbBadge.disabled, true);
    assert.match(fskTmdbBadge.textContent, /TMDb: keine FSK/);
    assert.equal(fskOfdbBadge.classList.contains('selected'), true);
    assert.match(fskOfdbBadge.textContent, /FSK 16/);

    const plotTmdbBadge = editor.providerBadges.plot.tmdb;
    const plotOfdbBadge = editor.providerBadges.plot.ofdb;
    assert.equal(plotTmdbBadge.classList.contains('selected'), true);
    assert.equal(plotOfdbBadge.classList.contains('empty'), true);
    assert.equal(plotOfdbBadge.disabled, true);
    assert.match(plotOfdbBadge.textContent, /OFDb: keine Daten/);

    // Clicking OFDb title badge switches title to OFDb's value and moves .selected
    const titleTmdbBadge = editor.providerBadges.title.tmdb;
    const titleOfdbBadge = editor.providerBadges.title.ofdb;
    assert.equal(titleTmdbBadge.classList.contains('selected'), true);
    titleOfdbBadge.click();
    assert.equal(editor.getValues().title, 'Killing Faith - Die letzte Versuchung');
    assert.equal(titleOfdbBadge.classList.contains('selected'), true);
    assert.equal(titleTmdbBadge.classList.contains('selected'), false);

    // Clicking Genre badge selects exclusively that provider's genres (e.g. clicking TMDb sets only TMDb genres without OFDb extras)
    const genreTmdbBadge = editor.providerBadges.genres.tmdb;
    const genreOfdbBadge = editor.providerBadges.genres.ofdb;
    const genreCombineBadge = editor.providerBadges.genres.all;
    assert.ok(genreCombineBadge);
    assert.equal(genreTmdbBadge.classList.contains('selected'), true);
    assert.equal(genreOfdbBadge.classList.contains('selected'), true);
    assert.equal(genreCombineBadge.classList.contains('selected'), true);
    genreTmdbBadge.click();
    assert.deepEqual(editor.getValues().genres, ['Western', 'Drama']);
    assert.equal(genreTmdbBadge.classList.contains('selected'), true);
    assert.equal(genreOfdbBadge.classList.contains('selected'), false);
    assert.equal(genreCombineBadge.classList.contains('selected'), false);

    // Clicking "Kombinieren · Beide Quellen" restores the deduplicated union of both providers
    genreCombineBadge.click();
    assert.deepEqual(editor.getValues().genres, ['Western', 'Drama', 'Thriller']);
    assert.equal(genreCombineBadge.classList.contains('selected'), true);

    // Clicking OFDb Genre badge switches to exclusively OFDb's genres, then back to TMDb
    genreOfdbBadge.click();
    assert.deepEqual(editor.getValues().genres, ['Thriller', 'Drama']);
    assert.equal(genreOfdbBadge.classList.contains('selected'), true);
    assert.equal(genreTmdbBadge.classList.contains('selected'), false);
    assert.equal(genreCombineBadge.classList.contains('selected'), false);
    genreTmdbBadge.click();
    assert.deepEqual(editor.getValues().genres, ['Western', 'Drama']);

    // buildWizardMovieOverrides includes all merged & chosen fields
    const overrides = editor.buildWizardMovieOverrides();
    assert.deepEqual(overrides, {
        movie: {
            title: 'Killing Faith - Die letzte Versuchung',
            year: '2025',
            plot: 'Ein Arzt begleitet eine Mutter durch die Wüste.',
            fsk: '16',
            genres: ['Western', 'Drama'],
        },
    });

    // Manual input clears .selected on that field's badges
    editor.elements.title.value = 'Killing Faith (Director Cut)';
    editor.elements.title.dispatchEvent({ type: 'input' });
    assert.equal(titleOfdbBadge.classList.contains('selected'), false);
    assert.equal(titleTmdbBadge.classList.contains('selected'), false);
});

test('E4-AK2 & Option 1A: 1-click search pairing in Step 1 and partial provider failure in Step 2 keep working provider selectable', async () => {
    const { doc } = createMockDom();
    const fetchCalls = [];

    const mockFetch = async (url, opts = {}) => {
        fetchCalls.push({ url, body: opts.body ? JSON.parse(opts.body) : null });
        if (url.startsWith('/api/search')) {
            return {
                ok: true,
                status: 200,
                json: async () => [
                    { id: '1200320', name: 'Killing Faith (2025)', provider: 'tmdb' },
                    { id: 'ofdb_391234_Killing-Faith', name: 'Killing Faith (2025)', provider: 'ofdb' },
                ],
            };
        }
        if (url.startsWith('/api/metadata/fetch')) {
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    providers: {
                        tmdb: {
                            provider: 'tmdb',
                            movie_id: '1200320',
                            status: 'ok',
                            error: null,
                            fields: {
                                title: 'Killing Faith',
                                year: '2025',
                                plot: 'Wüsten-Drama.',
                                fsk: '16',
                                genres: ['Western'],
                            },
                        },
                        ofdb: {
                            provider: 'ofdb',
                            movie_id: 'ofdb_391234_Killing-Faith',
                            status: 'error',
                            error: 'OFDb Timeout',
                            fields: { title: '', year: '', plot: '', fsk: '', genres: [] },
                        },
                    },
                    provider_order: ['tmdb', 'ofdb'],
                }),
            };
        }
        throw new Error(`Unexpected URL: ${url}`);
    };

    const wizard = createFilmWizard({ document: doc, fetch: mockFetch });
    wizard.open({ query: 'Killing Faith', autoSearch: false });
    await wizard.performSearch('Killing Faith');

    // Click first search row (TMDb) -> Option 1A automatically pairs matching OFDb item
    const searchRows = doc.getElementById('mw-wizard-search-results').querySelectorAll('.mw-wizard-search-item');
    assert.equal(searchRows.length, 2);
    searchRows[0].click();
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(wizard.getCurrentStep(), 2);
    const metaCall = fetchCalls.find((c) => c.url.startsWith('/api/metadata/fetch'));
    assert.ok(metaCall);
    assert.deepEqual(metaCall.body.providers, [
        { provider: 'tmdb', movie_id: '1200320' },
        { provider: 'ofdb', movie_id: 'ofdb_391234_Killing-Faith' },
    ]);

    // E4-AK2: OFDb badge is marked .error ("OFDb: nicht erreichbar"), TMDb badge is .selected and editable
    const titleTmdbBadge = wizard.nfoEditor.providerBadges.title.tmdb;
    const titleOfdbBadge = wizard.nfoEditor.providerBadges.title.ofdb;
    assert.equal(titleTmdbBadge.classList.contains('selected'), true);
    assert.equal(titleOfdbBadge.classList.contains('error'), true);
    assert.equal(titleOfdbBadge.disabled, true);
    assert.match(titleOfdbBadge.textContent, /OFDb: nicht erreichbar/);

    // Partial failure banner is shown, header badge indicates Teil-Erfolg, and TMDb values are populated
    assert.equal(doc.getElementById('mw-wizard-error-banner').classList.contains('hidden'), false);
    assert.match(doc.getElementById('mw-wizard-provider-badge').textContent, /Teil-Erfolg/);
    assert.equal(wizard.nfoEditor.getValues().title, 'Killing Faith');
    assert.equal(wizard.nfoEditor.getValues().plot, 'Wüsten-Drama.');
});

test('E4 Option 1A Regression: going Back from Step 2 to Step 1 and selecting different items via checkboxes updates Step 2 on Next', async () => {
    const { doc } = createMockDom();
    const metaBodies = [];

    const mockFetch = async (url, opts = {}) => {
        if (url.startsWith('/api/search')) {
            return {
                ok: true,
                status: 200,
                json: async () => [
                    { id: '100', name: 'Film A (2020)', provider: 'tmdb' },
                    { id: '200', name: 'Film B (2024)', provider: 'tmdb' },
                    { id: 'ofdb_200_Film-B', name: 'Film B (2024)', provider: 'ofdb' },
                ],
            };
        }
        if (url.startsWith('/api/metadata/fetch')) {
            const body = opts.body ? JSON.parse(opts.body) : {};
            metaBodies.push(body);
            const isFilmB = body.providers && body.providers.some((p) => p.movie_id === '200');
            return {
                ok: true,
                status: 200,
                json: async () => ({
                    providers: isFilmB
                        ? {
                              tmdb: {
                                  provider: 'tmdb',
                                  movie_id: '200',
                                  status: 'ok',
                                  error: null,
                                  fields: { title: 'Film B', year: '2024', plot: 'Plot B', fsk: '', genres: ['Sci-Fi'] },
                              },
                              ofdb: {
                                  provider: 'ofdb',
                                  movie_id: 'ofdb_200_Film-B',
                                  status: 'ok',
                                  error: null,
                                  fields: { title: 'Film B (DE)', year: '2024', plot: '', fsk: '12', genres: ['Thriller'] },
                              },
                          }
                        : {
                              tmdb: {
                                  provider: 'tmdb',
                                  movie_id: '100',
                                  status: 'ok',
                                  error: null,
                                  fields: { title: 'Film A', year: '2020', plot: 'Plot A', fsk: '6', genres: ['Drama'] },
                              },
                          },
                    provider_order: isFilmB ? ['tmdb', 'ofdb'] : ['tmdb'],
                }),
            };
        }
        throw new Error(`Unexpected URL: ${url}`);
    };

    const wizard = createFilmWizard({ document: doc, fetch: mockFetch });
    wizard.open({ query: 'Film', autoSearch: false });
    await wizard.performSearch('Film');

    const rows = doc.getElementById('mw-wizard-search-results').querySelectorAll('.mw-wizard-search-item');
    assert.equal(rows.length, 3);

    // 1. Select Film A first by clicking row 0
    rows[0].click();
    await new Promise((r) => setTimeout(r, 0));
    assert.equal(wizard.getCurrentStep(), 2);
    assert.equal(wizard.nfoEditor.getValues().title, 'Film A');

    // 2. Navigate Back to Step 1, check comparison checkboxes for Film B (TMDb + OFDb), and press Next
    wizard.prevStep();
    assert.equal(wizard.getCurrentStep(), 1);

    const checkboxes = doc.getElementById('mw-wizard-search-results').querySelectorAll('.mw-wizard-compare-cb');
    checkboxes[1].checked = true;
    checkboxes[1].click();
    checkboxes[2].checked = true;
    checkboxes[2].click();

    wizard.nextStep();
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(wizard.getCurrentStep(), 2);
    assert.equal(metaBodies.length, 2);
    assert.deepEqual(metaBodies[1].providers, [
        { provider: 'tmdb', movie_id: '200' },
        { provider: 'ofdb', movie_id: 'ofdb_200_Film-B' },
    ]);
    assert.equal(wizard.nfoEditor.getValues().title, 'Film B');
    assert.equal(wizard.nfoEditor.getValues().fsk, '12');
    assert.deepEqual(wizard.nfoEditor.getValues().genres, ['Sci-Fi', 'Thriller']);
});

test('E4 Theme & Parcours verification: all 5 themes define all CSS variables used by provider badge rules', () => {
    const stylePath = path.resolve(__dirname, '../../gui/static/style.css');
    const css = fs.readFileSync(stylePath, 'utf8');

    // Verify all 5 themes exist in style.css
    for (const theme of [
        'theme-deep-space',
        'theme-nordic-slate',
        'theme-amber-warmth',
        'theme-apple-black',
        'theme-superfood-light',
    ]) {
        assert.ok(css.includes(`body.${theme}`), `Missing theme selector body.${theme}`);
    }

    // Extract the E4 badge & checkbox CSS block and verify it uses only CSS custom properties (no raw hex colors)
    const e4Start = css.indexOf('.mw-wizard-search-item-main');
    const e4End = css.indexOf('@media (max-width: 700px)', e4Start);
    assert.ok(e4Start > 0 && e4End > e4Start, 'E4 badge CSS block present in style.css');
    const e4Block = css.slice(e4Start, e4End);
    for (const selector of [
        '.mw-wizard-field-badges',
        '.mw-wizard-provider-badge',
        '.mw-wizard-provider-badge.selected',
        '.mw-wizard-provider-badge.empty',
        '.mw-wizard-provider-badge.error',
        '.mw-wizard-provider-name',
        '.mw-wizard-provider-value',
        '.mw-wizard-compare-cb',
    ]) {
        assert.ok(e4Block.includes(selector), `Missing selector ${selector} in style.css`);
    }
    assert.equal(/#[0-9a-fA-F]{3,8}\b/.test(e4Block), false, 'E4 badge CSS must not contain hardcoded hex colors');
});
