import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');
const filmWizardJsPath = path.resolve(__dirname, '../../gui/static/js/film_wizard.js');
const indexHtmlPath = path.resolve(__dirname, '../../gui/static/index.html');
const styleCssPath = path.resolve(__dirname, '../../gui/static/style.css');

function decodeHtmlEntities(str) {
    return String(str || '')
        .replace(/&quot;/g, '"')
        .replace(/&#039;/g, "'")
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
}

function createQueueTestEnv({ onFetch, onConfirm } = {}) {
    const byId = new Map();
    const alerts = [];
    const errors = [];
    const confirms = [];

    const matches = (el, sel) => {
        if (!el || !sel) return false;
        if (sel.startsWith('#')) return el.id === sel.slice(1);
        if (sel.startsWith('.')) return el.classList.contains(sel.slice(1));
        return el.tagName === sel.toUpperCase();
    };

    function makeElement(tagName) {
        const classes = new Set();
        const attrs = new Map();
        const listeners = {};
        let idVal = '';
        let htmlVal = '';
        let textVal = '';
        const el = {
            tagName: String(tagName).toUpperCase(),
            type: '',
            value: '',
            checked: false,
            disabled: false,
            style: {},
            children: [],
            dataset: {},
            get id() { return idVal; },
            set id(v) { idVal = String(v || ''); if (idVal) byId.set(idVal, el); },
            get className() { return Array.from(classes).join(' '); },
            set className(v) {
                classes.clear();
                String(v || '').split(/\s+/).filter(Boolean).forEach((c) => classes.add(c));
            },
            classList: {
                add: (...ns) => ns.forEach((n) => n && classes.add(n)),
                remove: (...ns) => ns.forEach((n) => classes.delete(n)),
                contains: (n) => classes.has(n),
                toggle: (n, f) => {
                    const add = f !== undefined ? Boolean(f) : !classes.has(n);
                    if (add) classes.add(n); else classes.delete(n);
                    return add;
                },
            },
            get textContent() { return textVal + el.children.map((c) => c.textContent).join(''); },
            set textContent(v) { textVal = String(v ?? ''); htmlVal = textVal; el.children = []; },
            get innerHTML() { return htmlVal; },
            set innerHTML(v) {
                htmlVal = String(v ?? '');
                textVal = htmlVal.replace(/<[^>]*>/g, '');
                el.children = [];
                const btnRe = /<button\b([^>]*)>([\s\S]*?)<\/button>/gi;
                let m;
                while ((m = btnRe.exec(htmlVal)) !== null) {
                    const attrStr = m[1];
                    const inner = m[2];
                    const btn = makeElement('button');
                    btn.innerHTML = inner;
                    btn.disabled = /\bdisabled\b/i.test(attrStr);
                    const attrPairRe = /([\w-]+)\s*=\s*"([^"]*)"/g;
                    let am;
                    while ((am = attrPairRe.exec(attrStr)) !== null) {
                        const k = am[1];
                        const val = decodeHtmlEntities(am[2]);
                        btn.setAttribute(k, val);
                        if (k === 'class') btn.className = val;
                        if (k === 'type') btn.type = val;
                    }
                    el.appendChild(btn);
                }
            },
            setAttribute: (k, v) => { attrs.set(k, String(v)); if (k === 'id') el.id = v; },
            getAttribute: (k) => (attrs.has(k) ? attrs.get(k) : null),
            appendChild(child) {
                if (child) {
                    if (child.id) byId.set(child.id, child);
                    el.children.push(child);
                }
                return child;
            },
            addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
            async clickAsync() {
                if (el.disabled) return;
                const evt = { type: 'click', target: el, currentTarget: el, preventDefault() {}, stopPropagation() {} };
                for (const fn of (listeners.click || [])) {
                    await fn(evt);
                }
            },
            querySelectorAll(sel) {
                const out = [];
                const walk = (node) => {
                    for (const ch of node.children || []) {
                        if (matches(ch, sel)) out.push(ch);
                        walk(ch);
                    }
                };
                walk(el);
                return out;
            },
            querySelector(sel) { return el.querySelectorAll(sel)[0] || null; },
        };
        return el;
    }

    const body = makeElement('body');
    const document = {
        cookie: 'mw_csrf_token=test-csrf',
        hidden: false,
        visibilityState: 'visible',
        documentElement: { style: { setProperty() {}, removeProperty() {} } },
        body,
        createElement: (tag) => makeElement(tag),
        getElementById(id) {
            if (!id) return null;
            if (!byId.has(id)) {
                const el = makeElement('div');
                el.id = id;
                body.appendChild(el);
            }
            return byId.get(id);
        },
        querySelectorAll: (sel) => body.querySelectorAll(sel),
        querySelector: (sel) => body.querySelector(sel),
        addEventListener() {},
    };

    const fetchCalls = [];
    const baseFetch = async (url, options = {}) => {
        fetchCalls.push({ url: String(url), options });
        if (onFetch) {
            const custom = await onFetch(String(url), options);
            if (custom) return custom;
        }
        return { ok: true, status: 200, json: async () => ({ jobs: [] }) };
    };

    const windowObj = {
        fetch: baseFetch,
        location: { reload() {} },
        scrollTo() {},
        addEventListener() {},
        AppCapabilities: { capabilities: { open_local_folder: true } },
    };

    const sandbox = {
        window: windowObj,
        document,
        fetch: baseFetch,
        Headers: class Headers {},
        console: {
            log() {},
            warn() {},
            error: (...args) => errors.push(args.join(' ')),
        },
        alert: (msg) => alerts.push(String(msg)),
        confirm: (msg) => {
            confirms.push(String(msg));
            return onConfirm ? Boolean(onConfirm(String(msg))) : true;
        },
        setTimeout: (fn, ms) => setTimeout(fn, Math.min(Number(ms) || 0, 5)),
        clearTimeout,
        setInterval: () => 1,
        clearInterval: () => {},
        localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
        URLSearchParams,
    };
    sandbox.globalThis = sandbox;

    const rawApp = fs.readFileSync(appJsPath, 'utf8');
    const stripped = rawApp.replace(/^\s*import\s+[\s\S]*?from\s+['"][^'"]+['"];?\s*$/gm, '');
    vm.createContext(sandbox);
    vm.runInContext(stripped, sandbox);

    return { sandbox, document, alerts, errors, confirms, fetchCalls, run: (expr) => vm.runInContext(expr, sandbox) };
}

