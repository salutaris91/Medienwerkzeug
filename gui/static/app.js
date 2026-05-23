// ==========================================================================
// STATE MANAGEMENT
// ==========================================================================
let currentProject = "";
let projectFiles = [];
let currentProjectIsDoku = false;
let selectedShow = null;
let selectedMovie = null;
let episodesData = {}; // maps episode number (string) to title/info
let fetchedEpisodeMetadataCache = {}; // caches fetched episode metadata: provider_showid_season_episode -> {title, plot, aired}
let eventSource = null;
let isManualMovieMode = false;
let isManualSeriesMode = false;

// YouTube Downloader states
let ytFetchedInfo = null;
let ytSelectedMovie = null;
let ytSelectedShow = null;
let ytEpisodesData = {};
let activeYtTaskId = null;
let ytStatusInterval = null;


// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    initViews();
    initConsole();
    initEventListeners();
    initQueue();
    
    // Load settings and status immediately
    loadSettings();
    loadStatus();
    
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
        seriesOverrideInput.addEventListener("change", fetchNasSeasons);
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
            const pcloudDest = document.getElementById("series-pcloud-destination");
            if (pcloudDest) {
                pcloudDest.value = e.target.value;
            }
        });
    }
    if (ytNasDest) {
        ytNasDest.addEventListener("change", (e) => {
            const pcloudDest = document.getElementById("yt-pcloud-destination");
            if (pcloudDest) {
                pcloudDest.value = e.target.value;
            }
        });
    }
    const movieNasDest = document.getElementById("movie-nas-destination");
    if (movieNasDest) {
        movieNasDest.addEventListener("change", (e) => {
            const pcloudDest = document.getElementById("movie-pcloud-destination");
            if (pcloudDest) {
                pcloudDest.value = e.target.value;
            }
        });
    }
});


// ==========================================================================
// UTILS / HELPERS
// ==========================================================================
function cleanSeriesName(name) {
    if (!name) return "";
    // Remove search suffixes in parentheses (case-insensitive)
    let cleaned = name.replace(/\s*\((Mediathek\s+(Serie|Film)\s+aus\s+URL|Freie\s+Mediathek-Suche|fernsehserien\.de\s+URL|\d*\s*Videos?\s+via\s+URL)\)/gi, '');
    // Remove trailing channel tag in brackets, e.g., [ARTE], [ARTE.DE], [TMDB_TV]
    cleaned = cleaned.replace(/\s*\[[a-zA-Z0-9\._-]+\]\s*$/, '');
    // Replace underscores with spaces
    cleaned = cleaned.replace(/_/g, ' ');
    return cleaned.trim();
}

// ==========================================================================
// VIEW ROUTING (MASTER-DETAIL)
// ==========================================================================
function initViews() {
    const btnYoutube = document.getElementById("master-btn-youtube");
    if(btnYoutube) {
        btnYoutube.addEventListener("click", () => {
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById("view-youtube").classList.remove("hidden");
            document.getElementById("view-youtube").classList.add("active");
            
            // Remove active from any selected project in sidebar
            document.querySelectorAll(".project-item").forEach(el => el.classList.remove("active"));
        });
    }
    
    const modes = ["movie", "series", "tools"];
    modes.forEach(mode => {
        const card = document.getElementById(`mode-${mode}`);
        if(card) {
            card.addEventListener("click", () => {
                // UI styling
                modes.forEach(m => document.getElementById(`mode-${m}`)?.classList.remove("active"));
                card.classList.add("active");
                
                document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
                
                let ctxTarget = `context-${mode}`;
                const ctx = document.getElementById(ctxTarget);
                if(ctx) {
                    ctx.classList.remove("hidden");
                    
                    // Autofill logic based on current project
                    let cleanedQuery = currentProject;
                    if (cleanedQuery) {
                        cleanedQuery = cleanedQuery.replace(/\([0-9]{4}\)/g, "").replace(/_/g, " ").trim();
                    }
                    
                    const getCatIdBySub = (sub, fallbackId) => {
                        const cats = currentSettings.sync_categories || [];
                        const found = cats.find(c => c.nas_sub === sub);
                        return found ? found.id : fallbackId;
                    };
                    
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
                    } else if (mode === "series") {
                        document.getElementById("series-nas-destination").value = getCatIdBySub("/Serien", "2");
                        document.getElementById("series-pcloud-destination").value = getCatIdBySub("/Serien", "2");
                        document.getElementById("series-search-query").value = cleanedQuery;
                        detectExistingSeries(currentProject);
                        updateSizeEstimation("series");
                    }
                }
            });
        }
    });
    
    // Tools Dashboard Nav
    const navTools = document.getElementById("nav-tools-dashboard");
    if(navTools) {
        navTools.addEventListener("click", () => {
            // Remove active from inbox items
            document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
            navTools.classList.add("active");
            
            // Show only tools view
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById("view-tools").classList.remove("hidden");
            
            // Auto-fill path if a project was selected
            const pathInput = document.getElementById("tools-target-path");
            if(currentProject && !pathInput.value) {
                pathInput.value = currentProject;
            }
        });
    }

    // Settings Dashboard Nav
    const navSettings = document.getElementById("nav-settings-dashboard");
    if(navSettings) {
        navSettings.addEventListener("click", () => {
            document.querySelectorAll(".project-item").forEach(item => item.classList.remove("active"));
            navSettings.classList.add("active");
            
            document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
            document.getElementById("view-settings").classList.remove("hidden");
            
            loadSettings();
        });
    }
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
}

