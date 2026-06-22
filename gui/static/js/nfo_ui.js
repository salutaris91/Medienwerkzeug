export function updateMwDataPanel(container, urlSpan, syncSpan, mwData) {
    if (!container) return;
    
    if (mwData && (mwData.source_url || mwData.last_sync)) {
        container.classList.remove("hidden");
        
        if (urlSpan) {
            if (mwData.source_url) {
                urlSpan.textContent = "Quell-URL: ";
                urlSpan.classList.remove("hidden");
                
                const link = document.createElement("a");
                link.href = mwData.source_url;
                link.textContent = mwData.source_url;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.style.color = "var(--primary)";
                link.style.textDecoration = "underline";
                
                urlSpan.appendChild(link);
            } else {
                urlSpan.classList.add("hidden");
                urlSpan.textContent = "";
            }
        }
        
        if (syncSpan) {
            if (mwData.last_sync) {
                try {
                    const formattedDate = new Date(mwData.last_sync).toLocaleString("de-DE");
                    syncSpan.textContent = `Letzter Sync: ${formattedDate}`;
                    syncSpan.classList.remove("hidden");
                } catch (e) {
                    syncSpan.textContent = `Letzter Sync: ${mwData.last_sync}`;
                    syncSpan.classList.remove("hidden");
                }
            } else {
                syncSpan.classList.add("hidden");
                syncSpan.textContent = "";
            }
        }
    } else {
        container.classList.add("hidden");
        if (urlSpan) {
            urlSpan.textContent = "";
            urlSpan.classList.add("hidden");
        }
        if (syncSpan) {
            syncSpan.textContent = "";
            syncSpan.classList.add("hidden");
        }
    }
}

export function prepareSeriesPayload(selectedShow, basePayload) {
    if (!selectedShow || !basePayload) return basePayload || {};
    
    const payload = { ...basePayload };
    if (selectedShow.mw_data) {
        payload.mw_data = selectedShow.mw_data;
        if (selectedShow.mw_data.source_url) {
            payload.source_url = selectedShow.mw_data.source_url;
        }
        if (selectedShow.mw_data.resolved_topic) {
            payload.resolved_topic = selectedShow.mw_data.resolved_topic;
        }
    }
    return payload;
}
