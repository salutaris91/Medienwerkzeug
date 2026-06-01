// ==========================================================================
// STATE MANAGEMENT
// ==========================================================================
let currentProject = "";
let projectFiles = [];
let currentProjectIsDoku = false;
let currentProjectSuggestedQuery = "";
let selectedShow = null;
let selectedMovie = null;
let episodesData = {}; // maps episode number (string) to title/info
let fetchedEpisodeMetadataCache = {}; // caches fetched episode metadata: provider_showid_season_episode -> {title, plot, aired}
let eventSource = null;
let isManualMovieMode = false;
let isManualSeriesMode = false;
let allLocalProfiles = [];
let selectShowRequestId = 0;

// YouTube Downloader states
let ytFetchedInfo = null;
let ytSelectedMovie = null;
let ytSelectedShow = null;
let ytEpisodesData = {};
let activeYtTaskId = null;
let ytStatusInterval = null;
let ytDownloaderMergeMode = false;
let ytDownloaderMergeItems = [];
let ytDownloaderMergeSubId = null;
function escapeHTML(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function getCatIdBySub(sub, fallbackId) {
    const cats = (typeof currentSettings !== "undefined" && currentSettings.sync_categories) || [];
    const found = cats.find(c => c.nas_sub === sub);
    return found ? found.id : fallbackId;
}

// ==========================================================================
// NAS SEASONS INFO
// ==========================================================================
async function fetchNasSeasons(requestId = null) {
    const targetRequestId = requestId !== null ? requestId : selectShowRequestId;
    const folderInput = document.getElementById("series-nas-folder-override");
    const destSelect = document.getElementById("series-nas-destination");
    const infoContainer = document.getElementById("selected-show-nas-seasons-info");
    if (!infoContainer) return;
    
    const folderName = folderInput ? folderInput.value.trim() : "";
    if (!folderName) {
        infoContainer.innerHTML = "";
        return;
    }
    
    const destId = destSelect ? destSelect.value : "";
    infoContainer.innerHTML = '<span style="color:var(--text-muted); font-style:italic;">Lade Staffelinfo vom NAS...</span>';
    
    let url = `/api/nas-seasons?folder=${encodeURIComponent(folderName)}&destination_id=${encodeURIComponent(destId)}`;
    if (window.disableNasFuzzyMatch) {
        url += "&exact=1";
    }
    
    try {
        const res = await fetch(url);
        if (targetRequestId !== selectShowRequestId) return;
        if (!res.ok) throw new Error("Fehler beim Laden");
        const data = await res.json();
        if (targetRequestId !== selectShowRequestId) return;
        
        // 1. Check if the backend matched a different destination category
        if (data.matched_destination_id && destSelect && destSelect.value !== data.matched_destination_id) {
            window.isProgrammaticCategoryChange = true;
            try {
                destSelect.value = data.matched_destination_id;
                destSelect.dispatchEvent(new Event('change', { bubbles: true }));
                if (typeof appendConsoleLog === "function") {
                    appendConsoleLog(`[System]: Serie in anderer Kategorie gefunden. Kategorie auf '${destSelect.options[destSelect.selectedIndex].text}' geändert.`);
                }
            } finally {
                window.isProgrammaticCategoryChange = false;
            }
        }
        
        if (data.seasons && data.seasons.length > 0) {
            const badges = data.seasons.map(s => {
                const episodeText = s.episodes === 1 ? "1 Episode" : `${s.episodes} Episoden`;
                const sourceText = s.source ? ` [${s.source}]` : "";
                return `<span style="display:inline-block; padding:2px 8px; margin:2px 4px 2px 0; border-radius:var(--radius-sm); background:rgba(139,92,246,0.15); color:var(--accent); font-size:11px; font-weight:500;">${s.name} <span style='opacity:0.7'>(${episodeText})${sourceText}</span></span>`;
            }).join("");
            
            infoContainer.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; background: rgba(255, 179, 0, 0.05); padding: 8px; border-radius: 6px; border: 1px solid rgba(255, 179, 0, 0.2);">
                    <div>
                        <span style="font-size:11px; color:var(--text-muted);">📂 Auf NAS vorhanden:</span><br>${badges}
                    </div>
                    <button class="btn btn-xs" style="background:var(--error); color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer; flex-shrink: 0;" onclick="clearNasOverride()" title="Falsche NAS-Zuordnung trennen und Serie als neu anlegen">❌ Falscher NAS-Ordner?</button>
                </div>
            `;
            
            // 2. Auto-check absolute numbering if only Staffel 1 exists
            if (data.seasons.length === 1) {
                const sName = data.seasons[0].name.toLowerCase();
                if (sName === "staffel 1" || sName === "season 1") {
                    const absoluteCb = document.getElementById("series-option-absolute-numbering");
                    if (absoluteCb && !absoluteCb.checked) {
                        absoluteCb.checked = true;
                        absoluteCb.dispatchEvent(new Event('change', { bubbles: true }));
                        if (typeof appendConsoleLog === "function") {
                            appendConsoleLog("[System]: Nur Staffel 1 auf NAS gefunden. Absolute Nummerierung wurde automatisch aktiviert.");
                        }
                    }
                }
            }
        } else {
            infoContainer.innerHTML = '<span style="font-size:11px; color:var(--text-muted);">📂 Keine Staffeln auf dem NAS gefunden.</span>';
        }
    } catch (e) {
        console.error("Error fetching NAS seasons:", e);
        infoContainer.innerHTML = "";
    }
}

async function fetchYtNasSeasons() {
    const folderInput = document.getElementById("yt-series-nas-folder-override");
    const destSelect = document.getElementById("yt-nas-destination");
    const infoContainer = document.getElementById("yt-selected-series-nas-seasons-info");
    if (!infoContainer) return;
    
    const folderName = folderInput ? folderInput.value.trim() : "";
    if (!folderName) {
        infoContainer.innerHTML = "";
        return;
    }
    
    const destId = destSelect ? destSelect.value : "";
    infoContainer.innerHTML = '<span style="color:var(--text-muted); font-style:italic;">Lade Staffelinfo vom NAS...</span>';
    
    try {
        const res = await fetch(`/api/nas-seasons?folder=${encodeURIComponent(folderName)}&destination_id=${encodeURIComponent(destId)}`);
        if (!res.ok) throw new Error("Fehler beim Laden");
        const data = await res.json();
        
        if (data.seasons && data.seasons.length > 0) {
            const badges = data.seasons.map(s => {
                const episodeText = s.episodes === 1 ? "1 Episode" : `${s.episodes} Episoden`;
                const sourceText = s.source ? ` [${s.source}]` : "";
                return `<span style="display:inline-block; padding:2px 8px; margin:2px 4px 2px 0; border-radius:var(--radius-sm); background:rgba(139,92,246,0.15); color:var(--accent); font-size:11px; font-weight:500;">${s.name} <span style='opacity:0.7'>(${episodeText})${sourceText}</span></span>`;
            }).join("");
            infoContainer.innerHTML = `<span style="font-size:11px; color:var(--text-muted);">📂 Auf NAS vorhanden:</span><br>${badges}`;
        } else {
            infoContainer.innerHTML = '<span style="font-size:11px; color:var(--text-muted);">📂 Keine Staffeln auf dem NAS gefunden.</span>';
        }
    } catch (e) {
        console.error("Error fetching YT NAS seasons:", e);
        infoContainer.innerHTML = "";
    }
}

// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    // Apply theme from localStorage immediately to prevent flashes on load
    const savedTheme = localStorage.getItem("app_theme");
    if (savedTheme) {
        applyTheme(savedTheme);
    }

    initViews();
    initConsole();
    initEventListeners();
    initQueue();
    
    // Load settings and status immediately
    loadSettings().then(() => {
        triggerLaunchQuote();
        // initCardParallaxAndGlow();
    });
    
    const themeSelect = document.getElementById("settings-app-theme");
    if (themeSelect) {
        themeSelect.addEventListener("change", async function() {
            const newTheme = this.value;
            applyTheme(newTheme);
            
            // Auto-save setting to backend settings.json
            if (currentSettings) {
                currentSettings.app_theme = newTheme;
                try {
                    const payload = {
                        ...currentSettings,
                        app_theme: newTheme,
                        import_sources: (currentSettings.import_sources || []).filter(s => s.trim() !== ""),
                        sync_categories: (currentSettings.sync_categories || []).filter(c => c.id.trim() !== "" && c.name.trim() !== ""),
                        local_download_folders: (currentSettings.local_download_folders || []).filter(f => f.path && f.path.trim() !== "")
                    };
                    await fetch("/api/settings", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                } catch (e) {
                    console.error("Fehler beim automatischen Speichern des Themes:", e);
                }
            }
        });
    }
    
    loadStatus();
    loadConversionRecommendations();
    initHealthDashboard();
    initDuplicateDashboard();
    initNormalizeTool();
    initNasRenamerTool();
    applyStorageTargetLabels();

    // Periodic status check (every 6 seconds)
    setInterval(loadStatus, 6000);
    
    setupNasFolderAutocomplete("series-nas-folder-override", "series-nas-folder-dropdown", "btn-load-nas-series", "series-nas-destination");
    setupNasFolderAutocomplete("yt-series-nas-folder-override", "yt-series-nas-folder-dropdown", "btn-load-yt-nas-series", "yt-nas-destination");

    // Register change listeners to update existing NAS seasons info
    const seriesNasDest = document.getElementById("series-nas-destination");
    if (seriesNasDest) {
        seriesNasDest.addEventListener("change", fetchNasSeasons);
    }
    const seriesOverrideInput = document.getElementById("series-nas-folder-override");
    if (seriesOverrideInput) {
        seriesOverrideInput.addEventListener("input", () => {
            window.nasFolderSelected = seriesOverrideInput.value;
        });
        seriesOverrideInput.addEventListener("change", () => {
            fetchNasSeasons();
            if (window.selectedShow) fetchEpisodes();
        });
    }
    
    const ytNasDest = document.getElementById("yt-nas-destination");
    if (ytNasDest) {
        ytNasDest.addEventListener("change", fetchYtNasSeasons);
    }
    const ytOverrideInput = document.getElementById("yt-series-nas-folder-override");
    if (ytOverrideInput) {
        ytOverrideInput.addEventListener("input", () => {
            window.ytNasFolderSelected = ytOverrideInput.value;
        });
        ytOverrideInput.addEventListener("change", fetchYtNasSeasons);
    }
    
    // Automatically match pCloud destination with NAS destination
    if (seriesNasDest) {
        seriesNasDest.addEventListener("change", (e) => {
            if (window.isProgrammaticCategoryChange) return;
            const pcloudDest = document.getElementById("series-pcloud-destination");
            if (pcloudDest) {
                pcloudDest.value = e.target.value;
                pcloudDest.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
    if (ytNasDest) {
        ytNasDest.addEventListener("change", (e) => {
            if (window.isProgrammaticCategoryChange) return;
            const pcloudDest = document.getElementById("yt-pcloud-destination");
            if (pcloudDest) {
                pcloudDest.value = e.target.value;
                pcloudDest.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
    const movieNasDest = document.getElementById("movie-nas-destination");
    if (movieNasDest) {
        movieNasDest.addEventListener("change", (e) => {
            if (window.isProgrammaticCategoryChange) return;
            const pcloudDest = document.getElementById("movie-pcloud-destination");
            if (pcloudDest) {
                pcloudDest.value = e.target.value;
                pcloudDest.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
});

// ==========================================================================
// NAS RENAMER TOOL
// ==========================================================================
let renamerPreviewPlan = [];

function initNasRenamerTool() {
    setupNasFolderAutocomplete("renamer-nas-folder", "renamer-nas-folder-dropdown", "btn-load-renamer-series", "renamer-nas-destination");
    
    const btnPreview = document.getElementById("btn-renamer-preview");
    if (btnPreview) btnPreview.addEventListener("click", loadNasRenamerPreview);
    
    const btnApply = document.getElementById("btn-renamer-apply");
    if (btnApply) btnApply.addEventListener("click", applyNasRenamer);
    
    const btnSelectAll = document.getElementById("btn-renamer-select-all");
    if (btnSelectAll) btnSelectAll.addEventListener("click", () => setNasRenamerSelection(true));
    
    const btnDeselectAll = document.getElementById("btn-renamer-deselect-all");
    if (btnDeselectAll) btnDeselectAll.addEventListener("click", () => setNasRenamerSelection(false));
    
    const btnRollback = document.getElementById("btn-renamer-rollback");
    if (btnRollback) btnRollback.addEventListener("click", rollbackNasRenamer);
    
    // Automatically fill Destination Dropdown
    const destSelect = document.getElementById("renamer-nas-destination");
    if (destSelect && typeof currentSettings !== "undefined" && currentSettings.sync_categories) {
        destSelect.innerHTML = currentSettings.sync_categories.map(c => 
            `<option value="${c.id}">${c.name} (${c.nas_sub})</option>`
        ).join("");
    }
}

async function loadNasRenamerPreview() {
    const statusEl = document.getElementById("renamer-status");
    const container = document.getElementById("renamer-preview-container");
    const tbody = document.getElementById("renamer-preview-tbody");
    
    const destId = document.getElementById("renamer-nas-destination").value;
    const folderName = document.getElementById("renamer-nas-folder").value.trim();
    
    if (!folderName) {
        if (statusEl) statusEl.textContent = "Bitte einen Ordnernamen angeben.";
        return;
    }
    
    if (statusEl) statusEl.textContent = "Scanne Ordner und lade Metadaten...";
    if (container) container.classList.add("hidden");
    if (tbody) tbody.innerHTML = "";
    
    try {
        const res = await fetch("/api/nas-renamer/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ destination_id: destId, folder_name: folderName })
        });
        const data = await res.json();
        
        if (data.status === "error") {
            if (statusEl) statusEl.innerHTML = `<span style="color: var(--danger);">${escapeHTML(data.message)}</span>`;
            return;
        }
        
        renamerPreviewPlan = data.items || [];
        renderNasRenamerPreview();
        
        if (statusEl) {
            statusEl.textContent = `Provider: ${data.provider} | ID: ${data.show_id} | ${renamerPreviewPlan.length} Video-Dateien gefunden.`;
        }
        if (container) container.classList.remove("hidden");
        
    } catch (e) {
        console.error("Error generating preview", e);
        if (statusEl) statusEl.textContent = "Fehler bei der Vorschau.";
    }
}

function renderNasRenamerPreview() {
    const tbody = document.getElementById("renamer-preview-tbody");
    if (!tbody) return;
    
    let html = "";
    let currentSeason = -1;
    
    renamerPreviewPlan.forEach((item, index) => {
        // Render season group header if season changed
        if (item.season !== null && item.season !== currentSeason) {
            currentSeason = item.season;
            html += `
                <tr style="background: rgba(255,255,255,0.05);">
                    <td colspan="5" style="padding: 8px;">
                        <label style="display:flex; align-items:center; gap:8px; font-weight:bold; cursor:pointer;">
                            <input type="checkbox" class="renamer-season-toggle" data-season="${currentSeason}" checked>
                            Staffel ${currentSeason}
                        </label>
                    </td>
                </tr>
            `;
        }
        
        let statusBadge = "";
        let isChecked = false;
        let isRowDisabled = false;
        let ext = item.current_filename.substring(item.current_filename.lastIndexOf('.'));
        
        if (item.status === "passt_bereits") {
            statusBadge = '<span style="color: var(--success); font-size: 0.85em;">✅ Passt</span>';
            isRowDisabled = true;
        } else if (item.status === "kein_treffer") {
            statusBadge = '<span style="color: var(--warning); font-size: 0.85em;">⚠️ Kein Treffer</span>';
            // User requirement: Fallback input for manual assign
            // We'll replace the "Vorgeschlagener Pfad" with an input field
        } else {
            statusBadge = '<span style="color: var(--accent); font-size: 0.85em;">🔄 Anpassen</span>';
            isChecked = true;
        }
        
        let proposedHtml = "";
        if (item.status === "kein_treffer") {
            proposedHtml = `
                <div style="display: flex; gap: 5px; align-items: center;">
                    <input type="text" class="renamer-manual-input" data-idx="${index}" placeholder="z.B. S01E02 - Titel" style="width: 100%; padding: 4px; font-size: 0.85em; border-radius: 4px; border: 1px solid var(--border-light); background: var(--bg-surface);">
                    <span style="font-size: 0.85em; color: var(--text-muted);">${ext}</span>
                </div>
            `;
            // Uncheck by default if no match
            isChecked = false;
        } else {
            proposedHtml = `<span style="word-break: break-all;">${escapeHTML(item.proposed_rel_path)}</span>`;
        }
        
        const seBadge = (item.season !== null && item.episode !== null) ? `S${String(item.season).padStart(2,'0')}E${String(item.episode).padStart(2,'0')}` : "?";
        
        html += `
            <tr style="${isRowDisabled ? 'opacity: 0.6;' : ''}">
                <td style="text-align: center;">
                    <input type="checkbox" class="renamer-item-checkbox season-${currentSeason}" data-idx="${index}" ${isChecked ? 'checked' : ''} ${isRowDisabled ? 'disabled' : ''}>
                </td>
                <td>${statusBadge}</td>
                <td><span style="font-size: 0.8em; background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${seBadge}</span></td>
                <td style="word-break: break-all; font-size: 0.9em;">${escapeHTML(item.rel_path)}</td>
                <td style="font-size: 0.9em;">${proposedHtml}</td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
    
    // Attach listeners
    tbody.querySelectorAll(".renamer-item-checkbox").forEach(cb => cb.addEventListener("change", updateNasRenamerApplyCount));
    
    tbody.querySelectorAll(".renamer-season-toggle").forEach(toggle => {
        toggle.addEventListener("change", (e) => {
            const season = e.target.getAttribute("data-season");
            const isChecked = e.target.checked;
            tbody.querySelectorAll(`.renamer-item-checkbox.season-${season}:not([disabled])`).forEach(cb => {
                cb.checked = isChecked;
            });
            updateNasRenamerApplyCount();
        });
    });
    
    tbody.querySelectorAll(".renamer-manual-input").forEach(input => {
        input.addEventListener("input", (e) => {
            const idx = e.target.getAttribute("data-idx");
            const cb = tbody.querySelector(`.renamer-item-checkbox[data-idx="${idx}"]`);
            if (e.target.value.trim() !== "") {
                cb.checked = true;
                
                // Update the plan data
                let ext = renamerPreviewPlan[idx].current_filename.substring(renamerPreviewPlan[idx].current_filename.lastIndexOf('.'));
                let targetDir = renamerPreviewPlan[idx].rel_path.substring(0, renamerPreviewPlan[idx].rel_path.lastIndexOf('/'));
                if (targetDir === renamerPreviewPlan[idx].rel_path) targetDir = "";
                
                renamerPreviewPlan[idx].proposed_rel_path = (targetDir ? targetDir + '/' : '') + e.target.value.trim() + ext;
                renamerPreviewPlan[idx].status = "manuell"; // Mark as manually edited
                
            } else {
                cb.checked = false;
            }
            updateNasRenamerApplyCount();
        });
    });
    
    updateNasRenamerApplyCount();
}

function setNasRenamerSelection(checked) {
    const tbody = document.getElementById("renamer-preview-tbody");
    if (!tbody) return;
    
    tbody.querySelectorAll(".renamer-item-checkbox:not([disabled])").forEach(cb => {
        cb.checked = checked;
    });
    tbody.querySelectorAll(".renamer-season-toggle").forEach(cb => {
        cb.checked = checked;
    });
    updateNasRenamerApplyCount();
}

function updateNasRenamerApplyCount() {
    const tbody = document.getElementById("renamer-preview-tbody");
    const applyBtn = document.getElementById("btn-renamer-apply");
    const countEl = document.getElementById("renamer-selected-count");
    if (!tbody || !applyBtn || !countEl) return;
    
    const checkedBoxes = Array.from(tbody.querySelectorAll(".renamer-item-checkbox:checked"));
    countEl.textContent = `${checkedBoxes.length} Dateien ausgewählt`;
    applyBtn.disabled = checkedBoxes.length === 0;
}

async function applyNasRenamer() {
    const tbody = document.getElementById("renamer-preview-tbody");
    const applyBtn = document.getElementById("btn-renamer-apply");
    const statusEl = document.getElementById("renamer-status");
    
    const destId = document.getElementById("renamer-nas-destination").value;
    const folderName = document.getElementById("renamer-nas-folder").value.trim();
    
    const checkedBoxes = Array.from(tbody.querySelectorAll(".renamer-item-checkbox:checked"));
    const planToApply = checkedBoxes.map(cb => {
        const idx = parseInt(cb.getAttribute("data-idx"));
        return renamerPreviewPlan[idx];
    });
    
    if (planToApply.length === 0) return;
    
    if (!confirm(`Sollen ${planToApply.length} Dateien jetzt umbenannt werden?`)) return;
    
    applyBtn.disabled = true;
    if (statusEl) statusEl.textContent = "Wende Umbenennungen an...";
    
    try {
        const res = await fetch("/api/nas-renamer/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                destination_id: destId, 
                folder_name: folderName,
                rename_plan: planToApply
            })
        });
        const data = await res.json();
        
        if (data.status === "error") {
            if (statusEl) statusEl.innerHTML = `<span style="color: var(--danger);">Fehler: ${escapeHTML(data.message)}</span>`;
            applyBtn.disabled = false;
            return;
        }
        
        if (statusEl) {
            statusEl.innerHTML = `<span style="color: var(--success);">✅ ${data.success_count} Dateien erfolgreich umbenannt.</span>`;
            if (data.errors && data.errors.length > 0) {
                statusEl.innerHTML += `<br><span style="color: var(--warning);">${data.errors.length} Fehler aufgetreten (siehe Konsole).</span>`;
                console.warn("Renamer Errors:", data.errors);
            }
        }
        
        // Show Rollback Container
        const rollbackContainer = document.getElementById("renamer-rollback-container");
        const rollbackInfo = document.getElementById("renamer-last-transaction-info");
        if (rollbackContainer && rollbackInfo && data.transaction_id) {
            rollbackContainer.setAttribute("data-transaction-id", data.transaction_id);
            rollbackInfo.textContent = `Transaktions-ID: ${data.transaction_id}`;
            rollbackContainer.style.display = "block";
        }
        
        // Refresh preview
        setTimeout(loadNasRenamerPreview, 1000);
        
    } catch (e) {
        console.error("Error applying renames", e);
        if (statusEl) statusEl.textContent = "Netzwerkfehler beim Anwenden.";
        applyBtn.disabled = false;
    }
}

async function rollbackNasRenamer() {
    const rollbackContainer = document.getElementById("renamer-rollback-container");
    const transactionId = rollbackContainer.getAttribute("data-transaction-id");
    const statusEl = document.getElementById("renamer-status");
    
    if (!transactionId) return;
    
    if (!confirm("Sollen die letzten Umbenennungen wirklich rückgängig gemacht werden?")) return;
    
    if (statusEl) statusEl.textContent = "Führe Rollback aus...";
    
    try {
        const res = await fetch("/api/nas-renamer/rollback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transaction_id: transactionId })
        });
        const data = await res.json();
        
        if (data.status === "error") {
            if (statusEl) statusEl.innerHTML = `<span style="color: var(--danger);">Fehler beim Rollback: ${escapeHTML(data.message)}</span>`;
            return;
        }
        
        if (statusEl) {
            statusEl.innerHTML = `<span style="color: var(--success);">✅ Rollback erfolgreich (${data.success_count} Dateien wiederhergestellt).</span>`;
        }
        
        rollbackContainer.style.display = "none";
        rollbackContainer.removeAttribute("data-transaction-id");
        
        // Refresh preview
        setTimeout(loadNasRenamerPreview, 1000);
        
    } catch (e) {
        console.error("Error during rollback", e);
        if (statusEl) statusEl.textContent = "Netzwerkfehler beim Rollback.";
    }
}
// ==========================================================================
// UTILS / HELPERS
// ==========================================================================
function cleanSeriesName(name) {
    if (!name) return "";
    // Remove search suffixes in parentheses (case-insensitive)
    let cleaned = name.replace(/\s*\((Mediathek\s+(Serie|Film)\s+aus\s+URL|Freie\s+Mediathek-Suche|fernsehserien\.de\s+URL|\d*\s*Videos?\s+via\s+URL)\)/gi, '');
    // Remove trailing channel tag in brackets, e.g., [ARTE], [ARTE.DE], [TMDB_TV], [US]
    let prev;
    do {
        prev = cleaned;
        cleaned = cleaned.replace(/\s*\[[a-zA-Z0-9\._-]+\]\s*$/, '');
    } while (cleaned !== prev);
    // Replace underscores with spaces
    cleaned = cleaned.replace(/_/g, ' ');
    return cleaned.trim();
}
function scrollToDetailTop() {
    // 1. Scroll main window / document root (used in responsive/zoomed layouts)
    window.scrollTo({ top: 0, behavior: 'instant' });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    // 2. Scroll the detail panel container (used in standard desktop layout)
    const detailContent = document.querySelector(".detail-content");
    if (detailContent) {
        detailContent.scrollTop = 0;
    }
}

// ==========================================================================
// VIEW ROUTING (MASTER-DETAIL)
// ==========================================================================
function initViews() {
    const goHome = () => {
        document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
        
        // Hide all views and show empty view (welcome homepage)
        document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
        const emptyView = document.getElementById("view-empty");
        if (emptyView) {
            emptyView.classList.remove("hidden");
            emptyView.classList.add("active");
        }
        
        // Clear active project
        currentProject = "";
        
        // Refresh homepage data immediately
        loadStatus();
        
        // Reset scroll position to top
        scrollToDetailTop();
    };
    window.goHome = goHome;

    const btnHome = document.getElementById("master-btn-home");
    if(btnHome) {
        btnHome.addEventListener("click", goHome);
    }
    
    const modes = ["movie", "series", "tools"];
    modes.forEach(mode => {
        const card = document.getElementById(`mode-${mode}`);
        if(card) {
            card.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    card.click();
                }
            });
            card.addEventListener("click", () => {
                // UI styling
                modes.forEach(m => {
                    const el = document.getElementById(`mode-${m}`);
                    if (el) {
                        el.classList.remove("active");
                        el.setAttribute("aria-checked", "false");
                    }
                });
                card.classList.add("active");
                card.setAttribute("aria-checked", "true");
                
                document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
                
                // Reset/close collapsible details
                const movieDetails = document.getElementById("movie-nfo-details");
                if (movieDetails) movieDetails.removeAttribute("open");
                const seriesDetails = document.getElementById("series-nfo-details");
                if (seriesDetails) seriesDetails.removeAttribute("open");
                
                let ctxTarget = `context-${mode}`;
                const ctx = document.getElementById(ctxTarget);
                if(ctx) {
                    ctx.classList.remove("hidden");
                    
                    // Autofill logic based on current project
                    let cleanedQuery = currentProjectSuggestedQuery || currentProject;
                    if (cleanedQuery) {
                        cleanedQuery = cleanedQuery.replace(/[._\-]/g, " ").trim();
                        cleanedQuery = cleanedQuery.replace(/\([0-9]{4}\)/g, "").trim();
                    }
                    

                    
                    if (mode === "movie") {
                        const isDoku = currentProjectIsDoku || (cleanedQuery && (cleanedQuery.toLowerCase().includes("doku") || cleanedQuery.toLowerCase().includes("dokumentation")));
                        
                        if (isDoku) {
                            document.getElementById("context-movie-header").innerText = "Doku verarbeiten";
                            document.getElementById("movie-nas-destination").value = getCatIdBySub("/Dokus/Einzelne Dokus", "3");
                            document.getElementById("movie-pcloud-destination").value = getCatIdBySub("/Dokus/Einzelne Dokus", "3");
                        } else {
                            document.getElementById("context-movie-header").innerText = "Film verarbeiten";
                            document.getElementById("movie-nas-destination").value = getCatIdBySub("/Filme", "1");
                            document.getElementById("movie-pcloud-destination").value = getCatIdBySub("/Filme", "1");
                        }
                        
                        document.getElementById("movie-search-query").value = cleanedQuery;
                        searchMovie();
                        updateSizeEstimation("movie");
                        triggerQualityHintUpdates();
                    } else if (mode === "series") {
                        document.getElementById("series-nas-destination").value = getCatIdBySub("/Serien", "2");
                        document.getElementById("series-pcloud-destination").value = getCatIdBySub("/Serien", "2");
                        document.getElementById("series-search-query").value = cleanedQuery;
                        detectExistingSeries(currentProject);
                        updateSizeEstimation("series");
                        triggerQualityHintUpdates();
                    }
                }
            });
        }
    });
    
    // Dashboard Nav
    const navDashboard = document.getElementById("nav-dashboard");

    // Tools Dashboard Nav
    const navTools = document.getElementById("nav-tools-dashboard");
    if(navTools) {
        navTools.addEventListener("click", () => {
            // Remove active from inbox items
            document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
            navTools.classList.add("active");
            if(navDashboard) navDashboard.classList.remove("active");
            
            // Show only tools view
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById("view-tools").classList.remove("hidden");
            scrollToDetailTop();
            
            // Auto-fill path if a project was selected
            const pathInput = document.getElementById("tools-target-path");
            if(currentProject && !pathInput.value) {
                pathInput.value = currentProject;
            }
        });
    }

    // YouTube Downloader Nav
    const navYtDownloader = document.getElementById("nav-youtube-downloader");
    if (navYtDownloader) {
        navYtDownloader.addEventListener("click", () => {
            document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
            navYtDownloader.classList.add("active");
            
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            const ytView = document.getElementById("view-youtube");
            if (ytView) {
                ytView.classList.remove("hidden");
                ytView.classList.add("active");
            }
            scrollToDetailTop();
            
            // Clear active project
            currentProject = "";
        });
    }

    // Click on top logo goes home
    const headerLogo = document.querySelector(".header-logo");
    if (headerLogo) {
        headerLogo.addEventListener("click", goHome);
    }

    // Quick YouTube Abos page link on Welcome Dashboard
    window.openYoutubeAbosPage = function() {
        document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
        const navDashboard = document.getElementById("nav-dashboard");
        if(navDashboard) navDashboard.classList.remove("active");
        const navTools = document.getElementById("nav-tools-dashboard");
        if(navTools) navTools.classList.remove("active");
        const navSettings = document.getElementById("nav-settings-dashboard");
        if(navSettings) navSettings.classList.remove("active");
        
        document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
        const abosView = document.getElementById("view-youtube-abos");
        if (abosView) {
            abosView.classList.remove("hidden");
            abosView.classList.add("active");
        }
        
        loadSubscriptions();
        scrollToDetailTop();
        currentProject = "";
    };

    const btnHeroYtAbos = document.getElementById("btn-hero-yt-abos");
    if (btnHeroYtAbos) {
        btnHeroYtAbos.addEventListener("click", window.openYoutubeAbosPage);
    }

    if(navDashboard) {
        navDashboard.addEventListener("click", () => {
            document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
            navDashboard.classList.add("active");
            if(navTools) navTools.classList.remove("active");
            if(navSettings) navSettings.classList.remove("active");
            
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById("view-dashboard").classList.remove("hidden");
            document.getElementById("view-dashboard").classList.add("active");
            
            loadDashboard();
            scrollToDetailTop();
        });
    }

    // Bibliothek & Wartung Nav (NAS-Check + Duplikate)
    const navLibrary = document.getElementById("nav-library");
    function openLibraryView() {
        document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
        if (navLibrary) navLibrary.classList.add("active");
        document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
        const lib = document.getElementById("view-library");
        if (lib) { lib.classList.remove("hidden"); lib.classList.add("active"); }
        // Gecachte Scan-Ergebnisse beim Öffnen aktualisieren
        if (typeof pollHealthStatus === "function") pollHealthStatus(false);
        if (typeof pollDuplicateStatus === "function") pollDuplicateStatus(false);
        scrollToDetailTop();
    }
    window.openLibraryView = openLibraryView;
    if (navLibrary) navLibrary.addEventListener("click", openLibraryView);
    const cardHeroLibrary = document.getElementById("card-hero-library");
    if (cardHeroLibrary) cardHeroLibrary.addEventListener("click", openLibraryView);

    // Settings Dashboard Nav
    const navSettings = document.getElementById("nav-settings-dashboard");
    if(navSettings) {
        navSettings.addEventListener("click", () => {
            document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
            navSettings.classList.add("active");
            if(navDashboard) navDashboard.classList.remove("active");
            if(navTools) navTools.classList.remove("active");
            
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById("view-settings").classList.remove("hidden");
            
            loadSettings();
            scrollToDetailTop();
        });
    }

    // Set up collapsible sidebar sections
    setupCollapsibleSections();
}

function setupCollapsibleSections() {
    document.querySelectorAll(".collapsible-section").forEach(sec => {
        const header = sec.querySelector(".section-header");
        const content = sec.querySelector(".section-content");
        if (!header || !content) return;
        
        const secId = sec.id;
        
        // Restore expanded state from localStorage (default to false - collapsed by default)
        // For project folders, we always start collapsed on page load
        const isExpanded = secId === "section-project-folders" ? false : (localStorage.getItem(`expanded_${secId}`) === "true");
        if (isExpanded) {
            sec.classList.add("expanded");
            content.style.maxHeight = "none";
            content.style.opacity = "1";
        } else {
            sec.classList.remove("expanded");
            content.style.maxHeight = "0px";
            content.style.opacity = "0";
        }
        
        // Toggle function using dynamic heights for a perfectly smooth transition
        const toggleSection = (forceState) => {
            const willExpand = forceState !== undefined ? forceState : !sec.classList.contains("expanded");
            
            if (willExpand) {
                sec.classList.add("expanded");
                // Animate to scrollHeight
                content.style.maxHeight = content.scrollHeight + "px";
                content.style.opacity = "1";
                localStorage.setItem(`expanded_${secId}`, "true");
                
                // Allow overflow-y visible once transition completes so content layout works properly
                setTimeout(() => {
                    if (sec.classList.contains("expanded")) {
                        content.style.maxHeight = "none";
                    }
                }, 1200);
            } else {
                // Set explicit height to start transition
                content.style.maxHeight = content.scrollHeight + "px";
                // Force layout reflow
                content.offsetHeight;
                
                sec.classList.remove("expanded");
                content.style.maxHeight = "0px";
                content.style.opacity = "0";
                localStorage.setItem(`expanded_${secId}`, "false");
            }
        };
        
        header.addEventListener("click", () => toggleSection());
        
        // Expose toggle control for startpage interaction
        sec.toggleSection = toggleSection;
    });
}

// ==========================================================================
// CONSOLE / TERMINAL LOGS
// ==========================================================================
function initConsole() {
    const consoleHeader = document.getElementById("console-header-toggle");
    const appConsole = document.getElementById("app-console");
    const toggleIcon = document.getElementById("console-toggle-btn-icon");
    const clearBtn = document.getElementById("btn-clear-console");
    
    consoleHeader.addEventListener("click", (e) => {
        // Prevent toggle if clicking on clear button
        if (e.target === clearBtn) return;
        
        if (appConsole.classList.contains("collapsed")) {
            appConsole.classList.remove("collapsed");
            appConsole.classList.add("expanded");
            toggleIcon.textContent = "▼";
            document.documentElement.style.setProperty('--console-height', '320px');
        } else {
            appConsole.classList.remove("expanded");
            appConsole.classList.add("collapsed");
            toggleIcon.textContent = "▲";
            document.documentElement.style.setProperty('--console-height', '40px');
        }
    });
    
    clearBtn.addEventListener("click", () => {
        const consoleBody = document.getElementById("console-body-text");
        consoleBody.innerHTML = '<div class="console-line system-line">[System]: Konsole geleert.</div>';
    });

    const showConsoleCheckbox = document.getElementById("settings-show-console");
    if (showConsoleCheckbox) {
        showConsoleCheckbox.addEventListener("change", (e) => {
            applyConsoleVisibility(e.target.checked);
        });
    }
}

function applyConsoleVisibility(show) {
    const appConsole = document.getElementById("app-console");
    if (!appConsole) return;
    
    if (show) {
        appConsole.classList.remove("hidden-console");
        if (appConsole.classList.contains("expanded")) {
            document.documentElement.style.setProperty('--console-height', '320px');
        } else {
            document.documentElement.style.setProperty('--console-height', '40px');
        }
    } else {
        appConsole.classList.add("hidden-console");
        document.documentElement.style.setProperty('--console-height', '0px');
    }
}

function expandConsole() {
    const showConsoleCheckbox = document.getElementById("settings-show-console");
    if (showConsoleCheckbox && !showConsoleCheckbox.checked) {
        return;
    }
    const appConsole = document.getElementById("app-console");
    const toggleIcon = document.getElementById("console-toggle-btn-icon");
    if (appConsole.classList.contains("collapsed")) {
        appConsole.classList.remove("collapsed");
        appConsole.classList.add("expanded");
        toggleIcon.textContent = "▼";
        document.documentElement.style.setProperty('--console-height', '320px');
    }
}

function appendConsoleLog(line) {
    const consoleBody = document.getElementById("console-body-text");
    const div = document.createElement("div");
    div.className = "console-line";
    
    // Styling special logs
    if (line.startsWith("[System]") || line.startsWith("===")) {
        div.classList.add("system-line");
    } else if (line.includes("❌") || line.toLowerCase().includes("error") || line.toLowerCase().includes("fehler")) {
        div.style.color = "var(--danger)";
    } else if (line.includes("✅") || line.includes("successful") || line.includes("erfolgreich")) {
        div.style.color = "var(--success)";
    } else if (line.includes("⏳") || line.includes("convert") || line.includes("konvertiere")) {
        div.style.color = "var(--warning)";
    }
    
    div.textContent = line;
    consoleBody.appendChild(div);
    consoleBody.scrollTop = consoleBody.scrollHeight;
}

function connectLogStream() {
    if (eventSource) {
        eventSource.close();
    }
    
    const pulse = document.getElementById("console-pulse");
    pulse.classList.remove("hidden");
    
    eventSource = new EventSource("/api/logs");
    eventSource.onmessage = function(event) {
        appendConsoleLog(event.data);
        
        if (event.data.includes("=== VORGANG BEENDET ===")) {
            pulse.classList.add("hidden");
            eventSource.close();
            // Refresh status
            setTimeout(loadStatus, 2000);
            if (currentProject) {
                setTimeout(() => scanProject(currentProject), 2000);
            }
        }
    };
    
    eventSource.onerror = function() {
        pulse.classList.add("hidden");
        if (eventSource) {
            eventSource.close();
        }
    };
}

// ==========================================================================
// STATUS & BADGES
// ==========================================================================
async function loadStatus() {
    if (document.hidden) return;
    if (document.visibilityState === "hidden") return;
    try {
        const response = await fetch("/api/status");
        if (!response.ok) return;
        const data = await response.json();
        
        // Update NAS Badge
        const nasBadge = document.getElementById("nas-badge");
        const connectNasBtn = document.getElementById("btn-connect-nas");
        nasBadge.className = "status-badge";
        if (data.nas_status === "connected") {
            nasBadge.textContent = "Verbunden";
            nasBadge.classList.add("online");
            connectNasBtn?.classList.add("hidden");
        } else if (data.nas_status === "available_not_mounted") {
            nasBadge.textContent = "Bereit (Nicht gemountet)";
            nasBadge.classList.add("warning");
            connectNasBtn?.classList.remove("hidden");
        } else {
            nasBadge.textContent = "Offline";
            nasBadge.classList.add("offline");
            connectNasBtn?.classList.remove("hidden");
        }
        
        // Update StreamFab Badge
        const sfBadge = document.getElementById("streamfab-badge");
        const sfBtn = document.getElementById("btn-streamfab-import");
        if (data.streamfab_downloads && data.streamfab_downloads.length > 0) {
            sfBadge.textContent = `${data.streamfab_downloads.length} Datei(en)`;
            sfBadge.className = "status-badge warning";
            sfBtn.classList.remove("hidden");
        } else {
            sfBadge.textContent = "Leer";
            sfBadge.className = "status-badge neutral";
            sfBtn.classList.add("hidden");
        }
        
        // Render project lists (sidebar)
        renderProjectList(data.projects);
        
        // Update Welcome Dashboard if elements exist (includes folder-size warnings)
        if (typeof updateHomepageData === "function") {
            updateHomepageData(data);
        }
        
    } catch (e) {
        console.error("Error fetching status:", e);
    }
}

let activeProjectsProcessing = new Set();
let lastProjectListJson = "";
let lastActiveProject = "";

function renderProjectList(projects) {
    const currentJson = JSON.stringify(projects);
    if (currentJson === lastProjectListJson && currentProject === lastActiveProject) {
        return; // Skip DOM update if data hasn't changed
    }
    lastProjectListJson = currentJson;
    lastActiveProject = currentProject;
    const container = document.getElementById("project-list-container");
    const countEl = document.getElementById("project-folders-count");
    if (countEl) {
        countEl.textContent = projects.length;
    }

    if (projects.length === 0) {
        container.innerHTML = '<p class="text-muted text-center" style="padding: 20px;">Keine Ordner in der Inbox</p>';
        return;
    }
    
    // Save current active list name to keep it selected
    let html = `
        <button class="project-item ${currentProject === "" ? "active" : ""}" data-project="">
            <span class="project-item-icon">📥</span>
            <span class="project-item-name">Unsortierte Einzeldateien</span>
        </button>
        <button class="project-item ${currentProject === "__inbox_recursive__" ? "active" : ""}" data-project="__inbox_recursive__">
            <span class="project-item-icon">📂</span>
            <span class="project-item-name">Alle Dateien (inkl. Unterordner)</span>
        </button>
    `;
    
    projects.forEach(p => {
        const escapedP = escapeHTML(p);
        html += `
            <button class="project-item ${currentProject === p ? "active" : ""}" data-project="${escapedP}" draggable="true">
                <span class="project-item-icon">📁</span>
                <span class="project-item-name">${escapedP}</span>
                <span class="project-item-delete" title="Ordner löschen" data-project="${escapedP}">🗑️</span>
            </button>
        `;
    });
    
    container.innerHTML = html;
    
    // Bind click events
    container.querySelectorAll(".project-item").forEach(item => {
        item.addEventListener("click", (e) => {
            // Prevent selecting the project if delete icon was clicked
            if (e.target.classList.contains("project-item-delete")) {
                return;
            }
            const p = item.getAttribute("data-project");
            selectProject(p);
        });
    });

    // Bind delete events
    container.querySelectorAll(".project-item-delete").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const p = btn.getAttribute("data-project");
            if (confirm(`Möchtest du den Ordner "${p}" und alle darin enthaltenen Dateien wirklich unwiderruflich löschen?`)) {
                await deleteProject(p);
            }
        });
    });
    
    updateSidebarProcessingStates(activeProjectsProcessing);
}

function updateSidebarProcessingStates(activeProjects) {
    if (!activeProjects) activeProjects = new Set();
    
    const items = document.querySelectorAll("#project-list-container .project-item");
    items.forEach(item => {
        const p = item.getAttribute("data-project") || "";
        const iconEl = item.querySelector(".project-item-icon");
        const deleteEl = item.querySelector(".project-item-delete");
        const isProcessing = activeProjects.has(p);
        
        if (isProcessing) {
            item.classList.add("processing");
            if (iconEl) {
                iconEl.textContent = "🔄";
                iconEl.classList.add("spinning-icon");
            }
            if (deleteEl) {
                deleteEl.style.display = "none";
            }
        } else {
            item.classList.remove("processing");
            if (iconEl) {
                iconEl.textContent = p === "" ? "📥" : (p === "__inbox_recursive__" ? "📂" : "📁");
                iconEl.classList.remove("spinning-icon");
            }
            if (deleteEl) {
                deleteEl.style.display = "";
            }
        }
    });

    updateProjectProcessingStatus(activeProjects);
}

function updateProjectProcessingStatus(activeProjects) {
    if (!activeProjects) activeProjects = new Set();
    
    const isCurrentProcessing = activeProjects.has(currentProject || "");
    const warningEl = document.getElementById("project-processing-warning");
    const modeSelector = document.getElementById("folder-mode-selector");
    const cleanBtn = document.getElementById("btn-clean-project");
    
    if (warningEl) {
        if (isCurrentProcessing) {
            warningEl.classList.remove("hidden");
        } else {
            warningEl.classList.add("hidden");
        }
    }
    
    if (modeSelector) {
        if (isCurrentProcessing) {
            modeSelector.style.opacity = "0.5";
            modeSelector.style.pointerEvents = "none";
        } else {
            modeSelector.style.opacity = "1.0";
            modeSelector.style.pointerEvents = "auto";
        }
    }
    
    if (cleanBtn) {
        if (isCurrentProcessing) {
            cleanBtn.style.opacity = "0.5";
            cleanBtn.style.pointerEvents = "none";
        } else {
            cleanBtn.style.opacity = "1.0";
            cleanBtn.style.pointerEvents = "auto";
        }
    }

    // Update Smart Inbox items in DOM reactively
    const smartItems = document.querySelectorAll("#smart-inbox-list .smart-inbox-item");
    smartItems.forEach(item => {
        const p = item.getAttribute("data-project") || "";
        const isProcessing = activeProjects.has(p);
        const btn = item.querySelector(".btn-select-smart");

        if (isProcessing) {
            item.style.border = "1px solid rgba(0, 229, 255, 0.3)";
            item.style.background = "rgba(0, 229, 255, 0.03)";
        } else {
            item.style.border = "1px solid var(--border-light)";
            item.style.background = "rgba(255,255,255,0.02)";
        }
        configureSmartInboxButton(btn, p, isProcessing);
    });
}

function configureSmartInboxButton(btn, projectName, isProcessing) {
    if (!btn) return;

    btn.className = `btn ${isProcessing ? "btn-secondary" : "btn-primary"} btn-sm btn-select-smart`;
    btn.style.whiteSpace = "nowrap";
    btn.style.cursor = isProcessing ? "not-allowed" : "";
    btn.style.opacity = isProcessing ? "0.7" : "";
    btn.disabled = isProcessing;
    btn.innerHTML = isProcessing ? "🔄 In Bearbeitung..." : "⚡ Auswählen";
    btn.onclick = isProcessing
        ? null
        : () => handleSmartInboxClick(
            projectName,
            btn.getAttribute("data-media-type") || "",
            btn.getAttribute("data-suggested-query") || ""
        );
}

async function deleteProject(project) {
    try {
        const response = await fetch("/api/delete-project", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ project })
        });
        const data = await response.json();
        if (data.status === "success") {
            appendConsoleLog(`🗑️ Ordner "${project}" wurde erfolgreich gelöscht.`);
            if (currentProject === project) {
                selectProject("");
            }
            await loadStatus();
        } else {
            alert(`Fehler beim Löschen des Ordners: ${data.error}`);
        }
    } catch (e) {
        console.error("Error deleting project:", e);
        alert(`Netzwerkfehler beim Löschen des Ordners.`);
    }
}

async function splitProjectFile(project, fileName) {
    if (!confirm(`Möchtest du die Datei "${fileName}" und alle zugehörigen Begleitdateien in ein separates Projekt abspalten?`)) {
        return;
    }
    
    try {
        const response = await fetch("/api/split-project-file", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ project, file_name: fileName })
        });
        const data = await response.json();
        if (data.status === "success") {
            appendConsoleLog(`✂️ Datei "${fileName}" wurde in das Projekt "${data.new_project}" abgespalten.`);
            await loadStatus();
            if (data.new_project) {
                selectProject(data.new_project);
            } else {
                selectProject(currentProject);
            }
        } else {
            alert(`Fehler beim Trennen der Datei: ${data.error}`);
        }
    } catch (e) {
        console.error("Error splitting project file:", e);
        alert(`Netzwerkfehler beim Trennen der Datei.`);
    }
}

// ==========================================================================
// SIZE ESTIMATION FOR H.265 CONVERSION
// ==========================================================================
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = 2;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

async function updateSizeEstimation(mediaType) {
    const panelId = mediaType === "movie" ? "movie-size-estimate-panel" : "series-size-estimate-panel";
    const textId = mediaType === "movie" ? "movie-size-estimate-text" : "series-size-estimate-text";
    const convertId = mediaType === "movie" ? "movie-option-convert" : "series-option-convert";
    
    const panel = document.getElementById(panelId);
    const textEl = document.getElementById(textId);
    const convertCb = document.getElementById(convertId);
    
    if (!panel || !textEl || !convertCb) return;
    
    const sliderContainerId = mediaType === "movie" ? "movie-quality-slider-container" : "series-quality-slider-container";
    const sliderContainer = document.getElementById(sliderContainerId);
    
    if (!convertCb.checked) {
        panel.classList.add("hidden");
        if (sliderContainer) sliderContainer.classList.add("hidden");
        return;
    }
    
    if (sliderContainer) sliderContainer.classList.remove("hidden");
    
    // Check if we have video files
    const videoFiles = projectFiles.filter(f => {
        const isDir = f.endsWith("/");
        if (isDir) return false;
        const ext = f.split('.').pop().toLowerCase();
        return ['mp4', 'mkv', 'avi', 'webm', 'mov'].includes(ext);
    });
    
    if (videoFiles.length === 0) {
        panel.classList.add("hidden");
        return;
    }
    
    const sliderId = mediaType === "movie" ? "movie-quality-slider" : "series-quality-slider";
    const sliderInput = document.getElementById(sliderId);
    const qualityVal = sliderInput ? parseInt(sliderInput.value, 10) : 60;
    
    panel.classList.remove("hidden");
    if (mediaType === "movie") {
        textEl.textContent = "Dateigrößen-Prognose: Test-Konvertierung läuft für präzise Schätzung (ca. 15 Sek.)...";
    } else {
        textEl.textContent = "Dateigrößen-Prognose: Test-Konvertierung der ersten Folge läuft (ca. 15 Sek.)...";
    }
    
    try {
        const response = await fetch("/api/estimate-conversion", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                project_name: currentProject,
                filenames: videoFiles,
                quality: qualityVal
            })
        });
        
        if (!response.ok) {
            textEl.textContent = "Dateigrößen-Prognose: Fehler bei der Berechnung";
            return;
        }
        
        const data = await response.json();
        const estimates = data.estimates || {};
        
        let totalSizeIn = 0;
        let totalSizeOut = 0;
        let successCount = 0;
        
        for (const [file, est] of Object.entries(estimates)) {
            if (est.size_in !== undefined && est.size_out !== undefined) {
                totalSizeIn += est.size_in;
                totalSizeOut += est.size_out;
                successCount++;
            }
        }
        
        if (successCount > 0 && totalSizeIn > 0) {
            const savings = totalSizeIn - totalSizeOut;
            const pct = Math.round((savings / totalSizeIn) * 100);
            
            const inStr = formatBytes(totalSizeIn);
            const outStr = formatBytes(totalSizeOut);
            
            textEl.textContent = `Voraussichtliche Ersparnis: ${inStr} → ~${outStr} (-${pct}%)`;
        } else {
            textEl.textContent = "Dateigrößen-Prognose nicht verfügbar";
        }
        
    } catch (e) {
        console.error("Error updating size estimation:", e);
        textEl.textContent = "Dateigrößen-Prognose: Verbindungsfehler";
    }
}

// ==========================================================================
// INBOX FILES SCANNING
// ==========================================================================
function selectProject(projectName) {
    currentProject = projectName;
    
    window.nasFolderSelected = null;
    window.ytNasFolderSelected = null;
    
    // Reset local profile search
    const profileSearchInput = document.getElementById("series-local-profile-search");
    if (profileSearchInput) {
        profileSearchInput.value = "";
    }
    if (typeof allLocalProfiles !== "undefined") {
        renderLocalProfilesDropdown(allLocalProfiles);
    }
    
    // Reset manual mode variables
    isManualMovieMode = false;
    isManualSeriesMode = false;
    
    const manualMovieContainer = document.getElementById("manual-movie-container");
    if (manualMovieContainer) manualMovieContainer.classList.add("hidden");
    const manualSeriesContainer = document.getElementById("manual-series-container");
    if (manualSeriesContainer) manualSeriesContainer.classList.add("hidden");
    
    const btnManualMovie = document.getElementById("btn-manual-movie");
    if (btnManualMovie) {
        btnManualMovie.classList.remove("active");
        btnManualMovie.textContent = "Manuell eintragen";
    }
    const btnManualSeries = document.getElementById("btn-manual-series");
    if (btnManualSeries) {
        btnManualSeries.classList.remove("active");
        btnManualSeries.textContent = "Manuell eintragen";
    }
    
    const mMovieTitle = document.getElementById("manual-movie-title");
    if (mMovieTitle) mMovieTitle.value = "";
    const mMovieYear = document.getElementById("manual-movie-year");
    if (mMovieYear) mMovieYear.value = "";
    const mMoviePlot = document.getElementById("manual-movie-plot");
    if (mMoviePlot) mMoviePlot.value = "";
    const mSeriesTitle = document.getElementById("manual-series-title");
    if (mSeriesTitle) mSeriesTitle.value = "";
    const mSeriesPlot = document.getElementById("manual-series-plot");
    if (mSeriesPlot) mSeriesPlot.value = "";
    
    selectedMovie = null;
    selectedShow = null;
    const moviePanel = document.getElementById("selected-movie-panel");
    if (moviePanel) moviePanel.classList.add("hidden");
    const showPanel = document.getElementById("selected-show-panel");
    if (showPanel) showPanel.classList.add("hidden");
    const movieResults = document.getElementById("movie-search-results");
    if (movieResults) movieResults.innerHTML = "";
    const seriesResults = document.getElementById("series-search-results");
    if (seriesResults) seriesResults.innerHTML = "";
    const matchContainer = document.getElementById("matching-panel-container");
    if (matchContainer) matchContainer.innerHTML = "";
    const seriesExec = document.getElementById("series-execution-panel");
    if (seriesExec) seriesExec.classList.add("hidden");
    
    // Update active state in UI list
    document.querySelectorAll(".project-item").forEach(item => {
        if (item.getAttribute("data-project") === projectName) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });
    // Also remove active from system navs
    const navYtDownloader = document.getElementById("nav-youtube-downloader");
    if(navYtDownloader) navYtDownloader.classList.remove("active");
    const navTools = document.getElementById("nav-tools-dashboard");
    if(navTools) navTools.classList.remove("active");
    const navSettings = document.getElementById("nav-settings-dashboard");
    if(navSettings) navSettings.classList.remove("active");
    const navYtAbos = document.getElementById("nav-youtube-abos");
    if(navYtAbos) navYtAbos.classList.remove("active");
    const navDashboard = document.getElementById("nav-dashboard");
    if(navDashboard) navDashboard.classList.remove("active");
    
    // Hide context panels and reset mode cards on new project selection
    document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
    ["movie", "series", "doku", "tools"].forEach(m => {
        const el = document.getElementById(`mode-${m}`);
        if (el) {
            el.classList.remove("active");
            el.setAttribute("aria-checked", "false");
        }
    });

    // Close NFO details panels by default
    const movieDetails = document.getElementById("movie-nfo-details");
    if (movieDetails) movieDetails.removeAttribute("open");
    const seriesDetails = document.getElementById("series-nfo-details");
    if (seriesDetails) seriesDetails.removeAttribute("open");
    
    triggerQualityHintUpdates();
    scanProject(projectName);
}

function applySmartConversionDefault(hasInefficientVideo) {
    const isSmartDefault = currentSettings.smart_conversion_default !== false; // default to true
    const shouldConvert = isSmartDefault && hasInefficientVideo;
    
    const movieConvertCb = document.getElementById("movie-option-convert");
    const seriesConvertCb = document.getElementById("series-option-convert");
    
    if (movieConvertCb) {
        movieConvertCb.checked = shouldConvert;
        movieConvertCb.dispatchEvent(new Event('change'));
    }
    if (seriesConvertCb) {
        seriesConvertCb.checked = shouldConvert;
        seriesConvertCb.dispatchEvent(new Event('change'));
    }
}

async function scanProject(project) {
    updateProjectProcessingStatus(activeProjectsProcessing);
    const title = document.getElementById("current-project-title");
    const path = document.getElementById("current-project-path");
    const statsContainer = document.getElementById("project-stats-container");
    const statsBadges = document.getElementById("stats-badges-container");
    const tbody = document.getElementById("files-table-body");
    
    // UI View Switching
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    document.getElementById("view-folder").classList.remove("hidden");
    document.getElementById("view-folder").classList.add("active");
    scrollToDetailTop();
    
    
    title.textContent = project === "" ? "Unsortierte Einzeldateien verarbeiten" : (project === "__inbox_recursive__" ? "Alle Dateien (inkl. Unterordner) verarbeiten" : `Projekt: ${project}`);
    path.textContent = "Scanne Ordner...";
    tbody.innerHTML = '<tr><td colspan="3" class="text-center"><div class="loading-spinner"></div></td></tr>';
    statsContainer.style.display = "none";
    
    const modeSelector = document.getElementById("folder-mode-selector");
    const recursiveNotice = document.getElementById("recursive-mode-notice");
    if (project === "__inbox_recursive__") {
        if (modeSelector) modeSelector.classList.add("hidden");
        if (recursiveNotice) recursiveNotice.classList.remove("hidden");
    } else {
        if (modeSelector) modeSelector.classList.remove("hidden");
        if (recursiveNotice) recursiveNotice.classList.add("hidden");
    }
    
    try {
        const response = await fetch(`/api/scan-project?project=${encodeURIComponent(project)}`);
        if (!response.ok) {
            if (response.status === 404 && project !== "") {
                console.warn(`Project folder "${project}" not found, redirecting home.`);
                if (typeof window.goHome === "function") {
                    window.goHome();
                } else {
                    document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
                    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
                    const emptyView = document.getElementById("view-empty");
                    if (emptyView) {
                        emptyView.classList.remove("hidden");
                        emptyView.classList.add("active");
                    }
                    currentProject = "";
                    loadStatus();
                    scrollToDetailTop();
                }
                return;
            }
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger">Fehler beim Laden des Projektinhalts.</td></tr>';
            return;
        }
        
        const data = await response.json();
        path.textContent = `Pfad: ${data.current_dir}`;
        projectFiles = data.files || [];
        currentProjectIsDoku = data.is_doku || false;
        currentProjectSuggestedQuery = data.suggested_query || "";
        
        applySmartConversionDefault(data.has_inefficient_video || false);
        
        if (projectFiles.length === 0) {
            const emptyMsg = project === "" ? "Keine unsortierten Einzeldateien in der Hauptinbox gefunden." : (project === "__inbox_recursive__" ? "Keine Dateien in der gesamten Inbox (inkl. Unterordnern) gefunden." : "Dieser Ordner ist leer.");
            tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">${emptyMsg}</td></tr>`;
            return;
        }
        
        // Render files list
        let rowsHtml = "";
        projectFiles.forEach(f => {
            const isDir = f.endsWith("/");
            const name = isDir ? f.slice(0, -1) : f;
            const ext = isDir ? "ordner" : f.split('.').pop().toLowerCase();
            const isVideo = ['mp4', 'mkv', 'avi', 'webm', 'mov'].includes(ext);
            
            let badgeClass = "file-type-badge";
            if (isDir) badgeClass += " dir";
            else if (isVideo) badgeClass += " video";
            else if (['srt', 'vtt', 'ass'].includes(ext)) badgeClass += " subtitle";
            else if (ext === 'nfo') badgeClass += " nfo";
            
            let actionHtml = "";
            if (!isDir && isVideo && project !== "__inbox_recursive__") {
                actionHtml = `<button class="btn btn-sm btn-split-file" data-project="${escapeHTML(project)}" data-file="${escapeHTML(name)}" title="In ein separates Projekt abspalten" style="background: rgba(255, 255, 255, 0.1); border: 1px solid var(--border-glass); color: var(--text-normal); cursor: pointer; padding: 3px 8px; border-radius: var(--radius-sm); font-size: 0.7rem; transition: all 0.2s ease;">Trennen</button>`;
            }
            
            rowsHtml += `
                <tr>
                    <td>${escapeHTML(name)}</td>
                    <td><span class="${badgeClass}">${isDir ? "ORDNER" : ext.toUpperCase()}</span></td>
                    <td style="text-align:right;">${actionHtml}</td>
                </tr>
            `;
        });
        tbody.innerHTML = rowsHtml;
        
        tbody.querySelectorAll(".btn-split-file").forEach(btn => {
            btn.addEventListener("click", () => {
                const proj = btn.getAttribute("data-project");
                const fname = btn.getAttribute("data-file");
                splitProjectFile(proj, fname);
            });
        });
        
        // Render statistics
        if (data.ext_counts && Object.keys(data.ext_counts).length > 0) {
            statsContainer.style.display = "block";
            let badgesHtml = "";
            for (const [ext, count] of Object.entries(data.ext_counts)) {
                badgesHtml += `<span class="stat-badge">${count}x .${ext}</span>`;
            }
            statsBadges.innerHTML = badgesHtml;
        }
        
        // Trigger size estimations for the currently active context panel if any
        const movieContext = document.getElementById("context-movie");
        const seriesContext = document.getElementById("context-series");
        if (movieContext && !movieContext.classList.contains("hidden")) {
            updateSizeEstimation("movie");
        }
        if (seriesContext && !seriesContext.classList.contains("hidden")) {
            updateSizeEstimation("series");
        }
        
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">Verbindungsfehler: ${e}</td></tr>`;
    }
}

// ==========================================================================
// AUTO MATCHING ALGORITHM
// ==========================================================================
function cleanFilenameForManualTitle(filename) {
    if (!filename) return "";
    let name = filename.substring(0, filename.lastIndexOf('.')) || filename;
    name = name.replace(/s\d+e\d+/gi, "");
    name = name.replace(/\b\d+x\d+\b/gi, "");
    name = name.replace(/\b(ep|episode|folge|f|e|ep\.)\s*\d+\b/gi, "");
    name = name.replace(/[._\-]/g, " ");
    name = name.replace(/\s+/g, " ").trim();
    return name;
}

function guessEpisodeNumber(filename) {
    const cleanName = filename.toLowerCase();
    
    // Pattern: s01e05
    let match = cleanName.match(/s\d+e(\d+)/);
    if (match) return parseInt(match[1], 10);
    
    // Pattern: 1x05
    match = cleanName.match(/\d+x(\d+)/);
    if (match) return parseInt(match[1], 10);
    
    // Pattern: ep 05 / episode 05
    match = cleanName.match(/ep(?:isode)?[.\s-]?(\d+)/);
    if (match) return parseInt(match[1], 10);
    
    // Pattern: isolated digits (excluding year range 1900-2100)
    const withoutExt = filename.substring(0, filename.lastIndexOf('.')) || filename;
    const digitMatches = withoutExt.match(/\b\d+\b/g);
    if (digitMatches) {
        for (const digitStr of digitMatches) {
            const val = parseInt(digitStr, 10);
            if (val > 0 && val < 200) { // realistic episode range
                return val;
            }
        }
    }
    
    return null;
}

function guessSeasonAndEpisode(filename) {
    const clean = filename.toLowerCase();
    let match = clean.match(/s(\d+)e(\d+)/);
    if (match) {
        return `S${parseInt(match[1], 10).toString().padStart(2, '0')}E${parseInt(match[2], 10).toString().padStart(2, '0')}`;
    }
    match = clean.match(/\b(\d+)x(\d+)\b/);
    if (match) {
        return `S${parseInt(match[1], 10).toString().padStart(2, '0')}E${parseInt(match[2], 10).toString().padStart(2, '0')}`;
    }
    match = clean.match(/\b(?:staffel|st|s)\s*(\d+)\b.*?\b(?:folge|ep|e|f|episode)\s*(\d+)\b/);
    if (match) {
        return `S${parseInt(match[1], 10).toString().padStart(2, '0')}E${parseInt(match[2], 10).toString().padStart(2, '0')}`;
    }
    return null;
}

async function detectExistingSeries(projectName) {
    if (!projectName) {
        searchSeries();
        return;
    }
    const nasDestId = document.getElementById("series-nas-destination").value;
    try {
        const url = `/api/series/detect?project_name=${encodeURIComponent(projectName)}&nas_destination_id=${encodeURIComponent(nasDestId)}`;
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            if (data.found && data.show_id && data.provider) {
                console.log("[Auto-Detect] Found existing show:", data);
                selectShow({
                    id: data.show_id,
                    name: data.show_name || projectName,
                    provider: data.provider,
                    loadedFromNfo: true
                });
                return;
            }
        }
    } catch (err) {
        console.error("Error in detectExistingSeries:", err);
    }
    autoMatchNasFolder("series-nas-folder-override", "series-nas-destination", projectName);
    searchSeries();
}

async function triggerSeriesMatchingFromFolder(folderName) {
    if (!folderName) return;
    
    // Show a loading spinner in the matching panel
    const matchingContainer = document.getElementById("matching-panel-container");
    if (matchingContainer) {
        matchingContainer.innerHTML = `
            <div class="loading-spinner"></div>
            <p class="text-center text-muted" style="margin-top:10px;">Lese tvshow.nfo...</p>
        `;
    }
    
    const nasDestId = document.getElementById("series-nas-destination").value;
    try {
        const url = `/api/series/detect?project_name=${encodeURIComponent(folderName)}&nas_destination_id=${encodeURIComponent(nasDestId)}`;
        const response = await fetch(url);
        if (response.ok) {
            const data = await response.json();
            if (data.found && data.show_id && data.provider) {
                console.log("[Folder Select] Found existing show from tvshow.nfo:", data);
                appendConsoleLog(`[System]: tvshow.nfo gefunden. Serie "${data.show_name}" wird geladen...`);
                selectShow({
                    id: data.show_id,
                    name: data.show_name || folderName,
                    provider: data.provider,
                    loadedFromNfo: true
                });
                return;
            }
        }
    } catch (err) {
        console.error("Error in triggerSeriesMatchingFromFolder detect:", err);
    }
    
    // Clear the loading spinner since no existing tvshow.nfo was found
    if (matchingContainer) {
        matchingContainer.innerHTML = "";
    }
    
    // If tvshow.nfo not found, trigger online search automatically
    appendConsoleLog(`[System]: Keine tvshow.nfo gefunden. Starte Online-Suche nach "${folderName}"...`);
    const searchQueryInput = document.getElementById("series-search-query");
    if (searchQueryInput) {
        const cleanQuery = folderName.replace(/\([0-9]{4}\)/g, "").replace(/_/g, " ").trim();
        searchQueryInput.value = cleanQuery;
        searchSeries();
    }
}

// ==========================================================================
// SEARCH & METADATA HANDLERS (SERIES & MOVIES)
// ==========================================================================
let currentSearchSeriesController = null;
let lastSearchSeriesQuery = "";

async function searchSeries() {
    const query = document.getElementById("series-search-query").value.trim();
    const resultsContainer = document.getElementById("series-search-results");
    
    if (!query) return;
    
    if (currentSearchSeriesController) {
        currentSearchSeriesController.abort();
    }
    currentSearchSeriesController = new AbortController();
    lastSearchSeriesQuery = query;
    
    resultsContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {

        const destId = getCatIdBySub("/Dokus/Doku-Serien", "4");
        const nasDestSelect = document.getElementById("series-nas-destination");
        const isDokuDest = nasDestSelect && nasDestSelect.value === destId;
        const isDokuQuery = query.toLowerCase().includes("doku") || query.toLowerCase().includes("dokumentation");
        const isDokuMode = isDokuDest || isDokuQuery || currentProjectIsDoku;
        const searchType = isDokuMode ? "doku" : "tv";
        
        const response = await fetch(`/api/search?type=${searchType}&q=${encodeURIComponent(query)}`, {
            signal: currentSearchSeriesController.signal
        });
        const data = await response.json();
        
        if (query !== lastSearchSeriesQuery) return;
        
        if (data.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted text-center" style="padding:15px;">Keine Serie gefunden.</p>';
            return;
        }
        
        // Auto-select if URL query returns exactly one result
        const isUrlSearch = query.startsWith("http://") || query.startsWith("https://");
        if (isUrlSearch && data.length === 1) {
            const item = data[0];
            const targetMediaType = item.media_type;
            const showObj = {
                id: item.id,
                name: item.name,
                provider: item.provider
            };
            
            resultsContainer.innerHTML = "";
            if (targetMediaType === "movie") {
                document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
                document.getElementById("context-movie").classList.remove("hidden");
                document.getElementById("movie-search-query").value = query;
                selectMovie(showObj);
            } else {
                selectShow(showObj);
            }
            return;
        }
        
        let html = "";
        data.forEach(item => {
            let badge = "";
            if (isDokuMode) {
                if (item.media_type === "movie") {
                    badge = `<span class="badge badge-movie" style="background: var(--primary); padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">Film</span>`;
                } else if (item.media_type === "tv" && item.provider === "mediathek") {
                    badge = `<span class="badge badge-mediathek" style="background: #e67e22; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">Mediathek</span>`;
                } else {
                    badge = `<span class="badge badge-series" style="background: #2ecc71; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">Serie</span>`;
                }
            }
            
            const escapedId = escapeHTML(item.id);
            const escapedName = escapeHTML(item.name);
            const escapedProvider = escapeHTML(item.provider);
            const escapedMediaType = escapeHTML(item.media_type);
            html += `
                <div class="search-item" data-id="${escapedId}" data-name="${escapedName}" data-provider="${escapedProvider}" data-media-type="${escapedMediaType}">
                    <div class="search-item-name">${badge}${escapedName}</div>
                    <div class="search-item-provider">Metadatendienst: ${escapedProvider}</div>
                </div>
            `;
        });
        resultsContainer.innerHTML = html;
        
        // Bind selection clicks
        resultsContainer.querySelectorAll(".search-item").forEach(item => {
            item.addEventListener("click", () => {
                // Visual feedback: remove selected class from all, add to this
                resultsContainer.querySelectorAll(".search-item").forEach(i => {
                    i.style.background = "";
                    i.style.borderColor = "var(--border-light)";
                });
                item.style.background = "var(--primary-light)";
                item.style.borderColor = "var(--primary)";
                
                const targetMediaType = item.getAttribute("data-media-type");
                const showObj = {
                    id: item.getAttribute("data-id"),
                    name: item.getAttribute("data-name"),
                    provider: item.getAttribute("data-provider")
                };
                
                if (targetMediaType === "movie") {
                    document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
                    document.getElementById("context-movie").classList.remove("hidden");
                    document.getElementById("movie-search-query").value = showObj.name;
                    selectMovie(showObj);
                    
                    setTimeout(() => {
                        const panel = document.getElementById("selected-movie-panel");
                        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 200);
                } else {
                    selectShow(showObj);
                    
                    setTimeout(() => {
                        const panel = document.getElementById("selected-show-panel");
                        if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }, 200);
                }
            });
        });
        
    } catch (e) {
        if (e.name === 'AbortError') return; // Ignore aborted requests
        if (query !== lastSearchSeriesQuery) return;
        resultsContainer.innerHTML = `<p class="text-center text-danger">Suchfehler: ${e}</p>`;
    }
}

function renderProviderInfo(element, providerName, id, loadedFromNfo) {
    if (!element) return;
    element.innerHTML = "";
    element.className = "provider-badge-container";
    element.style.display = "flex";
    element.style.flexWrap = "wrap";
    element.style.gap = "8px";
    element.style.alignItems = "center";
    element.style.marginTop = "8px";
    element.style.marginBottom = "12px";

    // Source Badge (NAS or Online)
    const srcBadge = document.createElement("span");
    srcBadge.className = "source-badge";
    if (loadedFromNfo) {
        srcBadge.textContent = "📁 NAS (tvshow.nfo)";
        srcBadge.style.background = "rgba(139, 92, 246, 0.15)";
        srcBadge.style.color = "#a78bfa";
        srcBadge.style.border = "1px solid rgba(139, 92, 246, 0.35)";
    } else {
        srcBadge.textContent = "🌐 Online-Suche";
        srcBadge.style.background = "rgba(59, 130, 246, 0.15)";
        srcBadge.style.color = "#60a5fa";
        srcBadge.style.border = "1px solid rgba(59, 130, 246, 0.35)";
    }
    element.appendChild(srcBadge);

    // Provider Badge
    const provBadge = document.createElement("span");
    let displayProvider = (providerName || "unbekannt").toLowerCase();
    
    if (displayProvider === "tvdb") {
        provBadge.className = "provider-badge tvdb";
        provBadge.textContent = "Metadatendienst: TVDB";
    } else if (displayProvider === "tmdb_tv" || displayProvider === "tmdb") {
        provBadge.className = "provider-badge tmdb";
        provBadge.textContent = "Metadatendienst: TMDb";
    } else if (displayProvider === "mediathek") {
        provBadge.className = "provider-badge mediathek";
        provBadge.textContent = "Metadatendienst: Mediathek";
    } else if (displayProvider === "ytdlp" || displayProvider === "youtube") {
        provBadge.className = "provider-badge ytdlp";
        provBadge.textContent = "Metadatendienst: YouTube / yt-dlp";
    } else if (displayProvider === "manual" || displayProvider === "manuell") {
        provBadge.className = "provider-badge manual";
        provBadge.textContent = "Metadatendienst: Manuell";
    } else {
        provBadge.className = "provider-badge manual";
        provBadge.textContent = "Metadatendienst: " + providerName.toUpperCase();
    }
    element.appendChild(provBadge);

    // ID Badge/Text
    if (id && id !== "null" && id !== "undefined" && !id.startsWith("{")) {
        const idBadge = document.createElement("span");
        idBadge.className = "provider-badge manual"; // use simple styling
        idBadge.style.background = "rgba(255, 255, 255, 0.05)";
        idBadge.style.color = "var(--text-muted)";
        idBadge.style.border = "1px solid var(--border-glass)";
        idBadge.textContent = `ID: ${id}`;
        element.appendChild(idBadge);
    }
}

async function selectShow(show) {
    selectShowRequestId++;
    const currentRequestId = selectShowRequestId;
    selectedShow = show;
    
    // Update local profile dropdown selection to match this show if possible
    const localProfileSelect = document.getElementById("series-local-profile-select");
    if (localProfileSelect) {
        let found = false;
        const normalizeCompareName = (name) => {
            if (!name) return "";
            return name.toLowerCase().replace(/[^a-z0-9]/g, "");
        };
        const normS = normalizeCompareName(show.name);
        
        for (let i = 0; i < localProfileSelect.options.length; i++) {
            const opt = localProfileSelect.options[i];
            if (opt.value) {
                try {
                    const pData = JSON.parse(opt.value);
                    const normP = normalizeCompareName(pData.show_name);
                    const normF = pData.filename ? normalizeCompareName(pData.filename.replace(".json", "")) : "";
                    
                    if (pData.show_name === show.name || 
                        (normP && normP === normS) || 
                        (normF && normF === normS)) {
                        localProfileSelect.selectedIndex = i;
                        found = true;
                        break;
                    }
                } catch(e) {}
            }
        }
        if (!found) {
            localProfileSelect.value = "";
        }
    }
    
    const overrideInput = document.getElementById("series-nas-folder-override");
    const matchStatusLabel = document.getElementById("series-nas-folder-match-status");
    if (matchStatusLabel) {
        matchStatusLabel.classList.add("hidden");
        matchStatusLabel.textContent = "";
    }
    
    const panel = document.getElementById("selected-show-panel");
    const title = document.getElementById("selected-show-title");
    const provider = document.getElementById("selected-show-provider-info");
    const seasonsInfo = document.getElementById("selected-show-seasons-info");
    
    title.textContent = show.name;
    renderProviderInfo(provider, show.provider, show.id, show.loadedFromNfo);
    seasonsInfo.textContent = "Lade Staffel-Informationen...";
    panel.classList.remove("hidden");
    
    const clearBtn = document.getElementById("btn-clear-profile-selection");
    if (clearBtn) clearBtn.classList.remove("hidden");
    
    // Reset and close series details collapsible block
    const seriesDetails = document.getElementById("series-nfo-details");
    if (seriesDetails) {
        seriesDetails.removeAttribute("open");
    }
    const seriesNfoTitle = document.getElementById("series-nfo-title");
    const seriesNfoYear = document.getElementById("series-nfo-year");
    const seriesNfoPlot = document.getElementById("series-nfo-plot");
    if (seriesNfoTitle) seriesNfoTitle.value = show.name;
    if (seriesNfoYear) seriesNfoYear.value = "";
    if (seriesNfoPlot) seriesNfoPlot.value = "Lade Metadaten...";

    // Fetch and populate show NFO metadata (background thread, guarded)
    fetch(`/api/metadata/fetch?media_type=tv&provider=${show.provider}&show_id=${show.id}`)
        .then(res => {
            if (currentRequestId !== selectShowRequestId) return null;
            return res.json();
        })
        .then(data => {
            if (!data || currentRequestId !== selectShowRequestId) return;
            if (seriesNfoTitle && data.title) seriesNfoTitle.value = data.title;
            if (seriesNfoYear && data.year) seriesNfoYear.value = data.year;
            if (seriesNfoPlot) seriesNfoPlot.value = data.plot || "";
        })
        .catch(err => {
            console.error("Error fetching show NFO preview:", err);
            if (currentRequestId === selectShowRequestId && seriesNfoPlot) {
                seriesNfoPlot.value = "";
            }
        });

    // 1. Find folder on NAS (AWAIT)
    let nasFolder = cleanSeriesName(show.name);
    if (window.nasFolderSelected) {
        nasFolder = window.nasFolderSelected;
    } else {
        const destSelect = document.getElementById("series-nas-destination");
        const destVal = destSelect ? destSelect.value : "";
        try {
            const res = await fetch(`/api/series/find-folder-by-id?provider=${encodeURIComponent(show.provider)}&show_id=${encodeURIComponent(show.id)}&destination_id=${encodeURIComponent(destVal)}`);
            if (currentRequestId !== selectShowRequestId) return;
            if (res.ok) {
                const data = await res.json();
                if (currentRequestId !== selectShowRequestId) return;
                if (data.folder) {
                    nasFolder = data.folder;
                    if (matchStatusLabel) {
                        matchStatusLabel.textContent = `✅ Zugeordnet zu existierendem NAS-Ordner: ${data.folder}`;
                        matchStatusLabel.classList.remove("hidden");
                    }
                }
            }
        } catch (err) {
            console.error("Error finding folder by show ID:", err);
        }
    }
    if (overrideInput) {
        overrideInput.value = nasFolder;
    }
    autoMatchNasFolder("series-nas-folder-override", "series-nas-destination", nasFolder);

    let hasLoadedAllSeasons = false;
    
    // 2. Fetch and apply profile settings (AWAIT)
    try {
        const profRes = await fetch(`/api/profile?show_name=${encodeURIComponent(show.name)}`);
        if (currentRequestId !== selectShowRequestId) return;
        if (profRes.ok) {
            const profile = await profRes.json();
            if (currentRequestId !== selectShowRequestId) return;
            if (profile) {
                // Apply auto_h265
                const convertCb = document.getElementById("series-option-convert");
                if (convertCb) {
                    convertCb.checked = (profile.auto_h265 === "j");
                }
                
                // Apply copy_to_nas
                const nasCb = document.getElementById("series-option-copy-nas");
                if (nasCb) {
                    if (profile.copy_to_nas !== undefined) {
                        nasCb.checked = profile.copy_to_nas;
                    } else {
                        nasCb.checked = true; // default
                    }
                    nasCb.dispatchEvent(new Event('change'));
                }

                // Apply copy_to_pcloud
                const pcloudCb = document.getElementById("series-option-copy-pcloud");
                if (pcloudCb) {
                    if (profile.copy_to_pcloud !== undefined) {
                        pcloudCb.checked = profile.copy_to_pcloud;
                    } else {
                        pcloudCb.checked = (profile.pcloud_sonstiges === "j");
                    }
                    pcloudCb.dispatchEvent(new Event('change'));
                }
                
                // Apply destination category (wrapped in programmatic change block to prevent override sync)
                const nasSelect = document.getElementById("series-nas-destination");
                const pcloudSelect = document.getElementById("series-pcloud-destination");
                
                window.isProgrammaticCategoryChange = true;
                try {
                    if (nasSelect) {
                        if (profile.nas_destination_id) {
                            nasSelect.value = profile.nas_destination_id;
                        } else {
                            nasSelect.value = "2"; // Default for Serien
                        }
                        nasSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    
                    if (pcloudSelect) {
                        if (profile.pcloud_destination_id) {
                            pcloudSelect.value = profile.pcloud_destination_id;
                        } else {
                            if (profile.pcloud_sonstiges === "j") {
                                pcloudSelect.value = "6"; // Sonstiges category ID
                            } else {
                                pcloudSelect.value = "2"; // Serien category ID
                            }
                        }
                        pcloudSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } finally {
                    window.isProgrammaticCategoryChange = false;
                }

                // Apply force_absolute_season_1
                const absoluteCb = document.getElementById("series-option-absolute-numbering");
                if (absoluteCb) {
                    absoluteCb.checked = !!profile.force_absolute_season_1;
                    absoluteCb.dispatchEvent(new Event('change', { bubbles: true }));
                }

                // Apply all_seasons
                const allSeasonsCb = document.getElementById("series-all-seasons");
                if (allSeasonsCb) {
                    allSeasonsCb.checked = !!profile.all_seasons;
                    const seasonInput = document.getElementById("series-season-num");
                    if (seasonInput) {
                        if (allSeasonsCb.checked) {
                            seasonInput.disabled = true;
                            seasonInput.style.opacity = "0.5";
                            hasLoadedAllSeasons = true;
                        } else {
                            seasonInput.disabled = false;
                            seasonInput.style.opacity = "1";
                        }
                    }
                }
            }
        }
    } catch (err) {
        console.error("Error loading show profile:", err);
    }
    
    // 3. Auto-routing destination for Dokus (default fallback before profile application)
    const nameLower = show.name.toLowerCase();
    const isDoku = nameLower.includes("doku") || nameLower.includes("dokumentation") || currentProjectIsDoku;
    if (isDoku) {
        const destId = getCatIdBySub("/Dokus/Doku-Serien", "4");
        const nasSelect = document.getElementById("series-nas-destination");
        const pcloudSelect = document.getElementById("series-pcloud-destination");
        if (nasSelect) {
            nasSelect.value = destId;
            nasSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
        if (pcloudSelect) {
            pcloudSelect.value = destId;
            pcloudSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // 4. Fetch NAS seasons now that profile and correct folder/destination is loaded (AWAIT)
    await fetchNasSeasons(currentRequestId);
    if (currentRequestId !== selectShowRequestId) return;
    
    updateSizeEstimation("series");
    
    try {
        const response = await fetch(`/api/fetch-show-info?provider=${show.provider}&show_id=${show.id}`);
        if (currentRequestId !== selectShowRequestId) return;
        const data = await response.json();
        if (currentRequestId !== selectShowRequestId) return;
        seasonsInfo.textContent = data.info || "Keine Info gefunden";
    } catch (e) {
        if (currentRequestId === selectShowRequestId) {
            seasonsInfo.textContent = "Fehler beim Laden der Details.";
        }
    }

    if (hasLoadedAllSeasons) {
        fetchEpisodes(currentRequestId);
    } else {
        // Auto guess season
        const videoFiles = projectFiles.filter(f => {
            const isDir = f.endsWith("/");
            if (isDir) return false;
            const ext = f.split('.').pop().toLowerCase();
            return ['mp4', 'mkv', 'avi', 'webm', 'mov'].includes(ext);
        });

        if (videoFiles.length > 0) {
            try {
                const guessResponse = await fetch("/api/guess-season", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        provider: show.provider,
                        show_id: show.id,
                        filenames: videoFiles
                    })
                });
                if (currentRequestId !== selectShowRequestId) return;
                if (guessResponse.ok) {
                    const guessData = await guessResponse.json();
                    if (currentRequestId !== selectShowRequestId) return;
                    if (guessData.season) {
                        const seasonInput = document.getElementById("series-season-num");
                        if (seasonInput) {
                            seasonInput.value = guessData.season;
                        }
                        // Automatically trigger fetchEpisodes to populate matrix!
                        fetchEpisodes(currentRequestId);
                    }
                }
            } catch (err) {
                console.error("Error guessing season:", err);
            }
        }
    }
}

async function fetchEpisodes(requestId = null) {
    const targetRequestId = requestId !== null ? requestId : selectShowRequestId;
    if (!selectedShow) return;
    
    const allSeasonsCb = document.getElementById("series-all-seasons");
    const isAllSeasons = allSeasonsCb && allSeasonsCb.checked;
    const season = isAllSeasons ? "all" : document.getElementById("series-season-num").value;
    const matchingContainer = document.getElementById("matching-panel-container");
    const execPanel = document.getElementById("series-execution-panel");
    
    matchingContainer.innerHTML = '<div class="loading-spinner"></div>';
    execPanel.classList.add("hidden");
    
    if (isManualSeriesMode) {
        renderMatchingMatrix();
        execPanel.classList.remove("hidden");
        return;
    }
    
    try {
        const response = await fetch(`/api/fetch-episodes?provider=${selectedShow.provider}&show_id=${selectedShow.id}&season=${season}`);
        if (targetRequestId !== selectShowRequestId) return;
        episodesData = await response.json();
        if (targetRequestId !== selectShowRequestId) return;
        
        if (Object.keys(episodesData).length === 0) {
            matchingContainer.innerHTML = '<p class="text-center text-danger">Keine Episoden gefunden.</p>';
            return;
        }

        // Get video files
        const videoFiles = projectFiles.filter(f => {
            const isDir = f.endsWith("/");
            if (isDir) return false;
            const ext = f.split('.').pop().toLowerCase();
            return ['mp4', 'mkv', 'avi', 'webm', 'mov'].includes(ext);
        });

        let matches = {};
        let duplicates = {};
        const nasDestEl = document.getElementById("series-nas-destination");
        const nasFolderEl = document.getElementById("series-nas-folder-override");
        if (videoFiles.length > 0) {
            try {
                const matchResponse = await fetch('/api/match-episodes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider: selectedShow.provider,
                        show_id: selectedShow.id,
                        season: season,
                        filenames: videoFiles,
                        show_name: selectedShow.name,
                        nas_destination_id: nasDestEl ? nasDestEl.value : null,
                        nas_show_folder: nasFolderEl ? nasFolderEl.value : null
                    })
                });
                if (targetRequestId !== selectShowRequestId) return;
                if (matchResponse.ok) {
                    const matchData = await matchResponse.json();
                    if (targetRequestId !== selectShowRequestId) return;
                    matches = matchData.matches || {};
                    duplicates = matchData.duplicates || {};
                }
            } catch (err) {
                console.error("Error matching episodes:", err);
            }
        }
        
        if (targetRequestId !== selectShowRequestId) return;
        renderMatchingMatrix(matches, duplicates);
        execPanel.classList.remove("hidden");
        
    } catch (e) {
        matchingContainer.innerHTML = `<p class="text-center text-danger">Fehler beim Episoden-Laden: ${e}</p>`;
    }
}

function renderMatchingMatrix(matches = {}, duplicates = {}) {
    const container = document.getElementById("matching-panel-container");
    
    // Filter only local video files
    const videoFiles = projectFiles.filter(f => {
        const isDir = f.endsWith("/");
        if (isDir) return false;
        const ext = f.split('.').pop().toLowerCase();
        return ['mp4', 'mkv', 'avi', 'webm', 'mov'].includes(ext);
    });
    
    if (videoFiles.length === 0) {
        container.innerHTML = '<p class="text-center text-warning">Keine Videodateien im Projektordner zum Zuordnen gefunden.</p>';
        return;
    }
    
    if (isManualSeriesMode) {
        let html = "";
        const defaultSeason = document.getElementById("series-season-num")?.value || "1";
        
        videoFiles.forEach((file, index) => {
            let seasonVal = defaultSeason;
            let episodeVal = (index + 1).toString();
            
            // Try to parse season and episode from filename
            const guessedStr = guessSeasonAndEpisode(file);
            if (guessedStr) {
                const s_e_match = guessedStr.match(/^S(\d+)E(\d+)$/i);
                if (s_e_match) {
                    seasonVal = parseInt(s_e_match[1], 10).toString();
                    episodeVal = parseInt(s_e_match[2], 10).toString();
                }
            } else {
                const guessedEp = guessEpisodeNumber(file);
                if (guessedEp !== null && !isNaN(guessedEp)) {
                    episodeVal = guessedEp.toString();
                }
            }
            
            const cleanTitle = cleanFilenameForManualTitle(file);
            
            html += `
                <div class="matching-row manual-matching-row" data-file="${file}" style="display: flex; flex-direction: column; gap: 10px; padding: 15px; border: 1px solid var(--border-glass); border-radius: var(--radius-md); margin-bottom: 15px; background: rgba(255,255,255,0.02);">
                    <div style="font-weight: bold; color: var(--text-main); word-break: break-all;">${file}</div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 15px;">
                        <div>
                            <label style="display:block; font-size:11px; color:var(--text-muted); margin-bottom:5px;">Staffel:</label>
                            <input type="number" class="manual-season" id="manual-season-${index}" value="${seasonVal}" style="width:100%;">
                        </div>
                        <div>
                            <label style="display:block; font-size:11px; color:var(--text-muted); margin-bottom:5px;">Episode:</label>
                            <input type="number" class="manual-episode" id="manual-episode-${index}" value="${episodeVal}" style="width:100%;">
                        </div>
                        <div style="grid-column: span 2;">
                            <label style="display:block; font-size:11px; color:var(--text-muted); margin-bottom:5px;">Episodentitel:</label>
                            <input type="text" class="manual-title" id="manual-title-${index}" value="${cleanTitle}" style="width:100%;">
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; align-items: flex-end;">
                        <div style="flex: 1;">
                            <label style="display:block; font-size:11px; color:var(--text-muted); margin-bottom:5px;">Episode URL (Scraping):</label>
                            <input type="text" class="manual-url" id="manual-url-${index}" placeholder="z.B. ARD Mediathek oder YouTube Video URL" style="width:100%;">
                        </div>
                        <button type="button" class="btn btn-secondary btn-scrape-row" data-index="${index}" style="padding: 0 15px; height: 38px; display: flex; align-items: center; justify-content: center;">Scrapieren</button>
                    </div>
                    
                    <div>
                        <label style="display:block; font-size:11px; color:var(--text-muted); margin-bottom:5px;">Plot / Beschreibung:</label>
                        <textarea class="manual-plot" id="manual-plot-${index}" rows="2" placeholder="Beschreibung für diese Folge..." style="width:100%; resize:vertical;"></textarea>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
        // Bind scrape listeners for each row
        videoFiles.forEach((file, index) => {
            const btnScrape = container.querySelector(`.btn-scrape-row[data-index="${index}"]`);
            if (btnScrape) {
                btnScrape.addEventListener("click", async () => {
                    const urlInput = document.getElementById(`manual-url-${index}`);
                    const urlVal = urlInput ? urlInput.value.trim() : "";
                    if (!urlVal) {
                        alert("Bitte geben Sie zuerst eine URL ein!");
                        return;
                    }
                    
                    btnScrape.disabled = true;
                    btnScrape.textContent = "...";
                    
                    try {
                        const response = await fetch(`/api/yt/fetch?url=${encodeURIComponent(urlVal)}`);
                        if (response.ok) {
                            const data = await response.json();
                            if (data.error) {
                                alert("Fehler beim Scraping: " + data.error);
                            } else {
                                const titleInput = document.getElementById(`manual-title-${index}`);
                                const plotTextarea = document.getElementById(`manual-plot-${index}`);
                                if (titleInput && data.title) {
                                    titleInput.value = data.title;
                                }
                                if (plotTextarea && data.description) {
                                    plotTextarea.value = data.description;
                                }
                            }
                        } else {
                            alert("Fehler bei der Anfrage an den Scraper.");
                        }
                    } catch (err) {
                        alert("Fehler beim Abrufen der Metadaten: " + err.message);
                    } finally {
                        btnScrape.disabled = false;
                        btnScrape.textContent = "Scrapieren";
                    }
                });
            }
        });
        
        return;
    }
    
    const allSeasonsCb = document.getElementById("series-all-seasons");
    const isAllSeasons = allSeasonsCb && allSeasonsCb.checked;
    
    let html = "";
    videoFiles.forEach((file, index) => {
        // Try backend match first, fallback to frontend guess
        let guessedEp = matches[file];
        if (guessedEp === undefined || guessedEp === null) {
            if (isAllSeasons) {
                guessedEp = guessSeasonAndEpisode(file);
            } else {
                guessedEp = guessEpisodeNumber(file);
            }
        }
        
        html += `
            <div class="matching-row" data-file="${file}">
                <div class="match-file" title="${file}">
                    <div style="word-break: break-all;">${file}</div>
                    <div class="duplicate-badge-container" id="dup-badge-${index}">${duplicates[file] ? `
                        <div class="duplicate-badge" data-existing-path="${duplicates[file].path}" data-existing-filename="${duplicates[file].filename}" data-new-file="${file}" data-badge-id="dup-badge-${index}" style="margin-top: 5px; font-size: 11px; color: #ffb300; background: rgba(255, 179, 0, 0.08); border: 1px solid rgba(255, 179, 0, 0.25); padding: 4px 8px; border-radius: var(--radius-sm); display: inline-flex; align-items: center; gap: 6px; font-weight: normal; line-height: 1.2; max-width: 100%; box-sizing: border-box; cursor: pointer;" title="Klicken für Video-Vergleich & Upgrade">
                            <span>⚠️ Bereits auf NAS:</span>
                            <span style="font-weight: 500; opacity: 0.9; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 150px;" title="${duplicates[file].filename}">${duplicates[file].filename}</span>
                            <span style="opacity: 0.6; font-size: 10px;">(${duplicates[file].size_gb.toFixed(2)} GB${duplicates[file].resolution ? `, ${duplicates[file].resolution}` : ''})</span>
                        </div>
                    ` : ''}</div>
                </div>
                <div class="match-selection">
                    <div style="display: flex; gap: 8px; width: 100%;">
                        <input type="text" class="match-search-input" id="match-search-${index}" placeholder="🔍 Filtern..." style="flex: 0 0 35%; min-width: 80px;">
                        <select class="match-select" id="match-select-${index}" style="flex: 1; min-width: 0;">
                            <option value="skip">-- Überspringen --</option>
                            ${Object.entries(episodesData).map(([num, ep]) => {
                                const title = typeof ep === 'object' ? ep.title : ep;
                                let isSelected = false;
                                if (isAllSeasons) {
                                    isSelected = (guessedEp === num);
                                } else {
                                    isSelected = (guessedEp === parseInt(num, 10) || String(guessedEp) === String(num));
                                }
                                
                                let label = `Episode ${num}: ${title}`;
                                if (isAllSeasons) {
                                    const s_e_match = num.match(/^S(\d+)E(\d+)$/i);
                                    if (s_e_match) {
                                        const s = parseInt(s_e_match[1], 10);
                                        const e = parseInt(s_e_match[2], 10);
                                        label = `Staffel ${s} - Folge ${e}: ${title}`;
                                    }
                                }
                                return `<option value="${num}" ${isSelected ? 'selected' : ''}>${label}</option>`;
                            }).join('')}
                        </select>
                    </div>
                    <div class="selected-match-info" id="selected-match-info-${index}"></div>
                </div>
                
                <!-- Episoden NFO Editier-Bereich (Spans both columns for full width) -->
                <details class="episode-nfo-details" id="episode-nfo-details-${index}" data-index="${index}" style="grid-column: span 2; margin-top: 10px; border: 1px solid rgba(255,255,255,0.05); border-radius: var(--radius-sm); padding: 8px; background: rgba(0,0,0,0.15); width: 100%; box-sizing: border-box;">
                    <summary style="cursor: pointer; font-size: 11px; color: var(--text-muted);">📝 NFO für diese Episode bearbeiten</summary>
                    <div style="margin-top: 8px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <div>
                                <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Staffel Override (optional):</label>
                                <input type="number" class="episode-nfo-season-override" id="episode-nfo-season-override-${index}" placeholder="z.B. 1" style="width:100%; font-size: 12px; padding: 6px; box-sizing: border-box;">
                            </div>
                            <div>
                                <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Episode Override (optional):</label>
                                <input type="number" class="episode-nfo-episode-override" id="episode-nfo-episode-override-${index}" placeholder="z.B. 5" style="width:100%; font-size: 12px; padding: 6px; box-sizing: border-box;">
                            </div>
                        </div>
                        <div>
                            <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Episodentitel:</label>
                            <input type="text" class="episode-nfo-title" id="episode-nfo-title-${index}" style="width:100%; font-size: 12px; padding: 6px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Erstausstrahlung (Aired):</label>
                            <input type="text" class="episode-nfo-aired" id="episode-nfo-aired-${index}" style="width:100%; font-size: 12px; padding: 6px; box-sizing: border-box;">
                        </div>
                        <div>
                            <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Beschreibung / Plot:</label>
                            <textarea class="episode-nfo-plot" id="episode-nfo-plot-${index}" rows="2" style="width:100%; resize:vertical; font-size: 12px; padding: 6px; box-sizing: border-box;"></textarea>
                        </div>
                    </div>
                </details>
            </div>
        `;
    });
    
    container.innerHTML = html;

    // Bind change listeners to update the selected match info and search inputs
    videoFiles.forEach((file, index) => {
        const select = document.getElementById(`match-select-${index}`);
        const search = document.getElementById(`match-search-${index}`);
        const info = document.getElementById(`selected-match-info-${index}`);
        const seasonOverrideInput = document.getElementById(`episode-nfo-season-override-${index}`);
        const episodeOverrideInput = document.getElementById(`episode-nfo-episode-override-${index}`);
        if (select && info) {
            const updateInfo = () => {
                const selectedOption = select.options[select.selectedIndex];
                if (selectedOption) {
                    const text = selectedOption.text;
                    const val = selectedOption.value;
                    if (val === 'skip') {
                        info.textContent = "⚠️ Wird übersprungen";
                        info.classList.remove("matched");
                    } else {
                        info.textContent = `🎯 Zugeordnet: ${text}`;
                        info.classList.add("matched");
                    }
                }
            };
            
            const checkNasDuplicate = async () => {
                const val = select.value;
                const badgeContainer = document.getElementById(`dup-badge-${index}`);
                if (!badgeContainer) return;
                
                if (val === 'skip') {
                    badgeContainer.innerHTML = '';
                    return;
                }
                
                // Parse season/episode from the selected value, respecting overrides if set
                let epSeason, epNum;
                const sOverride = seasonOverrideInput ? parseInt(seasonOverrideInput.value, 10) : NaN;
                const eOverride = episodeOverrideInput ? parseInt(episodeOverrideInput.value, 10) : NaN;
                
                if (!isNaN(sOverride)) {
                    epSeason = sOverride;
                } else {
                    const seMatch = val.match(/^S(\d+)E(\d+)$/i);
                    if (seMatch) {
                        epSeason = parseInt(seMatch[1], 10);
                    } else {
                        epSeason = parseInt(document.getElementById("series-season-num")?.value || "1", 10);
                    }
                }
                
                if (!isNaN(eOverride)) {
                    epNum = eOverride;
                } else {
                    const seMatch = val.match(/^S(\d+)E(\d+)$/i);
                    if (seMatch) {
                        epNum = parseInt(seMatch[2], 10);
                    } else {
                        epNum = parseInt(val, 10);
                    }
                }
                
                if (isNaN(epSeason) || isNaN(epNum)) {
                    badgeContainer.innerHTML = '';
                    return;
                }
                
                const nasDestEl = document.getElementById("series-nas-destination");
                const nasFolderEl = document.getElementById("series-nas-folder-override");
                
                try {
                    badgeContainer.innerHTML = '<div style="margin-top: 5px; font-size: 10px; color: var(--text-muted);">🔍 Prüfe NAS...</div>';
                    const response = await fetch('/api/check-nas-duplicate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            episode: epNum,
                            season: epSeason,
                            show_name: selectedShow?.name || '',
                            nas_show_folder: nasFolderEl?.value || null,
                            nas_destination_id: nasDestEl?.value || null
                        })
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        if (data.duplicate) {
                            const d = data.duplicate;
                             badgeContainer.innerHTML = `
                                <div class="duplicate-badge" data-existing-path="${d.path}" data-existing-filename="${d.filename}" data-new-file="${file}" data-badge-id="dup-badge-${index}" style="margin-top: 5px; font-size: 11px; color: #ffb300; background: rgba(255, 179, 0, 0.08); border: 1px solid rgba(255, 179, 0, 0.25); padding: 4px 8px; border-radius: var(--radius-sm); display: inline-flex; align-items: center; gap: 6px; font-weight: normal; line-height: 1.2; max-width: 100%; box-sizing: border-box; cursor: pointer;" title="Klicken für Video-Vergleich & Upgrade">
                                    <span>⚠️ Bereits auf NAS:</span>
                                    <span style="font-weight: 500; opacity: 0.9; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 150px;" title="${d.filename}">${d.filename}</span>
                                    <span style="opacity: 0.6; font-size: 10px;">(${d.size_gb.toFixed(2)} GB${d.resolution ? `, ${d.resolution}` : ''})</span>
                                </div>`;
                        } else {
                            badgeContainer.innerHTML = '';
                        }
                    }
                } catch (err) {
                    console.error("NAS duplicate check error:", err);
                    badgeContainer.innerHTML = '';
                }
            };
            
            select.addEventListener("change", () => {
                updateInfo();
                checkNasDuplicate();
            });
            
            if (seasonOverrideInput) {
                seasonOverrideInput.addEventListener("input", () => {
                    checkNasDuplicate();
                });
            }
            if (episodeOverrideInput) {
                episodeOverrideInput.addEventListener("input", () => {
                    checkNasDuplicate();
                });
            }
            
            updateInfo();

            if (search) {
                search.addEventListener("input", () => {
                    const query = search.value;
                    const currentVal = select.value;
                    
                    const searchTerms = query.toLowerCase().split(/\s+/).filter(t => t);
                    
                    let selectHtml = `<option value="skip" ${currentVal === 'skip' ? 'selected' : ''}>-- Überspringen --</option>`;
                    
                    Object.entries(episodesData).forEach(([num, ep]) => {
                        const title = typeof ep === 'object' ? ep.title : ep;
                        let label = `Episode ${num}: ${title}`;
                        if (isAllSeasons) {
                            const s_e_match = num.match(/^S(\d+)E(\d+)$/i);
                            if (s_e_match) {
                                const s = parseInt(s_e_match[1], 10);
                                const e = parseInt(s_e_match[2], 10);
                                label = `Staffel ${s} - Folge ${e}: ${title}`;
                            }
                        }
                        
                        const matchesQuery = searchTerms.every(term => 
                            label.toLowerCase().includes(term) || num.toLowerCase().includes(term)
                        );
                        
                        const isSelected = (currentVal === num);
                        
                        if (matchesQuery || isSelected) {
                            selectHtml += `<option value="${num}" ${isSelected ? 'selected' : ''}>${label}</option>`;
                        }
                    });
                    
                    select.innerHTML = selectHtml;
                    updateInfo();
                });
            }
            
            // Bind NFO collapsible events
            const details = document.getElementById(`episode-nfo-details-${index}`);
            const epTitleInput = document.getElementById(`episode-nfo-title-${index}`);
            const epAiredInput = document.getElementById(`episode-nfo-aired-${index}`);
            const epPlotTextarea = document.getElementById(`episode-nfo-plot-${index}`);
            
            const loadEpisodeNfoData = async () => {
                const val = select.value;
                if (val === 'skip') {
                    if (epTitleInput) epTitleInput.value = "";
                    if (epAiredInput) epAiredInput.value = "";
                    if (epPlotTextarea) epPlotTextarea.value = "Folge wird übersprungen";
                    return;
                }
                
                let epNum = val;
                let epSeason = document.getElementById("series-season-num")?.value || "1";
                if (isAllSeasons) {
                    const s_e_match = val.match(/^S(\d+)E(\d+)$/i);
                    if (s_e_match) {
                        epSeason = parseInt(s_e_match[1], 10).toString();
                        epNum = parseInt(s_e_match[2], 10).toString();
                    }
                }
                
                const cacheKey = `${selectedShow.provider}_${selectedShow.id}_${epSeason}_${epNum}`;
                if (fetchedEpisodeMetadataCache[cacheKey]) {
                    const cached = fetchedEpisodeMetadataCache[cacheKey];
                    if (epTitleInput) epTitleInput.value = cached.title || "";
                    if (epAiredInput) epAiredInput.value = cached.aired || "";
                    if (epPlotTextarea) epPlotTextarea.value = cached.plot || "";
                    return;
                }
                
                if (epPlotTextarea) epPlotTextarea.value = "Lade Metadaten...";
                try {
                    const response = await fetch(`/api/metadata/fetch?media_type=episode&provider=${selectedShow.provider}&show_id=${selectedShow.id}&season=${epSeason}&episode=${epNum}`);
                    if (response.ok) {
                        const data = await response.json();
                        const cacheKeys = Object.keys(fetchedEpisodeMetadataCache);
                        if (cacheKeys.length >= 500) {
                            delete fetchedEpisodeMetadataCache[cacheKeys[0]];
                        }
                        fetchedEpisodeMetadataCache[cacheKey] = data;
                        if (select.value === val) {
                            if (epTitleInput) epTitleInput.value = data.title || "";
                            if (epAiredInput) epAiredInput.value = data.aired || "";
                            if (epPlotTextarea) epPlotTextarea.value = data.plot || "";
                        }
                    }
                } catch (err) {
                    console.error("Error fetching episode NFO:", err);
                    if (epPlotTextarea) epPlotTextarea.value = "";
                }
            };
            
            if (details) {
                details.addEventListener("toggle", () => {
                    if (details.open) {
                        loadEpisodeNfoData();
                    }
                });
            }
            
            select.addEventListener("change", () => {
                if (details && details.open) {
                    loadEpisodeNfoData();
                }
            });
        }
    });
}

let currentSearchMovieController = null;
let lastSearchMovieQuery = "";

async function searchMovie() {
    const query = document.getElementById("movie-search-query").value.trim();
    const resultsContainer = document.getElementById("movie-search-results");
    
    if (!query) return;
    
    if (currentSearchMovieController) {
        currentSearchMovieController.abort();
    }
    currentSearchMovieController = new AbortController();
    lastSearchMovieQuery = query;
    
    resultsContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {

        const destId = getCatIdBySub("/Dokus/Einzelne Dokus", "3");
        const nasDestSelect = document.getElementById("movie-nas-destination");
        const isDokuDest = nasDestSelect && nasDestSelect.value === destId;
        const queryLower = query.toLowerCase();
        const isDokuQuery = queryLower.includes("doku") || queryLower.includes("dokumentation");
        
        const searchType = (isDokuDest || isDokuQuery || currentProjectIsDoku) ? "doku" : "movie";
        
        const response = await fetch(`/api/search?type=${searchType}&q=${encodeURIComponent(query)}`, {
            signal: currentSearchMovieController.signal
        });
        const data = await response.json();
        
        if (query !== lastSearchMovieQuery) return;
        
        if (data.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted text-center" style="padding:15px;">Keine Einträge gefunden.</p>';
            return;
        }
        
        // Auto-select if URL query returns exactly one result
        const isUrlSearch = query.startsWith("http://") || query.startsWith("https://");
        if (isUrlSearch && data.length === 1) {
            const item = data[0];
            const targetMediaType = item.media_type;
            const showObj = {
                id: item.id,
                name: item.name,
                provider: item.provider
            };
            
            resultsContainer.innerHTML = "";
            if (targetMediaType === "tv") {
                document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
                document.getElementById("context-series").classList.remove("hidden");
                document.getElementById("series-search-query").value = query;
                selectShow(showObj);
            } else {
                selectMovie(showObj);
            }
            return;
        }
        
        let html = "";
        data.forEach(item => {
            let badge = "";
            if (searchType === "doku") {
                if (item.media_type === "movie") {
                    badge = `<span class="badge badge-movie" style="background: var(--primary); padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">Film</span>`;
                } else if (item.media_type === "tv" && item.provider === "mediathek") {
                    badge = `<span class="badge badge-mediathek" style="background: #e67e22; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">Mediathek</span>`;
                } else {
                    badge = `<span class="badge badge-series" style="background: #2ecc71; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">Serie</span>`;
                }
            }
            
            const escapedId = escapeHTML(item.id);
            const escapedName = escapeHTML(item.name);
            const escapedProvider = escapeHTML(item.provider);
            const escapedMediaType = escapeHTML(item.media_type);
            html += `
                <div class="search-item" data-id="${escapedId}" data-name="${escapedName}" data-provider="${escapedProvider}" data-media-type="${escapedMediaType}">
                    <div class="search-item-name">${badge}${escapedName}</div>
                    <div class="search-item-provider">Metadatendienst: ${escapedProvider}</div>
                </div>
            `;
        });
        resultsContainer.innerHTML = html;
        
        resultsContainer.querySelectorAll(".search-item").forEach(item => {
            item.addEventListener("click", () => {
                const targetMediaType = item.getAttribute("data-media-type");
                const showObj = {
                    id: item.getAttribute("data-id"),
                    name: item.getAttribute("data-name"),
                    provider: item.getAttribute("data-provider")
                };
                
                if (targetMediaType === "tv") {
                    document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
                    document.getElementById("context-series").classList.remove("hidden");
                    document.getElementById("series-search-query").value = showObj.name;
                    selectShow(showObj);
                } else {
                    selectMovie(showObj);
                }
            });
        });
        
    } catch (e) {
        if (e.name === 'AbortError') return; // Ignore aborted requests
        if (query !== lastSearchMovieQuery) return;
        resultsContainer.innerHTML = `<p class="text-center text-danger">Suchfehler: ${e}</p>`;
    }
}

function selectMovie(movie) {
    selectedMovie = movie;
    
    const panel = document.getElementById("selected-movie-panel");
    const title = document.getElementById("selected-movie-title");
    const provider = document.getElementById("selected-movie-provider-info");
    
    title.textContent = movie.name;
    renderProviderInfo(provider, movie.provider, movie.id, movie.loadedFromNfo);
    panel.classList.remove("hidden");
    
    // Reset and close movie details collapsible block
    const movieDetails = document.getElementById("movie-nfo-details");
    if (movieDetails) {
        movieDetails.removeAttribute("open");
    }
    const movieNfoTitle = document.getElementById("movie-nfo-title");
    const movieNfoYear = document.getElementById("movie-nfo-year");
    const movieNfoPlot = document.getElementById("movie-nfo-plot");
    if (movieNfoTitle) movieNfoTitle.value = movie.name;
    if (movieNfoYear) movieNfoYear.value = "";
    if (movieNfoPlot) movieNfoPlot.value = "Lade Metadaten...";

    // Fetch and populate movie NFO metadata
    fetch(`/api/metadata/fetch?media_type=movie&provider=${movie.provider}&movie_id=${movie.id}`)
        .then(res => res.json())
        .then(data => {
            if (movieNfoTitle && data.title) movieNfoTitle.value = data.title;
            if (movieNfoYear && data.year) movieNfoYear.value = data.year;
            if (movieNfoPlot) movieNfoPlot.value = data.plot || "";
        })
        .catch(err => {
            console.error("Error fetching movie NFO preview:", err);
            if (movieNfoPlot) movieNfoPlot.value = "";
        });
    
    // Auto-routing destination for Dokus
    const nameLower = movie.name.toLowerCase();
    const isDoku = nameLower.includes("doku") || nameLower.includes("dokumentation") || currentProjectIsDoku;
    if (isDoku) {

        const destId = getCatIdBySub("/Dokus/Einzelne Dokus", "3");
        
        const nasSelect = document.getElementById("movie-nas-destination");
        const pcloudSelect = document.getElementById("movie-pcloud-destination");
        if (nasSelect) nasSelect.value = destId;
        if (pcloudSelect) pcloudSelect.value = destId;
    }
}

// ==========================================================================
// CORE EXECUTION HANDLERS (SERIES & MOVIES & YOUTUBE & TOOLS)
// ==========================================================================
async function executeSeriesWorkflow() {
    if (activeProjectsProcessing && activeProjectsProcessing.has(currentProject || "")) {
        alert("⚠️ Dieses Projekt wird bereits verarbeitet oder befindet sich in der Warteschlange!");
        return;
    }
    if (!selectedShow) return;
    
    const allSeasonsCb = document.getElementById("series-all-seasons");
    const isAllSeasons = allSeasonsCb && allSeasonsCb.checked;
    
    // Collect mappings
    const mappings = {};
    const rows = document.querySelectorAll(".matching-row");
    
    if (isManualSeriesMode) {
        rows.forEach((row, index) => {
            const file = row.getAttribute("data-file");
            const seasonInput = document.getElementById(`manual-season-${index}`);
            const episodeInput = document.getElementById(`manual-episode-${index}`);
            const titleInput = document.getElementById(`manual-title-${index}`);
            const plotTextarea = document.getElementById(`manual-plot-${index}`);
            
            const seasonVal = seasonInput ? parseInt(seasonInput.value, 10) : 1;
            const episodeVal = episodeInput ? parseInt(episodeInput.value, 10) : 1;
            const titleVal = titleInput ? titleInput.value.trim() : "";
            const plotVal = plotTextarea ? plotTextarea.value.trim() : "";
            
            mappings[file] = {
                season: isNaN(seasonVal) ? 1 : seasonVal,
                episode: isNaN(episodeVal) ? 1 : episodeVal,
                title: titleVal,
                plot: plotVal
            };
        });
    } else {
        rows.forEach((row, index) => {
            const file = row.getAttribute("data-file");
            const select = document.getElementById(`match-select-${index}`);
            const val = select.value;
            if (val !== "skip") {
                const sOverrideEl = document.getElementById(`episode-nfo-season-override-${index}`);
                const eOverrideEl = document.getElementById(`episode-nfo-episode-override-${index}`);
                const sOverride = sOverrideEl ? parseInt(sOverrideEl.value, 10) : NaN;
                const eOverride = eOverrideEl ? parseInt(eOverrideEl.value, 10) : NaN;
                
                if (!isNaN(sOverride) || !isNaN(eOverride)) {
                    let defaultSeason, defaultEpisode;
                    const seMatch = val.match(/^S(\d+)E(\d+)$/i);
                    if (seMatch) {
                        defaultSeason = parseInt(seMatch[1], 10);
                        defaultEpisode = parseInt(seMatch[2], 10);
                    } else {
                        defaultSeason = parseInt(document.getElementById("series-season-num")?.value || "1", 10);
                        defaultEpisode = parseInt(val, 10);
                    }
                    
                    mappings[file] = {
                        season: !isNaN(sOverride) ? sOverride : defaultSeason,
                        episode: !isNaN(eOverride) ? eOverride : defaultEpisode,
                        metadata_ep_num: val
                    };
                } else {
                    if (isAllSeasons) {
                        mappings[file] = val;
                    } else {
                        mappings[file] = parseInt(val, 10);
                    }
                }
            }
        });
    }
    
    if (Object.keys(mappings).length === 0) {
        alert("Bitte mindestens eine Datei einer Episode zuordnen!");
        return;
    }
    
    let season = "1";
    if (isManualSeriesMode) {
        const firstEp = Object.values(mappings)[0];
        season = firstEp ? firstEp.season.toString() : "1";
    } else {
        season = isAllSeasons ? "all" : document.getElementById("series-season-num").value;
    }
    
    const convert = document.getElementById("series-option-convert").checked;
    const deleteOrig = document.getElementById("series-option-delete").checked;
    const copyNas = document.getElementById("series-option-copy-nas").checked;
    const copyPcloud = document.getElementById("series-option-copy-pcloud").checked;
    const nasDestId = document.getElementById("series-nas-destination").value;
    const pcloudDestId = document.getElementById("series-pcloud-destination").value;
    const quality = document.getElementById("series-quality-slider") ? parseInt(document.getElementById("series-quality-slider").value, 10) : 60;
    
    const nasShowFolder = document.getElementById("series-nas-folder-override")?.value?.trim();
    const forceAbsoluteSeason1 = document.getElementById("series-option-absolute-numbering") ? document.getElementById("series-option-absolute-numbering").checked : false;
    
    const payload = {
        media_type: "tv",
        project_name: currentProject,
        show_name: selectedShow.name,
        show_id: selectedShow.id,
        provider: selectedShow.provider,
        season: (isManualSeriesMode || !isAllSeasons) ? parseInt(season, 10) : "all",
        mappings: mappings,
        convert: convert,
        quality: quality,
        delete_original: deleteOrig,
        copy_to_nas: copyNas,
        copy_to_pcloud: copyPcloud,
        destination_id: nasDestId,
        nas_destination_id: nasDestId,
        pcloud_destination_id: pcloudDestId,
        force_absolute_season_1: forceAbsoluteSeason1,
        is_anime: document.getElementById("series-is-anime")?.checked || false
    };
    if (nasShowFolder) {
        payload.nas_show_folder = nasShowFolder;
    }
    
    // Collect NFO overrides
    const nfoOverrides = {
        show: {
            title: document.getElementById("series-nfo-title")?.value?.trim() || "",
            year: document.getElementById("series-nfo-year")?.value?.trim() || "",
            plot: document.getElementById("series-nfo-plot")?.value?.trim() || ""
        },
        episodes: {}
    };
    if (!isManualSeriesMode) {
        rows.forEach((row, index) => {
            const file = row.getAttribute("data-file");
            const select = document.getElementById(`match-select-${index}`);
            if (select && select.value !== "skip") {
                const epTitle = document.getElementById(`episode-nfo-title-${index}`)?.value?.trim() || "";
                const epAired = document.getElementById(`episode-nfo-aired-${index}`)?.value?.trim() || "";
                const epPlot = document.getElementById(`episode-nfo-plot-${index}`)?.value?.trim() || "";
                nfoOverrides.episodes[file] = {
                    title: epTitle,
                    aired: epAired,
                    plot: epPlot
                };
            }
        });
    }
    payload.nfo_overrides = nfoOverrides;
    
    openPreviewModal(payload);
}

async function executeMovieWorkflow() {
    if (activeProjectsProcessing && activeProjectsProcessing.has(currentProject || "")) {
        alert("⚠️ Dieses Projekt wird bereits verarbeitet oder befindet sich in der Warteschlange!");
        return;
    }
    if (!selectedMovie) {
        alert("Bitte zuerst einen Film suchen und auswählen!");
        return;
    }
    
    const convert = document.getElementById("movie-option-convert").checked;
    const deleteOrig = document.getElementById("movie-option-delete").checked;
    const copyNas = document.getElementById("movie-option-copy-nas").checked;
    const copyPcloud = document.getElementById("movie-option-copy-pcloud").checked;
    const nasDestId = document.getElementById("movie-nas-destination").value;
    const pcloudDestId = document.getElementById("movie-pcloud-destination").value;
    const quality = document.getElementById("movie-quality-slider") ? parseInt(document.getElementById("movie-quality-slider").value, 10) : 60;
    
    let titleVal = document.getElementById("movie-nfo-title")?.value?.trim() || selectedMovie.name;
    titleVal = titleVal.replace(/\s*\(Mediathek.*?\)/g, "").replace(/\s*\(Freie Mediathek.*?\)/g, "").trim();
    
    const yearVal = document.getElementById("movie-nfo-year")?.value?.trim();
    let finalMovieName = titleVal;
    if (yearVal && /^\d{4}$/.test(yearVal)) {
        titleVal = titleVal.replace(/\s*\(\d{4}\)$/, "").trim();
        finalMovieName = `${titleVal} (${yearVal})`;
    }

    const payload = {
        media_type: "movie",
        project_name: currentProject,
        movie_name: finalMovieName,
        movie_id: selectedMovie.id,
        provider: selectedMovie.provider,
        convert: convert,
        quality: quality,
        delete_original: deleteOrig,
        copy_to_nas: copyNas,
        copy_to_pcloud: copyPcloud,
        destination_id: nasDestId,
        nas_destination_id: nasDestId,
        pcloud_destination_id: pcloudDestId
    };
    
    // Collect NFO overrides
    const nfoOverrides = {
        movie: {
            title: document.getElementById("movie-nfo-title")?.value?.trim() || "",
            year: document.getElementById("movie-nfo-year")?.value?.trim() || "",
            plot: document.getElementById("movie-nfo-plot")?.value?.trim() || ""
        }
    };
    payload.nfo_overrides = nfoOverrides;
    
    openPreviewModal(payload);
}

// ==========================================================================
// YOUTUBE DOWNLOADER PIPELINE HANDLERS
// ==========================================================================
async function analyseYtLink(isHandoff = false) {
    if (isHandoff !== true) {
        ytDownloaderMergeMode = false;
        ytDownloaderMergeItems = [];
        ytDownloaderMergeSubId = null;
    }

    const url = document.getElementById("yt-url").value.trim();
    if (!url) {
        alert("Bitte eine gültige YouTube-/Mediathek-URL eingeben!");
        return;
    }
    
    const loading = document.getElementById("yt-loading-indicator");
    const detailsPanel = document.getElementById("yt-details-panel");
    
    loading.classList.remove("hidden");
    detailsPanel.classList.add("hidden");
    
    try {
        const response = await fetch(`/api/yt/fetch?url=${encodeURIComponent(url)}`);
        if (!response.ok) {
            alert("Fehler bei der Link-Analyse. Bitte Logs prüfen.");
            loading.classList.add("hidden");
            return;
        }
        const data = await response.json();
        if (data.error) {
            alert("Fehler: " + data.error);
            loading.classList.add("hidden");
            return;
        }
        
        ytFetchedInfo = data;
        
        // Render Preview Info
        const previewContainer = document.getElementById("yt-video-info-preview");
        const minutes = Math.floor(data.duration / 60);
        const seconds = Math.floor(data.duration % 60);
        const durationStr = `${minutes}:${seconds.toString().padStart(2, '0')} Min.`;
        
        previewContainer.innerHTML = `
            <div class="yt-preview-box">
                ${data.thumbnail ? `<div class="yt-preview-thumbnail" style="background-image: url('${data.thumbnail}')"></div>` : ''}
                <div class="yt-preview-title">${data.title}</div>
                <div class="yt-preview-meta">
                    <span>👤 ${data.uploader}</span>
                    <span>⏱️ ${durationStr}</span>
                </div>
            </div>
        `;
        
        // Populate Formats/Resolutions
        const formatSelect = document.getElementById("yt-format-select");
        formatSelect.innerHTML = "";
        
        data.resolutions.forEach(optData => {
            const opt = document.createElement("option");
            opt.value = optData.id;
            opt.textContent = optData.label;
            formatSelect.appendChild(opt);
        });
        
        // Populate Subtitles Checkboxes
        const subsContainer = document.getElementById("yt-subtitles-container");
        subsContainer.innerHTML = "";
        if (data.subtitles.length === 0) {
            subsContainer.innerHTML = '<span class="text-muted" style="font-size:12px;">Keine Untertitel gefunden.</span>';
        } else {
            data.subtitles.forEach(sub => {
                const label = document.createElement("label");
                label.className = "checkbox-container";
                label.style.fontSize = "12px";
                label.style.paddingLeft = "22px";
                label.style.marginBottom = "5px";
                label.innerHTML = `
                    <input type="checkbox" name="yt-subs" value="${sub}" ${['de', 'deu', 'ger'].includes(sub.toLowerCase()) ? 'checked' : ''}>
                    <span class="checkmark" style="height:14px; width:14px; top:2px;"></span>
                    ${sub}
                `;
                subsContainer.appendChild(label);
            });
        }
        
        // Handle Merge Mode VS Tagging/Trim sections visibility
        const taggingSection = document.getElementById("yt-tagging-section");
        const trimSection = document.getElementById("yt-trim-section");
        const mergeDetailsSection = document.getElementById("yt-merge-details-section");
        
        if (ytDownloaderMergeMode) {
            if (taggingSection) taggingSection.classList.add("hidden");
            if (trimSection) trimSection.classList.add("hidden");
            if (mergeDetailsSection) {
                mergeDetailsSection.classList.remove("hidden");
                renderDownloaderMergeItems();
            }
        } else {
            if (taggingSection) taggingSection.classList.remove("hidden");
            if (trimSection) trimSection.classList.remove("hidden");
            if (mergeDetailsSection) mergeDetailsSection.classList.add("hidden");
            
            // Reset Search Fields
            document.getElementById("yt-meta-mode").value = "youtube";
            toggleYtMetaSection();
        }
        
        // Show Panel
        detailsPanel.classList.remove("hidden");
        
    } catch (e) {
        alert("Fehler: " + e.message);
    } finally {
        loading.classList.add("hidden");
    }
}

function renderDownloaderMergeItems() {
    const listContainer = document.getElementById("yt-merge-details-list");
    if (!listContainer) return;
    
    listContainer.innerHTML = "";
    
    ytDownloaderMergeItems.forEach((item, index) => {
        const row = document.createElement("div");
        row.className = "merge-item-row";
        row.style.display = "flex";
        row.style.alignItems = "center";
        row.style.justifyContent = "space-between";
        row.style.gap = "10px";
        row.style.background = "rgba(255,255,255,0.02)";
        row.style.border = "1px solid var(--border-glass)";
        row.style.borderRadius = "var(--radius-sm)";
        row.style.padding = "8px 12px";
        row.style.transition = "all 0.2s ease";
        
        // Left part: Checkbox + Thumbnail + Title
        const left = document.createElement("div");
        left.style.display = "flex";
        left.style.alignItems = "center";
        left.style.gap = "10px";
        left.style.flex = "1";
        left.style.minWidth = "0";
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = item.checked;
        checkbox.disabled = item.isInitial; // Initial item must be checked
        checkbox.style.cursor = item.isInitial ? "default" : "pointer";
        checkbox.addEventListener("change", (e) => {
            item.checked = e.target.checked;
            const checked = ytDownloaderMergeItems.filter(x => x.checked);
            const unchecked = ytDownloaderMergeItems.filter(x => !x.checked);
            ytDownloaderMergeItems = [...checked, ...unchecked];
            renderDownloaderMergeItems();
        });
        left.appendChild(checkbox);
        
        if (item.thumbnail) {
            const img = document.createElement("img");
            img.src = item.thumbnail;
            img.style.width = "54px";
            img.style.height = "30px";
            img.style.objectFit = "cover";
            img.style.borderRadius = "2px";
            left.appendChild(img);
        } else {
            const placeholder = document.createElement("div");
            placeholder.style.width = "54px";
            placeholder.style.height = "30px";
            placeholder.style.background = "rgba(255,255,255,0.05)";
            placeholder.style.borderRadius = "2px";
            left.appendChild(placeholder);
        }
        
        const info = document.createElement("div");
        info.style.minWidth = "0";
        
        const titleSpan = document.createElement("div");
        titleSpan.style.fontWeight = "500";
        titleSpan.style.fontSize = "12px";
        titleSpan.style.whiteSpace = "nowrap";
        titleSpan.style.overflow = "hidden";
        titleSpan.style.textOverflow = "ellipsis";
        titleSpan.textContent = item.title;
        titleSpan.title = item.title;
        info.appendChild(titleSpan);
        
        if (item.isInitial) {
            const badge = document.createElement("span");
            badge.style.fontSize = "9px";
            badge.style.background = "rgba(16, 185, 129, 0.15)";
            badge.style.color = "var(--success)";
            badge.style.padding = "1px 4px";
            badge.style.borderRadius = "3px";
            badge.style.marginLeft = "0px";
            badge.style.fontWeight = "bold";
            badge.textContent = "AUSGANGS-VIDEO";
            info.appendChild(badge);
        }
        
        left.appendChild(info);
        row.appendChild(left);
        
        // Right part: Re-order controls
        const right = document.createElement("div");
        right.style.display = "flex";
        right.style.gap = "4px";
        
        const btnUp = document.createElement("button");
        btnUp.className = "btn btn-secondary btn-xs";
        btnUp.style.padding = "2px 6px";
        btnUp.innerHTML = "▲";
        btnUp.disabled = index === 0;
        btnUp.addEventListener("click", () => {
            // Swap with previous
            const temp = ytDownloaderMergeItems[index - 1];
            ytDownloaderMergeItems[index - 1] = ytDownloaderMergeItems[index];
            ytDownloaderMergeItems[index] = temp;
            renderDownloaderMergeItems();
        });
        
        const btnDown = document.createElement("button");
        btnDown.className = "btn btn-secondary btn-xs";
        btnDown.style.padding = "2px 6px";
        btnDown.innerHTML = "▼";
        btnDown.disabled = index === ytDownloaderMergeItems.length - 1;
        btnDown.addEventListener("click", () => {
            // Swap with next
            const temp = ytDownloaderMergeItems[index + 1];
            ytDownloaderMergeItems[index + 1] = ytDownloaderMergeItems[index];
            ytDownloaderMergeItems[index] = temp;
            renderDownloaderMergeItems();
        });
        
        right.appendChild(btnUp);
        right.appendChild(btnDown);
        row.appendChild(right);
        
        listContainer.appendChild(row);
    });
}

function toggleYtMetaSection() {
    const mode = document.getElementById("yt-meta-mode").value;
    const movieSec = document.getElementById("yt-movie-search-section");
    const tvSec = document.getElementById("yt-series-search-section");
    
    movieSec.classList.add("hidden");
    tvSec.classList.add("hidden");
    
    // Clear selections
    ytSelectedMovie = null;
    ytSelectedShow = null;
    document.getElementById("yt-selected-movie-card").classList.add("hidden");
    document.getElementById("yt-selected-series-card").classList.add("hidden");
    document.getElementById("yt-movie-search-results").innerHTML = "";
    document.getElementById("yt-series-search-results").innerHTML = "";
    document.getElementById("yt-movie-search-query").value = "";
    document.getElementById("yt-series-search-query").value = "";
    
    if (mode === "movie") {
        movieSec.classList.remove("hidden");
        // Pre-fill query
        document.getElementById("yt-movie-search-query").value = ytFetchedInfo ? ytFetchedInfo.title.replace(/\([0-9]{4}\)/g, "").trim() : "";
    } else if (mode === "tv") {
        tvSec.classList.remove("hidden");
        // Pre-fill query
        document.getElementById("yt-series-search-query").value = ytFetchedInfo ? ytFetchedInfo.title.replace(/\([0-9]{4}\)/g, "").trim() : "";
    }
}

let currentSearchYtMovieController = null;
let lastSearchYtMovieQuery = "";
let currentSearchYtSeriesController = null;
let lastSearchYtSeriesQuery = "";

async function searchYtMovie() {
    const query = document.getElementById("yt-movie-search-query").value.trim();
    const resultsContainer = document.getElementById("yt-movie-search-results");
    if (!query) return;
    
    if (currentSearchYtMovieController) {
        currentSearchYtMovieController.abort();
    }
    currentSearchYtMovieController = new AbortController();
    lastSearchYtMovieQuery = query;
    
    resultsContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch(`/api/search?type=movie&q=${encodeURIComponent(query)}`, {
            signal: currentSearchYtMovieController.signal
        });
        const data = await response.json();
        
        if (query !== lastSearchYtMovieQuery) return;
        
        if (data.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted text-center" style="padding:10px;">Keine Filme gefunden.</p>';
            return;
        }
        
        let html = "";
        data.forEach(item => {
            const escapedId = escapeHTML(item.id);
            const escapedName = escapeHTML(item.name);
            const escapedProvider = escapeHTML(item.provider);
            html += `
                <div class="search-item yt-movie-search-item" data-id="${escapedId}" data-name="${escapedName}" data-provider="${escapedProvider}">
                    <div class="search-item-name">${escapedName}</div>
                    <div class="search-item-provider">Metadatendienst: ${escapedProvider}</div>
                </div>
            `;
        });
        resultsContainer.innerHTML = html;
        
        resultsContainer.querySelectorAll(".yt-movie-search-item").forEach(item => {
            item.addEventListener("click", () => {
                ytSelectedMovie = {
                    id: item.getAttribute("data-id"),
                    name: item.getAttribute("data-name"),
                    provider: item.getAttribute("data-provider")
                };
                
                const card = document.getElementById("yt-selected-movie-card");
                document.getElementById("yt-selected-movie-title").textContent = ytSelectedMovie.name;
                document.getElementById("yt-selected-movie-info").textContent = `Provider: ${ytSelectedMovie.provider} (ID: ${ytSelectedMovie.id})`;
                card.classList.remove("hidden");
            });
        });
        
    } catch (e) {
        if (e.name === 'AbortError') return; // Ignore aborted requests
        if (query !== lastSearchYtMovieQuery) return;
        resultsContainer.innerHTML = `<p class="text-center text-danger">${e}</p>`;
    }
}

async function searchYtSeries() {
    const query = document.getElementById("yt-series-search-query").value.trim();
    const resultsContainer = document.getElementById("yt-series-search-results");
    if (!query) return;
    
    if (currentSearchYtSeriesController) {
        currentSearchYtSeriesController.abort();
    }
    currentSearchYtSeriesController = new AbortController();
    lastSearchYtSeriesQuery = query;
    
    resultsContainer.innerHTML = '<div class="loading-spinner"></div>';
    
    try {
        const response = await fetch(`/api/search?type=tv&q=${encodeURIComponent(query)}`, {
            signal: currentSearchYtSeriesController.signal
        });
        const data = await response.json();
        
        if (query !== lastSearchYtSeriesQuery) return;
        
        if (data.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted text-center" style="padding:10px;">Keine Serie gefunden.</p>';
            return;
        }
        
        let html = "";
        data.forEach(item => {
            const escapedId = escapeHTML(item.id);
            const escapedName = escapeHTML(item.name);
            const escapedProvider = escapeHTML(item.provider);
            html += `
                <div class="search-item yt-series-search-item" data-id="${escapedId}" data-name="${escapedName}" data-provider="${escapedProvider}">
                    <div class="search-item-name">${escapedName}</div>
                    <div class="search-item-provider">Metadatendienst: ${escapedProvider}</div>
                </div>
            `;
        });
        resultsContainer.innerHTML = html;
        
        resultsContainer.querySelectorAll(".yt-series-search-item").forEach(item => {
            item.addEventListener("click", () => {
                ytSelectedShow = {
                    id: item.getAttribute("data-id"),
                    name: item.getAttribute("data-name"),
                    provider: item.getAttribute("data-provider")
                };
                
                const card = document.getElementById("yt-selected-series-card");
                document.getElementById("yt-selected-series-title").textContent = ytSelectedShow.name;
                document.getElementById("yt-selected-series-info").textContent = `Provider: ${ytSelectedShow.provider} (ID: ${ytSelectedShow.id})`;
                card.classList.remove("hidden");
                
                const ytOverrideInput = document.getElementById("yt-series-nas-folder-override");
                if (ytOverrideInput) {
                    if (window.ytNasFolderSelected) {
                        ytOverrideInput.value = window.ytNasFolderSelected;
                    } else {
                        ytOverrideInput.value = cleanSeriesName(ytSelectedShow.name);
                    }
                    autoMatchNasFolder("yt-series-nas-folder-override", "yt-nas-destination", ytOverrideInput.value);
                }
                
                fetchYtNasSeasons();
            });
        });
        
    } catch (e) {
        if (e.name === 'AbortError') return; // Ignore aborted requests
        if (query !== lastSearchYtSeriesQuery) return;
        resultsContainer.innerHTML = `<p class="text-center text-danger">${e}</p>`;
    }
}

function resetYtDownload() {
    document.getElementById("yt-url").value = "";
    document.getElementById("yt-details-panel").classList.add("hidden");
    document.getElementById("yt-video-info-preview").innerHTML = "";
    const overrideInput = document.getElementById("yt-series-nas-folder-override");
    if (overrideInput) {
        overrideInput.value = "";
    }
    ytFetchedInfo = null;
    ytSelectedMovie = null;
    ytSelectedShow = null;
    ytEpisodesData = {};
    ytDownloaderMergeMode = false;
    ytDownloaderMergeItems = [];
    ytDownloaderMergeSubId = null;
}

async function startYtPipeline() {
    if (!ytFetchedInfo) return;
    
    if (ytDownloaderMergeMode) {
        const finalTitleInput = document.getElementById("yt-merge-details-title");
        const finalTitle = finalTitleInput ? finalTitleInput.value.trim() : "";
        if (!finalTitle) {
            alert("Bitte gib einen Dateinamen für das zusammengefügte Video an!");
            return;
        }
        
        const selectedItems = ytDownloaderMergeItems.filter(item => item.checked);
        if (selectedItems.length === 0) {
            alert("Bitte wähle mindestens ein Video aus!");
            return;
        }
        
        const urls = selectedItems.map(item => item.url);
        const videoIdsToRemove = selectedItems.map(item => item.id);
        
        const copyToNas = document.getElementById("yt-option-copy-nas").checked;
        const copyToPcloud = document.getElementById("yt-option-copy-pcloud").checked;
        const copyToLocal = document.getElementById("yt-option-copy-local").checked;
        
        const nasDest = document.getElementById("yt-nas-destination").value;
        const pcloudDest = document.getElementById("yt-pcloud-destination").value;
        const localDest = document.getElementById("yt-local-destination").value;
        
        const ytFormat = document.getElementById("yt-format-select").value;
        
        expandConsole();
        appendConsoleLog(`[System]: Starte Merge-Job für "${finalTitle}" mit ${urls.length} Teilen...`);
        
        try {
            const res = await fetch("/api/youtube/merge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    urls: urls,
                    title: finalTitle,
                    subscription_id: ytDownloaderMergeSubId,
                    video_ids_to_remove: videoIdsToRemove,
                    thumbnail: selectedItems[0].thumbnail || "",
                    copy_to_nas: copyToNas,
                    copy_to_pcloud: copyToPcloud,
                    copy_to_local: copyToLocal,
                    nas_destination_id: nasDest,
                    pcloud_destination_id: pcloudDest,
                    local_destination_id: localDest,
                    yt_format: ytFormat
                })
            });
            const data = await res.json();
            
            if (res.ok && data.task_id) {
                appendConsoleLog(`[System]: Merge-Job im Hintergrund gestartet (Task ID: ${data.task_id}).`);
                
                // Clear the merge mode state
                ytDownloaderMergeMode = false;
                ytDownloaderMergeItems = [];
                ytDownloaderMergeSubId = null;
                
                // Hide details panel
                document.getElementById("yt-details-panel").classList.add("hidden");
                
                // Switch to Queue panel automatically
                const navQueue = document.getElementById("nav-queue-dashboard");
                if (navQueue) navQueue.click();
            } else {
                appendConsoleLog(`[System]: Fehler beim Starten des Merge-Jobs: ${data.error || 'Serverfehler'}`);
            }
        } catch (err) {
            console.error(err);
            appendConsoleLog(`[System]: Netzwerkfehler beim Starten des Zusammenfügens: ${err}`);
        }
        return;
    }
    
    const mode = document.getElementById("yt-meta-mode").value;
    if (mode === "movie" && !ytSelectedMovie) {
        alert("Bitte wähle zuerst einen Film aus!");
        return;
    }
    if (mode === "tv" && !ytSelectedShow) {
        alert("Bitte wähle zuerst eine Serie aus!");
        return;
    }
    
    // Subtitles
    const checkedSubs = [];
    document.querySelectorAll("input[name='yt-subs']:checked").forEach(cb => {
        checkedSubs.push(cb.value);
    });
    
    // Payload building
    const payload = {
        media_type: "youtube",
        yt_url: document.getElementById("yt-url").value.trim(),
        yt_format: document.getElementById("yt-format-select").value,
        yt_subtitles: checkedSubs,
        yt_embed_thumbnail: true,
        yt_thumbnail: ytFetchedInfo ? ytFetchedInfo.thumbnail : "",
        
        split_chapters: document.getElementById("yt-split-chapters").checked,
        open_losslesscut: document.getElementById("yt-open-losslesscut").checked,
        trim_start: document.getElementById("yt-trim-start").value.trim(),
        trim_end: document.getElementById("yt-trim-end").value.trim(),
        
        metadata_mode: mode,
        copy_to_nas: document.getElementById("yt-option-copy-nas").checked,
        copy_to_pcloud: document.getElementById("yt-option-copy-pcloud").checked,
        copy_to_local: document.getElementById("yt-option-copy-local").checked,
        destination_id: document.getElementById("yt-nas-destination").value,
        nas_destination_id: document.getElementById("yt-nas-destination").value,
        pcloud_destination_id: document.getElementById("yt-pcloud-destination").value,
        local_destination_id: document.getElementById("yt-local-destination").value
    };
    
    // Enrich details based on mode
    if (mode === "movie") {
        payload.movie_id = ytSelectedMovie.id;
        payload.movie_name = ytSelectedMovie.name;
        payload.provider = ytSelectedMovie.provider;
    } else if (mode === "tv") {
        const seasonVal = parseInt(document.getElementById("yt-series-season").value, 10);
        if (!isNaN(seasonVal) && seasonVal >= 1000) {
            const confirmed = confirm(`Warnung: Die Staffel-Nummer ist eine Jahreszahl (${seasonVal})! Bitte prüfen, ob das korrekt ist (z.B. Staffel 56 statt 2026). Möchtest du trotzdem fortfahren?`);
            if (!confirmed) {
                return;
            }
        }
        payload.show_id = ytSelectedShow.id;
        payload.show_name = ytSelectedShow.name;
        payload.season = seasonVal;
        payload.provider = ytSelectedShow.provider;
        const nasShowFolder = document.getElementById("yt-series-nas-folder-override")?.value?.trim();
        if (nasShowFolder) {
            payload.nas_show_folder = nasShowFolder;
        }
    } else {
        // General YouTube mode
        payload.yt_title = ytFetchedInfo.title;
        payload.yt_uploader = ytFetchedInfo.uploader;
        payload.yt_description = ytFetchedInfo.description;
    }
    
    expandConsole();
    appendConsoleLog("[System]: Starte YouTube Download Pipeline...");
    
    try {
        const response = await fetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        if (response.ok && data.task_id) {
            connectLogStream();
            startYtTaskPolling(data.task_id);
            document.getElementById("yt-details-panel").classList.add("hidden");
        } else {
            appendConsoleLog("[System] Fehler beim Starten der Pipeline.");
        }
    } catch (e) {
        appendConsoleLog(`[System] Fehler: ${e}`);
    }
}

async function markYtCutDone() {
    if (!activeYtTaskId) return;
    try {
        const response = await fetch("/api/yt/cut-done", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: activeYtTaskId })
        });
        if (response.ok) {
            appendConsoleLog("[System] Schnitt-Freigabe gesendet. Warte auf Segment-Scan...");
            document.getElementById("yt-losslesscut-modal").classList.add("hidden");
        }
    } catch (e) {
        console.error("Error setting cut done:", e);
    }
}

async function finalizeYtMapping() {
    if (!activeYtTaskId) return;
    
    const mapping = {};
    document.querySelectorAll(".mapping-row").forEach((row, index) => {
        const seg = row.getAttribute("data-segment");
        const val = document.getElementById(`yt-seg-select-${index}`).value;
        if (val !== "skip") {
            mapping[seg] = parseInt(val, 10);
        }
    });
    
    try {
        const response = await fetch("/api/yt/finalize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                task_id: activeYtTaskId,
                mapping: mapping
            })
        });
        if (response.ok) {
            appendConsoleLog("[System] Episodenzuordnung gesendet.");
            document.getElementById("yt-mapping-modal").classList.add("hidden");
            stopYtTaskPolling();
        }
    } catch (e) {
        console.error("Error sending finalize mapping:", e);
    }
}

async function loadYtEpisodesForMapping(provider, showId, season) {
    try {
        const response = await fetch(`/api/fetch-episodes?provider=${provider}&show_id=${showId}&season=${season}`);
        ytEpisodesData = await response.json();
    } catch (e) {
        console.error("Error loading mapping episodes:", e);
    }
}

function renderYtMappingRows(segments) {
    const listContainer = document.getElementById("yt-mapping-list");
    let html = "";
    segments.forEach((seg, index) => {
        const guessed = guessEpisodeNumber(seg);
        html += `
            <div class="mapping-row" data-segment="${seg}">
                <div class="filename" title="${seg}">${seg}</div>
                <div class="match-selection">
                    <select class="match-select yt-segment-select" id="yt-seg-select-${index}">
                        <option value="skip">-- Überspringen --</option>
                        ${Object.entries(ytEpisodesData).map(([num, ep]) => {
                            const title = typeof ep === 'object' ? ep.title : ep;
                            const isSel = guessed === parseInt(num, 10);
                            return `<option value="${num}" ${isSel ? 'selected' : ''}>Episode ${num}: ${title}</option>`;
                        }).join('')}
                    </select>
                    <div class="selected-match-info" id="yt-selected-match-info-${index}"></div>
                </div>
            </div>
        `;
    });
    listContainer.innerHTML = html;

    // Bind change listeners to update the selected match info
    segments.forEach((seg, index) => {
        const select = document.getElementById(`yt-seg-select-${index}`);
        const info = document.getElementById(`yt-selected-match-info-${index}`);
        if (select && info) {
            const updateInfo = () => {
                const selectedOption = select.options[select.selectedIndex];
                if (selectedOption) {
                    const text = selectedOption.text;
                    const val = selectedOption.value;
                    if (val === 'skip') {
                        info.textContent = "⚠️ Wird übersprungen";
                        info.classList.remove("matched");
                    } else {
                        info.textContent = `🎯 Zugeordnet: ${text}`;
                        info.classList.add("matched");
                    }
                }
            };
            select.addEventListener("change", updateInfo);
            updateInfo();
        }
    });
}

function startYtTaskPolling(taskId) {
    activeYtTaskId = taskId;
    if (ytStatusInterval) clearInterval(ytStatusInterval);
    
    let mappingRendered = false;
    
    ytStatusInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/yt/segments?taskId=${taskId}`);
            if (!response.ok) {
                stopYtTaskPolling();
                return;
            }
            const data = await response.json();
            if (data.error) {
                stopYtTaskPolling();
                return;
            }
            
            const state = data.state;
            const losslessModal = document.getElementById("yt-losslesscut-modal");
            const mappingModal = document.getElementById("yt-mapping-modal");
            
            if (state === "waiting_for_cut") {
                losslessModal.classList.remove("hidden");
                mappingModal.classList.add("hidden");
            } else if (state === "waiting_for_mapping") {
                losslessModal.classList.add("hidden");
                mappingModal.classList.remove("hidden");
                
                if (!mappingRendered) {
                    mappingRendered = true;
                    const mode = document.getElementById("yt-meta-mode").value;
                    if (mode === "tv" && ytSelectedShow) {
                        const season = document.getElementById("yt-series-season").value;
                        await loadYtEpisodesForMapping(ytSelectedShow.provider, ytSelectedShow.id, season);
                        renderYtMappingRows(data.segments);
                    }
                }
            } else {
                losslessModal.classList.add("hidden");
                mappingModal.classList.add("hidden");
            }
        } catch (e) {
            console.error("Error polling task:", e);
        }
    }, 2000);
}

function stopYtTaskPolling() {
    if (ytStatusInterval) {
        clearInterval(ytStatusInterval);
        ytStatusInterval = null;
    }
    document.getElementById("yt-losslesscut-modal").classList.add("hidden");
    document.getElementById("yt-mapping-modal").classList.add("hidden");
    activeYtTaskId = null;
}

// ==========================================================================
// YOUTUBE SUBSCRIPTIONS MONITORING HANDLERS
// ==========================================================================
let currentSubscriptions = [];

async function loadSubscriptions() {
    try {
        const [settingsRes, subsRes] = await Promise.all([
            fetch("/api/settings"),
            fetch("/api/youtube/subscriptions")
        ]);
        
        if (settingsRes.ok) {
            currentSettings = await settingsRes.json();
            updateDestinationDropdowns();
        }
        
        if (subsRes.ok) {
            const data = await subsRes.json();
            currentSubscriptions = data.subscriptions || [];
            renderSubscriptionsList();
        }
    } catch (e) {
        console.error("Error loading subscriptions:", e);
        const listContainer = document.getElementById("youtube-abos-list");
        if (listContainer) {
            listContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--danger);">Fehler beim Laden der Abonnements.</div>`;
        }
    }
}

function renderSubscriptionsList() {
    const listContainer = document.getElementById("youtube-abos-list");
    if (!listContainer) return;
    
    if (currentSubscriptions.length === 0) {
        listContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">Keine aktiven Abonnements vorhanden. Füge oben ein neues hinzu.</div>`;
        return;
    }
    
    listContainer.innerHTML = "";
    
    // Sort subscriptions: enabled ones at the top, disabled ones at the bottom
    const sortedSubs = [...currentSubscriptions].sort((a, b) => {
        if (a.enabled === b.enabled) return 0;
        return a.enabled ? -1 : 1;
    });
    
    sortedSubs.forEach((sub) => {
        const item = document.createElement("div");
        item.className = "subscription-item";
        item.dataset.id = sub.id;
        
        // Inline premium styles with transitions
        item.style.background = "rgba(255, 255, 255, 0.02)";
        item.style.border = "1px solid var(--border-glass)";
        item.style.borderRadius = "var(--radius-md)";
        item.style.padding = "12px 20px";
        item.style.display = "flex";
        item.style.flexDirection = "column";
        item.style.gap = "0";
        item.style.transition = "all 0.3s ease";
        
        const headerRow = document.createElement("div");
        headerRow.style.display = "flex";
        headerRow.style.justifyContent = "space-between";
        headerRow.style.alignItems = "center";
        headerRow.style.gap = "15px";
        headerRow.style.flexWrap = "wrap";
        
        // Find category name
        const cats = currentSettings.sync_categories || [];
        
        // Format last checked timestamp
        let lastCheckedStr = "Nie";
        if (sub.last_checked) {
            const date = new Date(sub.last_checked * 1000);
            lastCheckedStr = date.toLocaleString('de-DE', { 
                day: '2-digit', 
                month: '2-digit', 
                year: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }
        
        // Info column
        const infoCol = document.createElement("div");
        infoCol.style.flex = "1";
        infoCol.style.minWidth = "250px";
        
        const titleRow = document.createElement("div");
        titleRow.style.display = "flex";
        titleRow.style.alignItems = "center";
        titleRow.style.gap = "10px";
        titleRow.style.marginBottom = "5px";
        
        // Collapse/Expand Caret
        const expandCaret = document.createElement("span");
        expandCaret.style.display = "inline-block";
        expandCaret.style.marginRight = "6px";
        expandCaret.style.color = "var(--text-muted)";
        expandCaret.style.transition = "all 0.2s ease";
        expandCaret.innerHTML = "▶";
        titleRow.appendChild(expandCaret);
        
        // Show YouTube channel avatar if available
        if (sub.avatar_url) {
            const avatarImg = document.createElement("img");
            avatarImg.src = sub.avatar_url;
            avatarImg.alt = "Kanal-Logo";
            avatarImg.style.width = "24px";
            avatarImg.style.height = "24px";
            avatarImg.style.borderRadius = "50%";
            avatarImg.style.objectFit = "cover";
            avatarImg.style.border = "1px solid rgba(255, 255, 255, 0.15)";
            avatarImg.style.marginRight = "8px";
            titleRow.appendChild(avatarImg);
        }
        
        const titleSpan = document.createElement("span");
        titleSpan.style.fontWeight = "600";
        titleSpan.style.fontSize = "15px";
        titleSpan.style.color = "var(--text-main)";
        titleSpan.textContent = sub.name;
        titleRow.appendChild(titleSpan);
        
        // Active indicator badge
        const activeBadge = document.createElement("span");
        activeBadge.style.fontSize = "10px";
        activeBadge.style.fontWeight = "bold";
        activeBadge.style.padding = "2px 6px";
        activeBadge.style.borderRadius = "4px";
        activeBadge.style.transition = "all 0.3s ease";
        
        const updateBadge = (isEnabled) => {
            if (isEnabled) {
                activeBadge.style.background = "rgba(16, 185, 129, 0.15)";
                activeBadge.style.color = "var(--success)";
                activeBadge.textContent = "AKTIV";
                item.style.opacity = "1";
                item.style.borderColor = "var(--border-glass)";
            } else {
                activeBadge.style.background = "rgba(239, 68, 68, 0.15)";
                activeBadge.style.color = "var(--danger)";
                activeBadge.textContent = "DEAKTIVIERT";
                item.style.opacity = "0.6";
                item.style.borderColor = "transparent";
            }
        };
        updateBadge(sub.enabled);
        titleRow.appendChild(activeBadge);
        
        let pendingVideos = sub.pending_videos || [];
        if (pendingVideos.length > 0) {
            const pendingBadge = document.createElement("span");
            pendingBadge.style.fontSize = "10px";
            pendingBadge.style.fontWeight = "bold";
            pendingBadge.style.padding = "2px 6px";
            pendingBadge.style.borderRadius = "4px";
            pendingBadge.style.background = "rgba(255, 159, 67, 0.15)";
            pendingBadge.style.color = "rgb(255, 159, 67)";
            pendingBadge.style.marginLeft = "5px";
            pendingBadge.textContent = `${pendingVideos.length} AUSSTEHEND`;
            titleRow.appendChild(pendingBadge);
        }
        
        infoCol.appendChild(titleRow);
        
        // Collapsible details container
        const detailsContainer = document.createElement("div");
        detailsContainer.style.display = "none";
        detailsContainer.style.flexDirection = "column";
        detailsContainer.style.gap = "15px";
        detailsContainer.style.marginTop = "15px";
        detailsContainer.style.paddingTop = "10px";
        detailsContainer.style.borderTop = "1px solid rgba(255, 255, 255, 0.05)";
        
        // Details row
        const detailsRow = document.createElement("div");
        detailsRow.style.fontSize = "12.5px";
        detailsRow.style.color = "var(--text-muted)";
        detailsRow.style.display = "flex";
        detailsRow.style.flexWrap = "wrap";
        detailsRow.style.gap = "15px";
        
        // URL link
        const urlItem = document.createElement("div");
        urlItem.innerHTML = `🔗 <a href="${sub.url.startsWith('http') ? sub.url : '#'}" target="_blank" style="color: var(--accent); text-decoration: none;">${sub.url.startsWith('http') ? 'Link öffnen' : 'Suchbegriff: "' + sub.url + '"'}</a>`;
        detailsRow.appendChild(urlItem);
        
        // Filter badge
        if (sub.search_filter && sub.search_filter.trim() !== "") {
            const filterItem = document.createElement("div");
            filterItem.innerHTML = `🔍 Filter: <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; color: var(--text-main); font-weight: 500;">"${sub.search_filter}"</span>`;
            detailsRow.appendChild(filterItem);
        }
        
        // Category/Transfer destination badges
        const copyToNas = sub.copy_to_nas !== false;
        if (copyToNas) {
            const nasId = sub.nas_destination_id || sub.destination_id;
            const cat = cats.find(c => c.id === nasId);
            const catName = cat ? cat.name : (nasId || "Unbekannt");
            const nasItem = document.createElement("div");
            nasItem.innerHTML = `📁 NAS: <span style="color: var(--text-main); font-weight: 500;">${catName}</span>`;
            detailsRow.appendChild(nasItem);
        }
        
        const copyToPcloud = !!sub.copy_to_pcloud;
        if (copyToPcloud) {
            const pcloudId = sub.pcloud_destination_id || sub.destination_id;
            const cat = cats.find(c => c.id === pcloudId);
            const catName = cat ? cat.name : (pcloudId || "Unbekannt");
            const pcloudItem = document.createElement("div");
            pcloudItem.innerHTML = `☁️ pCloud: <span style="color: var(--text-main); font-weight: 500;">${catName}</span>`;
            detailsRow.appendChild(pcloudItem);
        }
        
        const copyToLocal = !!sub.copy_to_local;
        if (copyToLocal) {
            const localId = sub.local_destination_id;
            let localName = localId || "Unbekannt";
            if (localId === "__inbox__") {
                localName = "Input-Ordner";
            } else if (localId === "__outbox__") {
                localName = "Output-Ordner";
            } else if (localId && localId.startsWith("__cat_")) {
                const cat = cats.find(c => c.id === localId.substring(6));
                localName = cat ? `${cat.name} (Output)` : localId;
            } else if (localId && localId.startsWith("__custom_")) {
                try {
                    const idx = parseInt(localId.substring(9), 10);
                    const customFolder = (currentSettings.local_download_folders || [])[idx];
                    localName = customFolder ? customFolder.name : localId;
                } catch(e) {
                    localName = localId;
                }
            }
            const localItem = document.createElement("div");
            localItem.innerHTML = `💻 Lokal: <span style="color: var(--text-main); font-weight: 500;">${localName}</span>`;
            detailsRow.appendChild(localItem);
        }
        
        if (!copyToNas && !copyToPcloud && !copyToLocal) {
            const warningItem = document.createElement("div");
            warningItem.innerHTML = `⚠️ <span style="color: var(--danger); font-weight: 500;">Kein Transferziel aktiviert</span>`;
            detailsRow.appendChild(warningItem);
        }
        
        // Mode badge
        const isAuto = sub.auto_download !== false;
        const modeItem = document.createElement("div");
        modeItem.innerHTML = `⚙️ Modus: <span style="color: var(--text-main); font-weight: 500;">${isAuto ? "Direkt laden" : "Freigabeliste"}</span>`;
        detailsRow.appendChild(modeItem);
        
        // Schedule badge
        const schedule = sub.schedule || "hourly";
        let scheduleText = "Stündlich";
        if (schedule === "daily") scheduleText = "Täglich";
        else if (schedule === "on_startup") scheduleText = "Beim App-Start";
        else if (schedule === "manual") scheduleText = "Nur manuell";
        
        const scheduleItem = document.createElement("div");
        scheduleItem.innerHTML = `🔄 Aktualisierung: <span style="color: var(--text-main); font-weight: 500;">${scheduleText}</span>`;
        detailsRow.appendChild(scheduleItem);

        // German language filter badge
        if (sub.filter_german) {
            const deItem = document.createElement("div");
            deItem.innerHTML = `🇩🇪 Filter: <span style="background: rgba(16, 185, 129, 0.1); padding: 2px 6px; border-radius: 4px; color: var(--success); font-weight: 500; font-size: 11px;">Nur Deutsch</span>`;
            detailsRow.appendChild(deItem);
        }
        
        // Exclude keywords badge
        if (sub.exclude_keywords && sub.exclude_keywords.trim() !== "") {
            const excludeItem = document.createElement("div");
            excludeItem.innerHTML = `🚫 Ausschluss: <span style="background: rgba(239, 68, 68, 0.08); padding: 2px 6px; border-radius: 4px; color: var(--danger); font-weight: 500; font-size: 11px;">"${sub.exclude_keywords}"</span>`;
            detailsRow.appendChild(excludeItem);
        }
        
        // Last checked timestamp
        const timeItem = document.createElement("div");
        timeItem.innerHTML = `⏱️ Letzter Check: ${lastCheckedStr}`;
        detailsRow.appendChild(timeItem);
        
        detailsContainer.appendChild(detailsRow);
        headerRow.appendChild(infoCol);
        
        // Controls column (Toggle + Delete)
        const ctrlCol = document.createElement("div");
        ctrlCol.style.display = "flex";
        ctrlCol.style.alignItems = "center";
        ctrlCol.style.gap = "20px";
        
        // Toggle Switch Container
        const switchLabel = document.createElement("label");
        switchLabel.className = "checkbox-container";
        switchLabel.style.margin = "0";
        switchLabel.style.paddingLeft = "28px";
        switchLabel.style.fontSize = "13px";
        switchLabel.style.fontWeight = "500";
        
        const switchInput = document.createElement("input");
        switchInput.type = "checkbox";
        switchInput.checked = !!sub.enabled;
        
        const switchCheckmark = document.createElement("span");
        switchCheckmark.className = "checkmark";
        
        const statusText = document.createTextNode(sub.enabled ? "Aktiv" : "Aus");
        
        switchInput.addEventListener("change", async (e) => {
            const isEnabled = e.target.checked;
            sub.enabled = isEnabled;
            statusText.textContent = isEnabled ? "Aktiv" : "Aus";
            updateBadge(isEnabled);
            
            // Background save without full list refresh
            await saveAllSubscriptions();
            // Re-render list to sort disabled ones to the bottom
            renderSubscriptionsList();
        });
        
        switchLabel.appendChild(switchInput);
        switchLabel.appendChild(switchCheckmark);
        switchLabel.appendChild(statusText);
        
        ctrlCol.appendChild(switchLabel);
        
        // Delete button
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-danger btn-sm";
        deleteBtn.innerHTML = "🗑️ Löschen";
        deleteBtn.addEventListener("click", async () => {
            if (confirm(`Abonnement "${sub.name}" wirklich löschen?`)) {
                // Visual fadeout effect
                item.style.transform = "scale(0.9)";
                item.style.opacity = "0";
                
                setTimeout(async () => {
                    currentSubscriptions = currentSubscriptions.filter(s => s.id !== sub.id);
                    item.remove();
                    await saveAllSubscriptions();
                    if (currentSubscriptions.length === 0) {
                        renderSubscriptionsList();
                    }
                }, 300);
            }
        });
        ctrlCol.appendChild(deleteBtn);
        
        headerRow.appendChild(ctrlCol);
        item.appendChild(headerRow);
        
        // Render Inbox (pending_videos) if mode is manual
        pendingVideos = sub.pending_videos || [];
        if (!isAuto) {
            const inboxDiv = document.createElement("div");
            inboxDiv.style.marginTop = "10px";
            inboxDiv.style.paddingTop = "15px";
            inboxDiv.style.borderTop = "1px solid rgba(255, 255, 255, 0.05)";
            inboxDiv.style.display = "flex";
            inboxDiv.style.flexDirection = "column";
            inboxDiv.style.gap = "10px";
            
            const inboxHeader = document.createElement("div");
            inboxHeader.style.display = "flex";
            inboxHeader.style.justifyContent = "space-between";
            inboxHeader.style.alignItems = "center";
            inboxHeader.style.fontSize = "13px";
            inboxHeader.style.fontWeight = "600";
            inboxHeader.style.color = "var(--text-muted)";
            inboxHeader.innerHTML = `📥 Freigabeliste (${pendingVideos.length} ausstehend)`;
            inboxDiv.appendChild(inboxHeader);
            
            if (pendingVideos.length === 0) {
                const emptyMsg = document.createElement("div");
                emptyMsg.style.fontSize = "12.5px";
                emptyMsg.style.color = "var(--text-muted)";
                emptyMsg.style.fontStyle = "italic";
                emptyMsg.style.padding = "5px 0";
                emptyMsg.textContent = "Keine neuen Videos ausstehend.";
                inboxDiv.appendChild(emptyMsg);
            } else {
                const listDiv = document.createElement("div");
                listDiv.style.display = "flex";
                listDiv.style.flexDirection = "column";
                listDiv.style.gap = "8px";
                
                pendingVideos.forEach(v => {
                    const vRow = document.createElement("div");
                    vRow.style.display = "flex";
                    vRow.style.alignItems = "center";
                    vRow.style.justifyContent = "space-between";
                    vRow.style.gap = "12px";
                    vRow.style.background = "rgba(255, 255, 255, 0.01)";
                    vRow.style.border = "1px solid rgba(255, 255, 255, 0.03)";
                    vRow.style.borderRadius = "var(--radius-sm)";
                    vRow.style.padding = "8px 12px";
                    vRow.style.flexWrap = "wrap";
                    vRow.style.transition = "all 0.3s ease";
                    
                    const vLeft = document.createElement("div");
                    vLeft.style.display = "flex";
                    vLeft.style.alignItems = "center";
                    vLeft.style.gap = "12px";
                    vLeft.style.flex = "1";
                    vLeft.style.minWidth = "200px";
                    
                    if (v.thumbnail) {
                        const img = document.createElement("img");
                        img.src = v.thumbnail;
                        img.alt = "Thumbnail";
                        img.style.width = "72px";
                        img.style.height = "40px";
                        img.style.objectFit = "cover";
                        img.style.borderRadius = "4px";
                        img.style.border = "1px solid rgba(255, 255, 255, 0.05)";
                        vLeft.appendChild(img);
                    } else {
                        const imgPlaceholder = document.createElement("div");
                        imgPlaceholder.style.width = "72px";
                        imgPlaceholder.style.height = "40px";
                        imgPlaceholder.style.background = "rgba(255, 255, 255, 0.05)";
                        imgPlaceholder.style.borderRadius = "4px";
                        vLeft.appendChild(imgPlaceholder);
                    }
                    
                    const vInfo = document.createElement("div");
                    vInfo.style.display = "flex";
                    vInfo.style.flexDirection = "column";
                    vInfo.style.gap = "2px";
                    
                    const vTitle = document.createElement("div");
                    vTitle.style.fontWeight = "500";
                    vTitle.style.fontSize = "13px";
                    vTitle.style.color = "var(--text-main)";
                    vTitle.textContent = v.title;
                    vInfo.appendChild(vTitle);
                    
                    const vMeta = document.createElement("div");
                    vMeta.style.fontSize = "11px";
                    vMeta.style.color = "var(--text-muted)";
                    vMeta.textContent = `${v.channel || "Unbekannter Kanal"}${v.published_at ? " • " + v.published_at : ""}`;
                    vInfo.appendChild(vMeta);
                    
                    vLeft.appendChild(vInfo);
                    vRow.appendChild(vLeft);
                    
                    const vRight = document.createElement("div");
                    vRight.style.display = "flex";
                    vRight.style.gap = "8px";
                    
                    const btnApprove = document.createElement("button");
                    btnApprove.className = "btn btn-success btn-xs";
                    btnApprove.style.padding = "4px 8px";
                    btnApprove.style.fontSize = "11px";
                    btnApprove.style.fontWeight = "600";
                    btnApprove.innerHTML = "📥 Jetzt laden";
                    
                    const btnProcessInDownloader = document.createElement("button");
                    btnProcessInDownloader.className = "btn btn-primary btn-xs";
                    btnProcessInDownloader.style.padding = "4px 8px";
                    btnProcessInDownloader.style.fontSize = "11px";
                    btnProcessInDownloader.style.fontWeight = "600";
                    btnProcessInDownloader.innerHTML = "🎬 Im Downloader verarbeiten";
                    
                    const btnSearchParts = document.createElement("button");
                    btnSearchParts.className = "btn btn-accent btn-xs";
                    btnSearchParts.style.padding = "4px 8px";
                    btnSearchParts.style.fontSize = "11px";
                    btnSearchParts.style.fontWeight = "600";
                    btnSearchParts.innerHTML = "🔍 Teile suchen";
                    
                    const btnIgnore = document.createElement("button");
                    btnIgnore.className = "btn btn-secondary btn-xs";
                    btnIgnore.style.padding = "4px 8px";
                    btnIgnore.style.fontSize = "11px";
                    btnIgnore.style.fontWeight = "600";
                    btnIgnore.innerHTML = "🗑️ Ignorieren";
                    
                    const btnLink = document.createElement("a");
                    btnLink.href = v.url || `https://www.youtube.com/watch?v=${v.id}`;
                    btnLink.target = "_blank";
                    btnLink.className = "btn btn-info btn-xs";
                    btnLink.style.padding = "4px 8px";
                    btnLink.style.fontSize = "11px";
                    btnLink.style.fontWeight = "600";
                    btnLink.style.textDecoration = "none";
                    btnLink.innerHTML = "🔗 Link";
                    
                    btnApprove.addEventListener("click", async () => {
                        btnApprove.disabled = true;
                        btnIgnore.disabled = true;
                        btnApprove.textContent = "⌛ Starte...";
                        try {
                            const res = await fetch("/api/youtube/subscriptions/approve", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ subscription_id: sub.id, video_id: v.id })
                            });
                            if (res.ok) {
                                vRow.style.opacity = "0.5";
                                vRow.style.transform = "scale(0.98)";
                                setTimeout(() => {
                                    vRow.remove();
                                    sub.pending_videos = sub.pending_videos.filter(pv => pv.id !== v.id);
                                    if (sub.pending_videos.length === 0) {
                                        inboxHeader.textContent = "📥 Freigabeliste (0 ausstehend)";
                                        listDiv.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted); font-style:italic; padding:5px 0;">Keine neuen Videos ausstehend.</div>`;
                                    } else {
                                        inboxHeader.textContent = `📥 Freigabeliste (${sub.pending_videos.length} ausstehend)`;
                                    }
                                }, 300);
                                appendConsoleLog(`[System]: Video "${v.title}" zur Warteschlange hinzugefügt.`);
                            } else {
                                alert("Fehler beim Freigeben des Videos");
                                btnApprove.disabled = false;
                                btnIgnore.disabled = false;
                                btnApprove.innerHTML = "📥 Jetzt laden";
                            }
                        } catch (err) {
                            console.error(err);
                            alert("Netzwerkfehler beim Freigeben");
                            btnApprove.disabled = false;
                            btnIgnore.disabled = false;
                            btnApprove.innerHTML = "📥 Jetzt laden";
                        }
                    });
                    
                    btnProcessInDownloader.addEventListener("click", () => {
                        sendVideoToDownloader(sub, v);
                    });
                    
                    btnIgnore.addEventListener("click", async () => {
                        btnApprove.disabled = true;
                        btnIgnore.disabled = true;
                        btnIgnore.textContent = "⌛ Ignoriere...";
                        try {
                            const res = await fetch("/api/youtube/subscriptions/ignore", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ subscription_id: sub.id, video_id: v.id })
                            });
                            if (res.ok) {
                                vRow.style.opacity = "0.5";
                                vRow.style.transform = "scale(0.98)";
                                setTimeout(() => {
                                    vRow.remove();
                                    sub.pending_videos = sub.pending_videos.filter(pv => pv.id !== v.id);
                                    if (sub.pending_videos.length === 0) {
                                        inboxHeader.textContent = "📥 Freigabeliste (0 ausstehend)";
                                        listDiv.innerHTML = `<div style="font-size:12.5px; color:var(--text-muted); font-style:italic; padding:5px 0;">Keine neuen Videos ausstehend.</div>`;
                                    } else {
                                        inboxHeader.textContent = `📥 Freigabeliste (${sub.pending_videos.length} ausstehend)`;
                                    }
                                }, 300);
                                appendConsoleLog(`[System]: Video "${v.title}" als ignoriert markiert.`);
                            } else {
                                alert("Fehler beim Ignorieren des Videos");
                                btnApprove.disabled = false;
                                btnIgnore.disabled = false;
                                btnIgnore.innerHTML = "🗑️ Ignorieren";
                            }
                        } catch (err) {
                            console.error(err);
                            alert("Netzwerkfehler beim Ignorieren");
                            btnApprove.disabled = false;
                            btnIgnore.disabled = false;
                            btnIgnore.innerHTML = "🗑️ Ignorieren";
                        }
                    });
                    
                    btnSearchParts.addEventListener("click", () => {
                        handoffMergeToDownloader(sub, v);
                    });
                    
                    vRight.appendChild(btnApprove);
                    vRight.appendChild(btnProcessInDownloader);
                    vRight.appendChild(btnSearchParts);
                    vRight.appendChild(btnIgnore);
                    vRight.appendChild(btnLink);
                    vRow.appendChild(vRight);
                    listDiv.appendChild(vRow);
                });
                inboxDiv.appendChild(listDiv);
            }
            detailsContainer.appendChild(inboxDiv);
        }
        
        // Collapsible states & Click handler
        let isExpanded = false;
        
        const updateExpandState = () => {
            if (isExpanded) {
                detailsContainer.style.display = "flex";
                expandCaret.innerHTML = "▼";
                expandCaret.style.color = "var(--accent)";
            } else {
                detailsContainer.style.display = "none";
                expandCaret.innerHTML = "▶";
                expandCaret.style.color = "var(--text-muted)";
            }
        };
        updateExpandState();
        
        infoCol.style.cursor = "pointer";
        infoCol.addEventListener("click", () => {
            isExpanded = !isExpanded;
            updateExpandState();
        });
        
        item.appendChild(detailsContainer);
        listContainer.appendChild(item);
    });
}

async function saveAllSubscriptions() {
    try {
        const response = await fetch("/api/youtube/subscriptions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subscriptions: currentSubscriptions })
        });
        if (!response.ok) {
            throw new Error("Fehler beim Speichern");
        }
        appendConsoleLog("[System]: YouTube-Abonnements erfolgreich aktualisiert.");
    } catch (e) {
        console.error("Error saving subscriptions:", e);
        alert("Fehler beim Speichern der Abonnements!");
    }
}

async function sendVideoToDownloader(sub, v) {
    // 1. Switch to Downloader tab
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    const viewYt = document.getElementById("view-youtube");
    if (viewYt) {
        viewYt.classList.remove("hidden");
        viewYt.classList.add("active");
    }
    document.querySelectorAll(".project-item").forEach(el => el.classList.remove("active"));
    
    // Reset merge modes
    ytDownloaderMergeMode = false;
    ytDownloaderMergeItems = [];
    ytDownloaderMergeSubId = null;
    
    // 2. Pre-fill URL
    const ytUrlInput = document.getElementById("yt-url");
    if (ytUrlInput) {
        ytUrlInput.value = v.url || `https://www.youtube.com/watch?v=${v.id}`;
    }
    
    // 3. Pre-fill storage options
    const cbNas = document.getElementById("yt-option-copy-nas");
    const cbPcloud = document.getElementById("yt-option-copy-pcloud");
    const cbLocal = document.getElementById("yt-option-copy-local");
    
    if (cbNas) {
        cbNas.checked = sub.copy_to_nas !== false;
        cbNas.dispatchEvent(new Event("change"));
    }
    if (cbPcloud) {
        cbPcloud.checked = !!sub.copy_to_pcloud;
        cbPcloud.dispatchEvent(new Event("change"));
    }
    if (cbLocal) {
        cbLocal.checked = !!sub.copy_to_local;
        cbLocal.dispatchEvent(new Event("change"));
    }
    
    const selNas = document.getElementById("yt-nas-destination");
    const selPcloud = document.getElementById("yt-pcloud-destination");
    const selLocal = document.getElementById("yt-local-destination");
    
    const nasDestId = sub.nas_destination_id || sub.destination_id || "";
    const pcloudDestId = sub.pcloud_destination_id || "";
    const localDestId = sub.local_destination_id || "";
    
    if (selNas && nasDestId) selNas.value = nasDestId;
    if (selPcloud && pcloudDestId) selPcloud.value = pcloudDestId;
    if (selLocal && localDestId) selLocal.value = localDestId;
    
    // 4. Remove from subscriptions list in background
    try {
        await fetch("/api/youtube/subscriptions/ignore", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subscription_id: sub.id, video_id: v.id })
        });
        // Remove locally from state and refresh UI
        sub.pending_videos = sub.pending_videos.filter(pv => pv.id !== v.id);
        renderSubscriptionsList();
    } catch (e) {
        console.error("Error archiving video on handoff:", e);
    }
    
    // 5. Start Link Analysis automatically
    analyseYtLink(true);
}

async function handoffMergeToDownloader(sub, v) {
    // 1. Switch to Downloader tab
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    const viewYt = document.getElementById("view-youtube");
    if (viewYt) {
        viewYt.classList.remove("hidden");
        viewYt.classList.add("active");
    }
    document.querySelectorAll(".project-item").forEach(el => el.classList.remove("active"));
    
    // 2. Set merge mode states
    ytDownloaderMergeMode = true;
    ytDownloaderMergeSubId = sub.id;
    ytDownloaderMergeItems = [];
    
    // Pre-fill URL in downloader tab
    const ytUrlInput = document.getElementById("yt-url");
    if (ytUrlInput) {
        ytUrlInput.value = v.url || `https://www.youtube.com/watch?v=${v.id}`;
    }
    
    // Pre-fill storage targets
    const cbNas = document.getElementById("yt-option-copy-nas");
    const cbPcloud = document.getElementById("yt-option-copy-pcloud");
    const cbLocal = document.getElementById("yt-option-copy-local");
    
    if (cbNas) {
        cbNas.checked = sub.copy_to_nas !== false;
        cbNas.dispatchEvent(new Event("change"));
    }
    if (cbPcloud) {
        cbPcloud.checked = !!sub.copy_to_pcloud;
        cbPcloud.dispatchEvent(new Event("change"));
    }
    if (cbLocal) {
        cbLocal.checked = !!sub.copy_to_local;
        cbLocal.dispatchEvent(new Event("change"));
    }
    
    const selNas = document.getElementById("yt-nas-destination");
    const selPcloud = document.getElementById("yt-pcloud-destination");
    const selLocal = document.getElementById("yt-local-destination");
    
    const nasDestId = sub.nas_destination_id || sub.destination_id || "";
    const pcloudDestId = sub.pcloud_destination_id || "";
    const localDestId = sub.local_destination_id || "";
    
    if (selNas && nasDestId) selNas.value = nasDestId;
    if (selPcloud && pcloudDestId) selPcloud.value = pcloudDestId;
    if (selLocal && localDestId) selLocal.value = localDestId;
    
    // Clean up merge title override
    let cleanTitle = v.title;
    const patterns = [
        /\bteil\s*\d+\b/i,
        /\bpart\s*\d+\b/i,
        /\bepisode\s*\d+\b/i,
        /#\s*\d+\b/i,
        /\b\d+\s*\/\s*\d+\b/i,
        /\b\d+\s*von\s*\d+\b/i,
        /\b\d+\.\s*teil\b/i,
        /\b\d+\.\s*part\b/i
    ];
    patterns.forEach(p => {
        cleanTitle = cleanTitle.replace(p, "");
    });
    cleanTitle = cleanTitle.replace(/\s*-\s*$/, "").replace(/\s+/g, " ").trim();
    
    const mergeTitleInput = document.getElementById("yt-merge-details-title");
    if (mergeTitleInput) {
        mergeTitleInput.value = cleanTitle || v.title;
    }
    
    const listContainer = document.getElementById("yt-merge-details-list");
    if (listContainer) {
        listContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">🔍 Suche nach Teilen auf YouTube...</div>`;
    }
    
    // Search parts
    fetch(`/api/youtube/search-parts?title=${encodeURIComponent(v.title)}`)
        .then(res => res.json())
        .then(data => {
            const results = data.results || [];
            
            // Build unique list of items
            const items = [];
            
            // 1. Add our initial video
            items.push({
                id: v.id,
                title: v.title,
                url: v.url || `https://www.youtube.com/watch?v=${v.id}`,
                thumbnail: v.thumbnail,
                checked: true,
                isInitial: true
            });
            
            // 2. Add search results, avoiding duplicates of the initial video
            results.forEach(r => {
                if (r.id !== v.id) {
                    items.push({
                        id: r.id,
                        title: r.title,
                        url: r.url,
                        thumbnail: r.thumbnail,
                        checked: false,
                        isInitial: false
                    });
                }
            });
            
            ytDownloaderMergeItems = items;
            renderDownloaderMergeItems();
        })
        .catch(err => {
            console.error(err);
            if (listContainer) {
                listContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--danger);">Fehler bei der Suche nach Teilen.</div>`;
            }
        });
        
    // 3. Start Link Analysis automatically on the initial URL to populate formats
    analyseYtLink(true);
}

async function addSubscription() {
    const nameInput = document.getElementById("abo-name");
    const urlInput = document.getElementById("abo-url");
    const filterInput = document.getElementById("abo-filter");
    const modeSelect = document.getElementById("abo-mode");
    const scheduleSelect = document.getElementById("abo-schedule");
    const filterGermanCheck = document.getElementById("abo-filter-german");
    const excludeInput = document.getElementById("abo-exclude");
    
    const copyNasCheck = document.getElementById("abo-copy-nas");
    const copyPcloudCheck = document.getElementById("abo-copy-pcloud");
    const copyLocalCheck = document.getElementById("abo-copy-local");
    const nasDestSelect = document.getElementById("abo-nas-destination");
    const pcloudDestSelect = document.getElementById("abo-pcloud-destination");
    const localDestSelect = document.getElementById("abo-local-destination");
    
    if (!nameInput || !urlInput) return;
    
    const name = nameInput.value.trim();
    const url = urlInput.value.trim();
    const filter = filterInput ? filterInput.value.trim() : "";
    const excludeKeywords = excludeInput ? excludeInput.value.trim() : "";
    const autoDownload = modeSelect ? (modeSelect.value !== "manual") : true;
    const schedule = scheduleSelect ? scheduleSelect.value : "hourly";
    const filterGerman = filterGermanCheck ? !!filterGermanCheck.checked : false;
    
    const copyToNas = copyNasCheck ? !!copyNasCheck.checked : true;
    const copyToPcloud = copyPcloudCheck ? !!copyPcloudCheck.checked : false;
    const copyToLocal = copyLocalCheck ? !!copyLocalCheck.checked : false;
    const nasDestId = nasDestSelect ? nasDestSelect.value : "";
    const pcloudDestId = pcloudDestSelect ? pcloudDestSelect.value : "";
    const localDestId = localDestSelect ? localDestSelect.value : "";
    
    if (!name || !url) {
        alert("Bitte geben Sie einen Namen und eine YouTube-URL oder einen Suchbegriff ein!");
        return;
    }
    
    // Generate UUID
    const newId = crypto.randomUUID();
    
    const newSub = {
        id: newId,
        name: name,
        url: url,
        search_filter: filter,
        exclude_keywords: excludeKeywords,
        destination_id: nasDestId, // Fallback/Backward compatibility
        nas_destination_id: nasDestId,
        pcloud_destination_id: pcloudDestId,
        local_destination_id: localDestId,
        copy_to_nas: copyToNas,
        copy_to_pcloud: copyToPcloud,
        copy_to_local: copyToLocal,
        enabled: true,
        last_checked: null,
        last_checked_timestamp: 0,
        downloaded_ids: [],
        auto_download: autoDownload,
        schedule: schedule,
        filter_german: filterGerman,
        pending_videos: []
    };
    
    currentSubscriptions.push(newSub);
    
    // Reset form inputs
    nameInput.value = "";
    urlInput.value = "";
    if (filterInput) filterInput.value = "";
    if (excludeInput) excludeInput.value = "";
    if (modeSelect) modeSelect.value = "auto";
    if (scheduleSelect) scheduleSelect.value = "hourly";
    if (filterGermanCheck) filterGermanCheck.checked = false;
    
    if (copyNasCheck) {
        copyNasCheck.checked = true;
        copyNasCheck.dispatchEvent(new Event("change"));
    }
    if (copyPcloudCheck) {
        copyPcloudCheck.checked = false;
        copyPcloudCheck.dispatchEvent(new Event("change"));
    }
    if (copyLocalCheck) {
        copyLocalCheck.checked = false;
        copyLocalCheck.dispatchEvent(new Event("change"));
    }
    
    // Optimistic render and background save
    renderSubscriptionsList();
    await saveAllSubscriptions();
}

async function checkAllSubscriptions() {
    const btn = document.getElementById("btn-check-all-abos");
    if (btn) {
        btn.disabled = true;
        btn.textContent = "🔄 Prüfe...";
    }
    
    appendConsoleLog("[System]: Starte manuelle Prüfung aller YouTube Abos...");
    
    try {
        const response = await fetch("/api/youtube/subscriptions/check", {
            method: "POST"
        });
        if (response.ok) {
            appendConsoleLog("✅ YouTube Abo-Überprüfung im Hintergrund gestartet.");
            alert("Abo-Überprüfung im Hintergrund gestartet! Das kann einige Minuten dauern.");
        } else {
            throw new Error("API meldet Fehler");
        }
    } catch (e) {
        console.error("Error checking subscriptions:", e);
        appendConsoleLog(`❌ Fehler beim Starten der Abo-Überprüfung: ${e}`);
        alert("Fehler beim Starten der Abo-Überprüfung!");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = "🔄 Jetzt alle prüfen";
        }
    }
}


// Helper to render files list in clean modal with sizes and video codecs
function renderCleanFileList(files, isJunk) {
    const sortedFiles = [...files].sort((a, b) => {
        const nameA = typeof a === "string" ? a : (a.name || "");
        const nameB = typeof b === "string" ? b : (b.name || "");
        return nameA.localeCompare(nameB, undefined, { numeric: true, sensitivity: "base" });
    });
    return sortedFiles.map(fileObj => {
        const f = typeof fileObj === "string" ? fileObj : fileObj.name;
        const sizeBytes = fileObj.size_bytes || 0;
        const codec = fileObj.codec || "";
        const resolution = fileObj.resolution || "";
        
        let sizeStr = "";
        if (sizeBytes > 0) {
            if (sizeBytes > 1024 * 1024 * 1024) {
                sizeStr = `(${(sizeBytes / (1024 * 1024 * 1024)).toFixed(2)} GB)`;
            } else if (sizeBytes > 1024 * 1024) {
                sizeStr = `(${(sizeBytes / (1024 * 1024)).toFixed(1)} MB)`;
            } else {
                sizeStr = `(${(sizeBytes / 1024).toFixed(0)} KB)`;
            }
        }
        
        let detailsStr = "";
        if (codec || resolution) {
            const parts = [];
            if (codec) parts.push(codec.toUpperCase());
            if (resolution) parts.push(resolution);
            detailsStr = `<span style="background: rgba(var(--accent-rgb), 0.15); color: var(--accent); font-size: 9.5px; font-weight: 600; padding: 1.5px 5px; border-radius: 4px; margin-left: 6px; letter-spacing: 0.3px;">${parts.join(" • ")}</span>`;
        }
        
        return `
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer; padding: 2px 0;">
                <input type="checkbox" class="clean-cb-item" data-file="${escapeHTML(f)}" ${isJunk ? 'checked' : ''} style="accent-color:#ff4757;">
                <span style="font-size:11px; color:var(--text-main); word-break:break-all;">
                    ${escapeHTML(f)} 
                    <span style="color:var(--text-muted); font-size: 10.5px; margin-left: 4px;">${sizeStr}</span>
                    ${detailsStr}
                </span>
            </label>
        `;
    }).join("");
}

// Helper clean project
async function cleanCurrentProject() {
    if (!currentProject) return;
    
    // UI Loading state
    const overlay = document.getElementById("clean-modal-overlay");
    const modal = document.getElementById("clean-modal");
    const list = document.getElementById("clean-list");
    
    list.innerHTML = `<div style="color:var(--text-muted); font-size:12px;">Scanne Ordner...</div>`;
    
    overlay.classList.remove("hidden");
    setTimeout(() => {
        overlay.style.opacity = "1";
        overlay.style.pointerEvents = "auto";
        modal.style.transform = "translateY(0)";
    }, 10);
    
    try {
        const response = await fetch("/api/preview_clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project: currentProject })
        });
        
        if (!response.ok) throw new Error("Fehler beim Scannen");
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            closeCleanModal();
            return;
        }
        
        list.innerHTML = "";
        
        const groups = data.groups || {};
        if (Object.keys(groups).length === 0) {
            list.innerHTML = `<div style="color:var(--text-muted); font-size:12px;">Ordner ist bereits komplett leer.</div>`;
            return;
        }
        
        // Render groups sorted alphabetically by extension
        const sortedKeys = Object.keys(groups).sort();
        for (const ext of sortedKeys) {
            const files = groups[ext];
            // Check by default if it's typical junk
            const isJunk = ['txt', 'url', 'exe', 'ds_store', 'nfo', 'jpg', 'png'].includes(ext);
            
            const groupDiv = document.createElement("div");
            groupDiv.className = "clean-group-container";
            groupDiv.style.marginBottom = "10px";
            groupDiv.innerHTML = `
                <div style="font-size:12px; font-weight:bold; color:var(--accent); text-transform:uppercase; margin-bottom:5px; display:flex; justify-content:space-between; align-items:center;">
                    <span>Dateityp: .${ext} <span style="color:var(--text-muted); font-weight:normal;">(${files.length} Dateien)</span></span>
                    <span class="group-select-toggle" data-ext="${ext}" style="font-size:10px; color:var(--text-muted); text-transform:none; font-weight:normal; cursor:pointer; text-decoration:underline;">Alle aus-/abwählen</span>
                </div>
                <div style="display:flex; flex-direction:column; gap:5px; padding-left:10px; border-left:2px solid rgba(255,255,255,0.05);">
                    ${renderCleanFileList(files, isJunk)}
                </div>
            `;
            list.appendChild(groupDiv);
        }
        
        // Store target path for execution
        document.getElementById("btn-clean-execute").dataset.target = currentProject;
        
    } catch (e) {
        alert("Fehler: " + e.message);
        closeCleanModal();
    }
}

// Tool events
async function runToolPullFiles() {
    const targetPath = document.getElementById("tools-target-path").value || currentProject;
    if (activeProjectsProcessing && activeProjectsProcessing.has(targetPath)) {
        alert("⚠️ Dieses Projekt wird bereits verarbeitet oder befindet sich in der Warteschlange!");
        return;
    }
    expandConsole();
    appendConsoleLog("[System]: Verschiebe Dateien aus Unterordnern nach oben...");
    
    try {
        const response = await fetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                media_type: "tool_pull_files",
                project_name: targetPath
            })
        });
        if (response.ok) {
            connectLogStream();
        } else {
            appendConsoleLog(`[System]: ❌ Serverfehler (${response.status}) beim Verschieben.`);
        }
    } catch (e) {
        console.error("Error in runToolPullFiles:", e);
        appendConsoleLog(`[System]: ❌ Fehler beim Verschieben: ${e.message}`);
    }
}
async function runToolClean(path) {
    const targetPath = path || currentProject;
    if (!targetPath) {
        alert("⚠️ Bitte wähle zuerst einen Zielordner-Pfad aus!");
        return;
    }
    
    // UI Loading state
    const overlay = document.getElementById("clean-modal-overlay");
    const modal = document.getElementById("clean-modal");
    const list = document.getElementById("clean-list");
    
    list.innerHTML = `<div style="color:var(--text-muted); font-size:12px;">Scanne Ordner...</div>`;
    
    overlay.classList.remove("hidden");
    setTimeout(() => {
        overlay.style.opacity = "1";
        overlay.style.pointerEvents = "auto";
        modal.style.transform = "translateY(0)";
    }, 10);
    
    try {
        const response = await fetch("/api/preview_clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project: targetPath })
        });
        
        if (!response.ok) throw new Error("Fehler beim Scannen");
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            closeCleanModal();
            return;
        }
        
        list.innerHTML = "";
        
        const groups = data.groups || {};
        if (Object.keys(groups).length === 0) {
            list.innerHTML = `<div style="color:var(--text-muted); font-size:12px;">Ordner ist bereits komplett leer.</div>`;
            return;
        }
        
        // Render groups sorted alphabetically by extension
        const sortedKeys = Object.keys(groups).sort();
        for (const ext of sortedKeys) {
            const files = groups[ext];
            // Check by default if it's typical junk
            const isJunk = ['txt', 'url', 'exe', 'ds_store', 'nfo', 'jpg', 'png'].includes(ext);
            
            const groupDiv = document.createElement("div");
            groupDiv.className = "clean-group-container";
            groupDiv.style.marginBottom = "10px";
            groupDiv.innerHTML = `
                <div style="font-size:12px; font-weight:bold; color:var(--accent); text-transform:uppercase; margin-bottom:5px; display:flex; justify-content:space-between; align-items:center;">
                    <span>Dateityp: .${ext} <span style="color:var(--text-muted); font-weight:normal;">(${files.length} Dateien)</span></span>
                    <span class="group-select-toggle" data-ext="${ext}" style="font-size:10px; color:var(--text-muted); text-transform:none; font-weight:normal; cursor:pointer; text-decoration:underline;">Alle aus-/abwählen</span>
                </div>
                <div style="display:flex; flex-direction:column; gap:5px; padding-left:10px; border-left:2px solid rgba(255,255,255,0.05);">
                    ${renderCleanFileList(files, isJunk)}
                </div>
            `;
            list.appendChild(groupDiv);
        }
        
        // Store target path for execution
        document.getElementById("btn-clean-execute").dataset.target = targetPath;
        
    } catch (e) {
        alert("Fehler: " + e.message);
        closeCleanModal();
    }
}

function closeCleanModal() {
    const overlay = document.getElementById("clean-modal-overlay");
    const modal = document.getElementById("clean-modal");
    
    overlay.style.opacity = "0";
    overlay.style.pointerEvents = "none";
    modal.style.transform = "translateY(20px)";
    setTimeout(() => {
        overlay.classList.add("hidden");
    }, 300);
}

// Medienpfade bereinigen (Clean Paths Tool)
function openPathsCleanModal() {
    const overlay = document.getElementById("paths-clean-modal-overlay");
    const modal = document.getElementById("paths-clean-modal");
    
    // Standardmäßig Phase 1 anzeigen und Checkboxen aktivieren
    document.getElementById("paths-clean-opt-inbox").checked = true;
    document.getElementById("paths-clean-opt-output").checked = true;
    document.getElementById("paths-clean-phase-select").classList.remove("hidden");
    document.getElementById("paths-clean-phase-preview").classList.add("hidden");
    document.getElementById("paths-clean-list").innerHTML = "";
    
    overlay.classList.remove("hidden");
    setTimeout(() => {
        overlay.style.opacity = "1";
        overlay.style.pointerEvents = "auto";
        modal.style.transform = "translateY(0)";
    }, 10);
}

function closePathsCleanModal() {
    const overlay = document.getElementById("paths-clean-modal-overlay");
    const modal = document.getElementById("paths-clean-modal");
    
    overlay.style.opacity = "0";
    overlay.style.pointerEvents = "none";
    modal.style.transform = "translateY(20px)";
    setTimeout(() => {
        overlay.classList.add("hidden");
    }, 300);
}

function backToPathsCleanSelect() {
    document.getElementById("paths-clean-phase-preview").classList.add("hidden");
    document.getElementById("paths-clean-phase-select").classList.remove("hidden");
}

async function runPathsCleanScan() {
    const scanInbox = document.getElementById("paths-clean-opt-inbox").checked;
    const scanOutput = document.getElementById("paths-clean-opt-output").checked;
    
    if (!scanInbox && !scanOutput) {
        alert("Bitte wähle mindestens einen Pfad aus (Inbox und/oder Output)!");
        return;
    }
    
    const list = document.getElementById("paths-clean-list");
    list.innerHTML = `<div style="color:var(--text-muted); font-size:13px; text-align:center; padding:20px;">🔍 Scanne Medienpfade, bitte warten...</div>`;
    
    // Zu Phase 2 wechseln
    document.getElementById("paths-clean-phase-select").classList.add("hidden");
    document.getElementById("paths-clean-phase-preview").classList.remove("hidden");
    
    try {
        const response = await fetch("/api/paths/preview_clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ inbox: scanInbox, output: scanOutput })
        });
        
        if (!response.ok) throw new Error("Fehler beim Scannen der Medienpfade.");
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            backToPathsCleanSelect();
            return;
        }
        
        list.innerHTML = "";
        
        const inboxFiles = data.inbox_files || [];
        const outputFiles = data.output_files || [];
        
        if (inboxFiles.length === 0 && outputFiles.length === 0) {
            list.innerHTML = `<div style="color:var(--text-muted); font-size:13px; text-align:center; padding:20px;">Keine Dateien in den ausgewählten Pfaden gefunden.</div>`;
            return;
        }
        
        const renderSection = (title, files, source) => {
            if (files.length === 0) return "";
            
            const totalBytes = files.reduce((sum, f) => sum + (f.size_bytes || 0), 0);
            
            return `
                <div style="margin-bottom: 20px;">
                    <div style="font-size:13px; font-weight:bold; color:var(--accent); margin-bottom:8px; display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:4px;">
                        <span>📂 ${title}</span>
                        <span style="color:var(--text-muted); font-weight:normal;">(${files.length} Dateien, Gesamt: ${formatBytes(totalBytes)})</span>
                    </div>
                    <div style="display:flex; flex-direction:column; gap:6px; padding-left:8px;">
                        ${files.map(f => {
                            const isJunk = ['.txt', '.url', '.nfo', '.db', '.ds_store'].some(ext => f.rel_path.toLowerCase().endsWith(ext)) || f.rel_path.toLowerCase().includes("ds_store");
                            return `
                                <label style="display:flex; align-items:center; justify-content:space-between; gap:10px; cursor:pointer; padding:6px 8px; background:rgba(255,255,255,0.01); border-radius:var(--radius-sm); border:1px solid rgba(255,255,255,0.02); transition:background 0.2s;">
                                    <div style="display:flex; align-items:center; gap:10px; flex:1; min-width:0;">
                                        <input type="checkbox" class="paths-clean-cb-item" data-source="${source}" data-file="${f.rel_path}" data-junk="${isJunk}" checked style="accent-color:#ff4757; width:16px; height:16px; flex-shrink:0;">
                                        <span style="font-size:12px; color:var(--text-main); word-break:break-all; text-align:left;">${f.rel_path}</span>
                                    </div>
                                    <span style="font-size:11px; color:var(--text-muted); flex-shrink:0;">${formatBytes(f.size_bytes)}</span>
                                </label>
                            `;
                        }).join("")}
                    </div>
                </div>
            `;
        };
        
        let htmlContent = "";
        if (scanInbox && inboxFiles.length > 0) {
            htmlContent += renderSection("Inbox (Medien Input)", inboxFiles, "inbox");
        }
        if (scanOutput && outputFiles.length > 0) {
            htmlContent += renderSection("Output (Medien Output)", outputFiles, "output");
        }
        
        list.innerHTML = htmlContent;
        
    } catch (e) {
        alert("Fehler beim Scannen: " + e.message);
        backToPathsCleanSelect();
    }
}

async function executePathsClean() {
    const cbs = document.querySelectorAll(".paths-clean-cb-item:checked");
    if (cbs.length === 0) {
        alert("Bitte wähle mindestens eine Datei zum Löschen aus!");
        return;
    }
    
    const confirmDelete = confirm(`Bist du sicher, dass du die ${cbs.length} ausgewählten Dateien unwiderruflich löschen möchtest?`);
    if (!confirmDelete) return;
    
    const inboxFiles = [];
    const outputFiles = [];
    
    cbs.forEach(cb => {
        const source = cb.dataset.source;
        const file = cb.dataset.file;
        if (source === "inbox") {
            inboxFiles.push(file);
        } else if (source === "output") {
            outputFiles.push(file);
        }
    });
    
    closePathsCleanModal();
    expandConsole();
    appendConsoleLog("[System]: Löschvorgang gestartet...");
    
    try {
        const response = await fetch("/api/paths/clean", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                inbox_files: inboxFiles,
                output_files: outputFiles
            })
        });
        
        if (!response.ok) throw new Error("Fehler bei der Übertragung an den Server.");
        const data = await response.json();
        
        if (data.status === "ok") {
            const filesDeletedCount = (data.deleted_files || []).length;
            const dirsDeletedCount = (data.deleted_dirs || []).length;
            appendConsoleLog(`[System]: Löschvorgang erfolgreich abgeschlossen!`);
            appendConsoleLog(`[System]: -> ${filesDeletedCount} Dateien gelöscht.`);
            if (dirsDeletedCount > 0) {
                appendConsoleLog(`[System]: -> ${dirsDeletedCount} leere Ordner bereinigt.`);
            }
            loadStatus();
        } else {
            appendConsoleLog(`[System]: ❌ Fehler beim Löschen: ${data.error || 'Unbekannter Fehler'}`);
            alert(`Fehler beim Löschen: ${data.error}`);
        }
    } catch (e) {
        appendConsoleLog(`[System]: ❌ Fehler beim Löschen: ${e.message}`);
        alert("Fehler beim Löschen: " + e.message);
    }
}

async function runToolConvert() {
    const targetPath = document.getElementById("tools-target-path").value || currentProject;
    if (activeProjectsProcessing && activeProjectsProcessing.has(targetPath)) {
        alert("⚠️ Dieses Projekt wird bereits verarbeitet oder befindet sich in der Warteschlange!");
        return;
    }
    expandConsole();
    appendConsoleLog("[System]: Starte Batch-H.265-Konvertierung...");
    const quality = document.getElementById("tool-quality-slider") ? parseInt(document.getElementById("tool-quality-slider").value, 10) : 60;
    try {
        const response = await fetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                media_type: "tool_batch_convert",
                project_name: targetPath,
                quality: quality
            })
        });
        if (response.ok) {
            connectLogStream();
        } else {
            appendConsoleLog(`[System]: ❌ Serverfehler (${response.status}) bei der Konvertierung.`);
        }
    } catch (e) {
        console.error("Error in runToolConvert:", e);
        appendConsoleLog(`[System]: ❌ Fehler bei der Konvertierung: ${e.message}`);
    }
}

async function runToolGeneric(toolType, logMsg, extraParams = {}) {
    const targetPath = document.getElementById("tools-target-path").value.trim();
    
    if (!targetPath) {
        alert("⚠️ Sicherheits-Stopp: Bitte wähle zuerst einen spezifischen Zielordner-Pfad aus oder klicke auf 'Durchsuchen'!");
        return;
    }
    if (activeProjectsProcessing && activeProjectsProcessing.has(targetPath)) {
        alert("⚠️ Dieses Projekt wird bereits verarbeitet oder befindet sich in der Warteschlange!");
        return;
    }
    
    // Check if a dangerous root directory is selected
    const nasRoot = currentSettings.nas_root || "";
    const inbox = currentSettings.inbox_dir || "";
    const outbox = currentSettings.outbox_dir || "";
    
    if (targetPath === nasRoot || targetPath === inbox || targetPath === outbox || targetPath === "/") {
        const confirmRoot = confirm(`⚠️ WARNUNG: Du hast einen Hauptordner (${targetPath}) ausgewählt!\n\nDas Werkzeug wird auf ALLE Unterordner und Dateien darin angewendet, was sehr lange dauern kann.\n\nBist du dir ganz sicher, dass du keinen spezifischen Unterordner auswählen wolltest?`);
        if (!confirmRoot) return;
    }

    expandConsole();
    appendConsoleLog(`[System]: ${logMsg}`);
    
    const openAfter = document.getElementById("opt-open-after")?.checked || false;
    const deleteOriginal = document.getElementById("opt-delete-original")?.checked || false;
    
    const payload = {
        media_type: toolType,
        project_name: targetPath,
        open_after: openAfter,
        delete_original: deleteOriginal,
        ...extraParams
    };
    
    const response = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (response.ok) connectLogStream();
}

// ==========================================================================
// EVENT LISTENERS BINDINGS
// ==========================================================================
function initEventListeners() {
    const connectNasBtn = document.getElementById("btn-connect-nas");
    if (connectNasBtn) {
        connectNasBtn.addEventListener("click", async () => {
            connectNasBtn.disabled = true;
            connectNasBtn.textContent = "Verbinde...";
            try {
                const response = await fetch("/api/nas/connect", { method: "POST" });
                const data = await response.json();
                alert(data.message || (response.ok ? "NAS wurde verbunden." : "NAS-Verbindung fehlgeschlagen."));
                await loadStatus();
            } catch (error) {
                console.error("NAS-Verbindung fehlgeschlagen:", error);
                alert("NAS-Verbindung fehlgeschlagen. Bitte prüfe, ob der Server erreichbar ist.");
            } finally {
                connectNasBtn.disabled = false;
                connectNasBtn.textContent = "Verbinden";
            }
        });
    }

    // Settings Sub-Tabs navigation click listeners
    const settingsTabButtons = document.querySelectorAll(".settings-tab-btn");
    const settingsTabDescriptions = {
        "tab-paths": "Passe die globalen Pfade für das Medienwerkzeug an. Diese Werte werden für das Importieren und Verschieben verwendet.",
        "tab-sync": "Verwalte deine Speicherziele, Import-Quellen und Sync-Kategorien für die automatische Medienverteilung.",
        "tab-notifications": "Konfiguriere, wann und wie du über abgeschlossene Verarbeitungen benachrichtigt wirst.",
        "tab-appearance": "Passe das Erscheinungsbild der App an und verwalte die Abhängigkeiten zu externen CLI-Tools."
    };
    settingsTabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTabId = btn.getAttribute("data-settings-tab");

            settingsTabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            document.querySelectorAll(".settings-tab-panel").forEach(panel => {
                if (panel.id === `settings-${targetTabId}`) {
                    panel.classList.remove("hidden");
                } else {
                    panel.classList.add("hidden");
                }
            });

            const descEl = document.getElementById("settings-tab-desc");
            if (descEl && settingsTabDescriptions[targetTabId]) {
                descEl.textContent = settingsTabDescriptions[targetTabId];
            }
        });
    });

    // Refresh & Clean
    document.getElementById("btn-scan-project").addEventListener("click", () => scanProject(currentProject));
    document.getElementById("btn-clean-project").addEventListener("click", cleanCurrentProject);
    
    const cleanList = document.getElementById("clean-list");
    if (cleanList) {
        cleanList.addEventListener("click", (e) => {
            const toggle = e.target.closest(".group-select-toggle");
            if (toggle) {
                const groupContainer = toggle.closest(".clean-group-container");
                if (groupContainer) {
                    const checkboxes = groupContainer.querySelectorAll(".clean-cb-item");
                    const anyUnchecked = Array.from(checkboxes).some(cb => !cb.checked);
                    checkboxes.forEach(cb => {
                        const wasChecked = cb.checked;
                        cb.checked = anyUnchecked;
                        if (wasChecked !== anyUnchecked) {
                            cb.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                    });
                }
            }
        });
        
        cleanList.addEventListener("change", (e) => {
            const cb = e.target.closest(".clean-cb-item");
            if (cb) {
                const filename = cb.dataset.file;
                if (!filename) return;
                
                const dotIdx = filename.lastIndexOf(".");
                if (dotIdx === -1) return;
                const ext = filename.substring(dotIdx).toLowerCase();
                const videoExtensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov'];
                
                if (videoExtensions.includes(ext)) {
                    const baseName = filename.substring(0, dotIdx);
                    const isChecked = cb.checked;
                    
                    const otherCbs = cleanList.querySelectorAll(".clean-cb-item");
                    otherCbs.forEach(otherCb => {
                        if (otherCb === cb) return;
                        const otherFile = otherCb.dataset.file;
                        if (!otherFile) return;
                        const otherDotIdx = otherFile.lastIndexOf(".");
                        if (otherDotIdx === -1) return;
                        
                        const otherBaseName = otherFile.substring(0, otherDotIdx);
                        const otherExt = otherFile.substring(otherDotIdx).toLowerCase();
                        
                        if (otherBaseName === baseName && !videoExtensions.includes(otherExt)) {
                            if (otherCb.checked !== isChecked) {
                                otherCb.checked = isChecked;
                                const label = otherCb.closest("label");
                                if (label) {
                                    label.style.transition = "background-color 0.2s ease";
                                    label.style.backgroundColor = "rgba(var(--accent-rgb), 0.25)";
                                    setTimeout(() => {
                                        label.style.backgroundColor = "transparent";
                                    }, 800);
                                }
                            }
                        }
                    });
                }
            }
        });
    }
    
    // Import StreamFab Preview & Execution
    let currentImportPreviewData = [];

    document.getElementById("btn-streamfab-import").addEventListener("click", async () => {
        appendConsoleLog("[System]: Lade Import-Vorschau...");
        try {
            const response = await fetch("/api/streamfab-import", { method: "GET" });
            const data = await response.json();
            if (data.status === "ok") {
                currentImportPreviewData = data.preview;
                renderImportPreviewModal(currentImportPreviewData);
                document.getElementById("modal-import-preview").classList.add("active");
            } else {
                appendConsoleLog("❌ Fehler beim Laden der Import-Vorschau.");
            }
        } catch (e) {
            appendConsoleLog(`❌ Fehler beim Laden der Import-Vorschau: ${e}`);
        }
    });

    window.closeImportPreview = function() {
        document.getElementById("modal-import-preview").classList.remove("active");
    };

    window.openFolderInFinder = function(path) {
        fetch(`/api/system-open-folder?path=${encodeURIComponent(path)}`).catch(() => {});
    };

    function renderImportPreviewModal(previewData) {
        const listContainer = document.getElementById("import-preview-list");
        listContainer.innerHTML = "";
        
        if (!previewData || previewData.length === 0) {
            listContainer.innerHTML = "<p class='text-muted'>Keine Dateien zum Importieren gefunden.</p>";
            return;
        }

        // --- Bulk Action Toolbar ---
        let allExtensions = new Set();
        previewData.forEach(g => g.files.forEach(f => {
            let parts = f.filename.split('.');
            if (parts.length > 1) {
                allExtensions.add("." + parts[parts.length-1].toLowerCase());
            } else {
                allExtensions.add("Ohne Endung");
            }
        }));
        
        const bulkDiv = document.createElement("div");
        bulkDiv.className = "flex justify-between items-center mb-4 p-3 rounded";
        bulkDiv.style.background = "var(--bg-main)";
        bulkDiv.style.border = "1px solid var(--border-color)";
        bulkDiv.innerHTML = `
            <div class="flex items-center gap-3">
                <span class="font-bold text-sm">Filter:</span>
                <select id="filter-ext" class="input input-sm" style="width:140px;" onchange="applyVisualFilter()">
                    <option value="all">Alle anzeigen</option>
                    ${Array.from(allExtensions).sort().map(ext => `<option value="${ext}">${ext}</option>`).join("")}
                </select>
            </div>
            <div class="flex items-center gap-3 border-l border-gray-600 pl-4">
                <span class="text-sm">Sichtbare setzen auf:</span>
                <select id="bulk-action" class="input input-sm" style="width:130px;">
                    <option value="import">Importieren</option>
                    <option value="ignore">Ignorieren</option>
                    <option value="delete">🗑 Löschen</option>
                </select>
                <button class="btn btn-sm btn-secondary" onclick="applyBulkImportAction()">Anwenden</button>
            </div>
        `;
        listContainer.appendChild(bulkDiv);

        window.applyVisualFilter = function() {
            const ext = document.getElementById("filter-ext").value;
            // Iterate over all groups and their rows
            document.querySelectorAll(".import-group").forEach(groupDiv => {
                let visibleCount = 0;
                groupDiv.querySelectorAll(".file-row").forEach(row => {
                    if (ext === "all" || row.getAttribute("data-ext") === ext) {
                        row.style.display = "flex";
                        visibleCount++;
                    } else {
                        row.style.display = "none";
                    }
                });
                // Hide entire group if no files are visible
                groupDiv.style.display = visibleCount > 0 ? "block" : "none";
            });
        };

        window.applyBulkImportAction = function() {
            const act = document.getElementById("bulk-action").value;
            document.querySelectorAll("#import-preview-list .file-row").forEach(row => {
                if (row.style.display !== "none") {
                    const sel = row.querySelector(".action-select");
                    if (sel) sel.value = act;
                }
            });
        };
        // --- End Bulk Action Toolbar ---

        previewData.forEach((group) => {
            // Sort files by extension, then name
            group.files.sort((a, b) => {
                const extA = a.filename.split('.').pop().toLowerCase();
                const extB = b.filename.split('.').pop().toLowerCase();
                if (extA !== extB) return extA.localeCompare(extB);
                return a.filename.localeCompare(b.filename);
            });

            const groupDiv = document.createElement("div");
            groupDiv.className = "mb-4 border border-gray-700 rounded p-3 inline-style-119 import-group";
            groupDiv.style.background = "var(--bg-card)";
            
            // Assume all files in group come from roughly same dir
            const firstPath = group.files.length > 0 ? group.files[0].path : "";
            const dirPath = firstPath ? firstPath.substring(0, firstPath.lastIndexOf('/')) : "";
            
            const header = document.createElement("div");
            header.className = "flex justify-between items-center mb-2 pb-2 border-b border-gray-700";
            header.innerHTML = `
                <div>
                    <strong style="color: var(--accent);">${group.project_name}</strong>
                    <span class="text-muted text-sm ml-2">Ordner: ${group.safe_folder_name}</span>
                </div>
                <button class="btn btn-xs btn-secondary" onclick="openFolderInFinder('${dirPath.replace(/'/g, "\\'")}')" title="Im Finder öffnen">📂 Finder</button>
            `;
            groupDiv.appendChild(header);
            
            group.files.forEach((file) => {
                const fileRow = document.createElement("div");
                fileRow.className = "flex justify-between items-center py-1 text-sm file-row";
                fileRow.style.borderBottom = "1px solid var(--border-color)";
                
                let parts = file.filename.split('.');
                let fExt = parts.length > 1 ? "." + parts[parts.length-1].toLowerCase() : "Ohne Endung";
                fileRow.setAttribute("data-ext", fExt);
                
                const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
                const defaultAction = "import";
                
                fileRow.innerHTML = `
                    <div style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 10px;" title="${file.path}">
                        ${file.filename} <span class="text-muted" style="font-size: 0.8em;">(${sizeMb} MB)</span>
                    </div>
                    <select class="input input-sm action-select" data-group="${group.safe_folder_name}" data-path="${file.path}" data-filename="${file.filename}" style="width: 130px;">
                        <option value="import" ${defaultAction === 'import' ? 'selected' : ''}>Importieren</option>
                        <option value="ignore">Ignorieren</option>
                        <option value="delete">🗑 Löschen</option>
                    </select>
                `;
                groupDiv.appendChild(fileRow);
            });
            
            listContainer.appendChild(groupDiv);
        });
    }

    window.confirmImportPreview = async function() {
        const selects = document.querySelectorAll("#import-preview-list .action-select");
        const importItems = {};
        const deleteItems = [];
        
        selects.forEach(select => {
            const action = select.value;
            const group = select.getAttribute("data-group");
            const path = select.getAttribute("data-path");
            
            if (action === "import") {
                if (!importItems[group]) importItems[group] = [];
                importItems[group].push(path);
            } else if (action === "delete") {
                deleteItems.push(path);
            }
        });
        
        closeImportPreview();
        appendConsoleLog("[System]: Führe Import aus...");
        
        try {
            const response = await fetch("/api/streamfab-import", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ import_items: importItems, delete_items: deleteItems })
            });
            const data = await response.json();
            if (data.status === "ok") {
                appendConsoleLog(`✅ ${data.moved_count} Datei(en) in die Inbox importiert.`);
                loadStatus();
                if (currentProject === "") {
                    scanProject("");
                }
            } else {
                appendConsoleLog(`❌ Fehler beim StreamFab Import.`);
            }
        } catch (e) {
            appendConsoleLog(`❌ Fehler beim StreamFab Import: ${e}`);
        }
    };
    
    // Browse Tools Path
    const btnBrowseTools = document.getElementById("btn-browse-tools-path");
    if(btnBrowseTools) {
        btnBrowseTools.addEventListener("click", async () => {
            try {
                const response = await fetch("/api/browse-folder");
                const data = await response.json();
                if(data.status === "ok" && data.path) {
                    document.getElementById("tools-target-path").value = data.path;
                }
            } catch (e) {
                console.error("Browse folder error:", e);
            }
        });
    }
    
    // Workflow routing relies entirely on the big cards now.
    
    // Series searches & loads
    document.getElementById("btn-search-series").addEventListener("click", searchSeries);
    document.getElementById("series-search-query").addEventListener("keypress", (e) => {
        if (e.key === "Enter") searchSeries();
    });
    document.getElementById("btn-fetch-episodes").addEventListener("click", fetchEpisodes);
    document.getElementById("btn-execute-series-process").addEventListener("click", executeSeriesWorkflow);
    
    // Manual Movie setup
    const btnManualMovie = document.getElementById("btn-manual-movie");
    const manualMovieContainer = document.getElementById("manual-movie-container");
    if (btnManualMovie && manualMovieContainer) {
        btnManualMovie.addEventListener("click", () => {
            isManualMovieMode = !isManualMovieMode;
            if (isManualMovieMode) {
                btnManualMovie.classList.add("active");
                btnManualMovie.textContent = "Suche nutzen";
                manualMovieContainer.classList.remove("hidden");
                const movieResults = document.getElementById("movie-search-results");
                if (movieResults) movieResults.innerHTML = "";
                const selectedMoviePanel = document.getElementById("selected-movie-panel");
                if (selectedMoviePanel) selectedMoviePanel.classList.add("hidden");
                
                updateSelectedMovieFromInputs();
            } else {
                btnManualMovie.classList.remove("active");
                btnManualMovie.textContent = "Manuell eintragen";
                manualMovieContainer.classList.add("hidden");
                selectedMovie = null;
            }
        });
    }
    
    const updateSelectedMovieFromInputs = () => {
        if (isManualMovieMode) {
            const titleVal = document.getElementById("manual-movie-title").value.trim() || currentProject || "Manueller Film";
            const yearVal = document.getElementById("manual-movie-year").value.trim() || "";
            const plotVal = document.getElementById("manual-movie-plot").value.trim() || "";
            
            const movieMetaObj = {
                title: titleVal,
                year: yearVal,
                plot: plotVal
            };
            
            selectedMovie = {
                id: JSON.stringify(movieMetaObj),
                name: titleVal,
                provider: "manual"
            };
        }
    };
    document.getElementById("manual-movie-title")?.addEventListener("input", updateSelectedMovieFromInputs);
    document.getElementById("manual-movie-year")?.addEventListener("input", updateSelectedMovieFromInputs);
    document.getElementById("manual-movie-plot")?.addEventListener("input", updateSelectedMovieFromInputs);

    // Manual Series setup
    const btnManualSeries = document.getElementById("btn-manual-series");
    const manualSeriesContainer = document.getElementById("manual-series-container");
    if (btnManualSeries && manualSeriesContainer) {
        btnManualSeries.addEventListener("click", () => {
            isManualSeriesMode = !isManualSeriesMode;
            if (isManualSeriesMode) {
                btnManualSeries.classList.add("active");
                btnManualSeries.textContent = "Suche nutzen";
                manualSeriesContainer.classList.remove("hidden");
                const seriesResults = document.getElementById("series-search-results");
                if (seriesResults) seriesResults.innerHTML = "";
                const selectedShowPanel = document.getElementById("selected-show-panel");
                if (selectedShowPanel) selectedShowPanel.classList.add("hidden");
                
                updateSelectedShowFromInputs();
                renderMatchingMatrix();
                const seriesExec = document.getElementById("series-execution-panel");
                if (seriesExec) seriesExec.classList.remove("hidden");
            } else {
                btnManualSeries.classList.remove("active");
                btnManualSeries.textContent = "Manuell eintragen";
                manualSeriesContainer.classList.add("hidden");
                selectedShow = null;
                const matchContainer = document.getElementById("matching-panel-container");
                if (matchContainer) matchContainer.innerHTML = "";
                const seriesExec = document.getElementById("series-execution-panel");
                if (seriesExec) seriesExec.classList.add("hidden");
            }
        });
    }
    
    const updateSelectedShowFromInputs = () => {
        if (isManualSeriesMode) {
            const titleVal = document.getElementById("manual-series-title").value.trim() || currentProject || "Manuelle Serie";
            const plotVal = document.getElementById("manual-series-plot").value.trim() || "";
            
            const showMetaObj = {
                title: titleVal,
                plot: plotVal
            };
            
            selectedShow = {
                id: JSON.stringify(showMetaObj),
                name: titleVal,
                plot: plotVal,
                provider: "manual"
            };
        }
    };
    document.getElementById("manual-series-title")?.addEventListener("input", updateSelectedShowFromInputs);
    document.getElementById("manual-series-plot")?.addEventListener("input", updateSelectedShowFromInputs);

    const allSeasonsCb = document.getElementById("series-all-seasons");
    if (allSeasonsCb) {
        allSeasonsCb.addEventListener("change", (e) => {
            const seasonInput = document.getElementById("series-season-num");
            if (seasonInput) {
                if (e.target.checked) {
                    seasonInput.disabled = true;
                    seasonInput.style.opacity = "0.5";
                } else {
                    seasonInput.disabled = false;
                    seasonInput.style.opacity = "1";
                }
            }
            fetchEpisodes();
        });
    }
    
    // Movie searches & loads
    document.getElementById("btn-search-movie").addEventListener("click", searchMovie);
    document.getElementById("movie-search-query").addEventListener("keypress", (e) => {
        if (e.key === "Enter") searchMovie();
    });
    document.getElementById("btn-execute-movie-process").addEventListener("click", executeMovieWorkflow);
    
    // YouTube Downloader
    document.getElementById("btn-analyse-yt-link").addEventListener("click", analyseYtLink);
    document.getElementById("yt-url").addEventListener("keypress", (e) => {
        if (e.key === "Enter") analyseYtLink();
    });
    
    document.getElementById("yt-meta-mode").addEventListener("change", toggleYtMetaSection);
    
    document.getElementById("btn-search-yt-movie").addEventListener("click", searchYtMovie);
    document.getElementById("yt-movie-search-query").addEventListener("keypress", (e) => {
        if (e.key === "Enter") searchYtMovie();
    });
    
    document.getElementById("btn-search-yt-series").addEventListener("click", searchYtSeries);
    document.getElementById("yt-series-search-query").addEventListener("keypress", (e) => {
        if (e.key === "Enter") searchYtSeries();
    });
    
    document.getElementById("yt-open-losslesscut").addEventListener("change", (e) => {
        const panel = document.getElementById("yt-custom-trim-panel");
        if (e.target.checked) {
            panel.classList.add("hidden");
        } else {
            panel.classList.remove("hidden");
        }
    });
    
    document.getElementById("btn-yt-reset").addEventListener("click", resetYtDownload);
    document.getElementById("btn-execute-yt-pipeline").addEventListener("click", startYtPipeline);
    
    document.getElementById("btn-yt-cut-done").addEventListener("click", markYtCutDone);
    document.getElementById("btn-yt-finalize-mapping").addEventListener("click", finalizeYtMapping);

    // YouTube subscriptions event listeners
    const btnAddAbo = document.getElementById("btn-add-abo");
    if (btnAddAbo) {
        btnAddAbo.addEventListener("click", addSubscription);
    }
    const btnCheckAllAbos = document.getElementById("btn-check-all-abos");
    if (btnCheckAllAbos) {
        btnCheckAllAbos.addEventListener("click", checkAllSubscriptions);
    }
    const urlAboInput = document.getElementById("abo-url");
    if (urlAboInput) {
        urlAboInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") addSubscription();
        });
    }

    
    // Tools Tab
    document.getElementById("tool-btn-pull-files")?.addEventListener("click", () => {
        openToolRunnerModal("tool_pull_files", "Dateien hochziehen", "Löst alle Unterordner im gewählten Verzeichnis auf und zieht alle Mediendateien hoch.");
    });
    document.getElementById("tool-btn-clean")?.addEventListener("click", () => {
        openToolRunnerModal("tool_clean", "Ordner bereinigen", "Entfernt leere Ordner und unerwünschte Junk-Dateien (z.B. txt, url, exe, ds_store, nfo, jpg, png).");
    });
    document.getElementById("tool-btn-paths-clean")?.addEventListener("click", openPathsCleanModal);
    
    // Modal-Steuerung für Medienpfade bereinigen
    document.getElementById("btn-paths-clean-close").addEventListener("click", closePathsCleanModal);
    document.getElementById("btn-paths-clean-select-cancel").addEventListener("click", closePathsCleanModal);
    document.getElementById("btn-paths-clean-preview-cancel").addEventListener("click", closePathsCleanModal);
    document.getElementById("btn-paths-clean-back").addEventListener("click", backToPathsCleanSelect);
    document.getElementById("btn-paths-clean-scan").addEventListener("click", runPathsCleanScan);
    document.getElementById("btn-paths-clean-execute").addEventListener("click", executePathsClean);
    
    // Schnellauswahl
    document.getElementById("btn-paths-clean-select-all").addEventListener("click", () => {
        document.querySelectorAll(".paths-clean-cb-item").forEach(cb => cb.checked = true);
    });
    document.getElementById("btn-paths-clean-select-none").addEventListener("click", () => {
        document.querySelectorAll(".paths-clean-cb-item").forEach(cb => cb.checked = false);
    });
    document.getElementById("btn-paths-clean-select-junk").addEventListener("click", () => {
        document.querySelectorAll(".paths-clean-cb-item").forEach(cb => {
            cb.checked = cb.dataset.junk === "true";
        });
    });

    document.getElementById("tool-btn-convert")?.addEventListener("click", () => {
        openToolRunnerModal("tool_batch_convert", "H.265 Batch-Konvertierung", "Videos im gewählten Verzeichnis in das platzsparende H.265 (HEVC) Format konvertieren.", true);
    });
    
    document.getElementById("tool-btn-nfo-agent")?.addEventListener("click", () => {
        openToolRunnerModal("tool_nfo_agent", "NFO Agent", "Generiert NFO-Metadaten für alle Episoden/Filme im gewählten Ordner anhand der TMDb/TVDb IDs.");
    });
    document.getElementById("tool-btn-nfo-batch")?.addEventListener("click", () => {
        const fskEl = document.getElementById("tool-fsk-value");
        const fsk = fskEl ? fskEl.value : "6";
        runToolGeneric("tool_nfo_batch_fsk", `Passe FSK auf ${fsk} an...`, { fsk: parseInt(fsk, 10) });
    });
    document.getElementById("tool-btn-manual-sync")?.addEventListener("click", () => {
        openToolRunnerModal("tool_manual_sync", "Speicherziel-Syncing", "Kopiert den gewählten Ordner auf das NAS-Speicherziel und optional in die pCloud.");
    });

    document.getElementById("tool-btn-pcloud-sync")?.addEventListener("click", () => {
        openToolRunnerModal("tool_pcloud_sync", "Reiner pCloud Sync", "Kopiert den gewählten Ordner in den Cloud-Ordner der pCloud.");
    });
    
    document.getElementById("tool-btn-profiles")?.addEventListener("click", openProfilesModal);
    document.getElementById("close-modal-profiles")?.addEventListener("click", () => {
        document.getElementById("modal-profiles").classList.remove("active");
    });

    // Modal-Tool-Runner Events
    document.getElementById("btn-browse-tool-modal-path")?.addEventListener("click", async () => {
        try {
            const response = await fetch("/api/browse-folder");
            const data = await response.json();
            if (data.status === "ok" && data.path) {
                document.getElementById("tool-modal-target-path").value = data.path;
            }
        } catch (e) {
            console.error("Fehler beim Browsen im Modal:", e);
        }
    });
    
    document.getElementById("btn-tool-modal-shortcut-inbox")?.addEventListener("click", () => {
        if (currentSettings && currentSettings.inbox_dir) {
            document.getElementById("tool-modal-target-path").value = currentSettings.inbox_dir;
        }
    });
    
    document.getElementById("btn-tool-modal-shortcut-outbox")?.addEventListener("click", () => {
        if (currentSettings && currentSettings.outbox_dir) {
            document.getElementById("tool-modal-target-path").value = currentSettings.outbox_dir;
        }
    });
    
    const closeToolRunnerModal = () => {
        document.getElementById("modal-tool-runner").classList.remove("active");
    };
    document.getElementById("btn-tool-modal-cancel")?.addEventListener("click", closeToolRunnerModal);
    document.getElementById("close-modal-tool-runner")?.addEventListener("click", closeToolRunnerModal);
    
    document.getElementById("btn-tool-modal-execute")?.addEventListener("click", async () => {
        const path = document.getElementById("tool-modal-target-path").value.trim();
        if (!path) {
            alert("⚠️ Bitte wähle zuerst einen Zielordner-Pfad aus!");
            return;
        }
        if (activeProjectsProcessing && activeProjectsProcessing.has(path)) {
            alert("⚠️ Dieses Projekt wird bereits verarbeitet oder befindet sich in der Warteschlange!");
            return;
        }
        closeToolRunnerModal();
        
        const toolType = window.currentActiveTool;
        if (toolType === "tool_pull_files") {
            expandConsole();
            appendConsoleLog("[System]: Verschiebe Dateien aus Unterordnern nach oben...");
            try {
                const res = await fetch("/api/process", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ media_type: "tool_pull_files", project_name: path })
                });
                if (res.ok) connectLogStream();
                else appendConsoleLog(`[System]: ❌ Serverfehler bei der Ausführung.`);
            } catch(e) {
                appendConsoleLog(`[System]: ❌ Fehler: ${e.message}`);
            }
        } else if (toolType === "tool_batch_convert") {
            const slider = document.getElementById("tool-modal-quality-slider");
            const quality = slider ? parseInt(slider.value, 10) : 60;
            expandConsole();
            appendConsoleLog("[System]: Starte Batch-H.265-Konvertierung...");
            try {
                const res = await fetch("/api/process", {
                     method: "POST",
                     headers: { "Content-Type": "application/json" },
                     body: JSON.stringify({ media_type: "tool_batch_convert", project_name: path, quality: quality })
                });
                if (res.ok) connectLogStream();
                else appendConsoleLog(`[System]: ❌ Serverfehler bei der Ausführung.`);
            } catch(e) {
                appendConsoleLog(`[System]: ❌ Fehler: ${e.message}`);
            }
        } else if (toolType === "tool_nfo_agent") {
            expandConsole();
            appendConsoleLog("[System]: Starte NFO Agent...");
            try {
                const res = await fetch("/api/process", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ media_type: "tool_nfo_agent", project_name: path })
                });
                if (res.ok) connectLogStream();
                else appendConsoleLog(`[System]: ❌ Serverfehler bei der Ausführung.`);
            } catch(e) {
                appendConsoleLog(`[System]: ❌ Fehler: ${e.message}`);
            }
        } else if (toolType === "tool_clean") {
            runToolClean(path);
        } else if (toolType === "tool_manual_sync") {
            if(!currentSettings.sync_categories || currentSettings.sync_categories.length === 0) {
                alert("Bitte lege zuerst Sync-Kategorien in den Einstellungen an."); return;
            }
            const promptText = "Wohin soll der Ordner auf dem NAS kopiert werden?\n\n" + 
                               currentSettings.sync_categories.map(c => `${c.id} = ${c.name}`).join("\n") + 
                               "\n\nZiel wählen:";
            const dest = prompt(promptText, currentSettings.sync_categories[0].id);
            
            const category = currentSettings.sync_categories.find(c => String(c.id) === String(dest));
            if(!category) return;
            
            const nasRoot = currentSettings.nas_root || "";
            const destPath = nasRoot ? `${nasRoot}${category.nas_sub}` : category.nas_sub;
            
            const doPcloud = confirm("Soll das Projekt zusätzlich auch in die pCloud hochgeladen werden?");
            expandConsole();
            appendConsoleLog("[System]: Starte NAS Sync...");
            try {
                const res = await fetch("/api/process", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        media_type: "tool_manual_sync",
                        project_name: path,
                        destination: destPath,
                        copy_to_pcloud: doPcloud
                    })
                });
                if (res.ok) connectLogStream();
            } catch(e) {
                appendConsoleLog(`[System]: ❌ Fehler: ${e.message}`);
            }
        } else if (toolType === "tool_pcloud_sync") {
            if(!currentSettings.sync_categories || currentSettings.sync_categories.length === 0) {
                alert("Bitte lege zuerst Sync-Kategorien in den Einstellungen an."); return;
            }
            const promptText = "In welchen Cloud-Ordner soll kopiert werden?\n\n" + 
                               currentSettings.sync_categories.map(c => `${c.id} = ${c.name}`).join("\n") + 
                               "\n\nZiel wählen:";
            const dest = prompt(promptText, currentSettings.sync_categories[0].id);
            
            const category = currentSettings.sync_categories.find(c => String(c.id) === String(dest));
            if(!category) return;
            
            expandConsole();
            appendConsoleLog("[System]: Starte reinen pCloud Sync...");
            try {
                const res = await fetch("/api/process", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        media_type: "tool_pcloud_sync",
                        project_name: path,
                        destination: category.nas_sub
                    })
                });
                if (res.ok) connectLogStream();
            } catch(e) {
                appendConsoleLog(`[System]: ❌ Fehler: ${e.message}`);
            }
        }
    });

    setupDestinationToggles();
    
    // Re-trigger auto-matching if destination is changed
    document.getElementById("series-nas-destination")?.addEventListener("change", () => {
        if (window.isProgrammaticCategoryChange) return;
        const showName = selectedShow ? selectedShow.name : (currentProject ? currentProject.replace(/\([0-9]{4}\)/g, "").replace(/_/g, " ").trim() : "");
        if (showName) {
            autoMatchNasFolder("series-nas-folder-override", "series-nas-destination", showName);
        }
    });
    
    document.getElementById("yt-nas-destination")?.addEventListener("change", () => {
        if (window.isProgrammaticCategoryChange) return;
        if (ytSelectedShow && ytSelectedShow.name) {
            autoMatchNasFolder("yt-series-nas-folder-override", "yt-nas-destination", ytSelectedShow.name);
        }
    });

    // Welcome Dashboard Hero/Card Listeners
    // (Die frühere "Inbox & Projekte"-Kachel wurde durch die Smart Inbox ersetzt.)

    const cardHeroAbos = document.getElementById("card-hero-abos");
    if (cardHeroAbos) {
        cardHeroAbos.addEventListener("click", () => {
            if (typeof window.openYoutubeAbosPage === "function") {
                window.openYoutubeAbosPage();
            }
        });
    }

    const cardHeroStats = document.getElementById("card-hero-stats");
    if (cardHeroStats) {
        cardHeroStats.addEventListener("click", () => {
            const navDashboard = document.getElementById("nav-dashboard");
            if (navDashboard) navDashboard.click();
        });
    }

    const btnHeroYtGo = document.getElementById("btn-hero-yt-go");
    if (btnHeroYtGo) {
        btnHeroYtGo.addEventListener("click", handleHeroYtDownload);
    }
    const inputHeroYtUrl = document.getElementById("hero-yt-url");
    if (inputHeroYtUrl) {
        inputHeroYtUrl.addEventListener("keypress", (e) => {
            if (e.key === "Enter") handleHeroYtDownload();
        });
    }
    
    // Conversion Intelligence Event Listeners
    const seriesIsAnime = document.getElementById("series-is-anime");
    if (seriesIsAnime) {
        seriesIsAnime.addEventListener("change", triggerQualityHintUpdates);
    }
    const movieNasDest = document.getElementById("movie-nas-destination");
    if (movieNasDest) {
        movieNasDest.addEventListener("change", triggerQualityHintUpdates);
    }
    const seriesNasDest = document.getElementById("series-nas-destination");
    if (seriesNasDest) {
        seriesNasDest.addEventListener("change", triggerQualityHintUpdates);
    }
}

// ==========================================================================
// SETTINGS DASHBOARD LOGIC
// ==========================================================================
let currentSettings = { import_sources: [] };
let conversionRecommendations = null;

async function checkDependencies(force = false) {
    const listContainer = document.getElementById("dependency-status-list");
    if (!listContainer) return;

    if (force) {
        listContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: var(--text-muted);">
            <span style="display: inline-block; animation: spin 1s linear infinite; margin-right: 8px;">🔄</span> Abhängigkeiten werden geprüft...
        </div>`;
    }

    try {
        const response = await fetch(`/api/check-dependencies?force=${force}`);
        if (response.ok) {
            const data = await response.json();
            renderDependencyStatus(data);
        } else {
            listContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: var(--danger);">
                Fehler beim Abrufen des Status der Abhängigkeiten.
            </div>`;
        }
    } catch (e) {
        console.error("Error checking dependencies:", e);
        listContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: var(--danger);">
            Verbindungsfehler: ${e.message}
        </div>`;
    }
}

function renderDependencyStatus(deps) {
    const listContainer = document.getElementById("dependency-status-list");
    if (!listContainer) return;

    listContainer.innerHTML = "";
    
    const statusLabels = {
        "missing": "Nicht installiert",
        "installed": "Bereit",
        "up_to_date": "Aktuell",
        "update_available": "Update verfügbar",
        "unknown": "Unbekannt"
    };

    const missingDeps = [];

    for (const [name, info] of Object.entries(deps)) {
        const card = document.createElement("div");
        card.className = `dep-card status-${info.status}`;

        const label = statusLabels[info.status] || info.status;

        if (info.status === "missing") {
            missingDeps.push(name);
        }

        let versionLines = "";
        if (info.status === "missing") {
            versionLines = `
                <div class="dep-version-label">
                    <span>Status:</span>
                    <span class="dep-version-val" style="color: var(--danger);">Fehlt</span>
                </div>
            `;
        } else {
            versionLines = `
                <div class="dep-version-label">
                    <span>Installiert:</span>
                    <span class="dep-version-val">${info.installed_version || "N/A"}</span>
                </div>
            `;
            if (info.latest_version) {
                versionLines += `
                    <div class="dep-version-label">
                        <span>Verfügbar:</span>
                        <span class="dep-version-val" style="color: ${info.status === 'update_available' ? 'var(--warning)' : 'var(--text-muted)'};">${info.latest_version}</span>
                    </div>
                `;
            }
        }

        card.innerHTML = `
            <div class="dep-header">
                <span class="dep-name">${name}</span>
                <span class="dep-badge badge-${info.status}">${label}</span>
            </div>
            <div class="dep-version-info">
                ${versionLines}
            </div>
        `;
        listContainer.appendChild(card);
    }

    const sfBadge = document.getElementById("streamfab-badge");
    if (missingDeps.length > 0 && sfBadge && sfBadge.classList.contains("neutral")) {
        const heroSfBadge = document.getElementById("hero-streamfab-badge");
        if (heroSfBadge) {
            heroSfBadge.textContent = `${missingDeps.length} fehlt`;
            heroSfBadge.className = "status-badge error";
        }
    }
}

async function loadDashboard() {
    const tableBody = document.getElementById("dashboard-history-tbody");
    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding: 30px;"><div class="loading-spinner"></div> Letzte Statistiken werden geladen...</td></tr>';
    }

    try {
        const response = await fetch("/api/stats");
        if (!response.ok) {
            throw new Error(`Server antwortete mit Code ${response.status}`);
        }
        const data = await response.json();

        // Helper to format bytes
        const formatBytes = (bytes, decimals = 2) => {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        };

        // 1. NAS Storage Info
        const circle = document.getElementById("nas-usage-circle");
        const percentText = document.getElementById("nas-usage-percent-text");
        const detailText = document.getElementById("nas-usage-detail-text");
        const pathText = document.getElementById("nas-usage-path-text");

        // Label aufs aktive Speicherziel umstellen (NAS, Cloud, ... – je nach Fallback)
        const storageLabel = document.getElementById("dashboard-storage-label");
        if (storageLabel) storageLabel.textContent = (data.nas.name || "Speicher") + " Speicherbelegung";

        if (data.nas.available && data.nas.usage_unreliable) {
            // SMB-Netzlaufwerk: Belegung nicht zuverlässig messbar -> nur freien Platz zeigen
            if (circle) {
                circle.style.strokeDashoffset = 364.4;
                circle.classList.remove("warning", "danger");
            }
            if (percentText) percentText.textContent = "–";
            if (detailText) {
                detailText.innerHTML = `${formatBytes(data.nas.free)} frei<br><span style="color:var(--text-muted); font-size:11px;">(Belegung bei Netzlaufwerk nicht ermittelbar)</span>`;
            }
            if (pathText) pathText.textContent = data.nas.path;
        } else if (data.nas.available) {
            const pct = data.nas.used_percent || 0;
            // stroke dasharray is 364.4 (for radius 58, 2 * Math.PI * 58 = 364.42)
            const offset = 364.4 - (364.4 * pct / 100);
            if (circle) {
                circle.style.strokeDashoffset = offset;
                circle.classList.remove("warning", "danger");
                if (pct >= 95) {
                    circle.classList.add("danger");
                } else if (pct >= 85) {
                    circle.classList.add("warning");
                }
            }
            if (percentText) percentText.textContent = pct.toFixed(1) + "%";
            if (detailText) {
                detailText.innerHTML = `${formatBytes(data.nas.used)} von ${formatBytes(data.nas.total)} belegt<br><span style="color:var(--text-muted); font-size:11px;">(${formatBytes(data.nas.free)} frei)</span>`;
            }
            if (pathText) pathText.textContent = data.nas.path;
        } else {
            if (circle) circle.style.strokeDashoffset = 364.4;
            if (percentText) percentText.textContent = "N/A";
            if (detailText) detailText.innerHTML = `<span class="text-danger">${data.nas.error || 'NAS nicht erreichbar'}</span>`;
            if (pathText) pathText.textContent = data.nas.path;
        }

        // 2. Savings Info
        const savedSpaceVal = document.getElementById("stats-saved-space");
        const savedPercentVal = document.getElementById("stats-saved-percent");
        const sizeInVal = document.getElementById("stats-size-in");
        const sizeOutVal = document.getElementById("stats-size-out");
        const savingsBar = document.getElementById("stats-savings-bar");
        const totalFilesVal = document.getElementById("stats-total-files");

        if (savedSpaceVal) savedSpaceVal.textContent = formatBytes(data.stats.saved_bytes);
        if (savedPercentVal) savedPercentVal.textContent = data.stats.ratio_percent.toFixed(1) + "%";
        if (sizeInVal) sizeInVal.textContent = formatBytes(data.stats.size_in_total);
        if (sizeOutVal) sizeOutVal.textContent = formatBytes(data.stats.size_out_total);
        if (savingsBar) savingsBar.style.width = data.stats.ratio_percent.toFixed(1) + "%";
        if (totalFilesVal) totalFilesVal.textContent = data.stats.total_files;

        // 3. Ratio Info
        const averageRatioVal = document.getElementById("stats-average-ratio");
        const averageRatioPercentVal = document.getElementById("stats-average-ratio-percent");

        if (averageRatioVal) averageRatioVal.textContent = data.stats.average_ratio.toFixed(2) + "x";
        if (averageRatioPercentVal) averageRatioPercentVal.textContent = (data.stats.average_ratio * 100).toFixed(1) + "%";

        // 4. Bar Chart for the last 15 entries
        const barChartContainer = document.getElementById("dashboard-bar-chart");
        if (barChartContainer) {
            barChartContainer.innerHTML = "";
            const historySlice = data.history.slice(0, 15).reverse(); // show chronological order (left to right)
            
            if (historySlice.length === 0) {
                barChartContainer.innerHTML = '<div style="width: 100%; display:flex; align-items:center; justify-content:center; height:100%; color:var(--text-muted);">Keine Konvertierungsdaten für das Diagramm vorhanden.</div>';
            } else {
                const maxVal = Math.max(...historySlice.map(h => h.size_in), 1);
                
                historySlice.forEach((item, index) => {
                    const dateObj = new Date(item.timestamp * 1000);
                    const labelStr = dateObj.toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit"});
                    const timeStr = dateObj.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"});
                    
                    const percentSaved = Math.max(0, ((item.size_in - item.size_out) / item.size_in) * 100);
                    const formattedSaved = formatBytes(item.size_in - item.size_out);
                    
                    const heightBg = (item.size_in / maxVal) * 100;
                    const heightFill = (item.size_out / maxVal) * 100;

                    const col = document.createElement("div");
                    col.className = "bar-column";
                    
                    col.innerHTML = `
                        <div class="bar-wrapper">
                            <div class="bar-bg-est" style="height: ${heightBg.toFixed(1)}%;"></div>
                            <div class="bar-fill-actual" style="height: ${heightFill.toFixed(1)}%;"></div>
                        </div>
                        <div class="bar-tooltip">
                            <strong>${labelStr} ${timeStr}</strong><br>
                            Codec: ${item.codec} (Q ${item.quality})<br>
                            Größe vorher: ${formatBytes(item.size_in)}<br>
                            Größe nachher: ${formatBytes(item.size_out)}<br>
                            Ersparnis: <span style="color:var(--accent); font-weight:700;">-${formattedSaved} (-${percentSaved.toFixed(1)}%)</span>
                        </div>
                        <div class="bar-label" title="${labelStr}">${labelStr}</div>
                    `;
                    
                    barChartContainer.appendChild(col);
                });
            }
        }

        // 5. History Table
        if (tableBody) {
            tableBody.innerHTML = "";
            if (data.history.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center" style="padding: 30px; color: var(--text-muted);">Keine Verlaufsdaten vorhanden.</td></tr>';
            } else {
                data.history.forEach(item => {
                    const tr = document.createElement("tr");
                    
                    let dateStr = "-";
                    if (item.timestamp > 0) {
                        const d = new Date(item.timestamp * 1000);
                        dateStr = `${d.toLocaleDateString("de-DE")} ${d.toLocaleTimeString("de-DE", {hour: '2-digit', minute:'2-digit'})} Uhr`;
                    }
                    
                    const savedBytes = Math.max(0, item.size_in - item.size_out);
                    const savedPct = item.size_in > 0 ? ((savedBytes / item.size_in) * 100) : 0;
                    
                    tr.innerHTML = `
                        <td>${dateStr}</td>
                        <td><span class="badge" style="background:rgba(var(--primary-rgb), 0.15); color:var(--primary);">${item.codec.toUpperCase()} (Q:${item.quality})</span></td>
                        <td>${formatBytes(item.size_in)}</td>
                        <td>${formatBytes(item.size_out)}</td>
                        <td style="color: var(--accent); font-weight:600;">-${formatBytes(savedBytes)} (-${savedPct.toFixed(1)}%)</td>
                        <td>${item.ratio.toFixed(2)}x</td>
                    `;
                    tableBody.appendChild(tr);
                });
            }
        }

    } catch (error) {
        console.error("Error loading dashboard data:", error);
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger" style="padding: 30px;">Fehler beim Laden der Dashboard-Statistiken: ${error.message}</td></tr>`;
        }
    }
}

async function loadSettings() {
    try {
        const response = await fetch("/api/settings");
        if (response.ok) {
            currentSettings = await response.json();
            const inboxEl = document.getElementById("settings-inbox-dir");
            if (inboxEl) inboxEl.value = currentSettings.inbox_dir || "";
            const outboxEl = document.getElementById("settings-outbox-dir");
            if (outboxEl) outboxEl.value = currentSettings.outbox_dir || "";
            const nasRootEl = document.getElementById("settings-nas-root");
            if (nasRootEl) nasRootEl.value = currentSettings.nas_root || "";
            const pcloudDirEl = document.getElementById("settings-pcloud-dir");
            if (pcloudDirEl) pcloudDirEl.value = currentSettings.pcloud_dir || "";
            
            const checkDepUpdatesEl = document.getElementById("settings-check-dependency-updates");
            if (checkDepUpdatesEl) {
                checkDepUpdatesEl.checked = !!currentSettings.check_dependency_updates;
            }
            
            const setCheckbox = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.checked = !!val;
            };
            const setInputVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.value = val !== undefined ? val : "";
            };

            setCheckbox("settings-open-outbox-finder", currentSettings.open_outbox_finder);
            setCheckbox("settings-open-nas-finder", currentSettings.open_nas_finder);
            setCheckbox("settings-open-pcloud-finder", currentSettings.open_pcloud_finder);
            
            setCheckbox("settings-notify-macos", currentSettings.notify_macos);
            setCheckbox("settings-notify-telegram", currentSettings.notify_telegram);
            setInputVal("settings-telegram-token", currentSettings.telegram_token);
            setInputVal("settings-telegram-chat-id", currentSettings.telegram_chat_id);
            setCheckbox("settings-notify-whatsapp", currentSettings.notify_whatsapp);
            setInputVal("settings-whatsapp-apikey", currentSettings.whatsapp_apikey);
            setInputVal("settings-whatsapp-phone", currentSettings.whatsapp_phone);
            setInputVal("settings-tmdb-key", currentSettings.tmdb_api_key);
            setInputVal("settings-tvdb-key", currentSettings.tvdb_api_key);
            setInputVal("settings-notify-min-size", currentSettings.notify_min_size !== undefined ? currentSettings.notify_min_size : 10);
            setCheckbox("settings-notify-only-end", currentSettings.notify_only_end !== false); // default to true
            
            // Folder Monitor Settings
            setCheckbox("set-monitor-enabled", currentSettings.folder_monitor_enabled !== false); // default true
            setInputVal("set-monitor-inbox-gb", currentSettings.folder_monitor_inbox_threshold_gb !== undefined ? currentSettings.folder_monitor_inbox_threshold_gb : 50);
            setInputVal("set-monitor-outbox-gb", currentSettings.folder_monitor_outbox_threshold_gb !== undefined ? currentSettings.folder_monitor_outbox_threshold_gb : 50);
            setInputVal("set-monitor-interval", currentSettings.folder_monitor_interval_minutes !== undefined ? currentSettings.folder_monitor_interval_minutes : 30);
            
            setCheckbox("set-monitor-notify-macos", currentSettings.folder_monitor_notify_macos !== false); // default true
            setCheckbox("set-monitor-notify-telegram", !!currentSettings.folder_monitor_notify_telegram);
            setCheckbox("set-monitor-notify-whatsapp", !!currentSettings.folder_monitor_notify_whatsapp);

            setCheckbox("settings-show-jokes", currentSettings.show_jokes !== false); // default to true
            setCheckbox("settings-show-quote", currentSettings.show_quote !== false); // default to true
            setCheckbox("settings-smart-conversion-default", currentSettings.smart_conversion_default !== false); // default to true
            setCheckbox("settings-show-console", currentSettings.show_console || false);
            applyConsoleVisibility(currentSettings.show_console || false);
            
            let themeVal = currentSettings.app_theme || "deep-space";
            if (themeVal === "apple-silver") themeVal = "apple-black";
            setInputVal("settings-app-theme", themeVal);
            applyTheme(themeVal);

            setInputVal("settings-media-server", currentSettings.media_server || "");
            
            if (!currentSettings.import_sources) currentSettings.import_sources = [];
            if (!currentSettings.sync_categories) currentSettings.sync_categories = [];
            if (!currentSettings.local_download_folders) currentSettings.local_download_folders = [];
            if (!currentSettings.storage_targets) currentSettings.storage_targets = [];
            renderImportSources();
            renderLocalFolders();
            renderSyncCategories();
            renderStorageTargets();
            updateDestinationDropdowns();
            
            checkDependencies(false);
        }
    } catch (e) {
        console.error("Error loading settings:", e);
    }
}

function updateDestinationDropdowns() {
    const nasSelects = ["movie-nas-destination", "series-nas-destination", "yt-nas-destination", "abo-nas-destination", "yt-merge-nas-destination"];
    const pcloudSelects = ["movie-pcloud-destination", "series-pcloud-destination", "yt-pcloud-destination", "abo-pcloud-destination", "yt-merge-pcloud-destination"];
    const localSelects = ["yt-local-destination", "abo-local-destination", "yt-merge-local-destination"];
    
    nasSelects.forEach(selId => {
        const select = document.getElementById(selId);
        if (!select) return;
        
        const currentVal = select.value;
        select.innerHTML = "";
        
        currentSettings.sync_categories.forEach(cat => {
            const opt = document.createElement("option");
            opt.value = cat.id;
            opt.textContent = `${cat.name} (NAS: ${cat.nas_sub})`;
            select.appendChild(opt);
        });
        
        if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
            select.value = currentVal;
        } else {
            if (selId.includes("movie") && Array.from(select.options).some(o => o.value === "1")) {
                select.value = "1";
            } else if (selId.includes("series") && Array.from(select.options).some(o => o.value === "2")) {
                select.value = "2";
            }
        }
    });
    
    pcloudSelects.forEach(selId => {
        const select = document.getElementById(selId);
        if (!select) return;
        
        const currentVal = select.value;
        select.innerHTML = "";
        
        currentSettings.sync_categories.forEach(cat => {
            const opt = document.createElement("option");
            opt.value = cat.id;
            opt.textContent = `${cat.name} (pCloud: ${cat.pcloud_remote})`;
            select.appendChild(opt);
        });
        
        if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
            select.value = currentVal;
        } else {
            if (selId.includes("movie") && Array.from(select.options).some(o => o.value === "1")) {
                select.value = "1";
            } else if (selId.includes("series") && Array.from(select.options).some(o => o.value === "2")) {
                select.value = "2";
            }
        }
    });
    
    localSelects.forEach(selId => {
        const select = document.getElementById(selId);
        if (!select) return;
        
        const currentVal = select.value;
        select.innerHTML = "";
        
        // Built-in: Input-Ordner
        const inboxDir = currentSettings.inbox_dir || "~/Downloads/Medien Input";
        const optInbox = document.createElement("option");
        optInbox.value = "__inbox__";
        optInbox.textContent = `📥 Input-Ordner (${inboxDir})`;
        select.appendChild(optInbox);
        
        // Built-in: Output-Ordner (root)
        const outboxDir = currentSettings.outbox_dir || "~/Downloads/Medien Output";
        const optOutbox = document.createElement("option");
        optOutbox.value = "__outbox__";
        optOutbox.textContent = `📤 Output-Ordner (${outboxDir})`;
        select.appendChild(optOutbox);
        
        // Sync categories as local outbox subdirectories
        if (currentSettings.sync_categories && currentSettings.sync_categories.length > 0) {
            const optGroup = document.createElement("optgroup");
            optGroup.label = "Kategorien (Output-Unterordner)";
            currentSettings.sync_categories.forEach(cat => {
                const opt = document.createElement("option");
                opt.value = `__cat_${cat.id}`;
                opt.textContent = `${cat.name} (${outboxDir}${cat.nas_sub})`;
                optGroup.appendChild(opt);
            });
            select.appendChild(optGroup);
        }
        
        // Custom local folders from settings
        if (currentSettings.local_download_folders && currentSettings.local_download_folders.length > 0) {
            const optGroup = document.createElement("optgroup");
            optGroup.label = "Eigene Ordner";
            currentSettings.local_download_folders.forEach((folder, idx) => {
                if (!folder.path) return;
                const opt = document.createElement("option");
                opt.value = `__custom_${idx}`;
                opt.textContent = `📁 ${folder.name || 'Ordner'} (${folder.path})`;
                optGroup.appendChild(opt);
            });
            select.appendChild(optGroup);
        }
        
        if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
            select.value = currentVal;
        }
    });
}

function setupDestinationToggles() {
    const pairs = [
        { cb: "movie-option-copy-nas", container: "movie-nas-destination-container" },
        { cb: "movie-option-copy-pcloud", container: "movie-pcloud-destination-container" },
        { cb: "series-option-copy-nas", container: "series-nas-destination-container" },
        { cb: "series-option-copy-pcloud", container: "series-pcloud-destination-container" },
        { cb: "yt-option-copy-nas", container: "yt-nas-destination-container" },
        { cb: "yt-option-copy-pcloud", container: "yt-pcloud-destination-container" },
        { cb: "yt-option-copy-local", container: "yt-local-destination-container" },
        { cb: "abo-copy-nas", container: "abo-nas-destination-container" },
        { cb: "abo-copy-pcloud", container: "abo-pcloud-destination-container" },
        { cb: "abo-copy-local", container: "abo-local-destination-container" },
        { cb: "yt-merge-option-copy-nas", container: "yt-merge-nas-destination-container" },
        { cb: "yt-merge-option-copy-pcloud", container: "yt-merge-pcloud-destination-container" },
        { cb: "yt-merge-option-copy-local", container: "yt-merge-local-destination-container" }
    ];
    
    pairs.forEach(({ cb, container }) => {
        const checkbox = document.getElementById(cb);
        const cont = document.getElementById(container);
        if (checkbox && cont) {
            const updateVisibility = () => {
                if (checkbox.checked) {
                    cont.classList.remove("hidden");
                } else {
                    cont.classList.add("hidden");
                }
            };
            checkbox.addEventListener("change", updateVisibility);
            updateVisibility();
        }
    });
}

function renderStorageTargets() {
    const container = document.getElementById("settings-storage-targets-container");
    if (!container) return;
    container.innerHTML = "";
    
    if (!currentSettings.storage_targets) currentSettings.storage_targets = [];
    
    currentSettings.storage_targets.forEach((target, index) => {
        const card = document.createElement("div");
        card.className = "clean-group-container";
        card.style.marginBottom = "15px";
        card.style.padding = "15px";
        card.style.background = "rgba(255, 255, 255, 0.02)";
        card.style.border = "1px solid var(--border-glass)";
        card.style.borderRadius = "var(--radius-md)";
        card.style.position = "relative";
        
        // Title row with ID/Type and delete button
        const titleRow = document.createElement("div");
        titleRow.style.display = "flex";
        titleRow.style.justifyContent = "space-between";
        titleRow.style.alignItems = "center";
        titleRow.style.marginBottom = "12px";
        
        const titleText = document.createElement("h4");
        titleText.style.margin = "0";
        titleText.style.fontSize = "13px";
        titleText.style.color = "var(--accent)";
        titleText.style.textTransform = "uppercase";
        titleText.textContent = `Ziel: ${target.name || target.id}`;
        
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-danger btn-xs";
        deleteBtn.textContent = "❌ Ziel entfernen";
        deleteBtn.onclick = (e) => {
            e.preventDefault();
            if (confirm(`Möchtest du das Speicherziel "${target.name || target.id}" wirklich entfernen?`)) {
                currentSettings.storage_targets.splice(index, 1);
                renderStorageTargets();
            }
        };
        
        titleRow.appendChild(titleText);
        // Only allow deletion for custom targets (keep nas and pcloud)
        if (target.id !== "nas" && target.id !== "pcloud") {
            titleRow.appendChild(deleteBtn);
        }
        card.appendChild(titleRow);
        
        // Form layout grid
        const grid = document.createElement("div");
        grid.style.display = "grid";
        grid.style.gridTemplateColumns = "repeat(auto-fit, minmax(200px, 1fr))";
        grid.style.gap = "12px";
        grid.style.marginBottom = "10px";
        
        // Helper to create form controls
        const createField = (labelText, value, placeholder, onchange) => {
            const wrap = document.createElement("div");
            wrap.style.display = "flex";
            wrap.style.flexDirection = "column";
            wrap.style.gap = "4px";
            
            const label = document.createElement("label");
            label.style.fontSize = "11px";
            label.style.color = "var(--text-muted)";
            label.textContent = labelText;
            
            const input = document.createElement("input");
            input.type = "text";
            input.className = "form-select";
            input.style.padding = "8px 12px";
            input.style.fontSize = "12px";
            input.style.border = "1px solid var(--border-glass)";
            input.style.background = "var(--bg-surface)";
            input.style.color = "var(--text-main)";
            input.placeholder = placeholder;
            input.value = value || "";
            input.addEventListener("input", (e) => onchange(e.target.value));
            
            wrap.appendChild(label);
            wrap.appendChild(input);
            return { wrap, input };
        };
        
        // Name field
        const nameField = createField("Name des Speicherziels:", target.name, "z.B. NAS Filme", (val) => {
            target.name = val;
            titleText.textContent = `Ziel: ${val || target.id}`;
        });
        grid.appendChild(nameField.wrap);
        
        // ID field (locked for default ones, editable for custom ones)
        const idField = createField("Eindeutige ID (Schlüssel):", target.id, "z.B. nas_dokus", (val) => {
            target.id = val.toLowerCase().replace(/[^a-z0-9_]/g, "");
            idField.input.value = target.id;
        });
        if (target.id === "nas" || target.id === "pcloud") {
            idField.input.disabled = true;
            idField.input.style.opacity = "0.5";
            idField.input.title = "Standard-IDs können nicht umbenannt werden.";
        }
        grid.appendChild(idField.wrap);
        
        // Type select
        const typeWrap = document.createElement("div");
        typeWrap.style.display = "flex";
        typeWrap.style.flexDirection = "column";
        typeWrap.style.gap = "4px";
        const typeLabel = document.createElement("label");
        typeLabel.style.fontSize = "11px";
        typeLabel.style.color = "var(--text-muted)";
        typeLabel.textContent = "Typ des Speichers:";
        const typeSelect = document.createElement("select");
        typeSelect.className = "form-select";
        typeSelect.style.padding = "8px 12px";
        typeSelect.style.fontSize = "12px";
        typeSelect.style.border = "1px solid var(--border-glass)";
        typeSelect.style.background = "var(--bg-surface)";
        typeSelect.style.color = "var(--text-main)";
        typeSelect.innerHTML = `
            <option value="nas" ${target.type === "nas" ? "selected" : ""}>NAS (Netzwerkordner)</option>
            <option value="pcloud" ${target.type === "pcloud" ? "selected" : ""}>pCloud (Cloud)</option>
            <option value="cloud" ${target.type === "cloud" && target.id !== "pcloud" ? "selected" : ""}>Sonstige Cloud (rclone)</option>
        `;
        if (target.id === "nas" || target.id === "pcloud") {
            typeSelect.disabled = true;
            typeSelect.style.opacity = "0.5";
        }
        typeSelect.addEventListener("change", (e) => {
            target.type = e.target.value;
            renderStorageTargets(); // Re-render to show/hide SMB settings
        });
        typeWrap.appendChild(typeLabel);
        typeWrap.appendChild(typeSelect);
        grid.appendChild(typeWrap);
        
        // Enabled checkbox
        const enabledWrap = document.createElement("div");
        enabledWrap.style.display = "flex";
        enabledWrap.style.alignItems = "center";
        enabledWrap.style.gap = "8px";
        enabledWrap.style.marginTop = "15px";
        
        const enabledCheckbox = document.createElement("input");
        enabledCheckbox.type = "checkbox";
        enabledCheckbox.id = `target-enabled-${index}`;
        enabledCheckbox.checked = target.enabled !== false;
        enabledCheckbox.style.width = "16px";
        enabledCheckbox.style.height = "16px";
        enabledCheckbox.style.accentColor = "var(--accent)";
        enabledCheckbox.addEventListener("change", (e) => {
            target.enabled = e.target.checked;
        });
        
        const enabledLabel = document.createElement("label");
        enabledLabel.htmlFor = `target-enabled-${index}`;
        enabledLabel.style.fontSize = "12px";
        enabledLabel.style.cursor = "pointer";
        enabledLabel.textContent = "Aktiviert (für Synchronisierung nutzen)";
        
        enabledWrap.appendChild(enabledCheckbox);
        enabledWrap.appendChild(enabledLabel);
        grid.appendChild(enabledWrap);
        
        card.appendChild(grid);
        
        // Local path field with Browse button
        const pathLabel = document.createElement("label");
        pathLabel.style.fontSize = "11px";
        pathLabel.style.color = "var(--text-muted)";
        pathLabel.style.display = "block";
        pathLabel.style.marginBottom = "4px";
        pathLabel.textContent = "Lokal-Pfad (Wurzelverzeichnis auf dem Mac):";
        card.appendChild(pathLabel);
        
        const pathRow = document.createElement("div");
        pathRow.style.display = "flex";
        pathRow.style.gap = "8px";
        pathRow.style.marginBottom = "12px";
        
        const pathInput = document.createElement("input");
        pathInput.type = "text";
        pathInput.className = "form-select";
        pathInput.style.flex = "1";
        pathInput.style.padding = "8px 12px";
        pathInput.style.fontSize = "12px";
        pathInput.style.border = "1px solid var(--border-glass)";
        pathInput.style.background = "var(--bg-surface)";
        pathInput.style.color = "var(--text-main)";
        pathInput.placeholder = "z.B. /Volumes/Media oder /mnt/nas";
        pathInput.value = target.root_path || "";
        pathInput.addEventListener("input", (e) => {
            target.root_path = e.target.value;
        });
        
        const browseBtn = document.createElement("button");
        browseBtn.className = "btn btn-secondary btn-sm";
        browseBtn.textContent = "🔍";
        browseBtn.onclick = async (e) => {
            e.preventDefault();
            try {
                const response = await fetch("/api/browse-folder");
                const data = await response.json();
                if (data.path) {
                    pathInput.value = data.path;
                    target.root_path = data.path;
                }
            } catch (err) {
                console.error("Browse error:", err);
            }
        };
        
        pathRow.appendChild(pathInput);
        pathRow.appendChild(browseBtn);
        card.appendChild(pathRow);
        
        // rclone remote field
        const rcloneField = createField("rclone Remote Name (Optional für Cloud-Fallbacks):", target.rclone_remote, "z.B. pcloud: oder gdrive:", (val) => {
            target.rclone_remote = val;
        });
        rcloneField.wrap.style.marginBottom = "12px";
        card.appendChild(rcloneField.wrap);
        
        // If type is NAS, show SMB settings
        if (target.type === "nas") {
            const smbTitle = document.createElement("div");
            smbTitle.style.fontSize = "11px";
            smbTitle.style.fontWeight = "bold";
            smbTitle.style.color = "var(--accent)";
            smbTitle.style.marginTop = "15px";
            smbTitle.style.marginBottom = "8px";
            smbTitle.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
            smbTitle.style.paddingBottom = "4px";
            smbTitle.textContent = "🌐 SMB-Netzwerk-Mounting Details (nur NAS)";
            card.appendChild(smbTitle);
            
            const smbGrid = document.createElement("div");
            smbGrid.style.display = "grid";
            smbGrid.style.gridTemplateColumns = "repeat(auto-fit, minmax(150px, 1fr))";
            smbGrid.style.gap = "10px";
            
            const ipField = createField("Lokale NAS-IP:", target.nas_ip, "z.B. 192.168.2.208", (val) => {
                target.nas_ip = val;
            });
            const backupIpField = createField("Backup-/Tailscale-IP:", target.nas_ip_backup, "z.B. 100.74.187.125", (val) => {
                target.nas_ip_backup = val;
            });
            const hostnameField = createField("Finder-Servername:", target.nas_hostname, "z.B. ALEXNAS91", (val) => {
                target.nas_hostname = val;
            });
            const shareField = createField("SMB Share-Name:", target.nas_share, "z.B. share", (val) => {
                target.nas_share = val;
            });
            
            smbGrid.appendChild(ipField.wrap);
            smbGrid.appendChild(backupIpField.wrap);
            smbGrid.appendChild(hostnameField.wrap);
            smbGrid.appendChild(shareField.wrap);
            card.appendChild(smbGrid);
        }
        
        container.appendChild(card);
    });
}

function renderImportSources() {
    const container = document.getElementById("settings-import-sources-container");
    container.innerHTML = "";
    
    currentSettings.import_sources.forEach((source, index) => {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.gap = "10px";
        
        const input = document.createElement("input");
        input.type = "text";
        input.className = "form-select";
        input.style.flex = "1";
        input.style.padding = "10px 14px";
        input.style.borderRadius = "var(--radius-sm)";
        input.style.border = "1px solid var(--border-glass)";
        input.style.background = "var(--bg-surface)";
        input.style.color = "var(--text-main)";
        input.value = source;
        input.onchange = (e) => { currentSettings.import_sources[index] = e.target.value; };
        
        const browseBtn = document.createElement("button");
        browseBtn.className = "btn btn-secondary";
        browseBtn.textContent = "🔍";
        browseBtn.onclick = async () => {
            try {
                const response = await fetch("/api/browse-folder");
                const data = await response.json();
                if (data.path) {
                    input.value = data.path;
                    currentSettings.import_sources[index] = data.path;
                }
            } catch (e) { console.error("Browse error:", e); }
        };
        
        const removeBtn = document.createElement("button");
        removeBtn.className = "btn btn-danger";
        removeBtn.textContent = "❌";
        removeBtn.onclick = () => {
            currentSettings.import_sources.splice(index, 1);
            renderImportSources();
        };
        
        row.appendChild(input);
        row.appendChild(browseBtn);
        row.appendChild(removeBtn);
        container.appendChild(row);
    });
}

function renderLocalFolders() {
    const container = document.getElementById("settings-local-folders-container");
    if (!container) return;
    container.innerHTML = "";
    
    if (!currentSettings.local_download_folders) currentSettings.local_download_folders = [];
    
    currentSettings.local_download_folders.forEach((folder, index) => {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.gap = "10px";
        
        const nameInput = document.createElement("input");
        nameInput.type = "text";
        nameInput.className = "form-select";
        nameInput.style.width = "140px";
        nameInput.style.padding = "10px 14px";
        nameInput.style.borderRadius = "var(--radius-sm)";
        nameInput.style.border = "1px solid var(--border-glass)";
        nameInput.style.background = "var(--bg-surface)";
        nameInput.style.color = "var(--text-main)";
        nameInput.placeholder = "Name";
        nameInput.value = folder.name || "";
        nameInput.onchange = (e) => { currentSettings.local_download_folders[index].name = e.target.value; };
        
        const pathInput = document.createElement("input");
        pathInput.type = "text";
        pathInput.className = "form-select";
        pathInput.style.flex = "1";
        pathInput.style.padding = "10px 14px";
        pathInput.style.borderRadius = "var(--radius-sm)";
        pathInput.style.border = "1px solid var(--border-glass)";
        pathInput.style.background = "var(--bg-surface)";
        pathInput.style.color = "var(--text-main)";
        pathInput.placeholder = "Pfad (z.B. /Users/alex/Videos)";
        pathInput.value = folder.path || "";
        pathInput.onchange = (e) => { currentSettings.local_download_folders[index].path = e.target.value; };
        
        const browseBtn = document.createElement("button");
        browseBtn.className = "btn btn-secondary";
        browseBtn.textContent = "🔍";
        browseBtn.onclick = async () => {
            try {
                const response = await fetch("/api/browse-folder");
                const data = await response.json();
                if (data.path) {
                    pathInput.value = data.path;
                    currentSettings.local_download_folders[index].path = data.path;
                    if (!nameInput.value) {
                        const parts = data.path.split("/");
                        nameInput.value = parts[parts.length - 1] || parts[parts.length - 2] || "Ordner";
                        currentSettings.local_download_folders[index].name = nameInput.value;
                    }
                }
            } catch (e) { console.error("Browse error:", e); }
        };
        
        const removeBtn = document.createElement("button");
        removeBtn.className = "btn btn-danger";
        removeBtn.textContent = "❌";
        removeBtn.onclick = () => {
            currentSettings.local_download_folders.splice(index, 1);
            renderLocalFolders();
        };
        
        row.appendChild(nameInput);
        row.appendChild(pathInput);
        row.appendChild(browseBtn);
        row.appendChild(removeBtn);
        container.appendChild(row);
    });
}

function renderSyncCategories() {
    const container = document.getElementById("settings-sync-categories-container");
    if(!container) return;
    container.innerHTML = "";
    
    currentSettings.sync_categories.forEach((cat, index) => {
        const row = document.createElement("div");
        row.style.display = "flex";
        row.style.gap = "8px";
        
        const createInput = (val, placeholder, width, field) => {
            const input = document.createElement("input");
            input.type = "text";
            input.className = "form-select";
            input.style.flex = width;
            input.style.padding = "10px";
            input.style.borderRadius = "var(--radius-sm)";
            input.style.border = "1px solid var(--border-glass)";
            input.style.background = "var(--bg-surface)";
            input.style.color = "var(--text-main)";
            input.placeholder = placeholder;
            input.value = val;
            input.onchange = (e) => { currentSettings.sync_categories[index][field] = e.target.value; };
            return input;
        };
        
        row.appendChild(createInput(cat.id, "ID (z.B. 1)", "0.5", "id"));
        row.appendChild(createInput(cat.name, "Name", "1", "name"));
        
        // NAS Sub-path field with browse button
        const nasWrapper = document.createElement("div");
        nasWrapper.style.flex = "1";
        nasWrapper.style.display = "flex";
        nasWrapper.style.gap = "5px";
        
        const nasInput = createInput(cat.nas_sub, "NAS (/Filme)", "1", "nas_sub");
        nasWrapper.appendChild(nasInput);
        
        const browseBtn = document.createElement("button");
        browseBtn.className = "btn btn-secondary";
        browseBtn.textContent = "🔍";
        browseBtn.title = "Ordner auswählen";
        browseBtn.style.padding = "5px 10px";
        browseBtn.onclick = async () => {
            try {
                const response = await fetch("/api/browse-folder");
                const data = await response.json();
                if (data.path) {
                    const nasRoot = currentSettings.nas_root || "";
                    let subPath = data.path;
                    if (nasRoot && subPath.startsWith(nasRoot)) {
                        subPath = subPath.substring(nasRoot.length);
                        if (!subPath.startsWith("/")) subPath = "/" + subPath;
                    }
                    nasInput.value = subPath;
                    currentSettings.sync_categories[index].nas_sub = subPath;
                }
            } catch (e) { console.error("Browse error:", e); }
        };
        nasWrapper.appendChild(browseBtn);
        row.appendChild(nasWrapper);
        
        // pCloud Sub-path field with browse button
        const pcloudWrapper = document.createElement("div");
        pcloudWrapper.style.flex = "1.5";
        pcloudWrapper.style.display = "flex";
        pcloudWrapper.style.gap = "5px";
        
        const pcloudInput = createInput(cat.pcloud_remote, "pCloud (pcloud:03_Filme)", "1", "pcloud_remote");
        pcloudWrapper.appendChild(pcloudInput);
        
        const browsePcloudBtn = document.createElement("button");
        browsePcloudBtn.className = "btn btn-secondary";
        browsePcloudBtn.textContent = "🔍";
        browsePcloudBtn.title = "pCloud-Ordner auswählen";
        browsePcloudBtn.style.padding = "5px 10px";
        browsePcloudBtn.onclick = async () => {
            try {
                const response = await fetch("/api/browse-folder");
                const data = await response.json();
                if (data.path) {
                    const pcloudRoot = currentSettings.pcloud_dir || "";
                    let subPath = data.path;
                    if (pcloudRoot && subPath.startsWith(pcloudRoot)) {
                        subPath = subPath.substring(pcloudRoot.length);
                        if (subPath.startsWith("/")) subPath = subPath.substring(1);
                        subPath = "pcloud:" + subPath;
                    }
                    pcloudInput.value = subPath;
                    currentSettings.sync_categories[index].pcloud_remote = subPath;
                }
            } catch (e) { console.error("Browse error:", e); }
        };
        pcloudWrapper.appendChild(browsePcloudBtn);
        row.appendChild(pcloudWrapper);
        
        const removeBtn = document.createElement("button");
        removeBtn.className = "btn btn-danger";
        removeBtn.textContent = "❌";
        removeBtn.onclick = () => {
            currentSettings.sync_categories.splice(index, 1);
            renderSyncCategories();
        };
        
        row.appendChild(removeBtn);
        container.appendChild(row);
    });
}

// Bind Settings Events
document.addEventListener("DOMContentLoaded", () => {
    const btnSaveSettings = document.getElementById("btn-save-settings");
    if(btnSaveSettings) {
        btnSaveSettings.addEventListener("click", async () => {
            const checkDepUpdatesEl = document.getElementById("settings-check-dependency-updates");
            const payload = {
                inbox_dir: document.getElementById("settings-inbox-dir")?.value || "",
                outbox_dir: document.getElementById("settings-outbox-dir")?.value || "",
                nas_root: document.getElementById("settings-nas-root")?.value || "",
                pcloud_dir: document.getElementById("settings-pcloud-dir")?.value || "",
                check_dependency_updates: checkDepUpdatesEl ? checkDepUpdatesEl.checked : false,
                
                open_outbox_finder: document.getElementById("settings-open-outbox-finder")?.checked || false,
                open_nas_finder: document.getElementById("settings-open-nas-finder")?.checked || false,
                open_pcloud_finder: document.getElementById("settings-open-pcloud-finder")?.checked || false,
                
                notify_macos: document.getElementById("settings-notify-macos")?.checked || false,
                notify_telegram: document.getElementById("settings-notify-telegram")?.checked || false,
                telegram_token: document.getElementById("settings-telegram-token")?.value || "",
                telegram_chat_id: document.getElementById("settings-telegram-chat-id")?.value || "",
                notify_whatsapp: document.getElementById("settings-notify-whatsapp")?.checked || false,
                whatsapp_apikey: document.getElementById("settings-whatsapp-apikey")?.value || "",
                whatsapp_phone: document.getElementById("settings-whatsapp-phone")?.value || "",
                tmdb_api_key: document.getElementById("settings-tmdb-key")?.value || "",
                tvdb_api_key: document.getElementById("settings-tvdb-key")?.value || "",
                notify_min_size: parseInt(document.getElementById("settings-notify-min-size")?.value, 10) || 0,
                notify_only_end: document.getElementById("settings-notify-only-end")?.checked || false,

                show_jokes: document.getElementById("settings-show-jokes")?.checked || false,
                show_quote: document.getElementById("settings-show-quote")?.checked || false,
                smart_conversion_default: document.getElementById("settings-smart-conversion-default")?.checked || false,
                show_console: document.getElementById("settings-show-console")?.checked || false,
                app_theme: document.getElementById("settings-app-theme")?.value || "deep-space",
                media_server: document.getElementById("settings-media-server")?.value || "",
                
                folder_monitor_enabled: document.getElementById("set-monitor-enabled")?.checked || false,
                folder_monitor_inbox_threshold_gb: parseFloat(document.getElementById("set-monitor-inbox-gb")?.value) || 50.0,
                folder_monitor_outbox_threshold_gb: parseFloat(document.getElementById("set-monitor-outbox-gb")?.value) || 50.0,
                folder_monitor_interval_minutes: parseInt(document.getElementById("set-monitor-interval")?.value, 10) || 30,
                
                folder_monitor_notify_macos: document.getElementById("set-monitor-notify-macos")?.checked || false,
                folder_monitor_notify_telegram: document.getElementById("set-monitor-notify-telegram")?.checked || false,
                folder_monitor_notify_whatsapp: document.getElementById("set-monitor-notify-whatsapp")?.checked || false,
                
                import_sources: currentSettings.import_sources.filter(s => s.trim() !== ""),
                sync_categories: currentSettings.sync_categories.filter(c => c.id.trim() !== "" && c.name.trim() !== ""),
                local_download_folders: (currentSettings.local_download_folders || []).filter(f => f.path && f.path.trim() !== ""),
                storage_targets: (currentSettings.storage_targets || []).filter(t => t.id && t.id.trim() !== "")
            };
            
            try {
                const response = await fetch("/api/settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    alert("Einstellungen erfolgreich gespeichert!");
                    loadSettings(); // Reload
                } else {
                    alert("Fehler beim Speichern der Einstellungen.");
                }
            } catch (e) {
                alert("Verbindungsfehler: " + e);
            }
        });
    }

    const btnRestartServer = document.getElementById("btn-restart-server");
    if (btnRestartServer) {
        btnRestartServer.addEventListener("click", async () => {
            if (!confirm("Bist du sicher, dass du den Server neu starten möchtest?")) {
                return;
            }
            
            btnRestartServer.disabled = true;
            btnRestartServer.textContent = "⌛ Starte neu...";
            
            try {
                const response = await fetch("/api/system/restart", {
                    method: "POST"
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.status === "busy") {
                        alert("Abgebrochen: " + data.message);
                        btnRestartServer.disabled = false;
                        btnRestartServer.textContent = "🔄 Server neu starten";
                    } else if (data.status === "restarting") {
                        appendConsoleLog("[System]: Server startet neu... Warte auf Neustart.");
                        expandConsole();
                        
                        const pollInterval = setInterval(async () => {
                            try {
                                const res = await fetch("/api/status");
                                if (res.ok) {
                                    clearInterval(pollInterval);
                                    appendConsoleLog("[System]: Server wieder online. Lade Seite neu...");
                                    setTimeout(() => {
                                        location.reload();
                                    }, 500);
                                }
                            } catch (err) {
                                // Keep polling
                            }
                        }, 1000);
                    }
                } else {
                    alert("Fehler beim Senden des Neustart-Befehls.");
                    btnRestartServer.disabled = false;
                    btnRestartServer.textContent = "🔄 Server neu starten";
                }
            } catch (e) {
                appendConsoleLog("[System]: Verbindung getrennt. Warte auf Server...");
                const pollInterval = setInterval(async () => {
                    try {
                        const res = await fetch("/api/status");
                        if (res.ok) {
                            clearInterval(pollInterval);
                            appendConsoleLog("[System]: Server wieder online. Lade Seite neu...");
                            setTimeout(() => {
                                location.reload();
                            }, 500);
                        }
                    } catch (err) {
                        // Keep polling
                    }
                }, 1000);
            }
        });
    }

    const btnCheckDeps = document.getElementById("btn-check-dependencies");
    if (btnCheckDeps) {
        btnCheckDeps.addEventListener("click", () => {
            checkDependencies(true);
        });
    }

    // Storage Targets Help Modal
    const btnStorageHelp = document.getElementById("btn-storage-help");
    const linkRcloneSetup = document.getElementById("link-rclone-setup");
    const storageHelpModal = document.getElementById("storage-help-modal");
    const btnCloseStorageHelp = document.getElementById("btn-close-storage-help");
    const btnCloseStorageHelpOk = document.getElementById("btn-close-storage-help-ok");
    
    const openStorageHelp = () => {
        if (storageHelpModal) {
            storageHelpModal.classList.remove("hidden");
            setTimeout(() => {
                storageHelpModal.style.opacity = "1";
                storageHelpModal.style.pointerEvents = "auto";
            }, 10);
        }
    };
    
    const closeStorageHelp = () => {
        if (storageHelpModal) {
            storageHelpModal.style.opacity = "0";
            storageHelpModal.style.pointerEvents = "none";
            setTimeout(() => {
                storageHelpModal.classList.add("hidden");
            }, 300);
        }
    };
    
    if (btnStorageHelp) btnStorageHelp.addEventListener("click", openStorageHelp);
    if (linkRcloneSetup) linkRcloneSetup.addEventListener("click", openStorageHelp);
    if (btnCloseStorageHelp) btnCloseStorageHelp.addEventListener("click", closeStorageHelp);
    if (btnCloseStorageHelpOk) btnCloseStorageHelpOk.addEventListener("click", closeStorageHelp);

    const btnAddSource = document.getElementById("btn-settings-add-source");
    if(btnAddSource) {
        btnAddSource.addEventListener("click", () => {
            currentSettings.import_sources.push("");
            renderImportSources();
        });
    }

    const btnAddTarget = document.getElementById("btn-settings-add-target");
    if(btnAddTarget) {
        btnAddTarget.addEventListener("click", () => {
            if (!currentSettings.storage_targets) currentSettings.storage_targets = [];
            const newId = "target_" + Date.now();
            currentSettings.storage_targets.push({
                id: newId,
                name: "Neues Speicherziel",
                type: "cloud",
                root_path: "",
                rclone_remote: "",
                enabled: true
            });
            renderStorageTargets();
        });
    }

    const btnAddCategory = document.getElementById("btn-settings-add-category");
    if(btnAddCategory) {
        btnAddCategory.addEventListener("click", () => {
            currentSettings.sync_categories.push({id: "", name: "", nas_sub: "", pcloud_remote: ""});
            renderSyncCategories();
        });
    }

    const btnAddLocalFolder = document.getElementById("btn-settings-add-local-folder");
    if (btnAddLocalFolder) {
        btnAddLocalFolder.addEventListener("click", () => {
            if (!currentSettings.local_download_folders) currentSettings.local_download_folders = [];
            currentSettings.local_download_folders.push({ name: "", path: "" });
            renderLocalFolders();
        });
    }

    // Browse Buttons
    const bindBrowse = (btnId, inputId) => {
        const btn = document.getElementById(btnId);
        if(btn) {
            btn.addEventListener("click", async () => {
                try {
                    const response = await fetch("/api/browse-folder");
                    const data = await response.json();
                    if (data.folder) {
                        const inputEl = document.getElementById(inputId);
                        if (inputEl) inputEl.value = data.folder;
                    }
                } catch (e) { console.error("Browse error:", e); }
            });
        }
    };
    bindBrowse("btn-settings-browse-inbox", "settings-inbox-dir");
    bindBrowse("btn-settings-browse-outbox", "settings-outbox-dir");
    bindBrowse("btn-settings-browse-nas", "settings-nas-root");
    bindBrowse("btn-settings-browse-pcloud", "settings-pcloud-dir");

    // Toggle Buttons
    const bindToggle = (btnId, inputId) => {
        const btn = document.getElementById(btnId);
        if(btn) {
            btn.addEventListener("click", async () => {
                const inputEl = document.getElementById(inputId);
                const path = inputEl ? inputEl.value : "";
                if (!path) return;
                
                const hide = confirm(`Möchtest du den Ordner '${path}' im Finder VERSTECKEN?\n(Abbrechen für WIEDER SICHTBAR MACHEN)`);
                try {
                    const response = await fetch("/api/toggle-visibility", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ path: path, hide: hide })
                    });
                    if (response.ok) {
                        alert(`Ordner wurde ${hide ? "versteckt" : "sichtbar gemacht"}.`);
                    } else {
                        alert("Fehler beim Ändern der Sichtbarkeit.");
                    }
                } catch (e) { console.error(e); }
            });
        }
    };
    bindToggle("btn-settings-toggle-inbox", "settings-inbox-dir");
    bindToggle("btn-settings-toggle-outbox", "settings-outbox-dir");
});

// ==========================================================================
// PREVIEW MODAL LOGIC
// ==========================================================================
let currentPreviewPayload = null;

async function openPreviewModal(basePayload) {
    expandConsole();
    appendConsoleLog("[System]: Erstelle Trockenlauf-Vorschau...");
    
    // Set loading state in UI
    const overlay = document.getElementById("preview-modal-overlay");
    const modal = document.getElementById("preview-modal");
    const listRenames = document.getElementById("preview-list-renames");
    const listSubs = document.getElementById("preview-list-subs");
    const listJunk = document.getElementById("preview-list-junk");
    const dest = document.getElementById("preview-destination");
    const warningBox = document.getElementById("preview-season-warning");
    const warningText = document.getElementById("preview-season-warning-text");
    
    if (warningBox) {
        warningBox.classList.add("hidden");
    }
    
    const mismatchBox = document.getElementById("preview-show-name-mismatch");
    if (mismatchBox) {
        mismatchBox.classList.add("hidden");
    }
    
    // Check if any mapped season is >= 1000 (possible year warning)
    let hasHighSeason = false;
    let highSeasonNum = null;

    if (!basePayload.force_absolute_season_1) {
        if (basePayload.season && basePayload.season !== "all") {
            const s = parseInt(basePayload.season, 10);
            if (!isNaN(s) && s >= 1000) {
                hasHighSeason = true;
                highSeasonNum = s;
            }
        }
        if (!hasHighSeason && basePayload.mappings) {
            for (const val of Object.values(basePayload.mappings)) {
                if (val && typeof val === "object") {
                    const s = parseInt(val.season, 10);
                    if (!isNaN(s) && s >= 1000) {
                        hasHighSeason = true;
                        highSeasonNum = s;
                        break;
                    }
                } else if (typeof val === "string") {
                    const match = val.match(/^S(\d+)/i);
                    if (match) {
                        const s = parseInt(match[1], 10);
                        if (s >= 1000) {
                            hasHighSeason = true;
                            highSeasonNum = s;
                            break;
                        }
                    }
                }
            }
        }
    }

    if (hasHighSeason && warningBox && warningText) {
        warningText.textContent = `Staffel-Nummer ist eine Jahreszahl (${highSeasonNum})! Bitte prüfen, ob das korrekt ist (z.B. Staffel 56 statt 2026).`;
        warningBox.classList.remove("hidden");
    }
    
    listRenames.innerHTML = `<div style="color:var(--text-muted); font-size:12px;">Analysiere Ordner und Metadaten...</div>`;
    listSubs.innerHTML = "";
    listJunk.innerHTML = "";
    dest.textContent = "Wird berechnet...";
    
    // Show modal
    overlay.classList.remove("hidden");
    setTimeout(() => {
        overlay.style.opacity = "1";
        overlay.style.pointerEvents = "auto";
        modal.style.transform = "translateY(0)";
    }, 10);
    
    try {
        const response = await fetch("/api/preview_process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(basePayload)
        });
        
        if (!response.ok) throw new Error("Fehler beim Abrufen der Vorschau");
        const data = await response.json();
        
        if (data.error) {
            alert(data.error);
            closePreviewModal();
            return;
        }
        
        if (data.warning && warningBox && warningText && !basePayload.force_absolute_season_1) {
            warningText.textContent = data.warning;
            warningBox.classList.remove("hidden");
        }
        
        if (data.show_name_mismatch && mismatchBox) {
            const mText = document.getElementById("preview-show-name-mismatch-text");
            if (mText) {
                mText.innerHTML = `Der Zielordner auf dem NAS heißt <strong>"${data.show_name_mismatch.nas_name}"</strong>, aber die Vorschau verwendet den Namen <strong>"${data.show_name_mismatch.metadata_name}"</strong>.`;
            }
            
            const btnAdoptNas = document.getElementById("btn-preview-adopt-nas-name");
            const btnAdoptMeta = document.getElementById("btn-preview-adopt-metadata-name");
            
            if (btnAdoptNas) {
                const newBtn = btnAdoptNas.cloneNode(true);
                btnAdoptNas.parentNode.replaceChild(newBtn, btnAdoptNas);
                newBtn.addEventListener("click", () => {
                    const overrideInput = document.getElementById("series-nas-folder-override");
                    if (overrideInput) {
                        overrideInput.value = data.show_name_mismatch.nas_name;
                        autoMatchNasFolder("series-nas-folder-override", "series-nas-destination", overrideInput.value);
                    }
                    basePayload.nas_show_folder = data.show_name_mismatch.nas_name;
                    openPreviewModal(basePayload);
                });
            }
            
            if (btnAdoptMeta) {
                const newBtn = btnAdoptMeta.cloneNode(true);
                btnAdoptMeta.parentNode.replaceChild(newBtn, btnAdoptMeta);
                newBtn.addEventListener("click", () => {
                    const overrideInput = document.getElementById("series-nas-folder-override");
                    if (overrideInput) {
                        overrideInput.value = data.show_name_mismatch.metadata_name;
                        autoMatchNasFolder("series-nas-folder-override", "series-nas-destination", overrideInput.value);
                    }
                    basePayload.nas_show_folder = data.show_name_mismatch.metadata_name;
                    openPreviewModal(basePayload);
                });
            }
            
            mismatchBox.classList.remove("hidden");
        }
        
        currentPreviewPayload = basePayload;
        
        dest.innerHTML = data.destination.replace(/\n/g, '<br>');
        
        const createCheckbox = (item, checked, groupName) => {
            return `
                <label style="display:flex; align-items:center; gap:10px; background:rgba(0,0,0,0.2); padding:8px 12px; border-radius:var(--radius-sm); border:1px solid rgba(255,255,255,0.05); cursor:pointer;">
                    <input type="checkbox" class="preview-cb-${groupName}" data-old="${item.old || item}" data-new="${item.new || ''}" ${checked ? 'checked' : ''} style="accent-color:var(--accent);">
                    <div style="flex:1; overflow:hidden;">
                        <div style="font-size:11px; color:var(--text-muted); text-decoration:line-through; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.old || item}</div>
                        ${item.new ? `<div style="font-size:13px; color:var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${item.new}</div>` : ''}
                    </div>
                </label>
            `;
        };
        
        listRenames.innerHTML = data.renames.length > 0 
            ? data.renames.map(r => createCheckbox(r, true, "renames")).join("")
            : `<div style="color:var(--text-muted); font-size:12px;">Keine Videos gefunden.</div>`;
            
        listSubs.innerHTML = data.subs.length > 0
            ? data.subs.map(s => createCheckbox(s, true, "subs")).join("")
            : `<div style="color:var(--text-muted); font-size:12px;">Keine Untertitel/Extras gefunden.</div>`;
            
        listJunk.innerHTML = data.junk.length > 0
            ? data.junk.map(j => createCheckbox(j, true, "junk")).join("")
            : `<div style="color:var(--text-muted); font-size:12px;">Keine Müll-Dateien gefunden! Ordner ist sauber.</div>`;
            
        appendConsoleLog("[System]: Vorschau erfolgreich generiert.");
            
    } catch (e) {
        alert("Fehler: " + e.message);
        closePreviewModal();
    }
}

function closePreviewModal() {
    const overlay = document.getElementById("preview-modal-overlay");
    const modal = document.getElementById("preview-modal");
    
    overlay.style.opacity = "0";
    overlay.style.pointerEvents = "none";
    modal.style.transform = "translateY(20px)";
    setTimeout(() => {
        overlay.classList.add("hidden");
    }, 300);
}

function saveConversionSettings() {
    const settings = {
        movieOptionConvert: document.getElementById("movie-option-convert")?.checked,
        movieOptionDelete: document.getElementById("movie-option-delete")?.checked,
        movieOptionCopyNas: document.getElementById("movie-option-copy-nas")?.checked,
        movieOptionCopyPcloud: document.getElementById("movie-option-copy-pcloud")?.checked,
        movieQualitySlider: document.getElementById("movie-quality-slider")?.value,

        seriesOptionConvert: document.getElementById("series-option-convert")?.checked,
        seriesOptionDelete: document.getElementById("series-option-delete")?.checked,
        seriesOptionCopyNas: document.getElementById("series-option-copy-nas")?.checked,
        seriesOptionCopyPcloud: document.getElementById("series-option-copy-pcloud")?.checked,
        seriesOptionAbsoluteNumbering: document.getElementById("series-option-absolute-numbering")?.checked,
        seriesQualitySlider: document.getElementById("series-quality-slider")?.value,

        ytOptionCopyNas: document.getElementById("yt-option-copy-nas")?.checked,
        ytOptionCopyPcloud: document.getElementById("yt-option-copy-pcloud")?.checked,
        ytOptionCopyLocal: document.getElementById("yt-option-copy-local")?.checked,
        ytLocalDestination: document.getElementById("yt-local-destination")?.value,

        toolQualitySlider: document.getElementById("tool-quality-slider")?.value,
        toolForceReconvert: document.getElementById("tool-force-reconvert")?.checked
    };
    localStorage.setItem("conversionSettings", JSON.stringify(settings));
}

function loadConversionSettings() {
    try {
        const stored = localStorage.getItem("conversionSettings");
        if (!stored) return;
        const settings = JSON.parse(stored);
        
        const setCheckbox = (id, val) => {
            const cb = document.getElementById(id);
            if (cb && val !== undefined) {
                cb.checked = !!val;
                cb.dispatchEvent(new Event('change'));
            }
        };

        const setSlider = (id, valElId, val) => {
            const slider = document.getElementById(id);
            const valEl = document.getElementById(valElId);
            if (slider && val !== undefined) {
                slider.value = val;
                if (valEl) valEl.textContent = val;
            }
        };

        setCheckbox("movie-option-convert", settings.movieOptionConvert);
        setCheckbox("movie-option-delete", settings.movieOptionDelete);
        setCheckbox("movie-option-copy-nas", settings.movieOptionCopyNas);
        setCheckbox("movie-option-copy-pcloud", settings.movieOptionCopyPcloud);
        setSlider("movie-quality-slider", "movie-quality-val", settings.movieQualitySlider);

        setCheckbox("series-option-convert", settings.seriesOptionConvert);
        setCheckbox("series-option-delete", settings.seriesOptionDelete);
        setCheckbox("series-option-copy-nas", settings.seriesOptionCopyNas);
        setCheckbox("series-option-copy-pcloud", settings.seriesOptionCopyPcloud);
        setCheckbox("series-option-absolute-numbering", settings.seriesOptionAbsoluteNumbering);
        setSlider("series-quality-slider", "series-quality-val", settings.seriesQualitySlider);

        setCheckbox("yt-option-copy-nas", settings.ytOptionCopyNas);
        setCheckbox("yt-option-copy-pcloud", settings.ytOptionCopyPcloud);
        setCheckbox("yt-option-copy-local", settings.ytOptionCopyLocal);
        const ytLocalDest = document.getElementById("yt-local-destination");
        if (ytLocalDest && settings.ytLocalDestination) {
            ytLocalDest.value = settings.ytLocalDestination;
        }

        setSlider("tool-quality-slider", "tool-quality-val", settings.toolQualitySlider);
        setCheckbox("tool-force-reconvert", settings.toolForceReconvert);
    } catch (e) {
        console.error("Error loading conversion settings:", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // 1. Load settings from localStorage first
    loadConversionSettings();

    // 2. Register listeners that trigger both size estimation/UI toggles and save settings
    const saveAndEstMovie = () => {
        saveConversionSettings();
        updateSizeEstimation("movie");
    };
    
    const saveAndEstSeries = () => {
        saveConversionSettings();
        updateSizeEstimation("series");
    };

    document.getElementById("movie-option-convert")?.addEventListener("change", saveAndEstMovie);
    document.getElementById("movie-option-delete")?.addEventListener("change", saveConversionSettings);
    document.getElementById("movie-option-copy-nas")?.addEventListener("change", saveConversionSettings);
    document.getElementById("movie-option-copy-pcloud")?.addEventListener("change", saveConversionSettings);

    document.getElementById("series-option-convert")?.addEventListener("change", saveAndEstSeries);
    document.getElementById("series-option-delete")?.addEventListener("change", saveConversionSettings);
    document.getElementById("series-option-copy-nas")?.addEventListener("change", saveConversionSettings);
    document.getElementById("series-option-copy-pcloud")?.addEventListener("change", saveConversionSettings);
    document.getElementById("series-option-absolute-numbering")?.addEventListener("change", saveConversionSettings);

    document.getElementById("yt-option-copy-nas")?.addEventListener("change", saveConversionSettings);
    document.getElementById("yt-option-copy-pcloud")?.addEventListener("change", saveConversionSettings);
    document.getElementById("yt-option-copy-local")?.addEventListener("change", saveConversionSettings);
    document.getElementById("yt-local-destination")?.addEventListener("change", saveConversionSettings);

    // Movie quality slider
    const movieSlider = document.getElementById("movie-quality-slider");
    const movieVal = document.getElementById("movie-quality-val");
    if (movieSlider && movieVal) {
        movieSlider.addEventListener("input", () => {
            movieVal.textContent = movieSlider.value;
            triggerQualityHintUpdates();
        });
        movieSlider.addEventListener("change", saveAndEstMovie);
    }
    document.getElementById("movie-nas-destination")?.addEventListener("change", triggerQualityHintUpdates);

    // Series quality slider
    const seriesSlider = document.getElementById("series-quality-slider");
    const seriesVal = document.getElementById("series-quality-val");
    if (seriesSlider && seriesVal) {
        seriesSlider.addEventListener("input", () => {
            seriesVal.textContent = seriesSlider.value;
            triggerQualityHintUpdates();
        });
        seriesSlider.addEventListener("change", saveAndEstSeries);
    }
    document.getElementById("series-nas-destination")?.addEventListener("change", triggerQualityHintUpdates);
    document.getElementById("series-is-anime")?.addEventListener("change", triggerQualityHintUpdates);

    // Tool quality slider
    const toolSlider = document.getElementById("tool-quality-slider");
    const toolVal = document.getElementById("tool-quality-val");
    if (toolSlider && toolVal) {
        toolSlider.addEventListener("input", () => {
            toolVal.textContent = toolSlider.value;
        });
        toolSlider.addEventListener("change", () => {
            saveConversionSettings();
        });
    }

    document.getElementById("tool-force-reconvert")?.addEventListener("change", () => {
        saveConversionSettings();
    });

    // Initialize size estimations and visibility of quality sliders on startup
    updateSizeEstimation("movie");
    updateSizeEstimation("series");

    document.getElementById("btn-open-nas-folder-series")?.addEventListener("click", async () => {
        const catSelect = document.getElementById("series-nas-destination");
        const folderInput = document.getElementById("series-nas-folder-override");
        if (!catSelect) return;
        const catId = catSelect.value;
        const folderName = folderInput ? folderInput.value.trim() : "";
        
        try {
            const res = await fetch(`/api/system/open-folder?category_id=${catId}&folder_name=${encodeURIComponent(folderName)}`);
            if (res.ok) {
                const data = await res.json();
                if (data.error) {
                    alert(data.error);
                } else {
                    appendConsoleLog(`[System]: ${data.msg || "Ordner im Finder geöffnet."}`);
                }
            } else {
                alert("Fehler beim Senden der Anfrage an den Server.");
            }
        } catch (err) {
            alert("Fehler beim Öffnen des Ordners: " + err.message);
        }
    });

    document.getElementById("btn-preview-close")?.addEventListener("click", closePreviewModal);
    document.getElementById("btn-preview-cancel")?.addEventListener("click", closePreviewModal);
    
    document.getElementById("btn-preview-execute")?.addEventListener("click", async () => {
        if (!currentPreviewPayload) return;
        
        // Collect checked items
        const explicitRenames = Array.from(document.querySelectorAll(".preview-cb-renames:checked")).map(cb => ({ old: cb.dataset.old, new: cb.dataset.new }));
        const explicitSubs = Array.from(document.querySelectorAll(".preview-cb-subs:checked")).map(cb => ({ old: cb.dataset.old, new: cb.dataset.new }));
        const explicitJunk = Array.from(document.querySelectorAll(".preview-cb-junk:checked")).map(cb => cb.dataset.old);
        
        const finalPayload = {
            ...currentPreviewPayload,
            explicit_renames: explicitRenames,
            explicit_subs: explicitSubs,
            explicit_junk: explicitJunk
        };
        
        // Save profile if media_type is TV and "no-profile" is not checked
        const noProfileCb = document.getElementById("series-option-no-profile");
        const skipProfileSave = noProfileCb ? noProfileCb.checked : false;
        
        if (finalPayload.media_type === "tv" && !skipProfileSave) {
            try {
                const auto_h265 = document.getElementById("series-option-convert").checked ? "j" : "n";
                const pcloud_sonstiges = document.getElementById("series-option-copy-pcloud").checked ? "j" : "n";
                const copy_to_nas = document.getElementById("series-option-copy-nas").checked;
                const copy_to_pcloud = document.getElementById("series-option-copy-pcloud").checked;
                const nas_destination_id = document.getElementById("series-nas-destination").value;
                const pcloud_destination_id = document.getElementById("series-pcloud-destination").value;
                const force_absolute_season_1 = document.getElementById("series-option-absolute-numbering")?.checked || false;
                
                await fetch("/api/profile", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        show_name: finalPayload.show_name,
                        profile: {
                            auto_h265: auto_h265,
                            pcloud_sonstiges: pcloud_sonstiges,
                            schema: "staffeln",
                            provider: finalPayload.provider || "",
                            show_id: finalPayload.show_id || "",
                            all_seasons: document.getElementById("series-all-seasons").checked,
                            copy_to_nas: copy_to_nas,
                            copy_to_pcloud: copy_to_pcloud,
                            nas_destination_id: nas_destination_id,
                            pcloud_destination_id: pcloud_destination_id,
                            force_absolute_season_1: force_absolute_season_1
                        }
                    })
                });
            } catch (err) {
                console.error("Error saving show profile on execution:", err);
            }
        }
        

        
        closePreviewModal();
        appendConsoleLog("[System]: Starte finalen Verarbeitungsprozess...");
        
        try {
            const response = await fetch("/api/process", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(finalPayload)
            });
            
            if (response.ok) {
                connectLogStream();
            } else {
                appendConsoleLog("[System] Fehler beim Starten des Prozesses.");
            }
        } catch (e) {
            appendConsoleLog(`[System] Fehler: ${e}`);
        }
    });

    // Clean Modal Listeners
    document.getElementById("btn-clean-close")?.addEventListener("click", closeCleanModal);
    document.getElementById("btn-clean-cancel")?.addEventListener("click", closeCleanModal);
    
    document.getElementById("btn-clean-execute")?.addEventListener("click", async (e) => {
        const targetPath = e.currentTarget.dataset.target;
        if (!targetPath) return;
        
        const explicitFiles = Array.from(document.querySelectorAll(".clean-cb-item:checked")).map(cb => cb.dataset.file);
        
        if (explicitFiles.length === 0) {
            alert("Es wurden keine Dateien zum Löschen ausgewählt.");
            closeCleanModal();
            return;
        }
        
        closeCleanModal();
        appendConsoleLog("[System]: Lösche ausgewählte Dateien...");
        
        try {
            const response = await fetch("/api/clean-project", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project: targetPath, explicit_files: explicitFiles })
            });
            const data = await response.json();
            
            if (data.status === "ok") {
                appendConsoleLog(`✅ Bereinigung fertig! (${data.deleted_files.length} Dateien, ${data.deleted_dirs.length} Ordner gelöscht)`);
                scanProject(targetPath);
            }
        } catch (err) {
            appendConsoleLog(`❌ Fehler bei Bereinigung: ${err}`);
        }
    });
});

// ==========================================================================
// TASK QUEUE SYSTEM
// ==========================================================================
function initQueue() {
    const queuePanel = document.getElementById("queue-panel");
    const overlay = document.getElementById("queue-panel-overlay");
    const navBtn = document.getElementById("nav-queue-dashboard");
    const headerBtn = document.getElementById("header-queue-btn");
    const closeBtn = document.getElementById("btn-close-queue");

    function openQueue() {
        overlay.classList.remove("hidden");
        setTimeout(() => {
            overlay.style.opacity = "1";
            overlay.style.pointerEvents = "auto";
            queuePanel.style.transform = "translateX(0)";
        }, 10);
    }

    function closeQueue() {
        overlay.style.opacity = "0";
        overlay.style.pointerEvents = "none";
        queuePanel.style.transform = "translateX(100%)";
        setTimeout(() => {
            overlay.classList.add("hidden");
        }, 300);
    }

    if (navBtn) navBtn.addEventListener("click", openQueue);
    if (headerBtn) headerBtn.addEventListener("click", openQueue);
    if (closeBtn) closeBtn.addEventListener("click", closeQueue);
    if (overlay) overlay.addEventListener("click", closeQueue);

    const clearBtn = document.getElementById("btn-clear-queue");
    if (clearBtn) {
        clearBtn.addEventListener("click", async () => {
            if (confirm("Möchtest du die Warteschlange wirklich leeren? (Laufende Aufgaben werden nicht abgebrochen)")) {
                try {
                    const res = await fetch("/api/queue/clear", { method: "POST" });
                    if (res.ok) {
                        pollQueue();
                    }
                } catch (e) {
                    console.error("Fehler beim Leeren der Warteschlange:", e);
                }
            }
        });
    }

    setInterval(pollQueue, 2000);
    pollQueue();
}

async function pollQueue() {
    if (document.hidden) return;
    if (document.visibilityState === "hidden") return;
    try {
        const res = await fetch("/api/queue");
        if (!res.ok) return;
        const data = await res.json();
        renderQueue(data.jobs || []);
    } catch (e) {
        // ignore network errors for polling
    }
}

function renderQueue(jobs) {
    const list = document.getElementById("queue-list");
    const badge = document.getElementById("queue-badge");
    const headerBadge = document.getElementById("header-queue-badge");

    const activeSet = new Set();
    jobs.forEach(j => {
        if (j.status === "queued" || j.status === "running") {
            const p = j.project_name;
            if (p !== undefined && p !== null) {
                activeSet.add(p);
            }
        }
    });
    activeProjectsProcessing = activeSet;
    updateSidebarProcessingStates(activeProjectsProcessing);

    const activeJobs = jobs.filter(j => j.status === "queued" || j.status === "running");
    
    if (activeJobs.length > 0) {
        if (badge) {
            badge.textContent = activeJobs.length;
            badge.classList.remove("hidden");
        }
        if (headerBadge) {
            headerBadge.textContent = activeJobs.length;
            headerBadge.classList.remove("hidden");
        }
    } else {
        if (badge) badge.classList.add("hidden");
        if (headerBadge) headerBadge.classList.add("hidden");
    }

    if (jobs.length === 0) {
        list.innerHTML = `<div style="color:var(--text-muted); text-align:center; padding: 30px;">Keine Aufgaben in der Warteschlange.</div>`;
        return;
    }

    list.innerHTML = "";
    
    // Sort so newest is at the top
    [...jobs].reverse().forEach(job => {
        let statusColor = "var(--text-muted)";
        let icon = "⏳";
        
        if (job.status === "running") { statusColor = "var(--accent)"; icon = "🔄"; }
        else if (job.status === "done") { statusColor = "#4caf50"; icon = "✅"; }
        else if (job.status === "error") { statusColor = "#ff6b6b"; icon = "❌"; }
        
        let progressHtml = "";
        if (job.status === "running" || job.status === "queued" || job.status === "done") {
            const displayProgress = job.progress || 0;
            const isAnimated = job.status === "running" ? "animation: pulse 2s infinite;" : "";
            progressHtml = `
                <div style="background:var(--bg-dark); height:8px; border-radius:4px; margin-top:10px; overflow:hidden;">
                    <div style="background:${statusColor}; height:100%; width:${displayProgress}%; transition:width 0.3s; ${isAnimated}"></div>
                </div>
            `;
        }

        let pipelineHtml = "";
        if (job.pipeline) {
            const steps = [
                { key: "metadata", label: "Metadaten" },
                { key: "convert", label: "Konvertierung" }
            ];
            
            // Dynamically add storage targets from settings or fallback to pipeline keys
            if (currentSettings && currentSettings.storage_targets) {
                currentSettings.storage_targets.forEach(target => {
                    const t_id = target.id;
                    if (job.pipeline[t_id]) {
                        steps.push({ key: t_id, label: target.name || t_id });
                    }
                });
            }
            
            // Fallback for targets in pipeline not present in storage_targets
            Object.keys(job.pipeline).forEach(key => {
                if (key !== "metadata" && key !== "convert" && key !== "local" && !steps.some(s => s.key === key)) {
                    const fallbackLabel = key === "nas" ? "NAS-Kopieren" : (key === "pcloud" ? "pCloud" : key);
                    steps.push({ key: key, label: fallbackLabel });
                }
            });
            
            if (job.pipeline.local) {
                steps.push({ key: "local", label: "Lokal-Kopieren" });
            }
            
            pipelineHtml = `<div class="pipeline-container" style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; gap: 4px; background: rgba(0,0,0,0.25); padding: 8px; border-radius: var(--radius-md); box-sizing: border-box; width: 100%;">`;
            
            steps.forEach((step, idx) => {
                const sData = job.pipeline[step.key];
                if (!sData) return;
                
                let stepColor = "rgba(255, 255, 255, 0.05)";
                let stepIcon = "⚪";
                let textColor = "var(--text-muted)";
                let borderStyle = "1px solid rgba(255,255,255,0.05)";
                
                if (sData.status === "running") {
                    stepColor = "rgba(0, 229, 255, 0.1)";
                    stepIcon = "🔄 animate-spin";
                    textColor = "#00e5ff";
                    borderStyle = "1px solid rgba(0, 229, 255, 0.3)";
                } else if (sData.status === "done") {
                    stepColor = "rgba(76, 175, 80, 0.1)";
                    stepIcon = "✅";
                    textColor = "#4caf50";
                    borderStyle = "1px solid rgba(76, 175, 80, 0.3)";
                } else if (sData.status === "error") {
                    stepColor = "rgba(244, 67, 54, 0.1)";
                    stepIcon = "❌";
                    textColor = "#f44336";
                    borderStyle = "1px solid rgba(244, 67, 54, 0.3)";
                } else if (sData.status === "skipped") {
                    stepColor = "rgba(255, 255, 255, 0.02)";
                    stepIcon = "➖";
                    textColor = "rgba(255,255,255,0.15)";
                    borderStyle = "1px solid rgba(255,255,255,0.02)";
                }
                
                // Add spinning animation inline style for animate-spin
                const isSpinning = stepIcon.includes("animate-spin") ? "animation: spin 2s linear infinite;" : "";
                const cleanIcon = stepIcon.replace(" animate-spin", "");
                
                pipelineHtml += `
                    <div style="flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 6px 2px; border-radius: var(--radius-sm); background: ${stepColor}; border: ${borderStyle}; text-align: center; box-sizing: border-box;">
                        <span style="font-size: 13px; line-height: 1; display: inline-block; ${isSpinning}">${cleanIcon}</span>
                        <span style="font-size: 9px; font-weight: 500; color: ${textColor}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; display: block;" title="${step.label}">${step.label}</span>
                        ${sData.status === "running" ? `<span style="font-size: 9px; color: ${textColor}; font-weight: bold; display: block;">${sData.progress}%</span>` : ""}
                    </div>
                `;
                
                if (idx < steps.length - 1) {
                    pipelineHtml += `
                        <div style="font-size: 9px; color: rgba(255,255,255,0.15); font-weight: bold; flex: 0 0 auto;">➔</div>
                    `;
                }
            });
            
            pipelineHtml += `</div>`;
        }

        let retryHtml = "";
        if (job.status === "error") {
            retryHtml = `
                <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
                    <button class="queue-retry-btn btn-secondary" data-task-id="${job.id}" style="padding: 4px 10px; font-size: 11px; display: flex; align-items: center; gap: 4px; border-radius: var(--radius-sm); cursor: pointer; transition: all 0.2s;">
                        🔄 Wiederholen
                    </button>
                </div>
            `;
        }

        const card = document.createElement("div");
        card.style.cssText = "background: rgba(20,20,30,0.5); border: 1px solid var(--border-glass); border-radius: var(--radius-lg); padding: 15px;";
        
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <strong style="font-size:14px; color:var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:10px;">${icon} ${job.name}</strong>
                <span style="font-size:12px; color:${statusColor}; text-transform:uppercase;">${job.status}</span>
            </div>
            <div style="font-size:12px; color:var(--text-muted);">${job.message || ""}</div>
            ${progressHtml}
            ${pipelineHtml}
            ${retryHtml}
        `;
        list.appendChild(card);
    });

    // Registriere Klick-Handler für Wiederholen-Buttons
    list.querySelectorAll(".queue-retry-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            const taskId = e.currentTarget.getAttribute("data-task-id");
            if (!taskId) return;
            
            // Button deaktivieren und Lade-Status anzeigen
            e.currentTarget.disabled = true;
            e.currentTarget.innerHTML = "🔄 Einreihen...";
            
            try {
                const res = await fetch("/api/queue/retry", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ task_id: taskId })
                });
                
                if (res.ok) {
                    pollQueue();
                } else {
                    const data = await res.json();
                    alert(`Fehler beim Wiederholen: ${data.message || "Unbekannter Fehler"}`);
                    e.currentTarget.disabled = false;
                    e.currentTarget.innerHTML = "🔄 Wiederholen";
                }
            } catch (err) {
                console.error("Fehler beim Wiederholen des Jobs:", err);
                alert("Fehler beim Verbinden mit dem Server.");
                e.currentTarget.disabled = false;
                e.currentTarget.innerHTML = "🔄 Wiederholen";
            }
        });
    });

    // Check for newly finished jobs to show joke
    jobs.forEach(job => {
        if (job.status === "done" || job.status === "error") {
            if (!knownFinishedJobs.has(job.id)) {
                if (!isFirstQueuePoll && job.status === "done") {
                    // Newly finished job! Trigger joke!
                    if (currentSettings && currentSettings.show_jokes !== false) {
                        fetch("/api/joke")
                            .then(res => res.json())
                            .then(data => {
                                if (data.joke) {
                                    showJokeModal(data.joke);
                                }
                            }).catch(err => console.error(err));
                    }
                }
                if (knownFinishedJobs.size >= 100) {
                    const firstVal = knownFinishedJobs.values().next().value;
                    knownFinishedJobs.delete(firstVal);
                }
                knownFinishedJobs.add(job.id);
            }
        }
    });
    
    if (isFirstQueuePoll) {
        isFirstQueuePoll = false;
    }
}

function setupNasFolderAutocomplete(inputId, dropdownId, loadBtnId, destSelectId) {
    const input = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
    const loadBtn = document.getElementById(loadBtnId);
    const destSelect = document.getElementById(destSelectId);
    
    if (!input || !dropdown || !loadBtn || !destSelect) return;
    
    let allFolders = [];
    let folderDestinations = {};
    const originalBtnText = loadBtn.textContent || "NAS laden";
    
    const loadFolders = async (shouldFocusInnerSearch = false) => {
        let destVal = destSelect.value;
        if (inputId === "series-nas-folder-override" || inputId === "yt-series-nas-folder-override") {
            destVal = "all";
        }
        loadBtn.disabled = true;
        loadBtn.textContent = "Lade...";
        try {
            const res = await fetch(`/api/nas-series?destination_id=${encodeURIComponent(destVal)}`);
            if (res.ok) {
                const data = await res.json();
                if (data.folders) {
                    allFolders = data.folders;
                    folderDestinations = data.folder_destinations || {};
                    appendConsoleLog(`[System]: ${allFolders.length} Serienordner erfolgreich geladen.`);
                    showDropdown(allFolders, shouldFocusInnerSearch);
                } else {
                    appendConsoleLog("[System]: Keine Serienordner auf dem NAS gefunden.");
                }
            } else {
                appendConsoleLog("[System]: Fehler beim Laden der Serienordner vom NAS.");
            }
        } catch (e) {
            console.error("Error loading NAS folders:", e);
            appendConsoleLog(`[System]: Fehler beim Laden der Serienordner: ${e.message}`);
        } finally {
            loadBtn.disabled = false;
            loadBtn.textContent = originalBtnText;
        }
    };
    
    const showDropdown = (list, shouldFocusInnerSearch = false) => {
        dropdown.innerHTML = "";
        
        // Add a search/filter input container at the top of the dropdown
        const searchWrapper = document.createElement("div");
        searchWrapper.className = "autocomplete-search-wrapper";
        searchWrapper.addEventListener("click", (e) => {
            e.stopPropagation();
        });
        
        // Premium magnifying glass SVG
        searchWrapper.innerHTML = `
            <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
        `;
        
        const searchInput = document.createElement("input");
        searchInput.type = "text";
        searchInput.className = "autocomplete-search-input";
        searchInput.placeholder = "Serienname suchen...";
        searchInput.autocomplete = "off";
        
        searchWrapper.appendChild(searchInput);
        dropdown.appendChild(searchWrapper);
        
        const itemsContainer = document.createElement("div");
        itemsContainer.className = "autocomplete-items-container";
        dropdown.appendChild(itemsContainer);
        
        const renderItems = (filteredList) => {
            itemsContainer.innerHTML = "";
            if (filteredList.length === 0) {
                itemsContainer.innerHTML = `<div class="autocomplete-no-results">Keine Ergebnisse</div>`;
            } else {
                filteredList.forEach(folder => {
                    const item = document.createElement("div");
                    item.className = "autocomplete-item";
                    item.textContent = folder;
                    item.addEventListener("click", (e) => {
                        e.stopPropagation();
                        input.value = folder;
                        if (inputId === "series-nas-folder-override") {
                            window.nasFolderSelected = folder;
                        } else if (inputId === "yt-series-nas-folder-override") {
                            window.ytNasFolderSelected = folder;
                        }
                        closeDropdown();
                        
                        // Automatically switch category if category mapping exists
                        if (destSelect && folderDestinations && folderDestinations[folder.toLowerCase()]) {
                            const matchedDestPath = folderDestinations[folder.toLowerCase()];
                            const nasRoot = currentSettings.nas_root || "";
                            const foundCat = (currentSettings.sync_categories || []).find(cat => {
                                const fullPath = nasRoot + (cat.nas_sub || "");
                                return fullPath.toLowerCase() === matchedDestPath.toLowerCase();
                            });
                            
                            if (foundCat) {
                                const matchedDest = foundCat.id;
                                let hasOption = false;
                                for (let i = 0; i < destSelect.options.length; i++) {
                                    if (destSelect.options[i].value === matchedDest) {
                                        hasOption = true;
                                        break;
                                    }
                                }
                                if (hasOption) {
                                    window.isProgrammaticCategoryChange = true;
                                    destSelect.value = matchedDest;
                                    destSelect.dispatchEvent(new Event("change", { bubbles: true }));
                                    window.isProgrammaticCategoryChange = false;
                                }
                            }
                        }
                        
                        // Trigger listeners
                        input.dispatchEvent(new Event("input", { bubbles: true }));
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                        
                        // Custom action: If this is the series tab autocomplete, trigger show matching!
                        if (inputId === "series-nas-folder-override") {
                            triggerSeriesMatchingFromFolder(folder);
                        } else if (inputId === "yt-series-nas-folder-override") {
                            fetchYtNasSeasons();
                        }
                    });
                    itemsContainer.appendChild(item);
                });
            }
        };
        
        // Inner search input event listener
        searchInput.addEventListener("input", () => {
            const query = searchInput.value.toLowerCase().trim();
            if (!query) {
                renderItems(list);
            } else {
                const filtered = list.filter(folder => folder.toLowerCase().includes(query));
                renderItems(filtered);
            }
        });
        
        // Initial render
        renderItems(list);
        
        dropdown.classList.remove("hidden");
        
        if (shouldFocusInnerSearch) {
            setTimeout(() => {
                searchInput.focus();
            }, 50);
        }
    };
    
    const closeDropdown = () => {
        dropdown.classList.add("hidden");
    };
    
    loadBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        loadFolders(true);
    });
    
    input.addEventListener("focus", async () => {
        if (allFolders.length === 0) {
            await loadFolders(false);
        } else {
            filterFolders(false);
        }
    });
    
    const filterFolders = (shouldFocusInnerSearch = false) => {
        const query = input.value.toLowerCase().trim();
        if (allFolders.length === 0) return;
        if (!query) {
            showDropdown(allFolders, shouldFocusInnerSearch);
            return;
        }
        // Case-insensitive substring match (fuzzy)
        const filtered = allFolders.filter(folder => folder.toLowerCase().includes(query));
        showDropdown(filtered, shouldFocusInnerSearch);
    };
    
    const debouncedFilter = debounce(() => filterFolders(false), 250);
    input.addEventListener("input", debouncedFilter);
    
    // Clear folder cache when destination select changes
    destSelect.addEventListener("change", () => {
        allFolders = [];
        folderDestinations = {};
    });
    
    // Close dropdown on click outside
    document.addEventListener("click", (e) => {
        if (!input.contains(e.target) && !dropdown.contains(e.target) && !loadBtn.contains(e.target)) {
            closeDropdown();
        }
    });
}

function findBestNasFolderMatch(cleanedTitle, folders) {
    if (!cleanedTitle || !folders || folders.length === 0) return null;
    
    const cleanStr = cleanSeriesName(cleanedTitle).trim();
    if (!cleanStr) return null;
    
    // 1. Exact case-insensitive match
    for (const f of folders) {
        if (f.toLowerCase().trim() === cleanStr.toLowerCase()) {
            return f;
        }
    }
    
    // 2. Normalized alphanumeric match
    const normProj = cleanStr.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (normProj) {
        for (const f of folders) {
            const normF = f.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (normF === normProj) {
                return f;
            }
        }
    }
    
    // 3. Substring match
    if (normProj.length >= 4) {
        const hasYear = (str) => /\d{4}/.test(str);
        for (const f of folders) {
            const normF = f.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (normF.includes(normProj) || normProj.includes(normF)) {
                if (hasYear(normProj) !== hasYear(normF)) {
                    continue; // Skip mismatching years to prevent e.g. Avatar (2024) matching Avatar (2005)
                }
                return f;
            }
        }
    }
    
    return null;
}

async function autoMatchNasFolder(inputId, destSelectId, originalCleanedName) {
    if (!originalCleanedName) return;
    const input = document.getElementById(inputId);
    const destSelect = document.getElementById(destSelectId);
    if (!input || !destSelect) return;
    
    const destVal = destSelect.value;
    try {
        const res = await fetch(`/api/nas-series?destination_id=${encodeURIComponent(destVal)}`);
        if (res.ok) {
            const data = await res.json();
            if (data.folders && data.folders.length > 0) {
                const bestMatch = findBestNasFolderMatch(originalCleanedName, data.folders);
                if (bestMatch) {
                    input.value = bestMatch;
                    
                    // Trigger visual flash
                    input.classList.remove("highlight-match-flash");
                    void input.offsetWidth; // trigger reflow
                    input.classList.add("highlight-match-flash");
                    setTimeout(() => {
                        input.classList.remove("highlight-match-flash");
                    }, 1500);
                    
                    appendConsoleLog(`[System]: Automatisch passenden NAS-Ordner "${bestMatch}" zugeordnet.`);
                }
            }
        }
    } catch (e) {
        console.error("Error auto matching NAS folder:", e);
    }
}

let isFirstQueuePoll = true;
let knownFinishedJobs = new Set();

function showJokeModal(jokeText) {
    const existing = document.getElementById("joke-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "joke-modal";
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    const content = document.createElement("div");
    content.style.cssText = `
        background: rgba(30, 30, 45, 0.95);
        border: 1px solid var(--border-glass);
        border-radius: var(--radius-lg);
        padding: 30px;
        width: 90%;
        max-width: 450px;
        text-align: center;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        transform: scale(0.9);
        transition: transform 0.3s ease;
    `;

    content.innerHTML = `
        <div style="font-size: 40px; margin-bottom: 15px;">🎭</div>
        <h3 style="margin-top: 0; color: var(--text-main); font-size: 18px; font-weight: 600; letter-spacing: 0.5px;">Witz des Tages</h3>
        <p style="font-size: 14px; color: var(--text-main); line-height: 1.6; margin: 20px 0; font-style: italic;">"${jokeText}"</p>
        <button id="btn-close-joke" class="btn btn-primary" style="margin-top: 10px; min-width: 120px;">Hahaha! 😂</button>
    `;

    modal.appendChild(content);
    document.body.appendChild(modal);

    setTimeout(() => {
        modal.style.opacity = "1";
        content.style.transform = "scale(1)";
    }, 10);

    const closeBtn = content.querySelector("#btn-close-joke");
    const closeModal = () => {
        modal.style.opacity = "0";
        content.style.transform = "scale(0.9)";
        setTimeout(() => modal.remove(), 300);
    };

    closeBtn.addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });
}

async function triggerLaunchJoke() {
    if (currentSettings && currentSettings.show_jokes !== false) {
        try {
            const res = await fetch("/api/joke");
            if (res.ok) {
                const data = await res.json();
                if (data.joke) {
                    showJokeModal(data.joke);
                }
            }
        } catch (e) {
            console.error("Failed to load joke:", e);
        }
    }
}

async function triggerLaunchQuote() {
    if (currentSettings && currentSettings.show_quote !== false) {
        try {
            const res = await fetch("/api/quote");
            if (res.ok) {
                const data = await res.json();
                if (data.quote) {
                    showQuoteModal(data);
                }
            }
        } catch (e) {
            console.error("Failed to load quote:", e);
        }
    }
}

function showQuoteModal(quoteData) {
    const existing = document.getElementById("quote-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "quote-modal";
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    const content = document.createElement("div");
    content.style.cssText = `
        background: rgba(30, 30, 45, 0.95);
        border: 1px solid var(--border-glass);
        border-radius: var(--radius-lg);
        padding: 35px 30px;
        width: 90%;
        max-width: 500px;
        text-align: center;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        transform: scale(0.9);
        transition: transform 0.3s ease;
        position: relative;
    `;

    const cleanQuote = quoteData.quote.trim();
    const cleanAuthor = (quoteData.authorName || "Unbekannt").trim();
    const authorHtml = quoteData.authorLink 
        ? `<a href="${quoteData.authorLink}" target="_blank" style="color: #c084fc; text-decoration: none; border-bottom: 1px dotted #c084fc; font-weight: 500;">— ${cleanAuthor}</a>`
        : `<span style="color: #94a3b8; font-weight: 500;">— ${cleanAuthor}</span>`;

    content.innerHTML = `
        <div style="font-size: 44px; margin-bottom: 15px; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.3));">✍️</div>
        <h3 style="margin-top: 0; color: #94a3b8; font-size: 13px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 20px;">Zitat des Tages</h3>
        
        <p style="
            font-size: 16px; 
            color: #e2e8f0;
            line-height: 1.7; 
            margin: 0 0 20px 0; 
            font-style: italic;
            font-weight: 400;
        ">
            "${cleanQuote}"
        </p>
        
        <div style="font-size: 14px; margin-bottom: 30px;">
            ${authorHtml}
        </div>
        
        <button id="btn-close-quote" class="btn btn-primary" style="min-width: 145px; padding: 10px 24px; font-size: 14px; font-weight: 600;">Inspirierend! 🌟</button>
    `;

    modal.appendChild(content);
    document.body.appendChild(modal);

    setTimeout(() => {
        modal.style.opacity = "1";
        content.style.transform = "scale(1)";
    }, 10);

    const closeModal = () => {
        modal.style.opacity = "0";
        content.style.transform = "scale(0.9)";
        setTimeout(() => modal.remove(), 300);
    };

    content.querySelector("#btn-close-quote").addEventListener("click", closeModal);
    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });
}

function applyTheme(themeName) {
    if (themeName === "apple-silver") themeName = "apple-black";
    if (!themeName) themeName = "deep-space";
    localStorage.setItem("app_theme", themeName);
    
    const themes = ["theme-deep-space", "theme-nordic-slate", "theme-amber-warmth", "theme-apple-black", "theme-superfood-light"];
    
    // Prüfe View-Transition Support für flüssige Farbübergänge
    if (document.startViewTransition) {
        document.startViewTransition(() => {
            themes.forEach(t => document.body.classList.remove(t));
            document.body.classList.add("theme-" + themeName);
        });
    } else {
        themes.forEach(t => document.body.classList.remove(t));
        document.body.classList.add("theme-" + themeName);
    }
}

function initCardParallaxAndGlow() {
    // Registriere die Listener direkt und exklusiv auf den einzelnen Karten
    const cards = document.querySelectorAll(".card");
    cards.forEach(card => {
        let rect = null;
        
        card.addEventListener("mouseenter", () => {
            rect = card.getBoundingClientRect();
        });
        
        card.addEventListener("mousemove", (e) => {
            if (!rect) {
                rect = card.getBoundingClientRect();
            }
            
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Setze CSS Variablen für den radialen Glow
            card.style.setProperty("--mouse-x", `${x}px`);
            card.style.setProperty("--mouse-y", `${y}px`);
            
            // 3D-Kipp-Effekt
            const cardWidth = rect.width;
            const cardHeight = rect.height;
            const relativeX = (x / cardWidth) - 0.5;
            const relativeY = (y / cardHeight) - 0.5;
            
            const rotateY = relativeX * 6; // Max 3 Grad Rotation
            const rotateX = -relativeY * 6;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-2px)`;
        });
        
        card.addEventListener("mouseleave", () => {
            rect = null;
            card.style.transform = "none";
            // Setze Glow zurück außerhalb des Sichtfelds
            card.style.setProperty("--mouse-x", `-9999px`);
            card.style.setProperty("--mouse-y", `-9999px`);
        });
    });
}

// YouTube Merge Modal Logic
let currentMergeItems = [];
let mergeSubId = null;
let mergeInitialVideoId = null;

function openYtMergeModal(initialTitle, initialUrl, initialThumbnail, subId, videoId) {
    mergeSubId = subId;
    mergeInitialVideoId = videoId;
    
    const modal = document.getElementById("yt-merge-modal");
    if (!modal) return;
    
    modal.classList.remove("hidden");
    
    // Load subscription settings if available
    let copyToNas = true;
    let copyToPcloud = false;
    let copyToLocal = false;
    let nasDest = "";
    let pcloudDest = "";
    let localDest = "";
    
    if (subId && currentSettings && currentSettings.youtube_subscriptions) {
        const sub = currentSettings.youtube_subscriptions.find(s => s.id === subId);
        if (sub) {
            copyToNas = sub.copy_to_nas !== false;
            copyToPcloud = !!sub.copy_to_pcloud;
            copyToLocal = !!sub.copy_to_local;
            nasDest = sub.nas_destination_id || sub.destination_id || "";
            pcloudDest = sub.pcloud_destination_id || "";
            localDest = sub.local_destination_id || "";
        }
    }
    
    const cbNas = document.getElementById("yt-merge-option-copy-nas");
    const cbPcloud = document.getElementById("yt-merge-option-copy-pcloud");
    const cbLocal = document.getElementById("yt-merge-option-copy-local");
    
    if (cbNas) cbNas.checked = copyToNas;
    if (cbPcloud) cbPcloud.checked = copyToPcloud;
    if (cbLocal) cbLocal.checked = copyToLocal;
    
    // Trigger change event to sync visibility
    if (cbNas) cbNas.dispatchEvent(new Event("change"));
    if (cbPcloud) cbPcloud.dispatchEvent(new Event("change"));
    if (cbLocal) cbLocal.dispatchEvent(new Event("change"));
    
    const selNas = document.getElementById("yt-merge-nas-destination");
    const selPcloud = document.getElementById("yt-merge-pcloud-destination");
    const selLocal = document.getElementById("yt-merge-local-destination");
    
    if (selNas && nasDest) selNas.value = nasDest;
    if (selPcloud && pcloudDest) selPcloud.value = pcloudDest;
    if (selLocal && localDest) selLocal.value = localDest;
    
    // Set default final title (clean up part/episode indicators)
    let cleanTitle = initialTitle;
    const patterns = [
        /\bteil\s*\d+\b/i,
        /\bpart\s*\d+\b/i,
        /\bepisode\s*\d+\b/i,
        /#\s*\d+\b/i,
        /\b\d+\s*\/\s*\d+\b/i,
        /\b\d+\s*von\s*\d+\b/i,
        /\b\d+\.\s*teil\b/i,
        /\b\d+\.\s*part\b/i
    ];
    patterns.forEach(p => {
        cleanTitle = cleanTitle.replace(p, "");
    });
    cleanTitle = cleanTitle.replace(/\s*-\s*$/, "").replace(/\s+/g, " ").trim();
    
    document.getElementById("yt-merge-title").value = cleanTitle || initialTitle;
    document.getElementById("yt-merge-query").textContent = initialTitle;
    
    const listContainer = document.getElementById("yt-merge-list");
    listContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">🔍 Suche nach Teilen auf YouTube...</div>`;
    
    fetch(`/api/youtube/search-parts?title=${encodeURIComponent(initialTitle)}`)
        .then(res => res.json())
        .then(data => {
            const results = data.results || [];
            
            // Build unique list of items
            const items = [];
            
            // 1. Add our initial video
            items.push({
                id: videoId,
                title: initialTitle,
                url: initialUrl,
                thumbnail: initialThumbnail,
                checked: true,
                isInitial: true
            });
            
            // 2. Add search results, avoiding duplicates of the initial video
            results.forEach(r => {
                if (r.id !== videoId) {
                    items.push({
                        id: r.id,
                        title: r.title,
                        url: r.url,
                        thumbnail: r.thumbnail,
                        checked: false,
                        isInitial: false
                    });
                }
            });
            
            currentMergeItems = items;
            renderMergeItems();
        })
        .catch(err => {
            console.error(err);
            listContainer.innerHTML = `<div style="text-align:center; padding:20px; color:var(--danger);">Fehler bei der Suche nach Teilen.</div>`;
        });
}

function renderMergeItems() {
    const listContainer = document.getElementById("yt-merge-list");
    if (!listContainer) return;
    
    listContainer.innerHTML = "";
    
    currentMergeItems.forEach((item, index) => {
        const row = document.createElement("div");
        row.className = "merge-item-row";
        row.style.display = "flex";
        row.style.alignItems = "center";
        row.style.justifyContent = "space-between";
        row.style.gap = "10px";
        row.style.background = "rgba(255,255,255,0.02)";
        row.style.border = "1px solid var(--border-glass)";
        row.style.borderRadius = "var(--radius-sm)";
        row.style.padding = "8px 12px";
        row.style.transition = "all 0.2s ease";
        
        // Left part: Checkbox + Thumbnail + Title
        const left = document.createElement("div");
        left.style.display = "flex";
        left.style.alignItems = "center";
        left.style.gap = "10px";
        left.style.flex = "1";
        left.style.minWidth = "0";
        
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = item.checked;
        checkbox.disabled = item.isInitial; // Initial item must be checked
        checkbox.style.cursor = item.isInitial ? "default" : "pointer";
        checkbox.addEventListener("change", (e) => {
            item.checked = e.target.checked;
            const checked = currentMergeItems.filter(x => x.checked);
            const unchecked = currentMergeItems.filter(x => !x.checked);
            currentMergeItems = [...checked, ...unchecked];
            renderMergeItems();
        });
        left.appendChild(checkbox);
        
        if (item.thumbnail) {
            const img = document.createElement("img");
            img.src = item.thumbnail;
            img.style.width = "54px";
            img.style.height = "30px";
            img.style.objectFit = "cover";
            img.style.borderRadius = "2px";
            left.appendChild(img);
        } else {
            const placeholder = document.createElement("div");
            placeholder.style.width = "54px";
            placeholder.style.height = "30px";
            placeholder.style.background = "rgba(255,255,255,0.05)";
            placeholder.style.borderRadius = "2px";
            left.appendChild(placeholder);
        }
        
        const info = document.createElement("div");
        info.style.minWidth = "0";
        
        const titleSpan = document.createElement("div");
        titleSpan.style.fontWeight = "500";
        titleSpan.style.fontSize = "12px";
        titleSpan.style.whiteSpace = "nowrap";
        titleSpan.style.overflow = "hidden";
        titleSpan.style.textOverflow = "ellipsis";
        titleSpan.textContent = item.title;
        titleSpan.title = item.title;
        info.appendChild(titleSpan);
        
        if (item.isInitial) {
            const badge = document.createElement("span");
            badge.style.fontSize = "9px";
            badge.style.background = "rgba(16, 185, 129, 0.15)";
            badge.style.color = "var(--success)";
            badge.style.padding = "1px 4px";
            badge.style.borderRadius = "3px";
            badge.style.marginLeft = "0px";
            badge.style.fontWeight = "bold";
            badge.textContent = "AUSGANGS-VIDEO";
            info.appendChild(badge);
        }
        
        left.appendChild(info);
        row.appendChild(left);
        
        // Right part: Re-order controls
        const right = document.createElement("div");
        right.style.display = "flex";
        right.style.gap = "4px";
        
        const btnUp = document.createElement("button");
        btnUp.className = "btn btn-secondary btn-xs";
        btnUp.style.padding = "2px 6px";
        btnUp.innerHTML = "▲";
        btnUp.disabled = index === 0;
        btnUp.addEventListener("click", () => {
            // Swap with previous
            const temp = currentMergeItems[index - 1];
            currentMergeItems[index - 1] = currentMergeItems[index];
            currentMergeItems[index] = temp;
            renderMergeItems();
        });
        
        const btnDown = document.createElement("button");
        btnDown.className = "btn btn-secondary btn-xs";
        btnDown.style.padding = "2px 6px";
        btnDown.innerHTML = "▼";
        btnDown.disabled = index === currentMergeItems.length - 1;
        btnDown.addEventListener("click", () => {
            // Swap with next
            const temp = currentMergeItems[index + 1];
            currentMergeItems[index + 1] = currentMergeItems[index];
            currentMergeItems[index] = temp;
            renderMergeItems();
        });
        
        right.appendChild(btnUp);
        right.appendChild(btnDown);
        row.appendChild(right);
        
        listContainer.appendChild(row);
    });
}

function closeYtMergeModal() {
    document.getElementById("yt-merge-modal").classList.add("hidden");
    currentMergeItems = [];
    mergeSubId = null;
    mergeInitialVideoId = null;
}

// Hook up events
document.addEventListener("DOMContentLoaded", () => {
    const btnClose = document.getElementById("btn-close-yt-merge");
    const btnCancel = document.getElementById("btn-cancel-yt-merge");
    const btnStart = document.getElementById("btn-start-yt-merge");
    
    if (btnClose) btnClose.addEventListener("click", closeYtMergeModal);
    if (btnCancel) btnCancel.addEventListener("click", closeYtMergeModal);
    
    if (btnStart) {
        btnStart.addEventListener("click", async () => {
            const finalTitleInput = document.getElementById("yt-merge-title");
            const finalTitle = finalTitleInput ? finalTitleInput.value.trim() : "";
            
            if (!finalTitle) {
                alert("Bitte gib einen Dateinamen an!");
                return;
            }
            
            const selectedItems = currentMergeItems.filter(item => item.checked);
            if (selectedItems.length === 0) {
                alert("Bitte wähle mindestens ein Video aus!");
                return;
            }
            
            const urls = selectedItems.map(item => item.url);
            const videoIdsToRemove = selectedItems.map(item => item.id);
            
            btnStart.disabled = true;
            btnStart.textContent = "⌛ Starte Merge...";
            
            const copyToNas = document.getElementById("yt-merge-option-copy-nas")?.checked ?? false;
            const copyToPcloud = document.getElementById("yt-merge-option-copy-pcloud")?.checked ?? false;
            const copyToLocal = document.getElementById("yt-merge-option-copy-local")?.checked ?? false;
            
            const nasDest = document.getElementById("yt-merge-nas-destination")?.value || "";
            const pcloudDest = document.getElementById("yt-merge-pcloud-destination")?.value || "";
            const localDest = document.getElementById("yt-merge-local-destination")?.value || "";
            
            try {
                const res = await fetch("/api/youtube/merge", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        urls: urls,
                        title: finalTitle,
                        subscription_id: mergeSubId,
                        video_ids_to_remove: videoIdsToRemove,
                        thumbnail: selectedItems[0].thumbnail || "",
                        copy_to_nas: copyToNas,
                        copy_to_pcloud: copyToPcloud,
                        copy_to_local: copyToLocal,
                        nas_destination_id: nasDest,
                        pcloud_destination_id: pcloudDest,
                        local_destination_id: localDest
                    })
                });
                
                if (res.ok) {
                    appendConsoleLog(`[System]: Merge-Job für "${finalTitle}" mit ${urls.length} Teilen gestartet.`);
                    alert("Merge-Job im Hintergrund gestartet!");
                    closeYtMergeModal();
                    
                    // Remove processed videos from UI
                    loadSubscriptions();
                } else {
                    const data = await res.json();
                    alert(`Fehler beim Starten: ${data.error || 'Serverfehler'}`);
                }
            } catch (err) {
                console.error(err);
                alert("Netzwerkfehler beim Starten des Zusammenfügens.");
            } finally {
                btnStart.disabled = false;
                btnStart.innerHTML = "🚀 Teile zusammenfügen & laden";
            }
        });
    }
});

// Duplicate Compare Modal Logic
let activeDuplicateInfo = null;

function openDuplicateCompareModal(existingPath, existingFilename, newFilename, badgeId) {
    const modal = document.getElementById("duplicate-compare-modal");
    if (!modal) return;
    
    modal.classList.remove("hidden");
    
    // Reset fields to loading state
    document.getElementById("dup-new-name").textContent = newFilename;
    document.getElementById("dup-new-res").textContent = "Lade...";
    document.getElementById("dup-new-size").textContent = "Lade...";
    document.getElementById("dup-new-vcodec").textContent = "Lade...";
    document.getElementById("dup-new-acodec").textContent = "Lade...";
    document.getElementById("dup-new-bitrate").textContent = "Lade...";
    document.getElementById("dup-new-duration").textContent = "Lade...";
    
    document.getElementById("dup-exist-name").textContent = existingFilename;
    document.getElementById("dup-exist-res").textContent = "Lade...";
    document.getElementById("dup-exist-size").textContent = "Lade...";
    document.getElementById("dup-exist-vcodec").textContent = "Lade...";
    document.getElementById("dup-exist-acodec").textContent = "Lade...";
    document.getElementById("dup-exist-bitrate").textContent = "Lade...";
    document.getElementById("dup-exist-duration").textContent = "Lade...";
    
    const projName = typeof activeProject === "string" ? activeProject : "";
    const newPath = currentSettings.inbox_dir + "/" + (projName ? projName + "/" : "") + newFilename;
    
    activeDuplicateInfo = {
        new_path: newPath,
        existing_path: existingPath,
        badge_id: badgeId
    };
    
    fetch(`/api/media/compare-files?new_path=${encodeURIComponent(newPath)}&existing_path=${encodeURIComponent(existingPath)}`)
        .then(res => {
            if (!res.ok) throw new Error("HTTP Fehler");
            return res.json();
        })
        .then(data => {
            const n = data.new_file;
            const e = data.existing_file;
            
            document.getElementById("dup-new-res").textContent = n.resolution;
            document.getElementById("dup-new-size").textContent = n.size_readable;
            document.getElementById("dup-new-vcodec").textContent = n.video_codec;
            document.getElementById("dup-new-acodec").textContent = n.audio_codec;
            document.getElementById("dup-new-bitrate").textContent = n.bitrate_kbps;
            document.getElementById("dup-new-duration").textContent = n.duration_str;
            
            document.getElementById("dup-exist-res").textContent = e.resolution;
            document.getElementById("dup-exist-size").textContent = e.size_readable;
            document.getElementById("dup-exist-vcodec").textContent = e.video_codec;
            document.getElementById("dup-exist-acodec").textContent = e.audio_codec;
            document.getElementById("dup-exist-bitrate").textContent = e.bitrate_kbps;
            document.getElementById("dup-exist-duration").textContent = e.duration_str;
        })
        .catch(err => {
            console.error("Comparison error:", err);
            ["new", "exist"].forEach(prefix => {
                document.getElementById(`dup-${prefix}-res`).textContent = "Fehler";
                document.getElementById(`dup-${prefix}-size`).textContent = "Fehler beim Laden";
            });
        });
}

function closeDuplicateCompareModal() {
    document.getElementById("duplicate-compare-modal").classList.add("hidden");
    activeDuplicateInfo = null;
}

// Global click event delegation for duplicate badges
document.addEventListener("click", (e) => {
    const badge = e.target.closest(".duplicate-badge");
    if (badge) {
        const existingPath = badge.getAttribute("data-existing-path");
        const existingFilename = badge.getAttribute("data-existing-filename");
        const newFile = badge.getAttribute("data-new-file");
        const badgeId = badge.getAttribute("data-badge-id");
        
        if (existingPath && newFile) {
            openDuplicateCompareModal(existingPath, existingFilename, newFile, badgeId);
        }
    }
});

// Hook up duplicate modal events
document.addEventListener("DOMContentLoaded", () => {
    const btnClose = document.getElementById("btn-close-dup-compare");
    const btnKeep = document.getElementById("btn-dup-keep-both");
    const btnUpgrade = document.getElementById("btn-dup-upgrade");
    
    if (btnClose) btnClose.addEventListener("click", closeDuplicateCompareModal);
    if (btnKeep) btnKeep.addEventListener("click", closeDuplicateCompareModal);
    
    if (btnUpgrade) {
        btnUpgrade.addEventListener("click", async () => {
            if (!activeDuplicateInfo) return;
            
            if (confirm("Möchtest du die existierende Datei auf dem NAS wirklich löschen? Dieser Schritt kann nicht rückgängig gemacht werden.")) {
                btnUpgrade.disabled = true;
                btnUpgrade.textContent = "⌛ Führe Upgrade aus...";
                
                try {
                    const res = await fetch("/api/media/resolve-duplicate", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            action: "upgrade",
                            new_path: activeDuplicateInfo.new_path,
                            existing_path: activeDuplicateInfo.existing_path
                        })
                    });
                    
                    if (res.ok) {
                        appendConsoleLog(`[System]: Vorhandene Datei auf NAS gelöscht: ${activeDuplicateInfo.existing_path}`);
                        alert("Upgrade erfolgreich vorbereitet! Die alte Datei auf dem NAS wurde gelöscht. Klicke jetzt auf 'Zuweisung starten', um das neue Video dorthin zu kopieren.");
                        
                        const badgeContainer = document.getElementById(activeDuplicateInfo.badge_id);
                        if (badgeContainer) {
                            badgeContainer.innerHTML = "";
                        }
                        
                        closeDuplicateCompareModal();
                    } else {
                        const data = await res.json();
                        alert(`Fehler beim Upgrade: ${data.error || 'Serverfehler'}`);
                    }
                } catch (err) {
                    console.error(err);
                    alert("Netzwerkfehler beim Ausführen des Upgrades.");
                } finally {
                    btnUpgrade.disabled = false;
                    btnUpgrade.innerHTML = "🗑️ Vorhandene löschen & Upgrade";
                }
            }
        });
    }
});

// ==========================================================================
// WELCOME DASHBOARD DATA BINDING & INTERACTION
// ==========================================================================
async function updateHomepageData(statusData) {
    if (!statusData) return;

    // 0. Folder Size Warnings (Feature 5)
    const warningBanner = document.getElementById("folder-size-warning");
    const warningText = document.getElementById("folder-size-warning-text");
    if (warningBanner && warningText) {
        let warnings = [];
        const inboxSize = statusData.inbox_size_gb || 0;
        const outboxSize = statusData.outbox_size_gb || 0;
        const threshInbox = parseFloat(document.getElementById("set-monitor-inbox-gb")?.value) || 50.0;
        const threshOutbox = parseFloat(document.getElementById("set-monitor-outbox-gb")?.value) || 50.0;
        
        if (inboxSize > threshInbox) {
            warnings.push(`Der Inbox-Ordner belegt ${inboxSize.toFixed(1)} GB (Schwelle: ${threshInbox} GB).`);
        }
        if (outboxSize > threshOutbox) {
            warnings.push(`Der Outbox-Ordner belegt ${outboxSize.toFixed(1)} GB (Schwelle: ${threshOutbox} GB). Denke daran, verarbeitete Projekte zu löschen.`);
        }
        
        if (warnings.length > 0) {
            warningText.innerHTML = warnings.join("<br>");
            warningBanner.classList.remove("hidden");
        } else {
            warningBanner.classList.add("hidden");
        }
    }

    // 1. (Inbox-Status wird jetzt von der Smart Inbox abgedeckt)

    // 2. NAS Badge
    const nasBadge = document.getElementById("hero-nas-badge");
    if (nasBadge) {
        nasBadge.className = "status-badge";
        if (statusData.nas_status === "connected") {
            nasBadge.textContent = "Verbunden";
            nasBadge.classList.add("online");
        } else if (statusData.nas_status === "available_not_mounted") {
            nasBadge.textContent = "Bereit (Nicht gemountet)";
            nasBadge.classList.add("warning");
        } else {
            nasBadge.textContent = "Offline";
            nasBadge.classList.add("offline");
        }
    }

    // 3. StreamFab Badge
    const sfBadge = document.getElementById("hero-streamfab-badge");
    if (sfBadge) {
        if (statusData.streamfab_downloads && statusData.streamfab_downloads.length > 0) {
            sfBadge.textContent = `${statusData.streamfab_downloads.length} Datei(en)`;
            sfBadge.className = "status-badge warning";
        } else {
            sfBadge.textContent = "Leer";
            sfBadge.className = "status-badge neutral";
        }
    }

    // Helper to format bytes
    const formatBytes = (bytes, decimals = 2) => {
        if (!bytes || bytes === 0) return "0 GB";
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
    };

    // 4. Fetch Stats for NAS capacity and space savings
    try {
        const statsRes = await fetch("/api/stats");
        if (statsRes.ok) {
            const statsData = await statsRes.json();

            // NAS storage
            const nasInfo = statsData.nas;
            const progress = document.getElementById("hero-nas-progress");
            const usageText = document.getElementById("hero-nas-usage-text");
            const heroStorageLabel = document.getElementById("hero-storage-label");
            if (heroStorageLabel && nasInfo) heroStorageLabel.textContent = (nasInfo.name || "Speicher") + " Speicherbelegung:";
            if (nasInfo && nasInfo.available && nasInfo.usage_unreliable) {
                if (progress) progress.style.width = "0%";
                if (usageText) {
                    usageText.textContent = `${formatBytes(nasInfo.free)} frei (Belegung bei Netzlaufwerk nicht ermittelbar)`;
                }
            } else if (nasInfo && nasInfo.available) {
                const pct = nasInfo.used_percent || 0;
                if (progress) {
                    progress.style.width = `${pct}%`;
                    progress.className = "progress-bar";
                    if (pct >= 90) {
                        progress.style.background = "var(--danger, #ef4444)";
                    } else if (pct >= 75) {
                        progress.style.background = "var(--warning, #f59e0b)";
                    } else {
                        progress.style.background = "var(--accent, #3b82f6)";
                    }
                }
                if (usageText) {
                    usageText.textContent = `${formatBytes(nasInfo.used)} von ${formatBytes(nasInfo.total)} belegt (${formatBytes(nasInfo.free)} frei)`;
                }
            } else {
                if (progress) progress.style.width = "0%";
                if (usageText) {
                    usageText.textContent = nasInfo && nasInfo.error ? nasInfo.error : "NAS nicht verfügbar";
                }
            }

            // Savings
            const savedSpace = document.getElementById("hero-saved-space");
            const convertedText = document.getElementById("hero-converted-files-text");
            if (statsData.stats) {
                if (savedSpace) {
                    savedSpace.textContent = formatBytes(statsData.stats.saved_bytes);
                }
                if (convertedText) {
                    convertedText.textContent = `${statsData.stats.total_files} Konvertierung(en) abgeschlossen`;
                }
            }
        }
    } catch (e) {
        console.error("Error fetching stats for homepage:", e);
    }

    // 5. Fetch YouTube Subscriptions Count
    try {
        const subsRes = await fetch("/api/youtube/subscriptions");
        if (subsRes.ok) {
            const subsData = await subsRes.json();
            const subs = subsData.subscriptions || [];
            const abosText = document.getElementById("hero-abos-status-text");
            if (abosText) {
                const pendingCount = subs.reduce((acc, sub) => acc + (sub.pending_videos ? sub.pending_videos.length : 0), 0);
                if (pendingCount > 0) {
                    abosText.textContent = `${subs.length} Abo(s) aktiv • ${pendingCount} Video(s) bereit`;
                } else {
                    abosText.textContent = `${subs.length} Abo(s) aktiv • Alles aktuell`;
                }
            }
        }
    } catch (e) {
        console.error("Error fetching subscriptions for homepage:", e);
    }

    // 6. Fetch Smart Inbox Suggestions
    try {
        const analyzeRes = await fetch("/api/inbox/analyze");
        const cardSmartInbox = document.getElementById("card-smart-inbox");
        const smartInboxList = document.getElementById("smart-inbox-list");
        if (analyzeRes.ok && cardSmartInbox && smartInboxList) {
            const analyzeData = await analyzeRes.json();
            const suggestions = analyzeData.suggestions || [];
            if (suggestions.length > 0) {
                cardSmartInbox.style.display = "block";
                smartInboxList.innerHTML = "";
                suggestions.forEach(item => {
                    let typeBadge = "";
                    let badgeColor = "";
                    if (item.media_type === "movie") {
                        typeBadge = "🎬 Film";
                        badgeColor = "background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);";
                    } else if (item.media_type === "tv") {
                        typeBadge = "📺 Serie";
                        badgeColor = "background: rgba(139, 92, 246, 0.15); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.3);";
                    } else if (item.media_type === "doku") {
                        typeBadge = "🌿 Doku";
                        badgeColor = "background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);";
                    } else if (item.media_type === "anime") {
                        typeBadge = "🌸 Anime";
                        badgeColor = "background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);";
                    }

                    const reasonsHtml = (item.reasons || []).map(r => `<span style="font-size: 0.8em; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.05); color: var(--text-muted);">${escapeHTML(r)}</span>`).join(" ");

                    const isProcessing = activeProjectsProcessing && activeProjectsProcessing.has(item.project);
                    const borderStyle = isProcessing ? "border: 1px solid rgba(0, 229, 255, 0.3);" : "border: 1px solid var(--border-light);";
                    const bgStyle = isProcessing ? "background: rgba(0, 229, 255, 0.03);" : "background: rgba(255,255,255,0.02);";

                    const itemDiv = document.createElement("div");
                    itemDiv.className = "smart-inbox-item";
                    itemDiv.setAttribute("data-project", item.project);
                    itemDiv.style.cssText = `${bgStyle} ${borderStyle} border-radius: 8px; padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px; transition: all 0.2s ease;`;
                    itemDiv.innerHTML = `
                        <div style="display: flex; flex-direction: column; gap: 6px; flex-grow: 1;">
                            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                <strong style="font-size: 1rem; color: var(--text-main);">${escapeHTML(item.project)}</strong>
                                <span style="font-size: 0.75em; padding: 2px 8px; border-radius: 12px; font-weight: 500; ${badgeColor}">${typeBadge}</span>
                                <span style="font-size: 0.8em; color: var(--text-muted);">${item.video_count} Datei(en)</span>
                            </div>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                                ${reasonsHtml}
                            </div>
                        </div>
                        <div>
                            <button class="btn btn-select-smart"
                                    data-media-type="${escapeHTML(item.media_type || "")}"
                                    data-suggested-query="${escapeHTML(item.suggested_query || "")}"></button>
                        </div>
                    `;

                    const btn = itemDiv.querySelector(".btn-select-smart");
                    configureSmartInboxButton(btn, item.project, isProcessing);
                    smartInboxList.appendChild(itemDiv);
                });
            } else {
                cardSmartInbox.style.display = "none";
            }
        }
    } catch (e) {
        console.error("Error fetching smart inbox suggestions:", e);
    }
}

function handleSmartInboxClick(projectName, mediaType, suggestionTitle) {
    selectProject(projectName);
    
    setTimeout(() => {
        currentProjectSuggestedQuery = suggestionTitle;
        currentProjectIsDoku = (mediaType === 'doku');
        
        if (mediaType === 'movie' || mediaType === 'doku') {
            const card = document.getElementById("mode-movie");
            if (card) card.click();
        } else {
            const card = document.getElementById("mode-series");
            if (card) {
                card.click();
                
                setTimeout(() => {
                    const animeCheck = document.getElementById("series-is-anime");
                    if (animeCheck) {
                        animeCheck.checked = (mediaType === 'anime');
                        animeCheck.dispatchEvent(new Event('change'));
                    }
                }, 50);
            }
        }
    }, 100);
}

function handleHeroYtDownload() {
    const heroInput = document.getElementById("hero-yt-url");
    if (!heroInput) return;
    const url = heroInput.value.trim();
    if (!url) {
        alert("Bitte eine gültige YouTube-/Mediathek-URL eingeben!");
        return;
    }
    
    // Copy to downloader input
    const ytInput = document.getElementById("yt-url");
    if (ytInput) {
        ytInput.value = url;
    }
    
    // Clear hero input
    heroInput.value = "";
    
    // Navigate to YouTube view
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    const ytView = document.getElementById("view-youtube");
    if (ytView) {
        ytView.classList.remove("hidden");
        ytView.classList.add("active");
    }
    // Remove active sidebar project selections
    document.querySelectorAll(".project-item").forEach(el => el.classList.remove("active"));
    
    scrollToDetailTop();
    
    // Call analyseYtLink()
    analyseYtLink();
}




async function populateLocalProfilesDropdown() {
    const select = document.getElementById("series-local-profile-select");
    if (!select) return;
    
    try {
        const res = await fetch("/api/profiles");
        const data = await res.json();
        
        allLocalProfiles = [];
        if (data.profiles && data.profiles.length > 0) {
            // Sort by show name
            data.profiles.sort((a, b) => {
                const nameA = a.data.show_name || a.filename;
                const nameB = b.data.show_name || b.filename;
                return nameA.localeCompare(nameB);
            });
            
            data.profiles.forEach(p => {
                const displayName = p.data.show_name || p.filename.replace(".json", "");
                p.data.show_name = displayName;
                p.data.filename = p.filename;
                allLocalProfiles.push(p.data);
            });
        }
        
        renderLocalProfilesDropdown(allLocalProfiles);
    } catch (e) {
        console.error("Fehler beim Laden lokaler Profile:", e);
    }
}

function renderLocalProfilesDropdown(profiles) {
    const select = document.getElementById("series-local-profile-select");
    if (!select) return;
    
    let html = "<option value=\"\">-- Lokales Profil wählen --</option>";
    profiles.forEach(p => {
        html += `<option value='${JSON.stringify(p).replace(/'/g, "&#39;")}' data-name="${p.show_name.toLowerCase()}">${p.show_name}</option>`;
    });
    select.innerHTML = html;
}

document.addEventListener("DOMContentLoaded", () => {
    populateLocalProfilesDropdown();
    
    const select = document.getElementById("series-local-profile-select");
    if (select) {
        select.addEventListener("change", (e) => {
            if (!e.target.value) return;
            try {
                const profileData = JSON.parse(e.target.value);
                const showObj = {
                    id: profileData.show_id,
                    provider: profileData.provider || "tmdb",
                    name: profileData.show_name || "",
                    year: "",
                    plot: profileData.plot || "",
                    poster: profileData.poster || ""
                };
                
                const resultsContainer = document.getElementById("series-search-results");
                if (resultsContainer) resultsContainer.innerHTML = "";
                
                selectShow(showObj);
            } catch(err) {
                console.error("Fehler beim Profil-Auswählen", err);
            }
        });
    }
    
    // Fuzzy-Suche für Profile
    const searchInput = document.getElementById("series-local-profile-search");
    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query) {
                renderLocalProfilesDropdown(allLocalProfiles);
                return;
            }
            
            // Fuzzy match helper: true if all query characters appear in string in relative order
            const fuzzyMatch = (str, q) => {
                str = str.toLowerCase();
                if (str.includes(q)) return true;
                let qIdx = 0;
                for (let i = 0; i < str.length; i++) {
                    if (str[i] === q[qIdx]) {
                        qIdx++;
                    }
                    if (qIdx === q.length) return true;
                }
                return false;
            };
            
            const filtered = allLocalProfiles.filter(p => {
                const displayName = p.show_name || "";
                return fuzzyMatch(displayName, query);
            });
            
            renderLocalProfilesDropdown(filtered);
        });
    }
});

// Conversion Intelligence Globals & Functions
let globalRecommendations = null;

async function loadConversionRecommendations() {
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

function renderIntelligenceDashboard(data) {
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

function triggerQualityHintUpdates() {
    if (!globalRecommendations) return;
    
    const recs = globalRecommendations.recommendations || {};
    
    // Movie context check
    const contextMovie = document.getElementById("context-movie");
    if (contextMovie && !contextMovie.classList.contains("hidden")) {
        const slider = document.getElementById("movie-quality-slider");
        const hintEl = document.getElementById("movie-quality-hint");
        const destSelect = document.getElementById("movie-nas-destination");
        
        if (slider && hintEl) {
            const val = parseInt(slider.value);
            const isDoku = destSelect && destSelect.value.toLowerCase().includes("doku");
            const mediaType = isDoku ? "doku" : "movie";
            
            updateHintElement(hintEl, val, recs[mediaType]);
        }
    }
    
    // Series context check
    const contextSeries = document.getElementById("context-series");
    if (contextSeries && !contextSeries.classList.contains("hidden")) {
        const slider = document.getElementById("series-quality-slider");
        const hintEl = document.getElementById("series-quality-hint");
        const isAnime = document.getElementById("series-is-anime")?.checked || false;
        const destSelect = document.getElementById("series-nas-destination");
        
        if (slider && hintEl) {
            const val = parseInt(slider.value);
            let mediaType = "live_action";
            if (isAnime) mediaType = "anime";
            else if (destSelect && destSelect.value.toLowerCase().includes("doku")) mediaType = "doku";
            
            updateHintElement(hintEl, val, recs[mediaType]);
        }
    }
}

function updateHintElement(el, currentVal, recInfo) {
    if (!recInfo) {
        el.textContent = "💡 Noch keine historischen Daten für diesen Inhaltstyp vorhanden. Standardempfehlung ist CRF 60.";
        el.classList.remove("hidden");
        return;
    }
    
    const optimal = recInfo.optimal_quality;
    if (currentVal === optimal) {
        el.textContent = `✅ Optimaler Wert für diesen Inhaltstyp basierend auf deiner Historie (CRF ${optimal}).`;
    } else if (currentVal > optimal) {
        el.textContent = `💡 Deine Historie zeigt, dass dieser Inhaltstyp auch mit CRF ${optimal} ohne sichtbaren Qualitätsverlust gut komprimiert wird (spart mehr Platz).`;
    } else {
        el.textContent = `⚠️ Dieser Wert liegt unter dem empfohlenen Optimum von CRF ${optimal}. Es könnte zu sichtbaren Kompressionsartefakten kommen.`;
    }
    el.classList.remove("hidden");
}

// ==========================================================================
// Feature 3: NAS Bibliotheks-Check (Health Dashboard)
// ==========================================================================
let healthPollTimer = null;

const HEALTH_SEVERITY = {
    critical: { label: "Kritisch", icon: "⛔", color: "#ef4444" },
    warning:  { label: "Warnung",  icon: "⚠️", color: "#f59e0b" },
    info:     { label: "Hinweis",  icon: "ℹ️", color: "#3b82f6" },
};

function initHealthDashboard() {
    const btn = document.getElementById("btn-health-scan");
    if (btn) {
        btn.addEventListener("click", startHealthScan);
    }
    const cancelBtn = document.getElementById("btn-health-cancel");
    if (cancelBtn) {
        cancelBtn.addEventListener("click", cancelHealthScan);
    }
    // Lade Kategorien dynamisch
    loadHealthCategories();
    // Vorhandenes (gecachtes) Ergebnis laden
    pollHealthStatus(false);
}

async function loadHealthCategories() {
    const container = document.getElementById("health-categories-container");
    if (!container) return;
    try {
        const res = await fetch("/api/settings");
        if (!res.ok) {
            container.innerHTML = `<span style="font-size:0.85em; color:#ef4444; font-style:italic;">Fehler beim Laden der Kategorien.</span>`;
            return;
        }
        const settings = await res.json();
        const categories = settings.sync_categories || [];
        if (categories.length === 0) {
            container.innerHTML = `<span style="font-size:0.85em; color:var(--text-muted); font-style:italic;">Keine Kategorien konfiguriert.</span>`;
            return;
        }
        
        container.innerHTML = categories.map(cat => {
            const id = cat.id || "";
            const name = cat.name || "Unbenannt";
            return `
                <label class="checkbox-container" style="font-size:0.85em; color:var(--text-muted); margin:0;">
                    <input type="checkbox" class="health-category-checkbox" value="${escapeHTML(id)}" checked>
                    <span class="checkmark"></span> ${escapeHTML(name)}
                </label>
            `.trim();
        }).join("");
    } catch (e) {
        console.error("Kategorien für Health Scan konnten nicht geladen werden:", e);
        container.innerHTML = `<span style="font-size:0.85em; color:#ef4444; font-style:italic;">Fehler beim Laden der Kategorien.</span>`;
    }
}

async function startHealthScan() {
    const btn = document.getElementById("btn-health-scan");
    const deepCheck = document.getElementById("health-option-deep");
    const deep = deepCheck ? deepCheck.checked : false;

    // Ausgewählte Kategorien auslesen
    const checkboxes = document.querySelectorAll(".health-category-checkbox");
    const categoryIds = [];
    checkboxes.forEach(cb => {
        if (cb.checked) {
            categoryIds.push(cb.value);
        }
    });

    if (checkboxes.length > 0 && categoryIds.length === 0) {
        setHealthStatusText("Bitte mindestens eine Kategorie auswählen.");
        return;
    }

    const payload = { deep: deep };
    if (checkboxes.length > 0) {
        payload.category_ids = categoryIds;
    }

    try {
        const res = await fetch("/api/nas/health-scan", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
            setHealthStatusText(data.error || data.message || `Fehler ${res.status}: Scan konnte nicht gestartet werden.`);
            if (btn) btn.disabled = false;
            return;
        }
        if (data.started === false) {
            // Läuft bereits -> einfach weiterpollen
            setHealthStatusText(data.message || "Ein Scan läuft bereits.");
        }
        if (btn) btn.disabled = true;
        pollHealthStatus(true);
    } catch (e) {
        console.error("Health-Scan konnte nicht gestartet werden:", e);
        setHealthStatusText("Fehler: Scan konnte nicht gestartet werden.");
    }
}

async function cancelHealthScan() {
    const cancelBtn = document.getElementById("btn-health-cancel");
    if (cancelBtn) {
        cancelBtn.disabled = true;
        cancelBtn.textContent = "Abbruch...";
    }
    try {
        const res = await fetch("/api/nas/health-cancel", { method: "POST" });
        const data = await res.json();
        if (data.stopped) {
            setHealthStatusText("Abbruch angefordert...");
        }
    } catch (e) {
        console.error("Health-Scan konnte nicht abgebrochen werden:", e);
    }
}

function setHealthStatusText(txt) {
    const el = document.getElementById("health-scan-status");
    if (el) el.textContent = txt;
}

async function pollHealthStatus(keepPolling) {
    try {
        const res = await fetch("/api/nas/health-status");
        if (!res.ok) return;
        const data = await res.json();
        renderHealthStatus(data);

        const running = data.status === "running";
        const btn = document.getElementById("btn-health-scan");
        const cancelBtn = document.getElementById("btn-health-cancel");
        if (btn) btn.disabled = running;
        
        if (cancelBtn) {
            cancelBtn.style.display = running ? "inline-block" : "none";
            if (!running) {
                cancelBtn.disabled = false;
                cancelBtn.textContent = "⏹️ Abbrechen";
            }
        }

        if (running) {
            // Weiterpollen, solange der Scan läuft
            clearTimeout(healthPollTimer);
            healthPollTimer = setTimeout(() => pollHealthStatus(true), 2000);
        }
    } catch (e) {
        console.error("Health-Status konnte nicht geladen werden:", e);
    }
}

function renderHealthStatus(data) {
    const statusEl = document.getElementById("health-scan-status");
    const progWrap = document.getElementById("health-progress-wrap");
    const progBar = document.getElementById("health-progress-bar");
    const statsEl = document.getElementById("health-stats");
    const summaryEl = document.getElementById("health-summary");
    const issuesEl = document.getElementById("health-issues");
    if (!statusEl || !summaryEl || !issuesEl) return;

    // 1. Zustand sichern (geöffnete Gruppen und Scrollposition)
    const openSeverities = [];
    const hadDetails = issuesEl.querySelector("details") !== null;
    if (hadDetails) {
        issuesEl.querySelectorAll("details").forEach(d => {
            if (d.open) {
                const sev = d.getAttribute("data-sev");
                if (sev) openSeverities.push(sev);
            }
        });
    }
    const scrollTop = window.scrollY || document.documentElement.scrollTop;

    // Statuszeile + Fortschritt
    if (data.status === "running") {
        statusEl.textContent = data.message || "Scan läuft...";
        if (progWrap) progWrap.style.display = "block";
        if (progBar) progBar.style.width = `${data.progress || 0}%`;
        if (statsEl) statsEl.style.display = "none";
    } else {
        if (progWrap) progWrap.style.display = "none";
        if (data.status === "error") {
            statusEl.textContent = `Fehler: ${data.message || data.error || "Unbekannt"}`;
            if (statsEl) statsEl.style.display = "none";
        } else if (data.status === "cancelled") {
            const when = data.finished_at ? new Date(data.finished_at * 1000).toLocaleString("de-DE") : "";
            statusEl.textContent = `Abgebrochen: ${data.message || "Vom Benutzer abgebrochen."}` + (when ? ` (${when})` : "");
            if (statsEl) statsEl.style.display = "none";
        } else if (data.status === "done" || (data.issues && data.issues.length >= 0 && data.finished_at)) {
            const when = data.finished_at ? new Date(data.finished_at * 1000).toLocaleString("de-DE") : "";
            statusEl.textContent = data.message + (when ? ` (zuletzt: ${when})` : "");
            
            if (statsEl && data.stats) {
                const s = data.stats;
                statsEl.innerHTML = `⚡ Cache-Statistik: 
                    <span style="color:var(--accent); font-weight:500;">${s.cache_hits || 0}</span> Treffer, 
                    <span style="color:#f59e0b; font-weight:500;">${s.cache_miss_modified || 0}</span> wegen Änderungen neu geprüft, 
                    <span style="color:#ef4444; font-weight:500;">${s.cache_miss_known_issues || 0}</span> wegen bekannter Fehler neu geprüft, 
                    <span style="color:#3b82f6; font-weight:500;">${s.cache_miss_new || 0}</span> neu erfasst.`;
                statsEl.style.display = "block";
            } else if (statsEl) {
                statsEl.style.display = "none";
            }
        } else {
            statusEl.textContent = "Noch kein Scan durchgeführt.";
            if (statsEl) statsEl.style.display = "none";
        }
    }

    // Summary-Badges
    const summary = data.summary || { critical: 0, warning: 0, info: 0 };
    const hasResult = (data.issues && data.finished_at) || data.status === "done";
    if (hasResult) {
        summaryEl.innerHTML = ["critical", "warning", "info"].map(sev => {
            const m = HEALTH_SEVERITY[sev];
            return `<span style="font-size:0.85em; padding:4px 10px; border-radius:12px; background:${m.color}22; color:${m.color}; border:1px solid ${m.color}55;">
                        ${m.icon} ${summary[sev] || 0} ${m.label}
                    </span>`;
        }).join("");
    } else {
        summaryEl.innerHTML = "";
    }

    // Issues gruppiert nach Schwere
    if (data.issues && data.issues.length > 0) {
        const order = ["critical", "warning", "info"];
        const grouped = { critical: [], warning: [], info: [] };
        data.issues.forEach(it => { (grouped[it.severity] || grouped.info).push(it); });

        let html = "";
        order.forEach(sev => {
            const list = grouped[sev];
            if (!list.length) return;
            const m = HEALTH_SEVERITY[sev];
            html += `<details data-sev="${sev}" ${sev === "critical" ? "open" : ""} style="border:1px solid var(--border-light); border-radius:8px; padding:8px 12px;">
                        <summary style="cursor:pointer; color:${m.color}; font-weight:500;">${m.icon} ${m.label} (${list.length})</summary>
                        <div style="margin-top:8px; display:flex; flex-direction:column; gap:6px;">`;
            list.forEach(it => {
                let fixBtns = "";
                if (it.type === "nested_duplicate") {
                    fixBtns = `<button class="btn btn-secondary btn-sm health-fix-flatten" data-path="${escapeHTML(it.path)}" title="Unterordner auflösen">🔧 Auflösen</button>`;
                } else if (it.type === "name_mismatch" || it.type === "bad_folder_name") {
                    fixBtns = `<button class="btn btn-secondary btn-sm health-fix-rename" data-path="${escapeHTML(it.path)}" data-type="${escapeHTML(it.type)}" title="Umbenennen">🔧 Umbenennen</button>`;
                }
                html += `<div style="display:flex; align-items:center; justify-content:space-between; gap:10px; font-size:0.9em; padding:4px 0; border-top:1px solid rgba(255,255,255,0.04);">
                            <span>${escapeHTML(it.category)} · ${escapeHTML(it.message)}</span>
                            <span style="display:flex; gap:6px; white-space:nowrap;">
                                ${fixBtns}
                                <button class="btn btn-secondary btn-sm health-open-folder" data-path="${escapeHTML(it.path)}">📂 Öffnen</button>
                                <button class="btn btn-secondary btn-sm finding-ignore" data-key="${escapeHTML(it.key || "")}" title="Diesen Befund dauerhaft ausblenden">🚫 Ignorieren</button>
                            </span>
                         </div>`;
            });
            html += `</div></details>`;
        });
        html += renderIgnoredFooter(data.ignored_count);
        issuesEl.innerHTML = html;

        // 2. Zustand wiederherstellen
        if (hadDetails) {
            issuesEl.querySelectorAll("details").forEach(d => {
                const sev = d.getAttribute("data-sev");
                d.open = openSeverities.includes(sev);
            });
        }

        issuesEl.querySelectorAll(".health-open-folder").forEach(b => {
            b.addEventListener("click", () => {
                const p = b.getAttribute("data-path");
                fetch(`/api/system-open-folder?path=${encodeURIComponent(p)}`).catch(() => {});
            });
        });

        issuesEl.querySelectorAll(".health-fix-flatten").forEach(b => {
            b.addEventListener("click", async () => {
                const p = b.getAttribute("data-path");
                if (!confirm(`Verschachtelung auflösen?\n\nInhalt des Unterordners wird eine Ebene nach oben verschoben.`)) return;
                b.disabled = true;
                try {
                    const res = await fetch("/api/nas/health-fix", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ action: "flatten", path: p }),
                    });
                    const data = await res.json();
                    if (data.ok) { pollHealthStatus(false); }
                    else { alert(data.message || "Fehler"); b.disabled = false; }
                } catch (e) { alert("Fehler: " + e); b.disabled = false; }
            });
        });

        issuesEl.querySelectorAll(".health-fix-rename").forEach(b => {
            b.addEventListener("click", async () => {
                const p = b.getAttribute("data-path");
                const issueType = b.getAttribute("data-type");
                const folderName = p.split("/").filter(Boolean).pop();
                let choices;
                if (issueType === "name_mismatch") {
                    choices = `Wie soll umbenannt werden?\n\n1 = Ordner an Datei angleichen\n2 = Datei an Ordner angleichen\n3 = Freien Namen eingeben\n\nBitte 1, 2 oder 3 eingeben:`;
                } else {
                    choices = `Ordner „${folderName}" umbenennen.\n\nNeuen Ordnernamen eingeben:`;
                }
                const input = prompt(choices);
                if (!input) return;
                b.disabled = true;
                try {
                    let body;
                    if (issueType === "name_mismatch") {
                        if (input.trim() === "1") {
                            body = { action: "rename_folder_to_file", path: p };
                        } else if (input.trim() === "2") {
                            body = { action: "rename_file_to_folder", path: p };
                        } else if (input.trim() === "3") {
                            const customName = prompt("Neuen Namen eingeben (ohne Dateiendung):");
                            if (!customName) { b.disabled = false; return; }
                            body = { action: "rename_both", path: p, new_name: customName.trim() };
                        } else {
                            body = { action: "rename_folder", path: p, new_name: input.trim() };
                        }
                    } else {
                        body = { action: "rename_folder", path: p, new_name: input.trim() };
                    }
                    const res = await fetch("/api/nas/health-fix", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body),
                    });
                    const data = await res.json();
                    if (data.ok) { pollHealthStatus(false); }
                    else { alert(data.message || "Fehler"); b.disabled = false; }
                } catch (e) { alert("Fehler: " + e); b.disabled = false; }
            });
        });

        wireIgnoreButtons(issuesEl, () => pollHealthStatus(false));
        wireRestoreAll(issuesEl);
    } else if (hasResult) {
        issuesEl.innerHTML = `<p class="text-muted" style="margin:4px 0;">Keine Auffälligkeiten gefunden. 🎉</p>` + renderIgnoredFooter(data.ignored_count);
        wireRestoreAll(issuesEl);
    } else {
        issuesEl.innerHTML = "";
    }

    // 3. Scrollposition wiederherstellen
    if (hadDetails) {
        window.scrollTo(0, scrollTop);
    }
}

// Gemeinsame Helfer für die "Ignorieren"-Funktion (Health & Duplikate)
function renderIgnoredFooter(count) {
    if (!count) return "";
    return `<p class="text-muted" style="margin:10px 0 0; font-size:0.82em;">
              ${count} Befund(e) ausgeblendet ·
              <a href="#" class="finding-restore-all" style="color:var(--accent);">↩︎ wieder einblenden</a>
            </p>`;
}

function wireIgnoreButtons(container, onDone) {
    container.querySelectorAll(".finding-ignore").forEach(b => {
        b.addEventListener("click", async () => {
            const key = b.getAttribute("data-key");
            if (!key) return;
            b.disabled = true;
            try {
                await fetch("/api/findings/ignore", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ key }),
                });
                if (onDone) onDone();
            } catch (e) { b.disabled = false; }
        });
    });
}

function wireRestoreAll(container) {
    const link = container.querySelector(".finding-restore-all");
    if (!link) return;
    link.addEventListener("click", async (e) => {
        e.preventDefault();
        try {
            const res = await fetch("/api/findings/ignored");
            const data = await res.json();
            for (const key of (data.ignored || [])) {
                await fetch("/api/findings/unignore", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ key }),
                });
            }
            pollHealthStatus(false);
            pollDuplicateStatus(false);
        } catch (err) { /* ignore */ }
    });
}

// ==========================================================================
// Feature 4: NAS-weite Duplikat-Erkennung
// ==========================================================================
let duplicatePollTimer = null;

function fmtSize(bytes) {
    if (!bytes || bytes <= 0) return "0 MB";
    const gb = bytes / (1024 ** 3);
    if (gb >= 1) return gb.toFixed(2) + " GB";
    return (bytes / (1024 ** 2)).toFixed(0) + " MB";
}

// Beschriftet NAS-/Cloud-Schalter und Zielordner-Labels mit den tatsächlichen
// Speicherziel-Namen aus den Einstellungen (statt fix "NAS"/"pCloud").
// So heißt der Cloud-Schalter z.B. "Auch in Google Drive sichern", wenn das
// Cloud-Ziel entsprechend benannt ist.
async function applyStorageTargetLabels() {
    try {
        const res = await fetch("/api/settings");
        if (!res.ok) return;
        const settings = await res.json();
        const targets = settings.storage_targets || [];
        const nasT = targets.find(t => t.id === "nas") || targets.find(t => t.type === "nas");
        const cloudT = targets.find(t => t.id === "pcloud")
            || targets.find(t => (t.rclone_remote || "").trim() && t.id !== "nas");
        const nasName = (nasT && nasT.name) ? nasT.name : "NAS";
        const cloudName = (cloudT && cloudT.name) ? cloudT.name : "Cloud";
        document.querySelectorAll(".nas-target-name").forEach(el => { el.textContent = nasName; });
        document.querySelectorAll(".cloud-target-name").forEach(el => { el.textContent = cloudName; });
    } catch (e) {
        console.error("Speicherziel-Labels konnten nicht gesetzt werden:", e);
    }
}

function initDuplicateDashboard() {
    const btn = document.getElementById("btn-duplicate-scan");
    if (btn) btn.addEventListener("click", startDuplicateScan);
    pollDuplicateStatus(false);
}

async function startDuplicateScan() {
    const btn = document.getElementById("btn-duplicate-scan");
    try {
        const res = await fetch("/api/nas/scan-duplicates", { method: "POST" });
        const data = await res.json();
        const statusEl = document.getElementById("duplicate-scan-status");
        if (data.started === false && statusEl) statusEl.textContent = data.message || "Ein Scan läuft bereits.";
        if (btn) btn.disabled = true;
        pollDuplicateStatus(true);
    } catch (e) {
        console.error("Duplikat-Scan konnte nicht gestartet werden:", e);
    }
}

async function pollDuplicateStatus() {
    try {
        const res = await fetch("/api/nas/duplicates");
        if (!res.ok) return;
        const data = await res.json();
        renderDuplicateStatus(data);
        const running = data.status === "running";
        const btn = document.getElementById("btn-duplicate-scan");
        if (btn) btn.disabled = running;
        if (running) {
            clearTimeout(duplicatePollTimer);
            duplicatePollTimer = setTimeout(() => pollDuplicateStatus(true), 2000);
        }
    } catch (e) {
        console.error("Duplikat-Status konnte nicht geladen werden:", e);
    }
}

function renderDuplicateStatus(data) {
    const statusEl = document.getElementById("duplicate-scan-status");
    const progWrap = document.getElementById("duplicate-progress-wrap");
    const progBar = document.getElementById("duplicate-progress-bar");
    const summaryEl = document.getElementById("duplicate-summary");
    const groupsEl = document.getElementById("duplicate-groups");
    if (!statusEl || !summaryEl || !groupsEl) return;

    if (data.status === "running") {
        statusEl.textContent = data.message || "Scan läuft...";
        if (progWrap) progWrap.style.display = "block";
        if (progBar) progBar.style.width = `${data.progress || 0}%`;
        return;
    }
    if (progWrap) progWrap.style.display = "none";

    if (data.status === "error") {
        statusEl.textContent = `Fehler: ${data.message || data.error || "Unbekannt"}`;
        return;
    }

    const hasResult = data.finished_at || data.status === "done";
    if (!hasResult) {
        statusEl.textContent = "Noch kein Scan durchgeführt.";
        summaryEl.innerHTML = "";
        groupsEl.innerHTML = "";
        return;
    }

    const when = data.finished_at ? new Date(data.finished_at * 1000).toLocaleString("de-DE") : "";
    statusEl.textContent = data.message + (when ? ` (zuletzt: ${when})` : "");

    const sum = data.summary || { groups: 0, reclaimable_bytes: 0 };
    summaryEl.innerHTML = `<span style="font-size:0.9em;">
        <strong>${sum.groups || 0}</strong> auffällige Gruppe(n) · rückgewinnbar:
        <strong>${fmtSize(sum.reclaimable_bytes)}</strong></span>`;

    const groups = data.groups || [];
    if (groups.length === 0) {
        groupsEl.innerHTML = `<p class="text-muted" style="margin:4px 0;">Keine Duplikate gefunden. 🎉</p>`
            + renderIgnoredFooter(data.ignored_count);
        wireRestoreAll(groupsEl);
        return;
    }

    groupsEl.innerHTML = "";
    groups.forEach(g => {
        const card = document.createElement("div");
        card.style.cssText = "border:1px solid var(--border-light); border-radius:8px; padding:10px 12px;";
        const seLabel = `S${String(g.season).padStart(2, "0")}E${String(g.episode).padStart(2, "0")}`;
        const isCollision = g.kind === "collision";
        const headerColor = isCollision ? "#f59e0b" : "var(--text-main)";

        let html = `<div style="display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px;">
                        <span style="font-weight:500; color:${headerColor};">${isCollision ? "⚠️ " : ""}${escapeHTML(g.category || "")} · ${escapeHTML(g.show)} ${seLabel}</span>
                        <button class="btn btn-secondary btn-sm finding-ignore" data-key="${escapeHTML(g.key || "")}" title="Diese Gruppe dauerhaft ausblenden" style="white-space:nowrap;">🚫 Ignorieren</button>
                    </div>`;
        if (isCollision && g.note) {
            html += `<p class="text-muted" style="margin:0 0 8px; font-size:0.82em;">${escapeHTML(g.note)}</p>`;
        }
        html += `<div style="display:flex; flex-direction:column; gap:6px;">`;
        g.files.forEach(f => {
            const keep = f.recommended === "keep";
            let badge;
            if (isCollision) {
                badge = `<span style="color:#f59e0b; font-size:0.8em; white-space:nowrap;">prüfen</span>`;
            } else if (keep) {
                badge = `<span style="color:#10b981; font-size:0.8em; white-space:nowrap;">✅ behalten</span>`;
            } else {
                badge = `<span style="color:#f59e0b; font-size:0.8em; white-space:nowrap;">Duplikat</span>`;
            }
            const details = `${f.codec || "?"} · ${f.resolution || "?"} · ${fmtSize(f.size)}`;
            const openBtn = `<button class="btn btn-secondary btn-sm dup-open" data-path="${escapeHTML(f.path)}" style="white-space:nowrap;">📂 Öffnen</button>`;
            // Echtes Duplikat: nur die NICHT zu behaltende Datei löschbar.
            // Kollision: kein Auto-Vorschlag -> Löschen pro Datei manuell möglich.
            const showDelete = isCollision ? true : !keep;
            const delBtn = showDelete
                ? `<button class="btn btn-secondary btn-sm dup-delete" data-path="${escapeHTML(f.path)}" style="white-space:nowrap; color:#ef4444;">🗑️ Löschen</button>`
                : "";
            html += `<div class="dup-file-row" style="display:flex; align-items:center; justify-content:space-between; gap:10px; font-size:0.88em; padding:4px 0; border-top:1px solid rgba(255,255,255,0.04);">
                        <span style="overflow:hidden; text-overflow:ellipsis;">${badge} &nbsp; ${escapeHTML(f.filename)}<br><span class="text-muted" style="font-size:0.85em;">${details}</span></span>
                        <span style="display:flex; gap:6px; white-space:nowrap;">${openBtn}${delBtn}</span>
                     </div>`;
        });
        html += `</div>`;
        card.innerHTML = html;

        // "Öffnen" öffnet den Ordner, in dem die Datei liegt
        card.querySelectorAll(".dup-open").forEach(b => {
            b.addEventListener("click", () => {
                const p = b.getAttribute("data-path");
                const folder = p.substring(0, p.lastIndexOf("/"));
                fetch(`/api/system-open-folder?path=${encodeURIComponent(folder)}`).catch(() => {});
            });
        });
        card.querySelectorAll(".dup-delete").forEach(b => {
            b.addEventListener("click", () => resolveDuplicate(b.getAttribute("data-path"), b, card));
        });
        groupsEl.appendChild(card);
    });

    // Ignorieren-Footer + Verdrahtung (Gruppen ausblenden / wieder einblenden)
    const footer = document.createElement("div");
    footer.innerHTML = renderIgnoredFooter(data.ignored_count);
    groupsEl.appendChild(footer);
    wireIgnoreButtons(groupsEl, () => pollDuplicateStatus(false));
    wireRestoreAll(groupsEl);
}

async function resolveDuplicate(path, btn, card) {
    const name = path.split("/").pop();
    if (!confirm(`Diese Datei wirklich endgültig löschen?\n\n${name}\n\nBegleitdateien (NFO/Untertitel/Thumbnail) werden mitgelöscht.`)) {
        return;
    }
    btn.disabled = true;
    btn.textContent = "Lösche...";
    try {
        const res = await fetch("/api/nas/resolve-duplicate-global", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path }),
        });
        const data = await res.json();
        if (data.ok) {
            // Zeile entfernen; Gruppe entfernen, wenn nur noch eine Datei übrig ist
            const row = btn.closest(".dup-file-row");
            if (row) row.remove();
            const remaining = card.querySelectorAll(".dup-file-row").length;
            if (remaining <= 1) card.remove();
        } else {
            alert("Löschen fehlgeschlagen: " + (data.message || "Unbekannt"));
            btn.disabled = false;
            btn.textContent = "🗑️ Löschen";
        }
    } catch (e) {
        alert("Fehler beim Löschen: " + e);
        btn.disabled = false;
        btn.textContent = "🗑️ Löschen";
    }
}

// ==========================================================================
// Filme normalisieren (Genre-Ordner auflösen + lose Dateien einsammeln)
// ==========================================================================
let normalizePlan = [];

function initNormalizeTool() {
    const pv = document.getElementById("btn-normalize-preview");
    if (pv) pv.addEventListener("click", loadNormalizePreview);
    const ap = document.getElementById("btn-normalize-apply");
    if (ap) ap.addEventListener("click", applyNormalize);
}

async function loadNormalizePreview() {
    const statusEl = document.getElementById("normalize-status");
    const planEl = document.getElementById("normalize-plan");
    const applyWrap = document.getElementById("normalize-apply-wrap");
    if (statusEl) statusEl.textContent = "Analysiere…";
    if (planEl) planEl.innerHTML = "";
    if (applyWrap) applyWrap.style.display = "none";
    try {
        const res = await fetch("/api/nas/normalize-films/preview", { method: "POST" });
        const data = await res.json();
        normalizePlan = data.plan || [];
        renderNormalizePlan(normalizePlan);
    } catch (e) {
        if (statusEl) statusEl.textContent = "Fehler bei der Vorschau.";
    }
}

function renderNormalizePlan(plan) {
    const statusEl = document.getElementById("normalize-status");
    const planEl = document.getElementById("normalize-plan");
    const applyWrap = document.getElementById("normalize-apply-wrap");
    if (!planEl) return;
    if (!plan.length) {
        if (statusEl) statusEl.textContent = "Alles sauber – nichts zu normalisieren. 🎉";
        planEl.innerHTML = "";
        if (applyWrap) applyWrap.style.display = "none";
        return;
    }
    const conflicts = plan.filter(p => p.conflict).length;
    if (statusEl) statusEl.textContent = `${plan.length} Vorschlag(e)` + (conflicts ? ` · ${conflicts} mit Konflikt (übersprungen)` : "");
    planEl.innerHTML = plan.map((p, i) => {
        const attr = p.conflict ? "disabled" : "checked";
        const warn = p.conflict ? ` <span style="color:#ef4444;">(Ziel existiert bereits)</span>` : "";
        const kindBadge = p.kind === "genre" ? "📂 Genre" : "📄 lose";
        return `<label style="display:flex; gap:8px; align-items:flex-start; font-size:0.85em; padding:4px 0; border-top:1px solid rgba(255,255,255,0.04);">
                    <input type="checkbox" class="normalize-item" data-idx="${i}" ${attr} style="margin-top:3px;">
                    <span><span class="text-muted">${kindBadge}</span> ${escapeHTML(p.label)}${warn}</span>
                </label>`;
    }).join("");
    if (applyWrap) applyWrap.style.display = "block";
    planEl.querySelectorAll(".normalize-item").forEach(cb => cb.addEventListener("change", updateNormalizeApplyCount));
    updateNormalizeApplyCount();
}

function updateNormalizeApplyCount() {
    const n = document.querySelectorAll(".normalize-item:checked").length;
    const btn = document.getElementById("btn-normalize-apply");
    if (btn) { btn.textContent = `✅ ${n} Ausgewählte anwenden`; btn.disabled = n === 0; }
}

async function applyNormalize() {
    const idxs = Array.from(document.querySelectorAll(".normalize-item:checked"))
        .map(cb => parseInt(cb.getAttribute("data-idx")));
    const items = idxs.map(i => normalizePlan[i]).filter(Boolean);
    if (!items.length) return;
    if (!confirm(`${items.length} Verschiebung(en) jetzt ausführen?\n\nDateien werden auf dem NAS verschoben. Es wird nichts überschrieben.`)) return;
    const btn = document.getElementById("btn-normalize-apply");
    if (btn) { btn.disabled = true; btn.textContent = "Verschiebe…"; }
    try {
        const res = await fetch("/api/nas/normalize-films/apply", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items }),
        });
        const data = await res.json();
        if (data.ok) {
            const statusEl = document.getElementById("normalize-status");
            if (statusEl) statusEl.textContent = "In die Warteschlange eingereiht – Fortschritt im Queue-Panel.";
            openQueue();
            pollQueue();
            setTimeout(loadNormalizePreview, 3000);
        } else {
            const statusEl = document.getElementById("normalize-status");
            if (statusEl) statusEl.textContent = data.message || "Fehler beim Anwenden.";
            if (btn) { btn.disabled = false; }
        }
    } catch (e) {
        const statusEl = document.getElementById("normalize-status");
        if (statusEl) statusEl.textContent = "Fehler beim Anwenden.";
        if (btn) { btn.disabled = false; }
    }
}

function openToolRunnerModal(toolType, title, desc, hasQualitySlider = false) {
    window.currentActiveTool = toolType;
    
    const titleEl = document.getElementById("tool-modal-title");
    const descEl = document.getElementById("tool-modal-desc");
    const pathInput = document.getElementById("tool-modal-target-path");
    const extraOpt = document.getElementById("tool-modal-extra-options");
    const modal = document.getElementById("modal-tool-runner");
    
    if (titleEl) titleEl.textContent = title;
    if (descEl) descEl.textContent = desc;
    if (pathInput) {
        pathInput.value = currentProject || (currentSettings ? currentSettings.inbox_dir : "");
    }
    
    if (extraOpt) {
        if (hasQualitySlider) {
            extraOpt.innerHTML = `
                <div class="quality-slider-container form-group" style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <label for="tool-modal-quality-slider" style="font-weight: 500;">Konvertierungs-Qualität (CRF):</label>
                        <span id="tool-modal-quality-val" style="font-weight: bold; color: var(--accent);">60</span>
                    </div>
                    <input type="range" id="tool-modal-quality-slider" min="10" max="100" value="60" step="1" style="width: 100%; margin-top: 5px;">
                    <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-top: 4px;">
                        <span>Schneller / Kleinere Datei (10)</span>
                        <span>Sehr hohe Qualität / Große Datei (100)</span>
                    </div>
                </div>
            `;
            extraOpt.style.display = "block";
            const slider = document.getElementById("tool-modal-quality-slider");
            const valText = document.getElementById("tool-modal-quality-val");
            if (slider && valText) {
                slider.addEventListener("input", () => {
                    valText.textContent = slider.value;
                });
            }
        } else {
            extraOpt.innerHTML = "";
            extraOpt.style.display = "none";
        }
    }
    
    if (modal) modal.classList.add("active");
}

function openProfilesModal() {
    const modal = document.getElementById("modal-profiles");
    if (modal) {
        modal.classList.add("active");
        loadProfilesInModal();
    }
}

async function loadProfilesInModal() {
    const container = document.getElementById("profiles-list-container");
    if (!container) return;
    
    container.innerHTML = `<div style="color:var(--text-muted); font-size:13px; padding:10px; text-align:center;">Lade Profile...</div>`;
    
    try {
        const res = await fetch("/api/profiles");
        const data = await res.json();
        
        if (!data.profiles || data.profiles.length === 0) {
            container.innerHTML = `<div style="color:var(--text-muted); font-size:13px; padding:20px; text-align:center;">Keine gespeicherten Profile gefunden.</div>`;
            return;
        }
        
        // Sortieren
        data.profiles.sort((a, b) => {
            const nameA = a.data.show_name || a.filename;
            const nameB = b.data.show_name || b.filename;
            return nameA.localeCompare(nameB);
        });
        
        let html = "";
        data.profiles.forEach(p => {
            const displayName = p.data.show_name || p.filename.replace(".json", "");
            const info = `ID: ${p.data.show_id || 'N/A'} | Provider: ${p.data.provider || 'N/A'}`;
            html += `
                <div class="profile-card" style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 6px; gap: 10px;">
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 600; color: var(--text-main); font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${displayName}</div>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">${info}</div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary btn-sm" onclick="loadProfileFromModal('${p.filename.replace(/'/g, "\\'")}', '${displayName.replace(/'/g, "\\'")}', ${p.data.show_id || null}, '${p.data.provider || ''}')" title="In Sendezentrale laden" style="padding: 4px 8px; font-size: 12px; display: inline-flex; align-items: center; gap: 4px;">
                            📂 Laden
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="deleteProfileFromModal('${p.filename.replace(/'/g, "\\'")}', '${displayName.replace(/'/g, "\\'")}')" title="Profil löschen" style="padding: 4px 8px; font-size: 12px; display: inline-flex; align-items: center; gap: 4px;">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch(err) {
        console.error("Fehler beim Laden der Profile im Modal:", err);
        container.innerHTML = `<div style="color:var(--danger); font-size:13px; padding:10px; text-align:center;">Fehler beim Laden der Profile.</div>`;
    }
}

async function deleteProfileFromModal(filename, displayName) {
    if (!confirm(`Möchtest du das Profil für "${displayName}" wirklich löschen?`)) return;
    
    try {
        const response = await fetch("/api/profiles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "delete", filename: filename })
        });
        const data = await response.json();
        if (data.status === "success") {
            loadProfilesInModal();
            // Haupt-Dropdown ebenfalls aktualisieren falls vorhanden
            if (typeof populateLocalProfilesDropdown === "function") {
                populateLocalProfilesDropdown();
            }
        } else {
            alert("Fehler beim Löschen des Profils.");
        }
    } catch (e) {
        console.error("Fehler beim Löschen des Profils:", e);
    }
}

function loadProfileFromModal(filename, displayName, showId, provider) {
    // Schließe Modal
    const modal = document.getElementById("modal-profiles");
    if (modal) modal.classList.remove("active");
    
    // Wechsle zum Home-Tab / Sendezentrale
    const homeBtn = document.getElementById("master-btn-home");
    if (homeBtn) homeBtn.click();
    
    // Lade Show mit selectShow
    const showObj = {
        id: showId || "",
        provider: provider || "tmdb",
        name: displayName || "",
        year: "",
        plot: "",
        poster: ""
    };
    selectShow(showObj);
}

// Global registrieren, damit Inline-onclicks funktionieren
window.loadProfileFromModal = loadProfileFromModal;
window.deleteProfileFromModal = deleteProfileFromModal;

// Sidebar Drag & Drop to merge folders
function initSidebarDragAndDrop() {
    const container = document.getElementById("project-list-container");
    if (!container) return;

    let draggedProject = null;

    // Use event delegation for all drag/drop events
    container.addEventListener("dragstart", (e) => {
        const item = e.target.closest(".project-item");
        if (item && item.getAttribute("draggable") === "true") {
            draggedProject = item.getAttribute("data-project");
            e.dataTransfer.setData("text/plain", draggedProject);
            e.dataTransfer.effectAllowed = "move";
            item.classList.add("dragging");
        }
    });

    container.addEventListener("dragend", (e) => {
        const item = e.target.closest(".project-item");
        if (item) {
            item.classList.remove("dragging");
        }
        container.querySelectorAll(".project-item").forEach(el => el.classList.remove("drag-hover"));
        draggedProject = null;
    });

    container.addEventListener("dragover", (e) => {
        const targetItem = e.target.closest(".project-item");
        if (targetItem && targetItem.getAttribute("draggable") === "true" && draggedProject) {
            const targetProject = targetItem.getAttribute("data-project");
            if (targetProject !== draggedProject) {
                e.preventDefault();
                targetItem.classList.add("drag-hover");
            }
        }
    });

    container.addEventListener("dragleave", (e) => {
        const targetItem = e.target.closest(".project-item");
        if (targetItem && !targetItem.contains(e.relatedTarget)) {
            targetItem.classList.remove("drag-hover");
        }
    });

    container.addEventListener("drop", async (e) => {
        e.preventDefault();
        const targetItem = e.target.closest(".project-item");
        if (targetItem) {
            targetItem.classList.remove("drag-hover");
            const targetProject = targetItem.getAttribute("data-project");
            const sourceProject = e.dataTransfer.getData("text/plain") || draggedProject;

            if (sourceProject && targetProject && sourceProject !== targetProject) {
                const skipConfirm = localStorage.getItem("skipMergeConfirm") === "true";
                let confirmed = skipConfirm;
                if (!confirmed) {
                    confirmed = await showMergeConfirmModal(sourceProject, targetProject);
                }
                
                if (confirmed) {
                    await mergeProjects(sourceProject, targetProject);
                }
            }
        }
    });
}

function showMergeConfirmModal(source, target) {
    return new Promise((resolve) => {
        const modal = document.getElementById("modal-confirm-merge");
        const textEl = document.getElementById("confirm-merge-text");
        const btnCancel = document.getElementById("btn-cancel-merge");
        const btnClose = document.getElementById("close-modal-confirm-merge");
        const btnConfirm = document.getElementById("btn-confirm-merge-execute");
        const skipCb = document.getElementById("confirm-merge-skip-cb");
        
        if (!modal || !textEl || !btnCancel || !btnConfirm) {
            resolve(confirm(`Möchtest du den Ordner "${source}" in den Ordner "${target}" verschieben und mit ihm zusammenführen?`));
            return;
        }
        
        textEl.textContent = `Möchtest du den Ordner "${source}" in den Ordner "${target}" verschieben und mit ihm zusammenführen?`;
        if (skipCb) skipCb.checked = false;
        
        modal.classList.add("active");
        
        const cleanup = (result) => {
            modal.classList.remove("active");
            btnCancel.removeEventListener("click", onCancel);
            if (btnClose) btnClose.removeEventListener("click", onCancel);
            btnConfirm.removeEventListener("click", onConfirm);
            
            if (result && skipCb && skipCb.checked) {
                localStorage.setItem("skipMergeConfirm", "true");
            }
            
            resolve(result);
        };
        
        function onCancel() {
            cleanup(false);
        }
        
        function onConfirm() {
            cleanup(true);
        }
        
        btnCancel.addEventListener("click", onCancel);
        if (btnClose) btnClose.addEventListener("click", onCancel);
        btnConfirm.addEventListener("click", onConfirm);
    });
}

async function mergeProjects(source, target) {
    appendConsoleLog(`[System]: Führe Ordner zusammen: "${source}" -> "${target}"...`);
    try {
        const response = await fetch("/api/merge-projects", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source: source, target: target })
        });
        const data = await response.json();
        if (data.status === "success") {
            appendConsoleLog(`✅ Ordner erfolgreich zusammengeführt.`);
            if (typeof loadStatus === "function") {
                await loadStatus();
            }
            if (currentProject === source) {
                selectProject(target);
            } else if (currentProject === target) {
                scanProject(target);
            }
        } else {
            appendConsoleLog(`❌ Fehler beim Zusammenführen: ${data.error || "Unbekannter Fehler"}`);
            alert(`Fehler beim Zusammenführen: ${data.error || "Unbekannter Fehler"}`);
        }
    } catch (e) {
        console.error("Error merging projects:", e);
        appendConsoleLog(`❌ Fehler: ${e.message}`);
        alert(`Fehler: ${e.message}`);
    }
}

// Initialize Drag & Drop and Reset Button
document.addEventListener("DOMContentLoaded", () => {
    initSidebarDragAndDrop();
    
    const btnResetMerge = document.getElementById("btn-reset-merge-confirm");
    if (btnResetMerge) {
        btnResetMerge.addEventListener("click", () => {
            localStorage.removeItem("skipMergeConfirm");
            alert("Bestätigungs-Dialog beim Zusammenführen von Ordnern wurde erfolgreich reaktiviert!");
        });
    }
});


window.clearSelectedShow = function() {
    window.selectedShow = null;
    const panel = document.getElementById("selected-show-panel");
    if (panel) panel.classList.add("hidden");
    
    const clearBtn = document.getElementById("btn-clear-profile-selection");
    if (clearBtn) clearBtn.classList.add("hidden");
    
    const localProfileSelect = document.getElementById("series-local-profile-select");
    if (localProfileSelect) localProfileSelect.value = "";
    
    const overrideInput = document.getElementById("series-nas-folder-override");
    if (overrideInput) {
        overrideInput.value = "";
        window.nasFolderSelected = "";
    }
    
    const matchingContainer = document.getElementById("matching-panel-container");
    if (matchingContainer) matchingContainer.innerHTML = "";
    
    const execPanel = document.getElementById("series-execution-panel");
    if (execPanel) execPanel.classList.add("hidden");
    
    const seriesNfoTitle = document.getElementById("series-nfo-title");
    const seriesNfoYear = document.getElementById("series-nfo-year");
    const seriesNfoPlot = document.getElementById("series-nfo-plot");
    if (seriesNfoTitle) seriesNfoTitle.value = "";
    if (seriesNfoYear) seriesNfoYear.value = "";
    if (seriesNfoPlot) seriesNfoPlot.value = "";
    
    fetchNasSeasons();
};

window.clearNasOverride = function() {
    const overrideInput = document.getElementById("series-nas-folder-override");
    if (overrideInput && selectedShow) {
        overrideInput.value = cleanSeriesName(selectedShow.name);
        window.nasFolderSelected = ""; // Clear polluted saved state
        window.disableNasFuzzyMatch = true; // Prevent backend from re-matching the wrong folder
        
        // Visual flash to indicate reset
        overrideInput.classList.remove("highlight-match-flash");
        void overrideInput.offsetWidth;
        overrideInput.classList.add("highlight-match-flash");
        setTimeout(() => {
            overrideInput.classList.remove("highlight-match-flash");
        }, 1500);
        
        // Re-fetch NAS info and reset duplicates
        fetchNasSeasons();
        
        // If we are currently showing episodes, we must re-trigger match to clear duplicate warnings
        const execPanel = document.getElementById("series-execution-panel");
        if (execPanel && !execPanel.classList.contains("hidden")) {
            const btn = document.getElementById("btn-fetch-episodes");
            if (btn) btn.click();
        }
    }
};
