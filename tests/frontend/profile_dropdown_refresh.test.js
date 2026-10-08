import test from 'node:test';
import assert from 'node:assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appJsPath = path.resolve(__dirname, '../../gui/static/app.js');

function createMockElement(id = '') {
    const classSet = new Set();
    const listeners = {};
    const children = [];
    return {
        id,
        value: '',
        checked: false,
        textContent: '',
        innerHTML: '',
        style: {},
        dataset: {},
        __listeners: listeners,
        __children: children,
        classList: {
            add: (cls) => classSet.add(cls),
            remove: (cls) => classSet.delete(cls),
            contains: (cls) => classSet.has(cls)
        },
        addEventListener: (event, handler) => {
            if (!listeners[event]) listeners[event] = [];
            listeners[event].push(handler);
        },
        dispatchEvent: async function(eventObj) {
            const eventList = listeners[eventObj.type] || [];
            for (const handler of eventList) {
                await handler.call(this, eventObj);
            }
        },
        closest: () => createMockElement(),
        querySelectorAll: () => [],
        querySelector: () => null,
        appendChild: (child) => { children.push(child); },
        cloneNode: () => createMockElement(id),
        replaceWith: () => {}
    };
}

async function setupTestEnvironment() {
    const elements = {};
    function getElement(id) {
        if (!elements[id]) {
            elements[id] = createMockElement(id);
        }
        return elements[id];
    }

    const consoleLogs = [];
    const fetchCalls = {
        profile: [],
        profiles: [],
        process: [],
        other: []
    };

    let fetchRoutes = {
        profileResponse: { ok: true, data: { success: true } },
        profilesResponse: { ok: true, data: { profiles: [] } },
        processResponse: { ok: true, data: { success: true } },
        profileThrows: null,
        profileJsonThrows: null
    };

    globalThis.onConsoleLog = (line) => {
        consoleLogs.push(line);
    };

    const docListeners = {};
    globalThis.document = {
        documentElement: {
            style: {
                setProperty: () => {},
                removeProperty: () => {}
            }
        },
        getElementById: (id) => getElement(id),
        createElement: (tag) => createMockElement(tag),
        querySelectorAll: () => [],
        querySelector: () => null,
        addEventListener: (event, handler) => {
            if (!docListeners[event]) docListeners[event] = [];
            docListeners[event].push(handler);
        },
        dispatchEvent: async (eventObj) => {
            const list = docListeners[eventObj.type] || [];
            for (const handler of list) {
                try {
                    await handler(eventObj);
                } catch (e) {
                    // ignore secondary DOM setup errors
                }
            }
        }
    };

    globalThis.window = {
        scrollTo: () => {},
        addEventListener: () => {},
        location: { reload: () => {} }
    };

    globalThis.localStorage = {
        getItem: () => null,
        setItem: () => {}
    };

    globalThis.setInterval = () => ({ unref: () => {} });
    globalThis.clearInterval = () => {};

    globalThis.EventSource = class {
        constructor() {}
        close() {}
    };

    globalThis.escapeHTML = (str) => str;
    globalThis.renderIgnoredFooter = () => "";
    globalThis.wireRestoreAll = () => {};
    globalThis.alert = () => {};

    // Module stubs
    globalThis.applyTheme = () => {};
    globalThis.cleanSeriesName = (s) => s;
    globalThis.formatBytes = (b) => `${b} B`;
    globalThis.guessSeasonAndEpisode = () => null;
    globalThis.guessEpisodeNumber = () => null;
    globalThis.cleanFilenameForManualTitle = (s) => s;
    globalThis.osBasename = (s) => s;
    globalThis.formatFskLabel = (s) => s;
    globalThis.fetchStats = () => {};
    globalThis.fetchYoutubeSubscriptions = () => {};
    globalThis.fetchSmartInboxSuggestions = () => {};
    globalThis.loadConversionRecommendations = () => {};
    globalThis.triggerQualityHintUpdates = () => {};
    globalThis.updateMwDataPanel = () => {};
    globalThis.prepareSeriesPayload = () => ({});
    globalThis.setupMaskedInput = () => {};
    globalThis.setMaskedInputValue = () => {};
    globalThis.validateAllMaskedFields = () => ({ valid: true, changedFields: {}, errors: [] });

    const mockFetch = async (url, options = {}) => {
        const method = (options.method || 'GET').toUpperCase();
        if (url === '/api/profile' && method === 'POST') {
            fetchCalls.profile.push({ url, options });
            if (fetchRoutes.profileThrows) {
                throw new Error(fetchRoutes.profileThrows);
            }
            const r = fetchRoutes.profileResponse;
            return {
                ok: r.ok,
                status: r.status || (r.ok ? 200 : 500),
                json: async () => {
                    if (fetchRoutes.profileJsonThrows) {
                        throw new Error(fetchRoutes.profileJsonThrows);
                    }
                    return r.data;
                }
            };
        }
        if (url === '/api/profiles' && method === 'GET') {
            fetchCalls.profiles.push({ url, options });
            const r = fetchRoutes.profilesResponse;
            return {
                ok: r.ok,
                status: r.status || (r.ok ? 200 : 200),
                json: async () => r.data
            };
        }
        if (url === '/api/process' && method === 'POST') {
            fetchCalls.process.push({ url, options });
            const r = fetchRoutes.processResponse;
            return {
                ok: r.ok,
                status: r.status || (r.ok ? 200 : 200),
                json: async () => r.data
            };
        }
        fetchCalls.other.push({ url, options });
        return {
            ok: true,
            status: 200,
            json: async () => ({})
        };
    };

    globalThis.fetch = mockFetch;
    globalThis.window.fetch = mockFetch;

    const appJsContent = fs.readFileSync(appJsPath, 'utf8');
    let cleanAppJs = appJsContent.replace(/import\s+\{([^}]+)\}\s+from\s+['"].*?['"];?/g, "const { $1 } = globalThis;");
    cleanAppJs = cleanAppJs.replace(
        "function appendConsoleLog(line) {",
        "function appendConsoleLog(line) { if (globalThis.onConsoleLog) globalThis.onConsoleLog(line);"
    );
    cleanAppJs += `
globalThis.setCurrentPreviewPayload = (val) => { currentPreviewPayload = val; };
globalThis.getCurrentPreviewPayload = () => currentPreviewPayload;
globalThis.getAllLocalProfiles = () => allLocalProfiles;
globalThis.setAllLocalProfiles = (val) => { allLocalProfiles = val; };
globalThis.populateLocalProfilesDropdown = populateLocalProfilesDropdown;
`;

    eval(cleanAppJs);

    // Fire DOMContentLoaded so event listeners in app.js register on mock elements
    await globalThis.document.dispatchEvent({ type: 'DOMContentLoaded' });

    return {
        elements,
        getElement,
        consoleLogs,
        fetchCalls,
        fetchRoutes,
        resetState: () => {
            consoleLogs.length = 0;
            fetchCalls.profile.length = 0;
            fetchCalls.profiles.length = 0;
            fetchCalls.process.length = 0;
            fetchCalls.other.length = 0;
            globalThis.setAllLocalProfiles([]);
            globalThis.setCurrentPreviewPayload(null);
        }
    };
}

test('Profile Dropdown Refresh - Case (a): ok:true and data.success:true refreshes dropdown and logs no error', async () => {
    const env = await setupTestEnvironment();
    env.resetState();

    env.fetchRoutes.profileResponse = { ok: true, data: { success: true } };
    env.fetchRoutes.profilesResponse = {
        ok: true,
        data: {
            profiles: [
                { filename: 'TestShow.json', data: { show_name: 'Test Show' } }
            ]
        }
    };

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        show_name: 'Test Show',
        provider: 'tmdb_tv',
        show_id: '123'
    });

    const btnExecute = env.getElement('btn-preview-execute');
    await btnExecute.dispatchEvent({ type: 'click' });

    // Allow any pending microtasks (e.g. fire-and-forget populateLocalProfilesDropdown) to resolve
    await new Promise(resolve => setTimeout(resolve, 20));

    assert.strictEqual(env.fetchCalls.profile.length, 1, '/api/profile must be called once');
    assert.strictEqual(env.fetchCalls.profiles.length, 1, 'populateLocalProfilesDropdown must fetch /api/profiles');
    assert.strictEqual(env.fetchCalls.process.length, 1, '/api/process must be reached');

    // No error logs should be present
    const errorLogs = env.consoleLogs.filter(log => log.includes('❌') || log.includes('Fehler') || log.includes('nicht'));
    assert.strictEqual(errorLogs.length, 0, 'No error message should be logged on success');
});