test('AK7.1: isQueueJobActive governs activeProjectsProcessing, badges, executeSeriesWorkflow, and waitForQueueJob', async () => {
    let pollIdx = 0;
    const pollStatuses = ['queued', 'running', 'pausing', 'paused', 'cancelling', 'cancelled'];
    const env = createQueueTestEnv({
        onFetch: async (url) => {
            if (url === '/api/queue') {
                const st = pollStatuses[Math.min(pollIdx++, pollStatuses.length - 1)];
                return { ok: true, status: 200, json: async () => ({ jobs: [{ id: 'w-1', status: st }] }) };
            }
            return null;
        },
    });

    for (const activeSt of ['queued', 'running', 'pausing', 'paused', 'cancelling']) {
        assert.equal(env.run(`isQueueJobActive(${JSON.stringify(activeSt)})`), true);
    }
    for (const termSt of ['done', 'error', 'cancelled']) {
        assert.equal(env.run(`isQueueJobActive(${JSON.stringify(termSt)})`), false);
    }

    const sampleJobs = [
        { id: '1', status: 'queued', project_name: 'ProjQueued', files: ['ep1.mkv'] },
        { id: '2', status: 'pausing', project_name: 'ProjPausing', files: ['ep2.mkv'] },
        { id: '3', status: 'paused', project_name: 'ProjPaused', files: ['ep3.mkv'] },
        { id: '4', status: 'cancelling', project_name: 'ProjCancelling', files: ['ep4.mkv'] },
        { id: '5', status: 'cancelled', project_name: 'ProjCancelled', files: ['ep5.mkv'] },
        { id: '6', status: 'done', project_name: 'ProjDone', files: ['ep6.mkv'] },
    ];
    env.run(`renderQueue(${JSON.stringify(sampleJobs)})`);

    const activeProjects = Array.from(env.run('activeProjectsProcessing'));
    assert.deepEqual(activeProjects.sort(), ['ProjCancelling', 'ProjPaused', 'ProjPausing', 'ProjQueued']);
    assert.equal(env.document.getElementById('queue-badge').textContent, '4');
    assert.equal(env.document.getElementById('header-queue-badge').textContent, '4');

    // executeSeriesWorkflow blocks overlapping files in paused/pausing/cancelling, allows cancelled
    env.run(`selectedShow = { id: "10", provider: "tvdb", name: "Show" }; activeSeriesGroupFiles = ["ep3.mkv"];`);
    await env.run('executeSeriesWorkflow()');
    assert.equal(env.alerts.length, 1);
    assert.match(env.alerts[0], /ep3\.mkv/);

    // waitForQueueJob waits through queued -> running -> pausing -> paused -> cancelling and resolves on cancelled
    const resolved = await env.run('waitForQueueJob("w-1", { intervalMs: 1, timeoutMs: 2000 })');
    assert.equal(resolved.status, 'cancelled');
    assert.equal(pollIdx, 6);
});

