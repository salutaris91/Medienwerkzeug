/**
 * Welcome Dashboard API fetchers
 * Note: Network errors are intentionally propagated to the caller.
 */

export async function fetchStats() {
    const res = await fetch("/api/stats");
    return res.ok ? await res.json() : null;
}

export async function fetchYoutubeSubscriptions() {
    const res = await fetch("/api/youtube/subscriptions");
    return res.ok ? await res.json() : null;
}

export async function fetchSmartInboxSuggestions() {
    const res = await fetch("/api/inbox/analyze");
    return res.ok ? await res.json() : null;
}