test('Profile Dropdown Refresh - Case (b): ok:true and data.success:false logs warning and does not refresh dropdown', async () => {
    const env = await setupTestEnvironment();
    env.resetState();

    env.fetchRoutes.profileResponse = { ok: true, data: { success: false } };

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        show_name: 'Test Show',
        provider: 'tmdb_tv',
        show_id: '123'
    });

    const btnExecute = env.getElement('btn-preview-execute');
    await btnExecute.dispatchEvent({ type: 'click' });

    await new Promise(resolve => setTimeout(resolve, 20));

    assert.strictEqual(env.fetchCalls.profile.length, 1, '/api/profile must be called once');
    assert.strictEqual(env.fetchCalls.profiles.length, 0, 'populateLocalProfilesDropdown must NOT be called on success:false');
    assert.strictEqual(env.fetchCalls.process.length, 1, '/api/process must still be reached');

    // Check exact AK7 error message
    const expectedError = '[System]: ❌ Profil wurde nicht gespeichert. Einstellungen gelten nur für diesen Lauf. Nach Neuladen erneut versuchen.';
    assert.ok(env.consoleLogs.includes(expectedError), `Console logs must include exact error: "${expectedError}"`);
});

test('Profile Dropdown Refresh - Case (c): ok:false (HTTP 500) logs connection error and does not refresh dropdown', async () => {
    const env = await setupTestEnvironment();
    env.resetState();

    env.fetchRoutes.profileResponse = { ok: false, status: 500, data: { error: 'Internal error' } };

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        show_name: 'Test Show',
        provider: 'tmdb_tv',
        show_id: '123'
    });

    const btnExecute = env.getElement('btn-preview-execute');
    await btnExecute.dispatchEvent({ type: 'click' });

    await new Promise(resolve => setTimeout(resolve, 20));

    assert.strictEqual(env.fetchCalls.profile.length, 1, '/api/profile must be called once');
    assert.strictEqual(env.fetchCalls.profiles.length, 0, 'populateLocalProfilesDropdown must NOT be called on HTTP error');
    assert.strictEqual(env.fetchCalls.process.length, 1, '/api/process must still be reached');

    // Check exact AK7 error message
    const expectedError = '[System]: ❌ Profil konnte nicht gespeichert werden (Verbindungsfehler). Einstellungen gelten nur für diesen Lauf.';
    assert.ok(env.consoleLogs.includes(expectedError), `Console logs must include exact error: "${expectedError}"`);
});