test('AK7.2: renderQueue labels, progress bars, buttons, escaping, normalize exclusion & retry knownFinishedJobs reset', async () => {
    const env = createQueueTestEnv();
    const jobs = [
        { id: 'j-run', name: 'Film <A>', status: 'running', progress: 40, message: 'Msg & 1', type: 'movie' },
        { id: 'j-pausing', name: 'Film B', status: 'pausing', progress: 55, message: 'Wartet', type: 'movie' },
        { id: 'j-paused', name: 'Film C', status: 'paused', paused_from: 'queued', progress: 20, message: 'Pausiert', type: 'movie' },
        { id: 'j-cancelling', name: 'Film D', status: 'cancelling', progress: 70, message: 'Stop', type: 'movie' },
        {
            id: 'j-cancelled',
            name: 'Film E',
            status: 'cancelled',
            progress: 70,
            message: 'Vom Benutzer abgebrochen',
            type: 'movie',
            pipeline: { metadata: { status: 'done', progress: 100 }, convert: { status: 'cancelled', progress: 0 } },
        },
        { id: 'j-norm-canc', name: 'Norm', status: 'cancelled', progress: 10, message: 'Abgebrochen', type: 'normalize' },
    ];
    env.run(`isFirstQueuePoll = false; renderQueue(${JSON.stringify(jobs)})`);

    const cards = env.document.getElementById('queue-list').children;
    assert.equal(cards.length, 6);
    const byTaskHtml = Object.fromEntries(jobs.map((j, idx) => [j.id, cards[jobs.length - 1 - idx]]));

    // Escaping & pulse only on running
    assert.match(byTaskHtml['j-run'].innerHTML, /Film &lt;A&gt;/);
    assert.match(byTaskHtml['j-run'].innerHTML, /Msg &amp; 1/);
    assert.match(byTaskHtml['j-run'].innerHTML, /animation:\s*pulse/);
    assert.ok(byTaskHtml['j-run'].querySelector('.queue-pause-btn'));
    assert.ok(byTaskHtml['j-run'].querySelector('.queue-cancel-btn'));

    // pausing & paused: var(--warning), visible progress bar WITHOUT pulse, Fortsetzen + Abbrechen
    for (const [id, label] of [['j-pausing', 'Pausiert nach Schritt'], ['j-paused', 'Pausiert']]) {
        const html = byTaskHtml[id].innerHTML;
        assert.match(html, new RegExp(label));
        assert.match(html, /var\(--warning\)/);
        assert.match(html, /width:\d+%/);
        assert.doesNotMatch(html, /animation:\s*pulse/);
        assert.ok(byTaskHtml[id].querySelector('.queue-resume-btn'));
        assert.ok(byTaskHtml[id].querySelector('.queue-cancel-btn'));
    }

    // cancelling: var(--danger), Bricht ab…, visible progress bar, disabled "Wird abgebrochen…" button
    assert.match(byTaskHtml['j-cancelling'].innerHTML, /Bricht ab…/);
    assert.match(byTaskHtml['j-cancelling'].innerHTML, /var\(--danger\)/);
    assert.match(byTaskHtml['j-cancelling'].innerHTML, /width:70%/);
    const cancBtns = byTaskHtml['j-cancelling'].querySelectorAll('button');
    assert.equal(cancBtns.length, 1);
    assert.equal(cancBtns[0].disabled, true);
    assert.match(cancBtns[0].textContent, /Wird abgebrochen…/);

    // cancelled movie: var(--text-muted), Abgebrochen, dimmed pipeline step, retry button present; normalize cancelled has NO retry button
    assert.match(byTaskHtml['j-cancelled'].innerHTML, /Abgebrochen/);
    assert.ok(byTaskHtml['j-cancelled'].querySelector('.queue-retry-btn'));
    assert.equal(byTaskHtml['j-norm-canc'].querySelector('.queue-retry-btn'), null);

    // Every rendered button has explicit type="button"
    env.document.getElementById('queue-list').querySelectorAll('button').forEach((b) => {
        assert.equal(b.type, 'button');
    });

    // Clicking retry removes taskId from knownFinishedJobs
    assert.equal(env.run('knownFinishedJobs.has("j-cancelled")'), true);
    await byTaskHtml['j-cancelled'].querySelector('.queue-retry-btn').clickAsync();
    assert.equal(env.run('knownFinishedJobs.has("j-cancelled")'), false);
});

