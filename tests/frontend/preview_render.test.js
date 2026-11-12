import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
    escapeHTML,
    splitPreviewPath,
    formatDestinationHtml,
    renderPreviewDestination,
    createPreviewCheckbox,
    renderPreviewList,
    renderSimilarExistingHint,
    collectPreviewSelection,
    renderPreviewData,
} from '../../gui/static/js/preview_render.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const styleCssPath = path.resolve(__dirname, '../../gui/static/style.css');

function createMiniDomElement(tagName = 'div') {
    const classSet = new Set();
    const attrs = new Map();
    const dataset = {};
    const children = [];
    let html = '';

    const el = {
        tagName: tagName.toUpperCase(),
        id: '',
        checked: false,
        dataset,
        children,
        classList: {
            add: (...names) => names.forEach((n) => n && classSet.add(n)),
            remove: (...names) => names.forEach((n) => classSet.delete(n)),
            contains: (n) => classSet.has(n),
        },
        setAttribute(k, v) {
            attrs.set(k, String(v));
            if (k.startsWith('data-')) dataset[k.slice(5)] = String(v);
        },
        getAttribute(k) {
            return attrs.has(k) ? attrs.get(k) : null;
        },
        get innerHTML() {
            return html;
        },
        set innerHTML(val) {
            html = String(val ?? '');
        },
    };
    return el;
}

test('E2-AK1 (1): renderPreviewDestination escapes <script> and <img onerror=...> before converting line breaks to <br>', () => {
    const destEl = createMiniDomElement('div');
    const maliciousPath = '/mnt/nas/Filme/<script>alert(1)</script>\n/pCloud/Filme/<img src=x onerror="alert(2)">';

    const rendered = renderPreviewDestination(destEl, maliciousPath);

    assert.equal(rendered, formatDestinationHtml(maliciousPath));
    assert.equal(destEl.innerHTML, rendered);
    assert.equal(rendered.includes('<script>'), false);
    assert.equal(rendered.includes('<img'), false);
    assert.equal(rendered.includes('onerror="alert(2)"'), false);
    assert.match(rendered, /&lt;script&gt;alert\(1\)&lt;\/script&gt;<br>\/pCloud\/Filme\/&lt;img src=x onerror=&quot;alert\(2\)&quot;&gt;/);
});

test('E2-AK2 (2): createPreviewCheckbox and renderPreviewList escape old/new and set data-old/data-new for renames, subs, and junk', () => {
    const cases = [
        {
            group: 'renames',
            item: { old: 'bad<script>.mkv', new: 'Good "Movie" (2024).mkv' },
            expectedOld: 'bad&lt;script&gt;.mkv',
            expectedNew: 'Good &quot;Movie&quot; (2024).mkv',
        },
        {
            group: 'subs',
            item: { old: 'sub<img onerror=1>.srt', new: "Good 'Sub'.de.srt" },
            expectedOld: 'sub&lt;img onerror=1&gt;.srt',
            expectedNew: 'Good &#039;Sub&#039;.de.srt',
        },
        {
            group: 'junk',
            item: 'sample & <junk>.nfo',
            expectedOld: 'sample &amp; &lt;junk&gt;.nfo',
            expectedNew: '',
        },
    ];

    for (const c of cases) {
        const container = createMiniDomElement('div');
        renderPreviewList(container, [c.item], c.group, 'Leer', true);
        assert.match(container.innerHTML, new RegExp(`class="preview-cb-${c.group}"`));
        assert.ok(container.innerHTML.includes(`data-old="${c.expectedOld}"`));
        assert.ok(container.innerHTML.includes(`data-new="${c.expectedNew}"`));
        assert.equal(container.innerHTML.includes('<script>'), false);
        assert.equal(container.innerHTML.includes('<img'), false);
    }

    const emptyContainer = createMiniDomElement('div');
    renderPreviewList(emptyContainer, [], 'renames', 'Keine <Videos> gefunden.');
    assert.match(emptyContainer.innerHTML, /Keine &lt;Videos&gt; gefunden\./);
});

