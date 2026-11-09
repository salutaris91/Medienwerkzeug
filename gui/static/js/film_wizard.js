import { renderNfoEditor, buildMovieNfoOverrides } from './nfo_editor.js?v=108';
import {
    renderPreviewData,
    collectPreviewSelection,
} from './preview_render.js?v=108';

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

function buildResultGroupDom(doc, key, titleText, initialCollapsed = false) {
    const collapsedCls = initialCollapsed ? " collapsed" : "";
    const contentHiddenCls = initialCollapsed ? " hidden" : "";
    return mkEl(
        doc,
        "div",
        { id: `mw-wizard-group-${key}`, cls: `mw-wizard-result-group${collapsedCls}` },
        [
            mkEl(
                doc,
                "button",
                {
                    id: `mw-wizard-group-header-${key}`,
                    cls: `mw-wizard-result-group-header${collapsedCls}`,
                    type: "button",
                    attrs: { "aria-expanded": initialCollapsed ? "false" : "true" },
                },
                [
                    mkEl(doc, "span", { id: `mw-wizard-group-title-${key}`, text: titleText }),
                    mkEl(doc, "span", { cls: "mw-wizard-result-group-chevron", text: "▼" }),
                ]
            ),
            mkEl(doc, "div", { id: `mw-wizard-list-${key}`, cls: `mw-wizard-result-group-content${contentHiddenCls}` }),
        ]
    );
}

