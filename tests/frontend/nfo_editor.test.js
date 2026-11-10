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

    function makeElement(tagName) {
        const classes = new Set();
        const attrs = new Map();
        const listeners = {};
        const el = {
            tagName: String(tagName).toUpperCase(),
            id: '',
            className: '',
            type: '',
            value: '',
            placeholder: '',
            textContent: '',
            rows: 0,
            children: [],
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
                el.children.push(child);
                if (child.id) byId.set(child.id, child);
                return child;
            },
            addEventListener(type, fn) {
                listeners[type] = listeners[type] || [];
                listeners[type].push(fn);
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
                if (val === '') el.children.length = 0;
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