test('Profile Dropdown Refresh - Case (d): Network exception / invalid JSON logs connection error and processing continues', async () => {
    const env = await setupTestEnvironment();
    env.resetState();

    env.fetchRoutes.profileThrows = 'Failed to fetch network error';

    globalThis.setCurrentPreviewPayload({
        media_type: 'tv',
        show_name: 'Test Show',
        provider: 'tmdb_tv',
        show_id: '123'
    });

    const btnExecute = env.getElement('btn-preview-execute');
    await btnExecute.dispatchEvent({ type: 'click' });

    await new Promise(resolve => setTimeout(resolve, 20));

    assert.strictEqual(env.fetchCalls.profile.length, 1, '/api/profile was attempted');
    assert.strictEqual(env.fetchCalls.profiles.length, 0, 'populateLocalProfilesDropdown must NOT be called on exception');
    assert.strictEqual(env.fetchCalls.process.length, 1, 'Processing must continue (/api/process called) even on network exception');

    // Check exact AK7 error message
    const expectedError = '[System]: ❌ Profil konnte nicht gespeichert werden (Verbindungsfehler). Einstellungen gelten nur für diesen Lauf.';
    assert.ok(env.consoleLogs.includes(expectedError), `Console logs must include exact error: "${expectedError}"`);
});