function buildOptionsGroupDom(doc) {
    const optConvert = mkEl(doc, "input", { id: "mw-wizard-option-convert", type: "checkbox", attrs: { checked: "checked" } });
    optConvert.checked = true;

    const qualitySlider = mkEl(doc, "input", {
        id: "mw-wizard-quality-slider",
        type: "range",
        attrs: { min: "10", max: "100", value: "60", step: "1" },
    });
    qualitySlider.value = "60";

    const optDelete = mkEl(doc, "input", { id: "mw-wizard-option-delete", type: "checkbox", attrs: { checked: "checked" } });
    optDelete.checked = true;

    const optCopyNas = mkEl(doc, "input", { id: "mw-wizard-option-copy-nas", type: "checkbox", attrs: { checked: "checked" } });
    optCopyNas.checked = true;

    const nasSelect = mkEl(doc, "select", { id: "mw-wizard-nas-destination", cls: "mw-wizard-select" }, [
        mkEl(doc, "option", { text: "Filme", attrs: { value: "1" } }),
    ]);
    nasSelect.value = "1";

    const optCopyPcloud = mkEl(doc, "input", { id: "mw-wizard-option-copy-pcloud", type: "checkbox" });
    optCopyPcloud.checked = false;

    const pcloudSelect = mkEl(doc, "select", { id: "mw-wizard-pcloud-destination", cls: "mw-wizard-select" }, [
        mkEl(doc, "option", { text: "Filme", attrs: { value: "1" } }),
    ]);
    pcloudSelect.value = "1";

    const qualityLabel = mkEl(doc, "label", { cls: "mw-wizard-label", text: "Qualität: ", attrs: { for: "mw-wizard-quality-slider" } }, [
        mkEl(doc, "span", { id: "mw-wizard-quality-val", text: "60" }),
    ]);

    const optionsGrid = mkEl(doc, "div", { cls: "mw-wizard-options-grid" }, [
        mkEl(doc, "label", { cls: "mw-wizard-option-row" }, [
            optConvert,
            mkEl(doc, "span", { text: "Zu H.265 konvertieren" }),
        ]),
        mkEl(doc, "div", { id: "mw-wizard-quality-slider-container", cls: "mw-wizard-option-sub" }, [
            qualityLabel,
            qualitySlider,
        ]),
        mkEl(doc, "label", { cls: "mw-wizard-option-row" }, [
            optDelete,
            mkEl(doc, "span", { text: "Original löschen" }),
        ]),
        mkEl(doc, "label", { cls: "mw-wizard-option-row" }, [
            optCopyNas,
            mkEl(doc, "span", { text: "Auf NAS kopieren" }),
        ]),
        mkEl(doc, "div", { id: "mw-wizard-nas-destination-container", cls: "mw-wizard-option-sub" }, [
            mkEl(doc, "label", { cls: "mw-wizard-label", text: "NAS Ziel-Kategorie", attrs: { for: "mw-wizard-nas-destination" } }),
            nasSelect,
        ]),
        mkEl(doc, "label", { cls: "mw-wizard-option-row" }, [
            optCopyPcloud,
            mkEl(doc, "span", { text: "Auf pCloud kopieren" }),
        ]),
        mkEl(doc, "div", { id: "mw-wizard-pcloud-destination-container", cls: "mw-wizard-option-sub hidden" }, [
            mkEl(doc, "label", { cls: "mw-wizard-label", text: "pCloud Ziel-Kategorie", attrs: { for: "mw-wizard-pcloud-destination" } }),
            pcloudSelect,
        ]),
    ]);

    return mkEl(
        doc,
        "div",
        { id: "mw-wizard-group-options", cls: "mw-wizard-result-group collapsed" },
        [
            mkEl(
                doc,
                "button",
                {
                    id: "mw-wizard-group-header-options",
                    cls: "mw-wizard-result-group-header collapsed",
                    type: "button",
                    attrs: { "aria-expanded": "false" },
                },
                [
                    mkEl(doc, "span", { id: "mw-wizard-group-title-options", text: "Qualität & Conversion" }),
                    mkEl(doc, "span", { cls: "mw-wizard-result-group-chevron", text: "▼" }),
                ]
            ),
            mkEl(doc, "div", { id: "mw-wizard-options-content", cls: "mw-wizard-result-group-content hidden" }, [
                optionsGrid,
            ]),
        ]
    );
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
        [
            mkEl(doc, "div", { id: "mw-wizard-similar-existing", cls: "mw-wizard-similar-box hidden" }, [
                mkEl(doc, "div", { id: "mw-wizard-similar-existing-text", cls: "mw-wizard-similar-text" }),
            ]),
            mkEl(doc, "div", { cls: "mw-wizard-result-summary" }, [
                mkEl(doc, "div", { id: "mw-wizard-result-title", cls: "mw-wizard-result-title" }),
                mkEl(doc, "div", { cls: "mw-wizard-result-dest-label", text: "Zielpfad" }),
                mkEl(doc, "div", { id: "mw-wizard-destination", cls: "mw-wizard-result-destination", text: "Wird berechnet..." }),
                mkEl(doc, "div", { id: "mw-wizard-summary", cls: "mw-wizard-summary" }),
            ]),
            buildResultGroupDom(doc, "renames", "Umbenennungen (0)", false),
            buildResultGroupDom(doc, "subs", "Untertitel (0)", false),
            buildResultGroupDom(doc, "junk", "Junk-Dateien (0)", false),
            buildOptionsGroupDom(doc),
        ]
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
            mkEl(doc, "button", { id: "mw-wizard-btn-execute", cls: "mw-modal-btn mw-modal-btn-confirm hidden", type: "button", text: "Jetzt final verarbeiten" }),
        ]),
    ]);
    modalOverlay.appendChild(modal);
}

