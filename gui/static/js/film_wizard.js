import { renderNfoEditor, buildMovieNfoOverrides } from './nfo_editor.js?v=107';

let activeWizardInstance = null;

function mkEl(doc, tag, { id = "", cls = "", text = "", type = "", attrs = {} } = {}, children = []) {
    const el = doc.createElement(tag);
    if (id) el.id = id;
    if (cls) el.className = cls;
    if (type) el.type = type;
    if (text) el.textContent = text;
    for (const [k, v] of Object.entries(attrs)) {
        el.setAttribute(k, String(v));
    }
    for (const ch of children) {
        if (ch) el.appendChild(ch);
    }
    return el;
}

function buildWizardDom(doc, modalOverlay) {
    modalOverlay.classList.add("mw-modal-overlay", "mw-wizard-overlay", "hidden");
    const stepDefs = [
        [1, "Film suchen"],
        [2, "Metadaten"],
        [3, "Artwork"],
        [4, "Übersicht"],
    ];
    const stepper = mkEl(
        doc,
        "div",
        { id: "mw-wizard-stepper", cls: "mw-wizard-stepper" },
        stepDefs.map(([num, label]) =>
            mkEl(
                doc,
                "div",
                { cls: `mw-wizard-step${num === 1 ? " active" : ""}`, attrs: { "data-step": num } },
                [
                    mkEl(doc, "span", { cls: `step-dot${num === 1 ? " active" : ""}`, text: String(num) }),
                    mkEl(doc, "span", { cls: "mw-wizard-step-label", text: label }),
                ]
            )
        )
    );

    const searchInput = mkEl(doc, "input", {
        id: "mw-wizard-search-input",
        cls: "mw-wizard-input",
        type: "text",
    });
    searchInput.placeholder = "Filmtitel oder TMDb/OFDb-Suchbegriff...";

    const step1 = mkEl(
        doc,
        "section",
        { id: "mw-wizard-step-1", cls: "mw-wizard-panel active", attrs: { "data-step-panel": "1" } },
        [
            mkEl(doc, "div", { cls: "mw-wizard-search-row" }, [
                searchInput,
                mkEl(doc, "button", { id: "mw-wizard-search-btn", cls: "btn btn-primary", type: "button", text: "Suchen" }),
                mkEl(doc, "button", { id: "mw-wizard-manual-btn", cls: "btn btn-secondary", type: "button", text: "Metadaten manuell eintragen" }),
            ]),
            mkEl(doc, "div", { id: "mw-wizard-search-results", cls: "mw-wizard-search-results" }),
        ]
    );

    const step2 = mkEl(
        doc,
        "section",
        { id: "mw-wizard-step-2", cls: "mw-wizard-panel hidden", attrs: { "data-step-panel": "2" } },
        [
            mkEl(doc, "div", { cls: "mw-wizard-meta-header" }, [
                mkEl(doc, "span", { id: "mw-wizard-selected-info", cls: "mw-wizard-selected-info" }),
                mkEl(doc, "span", { id: "mw-wizard-provider-badge", cls: "mw-wizard-badge" }),
            ]),
            mkEl(doc, "div", { id: "mw-wizard-nfo-editor-container", cls: "mw-wizard-editor-host" }),
        ]
    );

    const step3 = mkEl(
        doc,
        "section",
        { id: "mw-wizard-step-3", cls: "mw-wizard-panel hidden", attrs: { "data-step-panel": "3" } },
        [
            mkEl(doc, "div", { cls: "mw-wizard-tabs" }, [
                mkEl(doc, "button", { id: "mw-wizard-tab-poster", cls: "mw-wizard-tab active", type: "button", text: "Poster (2:3)", attrs: { "data-artwork-tab": "poster" } }),
                mkEl(doc, "button", { id: "mw-wizard-tab-fanart", cls: "mw-wizard-tab", type: "button", text: "Fanart (16:9)", attrs: { "data-artwork-tab": "fanart" } }),
            ]),
            mkEl(doc, "div", { id: "mw-wizard-artwork-poster", cls: "mw-wizard-artwork-placeholder active", text: "Automatischer Poster-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden." }),
            mkEl(doc, "div", { id: "mw-wizard-artwork-fanart", cls: "mw-wizard-artwork-placeholder hidden", text: "Automatischer Fanart-/Backdrop-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden." }),
        ]
    );

    const step4 = mkEl(
        doc,
        "section",
        { id: "mw-wizard-step-4", cls: "mw-wizard-panel hidden", attrs: { "data-step-panel": "4" } },
        [mkEl(doc, "div", { id: "mw-wizard-summary", cls: "mw-wizard-summary" })]
    );

    const modal = mkEl(doc, "div", { cls: "mw-modal mw-wizard-modal" }, [
        mkEl(doc, "div", { cls: "mw-wizard-header" }, [
            mkEl(doc, "h3", { id: "mw-wizard-title", cls: "mw-wizard-title", text: "Film-Assistent" }),
            mkEl(doc, "button", { id: "mw-wizard-close", cls: "close-modal mw-wizard-close-btn", type: "button", text: "×", attrs: { "aria-label": "Schließen" } }),
        ]),
        stepper,
        mkEl(doc, "div", { id: "mw-wizard-error-banner", cls: "mw-wizard-error-banner hidden" }, [
            mkEl(doc, "span", { id: "mw-wizard-error-text", cls: "mw-wizard-error-text" }),
            mkEl(doc, "button", { id: "mw-wizard-error-retry", cls: "btn btn-secondary btn-sm", type: "button", text: "Erneut versuchen" }),
        ]),
        mkEl(doc, "div", { cls: "mw-wizard-body" }, [step1, step2, step3, step4]),
        mkEl(doc, "div", { cls: "mw-modal-actions mw-wizard-footer" }, [
            mkEl(doc, "button", { id: "mw-wizard-btn-back", cls: "mw-modal-btn mw-modal-btn-cancel hidden", type: "button", text: "Zurück" }),
            mkEl(doc, "button", { id: "mw-wizard-btn-skip", cls: "btn btn-secondary hidden", type: "button", text: "Überspringen" }),
            mkEl(doc, "button", { id: "mw-wizard-btn-next", cls: "btn btn-primary", type: "button", text: "Weiter" }),
            mkEl(doc, "button", { id: "mw-wizard-btn-handover", cls: "mw-modal-btn mw-modal-btn-confirm hidden", type: "button", text: "Weiter zur Verarbeitung" }),
        ]),
    ]);
    modalOverlay.appendChild(modal);
}

