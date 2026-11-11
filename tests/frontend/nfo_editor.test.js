import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
    renderNfoEditor,
    getNfoEditorValues,
    buildMovieNfoOverrides,
    normalizeFskValue,
    parseGenresInput,
} from '../../gui/static/js/nfo_editor.js';

function createMockDom() {
    const byId = new Map();

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
        const childNodes = [];
        const childrenView = createHtmlCollectionView(childNodes);
        const el = {
            tagName: String(tagName).toUpperCase(),
            id: '',
            className: '',
            type: '',
            value: '',
            disabled: false,
            placeholder: '',
            rows: 0,
            _childNodes: childNodes,
            _textParts: [],
            get children() {
                return childrenView;
            },
            get textContent() {
                return collectText(el);
            },
            set textContent(v) {
                const str = String(v ?? '');
                childNodes.length = 0;
                el._textParts = [str];
            },
            ownerDocument: null,
            classList: {
                add: (...names) => names.forEach((n) => classes.add(n)),
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
                if (k === 'id') {
                    el.id = String(v);
                    byId.set(el.id, el);
                }
            },
            getAttribute(k) {
                return attrs.has(k) ? attrs.get(k) : null;
            },
            appendChild(child) {
                childNodes.push(child);
                if (child.id) byId.set(child.id, child);
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
                const list = listeners[evt.type] || [];
                list.forEach((fn) => fn(evt));
            },
        };
        Object.defineProperty(el, 'innerHTML', {
            get() {
                return '';
            },
            set(val) {
                if (val === '') {
                    childNodes.length = 0;
                    el._textParts = [];
                }
            },
        });
        return el;
    }

    const doc = {
        createElement(tag) {
            const el = makeElement(tag);
            el.ownerDocument = doc;
            return el;
        },
        getElementById(id) {
            return byId.get(id) || null;
        },
    };

    const container = doc.createElement('div');
    return { doc, container };
}

test('E1-AK2: renderNfoEditor renders Titel, Jahr, Plot, FSK, Genre and builds nfo_overrides.movie with all 5 keys', () => {
    const { container } = createMockDom();
    const editor = renderNfoEditor(container, {
        title: 'Blade Runner 2049',
        year: '2017',
        plot: 'Ein junger Blade Runner deckt ein Geheimnis auf.',
        fsk: 'FSK 12',
        genres: ['Sci-Fi', 'Drama'],
    });

    assert.ok(editor.elements.title, 'Titel input rendered');
    assert.ok(editor.elements.year, 'Jahr input rendered');
    assert.ok(editor.elements.plot, 'Plot textarea rendered');
    assert.ok(editor.elements.fsk, 'FSK select rendered');
    assert.ok(editor.elements.genres, 'Genre input rendered');

    assert.equal(editor.elements.title.value, 'Blade Runner 2049');
    assert.equal(editor.elements.year.value, '2017');
    assert.equal(editor.elements.plot.value, 'Ein junger Blade Runner deckt ein Geheimnis auf.');
    assert.equal(editor.elements.fsk.value, '12');
    assert.equal(editor.elements.genres.value, 'Sci-Fi, Drama');
    assert.equal(editor.isDirty(), false);

    // Edit fields
    editor.elements.title.value = 'Blade Runner 2049 - Director Cut';
    editor.elements.fsk.value = '16';
    editor.elements.genres.value = 'Sci-Fi, Thriller; Cyberpunk';
    editor.elements.title.dispatchEvent({ type: 'input' });

    assert.equal(editor.isDirty(), true);

    const overrides = buildMovieNfoOverrides(container);
    assert.deepEqual(Object.keys(overrides.movie).sort(), ['fsk', 'genres', 'plot', 'title', 'year']);
    assert.deepEqual(overrides, {
        movie: {
            title: 'Blade Runner 2049 - Director Cut',
            year: '2017',
            plot: 'Ein junger Blade Runner deckt ein Geheimnis auf.',
            fsk: '16',
            genres: ['Sci-Fi', 'Thriller', 'Cyberpunk'],
        },
    });
});

test('E1-AK8 (D6c): cleared fields in nfo_editor are explicitly transmitted as empty values in nfo_overrides.movie', () => {
    const { container } = createMockDom();
    const editor = renderNfoEditor(container, {
        title: 'Arrival',
        year: '2016',
        plot: 'Provider Plot',
        fsk: '12',
        genres: ['Sci-Fi'],
    });

    // Clear FSK, Genre, and Plot
    editor.elements.fsk.value = '';
    editor.elements.genres.value = '   ';
    editor.elements.plot.value = '';

    const overrides = editor.getNfoOverrides();
    assert.deepEqual(overrides, {
        movie: {
            title: 'Arrival',
            year: '2016',
            plot: '',
            fsk: '',
            genres: [],
        },
    });

    // Reset restores initial provider values
    editor.resetToInitial();
    assert.equal(editor.isDirty(), false);
    assert.deepEqual(getNfoEditorValues(editor), {
        title: 'Arrival',
        year: '2016',
        plot: 'Provider Plot',
        fsk: '12',
        genres: ['Sci-Fi'],
    });
});