export function createFilmWizard(options = {}) {
    const doc = options.document || (typeof document !== "undefined" ? document : null);
    if (!doc) throw new Error("createFilmWizard requires a document");

    const fetchFn = options.fetch || (typeof fetch === "function" ? fetch.bind(globalThis) : null);
    const confirmFn = options.confirm || (typeof confirm === "function" ? confirm.bind(globalThis) : () => true);
    let logFn = options.onLog || (typeof globalThis.appendConsoleLog === "function" ? globalThis.appendConsoleLog : null);

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
    const executeBtn = getEl("mw-wizard-btn-execute");
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
    const resultTitleEl = getEl("mw-wizard-result-title");
    const destEl = getEl("mw-wizard-destination");
    const similarExistingBox = getEl("mw-wizard-similar-existing");
    const similarExistingText = getEl("mw-wizard-similar-existing-text");
    const listRenames = getEl("mw-wizard-list-renames");
    const listSubs = getEl("mw-wizard-list-subs");
    const listJunk = getEl("mw-wizard-list-junk");
    const errorBanner = getEl("mw-wizard-error-banner");
    const errorText = getEl("mw-wizard-error-text");
    const retryBtn = getEl("mw-wizard-error-retry");

    const optConvert = getEl("mw-wizard-option-convert");
    const optQualityContainer = getEl("mw-wizard-quality-slider-container");
    const optQualitySlider = getEl("mw-wizard-quality-slider");
    const optQualityVal = getEl("mw-wizard-quality-val");
    const optDelete = getEl("mw-wizard-option-delete");
    const optCopyNas = getEl("mw-wizard-option-copy-nas");
    const optNasContainer = getEl("mw-wizard-nas-destination-container");
    const optNasDest = getEl("mw-wizard-nas-destination");
    const optCopyPcloud = getEl("mw-wizard-option-copy-pcloud");
    const optPcloudContainer = getEl("mw-wizard-pcloud-destination-container");
    const optPcloudDest = getEl("mw-wizard-pcloud-destination");

    let currentStep = 1;
    let selectedMovie = null;
    let currentProjectName = options.projectName || "";
    let artworkSkipped = false;
    let activeArtworkTab = "poster";
    let onHandoverCallback = options.onHandover || null;
    let onProcessSuccessCallback = options.onProcessSuccess || null;
    let lastRetryAction = null;
    let sessionSeq = 0;
    let metadataRequestSeq = 0;
    let previewRequestSeq = 0;
    let currentPreviewPayload = null;
    let hasValidPreview = false;
    let isExecutingProcess = false;
    const previewCheckboxState = {
        renames: new Map(),
        subs: new Map(),
        junk: new Map(),
    };

    const nfoEditor = renderNfoEditor(editorContainer, {}, { idPrefix: "mw-wizard-nfo" });

    function clearPreviewCheckboxState() {
        previewCheckboxState.renames.clear();
        previewCheckboxState.subs.clear();
        previewCheckboxState.junk.clear();
        if (listRenames) listRenames.innerHTML = "";
        if (listSubs) listSubs.innerHTML = "";
        if (listJunk) listJunk.innerHTML = "";
    }

    function snapshotPreviewCheckboxState() {
        const groups = [
            ["renames", listRenames],
            ["subs", listSubs],
            ["junk", listJunk],
        ];
        for (const [group, container] of groups) {
            if (!container || typeof container.querySelectorAll !== "function") continue;
            const cbs = container.querySelectorAll(`.preview-cb-${group}`);
            for (const cb of cbs) {
                const key = (cb.dataset && cb.dataset.old !== undefined ? cb.dataset.old : cb.getAttribute("data-old")) || "";
                if (key) {
                    previewCheckboxState[group].set(key, Boolean(cb.checked));
                }
            }
        }
    }

    function isPreviewItemChecked(entry, groupName) {
        const rawOld = (typeof entry === "object" && entry !== null) ? (entry.old || "") : (entry || "");
        const groupMap = previewCheckboxState[groupName];
        if (groupMap && groupMap.has(rawOld)) {
            return groupMap.get(rawOld);
        }
        return true;
    }

    function updateExecuteButtonState() {
        if (!executeBtn) return;
        executeBtn.disabled = Boolean(isExecutingProcess || currentStep !== 4 || !hasValidPreview);
        if (!isExecutingProcess) {
            executeBtn.textContent = "Jetzt final verarbeiten";
        }
    }

    function hideError() {
        if (errorBanner) errorBanner.classList.add("hidden");
        lastRetryAction = null;
    }

    function showError(message, retryAction = null) {
        if (errorText) errorText.textContent = message;
        if (errorBanner) errorBanner.classList.remove("hidden");
        if (currentStep === 2 && providerBadge) {
            providerBadge.textContent = "Nicht erreichbar";
            providerBadge.classList.remove("mw-wizard-badge-loading");
            providerBadge.classList.add("mw-wizard-badge-error");
        }
        lastRetryAction = retryAction;
    }

    function setGroupCollapsed(groupEl, headerEl, contentEl, collapsed) {
        const isCollapsed = Boolean(collapsed);
        if (groupEl && groupEl.classList) groupEl.classList.toggle("collapsed", isCollapsed);
        if (headerEl && headerEl.classList) headerEl.classList.toggle("collapsed", isCollapsed);
        if (headerEl && typeof headerEl.setAttribute === "function") {
            headerEl.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
        }
        if (contentEl && contentEl.classList) contentEl.classList.toggle("hidden", isCollapsed);
    }

    function bindGroupToggle(groupId, headerId, contentId) {
        const groupEl = getEl(groupId);
        const headerEl = getEl(headerId);
        const contentEl = getEl(contentId);
        if (!headerEl || typeof headerEl.addEventListener !== "function") return;
        headerEl.addEventListener("click", () => {
            const currentlyCollapsed = groupEl && groupEl.classList
                ? groupEl.classList.contains("collapsed")
                : Boolean(contentEl && contentEl.classList && contentEl.classList.contains("hidden"));
            setGroupCollapsed(groupEl, headerEl, contentEl, !currentlyCollapsed);
        });
    }

    function applyResultGroupState(key, labelPrefix, items) {
        const count = Array.isArray(items) ? items.length : 0;
        const titleEl = getEl(`mw-wizard-group-title-${key}`);
        if (titleEl) titleEl.textContent = `${labelPrefix} (${count})`;
        const groupEl = getEl(`mw-wizard-group-${key}`);
        const headerEl = getEl(`mw-wizard-group-header-${key}`);
        const contentEl = getEl(`mw-wizard-list-${key}`);
        setGroupCollapsed(groupEl, headerEl, contentEl, count > 3);
    }

    function updateOptionSubcontainers() {
        if (optQualityContainer && optConvert) {
            optQualityContainer.classList.toggle("hidden", !optConvert.checked);
        }
        if (optNasContainer && optCopyNas) {
            optNasContainer.classList.toggle("hidden", !optCopyNas.checked);
        }
        if (optPcloudContainer && optCopyPcloud) {
            optPcloudContainer.classList.toggle("hidden", !optCopyPcloud.checked);
        }
        if (optQualityVal && optQualitySlider) {
            optQualityVal.textContent = String(optQualitySlider.value || "60");
        }
    }

    function syncWizardOptionsFromContext(openOptions = {}) {
        const ctxConvert = getEl("movie-option-convert");
        const ctxDelete = getEl("movie-option-delete");
        const ctxCopyNas = getEl("movie-option-copy-nas");
        const ctxCopyPcloud = getEl("movie-option-copy-pcloud");
        const ctxQuality = getEl("movie-quality-slider");
        const ctxNasDest = getEl("movie-nas-destination");
        const ctxPcloudDest = getEl("movie-pcloud-destination");

        let storedSettings = null;
        try {
            if (typeof localStorage !== "undefined" && typeof localStorage.getItem === "function") {
                const raw = localStorage.getItem("conversionSettings");
                if (raw) storedSettings = JSON.parse(raw);
            }
        } catch (_) {}

        if (optConvert) {
            optConvert.checked = (ctxConvert && ctxConvert.tagName === "INPUT")
                ? Boolean(ctxConvert.checked)
                : (storedSettings && storedSettings.movieOptionConvert !== undefined ? Boolean(storedSettings.movieOptionConvert) : true);
        }
        if (optDelete) {
            optDelete.checked = (ctxDelete && ctxDelete.tagName === "INPUT")
                ? Boolean(ctxDelete.checked)
                : (storedSettings && storedSettings.movieOptionDelete !== undefined ? Boolean(storedSettings.movieOptionDelete) : true);
        }
        if (optCopyNas) {
            optCopyNas.checked = (ctxCopyNas && ctxCopyNas.tagName === "INPUT")
                ? Boolean(ctxCopyNas.checked)
                : (storedSettings && storedSettings.movieOptionCopyNas !== undefined ? Boolean(storedSettings.movieOptionCopyNas) : true);
        }
        if (optCopyPcloud) {
            optCopyPcloud.checked = (ctxCopyPcloud && ctxCopyPcloud.tagName === "INPUT")
                ? Boolean(ctxCopyPcloud.checked)
                : (storedSettings && storedSettings.movieOptionCopyPcloud !== undefined ? Boolean(storedSettings.movieOptionCopyPcloud) : false);
        }
        if (optQualitySlider) {
            optQualitySlider.value = (ctxQuality && ctxQuality.tagName === "INPUT" && ctxQuality.value !== "")
                ? String(ctxQuality.value)
                : (storedSettings && storedSettings.movieQualitySlider !== undefined ? String(storedSettings.movieQualitySlider) : "60");
        }
        if (optNasDest) {
            if (ctxNasDest && ctxNasDest.tagName === "SELECT") {
                if (ctxNasDest.options && ctxNasDest.options.length > 0 && (!optNasDest.options || optNasDest.options.length <= 1)) {
                    optNasDest.innerHTML = ctxNasDest.innerHTML;
                }
                if (ctxNasDest.value) optNasDest.value = ctxNasDest.value;
            }
            if (!optNasDest.value) optNasDest.value = "1";
        }
        if (optPcloudDest) {
            if (ctxPcloudDest && ctxPcloudDest.tagName === "SELECT") {
                if (ctxPcloudDest.options && ctxPcloudDest.options.length > 0 && (!optPcloudDest.options || optPcloudDest.options.length <= 1)) {
                    optPcloudDest.innerHTML = ctxPcloudDest.innerHTML;
                }
                if (ctxPcloudDest.value) optPcloudDest.value = ctxPcloudDest.value;
            }
            if (!optPcloudDest.value) optPcloudDest.value = "1";
        }

        if (openOptions && openOptions.options && typeof openOptions.options === "object") {
            const o = openOptions.options;
            if (optConvert && o.convert !== undefined) optConvert.checked = Boolean(o.convert);
            if (optDelete && o.delete_original !== undefined) optDelete.checked = Boolean(o.delete_original);
            if (optCopyNas && o.copy_to_nas !== undefined) optCopyNas.checked = Boolean(o.copy_to_nas);
            if (optCopyPcloud && o.copy_to_pcloud !== undefined) optCopyPcloud.checked = Boolean(o.copy_to_pcloud);
            if (optQualitySlider && o.quality !== undefined) optQualitySlider.value = String(o.quality);
            if (optNasDest && o.nas_destination_id !== undefined) optNasDest.value = String(o.nas_destination_id);
            if (optPcloudDest && o.pcloud_destination_id !== undefined) optPcloudDest.value = String(o.pcloud_destination_id);
        }

        updateOptionSubcontainers();
    }

    function syncOptionBackToContext(wizardEl, contextId, prop = "checked") {
        const ctxEl = getEl(contextId);
        if (!wizardEl || !ctxEl || (ctxEl.tagName !== "INPUT" && ctxEl.tagName !== "SELECT")) return;
        ctxEl[prop] = wizardEl[prop];
        if (typeof ctxEl.dispatchEvent === "function" && typeof Event === "function") {
            try {
                ctxEl.dispatchEvent(new Event("change"));
            } catch (_) {}
        }
    }

    function buildMovieBasePayload() {
        const overrides = typeof nfoEditor.buildWizardMovieOverrides === "function"
            ? nfoEditor.buildWizardMovieOverrides()
            : buildMovieNfoOverrides(nfoEditor);
        const currentVals = nfoEditor.getValues();
        const baseMovie = selectedMovie || {
            id: "manual",
            name: currentVals.title || "Unbekannter Film",
            provider: "manual",
        };

        let titleVal = String(currentVals.title || baseMovie.name || "").trim();
        titleVal = titleVal.replace(/\s*\(Mediathek.*?\)/g, "").replace(/\s*\(Freie Mediathek.*?\)/g, "").trim();

        const yearVal = String(currentVals.year || "").trim();
        let finalMovieName = titleVal;
        if (yearVal && /^\d{4}$/.test(yearVal)) {
            titleVal = titleVal.replace(/\s*\(\d{4}\)$/, "").trim();
            finalMovieName = `${titleVal} (${yearVal})`;
        }

        const convert = optConvert ? Boolean(optConvert.checked) : true;
        const deleteOrig = optDelete ? Boolean(optDelete.checked) : true;
        const copyNas = optCopyNas ? Boolean(optCopyNas.checked) : true;
        const copyPcloud = optCopyPcloud ? Boolean(optCopyPcloud.checked) : false;
        const nasDestId = (optNasDest && optNasDest.value) ? String(optNasDest.value) : "1";
        const pcloudDestId = (optPcloudDest && optPcloudDest.value) ? String(optPcloudDest.value) : "1";
        const parsedQuality = optQualitySlider ? parseInt(optQualitySlider.value, 10) : 60;
        const quality = isNaN(parsedQuality) ? 60 : parsedQuality;

        return {
            media_type: "movie",
            project_name: currentProjectName,
            movie_name: finalMovieName,
            movie_id: String(baseMovie.id || "manual"),
            provider: String(baseMovie.provider || "manual"),
            convert,
            quality,
            delete_original: deleteOrig,
            copy_to_nas: copyNas,
            copy_to_pcloud: copyPcloud,
            destination_id: nasDestId,
            nas_destination_id: nasDestId,
            pcloud_destination_id: pcloudDestId,
            overwrite_nfo: false,
            wizard_overrides: true,
            nfo_overrides: overrides,
        };
    }

    function buildProcessPayload() {
        const basePayload = buildMovieBasePayload();
        const selection = collectPreviewSelection({
            listRenames,
            listSubs,
            listJunk,
            root: panels[3] || modalOverlay,
        });
        return {
            ...basePayload,
            explicit_renames: selection.explicit_renames,
            explicit_subs: selection.explicit_subs,
            explicit_junk: selection.explicit_junk,
        };
    }

    function renderSummary() {
        const vals = nfoEditor.getValues();
        const baseTitle = vals.title || (selectedMovie ? selectedMovie.name : "—");
        const yearSuffix = vals.year && /^\d{4}$/.test(String(vals.year).trim()) ? ` (${String(vals.year).trim()})` : "";
        if (resultTitleEl) {
            resultTitleEl.textContent = `${baseTitle}${yearSuffix}`;
        }
        if (!summaryBox) return;
        summaryBox.innerHTML = "";
        const lines = [
            `Titel: ${baseTitle}`,
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

    async function loadStep4Preview() {
        snapshotPreviewCheckboxState();
        const reqSeq = ++previewRequestSeq;
        const reqSession = sessionSeq;
        hideError();
        const basePayload = buildMovieBasePayload();
        hasValidPreview = false;
        currentPreviewPayload = null;
        updateExecuteButtonState();

        if (similarExistingBox && similarExistingBox.classList) {
            similarExistingBox.classList.add("hidden");
        }
        if (similarExistingText) {
            similarExistingText.innerHTML = "";
        }
        if (destEl) {
            destEl.textContent = "Wird berechnet...";
        }
        if (listRenames) {
            listRenames.innerHTML = `<div class="mw-wizard-result-empty">Analysiere Ordner und Metadaten...</div>`;
        }
        if (listSubs) listSubs.innerHTML = "";
        if (listJunk) listJunk.innerHTML = "";

        if (!fetchFn) return null;

        try {
            const res = await fetchFn("/api/preview_process", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(basePayload),
            });
            if (reqSeq !== previewRequestSeq || reqSession !== sessionSeq || currentStep !== 4) return null;

            if (!res || !res.ok) {
                let errorMsg = `HTTP ${res ? res.status : "Fehler"}`;
                if (res && typeof res.json === "function") {
                    try {
                        const errData = await res.json();
                        if (errData && (errData.error || errData.message)) {
                            errorMsg = errData.error || errData.message;
                        }
                    } catch (_) {}
                }
                throw new Error(errorMsg);
            }

            const data = await res.json();
            if (reqSeq !== previewRequestSeq || reqSession !== sessionSeq || currentStep !== 4) return null;
            if (data && data.error) {
                throw new Error(data.error);
            }

            applyResultGroupState("renames", "Umbenennungen", data ? data.renames : []);
            applyResultGroupState("subs", "Untertitel", data ? data.subs : []);
            applyResultGroupState("junk", "Junk-Dateien", data ? data.junk : []);

            renderPreviewData(
                {
                    similarBox: similarExistingBox,
                    similarText: similarExistingText,
                    dest: destEl,
                    listRenames,
                    listSubs,
                    listJunk,
                },
                data || {},
                {
                    idPrefix: "mw-wizard-similar",
                    onLog: logFn,
                    isItemChecked: isPreviewItemChecked,
                }
            );

            snapshotPreviewCheckboxState();
            currentPreviewPayload = basePayload;
            hasValidPreview = true;
            updateExecuteButtonState();

            return data;
        } catch (err) {
            if (reqSeq !== previewRequestSeq || reqSession !== sessionSeq || currentStep !== 4) return null;
            hasValidPreview = false;
            currentPreviewPayload = null;
            updateExecuteButtonState();
            const msg = err && err.message ? err.message : String(err);
            if (destEl) destEl.textContent = "Vorschau konnte nicht geladen werden.";
            if (listRenames) listRenames.innerHTML = "";
            showError(`Vorschau fehlgeschlagen: ${msg}`, () => loadStep4Preview());
            if (logFn) {
                try {
                    logFn(`[System]: Vorschau fehlgeschlagen: ${msg}`);
                } catch (_) {}
            }
            return null;
        }
    }

    async function executeStep4Process() {
        if (isExecutingProcess) return null;
        if (currentStep !== 4 || !hasValidPreview || !currentPreviewPayload) return null;
        if (executeBtn && executeBtn.disabled) return null;
        if (!fetchFn) return null;

        hideError();
        const procSession = sessionSeq;
        const sessionSuccessCb = onProcessSuccessCallback;
        isExecutingProcess = true;
        if (executeBtn) {
            executeBtn.disabled = true;
            executeBtn.textContent = "wird gestartet…";
        }

        const finalPayload = buildProcessPayload();

        try {
            const res = await fetchFn("/api/process", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(finalPayload),
            });

            if (res && res.ok) {
                isExecutingProcess = false;
                updateExecuteButtonState();
                if (procSession === sessionSeq) {
                    close({ force: true });
                    if (typeof sessionSuccessCb === "function") {
                        sessionSuccessCb(finalPayload);
                    }
                }
                return finalPayload;
            }

            let errorMsg = `HTTP ${res ? res.status : "Fehler"}`;
            if (res && typeof res.json === "function") {
                try {
                    const errData = await res.json();
                    if (errData && (errData.error || errData.message)) {
                        errorMsg = errData.error || errData.message;
                    }
                } catch (_) {}
            }
            isExecutingProcess = false;
            updateExecuteButtonState();
            if (procSession === sessionSeq) {
                showError(`Fehler beim Starten des Prozesses: ${errorMsg}`, () => executeStep4Process());
                if (logFn) {
                    try {
                        logFn(`[System] Fehler beim Starten des Prozesses: ${errorMsg}`);
                    } catch (_) {}
                }
            }
            return null;
        } catch (err) {
            isExecutingProcess = false;
            updateExecuteButtonState();
            if (procSession === sessionSeq) {
                const msg = err && err.message ? err.message : String(err);
                showError(`Fehler beim Starten des Prozesses: ${msg}`, () => executeStep4Process());
                if (logFn) {
                    try {
                        logFn(`[System] Fehler: ${msg}`);
                    } catch (_) {}
                }
            }
            return null;
        }
    }

    function goToStep(stepNumber) {
        const nextStepNum = Math.max(1, Math.min(4, Number(stepNumber) || 1));
        if (currentStep === 4 && nextStepNum !== 4) {
            snapshotPreviewCheckboxState();
            previewRequestSeq += 1;
            hasValidPreview = false;
            currentPreviewPayload = null;
        }
        currentStep = nextStepNum;
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
        if (executeBtn) executeBtn.classList.toggle("hidden", currentStep !== 4);
        if (handoverBtn) handoverBtn.classList.add("hidden");
        updateExecuteButtonState();
        if (currentStep === 4) {
            renderSummary();
            loadStep4Preview();
        }
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
        sessionSeq += 1;
        metadataRequestSeq += 1;
        previewRequestSeq += 1;
        hasValidPreview = false;
        currentPreviewPayload = null;
        clearPreviewCheckboxState();
        hideError();
        artworkSkipped = false;
        switchArtworkTab("poster");
        if (openOptions.projectName !== undefined) currentProjectName = String(openOptions.projectName || "");
        if (openOptions.onHandover) onHandoverCallback = openOptions.onHandover;
        if (openOptions.onProcessSuccess) onProcessSuccessCallback = openOptions.onProcessSuccess;
        if (openOptions.onLog) logFn = openOptions.onLog;
        syncWizardOptionsFromContext(openOptions);

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
        updateExecuteButtonState();
        modalOverlay.classList.remove("hidden");
        modalOverlay.classList.add("active");
        if (initialQuery && openOptions.autoSearch !== false && fetchFn) {
            performSearch(initialQuery);
        }
    }

    function close({ force = false } = {}) {
        if (isExecutingProcess && !force) return false;
        if (!force && nfoEditor.isDirty()) {
            if (!confirmFn("Änderungen im Film-Assistenten verwerfen?")) return false;
        }
        sessionSeq += 1;
        metadataRequestSeq += 1;
        previewRequestSeq += 1;
        hasValidPreview = false;
        currentPreviewPayload = null;
        updateExecuteButtonState();
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
        if (isExecutingProcess) return currentStep;
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
        if (isExecutingProcess) return currentStep;
        return currentStep > 1 ? goToStep(currentStep - 1) : currentStep;
    }

    function skipCurrentStep() {
        if (isExecutingProcess) return currentStep;
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
    bindClick(executeBtn, () => executeStep4Process());
    bindClick(handoverBtn, () => triggerHandover());
    bindClick(searchBtn, () => performSearch());
    bindClick(manualBtn, () => {
        const queryTitle = searchInput ? String(searchInput.value || "").trim() : "";
        selectMovieInWizard({ id: "manual", name: queryTitle, title: queryTitle, provider: "manual" }, false);
    });
    bindClick(tabPoster, () => switchArtworkTab("poster"));
    bindClick(tabFanart, () => switchArtworkTab("fanart"));
    bindClick(retryBtn, () => typeof lastRetryAction === "function" && lastRetryAction());

    bindGroupToggle("mw-wizard-group-renames", "mw-wizard-group-header-renames", "mw-wizard-list-renames");
    bindGroupToggle("mw-wizard-group-subs", "mw-wizard-group-header-subs", "mw-wizard-list-subs");
    bindGroupToggle("mw-wizard-group-junk", "mw-wizard-group-header-junk", "mw-wizard-list-junk");
    bindGroupToggle("mw-wizard-group-options", "mw-wizard-group-header-options", "mw-wizard-options-content");

    if (optConvert && typeof optConvert.addEventListener === "function") {
        optConvert.addEventListener("change", () => {
            updateOptionSubcontainers();
            syncOptionBackToContext(optConvert, "movie-option-convert", "checked");
        });
    }
    if (optDelete && typeof optDelete.addEventListener === "function") {
        optDelete.addEventListener("change", () => {
            syncOptionBackToContext(optDelete, "movie-option-delete", "checked");
        });
    }
    if (optQualitySlider && typeof optQualitySlider.addEventListener === "function") {
        const onQualityChange = () => {
            updateOptionSubcontainers();
            syncOptionBackToContext(optQualitySlider, "movie-quality-slider", "value");
        };
        optQualitySlider.addEventListener("input", onQualityChange);
        optQualitySlider.addEventListener("change", onQualityChange);
    }
    if (optCopyNas && typeof optCopyNas.addEventListener === "function") {
        optCopyNas.addEventListener("change", () => {
            updateOptionSubcontainers();
            syncOptionBackToContext(optCopyNas, "movie-option-copy-nas", "checked");
            if (currentStep === 4) loadStep4Preview();
        });
    }
    if (optCopyPcloud && typeof optCopyPcloud.addEventListener === "function") {
        optCopyPcloud.addEventListener("change", () => {
            updateOptionSubcontainers();
            syncOptionBackToContext(optCopyPcloud, "movie-option-copy-pcloud", "checked");
            if (currentStep === 4) loadStep4Preview();
        });
    }
    if (optNasDest && typeof optNasDest.addEventListener === "function") {
        optNasDest.addEventListener("change", () => {
            syncOptionBackToContext(optNasDest, "movie-nas-destination", "value");
            if (currentStep === 4) loadStep4Preview();
        });
    }
    if (optPcloudDest && typeof optPcloudDest.addEventListener === "function") {
        optPcloudDest.addEventListener("change", () => {
            syncOptionBackToContext(optPcloudDest, "movie-pcloud-destination", "value");
            if (currentStep === 4) loadStep4Preview();
        });
    }

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
        buildMovieBasePayload,
        buildProcessPayload,
        loadStep4Preview,
        executeStep4Process,
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
