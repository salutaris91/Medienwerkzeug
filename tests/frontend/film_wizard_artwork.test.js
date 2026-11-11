import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createFilmWizard } from '../../gui/static/js/film_wizard.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const VOID_TAGS = new Set(['img', 'input', 'br', 'hr', 'source', 'meta', 'link']);

function createArtworkMockDom(initialHtml = '') {
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
                stack[stack.length - 1]._textParts.push(match[4]);
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
            const attrRegex = /([a-z0-9\-:]+)=["']([^"']*)["']/gi;
            let aMatch;
            while ((aMatch = attrRegex.exec(attrStr)) !== null) {
                const k = aMatch[1];
                const v = aMatch[2];
                if (k === 'class') el.className = v;
                else if (k === 'id') el.id = v;
                else el.setAttribute(k, v);
            }
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
        let innerHtmlVal = '';

        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '',
            value: '',
            src: '',
            alt: '',
            checked: false,
            disabled: false,
            placeholder: '',
            files: [],
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
                classes.clear();
                String(v || '').split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
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
                if (k === 'src') el.src = String(v);
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
                (listeners.click || []).forEach((fn) => fn({ type: 'click', preventDefault() {}, stopPropagation() {} }));
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
    };
    doc.body = doc.createElement('body');
    if (initialHtml) {
        doc.body.innerHTML = initialHtml;
    }
    return { doc };
}

function makeBackendCandidatesResponse(overrides = {}) {
    return {
        tmdb_id: '603',
        matched_title: 'Matrix (1999)',
        matches: [
            { id: '603', name: 'Matrix (1999)' },
            { id: '604', name: 'Matrix Reloaded (2003)' },
        ],
        posters: [
            {
                url: 'https://image.tmdb.org/t/p/original/poster_de.jpg',
                thumb_url: 'https://image.tmdb.org/t/p/w185/poster_de.jpg',
                lang: 'de',
                width: 1000,
                height: 1500,
            },
            {
                url: 'https://image.tmdb.org/t/p/original/poster_en.jpg',
                thumb_url: 'https://image.tmdb.org/t/p/w185/poster_en.jpg',
                lang: 'en',
                width: 1000,
                height: 1500,
            },
        ],
        backdrops: [
            {
                url: 'https://image.tmdb.org/t/p/original/fanart_neutral.jpg',
                thumb_url: 'https://image.tmdb.org/t/p/w300/fanart_neutral.jpg',
                lang: '',
                width: 1920,
                height: 1080,
            },
        ],
        logos: [
            {
                url: 'https://image.tmdb.org/t/p/original/logo_de.png',
                thumb_url: 'https://image.tmdb.org/t/p/w185/logo_de.png',
                lang: 'de',
                width: 800,
                height: 300,
            },
        ],
        ...overrides,
    };
}