function expandConsole() {
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
    try {
        const response = await fetch("/api/status");
        if (!response.ok) return;
        const data = await response.json();
        
        // Update NAS Badge
        const nasBadge = document.getElementById("nas-badge");
        nasBadge.className = "status-badge";
        if (data.nas_status === "connected") {
            nasBadge.textContent = "Verbunden";
            nasBadge.classList.add("online");
        } else if (data.nas_status === "available_not_mounted") {
            nasBadge.textContent = "Bereit (Nicht gemountet)";
            nasBadge.classList.add("warning");
        } else {
            nasBadge.textContent = "Offline";
            nasBadge.classList.add("offline");
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
            sfBadge.className = "status-badge online";
            sfBtn.classList.add("hidden");
        }
        
        // Render project lists (sidebar)
        renderProjectList(data.projects);
        
    } catch (e) {
        console.error("Error fetching status:", e);
    }
}

function renderProjectList(projects) {
    const container = document.getElementById("project-list-container");
    if (projects.length === 0) {
        container.innerHTML = '<p class="text-muted text-center" style="padding: 20px;">Keine Ordner in der Inbox</p>';
        return;
    }
    
    // Save current active list name to keep it selected
    let html = `
        <div class="project-item ${currentProject === "" ? "active" : ""}" data-project="">
            <span class="project-item-name">📁 Hauptinbox (Root)</span>
        </div>
    `;
    
    projects.forEach(p => {
        html += `
            <div class="project-item ${currentProject === p ? "active" : ""}" data-project="${p}">
                <span class="project-item-name">📁 ${p}</span>
                <span class="project-item-delete" title="Ordner löschen" data-project="${p}">🗑️</span>
            </div>
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
    // Also remove active from tools nav
    const navTools = document.getElementById("nav-tools-dashboard");
    if(navTools) navTools.classList.remove("active");
    
    // Hide context panels and reset mode cards on new project selection
    document.querySelectorAll(".context-panel").forEach(c => c.classList.add("hidden"));
    ["movie", "series", "doku", "tools"].forEach(m => document.getElementById(`mode-${m}`)?.classList.remove("active"));
    
    scanProject(projectName);
}

async function scanProject(project) {
    const title = document.getElementById("current-project-title");
    const path = document.getElementById("current-project-path");
    const statsContainer = document.getElementById("project-stats-container");
    const statsBadges = document.getElementById("stats-badges-container");
    const tbody = document.getElementById("files-table-body");
    
    // UI View Switching
    document.querySelectorAll(".view-panel").forEach(p => p.classList.add("hidden"));
    document.getElementById("view-folder").classList.remove("hidden");
    document.getElementById("view-folder").classList.add("active");
    
    
    title.textContent = project === "" ? "Hauptinbox verarbeiten" : `Projekt: ${project}`;
    path.textContent = "Scanne Ordner...";
    tbody.innerHTML = '<tr><td colspan="3" class="text-center"><div class="loading-spinner"></div></td></tr>';
    statsContainer.style.display = "none";
    
    try {
        const response = await fetch(`/api/scan-project?project=${encodeURIComponent(project)}`);
        if (!response.ok) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-danger">Fehler beim Laden des Projektinhalts.</td></tr>';
            return;
        }
        
        const data = await response.json();
        path.textContent = `Pfad: ${data.current_dir}`;
        projectFiles = data.files || [];
        currentProjectIsDoku = data.is_doku || false;
        
        if (projectFiles.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Dieser Ordner ist leer.</td></tr>';
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
            if (!isDir && isVideo) {
                const safeProject = project.replace(/'/g, "\\'");
                const safeName = name.replace(/'/g, "\\'");
                actionHtml = `<button class="btn btn-sm" onclick="splitProjectFile('${safeProject}', '${safeName}')" title="In ein separates Projekt abspalten" style="background: rgba(255, 255, 255, 0.1); border: 1px solid var(--border-glass); color: var(--text-normal); cursor: pointer; padding: 3px 8px; border-radius: var(--radius-sm); font-size: 0.7rem; transition: all 0.2s ease;">Trennen</button>`;
            }
            
            rowsHtml += `
                <tr>
                    <td>${name}</td>
                    <td><span class="${badgeClass}">${isDir ? "ORDNER" : ext.toUpperCase()}</span></td>
                    <td style="text-align:right;">${actionHtml}</td>
                </tr>
            `;
        });
        tbody.innerHTML = rowsHtml;
        
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
        const getCatIdBySub = (sub, fallbackId) => {
            const cats = currentSettings.sync_categories || [];
            const found = cats.find(c => c.nas_sub === sub);
            return found ? found.id : fallbackId;
        };
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
            
            html += `
                <div class="search-item" data-id="${item.id}" data-name="${item.name}" data-provider="${item.provider}" data-media-type="${item.media_type}">
                    <div class="search-item-name">${badge}${item.name}</div>
                    <div class="search-item-provider">Metadatendienst: ${item.provider}</div>
                </div>
            `;
        });
        resultsContainer.innerHTML = html;
        
        // Bind selection clicks
        resultsContainer.querySelectorAll(".search-item").forEach(item => {
            item.addEventListener("click", () => {
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
                } else {
                    selectShow(showObj);
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
    selectedShow = show;
    
    const overrideInput = document.getElementById("series-nas-folder-override");
    if (overrideInput) {
        if (window.nasFolderSelected) {
            overrideInput.value = window.nasFolderSelected;
        } else {
            overrideInput.value = cleanSeriesName(show.name);
        }
        autoMatchNasFolder("series-nas-folder-override", "series-nas-destination", overrideInput.value);
    }
    
    const panel = document.getElementById("selected-show-panel");
    const title = document.getElementById("selected-show-title");
    const provider = document.getElementById("selected-show-provider-info");
    const seasonsInfo = document.getElementById("selected-show-seasons-info");
    
    title.textContent = show.name;
    renderProviderInfo(provider, show.provider, show.id, show.loadedFromNfo);
    seasonsInfo.textContent = "Lade Staffel-Informationen...";
    panel.classList.remove("hidden");
    
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

    // Fetch and populate show NFO metadata
    fetch(`/api/metadata/fetch?media_type=tv&provider=${show.provider}&show_id=${show.id}`)
        .then(res => res.json())
        .then(data => {
            if (seriesNfoTitle && data.title) seriesNfoTitle.value = data.title;
            if (seriesNfoYear && data.year) seriesNfoYear.value = data.year;
            if (seriesNfoPlot) seriesNfoPlot.value = data.plot || "";
        })
        .catch(err => {
            console.error("Error fetching show NFO preview:", err);
            if (seriesNfoPlot) seriesNfoPlot.value = "";
        });
        
    fetchNasSeasons();
    
    let hasLoadedAllSeasons = false;
    // Fetch and apply profile settings
    try {
        const profRes = await fetch(`/api/profile?show_name=${encodeURIComponent(show.name)}`);
        if (profRes.ok) {
            const profile = await profRes.json();
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
                
                // Apply destination category
                const nasSelect = document.getElementById("series-nas-destination");
                const pcloudSelect = document.getElementById("series-pcloud-destination");
                
                if (nasSelect) {
                    if (profile.nas_destination_id) {
                        nasSelect.value = profile.nas_destination_id;
                    } else {
                        nasSelect.value = "2"; // Default for Serien
                    }
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
    
    // Auto-routing destination for Dokus
    const nameLower = show.name.toLowerCase();
    const isDoku = nameLower.includes("doku") || nameLower.includes("dokumentation") || currentProjectIsDoku;
    if (isDoku) {
        const getCatIdBySub = (sub, fallbackId) => {
            const cats = currentSettings.sync_categories || [];
            const found = cats.find(c => c.nas_sub === sub);
            return found ? found.id : fallbackId;
        };
        const destId = getCatIdBySub("/Dokus/Doku-Serien", "4");
        
        const nasSelect = document.getElementById("series-nas-destination");
        const pcloudSelect = document.getElementById("series-pcloud-destination");
        if (nasSelect) nasSelect.value = destId;
        if (pcloudSelect) pcloudSelect.value = destId;
    }
    
    updateSizeEstimation("series");
    
    try {
        const response = await fetch(`/api/fetch-show-info?provider=${show.provider}&show_id=${show.id}`);
        const data = await response.json();
        seasonsInfo.textContent = data.info || "Keine Info gefunden";
    } catch (e) {
        seasonsInfo.textContent = "Fehler beim Laden der Details.";
    }

    if (hasLoadedAllSeasons) {
        fetchEpisodes();
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
                if (guessResponse.ok) {
                    const guessData = await guessResponse.json();
                    if (guessData.season) {
                        const seasonInput = document.getElementById("series-season-num");
                        if (seasonInput) {
                            seasonInput.value = guessData.season;
                        }
                        // Automatically trigger fetchEpisodes to populate matrix!
                        fetchEpisodes();
                    }
                }
            } catch (err) {
                console.error("Error guessing season:", err);
            }
        }
    }
}

async function fetchEpisodes() {
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
        episodesData = await response.json();
        
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
        if (videoFiles.length > 0) {
            try {
                const matchResponse = await fetch('/api/match-episodes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider: selectedShow.provider,
                        show_id: selectedShow.id,
                        season: season,
                        filenames: videoFiles
                    })
                });
                if (matchResponse.ok) {
                    const matchData = await matchResponse.json();
                    matches = matchData.matches || {};
                }
            } catch (err) {
                console.error("Error matching episodes:", err);
            }
        }
        
        renderMatchingMatrix(matches);
        execPanel.classList.remove("hidden");
        
    } catch (e) {
        matchingContainer.innerHTML = `<p class="text-center text-danger">Fehler beim Episoden-Laden: ${e}</p>`;
    }
}

function renderMatchingMatrix(matches = {}) {
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
                <div class="match-file" title="${file}">${file}</div>
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
                    
                    <!-- Episoden NFO Editier-Bereich -->
                    <details class="episode-nfo-details" id="episode-nfo-details-${index}" data-index="${index}" style="margin-top: 10px; border: 1px solid rgba(255,255,255,0.05); border-radius: var(--radius-sm); padding: 8px; background: rgba(0,0,0,0.15);">
                        <summary style="cursor: pointer; font-size: 11px; color: var(--text-muted);">📝 NFO für diese Episode bearbeiten</summary>
                        <div style="margin-top: 8px; display: flex; flex-direction: column; gap: 8px;">
                            <div>
                                <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Episodentitel:</label>
                                <input type="text" class="episode-nfo-title" id="episode-nfo-title-${index}" style="width:100%; font-size: 12px; padding: 6px;">
                            </div>
                            <div>
                                <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Erstausstrahlung (Aired):</label>
                                <input type="text" class="episode-nfo-aired" id="episode-nfo-aired-${index}" style="width:100%; font-size: 12px; padding: 6px;">
                            </div>
                            <div>
                                <label style="display:block; font-size:10px; color:var(--text-muted); margin-bottom:3px;">Beschreibung / Plot:</label>
                                <textarea class="episode-nfo-plot" id="episode-nfo-plot-${index}" rows="2" style="width:100%; resize:vertical; font-size: 12px; padding: 6px;"></textarea>
                            </div>
                        </div>
                    </details>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;

    // Bind change listeners to update the selected match info and search inputs
    videoFiles.forEach((file, index) => {
        const select = document.getElementById(`match-select-${index}`);
        const search = document.getElementById(`match-search-${index}`);
        const info = document.getElementById(`selected-match-info-${index}`);
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
        const getCatIdBySub = (sub, fallbackId) => {
            const cats = currentSettings.sync_categories || [];
            const found = cats.find(c => c.nas_sub === sub);
            return found ? found.id : fallbackId;
        };
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
            
            html += `
                <div class="search-item" data-id="${item.id}" data-name="${item.name}" data-provider="${item.provider}" data-media-type="${item.media_type}">
                    <div class="search-item-name">${badge}${item.name}</div>
                    <div class="search-item-provider">Metadatendienst: ${item.provider}</div>
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
        const getCatIdBySub = (sub, fallbackId) => {
            const cats = currentSettings.sync_categories || [];
            const found = cats.find(c => c.nas_sub === sub);
            return found ? found.id : fallbackId;
        };
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
                if (isAllSeasons) {
                    mappings[file] = val;
                } else {
                    mappings[file] = parseInt(val, 10);
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
        force_absolute_season_1: forceAbsoluteSeason1
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
    
    const payload = {
        media_type: "movie",
        project_name: currentProject,
        movie_name: selectedMovie.name,
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
async function analyseYtLink() {
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
        
        // Reset Search Fields
        document.getElementById("yt-meta-mode").value = "youtube";
        toggleYtMetaSection();
        
        // Show Panel
        detailsPanel.classList.remove("hidden");
        
    } catch (e) {
        alert("Fehler: " + e.message);
    } finally {
        loading.classList.add("hidden");
    }
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
            html += `
                <div class="search-item yt-movie-search-item" data-id="${item.id}" data-name="${item.name}" data-provider="${item.provider}">
                    <div class="search-item-name">${item.name}</div>
                    <div class="search-item-provider">Metadatendienst: ${item.provider}</div>
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
            html += `
                <div class="search-item yt-series-search-item" data-id="${item.id}" data-name="${item.name}" data-provider="${item.provider}">
                    <div class="search-item-name">${item.name}</div>
                    <div class="search-item-provider">Metadatendienst: ${item.provider}</div>
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
}

async function startYtPipeline() {
    if (!ytFetchedInfo) return;
    
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
        destination_id: document.getElementById("yt-nas-destination").value,
        nas_destination_id: document.getElementById("yt-nas-destination").value,
        pcloud_destination_id: document.getElementById("yt-pcloud-destination").value
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
        
        // Render groups
        for (const [ext, files] of Object.entries(groups)) {
            // Check by default if it's typical junk
            const isJunk = ['txt', 'url', 'exe', 'ds_store', 'nfo', 'jpg', 'png'].includes(ext);
            
            const groupDiv = document.createElement("div");
            groupDiv.style.marginBottom = "10px";
            groupDiv.innerHTML = `
                <div style="font-size:12px; font-weight:bold; color:var(--accent); text-transform:uppercase; margin-bottom:5px;">
                    Dateityp: .${ext} <span style="color:var(--text-muted); font-weight:normal;">(${files.length} Dateien)</span>
                </div>
                <div style="display:flex; flex-direction:column; gap:5px; padding-left:10px; border-left:2px solid rgba(255,255,255,0.05);">
                    ${files.map(f => `
                        <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
                            <input type="checkbox" class="clean-cb-item" data-file="${f}" ${isJunk ? 'checked' : ''} style="accent-color:#ff4757;">
                            <span style="font-size:11px; color:var(--text-main); word-break:break-all;">${f}</span>
                        </label>
                    `).join("")}
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
    expandConsole();
    appendConsoleLog("[System]: Verschiebe Dateien aus Unterordnern nach oben...");
    
    const payload = {
        media_type: "youtube", // abuse youtube handler to run arbitrary script in currentProject
        // Wait, instead of abuse, let's implement clean script execution for tools
        // Or we can just send it as a process post. Let's make server handle this.
    };
    
    // Let's implement tool actions directly on server in process_worker if we want, or do it client side
    // Actually pulling files can be done via tool API or background worker.
    // Let's check how we can do it: we can trigger a POST /api/process with media_type: "tool_pull_files"
    const targetPath = document.getElementById("tools-target-path").value || currentProject;
    
    const response = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            media_type: "tool_pull_files",
            project_name: targetPath
        })
    });
    if (response.ok) connectLogStream();
}
async function runToolClean() {
    const targetPath = document.getElementById("tools-target-path").value || currentProject;
    
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
        
        // Render groups
        for (const [ext, files] of Object.entries(groups)) {
            // Check by default if it's typical junk
            const isJunk = ['txt', 'url', 'exe', 'ds_store', 'nfo', 'jpg', 'png'].includes(ext);
            
            const groupDiv = document.createElement("div");
            groupDiv.style.marginBottom = "10px";
            groupDiv.innerHTML = `
                <div style="font-size:12px; font-weight:bold; color:var(--accent); text-transform:uppercase; margin-bottom:5px;">
                    Dateityp: .${ext} <span style="color:var(--text-muted); font-weight:normal;">(${files.length} Dateien)</span>
                </div>
                <div style="display:flex; flex-direction:column; gap:5px; padding-left:10px; border-left:2px solid rgba(255,255,255,0.05);">
                    ${files.map(f => `
                        <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
                            <input type="checkbox" class="clean-cb-item" data-file="${f}" ${isJunk ? 'checked' : ''} style="accent-color:#ff4757;">
                            <span style="font-size:11px; color:var(--text-main); word-break:break-all;">${f}</span>
                        </label>
                    `).join("")}
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
            if (typeof loadProjects === "function") {
                loadProjects();
            }
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
    expandConsole();
    appendConsoleLog("[System]: Starte Batch-H.265-Konvertierung...");
    const targetPath = document.getElementById("tools-target-path").value || currentProject;
    const quality = document.getElementById("tool-quality-slider") ? parseInt(document.getElementById("tool-quality-slider").value, 10) : 60;
    const response = await fetch("/api/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            media_type: "tool_batch_convert",
            project_name: targetPath,
            quality: quality
        })
    });
    if (response.ok) connectLogStream();
}

async function runToolGeneric(toolType, logMsg, extraParams = {}) {
    const targetPath = document.getElementById("tools-target-path").value.trim();
    
    if (!targetPath) {
        alert("⚠️ Sicherheits-Stopp: Bitte wähle zuerst einen spezifischen Zielordner-Pfad aus oder klicke auf 'Durchsuchen'!");
        return;
    }
    
    // Check if a dangerous root directory is selected
    const nasRoot = currentSettings.nas_root || "/Volumes/Kino";
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
    // Refresh & Clean
    document.getElementById("btn-scan-project").addEventListener("click", () => scanProject(currentProject));
    document.getElementById("btn-clean-project").addEventListener("click", cleanCurrentProject);
    
    // Import StreamFab
    document.getElementById("btn-streamfab-import").addEventListener("click", async () => {
        appendConsoleLog("[System]: Importiere StreamFab Downloads...");
        try {
            const response = await fetch("/api/streamfab-import", { method: "POST" });
            const data = await response.json();
            appendConsoleLog(`✅ ${data.moved_count} Datei(en) in die Hauptinbox importiert.`);
            loadStatus();
            if (currentProject === "") {
                scanProject("");
            }
        } catch (e) {
            appendConsoleLog(`❌ Fehler beim StreamFab Import: ${e}`);
        }
    });
    
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

    
    // Tools Tab
    document.getElementById("tool-btn-pull-files").addEventListener("click", runToolPullFiles);
    document.getElementById("tool-btn-clean").addEventListener("click", runToolClean);
    document.getElementById("tool-btn-paths-clean").addEventListener("click", openPathsCleanModal);
    
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

    document.getElementById("tool-btn-convert").addEventListener("click", runToolConvert);
    
    document.getElementById("tool-btn-nfo-agent").addEventListener("click", () => runToolGeneric("tool_nfo_agent", "Starte NFO Agent..."));
    document.getElementById("tool-btn-nfo-batch").addEventListener("click", () => {
        const fsk = document.getElementById("tool-fsk-value").value;
        runToolGeneric("tool_nfo_batch_fsk", `Passe FSK auf ${fsk} an...`, { fsk: parseInt(fsk, 10) });
    });
    document.getElementById("tool-btn-manual-sync").addEventListener("click", () => {
        if(!currentSettings.sync_categories || currentSettings.sync_categories.length === 0) {
            alert("Bitte lege zuerst Sync-Kategorien in den Einstellungen an."); return;
        }
        const promptText = "Wohin soll der Ordner auf dem NAS kopiert werden?\n\n" + 
                           currentSettings.sync_categories.map(c => `${c.id} = ${c.name}`).join("\n") + 
                           "\n\nZiel wählen:";
        const dest = prompt(promptText, currentSettings.sync_categories[0].id);
        
        const category = currentSettings.sync_categories.find(c => c.id === dest);
        if(!category) return;
        
        const nasRoot = currentSettings.nas_root || "/Volumes/Kino";
        const destPath = `${nasRoot}${category.nas_sub}`;
        
        const doPcloud = confirm("Soll das Projekt zusätzlich auch in die pCloud hochgeladen werden?");
        runToolGeneric("tool_manual_sync", "Starte NAS Sync...", { destination: destPath, copy_to_pcloud: doPcloud });
    });

    document.getElementById("tool-btn-pcloud-sync").addEventListener("click", () => {
        if(!currentSettings.sync_categories || currentSettings.sync_categories.length === 0) {
            alert("Bitte lege zuerst Sync-Kategorien in den Einstellungen an."); return;
        }
        const promptText = "In welchen Cloud-Ordner soll kopiert werden?\n\n" + 
                           currentSettings.sync_categories.map(c => `${c.id} = ${c.name}`).join("\n") + 
                           "\n\nZiel wählen:";
        const dest = prompt(promptText, currentSettings.sync_categories[0].id);
        
        const category = currentSettings.sync_categories.find(c => c.id === dest);
        if(!category) return;
        
        const nasRoot = currentSettings.nas_root || "/Volumes/Kino";
        const destPath = `${nasRoot}${category.nas_sub}`;
        
        runToolGeneric("tool_pcloud_sync", "Starte reinen pCloud Sync...", { destination: destPath });
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
}

// ==========================================================================
// SETTINGS DASHBOARD LOGIC
// ==========================================================================
let currentSettings = { import_sources: [] };

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

    for (const [name, info] of Object.entries(deps)) {
        const card = document.createElement("div");
        card.className = `dep-card status-${info.status}`;
        
        const label = statusLabels[info.status] || info.status;
        
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
}

async function loadSettings() {
    try {
        const response = await fetch("/api/settings");
        if (response.ok) {
            currentSettings = await response.json();
            document.getElementById("settings-inbox-dir").value = currentSettings.inbox_dir || "";
            document.getElementById("settings-outbox-dir").value = currentSettings.outbox_dir || "";
            document.getElementById("settings-nas-root").value = currentSettings.nas_root || "";
            document.getElementById("settings-pcloud-dir").value = currentSettings.pcloud_dir || "";
            
            const checkDepUpdatesEl = document.getElementById("settings-check-dependency-updates");
            if (checkDepUpdatesEl) {
                checkDepUpdatesEl.checked = !!currentSettings.check_dependency_updates;
            }
            
            if (!currentSettings.import_sources) currentSettings.import_sources = [];
            if (!currentSettings.sync_categories) currentSettings.sync_categories = [];
            renderImportSources();
            renderSyncCategories();
            updateDestinationDropdowns();
            
            checkDependencies(false);
        }
    } catch (e) {
        console.error("Error loading settings:", e);
    }
}

function updateDestinationDropdowns() {
    const nasSelects = ["movie-nas-destination", "series-nas-destination", "yt-nas-destination"];
    const pcloudSelects = ["movie-pcloud-destination", "series-pcloud-destination", "yt-pcloud-destination"];
    
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
}

function setupDestinationToggles() {
    const pairs = [
        { cb: "movie-option-copy-nas", container: "movie-nas-destination-container" },
        { cb: "movie-option-copy-pcloud", container: "movie-pcloud-destination-container" },
        { cb: "series-option-copy-nas", container: "series-nas-destination-container" },
        { cb: "series-option-copy-pcloud", container: "series-pcloud-destination-container" },
        { cb: "yt-option-copy-nas", container: "yt-nas-destination-container" },
        { cb: "yt-option-copy-pcloud", container: "yt-pcloud-destination-container" }
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
                    const nasRoot = currentSettings.nas_root || "/Volumes/Kino";
                    let subPath = data.path;
                    if (subPath.startsWith(nasRoot)) {
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
                    const pcloudRoot = currentSettings.pcloud_dir || "/Users/alex/pCloud Drive";
                    let subPath = data.path;
                    if (subPath.startsWith(pcloudRoot)) {
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
                inbox_dir: document.getElementById("settings-inbox-dir").value,
                outbox_dir: document.getElementById("settings-outbox-dir").value,
                nas_root: document.getElementById("settings-nas-root").value,
                pcloud_dir: document.getElementById("settings-pcloud-dir").value,
                check_dependency_updates: checkDepUpdatesEl ? checkDepUpdatesEl.checked : false,
                import_sources: currentSettings.import_sources.filter(s => s.trim() !== ""),
                sync_categories: currentSettings.sync_categories.filter(c => c.id.trim() !== "" && c.name.trim() !== "")
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

    const btnAddSource = document.getElementById("btn-settings-add-source");
    if(btnAddSource) {
        btnAddSource.addEventListener("click", () => {
            currentSettings.import_sources.push("");
            renderImportSources();
        });
    }

    const btnAddCategory = document.getElementById("btn-settings-add-category");
    if(btnAddCategory) {
        btnAddCategory.addEventListener("click", () => {
            currentSettings.sync_categories.push({id: "", name: "", nas_sub: "", pcloud_remote: ""});
            renderSyncCategories();
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
                        document.getElementById(inputId).value = data.folder;
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
                const path = document.getElementById(inputId).value;
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

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("movie-option-convert")?.addEventListener("change", () => {
        updateSizeEstimation("movie");
    });
    
    document.getElementById("series-option-convert")?.addEventListener("change", () => {
        updateSizeEstimation("series");
    });

    // Movie quality slider
    const movieSlider = document.getElementById("movie-quality-slider");
    const movieVal = document.getElementById("movie-quality-val");
    if (movieSlider && movieVal) {
        movieSlider.addEventListener("input", () => {
            movieVal.textContent = movieSlider.value;
        });
        movieSlider.addEventListener("change", () => {
            updateSizeEstimation("movie");
        });
    }

    // Series quality slider
    const seriesSlider = document.getElementById("series-quality-slider");
    const seriesVal = document.getElementById("series-quality-val");
    if (seriesSlider && seriesVal) {
        seriesSlider.addEventListener("input", () => {
            seriesVal.textContent = seriesSlider.value;
        });
        seriesSlider.addEventListener("change", () => {
            updateSizeEstimation("series");
        });
    }

    // Tool quality slider
    const toolSlider = document.getElementById("tool-quality-slider");
    const toolVal = document.getElementById("tool-quality-val");
    if (toolSlider && toolVal) {
        toolSlider.addEventListener("input", () => {
            toolVal.textContent = toolSlider.value;
        });
    }

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
        
        // Save profile if media_type is TV
        if (finalPayload.media_type === "tv") {
            try {
                const auto_h265 = document.getElementById("series-option-convert").checked ? "j" : "n";
                const pcloud_sonstiges = document.getElementById("series-option-copy-pcloud").checked ? "j" : "n";
                const copy_to_nas = document.getElementById("series-option-copy-nas").checked;
                const copy_to_pcloud = document.getElementById("series-option-copy-pcloud").checked;
                const nas_destination_id = document.getElementById("series-nas-destination").value;
                const pcloud_destination_id = document.getElementById("series-pcloud-destination").value;
                
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
                            pcloud_destination_id: pcloud_destination_id
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

    const activeJobs = jobs.filter(j => j.status === "queued" || j.status === "running");
    
    if (activeJobs.length > 0) {
        badge.textContent = activeJobs.length;
        badge.classList.remove("hidden");
    } else {
        badge.classList.add("hidden");
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

        const card = document.createElement("div");
        card.style.cssText = "background: rgba(20,20,30,0.5); border: 1px solid var(--border-glass); border-radius: var(--radius-lg); padding: 15px;";
        
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                <strong style="font-size:14px; color:var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:10px;">${icon} ${job.name}</strong>
                <span style="font-size:12px; color:${statusColor}; text-transform:uppercase;">${job.status}</span>
            </div>
            <div style="font-size:12px; color:var(--text-muted);">${job.message || ""}</div>
            ${progressHtml}
        `;
        list.appendChild(card);
    });
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
    
    input.addEventListener("input", () => {
        filterFolders(false);
    });
    
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
        for (const f of folders) {
            const normF = f.toLowerCase().replace(/[^a-z0-9]/g, '');
            if (normF.includes(normProj) || normProj.includes(normF)) {
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