test('E2-AK2 (3): collectPreviewSelection returns only checked items in explicit_renames, explicit_subs, and explicit_junk structure', () => {
    const checkboxes = [
        { group: 'renames', checked: true, old: 'raw1.mkv', new: 'Movie (2024) - Part 1.mkv' },
        { group: 'renames', checked: false, old: 'raw2.mkv', new: 'Movie (2024) - Part 2.mkv' },
        { group: 'subs', checked: true, old: 'raw1.srt', new: 'Movie (2024).de.srt' },
        { group: 'subs', checked: false, old: 'raw2.srt', new: 'Movie (2024).en.srt' },
        { group: 'junk', checked: true, old: 'RARBG.txt', new: '' },
        { group: 'junk', checked: false, old: 'keep.txt', new: '' },
    ].map((entry) => ({
        group: entry.group,
        checked: entry.checked,
        dataset: { old: entry.old, new: entry.new },
        getAttribute(attr) {
            if (attr === 'data-old') return entry.old;
            if (attr === 'data-new') return entry.new;
            return null;
        },
    }));

    const mockRoot = {
        querySelectorAll(selector) {
            const match = selector.match(/^\.preview-cb-(renames|subs|junk)(:checked)?$/);
            if (!match) return [];
            const [, grp, onlyChecked] = match;
            return checkboxes.filter((cb) => cb.group === grp && (!onlyChecked || cb.checked));
        },
    };

    const result = collectPreviewSelection(mockRoot);
    assert.deepEqual(result, {
        explicit_renames: [{ old: 'raw1.mkv', new: 'Movie (2024) - Part 1.mkv' }],
        explicit_subs: [{ old: 'raw1.srt', new: 'Movie (2024).de.srt' }],
        explicit_junk: ['RARBG.txt'],
    });
});

test('E2-AK4 (4): renderPreviewData catches and logs errors in #91 similar_existing renderer while still rendering destination and lists', () => {
    const logs = [];
    const destEl = createMiniDomElement('div');
    const listRenames = createMiniDomElement('div');
    const listSubs = createMiniDomElement('div');
    const listJunk = createMiniDomElement('div');
    const similarBox = createMiniDomElement('div');

    // Trigger an exception inside renderSimilarExistingHint when setting similarText.innerHTML
    const brokenSimilarText = {
        set innerHTML(_val) {
            throw new Error('DOM-Fehler im #91-Container');
        },
    };

    const brokenData = {
        destination: '/mnt/nas/Filme/Matrix (1999)',
        renames: [{ old: 'matrix.mkv', new: 'Matrix (1999).mkv' }],
        subs: [{ old: 'matrix.srt', new: 'Matrix (1999).de.srt' }],
        junk: ['info.nfo'],
        similar_existing: {
            exact: [{ folder: 'Matrix (1999)', relative_path: 'Matrix (1999)' }],
            similar: [],
        },
    };

    const origConsoleError = console.error;
    console.error = () => {};
    try {
        assert.doesNotThrow(() => {
            renderPreviewData(
                {
                    similarBox,
                    similarText: brokenSimilarText,
                    dest: destEl,
                    listRenames,
                    listSubs,
                    listJunk,
                },
                brokenData,
                {
                    idPrefix: 'mw-wizard-similar',
                    onLog: (msg) => logs.push(msg),
                }
            );
        });
    } finally {
        console.error = origConsoleError;
    }

    assert.equal(similarBox.classList.contains('hidden'), true);
    assert.equal(logs.length, 1);
    assert.match(logs[0], /Hinweis auf ähnliche Titel konnte nicht dargestellt werden/);
    assert.equal(destEl.innerHTML, '/mnt/nas/Filme/Matrix (1999)');
    assert.match(listRenames.innerHTML, /Matrix \(1999\)\.mkv/);
    assert.match(listSubs.innerHTML, /Matrix \(1999\)\.de\.srt/);
    assert.match(listJunk.innerHTML, /info\.nfo/);
    assert.equal(escapeHTML("a&b"), "a&amp;b");
    assert.equal(renderSimilarExistingHint(null, null, null), false);
});

