import test from 'node:test';
import assert from 'node:assert';
import { fetchStats, fetchYoutubeSubscriptions, fetchSmartInboxSuggestions } from '../../gui/static/js/welcome.js';

// Helper to back up and restore global fetch
const originalFetch = globalThis.fetch;

function mockFetch(responseObj, ok = true, status = 200, shouldThrow = false) {
    if (shouldThrow) {
        globalThis.fetch = () => Promise.reject(new TypeError("fetch failed"));
    } else {
        globalThis.fetch = () => Promise.resolve({
            ok,
            status,
            json: () => Promise.resolve(responseObj),
            statusText: status === 200 ? "OK" : "Internal Server Error"
        });
    }
}

function restoreFetch() {
    globalThis.fetch = originalFetch;
}

test('fetchStats - success', async () => {
    const mockData = { stats: { saved_bytes: 12345 } };
    mockFetch(mockData, true, 200);

    try {
        const result = await fetchStats();
        assert.deepStrictEqual(result, mockData);
    } finally {
        restoreFetch();
    }
});

test('fetchStats - non-ok status', async () => {
    mockFetch(null, false, 500);

    try {
        const result = await fetchStats();
        assert.strictEqual(result, null);
    } finally {
        restoreFetch();
    }
});

test('fetchStats - network error', async () => {
    mockFetch(null, false, 500, true);

    try {
        await assert.rejects(
            async () => { await fetchStats(); },
            /TypeError: fetch failed/
        );
    } finally {
        restoreFetch();
    }
});

test('fetchYoutubeSubscriptions - success', async () => {
    const mockData = { subscriptions: [{ name: "Test Channel" }] };
    mockFetch(mockData, true, 200);

    try {
        const result = await fetchYoutubeSubscriptions();
        assert.deepStrictEqual(result, mockData);
    } finally {
        restoreFetch();
    }
});

test('fetchYoutubeSubscriptions - non-ok status', async () => {
    mockFetch(null, false, 404);

    try {
        const result = await fetchYoutubeSubscriptions();
        assert.strictEqual(result, null);
    } finally {
        restoreFetch();
    }
});

test('fetchYoutubeSubscriptions - network error', async () => {
    mockFetch(null, false, 500, true);

    try {
        await assert.rejects(
            async () => { await fetchYoutubeSubscriptions(); },
            /TypeError: fetch failed/
        );
    } finally {
        restoreFetch();
    }
});

test('fetchSmartInboxSuggestions - success', async () => {
    const mockData = { suggestions: [{ project: "Test" }] };
    mockFetch(mockData, true, 200);

    try {
        const result = await fetchSmartInboxSuggestions();
        assert.deepStrictEqual(result, mockData);
    } finally {
        restoreFetch();
    }
});

test('fetchSmartInboxSuggestions - non-ok status', async () => {
    mockFetch(null, false, 503);

    try {
        const result = await fetchSmartInboxSuggestions();
        assert.strictEqual(result, null);
    } finally {
        restoreFetch();
    }
});

test('fetchSmartInboxSuggestions - network error', async () => {
    mockFetch(null, false, 500, true);

    try {
        await assert.rejects(
            async () => { await fetchSmartInboxSuggestions(); },
            /TypeError: fetch failed/
        );
    } finally {
        restoreFetch();
    }
});
