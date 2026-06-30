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
        let icon = "🎥";
        if (ct === "movie") { label = "Filme"; icon = "🎬"; }
        else if (ct === "live_action") { label = "Serien"; icon = "📺"; }
        else if (ct === "doku") { label = "Dokus"; icon = "🌿"; }
        else if (ct === "anime") { label = "Animes"; icon = "🌸"; }

        html += `
            <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-light); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 4px;">
                <span style="font-size: 0.95em; display: flex; align-items: center; gap: 6px;">
                    <span>${icon}</span> <strong>${label}</strong>
                </span>
                <span style="font-size: 0.9em; color: var(--text-main);">Optimal: CRF <strong>${info.optimal_quality}</strong></span>
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
        el.textContent = "Noch keine historischen Daten für diesen Inhaltstyp vorhanden. Standardempfehlung ist CRF 60.";
        el.classList.remove("hidden");
        return;
    }

    const optimal = recInfo.optimal_quality;
    if (currentVal === optimal) {
        el.textContent = `Optimaler Wert für diesen Inhaltstyp basierend auf deiner Historie (CRF ${optimal}).`;
    } else if (currentVal > optimal) {
        el.textContent = `Deine Historie zeigt, dass dieser Inhaltstyp auch mit CRF ${optimal} ohne sichtbaren Qualitätsverlust gut komprimiert wird (spart mehr Platz).`;
    } else {
        el.textContent = `Dieser Wert liegt unter dem empfohlenen Optimum von CRF ${optimal}. Es könnte zu sichtbaren Kompressionsartefakten kommen.`;
    }
    el.classList.remove("hidden");
}
