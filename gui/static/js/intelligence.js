/**
 * Conversion Intelligence Frontend Module
 */

let globalRecommendations = null;

export async function loadConversionRecommendations() {
    try {
        const res = await fetch("/api/conversion/recommendations");
        if (res.ok) {
            globalRecommendations = await res.json();
            renderIntelligenceDashboard(globalRecommendations);
            triggerQualityHintUpdates();
        }
    } catch (e) {
        console.error("Error loading conversion recommendations:", e);
    }
}

export function renderIntelligenceDashboard(data) {
    const grid = document.getElementById("intelligence-grid");
    if (!grid) return;

    const recs = data.recommendations || {};
    if (Object.keys(recs).length === 0) {
        grid.innerHTML = `<p class="text-muted text-center" style="grid-column: 1/-1; margin: 0; padding: 10px;">Noch keine Empfehlungen verfügbar. Führe erst Konvertierungen durch.</p>`;
        return;
    }

    let html = "";
    for (const [ct, info] of Object.entries(recs)) {
        let label = ct;
        let icon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-video" style="height:14px; width:14px; color:var(--text-muted);"><path d="m22 8-6 4 6 4V8Z"/><rect width="14" height="12" x="2" y="6" rx="2" ry="2"/></svg>`;
        if (ct === "movie") { label = "Filme"; icon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-film" style="height:14px; width:14px; color:var(--accent);"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M17 3v18"/><path d="M3 7h4"/><path d="M3 17h4"/><path d="M17 17h4"/><path d="M17 7h4"/><path d="M7 12h10"/></svg>`; }
        else if (ct === "live_action") { label = "Serien"; icon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-tv" style="height:14px; width:14px; color:var(--accent);"><rect width="20" height="15" x="2" y="7" rx="2" ry="2"/><polyline points="17 2 12 7 7 2"/></svg>`; }
        else if (ct === "doku") { label = "Dokus"; icon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-leaf" style="height:14px; width:14px; color:#10b981;"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.3 5.45-6"/></svg>`; }
        else if (ct === "anime") { label = "Animes"; icon = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sparkles" style="height:14px; width:14px; color:#ec4899;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>`; }

        html += `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-light); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 0.95em; display: flex; align-items: center; gap: 6px;">
                    <span>${icon}</span> <strong>${label}</strong>
                </span>
                <span style="font-size: 0.9em; color: var(--text-main);">Optimal: Qualität <strong>${info.optimal_quality}</strong></span>
                <span style="font-size: 0.8em; color: var(--text-muted);">Ersparnis: <strong>${Math.round((1 - info.avg_ratio) * 100)}%</strong></span>
                <span style="font-size: 0.7em; color: var(--text-muted); opacity: 0.7; margin-top: 2px;">Basis: ${info.sample_count} Datei(en)</span>
            </div>
        `;
    }
    grid.innerHTML = html;
}

export function triggerQualityHintUpdates() {
    if (!globalRecommendations) return;

    const recs = globalRecommendations.recommendations || {};

    // Movie context check
    const contextMovie = document.getElementById("context-movie");
    if (contextMovie && !contextMovie.classList.contains("hidden")) {
        const slider = document.getElementById("movie-quality-slider");
        const hintEl = document.getElementById("movie-quality-hint");
        const convertCb = document.getElementById("movie-option-convert");
        const destSelect = document.getElementById("movie-nas-destination");

        if (slider && hintEl) {
            if (!convertCb || !convertCb.checked) {
                hintEl.textContent = "";
                hintEl.classList.add("hidden");
            } else {
                const val = parseInt(slider.value);
                const isDoku = destSelect && destSelect.value.toLowerCase().includes("doku");
                const mediaType = isDoku ? "doku" : "movie";

                updateHintElement(hintEl, val, recs[mediaType]);
            }
        }
    }

    // Series context check
    const contextSeries = document.getElementById("context-series");
    if (contextSeries && !contextSeries.classList.contains("hidden")) {
        const slider = document.getElementById("series-quality-slider");
        const hintEl = document.getElementById("series-quality-hint");
        const convertCb = document.getElementById("series-option-convert");
        const isAnime = document.getElementById("series-is-anime")?.checked || false;
        const destSelect = document.getElementById("series-nas-destination");

        if (slider && hintEl) {
            if (!convertCb || !convertCb.checked) {
                hintEl.textContent = "";
                hintEl.classList.add("hidden");
            } else {
                const val = parseInt(slider.value);
                let mediaType = "live_action";
                if (isAnime) mediaType = "anime";
                else if (destSelect && destSelect.value.toLowerCase().includes("doku")) mediaType = "doku";

                updateHintElement(hintEl, val, recs[mediaType]);
            }
        }
    }
}

export function updateHintElement(el, currentVal, recInfo) {
    if (!recInfo) {
        el.textContent = "Noch keine historischen Daten für diesen Inhaltstyp vorhanden. Standardempfehlung ist Qualität 60.";
        el.classList.remove("hidden");
        return;
    }

    const optimal = recInfo.optimal_quality;
    if (currentVal === optimal) {
        el.textContent = `Optimaler Wert für diesen Inhaltstyp basierend auf deiner Historie (Qualität ${optimal}).`;
    } else if (currentVal > optimal) {
        el.textContent = `Deine Historie zeigt, dass dieser Inhaltstyp auch mit Qualität ${optimal} ohne sichtbaren Qualitätsverlust gut komprimiert wird (spart mehr Platz).`;
    } else {
        el.textContent = `Dieser Wert liegt unter dem empfohlenen Optimum von Qualität ${optimal}. Es könnte zu sichtbaren Kompressionsartefakten kommen.`;
    }
    el.classList.remove("hidden");
}