test('normalizeFskValue and parseGenresInput handle edge cases cleanly', () => {
    assert.equal(normalizeFskValue('FSK 18'), '18');
    assert.equal(normalizeFskValue('ab 6 Jahren'), '6');
    assert.equal(normalizeFskValue('invalid'), '');
    assert.deepEqual(parseGenresInput('Action, action, Komödie ; '), ['Action', 'Komödie']);
});

test('E3-AK1: renderNfoEditor supports showSourceBadges, titleLabel, setFieldSource/clearFieldSources, and both onChange callback contracts including return to initial value', () => {
    const { container } = createMockDom();
    const changeEvents = [];
    const editor = renderNfoEditor(
        container,
        { title: 'Dune', year: '2021', plot: 'Arrakis', fsk: '12', genre: ['Sci-Fi'] },
        (values, changedField, dirty) => changeEvents.push({ values, changedField, dirty }),
        { idPrefix: 'nfo-agent-movie', titleLabel: 'Filmtitel (movie.nfo)', showSourceBadges: true }
    );

    assert.equal(editor.elements.titleLabel.textContent, 'Filmtitel (movie.nfo)');
    assert.ok(editor.sourceBadges.title, 'title source badge rendered');

    editor.setFieldSource('title', 'aus vorhandener NFO');
    editor.setFieldSource('genres', 'vom Metadatendienst');
    assert.equal(editor.getFieldSource('title'), 'aus vorhandener NFO');
    assert.equal(editor.getFieldSource('genre'), 'vom Metadatendienst');

    editor.elements.fskSelect.value = '16';
    editor.elements.fskSelect.dispatchEvent({ type: 'change' });
    assert.equal(editor.getFieldSource('fsk'), 'manuell');
    assert.equal(changeEvents.length, 1);
    assert.equal(changeEvents[0].changedField, 'fsk');
    assert.equal(changeEvents[0].values.fsk, '16');
    assert.equal(changeEvents[0].dirty, true);
    assert.equal(editor.isDirty(), true);

    // Return to initial value -> changedField is still reported, dirty state returns to false
    editor.elements.fskSelect.value = '12';
    editor.elements.fskSelect.dispatchEvent({ type: 'change' });
    assert.equal(changeEvents.length, 2);
    assert.equal(changeEvents[1].changedField, 'fsk');
    assert.equal(changeEvents[1].values.fsk, '12');
    assert.equal(changeEvents[1].dirty, false);
    assert.equal(editor.isDirty(), false);

    editor.clearFieldSources();
    assert.equal(editor.getFieldSource('title'), '');
    assert.equal(editor.getFieldSource('fsk'), '');

    // Legacy options.onChange contract: second argument is boolean isDirty()
    const { container: legacyContainer } = createMockDom();
    const legacyEvents = [];
    const legacyEditor = renderNfoEditor(
        legacyContainer,
        { title: 'Dune', year: '2021', plot: 'Arrakis', fsk: '12', genres: ['Sci-Fi'] },
        {
            onChange: (values, dirty) => legacyEvents.push({ values, dirty }),
        }
    );

    legacyEditor.elements.title.value = 'Dune: Part Two';
    legacyEditor.elements.title.dispatchEvent({ type: 'input' });
    assert.equal(legacyEvents.length, 1);
    assert.equal(typeof legacyEvents[0].dirty, 'boolean');
    assert.equal(legacyEvents[0].dirty, true);

    // Returning input to initial baseline value passes false as second argument
    legacyEditor.elements.title.value = 'Dune';
    legacyEditor.elements.title.dispatchEvent({ type: 'input' });
    assert.equal(legacyEvents.length, 2);
    assert.equal(typeof legacyEvents[1].dirty, 'boolean');
    assert.equal(legacyEvents[1].dirty, false);
    assert.equal(legacyEditor.isDirty(), false);
});

test('E4: setProviderComparison and clearProviderComparison manage per-field provider badge containers with read-only HTMLCollection children.length', () => {
    const { container } = createMockDom();
    const editor = renderNfoEditor(container);

    // Native HTMLCollection has a getter-only .length in strict mode
    assert.throws(() => {
        container.children.length = 0;
    }, TypeError);
    assert.throws(() => {
        editor.fieldBadges.fsk.children.length = 0;
    }, TypeError);

    assert.equal(editor.getProviderComparison(), null);
    assert.equal(editor.fieldBadges.fsk.classList.contains('hidden'), true);

    editor.setProviderComparison({
        providers: {
            tmdb: { status: 'ok', fields: { title: 'Dune', year: '2021', plot: 'Arrakis', fsk: '', genres: ['Sci-Fi'] } },
            ofdb: { status: 'ok', fields: { title: 'Dune', year: '2021', plot: '', fsk: '12', genres: ['Abenteuer'] } },
        },
        provider_order: ['tmdb', 'ofdb'],
    });

    assert.ok(editor.getProviderComparison());
    assert.equal(editor.fieldBadges.fsk.classList.contains('hidden'), false);
    assert.equal(editor.fieldBadges.fsk.children.length, 2);
    assert.equal(editor.getValues().fsk, '12');
    assert.deepEqual(editor.getValues().genres, ['Sci-Fi', 'Abenteuer']);

    editor.clearProviderComparison();
    assert.equal(editor.getProviderComparison(), null);
    assert.equal(editor.fieldBadges.fsk.classList.contains('hidden'), true);
    assert.equal(editor.fieldBadges.fsk.children.length, 0);
});