export function createFilmWizard(options = {}) {
    const doc = options.document || (typeof document !== "undefined" ? document : null);
    if (!doc) throw new Error("createFilmWizard requires a document");

    const fetchFn = options.fetch || (typeof fetch === "function" ? fetch.bind(globalThis) : null);
    const confirmFn = options.confirm || (typeof confirm === "function" ? confirm.bind(globalThis) : () => true);

    let modalOverlay = doc.getElementById("modal-film-wizard");
    if (!modalOverlay) {
        modalOverlay = doc.createElement("div");
        modalOverlay.id = "modal-film-wizard";
        if (doc.body) doc.body.appendChild(modalOverlay);
    }
    if (!doc.getElementById("mw-wizard-step-1")) {
        buildWizardDom(doc, modalOverlay);
    }

    const getEl = (id) => doc.getElementById(id);
    const panels = [1, 2, 3, 4].map((n) => getEl(`mw-wizard-step-${n}`));
    const stepperEl = getEl("mw-wizard-stepper");
    const closeBtn = getEl("mw-wizard-close");
    const backBtn = getEl("mw-wizard-btn-back");
    const skipBtn = getEl("mw-wizard-btn-skip");
    const nextBtn = getEl("mw-wizard-btn-next");
    const handoverBtn = getEl("mw-wizard-btn-handover");
    const searchInput = getEl("mw-wizard-search-input");
    const searchBtn = getEl("mw-wizard-search-btn");
    const manualBtn = getEl("mw-wizard-manual-btn");
    const searchResults = getEl("mw-wizard-search-results");
    const selectedInfo = getEl("mw-wizard-selected-info");
    const providerBadge = getEl("mw-wizard-provider-badge");
    const editorContainer = getEl("mw-wizard-nfo-editor-container");
    const tabPoster = getEl("mw-wizard-tab-poster");
    const tabFanart = getEl("mw-wizard-tab-fanart");
    const posterPanel = getEl("mw-wizard-artwork-poster");
    const fanartPanel = getEl("mw-wizard-artwork-fanart");
    const summaryBox = getEl("mw-wizard-summary");
    const errorBanner = getEl("mw-wizard-error-banner");
    const errorText = getEl("mw-wizard-error-text");
    const retryBtn = getEl("mw-wizard-error-retry");

    let currentStep = 1;
    let selectedMovie = null;
    let artworkSkipped = false;
    let activeArtworkTab = "poster";
    let onHandoverCallback = options.onHandover || null;
    let lastRetryAction = null;
    let metadataRequestSeq = 0;

    const nfoEditor = renderNfoEditor(editorContainer, {}, { idPrefix: "mw-wizard-nfo" });

    function hideError() {
        if (errorBanner) errorBanner.classList.add("hidden");
        lastRetryAction = null;
    }

    function showError(message, retryAction = null) {
        if (errorText) errorText.textContent = message;
        if (errorBanner) errorBanner.classList.remove("hidden");
        if (providerBadge) {
            providerBadge.textContent = "Nicht erreichbar";
            providerBadge.classList.remove("mw-wizard-badge-loading");
            providerBadge.classList.add("mw-wizard-badge-error");
        }
        lastRetryAction = retryAction;
    }

    function renderSummary() {
        if (!summaryBox) return;
        const vals = nfoEditor.getValues();
        summaryBox.innerHTML = "";
        const lines = [
            `Titel: ${vals.title || (selectedMovie ? selectedMovie.name : "—")}`,
            `Jahr: ${vals.year || "—"}`,
            `FSK: ${vals.fsk !== "" ? `FSK ${vals.fsk}` : "Keine Angabe"}`,
            `Genre: ${vals.genres.length > 0 ? vals.genres.join(", ") : "Keine Angabe"}`,
            `Artwork: ${artworkSkipped ? "Übersprungen (Standard-Artwork)" : "Standard-Artwork (TMDb)"}`,
            `Plot: ${vals.plot || "—"}`,
        ];
        for (const text of lines) {
            summaryBox.appendChild(mkEl(doc, "div", { cls: "mw-wizard-summary-row", text }));
        }
    }

    function goToStep(stepNumber) {
        currentStep = Math.max(1, Math.min(4, Number(stepNumber) || 1));
        panels.forEach((panel, idx) => {
            if (!panel) return;
            const isCurrent = idx + 1 === currentStep;
            panel.classList.toggle("active", isCurrent);
            panel.classList.toggle("hidden", !isCurrent);
        });

        const stepItems = stepperEl && stepperEl.children ? Array.from(stepperEl.children) : [];
        stepItems.forEach((item, idx) => {
            const stepIdx = idx + 1;
            const dot = item.children && item.children[0];
            item.classList.toggle("active", stepIdx === currentStep);
            item.classList.toggle("completed", stepIdx < currentStep);
            if (dot && dot.classList) {
                dot.classList.toggle("active", stepIdx === currentStep);
                dot.classList.toggle("completed", stepIdx < currentStep);
            }
        });

        if (backBtn) backBtn.classList.toggle("hidden", currentStep === 1);
        if (skipBtn) skipBtn.classList.toggle("hidden", currentStep !== 2 && currentStep !== 3);
        if (nextBtn) nextBtn.classList.toggle("hidden", currentStep === 4);
        if (handoverBtn) handoverBtn.classList.toggle("hidden", currentStep === 1);
        if (currentStep === 4) renderSummary();
        return currentStep;
    }

    function switchArtworkTab(tabName) {
        activeArtworkTab = tabName === "fanart" ? "fanart" : "poster";
        if (tabPoster) tabPoster.classList.toggle("active", activeArtworkTab === "poster");
        if (tabFanart) tabFanart.classList.toggle("active", activeArtworkTab === "fanart");
        if (posterPanel) {
            posterPanel.classList.toggle("active", activeArtworkTab === "poster");
            posterPanel.classList.toggle("hidden", activeArtworkTab !== "poster");
        }
        if (fanartPanel) {
            fanartPanel.classList.toggle("active", activeArtworkTab === "fanart");
            fanartPanel.classList.toggle("hidden", activeArtworkTab !== "fanart");
        }
    }

    async function loadMovieMetadata(movie, reqSeq = ++metadataRequestSeq) {
        if (!movie || !fetchFn || movie.provider === "manual") return;
        const expectedMovie = selectedMovie;
        hideError();
        const providerUpper = String(movie.provider || "").toUpperCase();
        if (providerBadge) {
            providerBadge.textContent = `${providerUpper} · Lade Metadaten...`;
            providerBadge.classList.remove("mw-wizard-badge-error");
            providerBadge.classList.add("mw-wizard-badge-loading");
        }
        try {
            const url = `/api/metadata/fetch?media_type=movie&provider=${encodeURIComponent(movie.provider)}&movie_id=${encodeURIComponent(movie.id)}`;
            const res = await fetchFn(url);
            if (reqSeq !== metadataRequestSeq || selectedMovie !== expectedMovie) return;
            if (!res || !res.ok) throw new Error(`HTTP ${res ? res.status : "Fehler"}`);
            const data = await res.json();
            if (reqSeq !== metadataRequestSeq || selectedMovie !== expectedMovie) return;
            if (data && data.error) throw new Error(data.error);
            if (providerBadge) {
                providerBadge.textContent = providerUpper;
                providerBadge.classList.remove("mw-wizard-badge-loading");
            }
            nfoEditor.applyProviderMetadata({
                title: (data.title !== undefined && data.title !== "") ? data.title : (data.name || movie.name || ""),
                year: data.year ?? "",
                plot: data.plot ?? "",
                fsk: data.fsk ?? "",
                genres: Array.isArray(data.genres) ? data.genres : (data.genres ?? []),
            });
        } catch (err) {
            if (reqSeq !== metadataRequestSeq || selectedMovie !== expectedMovie) return;
            showError(`Metadaten-Abruf fehlgeschlagen (${err.message || err})`, () => loadMovieMetadata(movie));
        }
    }

    async function selectMovieInWizard(movie, fetchMeta = true) {
        const reqSeq = ++metadataRequestSeq;
        selectedMovie = {
            id: String(movie.id || "manual"),
            name: movie.name || movie.title || "",
            provider: movie.provider || "manual",
        };
        const isManual = selectedMovie.provider === "manual";
        if (selectedInfo) selectedInfo.textContent = selectedMovie.name || (isManual ? "Metadaten manuell eintragen" : "");
        if (providerBadge) {
            providerBadge.textContent = isManual ? "Metadaten manuell eintragen" : String(selectedMovie.provider).toUpperCase();
            providerBadge.classList.remove("mw-wizard-badge-error", "mw-wizard-badge-loading");
        }
        const initialLoaded = [];
        if (movie.title || movie.name) initialLoaded.push("title");
        if (movie.year !== undefined && movie.year !== "") initialLoaded.push("year");
        if (movie.plot !== undefined && movie.plot !== "") initialLoaded.push("plot");
        if (movie.fsk !== undefined && movie.fsk !== "") initialLoaded.push("fsk");
        if (Array.isArray(movie.genres) && movie.genres.length > 0) initialLoaded.push("genres");
        nfoEditor.setValues({
            title: movie.title || movie.name || "",
            year: movie.year ?? "",
            plot: movie.plot ?? "",
            fsk: movie.fsk ?? "",
            genres: movie.genres ?? [],
        }, true, { loadedFields: initialLoaded });
        goToStep(2);
        if (fetchMeta && selectedMovie.provider !== "manual") {
            await loadMovieMetadata(selectedMovie, reqSeq);
        }
    }

    async function performSearch(queryOverride) {
        const query = String(queryOverride ?? (searchInput ? searchInput.value : "") ?? "").trim();
        if (!query || !fetchFn) return [];
        hideError();
        if (searchResults) {
            searchResults.innerHTML = "";
            searchResults.appendChild(mkEl(doc, "div", { cls: "mw-wizard-loading", text: "Suche läuft..." }));
        }
        try {
            const res = await fetchFn(`/api/search?type=movie&q=${encodeURIComponent(query)}`);
            if (!res || !res.ok) throw new Error(`HTTP ${res ? res.status : "Fehler"}`);
            const items = await res.json();
            if (!Array.isArray(items)) throw new Error((items && items.error) || "Unerwartetes Suchergebnis");
            if (searchResults) {
                searchResults.innerHTML = "";
                for (const item of items) {
                    const row = mkEl(
                        doc,
                        "div",
                        {
                            cls: "search-item mw-wizard-search-item",
                            attrs: { "data-id": item.id ?? "", "data-name": item.name ?? "", "data-provider": item.provider ?? "tmdb" },
                        },
                        [
                            mkEl(doc, "div", { cls: "search-item-name", text: item.name || "" }),
                            mkEl(doc, "div", { cls: "search-item-provider", text: `Metadatendienst: ${item.provider || "tmdb"}` }),
                        ]
                    );
                    row.addEventListener("click", () => {
                        selectMovieInWizard({ id: item.id, name: item.name, provider: item.provider || "tmdb" });
                    });
                    searchResults.appendChild(row);
                }
            }
            return items;
        } catch (err) {
            if (searchResults) searchResults.innerHTML = "";
            showError(`Suche fehlgeschlagen: ${err.message || err}`, () => performSearch(query));
            return [];
        }
    }

    function open(openOptions = {}) {
        metadataRequestSeq += 1;
        hideError();
        artworkSkipped = false;
        switchArtworkTab("poster");
        if (openOptions.onHandover) onHandoverCallback = openOptions.onHandover;
        const initialQuery = String(openOptions.query ?? "").trim();
        if (searchInput) searchInput.value = initialQuery;
        if (searchResults) searchResults.innerHTML = "";
        selectedMovie = null;
        nfoEditor.setValues(
            { title: initialQuery, year: "", plot: "", fsk: "", genres: [] },
            true,
            { loadedFields: initialQuery ? ["title"] : [] }
        );
        goToStep(1);
        modalOverlay.classList.remove("hidden");
        modalOverlay.classList.add("active");
        if (initialQuery && openOptions.autoSearch !== false && fetchFn) {
            performSearch(initialQuery);
        }
    }

    function close({ force = false } = {}) {
        if (!force && nfoEditor.isDirty()) {
            if (!confirmFn("Änderungen im Film-Assistenten verwerfen?")) return false;
        }
        metadataRequestSeq += 1;
        modalOverlay.classList.add("hidden");
        modalOverlay.classList.remove("active");
        return true;
    }

    function handleEscapeKey(event) {
        if (!event || event.key !== "Escape") return false;
        if (modalOverlay.classList.contains("hidden")) return false;
        // E1-AK1 & D3: ESC schließt das Modal NUR im Schritt-1-Panel, mit Rückfrage bei geänderten Eingaben
        if (currentStep === 1) {
            if (typeof event.preventDefault === "function") event.preventDefault();
            return close({ force: false });
        }
        return false;
    }

    function nextStep() {
        if (currentStep === 1) {
            if (!selectedMovie) {
                metadataRequestSeq += 1;
                const manualTitle = searchInput ? String(searchInput.value || "").trim() : "";
                selectedMovie = { id: "manual", name: manualTitle || "Unbekannter Film", provider: "manual" };
                if (selectedInfo) selectedInfo.textContent = selectedMovie.name;
                if (providerBadge) {
                    providerBadge.textContent = "Metadaten manuell eintragen";
                    providerBadge.classList.remove("mw-wizard-badge-error", "mw-wizard-badge-loading");
                }
                nfoEditor.setValues(
                    { title: selectedMovie.name, year: "", plot: "", fsk: "", genres: [] },
                    true,
                    { loadedFields: ["title"] }
                );
            }
            return goToStep(2);
        }
        return currentStep < 4 ? goToStep(currentStep + 1) : currentStep;
    }

    function prevStep() {
        return currentStep > 1 ? goToStep(currentStep - 1) : currentStep;
    }

    function skipCurrentStep() {
        if (currentStep === 2) {
            nfoEditor.resetToInitial();
            return goToStep(3);
        }
        if (currentStep === 3) {
            artworkSkipped = true;
            return goToStep(4);
        }
        return currentStep;
    }

    function getHandoverPayload() {
        const overrides = typeof nfoEditor.buildWizardMovieOverrides === "function"
            ? nfoEditor.buildWizardMovieOverrides()
            : buildMovieNfoOverrides(nfoEditor);
        const currentVals = nfoEditor.getValues();
        const baseMovie = selectedMovie || { id: "manual", name: currentVals.title || "Unbekannter Film", provider: "manual" };
        return {
            movie: { ...baseMovie, id: String(baseMovie.id || "manual"), name: currentVals.title || baseMovie.name },
            nfo_overrides: overrides,
            wizard_overrides: true,
            artworkSkipped,
        };
    }

    function triggerHandover() {
        const payload = getHandoverPayload();
        close({ force: true });
        if (typeof onHandoverCallback === "function") onHandoverCallback(payload);
        return payload;
    }

    const bindClick = (el, fn) => el && typeof el.addEventListener === "function" && el.addEventListener("click", fn);
    bindClick(closeBtn, () => close({ force: false }));
    bindClick(backBtn, () => prevStep());
    bindClick(skipBtn, () => skipCurrentStep());
    bindClick(nextBtn, () => nextStep());
    bindClick(handoverBtn, () => triggerHandover());
    bindClick(searchBtn, () => performSearch());
    bindClick(manualBtn, () => {
        const queryTitle = searchInput ? String(searchInput.value || "").trim() : "";
        selectMovieInWizard({ id: "manual", name: queryTitle, title: queryTitle, provider: "manual" }, false);
    });
    bindClick(tabPoster, () => switchArtworkTab("poster"));
    bindClick(tabFanart, () => switchArtworkTab("fanart"));
    bindClick(retryBtn, () => typeof lastRetryAction === "function" && lastRetryAction());

    if (searchInput && typeof searchInput.addEventListener === "function") {
        searchInput.addEventListener("keydown", (e) => {
            if (e && e.key === "Enter") {
                if (typeof e.preventDefault === "function") e.preventDefault();
                performSearch();
            }
        });
    }
    if (typeof doc.addEventListener === "function") {
        doc.addEventListener("keydown", handleEscapeKey);
    }

    const instance = {
        modalOverlay,
        nfoEditor,
        open,
        close,
        goToStep,
        nextStep,
        prevStep,
        skipCurrentStep,
        selectMovieInWizard,
        performSearch,
        switchArtworkTab,
        handleEscapeKey,
        getHandoverPayload,
        triggerHandover,
        getCurrentStep: () => currentStep,
        isArtworkSkipped: () => artworkSkipped,
        getActiveArtworkTab: () => activeArtworkTab,
    };

    activeWizardInstance = instance;
    return instance;
}

export function initFilmWizard(options = {}) {
    if (!activeWizardInstance) activeWizardInstance = createFilmWizard(options);
    return activeWizardInstance;
}

export function openFilmWizard(openOptions = {}) {
    const wizard = initFilmWizard(openOptions);
    wizard.open(openOptions);
    return wizard;
}

export default { createFilmWizard, initFilmWizard, openFilmWizard };
