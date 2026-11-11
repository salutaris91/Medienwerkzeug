import { renderNfoEditor, buildMovieNfoOverrides, formatProviderLabel } from './nfo_editor.js?v=118';
import { formatBytes } from './format.js?v=118';
import {
    renderPreviewData,
    collectPreviewSelection,
} from './preview_render.js?v=118';

let activeWizardInstance = null;

function parseSearchItemTitleAndYear(item) {
    const rawName = String(item?.name || item?.title || "").trim();
    const yearMatch = rawName.match(/\((\d{4})\)\s*$/);
    const year = yearMatch ? yearMatch[1] : String(item?.year || "").trim();
    const titlePart = rawName.replace(/\s*\((?:\d{4}|\?\?\?\?)\)\s*$/, "").trim();
    const normTitle = titlePart.toLowerCase().replace(/[^a-z0-9äöüß]+/gi, "");
    return { normTitle, year };
}

function findCounterpartInSearchResults(clickedItem, results) {
    if (!clickedItem || !Array.isArray(results) || results.length === 0) return null;
    const clickedProv = String(clickedItem.provider || "tmdb").toLowerCase() === "tmdb_movie"
        ? "tmdb"
        : String(clickedItem.provider || "tmdb").toLowerCase();
    const targetProv = clickedProv === "ofdb" ? "tmdb" : "ofdb";
    const { normTitle, year } = parseSearchItemTitleAndYear(clickedItem);
    if (!normTitle) return null;

    for (const cand of results) {
        const candProv = String(cand?.provider || "tmdb").toLowerCase() === "tmdb_movie"
            ? "tmdb"
            : String(cand?.provider || "tmdb").toLowerCase();
        if (candProv !== targetProv) continue;
        const candParsed = parseSearchItemTitleAndYear(cand);
        if (candParsed.normTitle !== normTitle) continue;
        if (year && candParsed.year && year !== candParsed.year) continue;
        return {
            id: String(cand.id ?? ""),
            name: String(cand.name || cand.title || ""),
            provider: candProv,
        };
    }
    return null;
}

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
        mkEl(doc, "div", { id: "mw-wizard-size-estimate", cls: "mw-wizard-size-estimate hidden" }),
    ]);

    // NAS/pCloud targets live next to the destination path (summary card), not in this group.
    const targetsBlock = mkEl(doc, "div", { id: "mw-wizard-targets", cls: "mw-wizard-targets" }, [
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

    const group = mkEl(
        doc,
        "div",
        { id: "mw-wizard-group-options", cls: "mw-wizard-result-group" },
        [
            mkEl(
                doc,
                "button",
                {
                    id: "mw-wizard-group-header-options",
                    cls: "mw-wizard-result-group-header",
                    type: "button",
                    attrs: { "aria-expanded": "true" },
                },
                [
                    mkEl(doc, "span", { id: "mw-wizard-group-title-options", text: "Qualität & Conversion" }),
                    mkEl(doc, "span", { id: "mw-wizard-options-summary", cls: "mw-wizard-options-summary" }),
                    mkEl(doc, "span", { cls: "mw-wizard-result-group-chevron", text: "▼" }),
                ]
            ),
            mkEl(doc, "div", { id: "mw-wizard-options-content", cls: "mw-wizard-result-group-content" }, [
                optionsGrid,
            ]),
        ]
    );
    return { group, targetsBlock };
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

    const optionsDom = buildOptionsGroupDom(doc);
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
                optionsDom.targetsBlock,
                mkEl(doc, "div", { id: "mw-wizard-summary", cls: "mw-wizard-summary" }),
            ]),
            buildResultGroupDom(doc, "renames", "Umbenennungen (0)", false),
            buildResultGroupDom(doc, "subs", "Untertitel & Extras (0)", false),
            buildResultGroupDom(doc, "junk", "Junk-Dateien (0)", false),
            optionsDom.group,
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
    let selectedProviders = [];
    const successfulProviders = new Map();
    let lastSearchResults = [];
    let currentProjectName = options.projectName || "";
    let artworkSkipped = false;
    let activeArtworkTab = "poster";
    let onProcessSuccessCallback = options.onProcessSuccess || null;
    // Called after every successful close (×, ESC, after starting the process) so the app can leave
    // the project view instead of falling back to the legacy movie panel.
    let onClosedCallback = options.onClosed || null;
    let lastRetryAction = null;
    let sessionSeq = 0;
    let metadataRequestSeq = 0;
    let previewRequestSeq = 0;
    let currentPreviewPayload = null;
    let hasValidPreview = false;
    let isExecutingProcess = false;
    let sizeEstimateSeq = 0;
    let lastSizeEstimateText = "";
    let lastPreviewVideoFiles = [];
    const sizeEstimateCache = new Map();
    const sizeEstimateInFlight = new Map();
    let persistOptionsCallback = options.onPersistOptions || null;
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
        // Empty groups start collapsed (the "(0)" in the header is enough), long lists too.
        setGroupCollapsed(groupEl, headerEl, contentEl, count === 0 || count > 3);
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
        updateOptionsSummary();
    }

    // An NFO that already lies in the inbox folder is listed by the backend as an "extra" to rename.
    // The wizard always writes its own NFO, so the old one is offered as junk instead (sent to the
    // trash before the new NFO is written). If the user unchecks it, the backend moves the old
    // file with its old name into the target folder next to the new NFO (same as before E2).
    function moveExistingNfoToJunk(data) {
        const subs = Array.isArray(data.subs) ? data.subs : [];
        const junk = Array.isArray(data.junk) ? data.junk.slice() : [];
        const keptSubs = [];
        let movedNfoCount = 0;
        for (const entry of subs) {
            const oldName = (entry && typeof entry === "object") ? String(entry.old || "") : String(entry || "");
            if (/\.nfo$/i.test(oldName)) {
                if (!junk.includes(oldName)) junk.push(oldName);
                movedNfoCount += 1;
            } else {
                keptSubs.push(entry);
            }
        }
        return {
            ...data,
            renames: Array.isArray(data.renames) ? data.renames : [],
            subs: keptSubs,
            junk,
            movedNfoCount,
        };
    }

    function renderExistingNfoNote(movedNfoCount) {
        if (!listJunk || !movedNfoCount) return;
        listJunk.appendChild(mkEl(doc, "div", {
            id: "mw-wizard-junk-nfo-note",
            cls: "mw-wizard-result-note",
            text: "Vorhandene NFO wird in den Papierkorb verschoben und automatisch durch die neue NFO aus dem Assistenten ersetzt.",
        }));
    }

    // The preview's renames only contain the main video file(s); no extension filter needed
    // (the backend also accepts .ts/.m2ts/.wmv etc.).
    function extractVideoFiles(renames) {
        const list = Array.isArray(renames) ? renames : [];
        return list
            .map((entry) => ((entry && typeof entry === "object") ? String(entry.old || "") : String(entry || "")))
            .filter(Boolean);
    }

    function persistOptions() {
        if (typeof persistOptionsCallback !== "function") return;
        try {
            persistOptionsCallback();
        } catch (err) {
            if (logFn) {
                try { logFn(`[System]: Einstellungen aus dem Film-Assistenten konnten nicht gespeichert werden: ${err && err.message ? err.message : err}`); } catch (_) {}
            }
        }
    }

    function resetSizeEstimate() {
        sizeEstimateSeq += 1;
        lastSizeEstimateText = "";
        const estimateEl = getEl("mw-wizard-size-estimate");
        if (estimateEl) {
            estimateEl.classList.add("hidden");
            estimateEl.textContent = "";
        }
        updateOptionsSummary();
    }

    function showSizeEstimateResult(estimateEl, result) {
        lastSizeEstimateText = result.summaryText;
        estimateEl.textContent = result.detailText;
        updateOptionsSummary();
    }

    // Runs one forecast request and turns the answer into display texts. Shared per cache key while
    // in flight, so a preview reload during a running forecast does not start a second ffmpeg test run.
    function requestSizeEstimate(cacheKey, quality) {
        if (sizeEstimateInFlight.has(cacheKey)) return sizeEstimateInFlight.get(cacheKey);
        const pending = (async () => {
            const res = await fetchFn("/api/estimate-conversion", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_name: currentProjectName, filenames: lastPreviewVideoFiles, quality }),
            });
            if (!res || !res.ok) throw new Error(`HTTP ${res ? res.status : "Fehler"}`);
            const data = await res.json();
            let sizeIn = 0;
            let sizeOut = 0;
            let firstFileError = "";
            for (const est of Object.values((data && data.estimates) || {})) {
                if (est && est.size_in !== undefined && est.size_out !== undefined) {
                    sizeIn += est.size_in;
                    sizeOut += est.size_out;
                } else if (est && est.error && !firstFileError) {
                    firstFileError = String(est.error);
                }
            }
            if (sizeIn > 0) {
                const pct = Math.round(((sizeIn - sizeOut) / sizeIn) * 100);
                const result = {
                    ok: true,
                    summaryText: `~${formatBytes(sizeOut)}`,
                    detailText: `Voraussichtliche Größe: ${formatBytes(sizeIn)} → ~${formatBytes(sizeOut)} (-${pct}%)`,
                };
                // Cache even if the caller has moved on: the result stays valid for these parameters.
                sizeEstimateCache.set(cacheKey, result);
                return result;
            }
            return {
                ok: false,
                summaryText: "",
                detailText: firstFileError
                    ? `Größenprognose nicht verfügbar (${firstFileError}).`
                    : "Größenprognose nicht verfügbar.",
            };
        })();
        sizeEstimateInFlight.set(cacheKey, pending);
        pending.then(
            () => sizeEstimateInFlight.delete(cacheKey),
            () => sizeEstimateInFlight.delete(cacheKey)
        );
        return pending;
    }

    // Size forecast via the existing /api/estimate-conversion (short test conversion, ~15 s).
    // Only runs with H.265 enabled; stale answers are discarded, errors are shown but never block.
    async function refreshSizeEstimate() {
        const estimateEl = getEl("mw-wizard-size-estimate");
        const reqSeq = ++sizeEstimateSeq;
        lastSizeEstimateText = "";
        updateOptionsSummary();
        if (!estimateEl) return null;
        const convertOn = optConvert ? Boolean(optConvert.checked) : false;
        if (!convertOn || lastPreviewVideoFiles.length === 0 || !fetchFn || !currentProjectName) {
            estimateEl.classList.add("hidden");
            estimateEl.textContent = "";
            return null;
        }
        const quality = optQualitySlider ? parseInt(optQualitySlider.value, 10) || 60 : 60;
        estimateEl.classList.remove("hidden");
        // Same project, files and quality -> reuse the last result instead of another ffmpeg test run.
        const cacheKey = JSON.stringify([currentProjectName, lastPreviewVideoFiles, quality]);
        if (sizeEstimateCache.has(cacheKey)) {
            showSizeEstimateResult(estimateEl, sizeEstimateCache.get(cacheKey));
            return null;
        }
        estimateEl.textContent = "Größenprognose läuft (Test-Konvertierung, ca. 15 Sek.)…";
        try {
            const result = await requestSizeEstimate(cacheKey, quality);
            if (reqSeq !== sizeEstimateSeq) return null;
            if (result.ok) {
                showSizeEstimateResult(estimateEl, result);
            } else {
                estimateEl.textContent = result.detailText;
                updateOptionsSummary();
            }
            return result;
        } catch (err) {
            if (reqSeq !== sizeEstimateSeq) return null;
            const msg = err && err.message ? err.message : String(err);
            estimateEl.textContent = `Größenprognose fehlgeschlagen (${msg}).`;
            if (logFn) {
                try { logFn(`[System]: Größenprognose im Film-Assistenten fehlgeschlagen: ${msg}`); } catch (_) {}
            }
            return null;
        }
    }

    // Short, always visible summary of the processing options in the group header,
    // so the important choices (H.265, delete original, targets) are not hidden.
    function buildOptionsSummaryText() {
        const parts = [];
        if (optConvert) {
            const qualityText = optQualitySlider ? ` (${optQualitySlider.value || "60"})` : "";
            parts.push(optConvert.checked ? `H.265 an${qualityText}` : "H.265 aus");
        }
        if (optConvert && optConvert.checked && lastSizeEstimateText) parts.push(lastSizeEstimateText);
        if (optDelete) parts.push(optDelete.checked ? "Original löschen" : "Original behalten");
        return parts.join(" · ");
    }

    function updateOptionsSummary() {
        const summaryEl = getEl("mw-wizard-options-summary");
        if (summaryEl) summaryEl.textContent = buildOptionsSummaryText();
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

    // dispatchChange=false: only mirror the value. Used for H.265 and quality, whose legacy change
    // listeners start an ffmpeg size estimate for the (hidden) legacy panel on every event.
    function syncOptionBackToContext(wizardEl, contextId, prop = "checked", { dispatchChange = true, dispatchInput = false } = {}) {
        const ctxEl = getEl(contextId);
        if (!wizardEl || !ctxEl || (ctxEl.tagName !== "INPUT" && ctxEl.tagName !== "SELECT")) return;
        ctxEl[prop] = wizardEl[prop];
        if (!dispatchChange) {
            // Legacy "input" listeners only refresh the value label and quality hints (no estimate),
            // so the legacy panel stays in sync without starting an ffmpeg test run.
            if (dispatchInput && typeof ctxEl.dispatchEvent === "function" && typeof Event === "function") {
                try {
                    ctxEl.dispatchEvent(new Event("input"));
                } catch (_) {}
            }
            return;
        }
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

        let resolvedProvider = String(baseMovie.provider || "manual");
        let resolvedMovieId = String(baseMovie.id || "manual");
        if (resolvedProvider !== "manual") {
            if (successfulProviders.has("tmdb") && successfulProviders.get("tmdb")) {
                resolvedProvider = "tmdb";
                resolvedMovieId = String(successfulProviders.get("tmdb"));
            } else if (successfulProviders.size > 0 && !successfulProviders.has(resolvedProvider.toLowerCase())) {
                const [firstOkProv, firstOkId] = successfulProviders.entries().next().value;
                resolvedProvider = String(firstOkProv);
                resolvedMovieId = String(firstOkId);
            }
        }

        return {
            media_type: "movie",
            project_name: currentProjectName,
            movie_name: finalMovieName,
            movie_id: resolvedMovieId,
            provider: resolvedProvider,
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
        ];
        for (const text of lines) {
            summaryBox.appendChild(mkEl(doc, "div", { cls: "mw-wizard-summary-row", text }));
        }

        // Long plots are clamped to three lines (CSS) so the result groups stay in view.
        const plotText = `Plot: ${vals.plot || "—"}`;
        const plotEl = mkEl(doc, "div", {
            id: "mw-wizard-summary-plot",
            cls: "mw-wizard-summary-row mw-wizard-summary-plot clamped",
            text: plotText,
        });
        summaryBox.appendChild(plotEl);
        if (String(vals.plot || "").trim()) {
            const toggleBtn = mkEl(doc, "button", {
                id: "mw-wizard-summary-plot-toggle",
                cls: "mw-wizard-summary-plot-toggle",
                type: "button",
                text: "mehr",
            });
            toggleBtn.addEventListener("click", () => {
                const isClamped = plotEl.classList.contains("clamped");
                plotEl.classList.toggle("clamped", !isClamped);
                toggleBtn.textContent = isClamped ? "weniger" : "mehr";
            });
            summaryBox.appendChild(toggleBtn);
            // Hide the toggle once layout shows the plot fits into three lines (depends on width).
            const hideToggleIfNotClipped = () => {
                const clientHeight = Number(plotEl.clientHeight) || 0;
                const scrollHeight = Number(plotEl.scrollHeight) || 0;
                if (clientHeight > 0 && scrollHeight <= clientHeight + 1 && plotEl.classList.contains("clamped")) {
                    toggleBtn.classList.add("hidden");
                }
            };
            if (typeof globalThis.requestAnimationFrame === "function") {
                globalThis.requestAnimationFrame(hideToggleIfNotClipped);
            }
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
        resetSizeEstimate();

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

            const displayData = moveExistingNfoToJunk(data || {});
            applyResultGroupState("renames", "Umbenennungen", displayData.renames);
            applyResultGroupState("subs", "Untertitel & Extras", displayData.subs);
            applyResultGroupState("junk", "Junk-Dateien", displayData.junk);

            renderPreviewData(
                {
                    similarBox: similarExistingBox,
                    similarText: similarExistingText,
                    dest: destEl,
                    listRenames,
                    listSubs,
                    listJunk,
                },
                displayData,
                {
                    idPrefix: "mw-wizard-similar",
                    onLog: logFn,
                    isItemChecked: isPreviewItemChecked,
                }
            );
            renderExistingNfoNote(displayData.movedNfoCount);

            snapshotPreviewCheckboxState();
            currentPreviewPayload = basePayload;
            hasValidPreview = true;
            updateExecuteButtonState();
            lastPreviewVideoFiles = extractVideoFiles(displayData.renames);
            refreshSizeEstimate();

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
                // Completed steps show a check mark instead of their number (theme accent colour, see CSS).
                dot.textContent = stepIdx < currentStep ? "✓" : String(stepIdx);
            }
        });

        if (backBtn) backBtn.classList.toggle("hidden", currentStep === 1);
        if (skipBtn) skipBtn.classList.toggle("hidden", currentStep !== 2 && currentStep !== 3);
        if (nextBtn) nextBtn.classList.toggle("hidden", currentStep === 4);
        if (executeBtn) executeBtn.classList.toggle("hidden", currentStep !== 4);
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

    function collectCheckedSearchItems() {
        if (!searchResults || typeof searchResults.querySelectorAll !== "function") return [];
        const cbs = searchResults.querySelectorAll(".mw-wizard-compare-cb");
        const checked = [];
        for (const cb of cbs) {
            if (cb && cb.checked) {
                const id = (cb.dataset && cb.dataset.id !== undefined ? cb.dataset.id : cb.getAttribute("data-id")) || "";
                const prov = (cb.dataset && cb.dataset.provider !== undefined ? cb.dataset.provider : cb.getAttribute("data-provider")) || "tmdb";
                const name = (cb.dataset && cb.dataset.name !== undefined ? cb.dataset.name : cb.getAttribute("data-name")) || "";
                checked.push({ id: String(id), name: String(name), provider: String(prov) });
            }
        }
        return checked;
    }

    async function loadMovieMetadata(movie, reqSeq = ++metadataRequestSeq) {
        if (!movie || !fetchFn || movie.provider === "manual") return;
        const expectedMovie = selectedMovie;
        const providersToFetch = selectedProviders.length > 0
            ? selectedProviders.slice()
            : [{ id: String(movie.id || ""), name: movie.name || "", provider: movie.provider || "tmdb" }];
        hideError();
        const headerBadgeText = providersToFetch.length > 1
            ? providersToFetch.map((p) => formatProviderLabel(p.provider)).join(" + ")
            : String(movie.provider || "").toUpperCase();
        if (providerBadge) {
            providerBadge.textContent = `${headerBadgeText} · Lade Metadaten...`;
            providerBadge.classList.remove("mw-wizard-badge-error");
            providerBadge.classList.add("mw-wizard-badge-loading");
        }
        try {
            const url = `/api/metadata/fetch?media_type=movie&provider=${encodeURIComponent(movie.provider)}&movie_id=${encodeURIComponent(movie.id)}`;
            const fetchOptions = {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    media_type: "movie",
                    providers: providersToFetch.map((p) => ({
                        provider: String(p.provider || "tmdb"),
                        movie_id: String(p.id || ""),
                    })),
                }),
            };
            const res = await fetchFn(url, fetchOptions);
            if (reqSeq !== metadataRequestSeq || selectedMovie !== expectedMovie) return;
            if (!res || !res.ok) throw new Error(`HTTP ${res ? res.status : "Fehler"}`);
            const data = await res.json();
            if (reqSeq !== metadataRequestSeq || selectedMovie !== expectedMovie) return;

            if (data && data.providers && typeof data.providers === "object") {
                const order = Array.isArray(data.provider_order) && data.provider_order.length > 0
                    ? data.provider_order
                    : Object.keys(data.providers);
                const okProviders = [];
                const errProviders = [];
                successfulProviders.clear();

                for (const prov of order) {
                    const entry = data.providers[prov];
                    if (!entry || entry.status === "error" || entry.error) {
                        errProviders.push(prov);
                    } else {
                        okProviders.push(prov);
                        successfulProviders.set(prov, String(entry.movie_id || ""));
                        if (entry.fields && !entry.fields.title && (prov === String(movie.provider || "").toLowerCase() || order.length === 1)) {
                            entry.fields.title = movie.name || "";
                        }
                    }
                }

                nfoEditor.setProviderComparison(data);

                if (okProviders.length === 0) {
                    const firstErrProv = errProviders[0];
                    const errMsg = (firstErrProv && data.providers[firstErrProv]?.error) || "Provider nicht erreichbar";
                    showError(`Metadaten-Abruf fehlgeschlagen (${errMsg})`, () => loadMovieMetadata(movie));
                    return;
                }

                if (errProviders.length > 0) {
                    showError(
                        "Einige Provider sind nicht erreichbar. Du kannst mit den geladenen Daten fortfahren.",
                        () => loadMovieMetadata(movie)
                    );
                    if (providerBadge) {
                        providerBadge.textContent = `${order.map(formatProviderLabel).join(" + ")} (Teil-Erfolg)`;
                        providerBadge.classList.remove("mw-wizard-badge-loading", "mw-wizard-badge-error");
                    }
                    return;
                }

                if (providerBadge) {
                    providerBadge.textContent = order.length > 1
                        ? order.map(formatProviderLabel).join(" + ")
                        : String(order[0] || movie.provider || "").toUpperCase();
                    providerBadge.classList.remove("mw-wizard-badge-loading", "mw-wizard-badge-error");
                }
                return;
            }

            if (data && data.error) throw new Error(data.error);
            const normProv = String(movie.provider || "tmdb").toLowerCase() === "tmdb_movie"
                ? "tmdb"
                : String(movie.provider || "tmdb").toLowerCase();
            successfulProviders.clear();
            successfulProviders.set(normProv, String(movie.id || ""));
            if (providerBadge) {
                providerBadge.textContent = String(movie.provider || "").toUpperCase();
                providerBadge.classList.remove("mw-wizard-badge-loading", "mw-wizard-badge-error");
            }
            const resolvedFields = {
                title: (data.title !== undefined && data.title !== "") ? data.title : (data.name || movie.name || ""),
                year: data.year ?? "",
                plot: data.plot ?? "",
                fsk: data.fsk ?? "",
                genres: Array.isArray(data.genres) ? data.genres : (data.genres ?? []),
            };
            nfoEditor.setProviderComparison({
                providers: {
                    [normProv]: {
                        provider: normProv,
                        movie_id: String(movie.id || ""),
                        status: "ok",
                        error: null,
                        fields: resolvedFields,
                    },
                },
                provider_order: [normProv],
            });
        } catch (err) {
            if (reqSeq !== metadataRequestSeq || selectedMovie !== expectedMovie) return;
            showError(`Metadaten-Abruf fehlgeschlagen (${err.message || err})`, () => loadMovieMetadata(movie));
        }
    }

    async function selectMovieInWizard(movie, fetchMeta = true, comparisonMovies = null) {
        const reqSeq = ++metadataRequestSeq;
        selectedMovie = {
            id: String(movie.id || "manual"),
            name: movie.name || movie.title || "",
            provider: movie.provider || "manual",
        };
        successfulProviders.clear();
        nfoEditor.clearProviderComparison();

        const isManual = selectedMovie.provider === "manual";
        if (isManual) {
            selectedProviders = [];
        } else if (Array.isArray(comparisonMovies) && comparisonMovies.length > 0) {
            const seenProvs = new Set();
            const list = [];
            for (const item of [selectedMovie, ...comparisonMovies]) {
                if (!item || !item.provider || item.provider === "manual") continue;
                const normProv = String(item.provider).toLowerCase() === "tmdb_movie"
                    ? "tmdb"
                    : String(item.provider).toLowerCase();
                if (seenProvs.has(normProv)) continue;
                seenProvs.add(normProv);
                list.push({
                    id: String(item.id || ""),
                    name: String(item.name || item.title || ""),
                    provider: normProv,
                });
            }
            selectedProviders = list;
        } else {
            const normProv = String(selectedMovie.provider).toLowerCase() === "tmdb_movie"
                ? "tmdb"
                : String(selectedMovie.provider).toLowerCase();
            selectedProviders = [{
                id: selectedMovie.id,
                name: selectedMovie.name,
                provider: normProv,
            }];
        }

        if (selectedInfo) selectedInfo.textContent = selectedMovie.name || (isManual ? "Metadaten manuell eintragen" : "");
        if (providerBadge) {
            providerBadge.textContent = isManual
                ? "Metadaten manuell eintragen"
                : (selectedProviders.length > 1
                    ? selectedProviders.map((p) => formatProviderLabel(p.provider)).join(" + ")
                    : String(selectedMovie.provider).toUpperCase());
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
            lastSearchResults = items.map((item) => ({
                id: String(item.id ?? ""),
                name: String(item.name || item.title || ""),
                provider: String(item.provider || "tmdb"),
            }));
            if (searchResults) {
                searchResults.innerHTML = "";
                for (const item of items) {
                    const prov = String(item.provider || "tmdb");
                    const compareCb = mkEl(doc, "input", {
                        cls: "mw-wizard-compare-cb",
                        type: "checkbox",
                        attrs: {
                            "data-provider": prov,
                            "data-id": item.id ?? "",
                            "data-name": item.name || "",
                            title: "Zum Provider-Vergleich auswählen",
                        },
                    });
                    compareCb.addEventListener("click", (e) => {
                        if (e && typeof e.stopPropagation === "function") e.stopPropagation();
                        if (compareCb.checked && searchResults && typeof searchResults.querySelectorAll === "function") {
                            const allCbs = searchResults.querySelectorAll(".mw-wizard-compare-cb");
                            for (const otherCb of allCbs) {
                                if (otherCb !== compareCb) {
                                    const otherProv = (otherCb.dataset && otherCb.dataset.provider) || otherCb.getAttribute("data-provider");
                                    if (otherProv === prov) {
                                        otherCb.checked = false;
                                    }
                                }
                            }
                        }
                    });

                    const row = mkEl(
                        doc,
                        "div",
                        {
                            cls: "search-item mw-wizard-search-item",
                            attrs: { "data-id": item.id ?? "", "data-name": item.name ?? "", "data-provider": prov },
                        },
                        [
                            mkEl(doc, "div", { cls: "mw-wizard-search-item-main" }, [
                                compareCb,
                                mkEl(doc, "div", { cls: "search-item-name", text: item.name || "" }),
                            ]),
                            mkEl(doc, "div", { cls: "search-item-provider", text: `Metadatendienst: ${prov}` }),
                        ]
                    );
                    row.addEventListener("click", (e) => {
                        if (e && e.target === compareCb) return;
                        const clickedMovie = { id: item.id, name: item.name, provider: prov };
                        const checkedList = collectCheckedSearchItems();
                        if (checkedList.length > 0) {
                            selectMovieInWizard(clickedMovie, true, [clickedMovie, ...checkedList]);
                            return;
                        }
                        const counterpart = findCounterpartInSearchResults(clickedMovie, lastSearchResults);
                        const comparisonList = counterpart ? [clickedMovie, counterpart] : [clickedMovie];
                        selectMovieInWizard(clickedMovie, true, comparisonList);
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
        resetSizeEstimate();
        metadataRequestSeq += 1;
        previewRequestSeq += 1;
        hasValidPreview = false;
        currentPreviewPayload = null;
        clearPreviewCheckboxState();
        hideError();
        artworkSkipped = false;
        switchArtworkTab("poster");
        if (openOptions.projectName !== undefined) currentProjectName = String(openOptions.projectName || "");
        if (openOptions.onProcessSuccess) onProcessSuccessCallback = openOptions.onProcessSuccess;
        if (openOptions.onClosed) onClosedCallback = openOptions.onClosed;
        if (openOptions.onPersistOptions) persistOptionsCallback = openOptions.onPersistOptions;
        if (openOptions.onLog) logFn = openOptions.onLog;
        syncWizardOptionsFromContext(openOptions);

        const initialQuery = String(openOptions.query ?? "").trim();
        if (searchInput) searchInput.value = initialQuery;
        if (searchResults) searchResults.innerHTML = "";
        selectedMovie = null;
        selectedProviders = [];
        successfulProviders.clear();
        lastSearchResults = [];
        nfoEditor.clearProviderComparison();
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
        resetSizeEstimate();
        metadataRequestSeq += 1;
        previewRequestSeq += 1;
        hasValidPreview = false;
        currentPreviewPayload = null;
        updateExecuteButtonState();
        modalOverlay.classList.add("hidden");
        modalOverlay.classList.remove("active");
        if (typeof onClosedCallback === "function") {
            try {
                onClosedCallback();
            } catch (err) {
                if (logFn) {
                    try { logFn(`[System]: Rücksprung nach dem Film-Assistenten fehlgeschlagen: ${err && err.message ? err.message : err}`); } catch (_) {}
                }
            }
        }
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
            const checkedItems = collectCheckedSearchItems();
            if (checkedItems.length > 0) {
                const primaryItem = checkedItems.find((it) => String(it.provider).toLowerCase() === "tmdb") || checkedItems[0];
                selectMovieInWizard(primaryItem, true, checkedItems);
                return currentStep;
            }
            if (!selectedMovie) {
                metadataRequestSeq += 1;
                const manualTitle = searchInput ? String(searchInput.value || "").trim() : "";
                selectedMovie = { id: "manual", name: manualTitle || "Unbekannter Film", provider: "manual" };
                selectedProviders = [];
                successfulProviders.clear();
                nfoEditor.clearProviderComparison();
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

    const bindClick = (el, fn) => el && typeof el.addEventListener === "function" && el.addEventListener("click", fn);
    bindClick(closeBtn, () => close({ force: false }));
    bindClick(backBtn, () => prevStep());
    bindClick(skipBtn, () => skipCurrentStep());
    bindClick(nextBtn, () => nextStep());
    bindClick(executeBtn, () => executeStep4Process());
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
            syncOptionBackToContext(optConvert, "movie-option-convert", "checked", { dispatchChange: false });
            persistOptions();
            if (currentStep === 4 && hasValidPreview) refreshSizeEstimate();
        });
    }
    if (optDelete && typeof optDelete.addEventListener === "function") {
        optDelete.addEventListener("change", () => {
            updateOptionsSummary();
            syncOptionBackToContext(optDelete, "movie-option-delete", "checked");
        });
    }
    if (optQualitySlider && typeof optQualitySlider.addEventListener === "function") {
        // While dragging only the label updates; mirroring, saving and the forecast follow on release.
        optQualitySlider.addEventListener("input", () => updateOptionSubcontainers());
        optQualitySlider.addEventListener("change", () => {
            updateOptionSubcontainers();
            syncOptionBackToContext(optQualitySlider, "movie-quality-slider", "value", { dispatchChange: false, dispatchInput: true });
            persistOptions();
            if (currentStep === 4 && hasValidPreview) refreshSizeEstimate();
        });
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
            updateOptionsSummary();
            syncOptionBackToContext(optNasDest, "movie-nas-destination", "value");
            if (currentStep === 4) loadStep4Preview();
        });
    }
    if (optPcloudDest && typeof optPcloudDest.addEventListener === "function") {
        optPcloudDest.addEventListener("change", () => {
            updateOptionsSummary();
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