test('E5-AK1 & Option 3A: Step 3 consumes exact backend contract (posters/backdrops/logos, thumb_url, lang, matched_title, matches.id), renders loading/empty/check UI, and enforces 1 selection state per role', async () => {
    const { doc } = createArtworkMockDom();
    let resolveCandidatesFetch = null;
    const requestedCandidateUrls = [];

    const wizard = createFilmWizard({
        document: doc,
        fetch: (url) => {
            if (url.startsWith('/api/metadata/fetch')) {
                return Promise.resolve({
                    ok: true,
                    status: 200,
                    json: async () => ({ title: 'Matrix', year: '1999', plot: 'Cyberpunk.', fsk: '16', genres: ['Sci-Fi'] }),
                });
            }
            if (url.startsWith('/api/artwork/candidates')) {
                requestedCandidateUrls.push(url);
                return new Promise((resolve) => {
                    resolveCandidatesFetch = resolve;
                });
            }
            return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
        },
    });

    wizard.open({ query: 'Matrix', projectName: 'Matrix.1999', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '603', name: 'Matrix (1999)', provider: 'tmdb' });
    wizard.goToStep(3);

    const posterPanel = doc.getElementById('mw-wizard-artwork-poster');
    const fanartPanel = doc.getElementById('mw-wizard-artwork-fanart');
    const logoPanel = doc.getElementById('mw-wizard-artwork-logo');

    // While loading, skeleton tiles (.mw-wizard-artwork-tile.loading + .mw-wizard-artwork-skeleton) are shown
    const loadingTiles = posterPanel.querySelectorAll('.mw-wizard-artwork-tile');
    assert.equal(loadingTiles.length, 3);
    assert.equal(loadingTiles[0].classList.contains('loading'), true);
    assert.ok(loadingTiles[0].querySelector('.mw-wizard-artwork-skeleton'));

    // Resolve with exact backend response contract (posters/backdrops/logos, matched_title, matches[{id, name}])
    resolveCandidatesFetch({
        ok: true,
        status: 200,
        json: async () => makeBackendCandidatesResponse({ logos: [] }),
    });
    await new Promise((r) => setTimeout(r, 0));

    // Source bar shows matched_title and match dropdown with m.id options
    const sourceInfo = doc.getElementById('mw-wizard-artwork-source-info');
    assert.match(sourceInfo.textContent, /Matrix \(1999\) · #603/);
    const matchSelect = doc.getElementById('mw-wizard-artwork-match-select');
    assert.equal(matchSelect.classList.contains('hidden'), false);
    const matchOptions = matchSelect.querySelectorAll('option');
    assert.equal(matchOptions.length, 2);
    assert.equal(matchOptions[0].getAttribute('value'), '603');
    assert.equal(matchOptions[1].getAttribute('value'), '604');

    // Verify thumbnails (thumb_url w185/w300, not original), language badges (lang -> DE/EN/Neutral), and checkmark span
    const posterTiles = posterPanel.querySelectorAll('.mw-wizard-artwork-tile');
    assert.equal(posterTiles.length, 2);
    assert.equal(posterTiles[0].getAttribute('aria-pressed'), 'true');
    assert.equal(posterTiles[0].classList.contains('selected'), true);
    assert.equal(posterTiles[1].getAttribute('aria-pressed'), 'false');
    assert.equal(
        posterTiles[0].querySelector('.mw-wizard-artwork-image').getAttribute('src'),
        'https://image.tmdb.org/t/p/w185/poster_de.jpg'
    );
    assert.equal(posterTiles[0].querySelector('.mw-wizard-artwork-meta').textContent, 'DE · 1000×1500');
    assert.equal(posterTiles[1].querySelector('.mw-wizard-artwork-meta').textContent, 'EN · 1000×1500');
    assert.equal(posterTiles[0].querySelector('.mw-wizard-artwork-check').textContent, '✓');

    const fanartTiles = fanartPanel.querySelectorAll('.mw-wizard-artwork-tile');
    assert.equal(
        fanartTiles[0].querySelector('.mw-wizard-artwork-image').getAttribute('src'),
        'https://image.tmdb.org/t/p/w300/fanart_neutral.jpg'
    );
    assert.equal(fanartTiles[0].querySelector('.mw-wizard-artwork-meta').textContent, 'Neutral · 1920×1080');

    // Empty role renders .mw-wizard-artwork-tile.empty
    const emptyLogoTiles = logoPanel.querySelectorAll('.mw-wizard-artwork-tile');
    assert.equal(emptyLogoTiles.length, 1);
    assert.equal(emptyLogoTiles[0].classList.contains('empty'), true);
    assert.match(emptyLogoTiles[0].textContent, /Kein Logo bei TMDb verfügbar/);

    // For a TMDb movie without any explicit user selection in Step 3, artwork_overrides MUST be omitted
    assert.equal(wizard.buildMovieBasePayload().artwork_overrides, undefined);

    // Click second poster tile -> selects second and deselects first (strictly 1 selected)
    posterTiles[1].click();
    const posterTilesAfter = posterPanel.querySelectorAll('.mw-wizard-artwork-tile');
    assert.equal(posterTilesAfter.filter((t) => t.getAttribute('aria-pressed') === 'true').length, 1);
    assert.equal(posterTilesAfter[1].getAttribute('aria-pressed'), 'true');

    //Untouched roles on a TMDb movie stay 'auto' while explicitly changed poster is 'url'
    assert.deepEqual(wizard.buildMovieBasePayload().artwork_overrides, {
        poster: { mode: 'url', url: 'https://image.tmdb.org/t/p/original/poster_en.jpg' },
        backdrop: { mode: 'auto' },
        logo: { mode: 'auto' },
    });

    // Switch to Logo tab and explicitly deselect via button ("Kein Bild für diese Rolle")
    const tabLogo = doc.getElementById('mw-wizard-tab-logo');
    const tabFanart = doc.getElementById('mw-wizard-tab-fanart');
    const deselectBtn = doc.getElementById('mw-wizard-artwork-deselect-btn');
    tabLogo.click();
    assert.equal(wizard.getActiveArtworkTab(), 'logo');
    deselectBtn.click();
    assert.equal(deselectBtn.getAttribute('aria-pressed'), 'true');

    // Clicking selected Fanart tile again also deselects it to "none"
    tabFanart.click();
    fanartPanel.querySelectorAll('.mw-wizard-artwork-tile')[0].click();
    assert.equal(fanartPanel.querySelectorAll('.mw-wizard-artwork-tile').filter((t) => t.getAttribute('aria-pressed') === 'true').length, 0);
    assert.equal(deselectBtn.getAttribute('aria-pressed'), 'true');

    assert.deepEqual(wizard.buildMovieBasePayload().artwork_overrides, {
        poster: { mode: 'url', url: 'https://image.tmdb.org/t/p/original/poster_en.jpg' },
        backdrop: { mode: 'none' },
        logo: { mode: 'none' },
    });

    // Selecting a different movie in the match dropdown reloads candidates for that ID
    matchSelect.value = '604';
    matchSelect.dispatchEvent({ type: 'change' });
    resolveCandidatesFetch({
        ok: true,
        status: 200,
        json: async () => makeBackendCandidatesResponse({ tmdb_id: '604', matched_title: 'Matrix Reloaded (2003)' }),
    });
    await new Promise((r) => setTimeout(r, 0));
    assert.match(requestedCandidateUrls[1], /tmdb_id=604/);
});

test('Payload rules: OFDb/Manual movies transmit preselected TMDb candidates, TMDb without explicit edit omits artwork_overrides, and Skip omits artwork_overrides', async () => {
    const { doc } = createArtworkMockDom();
    const candidateUrls = [];
    const wizard = createFilmWizard({
        document: doc,
        fetch: async (url) => {
            if (url.startsWith('/api/artwork/candidates')) {
                candidateUrls.push(url);
                return {
                    ok: true,
                    status: 200,
                    json: async () => makeBackendCandidatesResponse(),
                };
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    // 1. OFDb movie enters Step 3 -> preselected TMDb candidates ARE included in payload even without clicking a tile
    wizard.open({ query: 'Matrix', projectName: 'Matrix.1999', autoSearch: false });
    await wizard.selectMovieInWizard(
        { id: 'https://ofdb.de/film/154,Die-Matrix', name: 'Matrix', title: 'Matrix', year: '1999', provider: 'ofdb' },
        false
    );
    wizard.goToStep(3);
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(candidateUrls.length, 1);
    assert.match(candidateUrls[0], /query=Matrix/);
    assert.match(candidateUrls[0], /year=1999/);

    const ofdbPayload = wizard.buildMovieBasePayload();
    assert.equal(ofdbPayload.provider, 'ofdb');
    assert.deepEqual(ofdbPayload.artwork_overrides, {
        poster: { mode: 'url', url: 'https://image.tmdb.org/t/p/original/poster_de.jpg' },
        backdrop: { mode: 'url', url: 'https://image.tmdb.org/t/p/original/fanart_neutral.jpg' },
        logo: { mode: 'url', url: 'https://image.tmdb.org/t/p/original/logo_de.png' },
    });

    // 2. Clicking "Überspringen" in Step 3 sets artworkSkipped and omits artwork_overrides
    doc.getElementById('mw-wizard-btn-skip').click();
    assert.equal(wizard.getCurrentStep(), 4);
    assert.equal(wizard.buildMovieBasePayload().artwork_overrides, undefined);
});

test('Option 1A: Visible upload button click (static & dynamic DOM) and async FileReader with role/session guard and error handling', async () => {
    const validPngDataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';
    const origFileReader = globalThis.FileReader;
    const readerInstances = [];

    class ControlledFileReader {
        constructor() {
            this.result = null;
            this.onload = null;
            this.onerror = null;
            this.onabort = null;
            this.file = null;
            readerInstances.push(this);
        }
        readAsDataURL(file) {
            this.file = file;
        }
    }

    globalThis.FileReader = ControlledFileReader;
    try {
        // A. Verify static DOM from index.html wires #mw-wizard-artwork-upload-btn click to #mw-wizard-artwork-upload-input.click()
        const indexHtml = fs.readFileSync(path.join(__dirname, '../../gui/static/index.html'), 'utf8');
        const modalStart = indexHtml.indexOf('<div id="modal-film-wizard"');
        const modalSnippet = indexHtml.slice(modalStart, indexHtml.indexOf('<!--', modalStart));
        const { doc: staticDoc } = createArtworkMockDom(modalSnippet);
        createFilmWizard({
            document: staticDoc,
            fetch: async () => ({ ok: true, status: 200, json: async () => makeBackendCandidatesResponse() }),
        });
        let staticInputClicked = 0;
        staticDoc.getElementById('mw-wizard-artwork-upload-input').addEventListener('click', () => {
            staticInputClicked += 1;
        });
        staticDoc.getElementById('mw-wizard-artwork-upload-btn').click();
        assert.equal(staticInputClicked, 1, 'Clicking visible upload button in static index.html DOM must trigger file input click');

        // B. Dynamic DOM: test button click, async FileReader role-lock across tab switch, movie-session guard, and read error
        const { doc } = createArtworkMockDom();
        const logs = [];
        const wizard = createFilmWizard({
            document: doc,
            onLog: (msg) => logs.push(msg),
            fetch: async () => ({ ok: true, status: 200, json: async () => makeBackendCandidatesResponse() }),
        });

        wizard.open({ query: 'Matrix', projectName: 'Matrix.1999', autoSearch: false });
        await wizard.selectMovieInWizard({ id: '603', name: 'Matrix (1999)', provider: 'tmdb' }, false);
        wizard.goToStep(3);
        await new Promise((r) => setTimeout(r, 0));

        const uploadBtn = doc.getElementById('mw-wizard-artwork-upload-btn');
        const uploadInput = doc.getElementById('mw-wizard-artwork-upload-input');
        let dynamicInputClicked = 0;
        uploadInput.addEventListener('click', () => {
            dynamicInputClicked += 1;
        });
        uploadBtn.click();
        assert.equal(dynamicInputClicked, 1, 'Clicking visible upload button in dynamic DOM must trigger file input click');

        // 1. Start reading a Poster file on 'poster' tab, then switch to 'logo' tab BEFORE FileReader finishes
        assert.equal(wizard.getActiveArtworkTab(), 'poster');
        uploadInput.value = 'C:\\fakepath\\my-poster.png';
        uploadInput.files = [{ name: 'my-poster.png', type: 'image/png', size: 128 }];
        uploadInput.dispatchEvent({ type: 'change' });
        assert.equal(uploadInput.value, '', 'Upload input value must be cleared after reading file so re-selecting the same file fires change again');
        assert.equal(readerInstances.length, 1);
        const posterReader = readerInstances[0];

        doc.getElementById('mw-wizard-tab-logo').click();
        assert.equal(wizard.getActiveArtworkTab(), 'logo');

        posterReader.result = validPngDataUrl;
        posterReader.onload();

        // Image must be assigned to 'poster' (captured at upload start), NOT 'logo'
        const stateAfterTabRace = wizard.getArtworkState();
        assert.equal(stateAfterTabRace.poster.mode, 'upload');
        assert.equal(stateAfterTabRace.poster.selectedDataUrl, validPngDataUrl);
        assert.equal(stateAfterTabRace.logo.mode, 'url');

        // 2. Start reading a Logo file, then switch to another movie BEFORE FileReader finishes -> stale upload discarded
        uploadInput.files = [{ name: 'stale-logo.png', type: 'image/png', size: 128 }];
        uploadInput.dispatchEvent({ type: 'change' });
        assert.equal(readerInstances.length, 2);
        const staleReader = readerInstances[1];

        await wizard.selectMovieInWizard({ id: '604', name: 'Matrix Reloaded (2003)', provider: 'tmdb' }, false);
        staleReader.result = validPngDataUrl;
        staleReader.onload();

        const stateNewMovie = wizard.getArtworkState();
        assert.equal(stateNewMovie.logo.hasCustomUpload, false);
        assert.equal(stateNewMovie.logo.mode, 'auto');

        // 3. FileReader error is visibly reported in the active panel and source bar
        wizard.goToStep(3);
        await new Promise((r) => setTimeout(r, 0));
        doc.getElementById('mw-wizard-tab-poster').click();
        uploadInput.files = [{ name: 'corrupt.png', type: 'image/png', size: 256 }];
        uploadInput.dispatchEvent({ type: 'change' });
        const errorReader = readerInstances[readerInstances.length - 1];
        errorReader.onerror();

        const posterPanel = doc.getElementById('mw-wizard-artwork-poster');
        const uploadErrEl = posterPanel.querySelector('.mw-wizard-artwork-upload-error');
        assert.ok(uploadErrEl, 'Upload error notice must be rendered in the role panel');
        assert.match(uploadErrEl.textContent, /Fehler beim Lesen der Bilddatei/);
        assert.ok(logs.some((l) => l.includes('Fehler beim Lesen der Bilddatei')));
    } finally {
        globalThis.FileReader = origFileReader;
    }
});

test('E5-AK2 & E5-AK3: Candidate API failure and broken <img> error render retry placeholders without aborting Step 3; official TMDb SVG & CSP are present', async () => {
    const indexHtml = fs.readFileSync(path.join(__dirname, '../../gui/static/index.html'), 'utf8');
    assert.match(indexHtml, /id="mw-wizard-tmdb-attribution"/);
    assert.match(indexHtml, /id="mw-wizard-tmdb-logo"[^>]*role="img"[^>]*aria-label="TMDB"/);
    assert.match(indexHtml, /<path d="M10 7h12v3h-4\.5v7h-3v-7H10V7z/);
    assert.match(indexHtml, /This product uses the TMDB API but is not endorsed or certified by TMDB\./);
    assert.doesNotMatch(indexHtml, /Content-Security-Policy/i);

    const { doc } = createArtworkMockDom();
    let failApi = true;
    const wizard = createFilmWizard({
        document: doc,
        fetch: async (url) => {
            if (url.startsWith('/api/artwork/candidates')) {
                if (failApi) {
                    return { ok: false, status: 502, json: async () => ({ error: 'TMDb Timeout' }) };
                }
                return {
                    ok: true,
                    status: 200,
                    json: async () => makeBackendCandidatesResponse(),
                };
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    // Dynamic DOM also includes identical official TMDb vector SVG (rect, circle, path) and attribution text
    const attrEl = doc.getElementById('mw-wizard-tmdb-attribution');
    const logoSvg = doc.getElementById('mw-wizard-tmdb-logo');
    assert.ok(attrEl);
    assert.equal(logoSvg.getAttribute('role'), 'img');
    assert.equal(logoSvg.getAttribute('aria-label'), 'TMDB');
    assert.ok(logoSvg.querySelector('path'), 'Dynamic TMDb logo must contain official vector <path>');
    assert.ok(logoSvg.querySelector('circle'), 'Dynamic TMDb logo must contain official <circle>');
    assert.equal(logoSvg.querySelector('text'), null, 'Dynamic TMDb logo must not use a generic <text> placeholder');
    assert.match(attrEl.textContent, /This product uses the TMDB API but is not endorsed or certified by TMDB\./);

    // 1. API failure shows error tile with retry button inside Step 3 and keeps Step 3 open
    wizard.open({ query: 'Matrix', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '603', name: 'Matrix', year: '1999', provider: 'manual' }, false);
    wizard.goToStep(3);
    await new Promise((r) => setTimeout(r, 0));

    assert.equal(wizard.getCurrentStep(), 3);
    const posterPanel = doc.getElementById('mw-wizard-artwork-poster');
    const errTile = posterPanel.querySelector('.mw-wizard-artwork-tile');
    assert.ok(errTile.classList.contains('error'));
    assert.match(errTile.textContent, /TMDb Timeout/);

    // 2. Clicking retry button reloads candidates
    failApi = false;
    posterPanel.querySelector('.mw-wizard-artwork-retry-btn').click();
    await new Promise((r) => setTimeout(r, 0));

    const tilesAfterRetry = posterPanel.querySelectorAll('.mw-wizard-artwork-tile');
    assert.equal(tilesAfterRetry.length, 2);
    assert.equal(tilesAfterRetry[0].classList.contains('error'), false);

    // 3. Individual <img> load error shows broken placeholder + retry button without losing selection
    const firstImg = tilesAfterRetry[0].querySelector('.mw-wizard-artwork-image');
    const brokenBox = tilesAfterRetry[0].querySelector('.mw-wizard-artwork-broken');
    const imgRetryBtn = tilesAfterRetry[0].querySelector('.mw-wizard-artwork-img-retry-btn');
    firstImg.dispatchEvent({ type: 'error' });
    assert.equal(tilesAfterRetry[0].classList.contains('error'), true);
    assert.equal(brokenBox.classList.contains('hidden'), false);
    assert.equal(tilesAfterRetry[0].getAttribute('aria-pressed'), 'true');

    imgRetryBtn.click();
    assert.equal(tilesAfterRetry[0].classList.contains('error'), false);
    assert.equal(brokenBox.classList.contains('hidden'), true);
    assert.match(firstImg.getAttribute('src'), /retry=/);
});

test('E5b: Hintergrundbild (16:9) label, ordered multi-select (✓ 1, ✓ 2, upload combination, max-10 limit, Step 4 summary), single-select Poster/Logo, and non-overlapping Logo grid CSS', async () => {
    const indexHtml = fs.readFileSync(path.join(__dirname, '../../gui/static/index.html'), 'utf8');
    const styleCss = fs.readFileSync(path.join(__dirname, '../../gui/static/style.css'), 'utf8');

    // 1. Static HTML tab label and CSS non-overlap & opaque Superfood Light logo background
    assert.match(indexHtml, /id="mw-wizard-tab-fanart"[^>]*>Hintergrundbild \(16:9\)<\/button>/);
    assert.match(styleCss, /\.mw-wizard-artwork-grid\s*\{[^}]*max-height:\s*290px;[^}]*overflow-x:\s*hidden;/);
    const tileRuleMatch = styleCss.match(/\.mw-wizard-artwork-tile\s*\{([^}]*)\}/);
    assert.ok(tileRuleMatch, '.mw-wizard-artwork-tile rule must exist');
    assert.match(tileRuleMatch[1], /min-width:\s*0/);
    assert.match(tileRuleMatch[1], /min-height:\s*0/);
    assert.doesNotMatch(tileRuleMatch[1], /min-height:\s*140px/);
    assert.match(styleCss, /body\.theme-superfood-light\s+\.mw-wizard-artwork-grid-logo\s+\.mw-wizard-artwork-tile\s*\{\s*background:\s*var\(--primary\);/);

    // 2. Dynamic DOM label, empty state text, ordered backdrop multi-select vs strict Poster/Logo single-select
    const validPngDataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=';
    const elevenBackdrops = Array.from({ length: 11 }, (_, idx) => ({
        url: `https://image.tmdb.org/t/p/original/bd_${idx + 1}.jpg`,
        thumb_url: `https://image.tmdb.org/t/p/w300/bd_${idx + 1}.jpg`,
        lang: idx === 0 ? 'de' : '',
        width: 1920,
        height: 1080,
    }));
    const twoLogos = [
        { url: 'https://image.tmdb.org/t/p/original/logo_1.png', thumb_url: 'https://image.tmdb.org/t/p/w185/logo_1.png', lang: 'de', width: 800, height: 300 },
        { url: 'https://image.tmdb.org/t/p/original/logo_2.png', thumb_url: 'https://image.tmdb.org/t/p/w185/logo_2.png', lang: 'en', width: 800, height: 300 },
    ];

    let emptyBackdropMode = true;
    const { doc } = createArtworkMockDom();
    const wizard = createFilmWizard({
        document: doc,
        fetch: async (url) => {
            if (url.startsWith('/api/metadata/fetch')) {
                return { ok: true, status: 200, json: async () => ({ title: 'Matrix', year: '1999' }) };
            }
            if (url.startsWith('/api/artwork/candidates')) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => makeBackendCandidatesResponse({
                        backdrops: emptyBackdropMode ? [] : elevenBackdrops,
                        logos: twoLogos,
                    }),
                };
            }
            if (url.startsWith('/api/preview_process')) {
                return {
                    ok: true,
                    status: 200,
                    json: async () => ({ destination: '/nas/Filme/Matrix (1999)', renames: [], subs: [], junk: [] }),
                };
            }
            return { ok: true, status: 200, json: async () => ({}) };
        },
    });

    assert.equal(doc.getElementById('mw-wizard-tab-fanart').textContent, 'Hintergrundbild (16:9)');

    wizard.open({ query: 'Matrix', projectName: 'Matrix.1999', autoSearch: false });
    await wizard.selectMovieInWizard({ id: '603', name: 'Matrix (1999)', provider: 'tmdb' });
    wizard.goToStep(3);
    await new Promise((r) => setTimeout(r, 0));

    const fanartPanel = doc.getElementById('mw-wizard-artwork-fanart');
    const logoPanel = doc.getElementById('mw-wizard-artwork-logo');
    assert.match(fanartPanel.textContent, /Kein Hintergrundbild bei TMDb verfügbar\./);

    // Reload with 11 backdrops + 2 logos
    emptyBackdropMode = false;
    await wizard.loadArtworkCandidates({ force: true, resetSelection: true });

    // Logo tab stays strictly 1-click single-select
    doc.getElementById('mw-wizard-tab-logo').click();
    logoPanel.querySelectorAll('.mw-wizard-artwork-tile')[1].click();
    const logoSelected = logoPanel.querySelectorAll('.mw-wizard-artwork-tile').filter((t) => t.getAttribute('aria-pressed') === 'true');
    assert.equal(logoSelected.length, 1);
    assert.equal(wizard.getArtworkState().logo.selectedCount, 1);

    // Backdrop tab supports ordered multi-select: bd_1 is preselected -> click bd_2 -> add custom upload -> 3 items (✓ 1, ✓ 2, ✓ 3)
    doc.getElementById('mw-wizard-tab-fanart').click();
    fanartPanel.querySelectorAll('.mw-wizard-artwork-tile')[1].click();
    assert.equal(wizard.setCustomArtworkUpload('backdrop', validPngDataUrl, 'custom-bg.png'), true);

    const bdState = wizard.getArtworkState().backdrop;
    assert.equal(bdState.mode, 'multi');
    assert.equal(bdState.selectedCount, 3);
    const activeBdTiles = fanartPanel.querySelectorAll('.mw-wizard-artwork-tile').filter((t) => t.getAttribute('aria-pressed') === 'true');
    assert.equal(activeBdTiles.length, 3);
    // Upload tile is rendered first in DOM (index 0 in DOM, 3rd in selection order -> '✓ 3'); bd_1 is '✓ 1', bd_2 is '✓ 2'
    assert.equal(activeBdTiles[0].querySelector('.mw-wizard-artwork-check').textContent, '✓ 3');
    assert.equal(activeBdTiles[1].querySelector('.mw-wizard-artwork-check').textContent, '✓ 1');
    assert.equal(activeBdTiles[2].querySelector('.mw-wizard-artwork-check').textContent, '✓ 2');

    assert.deepEqual(wizard.buildMovieBasePayload().artwork_overrides.backdrop, {
        mode: 'multi',
        items: [
            { mode: 'url', url: 'https://image.tmdb.org/t/p/original/bd_1.jpg' },
            { mode: 'url', url: 'https://image.tmdb.org/t/p/original/bd_2.jpg' },
            { mode: 'upload', data_url: validPngDataUrl },
        ],
    });

    // Step 4 summary displays 'Hintergrundbild: 3 Bilder'
    wizard.goToStep(4);
    await new Promise((r) => setTimeout(r, 0));
    const step4Summary = doc.getElementById('mw-wizard-step-4').textContent;
    assert.match(step4Summary, /Hintergrundbild: 3 Bilder/);

    // Go back to Step 3, fill up to 10 backdrops and verify 11th is rejected with clear message
    wizard.goToStep(3);
    for (let i = 2; i <= 8; i++) {
        wizard.selectArtworkCandidate('backdrop', i);
    }
    assert.equal(wizard.getArtworkState().backdrop.selectedCount, 10);
    wizard.selectArtworkCandidate('backdrop', 9);
    assert.equal(wizard.getArtworkState().backdrop.selectedCount, 10);
    assert.match(doc.getElementById('mw-wizard-artwork-source-info').textContent, /Maximal 10 Hintergrundbilder auswählbar/);

    // Deselecting down to 1 item returns payload cleanly to backward-compatible single { mode: 'url', url } and badge '✓'
    wizard.deselectArtworkRole('backdrop');
    assert.equal(wizard.getArtworkState().backdrop.selectedCount, 0);
    wizard.selectArtworkCandidate('backdrop', 1);
    assert.equal(wizard.getArtworkState().backdrop.selectedCount, 1);
    assert.deepEqual(wizard.buildMovieBasePayload().artwork_overrides.backdrop, {
        mode: 'url',
        url: 'https://image.tmdb.org/t/p/original/bd_2.jpg',
    });
    const singleSelectedTile = fanartPanel.querySelectorAll('.mw-wizard-artwork-tile').find((t) => t.getAttribute('aria-pressed') === 'true');
    assert.equal(singleSelectedTile.querySelector('.mw-wizard-artwork-check').textContent, '✓');

    // Re-add custom upload alongside bd_2 ([bd_2, upload]), and on Logo upload then pick a TMDb URL,
    // then reload a movie with 0 backdrops & 0 logos (resetSelection: true) -> orphaned TMDb URLs MUST be stripped!
    wizard.setCustomArtworkUpload('backdrop', validPngDataUrl, 'custom-bg.png');
    assert.equal(wizard.getArtworkState().backdrop.selectedCount, 2);
    wizard.setCustomArtworkUpload('logo', validPngDataUrl, 'custom-logo.png');
    wizard.selectArtworkCandidate('logo', 0);
    assert.equal(wizard.getArtworkState().logo.mode, 'url');

    emptyBackdropMode = true;
    twoLogos.length = 0;
    await wizard.loadArtworkCandidates({ force: true, resetSelection: true });

    const bdAfterEmpty = wizard.getArtworkState().backdrop;
    assert.equal(bdAfterEmpty.mode, 'upload');
    assert.equal(bdAfterEmpty.selectedCount, 1);
    assert.equal(bdAfterEmpty.selectedUrl, '');
    assert.deepEqual(wizard.buildMovieBasePayload().artwork_overrides.backdrop, {
        mode: 'upload',
        data_url: validPngDataUrl,
    });
    const remainingUploadTile = fanartPanel.querySelector('.mw-wizard-artwork-tile-upload');
    assert.equal(remainingUploadTile.querySelector('.mw-wizard-artwork-check').textContent, '✓');

    const logoAfterEmpty = wizard.getArtworkState().logo;
    assert.equal(logoAfterEmpty.mode, 'none');
    assert.equal(logoAfterEmpty.selectedUrl, '');
    assert.equal(logoAfterEmpty.selectedCount, 0);
});