test('E6b (6): createPreviewCheckbox renders uncut filename, subfolder prefix, title tooltip, and file-type badge while keeping full path in data-old', () => {
    const nfoRel = 'The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT/The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT.nfo';
    const jpgRel = 'The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT/The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT.jpg';

    assert.deepEqual(splitPreviewPath(nfoRel), {
        dirPath: 'The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT',
        fileName: 'The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT.nfo',
        extLabel: 'NFO',
    });
    assert.deepEqual(splitPreviewPath('PlainFileWithoutExt'), {
        dirPath: '',
        fileName: 'PlainFileWithoutExt',
        extLabel: 'DATEI',
    });

    const container = createMiniDomElement('div');
    renderPreviewList(container, [nfoRel, jpgRel], 'junk', 'Leer', true);
    const html = container.innerHTML;

    // 1. data-old retains full relative path and collectPreviewSelection returns full path in explicit_junk
    assert.ok(html.includes(`data-old="${nfoRel}"`));
    assert.ok(html.includes(`data-old="${jpgRel}"`));
    const extractedOlds = [...html.matchAll(/class="preview-cb-junk"\s+data-old="([^"]+)"\s+data-new="([^"]*)"/g)];
    const mockRoot = {
        querySelectorAll(sel) {
            if (sel === '.preview-cb-junk:checked') {
                return extractedOlds.map((m) => ({
                    checked: true,
                    dataset: { old: m[1], new: m[2] },
                    getAttribute: (k) => (k === 'data-old' ? m[1] : k === 'data-new' ? m[2] : null),
                }));
            }
            return [];
        },
    };
    assert.deepEqual(collectPreviewSelection(mockRoot).explicit_junk, [nfoRel, jpgRel]);

    // 2. Full filename, dimmed directory prefix, full-path title tooltip, and NFO / JPG extension badges
    assert.ok(html.includes('class="mw-wizard-result-item-dir">The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT/</div>'));
    assert.ok(html.includes('class="mw-wizard-result-item-filename">The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT.nfo</div>'));
    assert.ok(html.includes('class="mw-wizard-result-item-filename">The.Piano.Tuner.2026.German.DL.1080p.DV.HDR.WEBRip.AV1-WOTT.jpg</div>'));
    assert.ok(html.includes(`title="${nfoRel}"`));
    assert.ok(html.includes('class="mw-wizard-result-item-ext">NFO</span>'));
    assert.ok(html.includes('class="mw-wizard-result-item-ext">JPG</span>'));

    // Rename item also shows directory prefix, old/new names, and target extension badge
    const renameHtml = createPreviewCheckbox(
        { old: 'SubDir/raw.mkv', new: 'SubDir/The Piano Tuner (2026).mkv' },
        true,
        'renames'
    );
    assert.ok(renameHtml.includes('data-old="SubDir/raw.mkv"'));
    assert.ok(renameHtml.includes('data-new="SubDir/The Piano Tuner (2026).mkv"'));
    assert.ok(renameHtml.includes('class="mw-wizard-result-item-dir">SubDir/</div>'));
    assert.ok(renameHtml.includes('class="mw-wizard-result-item-old">raw.mkv</div>'));
    assert.ok(renameHtml.includes('class="mw-wizard-result-item-new">SubDir/The Piano Tuner (2026).mkv</div>'));
    assert.ok(renameHtml.includes('class="mw-wizard-result-item-ext">MKV</span>'));

    // 3. CSS check: .mw-wizard-result-item-filename uses overflow-wrap: anywhere and no ellipsis or line-through
    const styleCss = fs.readFileSync(styleCssPath, 'utf8');
    const filenameRuleMatch = styleCss.match(/\.mw-wizard-result-item-filename\s*\{([^}]+)\}/);
    assert.ok(filenameRuleMatch, '.mw-wizard-result-item-filename rule must exist in style.css');
    assert.match(filenameRuleMatch[1], /overflow-wrap:\s*anywhere/);
    assert.doesNotMatch(filenameRuleMatch[1], /text-overflow:\s*ellipsis/);
    assert.doesNotMatch(filenameRuleMatch[1], /line-through/);
});