test('AK7.3: confirm dialog only for started jobs, clear-queue prompt, pendingQueueActions lock across poll & error reporting', async () => {
    let resolveInFlight;
    let shouldFail = false;
    let allowConfirm = true;

    const env = createQueueTestEnv({
        onConfirm: () => allowConfirm,
        onFetch: async (url) => {
            if (url === '/api/queue/pause') {
                await new Promise((r) => { resolveInFlight = r; });
                if (shouldFail) {
                    return { ok: false, status: 400, json: async () => ({ message: 'Bereits beendet' }) };
                }
                return { ok: true, status: 200, json: async () => ({ status: 'success', job_status: 'pausing' }) };
            }
            return null;
        },
    });

    // Clear button confirmation text
    env.run('initQueue()');
    env.confirms.length = 0;
    await env.document.getElementById('btn-clear-queue').clickAsync();
    assert.equal(
        env.confirms[0],
        'Möchtest du alle abgeschlossenen, fehlgeschlagenen und abgebrochenen Aufgaben aus der Liste entfernen? (Laufende und wartende Aufgaben bleiben erhalten)'
    );

    // Cancel confirmation matrix: 1-click for queued & paused(queued), confirm required for running, pausing, paused(running)
    const cancelCases = [
        { id: 'c-queued', status: 'queued', expectConfirm: false },
        { id: 'c-paused-q', status: 'paused', paused_from: 'queued', expectConfirm: false },
        { id: 'c-running', status: 'running', expectConfirm: true },
        { id: 'c-pausing', status: 'pausing', expectConfirm: true },
        { id: 'c-paused-r', status: 'paused', paused_from: 'running', expectConfirm: true },
    ];
    for (const tc of cancelCases) {
        env.confirms.length = 0;
        env.fetchCalls.length = 0;
        allowConfirm = false;
        env.run(`renderQueue([${JSON.stringify({ name: tc.id, progress: 10, ...tc })}])`);
        await env.document.getElementById('queue-list').querySelector('.queue-cancel-btn').clickAsync();
        assert.equal(env.confirms.length > 0, tc.expectConfirm, `confirm mismatch for ${tc.id}`);
        assert.equal(
            env.fetchCalls.some((c) => c.url === '/api/queue/cancel'),
            !tc.expectConfirm,
            `fetch mismatch when confirm declined for ${tc.id}`
        );
    }

    // pendingQueueActions keeps buttons disabled across intermediate 2s poll & shows visible error on failure
    shouldFail = true;
    const runningJob = [{ id: 'inflight-1', name: 'Big Film', status: 'running', progress: 25, type: 'movie' }];
    env.run(`renderQueue(${JSON.stringify(runningJob)})`);
    const clickPromise = env.document.getElementById('queue-list').querySelector('.queue-pause-btn').clickAsync();

    // Simulate 2s poll arriving while /api/queue/pause is still in-flight -> buttons stay disabled!
    env.run(`renderQueue(${JSON.stringify(runningJob)})`);
    const btnsDuringPoll = env.document.getElementById('queue-list').querySelectorAll('button');
    assert.ok(btnsDuringPoll.length >= 2);
    btnsDuringPoll.forEach((b) => assert.equal(b.disabled, true));

    resolveInFlight();
    await clickPromise;
    assert.ok(env.alerts.some((a) => a.includes('Bereits beendet')));
    assert.ok(env.errors.some((e) => e.includes('Bereits beendet')));
    // Re-enabled after error
    env.document.getElementById('queue-list').querySelectorAll('button').forEach((b) => assert.equal(b.disabled, false));
});

test('AK7.4: Dynamic cache-busting sync (>= 127 / >= 71) and CSS variable-only queue rules', () => {
    const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');
    const appJs = fs.readFileSync(appJsPath, 'utf8');
    const filmWizardJs = fs.readFileSync(filmWizardJsPath, 'utf8');
    const styleCss = fs.readFileSync(styleCssPath, 'utf8');

    const cssMatch = indexHtml.match(/href="style\.css\?v=(\d+)"/);
    assert.ok(cssMatch && Number(cssMatch[1]) >= 71, 'style.css?v= must be >= 71');

    const jsMatch = indexHtml.match(/src="app\.js\?v=(\d+)"/);
    assert.ok(jsMatch && Number(jsMatch[1]) >= 127, 'app.js?v= must be >= 127');
    const expectedJsVer = jsMatch[1];

    const appImports = [...appJs.matchAll(/from\s+['"]\.\/js\/[^'"]+\?v=(\d+)['"]/g)];
    assert.equal(appImports.length, 12);
    appImports.forEach((m) => assert.equal(m[1], expectedJsVer));

    const wizImports = [...filmWizardJs.matchAll(/from\s+['"]\.\/[^'"]+\?v=(\d+)['"]/g)];
    assert.equal(wizImports.length, 3);
    wizImports.forEach((m) => assert.equal(m[1], expectedJsVer));

    for (const selector of ['.queue-card', '.queue-card-actions', '.queue-action-btn', '.queue-action-btn-danger']) {
        const idx = styleCss.indexOf(selector);
        assert.ok(idx > 0, `${selector} must exist in style.css`);
        const ruleBlock = styleCss.slice(idx, styleCss.indexOf('}', idx) + 1);
        assert.doesNotMatch(ruleBlock, /#[0-9a-fA-F]{3,8}/, `${selector} must not contain raw hex colors`);
    }
});
