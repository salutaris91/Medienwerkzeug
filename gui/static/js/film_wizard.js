import { renderNfoEditor, buildMovieNfoOverrides, formatProviderLabel } from './nfo_editor.js?v=123';
import { formatBytes } from './format.js?v=123';
import {
    renderPreviewData,
    collectPreviewSelection,
} from './preview_render.js?v=123';

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
        if (k === "src") el.src = String(v);
        if (k === "alt") el.alt = String(v);
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

    const artworkSearchInput = mkEl(doc, "input", {
        id: "mw-wizard-artwork-search-input",
        cls: "mw-wizard-input mw-wizard-artwork-search-input",
        type: "text",
        attrs: { "aria-label": "Filmtitel für TMDb-Bilder suchen" },
    });
    artworkSearchInput.placeholder = "Anderen Filmtitel für TMDb-Bilder suchen...";

    const artworkUploadInput = mkEl(doc, "input", {
        id: "mw-wizard-artwork-upload-input",
        cls: "hidden",
        type: "file",
        attrs: {
            accept: ".jpg,.jpeg,.png,.webp",
            "aria-label": "Eigenes Bild hochladen",
        },
    });

    const tmdbLogoWrap = mkEl(doc, "span", { cls: "mw-wizard-tmdb-logo-wrap" });
    tmdbLogoWrap.innerHTML = '<svg id="mw-wizard-tmdb-logo" class="mw-wizard-tmdb-logo" role="img" aria-label="TMDB" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 24" width="60" height="12"><rect width="120" height="24" rx="4" fill="#0d253f"></rect><rect x="78" y="6" width="34" height="12" rx="6" fill="#01b4e4"></rect><circle cx="84" cy="12" r="4" fill="#90cea1"></circle><path d="M10 7h12v3h-4.5v7h-3v-7H10V7zm15 0h3.2l2.8 5.2L33.8 7H37v10h-2.8v-5.5l-2.5 4.5h-1.4l-2.5-4.5V17H25V7zm16 0h4.8c3 0 5 2 5 5s-2 5-5 5H41V7zm2.8 2.5v5h1.9c1.4 0 2.3-.9 2.3-2.5s-.9-2.5-2.3-2.5h-1.9zM54 7h5.2c2.1 0 3.5 1 3.5 2.5 0 1-.6 1.8-1.5 2.1 1.1.3 1.8 1.1 1.8 2.3 0 1.8-1.5 3.1-3.8 3.1H54V7zm2.8 2.2v1.8h2c.7 0 1.1-.4 1.1-.9s-.4-.9-1.1-.9h-2zm0 3.8v2h2.2c.8 0 1.3-.4 1.3-1s-.5-1-1.3-1h-2.2z" fill="#90cea1"></path></svg>';
    const parsedSvg = tmdbLogoWrap.children && tmdbLogoWrap.children[0];
    if (parsedSvg && typeof parsedSvg.setAttribute === "function") {
        parsedSvg.setAttribute("role", "img");
        parsedSvg.setAttribute("aria-label", "TMDB");
    }

    const step3 = mkEl(
        doc,
        "section",
        { id: "mw-wizard-step-3", cls: "mw-wizard-panel hidden", attrs: { "data-step-panel": "3" } },
        [
            mkEl(doc, "div", { id: "mw-wizard-artwork-source-bar", cls: "mw-wizard-artwork-source-bar" }, [
                mkEl(doc, "span", { id: "mw-wizard-artwork-source-info", cls: "mw-wizard-artwork-source-info", text: "Bildquelle: TMDb" }),
                mkEl(doc, "select", { id: "mw-wizard-artwork-match-select", cls: "mw-wizard-select mw-wizard-artwork-match-select hidden", attrs: { "aria-label": "TMDb-Film für Artwork wählen" } }),
                artworkSearchInput,
                mkEl(doc, "button", { id: "mw-wizard-artwork-search-btn", cls: "btn btn-secondary btn-sm", type: "button", text: "Bilder suchen" }),
            ]),
            mkEl(doc, "div", { cls: "mw-wizard-tabs", attrs: { role: "tablist", "aria-label": "Artwork-Rollen" } }, [
                mkEl(doc, "button", { id: "mw-wizard-tab-poster", cls: "mw-wizard-tab active", type: "button", text: "Poster (2:3)", attrs: { "data-artwork-tab": "poster", role: "tab", "aria-selected": "true", "aria-controls": "mw-wizard-artwork-poster" } }),
                mkEl(doc, "button", { id: "mw-wizard-tab-fanart", cls: "mw-wizard-tab", type: "button", text: "Hintergrundbild (16:9)", attrs: { "data-artwork-tab": "fanart", role: "tab", "aria-selected": "false", "aria-controls": "mw-wizard-artwork-fanart" } }),
                mkEl(doc, "button", { id: "mw-wizard-tab-logo", cls: "mw-wizard-tab", type: "button", text: "Logo", attrs: { "data-artwork-tab": "logo", role: "tab", "aria-selected": "false", "aria-controls": "mw-wizard-artwork-logo" } }),
            ]),
            mkEl(doc, "div", { id: "mw-wizard-artwork-toolbar", cls: "mw-wizard-artwork-toolbar" }, [
                mkEl(doc, "button", { id: "mw-wizard-artwork-deselect-btn", cls: "btn btn-secondary btn-sm", type: "button", text: "Kein Bild für diese Rolle", attrs: { "aria-pressed": "false" } }),
                artworkUploadInput,
                mkEl(doc, "button", { id: "mw-wizard-artwork-upload-btn", cls: "btn btn-secondary btn-sm", type: "button", text: "Eigenes Bild wählen…" }),
            ]),
            mkEl(doc, "div", { id: "mw-wizard-artwork-poster", cls: "mw-wizard-artwork-panel mw-wizard-artwork-placeholder active", attrs: { role: "tabpanel", "aria-labelledby": "mw-wizard-tab-poster" }, text: "Automatischer Poster-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden." }),
            mkEl(doc, "div", { id: "mw-wizard-artwork-fanart", cls: "mw-wizard-artwork-panel mw-wizard-artwork-placeholder hidden", attrs: { role: "tabpanel", "aria-labelledby": "mw-wizard-tab-fanart", hidden: "" }, text: "Automatischer Hintergrundbild-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden." }),
            mkEl(doc, "div", { id: "mw-wizard-artwork-logo", cls: "mw-wizard-artwork-panel mw-wizard-artwork-placeholder hidden", attrs: { role: "tabpanel", "aria-labelledby": "mw-wizard-tab-logo", hidden: "" }, text: "Automatischer Logo-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden." }),
            mkEl(doc, "div", { id: "mw-wizard-tmdb-attribution", cls: "mw-wizard-tmdb-attribution" }, [
                tmdbLogoWrap,
                mkEl(doc, "span", { id: "mw-wizard-tmdb-attribution-text", cls: "mw-wizard-tmdb-attribution-text", text: "This product uses the TMDB API but is not endorsed or certified by TMDB." }),
            ]),
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

    const seriesContext = mkEl(
        doc,
        "div",
        {
            id: "mw-wizard-series-context",
            cls: "mw-wizard-series-context hidden",
            attrs: { role: "region", "aria-label": "Filmreihen-Fortschritt" },
        },
        [
            mkEl(doc, "div", { cls: "mw-wizard-queue-main" }, [
                mkEl(doc, "span", { cls: "mw-wizard-queue-icon", text: "🎬", attrs: { "aria-hidden": "true" } }),
                mkEl(doc, "span", { id: "mw-wizard-queue-label", cls: "mw-wizard-queue-label" }),
            ]),
            mkEl(doc, "div", { cls: "mw-wizard-queue-actions" }, [
                mkEl(doc, "div", { id: "mw-wizard-queue-status", cls: "mw-wizard-queue-status", attrs: { "aria-live": "polite" } }),
                mkEl(doc, "button", {
                    id: "mw-wizard-queue-skip-btn",
                    cls: "btn btn-secondary btn-sm mw-wizard-queue-skip-btn",
                    type: "button",
                    text: "Film überspringen →",
                }),
            ]),
        ]
    );

    const modal = mkEl(doc, "div", { cls: "mw-modal mw-wizard-modal" }, [
        mkEl(doc, "div", { cls: "mw-wizard-header" }, [
            mkEl(doc, "h3", { id: "mw-wizard-title", cls: "mw-wizard-title", text: "Film-Assistent" }),
            mkEl(doc, "button", { id: "mw-wizard-close", cls: "close-modal mw-wizard-close-btn", type: "button", text: "×", attrs: { "aria-label": "Schließen" } }),
        ]),
        seriesContext,
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
    const seriesContextEl = getEl("mw-wizard-series-context");
    const queueLabelEl = getEl("mw-wizard-queue-label");
    const queueStatusEl = getEl("mw-wizard-queue-status");
    const queueSkipBtn = getEl("mw-wizard-queue-skip-btn");
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
    const tabLogo = getEl("mw-wizard-tab-logo");
    const posterPanel = getEl("mw-wizard-artwork-poster");
    const fanartPanel = getEl("mw-wizard-artwork-fanart");
    const logoPanel = getEl("mw-wizard-artwork-logo");
    const artworkSourceInfo = getEl("mw-wizard-artwork-source-info");
    const artworkMatchSelect = getEl("mw-wizard-artwork-match-select");
    const artworkSearchInputEl = getEl("mw-wizard-artwork-search-input");
    const artworkSearchBtn = getEl("mw-wizard-artwork-search-btn");
    const artworkDeselectBtn = getEl("mw-wizard-artwork-deselect-btn");
    const artworkUploadInputEl = getEl("mw-wizard-artwork-upload-input");
    const artworkUploadBtn = getEl("mw-wizard-artwork-upload-btn");
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
    let queueActive = false;
    let queueItems = [];
    let queueIndex = 0;
    let queueCurrentError = "";
    let selectedMovie = null;
    let selectedProviders = [];
    const successfulProviders = new Map();
    let lastSearchResults = [];
    let currentProjectName = options.projectName || "";
    let artworkSkipped = false;
    let activeArtworkTab = "poster";
    const MAX_ARTWORK_UPLOAD_BYTES = 15 * 1024 * 1024;
    const MAX_BACKDROP_SELECTION = 10;
    const ARTWORK_ROLES = ["poster", "backdrop", "logo"];
    let artworkRequestSeq = 0;
    let artworkSessionSeq = 0;
    const uploadSeqByRole = { poster: 0, backdrop: 0, logo: 0 };
    let artworkCandidatesLoadedKey = "";
    let artworkResolvedTmdbId = "";
    let artworkResolvedTitle = "";
    let artworkMatches = [];
    let artworkOverrideTmdbId = "";
    let artworkOverrideQuery = "";
    let artworkLoading = false;
    let artworkLoadError = "";

    function createInitialArtworkRoleState() {
        return {
            candidates: [],
            customUpload: null,
            selectedItems: [],
            mode: "auto",
            selectedUrl: "",
            selectedThumbUrl: "",
            selectedDataUrl: "",
            explicit: false,
            uploadError: "",
        };
    }

    function syncBackdropStateFromItems(st) {
        if (!st) return;
        const items = Array.isArray(st.selectedItems) ? st.selectedItems : [];
        st.selectedItems = items;
        if (items.length === 0) {
            st.mode = st.explicit ? "none" : "auto";
            st.selectedUrl = "";
            st.selectedThumbUrl = "";
            st.selectedDataUrl = "";
            return;
        }
        const first = items[0];
        if (items.length === 1) {
            if (first.mode === "upload") {
                st.mode = "upload";
                st.selectedDataUrl = String(first.dataUrl || "");
                st.selectedUrl = "";
                st.selectedThumbUrl = "";
            } else {
                st.mode = "url";
                st.selectedUrl = String(first.url || "");
                st.selectedThumbUrl = String(first.thumbUrl || first.url || "");
                st.selectedDataUrl = "";
            }
            return;
        }
        st.mode = "multi";
        st.selectedUrl = first.mode === "url" ? String(first.url || "") : "";
        st.selectedThumbUrl = first.mode === "url" ? String(first.thumbUrl || first.url || "") : "";
        st.selectedDataUrl = first.mode === "upload" ? String(first.dataUrl || "") : "";
    }

    let artworkState = {
        poster: createInitialArtworkRoleState(),
        backdrop: createInitialArtworkRoleState(),
        logo: createInitialArtworkRoleState(),
    };
    let onProcessSuccessCallback = options.onProcessSuccess || null;
    // Called after every successful close (×, ESC, after starting the process) so the app can leave
    // the project view instead of falling back to the legacy movie panel.
    let onClosedCallback = options.onClosed || null;
    let lastRetryAction = null;
    let sessionSeq = 0;
    let searchRequestSeq = 0;
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

    function normalizeQueueInput(rawQueue) {
        if (!Array.isArray(rawQueue)) return [];
        const out = [];
        for (const entry of rawQueue) {
            if (!entry) continue;
            const projectName = typeof entry === "string"
                ? entry.trim()
                : String(entry.projectName || entry.project || "").trim();
            if (!projectName) continue;
            let query = typeof entry === "object" && entry.query !== undefined
                ? String(entry.query || "").trim()
                : "";
            if (!query) {
                query = projectName
                    .replace(/\.[a-z0-9]{2,4}$/i, "")
                    .replace(/[._\-]/g, " ")
                    .trim()
                    .replace(/\([0-9]{4}\)/g, "")
                    .trim() || projectName;
            }
            out.push({
                projectName,
                query,
                status: "pending",
                hadError: false,
            });
        }
        return out;
    }

    function renderQueueHeader() {
        if (!queueActive || queueItems.length === 0) {
            if (seriesContextEl && seriesContextEl.classList) {
                seriesContextEl.classList.add("hidden");
            }
            if (queueLabelEl) queueLabelEl.textContent = "";
            if (queueStatusEl) queueStatusEl.innerHTML = "";
            return;
        }
        if (seriesContextEl && seriesContextEl.classList) {
            seriesContextEl.classList.remove("hidden");
        }
        const currentItem = queueItems[queueIndex] || queueItems[0];
        if (queueLabelEl) {
            queueLabelEl.textContent = `Film ${queueIndex + 1} von ${queueItems.length} · ${currentItem ? currentItem.projectName : ""}`;
        }
        if (queueStatusEl) {
            queueStatusEl.innerHTML = "";
            const queuedCount = queueItems.filter((it) => it.status === "queued").length;
            const skippedCount = queueItems.filter((it) => it.status === "skipped").length;
            if (queuedCount > 0) {
                queueStatusEl.appendChild(
                    mkEl(doc, "span", { cls: "mw-wizard-queue-chip ok", text: `✓ ${queuedCount} eingereiht` })
                );
            }
            if (skippedCount > 0) {
                queueStatusEl.appendChild(
                    mkEl(doc, "span", { cls: "mw-wizard-queue-chip muted", text: `${skippedCount} übersprungen` })
                );
            }
            if (queueCurrentError !== "") {
                queueStatusEl.appendChild(
                    mkEl(doc, "span", {
                        id: "mw-wizard-queue-error-chip",
                        cls: "mw-wizard-queue-chip error",
                        text: `⚠ ${queueCurrentError}`,
                        attrs: { role: "status" },
                    })
                );
            }
        }
        if (queueSkipBtn) {
            queueSkipBtn.disabled = Boolean(isExecutingProcess);
            queueSkipBtn.textContent = queueIndex < queueItems.length - 1
                ? "Film überspringen →"
                : "Film überspringen & schließen";
        }
    }

    function updateExecuteButtonState() {
        if (!executeBtn) return;
        executeBtn.disabled = Boolean(isExecutingProcess || currentStep !== 4 || !hasValidPreview);
        if (!isExecutingProcess) {
            if (queueActive && queueIndex < queueItems.length - 1) {
                executeBtn.textContent = "Einreihen & nächster Film";
            } else {
                executeBtn.textContent = "Jetzt final verarbeiten";
            }
        }
        if (queueSkipBtn) {
            queueSkipBtn.disabled = Boolean(isExecutingProcess);
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

    function buildArtworkOverridesPayload(resolvedProvider = "tmdb") {
        if (artworkSkipped) return undefined;
        const normProv = String(resolvedProvider || "").toLowerCase();
        const isTmdbProvider = normProv === "tmdb" || normProv === "tmdb_movie";
        const hasExplicitSelection = ARTWORK_ROLES.some((role) => {
            const st = artworkState[role];
            return Boolean(st && st.explicit);
        });
        const hasAnySelection = ARTWORK_ROLES.some((role) => {
            const st = artworkState[role];
            if (!st) return false;
            return Boolean(
                st.explicit ||
                (st.mode === "multi" && Array.isArray(st.selectedItems) && st.selectedItems.length > 0) ||
                (st.mode === "url" && st.selectedUrl) ||
                (st.mode === "upload" && st.selectedDataUrl) ||
                st.mode === "none"
            );
        });
        if (isTmdbProvider) {
            if (!hasExplicitSelection) return undefined;
        } else if (!hasAnySelection) {
            return undefined;
        }

        const out = {};
        for (const role of ARTWORK_ROLES) {
            const st = artworkState[role];
            if (!st) {
                out[role] = { mode: "auto" };
            } else if (isTmdbProvider && !st.explicit) {
                out[role] = { mode: "auto" };
            } else if (st.mode === "none") {
                out[role] = { mode: "none" };
            } else if (role === "backdrop" && Array.isArray(st.selectedItems) && st.selectedItems.length >= 2) {
                out[role] = {
                    mode: "multi",
                    items: st.selectedItems.map((it) =>
                        it.mode === "upload"
                            ? { mode: "upload", data_url: it.dataUrl }
                            : { mode: "url", url: it.url }
                    ),
                };
            } else if (st.mode === "upload" && st.selectedDataUrl) {
                out[role] = { mode: "upload", data_url: st.selectedDataUrl };
            } else if (st.mode === "url" && st.selectedUrl) {
                out[role] = { mode: "url", url: st.selectedUrl };
            } else {
                out[role] = { mode: "auto" };
            }
        }
        return out;
    }

    function formatArtworkSummaryLine() {
        if (artworkSkipped) return "Übersprungen (Standard-Artwork)";
        const hasExplicit = ARTWORK_ROLES.some((r) => Boolean(artworkState[r] && artworkState[r].explicit));
        if (!hasExplicit) {
            const baseProv = String((selectedMovie && selectedMovie.provider) || "manual").toLowerCase();
            const isTmdb = baseProv === "tmdb" || baseProv === "tmdb_movie" || successfulProviders.has("tmdb");
            if (isTmdb) return "Standard-Artwork (TMDb)";
            const hasPreselectedUrl = ARTWORK_ROLES.some(
                (r) => Boolean(
                    artworkState[r] &&
                    ((artworkState[r].mode === "url" && artworkState[r].selectedUrl) ||
                        (artworkState[r].mode === "multi" && artworkState[r].selectedItems.length > 0))
                )
            );
            return hasPreselectedUrl ? "TMDb-Vorauswahl" : "Kein Artwork ausgewählt";
        }
        const labels = { poster: "Poster", backdrop: "Hintergrundbild", logo: "Logo" };
        return ARTWORK_ROLES.map((r) => {
            const st = artworkState[r];
            let statusText = "Auto";
            if (r === "backdrop" && Array.isArray(st.selectedItems) && st.selectedItems.length >= 2) {
                statusText = `${st.selectedItems.length} Bilder`;
            } else if (st.mode === "none") {
                statusText = "Kein Bild";
            } else if (st.mode === "upload") {
                statusText = "Eigenes Bild";
            } else if (st.mode === "url") {
                statusText = "TMDb-Auswahl";
            }
            return `${labels[r]}: ${statusText}`;
        }).join(" · ");
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

        const payload = {
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
        const artworkOverrides = buildArtworkOverridesPayload(resolvedProvider);
        if (artworkOverrides !== undefined) {
            payload.artwork_overrides = artworkOverrides;
        }
        return payload;
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
            `Artwork: ${formatArtworkSummaryLine()}`,
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
            if (queueActive && queueCurrentError === "Vorschau fehlgeschlagen") {
                queueCurrentError = "";
                renderQueueHeader();
            }
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
            if (queueActive && !queueCurrentError) {
                queueCurrentError = "Vorschau fehlgeschlagen";
                if (queueItems[queueIndex]) queueItems[queueIndex].hadError = true;
                renderQueueHeader();
            }
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
        if (queueSkipBtn) {
            queueSkipBtn.disabled = true;
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
                if (procSession === sessionSeq) {
                    if (queueActive && queueItems[queueIndex]) {
                        queueItems[queueIndex].status = "queued";
                    }
                    if (queueActive && queueIndex < queueItems.length - 1) {
                        loadQueueItemAt(queueIndex + 1, { autoSearch: true });
                    } else {
                        updateExecuteButtonState();
                        close({ force: true });
                    }
                    if (typeof sessionSuccessCb === "function") {
                        try {
                            sessionSuccessCb(finalPayload);
                        } catch (cbErr) {
                            if (logFn) {
                                try { logFn(`[System]: Nachbereitung nach Prozessstart fehlgeschlagen: ${cbErr && cbErr.message ? cbErr.message : cbErr}`); } catch (_) {}
                            }
                        }
                    }
                } else {
                    updateExecuteButtonState();
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

    function normalizeArtworkRole(roleOrTab) {
        const val = String(roleOrTab || "poster").trim().toLowerCase();
        if (val === "fanart" || val === "backdrop" || val === "backdrops") return "backdrop";
        if (val === "logo" || val === "logos") return "logo";
        return "poster";
    }

    function artworkRoleLabel(role) {
        const norm = normalizeArtworkRole(role);
        if (norm === "backdrop") return "Hintergrundbild";
        if (norm === "logo") return "Logo";
        return "Poster";
    }

    function getArtworkRolePanel(role) {
        const norm = normalizeArtworkRole(role);
        if (norm === "backdrop") return fanartPanel;
        if (norm === "logo") return logoPanel;
        return posterPanel;
    }

    function updateArtworkToolbarState() {
        const activeRole = normalizeArtworkRole(activeArtworkTab);
        const st = artworkState[activeRole];
        const isNone = Boolean(st && st.mode === "none");
        if (artworkDeselectBtn) {
            if (artworkDeselectBtn.classList) artworkDeselectBtn.classList.toggle("active", isNone);
            if (typeof artworkDeselectBtn.setAttribute === "function") {
                artworkDeselectBtn.setAttribute("aria-pressed", isNone ? "true" : "false");
            }
        }
    }

    function updateArtworkSourceBar() {
        const activeRole = normalizeArtworkRole(activeArtworkTab);
        const activeUploadError = artworkState[activeRole] && artworkState[activeRole].uploadError;
        if (artworkSourceInfo) {
            if (artworkLoading) {
                artworkSourceInfo.textContent = "TMDb-Bildkandidaten werden geladen…";
            } else if (activeUploadError) {
                artworkSourceInfo.textContent = activeUploadError;
            } else if (artworkLoadError) {
                artworkSourceInfo.textContent = `TMDb-Bildabruf fehlgeschlagen: ${artworkLoadError}`;
            } else if (artworkResolvedTmdbId) {
                const titleInfo = artworkResolvedTitle ? `${artworkResolvedTitle} · ` : "";
                artworkSourceInfo.textContent = `TMDb-Bildquelle: ${titleInfo}#${artworkResolvedTmdbId}`;
            } else if (artworkCandidatesLoadedKey) {
                artworkSourceInfo.textContent = "Kein passender TMDb-Eintrag für automatische Bildkandidaten gefunden.";
            } else {
                artworkSourceInfo.textContent = "TMDb-Bildquelle (Poster, Hintergrundbild, Logo)";
            }
        }
        if (artworkMatchSelect) {
            artworkMatchSelect.innerHTML = "";
            if (Array.isArray(artworkMatches) && artworkMatches.length > 1) {
                for (const m of artworkMatches) {
                    const mId = String((m && (m.id ?? m.tmdb_id)) || "").trim();
                    if (!mId) continue;
                    const opt = mkEl(doc, "option", {
                        text: String(m.name || m.title || `TMDb #${mId}`),
                        attrs: { value: mId },
                    });
                    opt.value = mId;
                    if (mId === artworkResolvedTmdbId) {
                        opt.selected = true;
                        opt.setAttribute("selected", "selected");
                    }
                    artworkMatchSelect.appendChild(opt);
                }
                if (artworkResolvedTmdbId) artworkMatchSelect.value = artworkResolvedTmdbId;
                artworkMatchSelect.classList.remove("hidden");
            } else {
                artworkMatchSelect.classList.add("hidden");
            }
        }
    }

    function renderArtworkRolePanel(role) {
        const normRole = normalizeArtworkRole(role);
        const panel = getArtworkRolePanel(normRole);
        if (!panel) return;
        const st = artworkState[normRole];
        if (!st) return;

        if (artworkLoading) {
            panel.classList.remove("mw-wizard-artwork-placeholder");
            panel.innerHTML = "";
            const loadingGrid = mkEl(doc, "div", {
                cls: `mw-wizard-artwork-grid mw-wizard-artwork-grid-${normRole}`,
                attrs: { "data-artwork-role": normRole, "aria-busy": "true" },
            });
            for (let i = 0; i < 3; i++) {
                loadingGrid.appendChild(mkEl(doc, "div", {
                    cls: "mw-wizard-artwork-tile loading",
                    attrs: { "data-artwork-role": normRole },
                }, [
                    mkEl(doc, "div", { cls: "mw-wizard-artwork-skeleton" }),
                ]));
            }
            panel.appendChild(loadingGrid);
            return;
        }

        const uploadErrorEl = st.uploadError
            ? mkEl(doc, "div", {
                  cls: "mw-wizard-artwork-tile error mw-wizard-artwork-upload-error",
                  attrs: { "data-artwork-role": normRole, "data-artwork-upload-error": "true" },
                  text: st.uploadError,
              })
            : null;

        if (artworkLoadError && !st.customUpload && (!Array.isArray(st.candidates) || st.candidates.length === 0)) {
            panel.classList.remove("mw-wizard-artwork-placeholder");
            panel.innerHTML = "";
            if (uploadErrorEl) panel.appendChild(uploadErrorEl);
            const retryTileBtn = mkEl(doc, "button", {
                cls: "btn btn-secondary btn-sm mw-wizard-artwork-retry-btn",
                type: "button",
                text: "Erneut versuchen",
                attrs: { "data-artwork-role": normRole },
            });
            retryTileBtn.addEventListener("click", () => {
                loadArtworkCandidates({ force: true });
            });
            const errTile = mkEl(doc, "div", {
                cls: "mw-wizard-artwork-tile error",
                attrs: { "data-artwork-role": normRole, "data-artwork-error": "true" },
            }, [
                mkEl(doc, "div", {
                    cls: "mw-wizard-artwork-error-text",
                    text: `${artworkRoleLabel(normRole)}-Kandidaten konnten nicht geladen werden (${artworkLoadError}).`,
                }),
                retryTileBtn,
            ]);
            panel.appendChild(errTile);
            return;
        }

        const hasCandidates = Array.isArray(st.candidates) && st.candidates.length > 0;
        if (!st.customUpload && !hasCandidates) {
            panel.innerHTML = "";
            if (uploadErrorEl) {
                panel.classList.remove("mw-wizard-artwork-placeholder");
                panel.appendChild(uploadErrorEl);
            }
            if (artworkCandidatesLoadedKey) {
                panel.classList.remove("mw-wizard-artwork-placeholder");
                const emptyGrid = mkEl(doc, "div", {
                    cls: `mw-wizard-artwork-grid mw-wizard-artwork-grid-${normRole}`,
                    attrs: { "data-artwork-role": normRole },
                }, [
                    mkEl(doc, "div", {
                        cls: "mw-wizard-artwork-tile empty",
                        attrs: { "data-artwork-role": normRole },
                        text: `Kein ${artworkRoleLabel(normRole)} bei TMDb verfügbar.`,
                    }),
                ]);
                panel.appendChild(emptyGrid);
            } else if (!uploadErrorEl) {
                panel.classList.add("mw-wizard-artwork-placeholder");
                panel.textContent = `Automatischer ${artworkRoleLabel(normRole)}-Download (TMDb) ist aktiv. Dieser Schritt kann übersprungen werden.`;
            }
            return;
        }

        panel.classList.remove("mw-wizard-artwork-placeholder");
        panel.innerHTML = "";
        if (uploadErrorEl) {
            panel.appendChild(uploadErrorEl);
        }
        const grid = mkEl(doc, "div", {
            cls: `mw-wizard-artwork-grid mw-wizard-artwork-grid-${normRole}`,
            attrs: { "data-artwork-role": normRole },
        });

        if (st.customUpload && st.customUpload.dataUrl) {
            let isUploadSelected = false;
            let uploadCheckText = "✓";
            if (normRole === "backdrop") {
                const uploadIdx = Array.isArray(st.selectedItems)
                    ? st.selectedItems.findIndex((it) => it.mode === "upload" && it.dataUrl === st.customUpload.dataUrl)
                    : -1;
                isUploadSelected = uploadIdx >= 0;
                if (isUploadSelected && st.selectedItems.length >= 2) {
                    uploadCheckText = `✓ ${uploadIdx + 1}`;
                }
            } else {
                isUploadSelected = st.mode === "upload" && st.selectedDataUrl === st.customUpload.dataUrl;
            }
            const uploadImg = mkEl(doc, "img", {
                cls: "mw-wizard-artwork-image",
                attrs: {
                    src: st.customUpload.dataUrl,
                    alt: st.customUpload.fileName || `Eigenes ${artworkRoleLabel(normRole)}`,
                },
            });
            const uploadTile = mkEl(doc, "button", {
                cls: `mw-wizard-artwork-tile mw-wizard-artwork-tile-upload${isUploadSelected ? " selected" : ""}`,
                type: "button",
                attrs: {
                    "aria-pressed": isUploadSelected ? "true" : "false",
                    "data-artwork-role": normRole,
                    "data-artwork-source": "upload",
                },
            }, [
                uploadImg,
                mkEl(doc, "span", { cls: "mw-wizard-artwork-check", text: uploadCheckText, attrs: { "aria-hidden": "true" } }),
                mkEl(doc, "span", {
                    cls: "mw-wizard-artwork-meta",
                    text: st.customUpload.fileName ? `Eigenes Bild · ${st.customUpload.fileName}` : "Eigenes Bild",
                }),
            ]);
            uploadTile.addEventListener("click", () => {
                artworkSkipped = false;
                st.uploadError = "";
                if (normRole === "backdrop") {
                    const existingIdx = Array.isArray(st.selectedItems)
                        ? st.selectedItems.findIndex((it) => it.mode === "upload")
                        : -1;
                    if (existingIdx >= 0) {
                        st.selectedItems.splice(existingIdx, 1);
                    } else {
                        if (st.selectedItems.length >= MAX_BACKDROP_SELECTION) {
                            setArtworkUploadError("backdrop", `Maximal ${MAX_BACKDROP_SELECTION} Hintergrundbilder auswählbar.`);
                            return;
                        }
                        st.selectedItems.push({
                            mode: "upload",
                            dataUrl: st.customUpload.dataUrl,
                            fileName: st.customUpload.fileName,
                        });
                    }
                    st.explicit = true;
                    syncBackdropStateFromItems(st);
                } else {
                    if (st.mode === "upload" && st.selectedDataUrl === st.customUpload.dataUrl) {
                        st.mode = "none";
                        st.selectedDataUrl = "";
                        st.selectedUrl = "";
                        st.selectedThumbUrl = "";
                        st.selectedItems = [];
                    } else {
                        st.mode = "upload";
                        st.selectedDataUrl = st.customUpload.dataUrl;
                        st.selectedUrl = "";
                        st.selectedThumbUrl = "";
                        st.selectedItems = [{
                            mode: "upload",
                            dataUrl: st.customUpload.dataUrl,
                            fileName: st.customUpload.fileName,
                        }];
                    }
                    st.explicit = true;
                }
                renderArtworkRolePanel(normRole);
                updateArtworkToolbarState();
                updateArtworkSourceBar();
            });
            grid.appendChild(uploadTile);
        }

        if (hasCandidates) {
            st.candidates.forEach((cand, idx) => {
                if (!cand || !cand.url) return;
                let isSelected = false;
                let checkText = "✓";
                if (normRole === "backdrop") {
                    const selIdx = Array.isArray(st.selectedItems)
                        ? st.selectedItems.findIndex((it) => it.mode === "url" && it.url === cand.url)
                        : -1;
                    isSelected = selIdx >= 0;
                    if (isSelected && st.selectedItems.length >= 2) {
                        checkText = `✓ ${selIdx + 1}`;
                    }
                } else {
                    isSelected = st.mode === "url" && st.selectedUrl === cand.url;
                }
                const tile = mkEl(doc, "button", {
                    cls: `mw-wizard-artwork-tile${isSelected ? " selected" : ""}`,
                    type: "button",
                    attrs: {
                        "aria-pressed": isSelected ? "true" : "false",
                        "data-artwork-role": normRole,
                        "data-artwork-url": cand.url,
                        "data-artwork-index": String(idx),
                    },
                });
                const imgSrc = String(cand.thumb_url || cand.preview_url || cand.url);
                const img = mkEl(doc, "img", {
                    cls: "mw-wizard-artwork-image",
                    attrs: {
                        src: imgSrc,
                        alt: `${artworkRoleLabel(normRole)} ${idx + 1}`,
                        loading: "lazy",
                    },
                });
                const imgRetryBtn = mkEl(doc, "button", {
                    cls: "btn btn-secondary btn-sm mw-wizard-artwork-img-retry-btn",
                    type: "button",
                    text: "Erneut laden",
                });
                const brokenBox = mkEl(doc, "div", { cls: "mw-wizard-artwork-broken hidden" }, [
                    mkEl(doc, "span", { cls: "mw-wizard-artwork-broken-text", text: "Bild nicht geladen" }),
                    imgRetryBtn,
                ]);
                img.addEventListener("error", () => {
                    tile.classList.add("error");
                    img.classList.add("hidden");
                    brokenBox.classList.remove("hidden");
                });
                imgRetryBtn.addEventListener("click", (e) => {
                    if (e && typeof e.stopPropagation === "function") e.stopPropagation();
                    if (e && typeof e.preventDefault === "function") e.preventDefault();
                    tile.classList.remove("error");
                    brokenBox.classList.add("hidden");
                    img.classList.remove("hidden");
                    const sep = imgSrc.includes("?") ? "&" : "?";
                    const nextSrc = `${imgSrc}${sep}retry=${Date.now()}`;
                    img.setAttribute("src", nextSrc);
                    img.src = nextSrc;
                });

                const rawLang = String(cand.lang ?? cand.iso_639_1 ?? "").trim();
                const langLabel = rawLang ? rawLang.toUpperCase() : "Neutral";
                const dimLabel = cand.width && cand.height ? `${cand.width}×${cand.height}` : "";
                const metaText = [langLabel, dimLabel].filter(Boolean).join(" · ");
                const checkEl = mkEl(doc, "span", { cls: "mw-wizard-artwork-check", text: checkText, attrs: { "aria-hidden": "true" } });
                const metaEl = mkEl(doc, "span", { cls: "mw-wizard-artwork-meta", text: metaText });

                tile.appendChild(img);
                tile.appendChild(checkEl);
                tile.appendChild(brokenBox);
                tile.appendChild(metaEl);

                tile.addEventListener("click", () => {
                    selectArtworkCandidate(normRole, idx);
                });
                grid.appendChild(tile);
            });
        }

        panel.appendChild(grid);
    }

    function renderAllArtworkPanels() {
        updateArtworkSourceBar();
        for (const role of ARTWORK_ROLES) {
            renderArtworkRolePanel(role);
        }
        updateArtworkToolbarState();
    }

    function resetArtworkState() {
        artworkRequestSeq += 1;
        artworkSessionSeq += 1;
        uploadSeqByRole.poster += 1;
        uploadSeqByRole.backdrop += 1;
        uploadSeqByRole.logo += 1;
        artworkCandidatesLoadedKey = "";
        artworkResolvedTmdbId = "";
        artworkResolvedTitle = "";
        artworkMatches = [];
        artworkOverrideTmdbId = "";
        artworkOverrideQuery = "";
        artworkLoading = false;
        artworkLoadError = "";
        artworkState = {
            poster: createInitialArtworkRoleState(),
            backdrop: createInitialArtworkRoleState(),
            logo: createInitialArtworkRoleState(),
        };
        if (artworkSearchInputEl) artworkSearchInputEl.value = "";
        if (artworkUploadInputEl) artworkUploadInputEl.value = "";
        renderAllArtworkPanels();
    }

    function getArtworkState() {
        const snapshot = {};
        for (const role of ARTWORK_ROLES) {
            const st = artworkState[role];
            const itemsCopy = Array.isArray(st.selectedItems)
                ? st.selectedItems.map((it) => ({ ...it }))
                : [];
            snapshot[role] = {
                mode: st.mode,
                selectedUrl: st.selectedUrl,
                selectedThumbUrl: st.selectedThumbUrl,
                selectedDataUrl: st.selectedDataUrl,
                selectedCount: itemsCopy.length,
                selectedItems: itemsCopy,
                explicit: st.explicit,
                uploadError: st.uploadError,
                candidatesCount: Array.isArray(st.candidates) ? st.candidates.length : 0,
                hasCustomUpload: Boolean(st.customUpload && st.customUpload.dataUrl),
            };
        }
        return snapshot;
    }

    function setArtworkUploadError(role, message) {
        const normRole = normalizeArtworkRole(role || activeArtworkTab);
        const st = artworkState[normRole];
        if (!st) return;
        st.uploadError = String(message || "");
        if (logFn && st.uploadError) {
            try { logFn(`[System]: ${st.uploadError}`); } catch (_) {}
        }
        renderArtworkRolePanel(normRole);
        updateArtworkSourceBar();
    }

    function selectArtworkCandidate(role, indexOrUrl) {
        const normRole = normalizeArtworkRole(role || activeArtworkTab);
        const st = artworkState[normRole];
        if (!st || !Array.isArray(st.candidates)) return getArtworkState();

        let cand = null;
        if (typeof indexOrUrl === "number" || /^\d+$/.test(String(indexOrUrl))) {
            const idx = Number(indexOrUrl);
            if (idx >= 0 && idx < st.candidates.length) {
                cand = st.candidates[idx];
            }
        }
        if (!cand && indexOrUrl) {
            const targetUrl = String(indexOrUrl);
            cand = st.candidates.find((c) => c && (c.url === targetUrl || c.thumb_url === targetUrl || c.preview_url === targetUrl)) || null;
        }
        if (!cand || !cand.url) return getArtworkState();

        artworkSkipped = false;
        st.uploadError = "";
        if (normRole === "backdrop") {
            const existingIdx = Array.isArray(st.selectedItems)
                ? st.selectedItems.findIndex((it) => it.mode === "url" && it.url === cand.url)
                : -1;
            if (existingIdx >= 0) {
                st.selectedItems.splice(existingIdx, 1);
            } else {
                if (st.selectedItems.length >= MAX_BACKDROP_SELECTION) {
                    setArtworkUploadError("backdrop", `Maximal ${MAX_BACKDROP_SELECTION} Hintergrundbilder auswählbar.`);
                    return getArtworkState();
                }
                st.selectedItems.push({
                    mode: "url",
                    url: String(cand.url),
                    thumbUrl: String(cand.thumb_url || cand.preview_url || cand.url),
                });
            }
            st.explicit = true;
            syncBackdropStateFromItems(st);
        } else {
            if (st.mode === "url" && st.selectedUrl === cand.url) {
                st.mode = "none";
                st.selectedUrl = "";
                st.selectedThumbUrl = "";
                st.selectedDataUrl = "";
                st.selectedItems = [];
            } else {
                const chosenUrl = String(cand.url);
                const chosenThumb = String(cand.thumb_url || cand.preview_url || cand.url);
                st.mode = "url";
                st.selectedUrl = chosenUrl;
                st.selectedThumbUrl = chosenThumb;
                st.selectedDataUrl = "";
                st.selectedItems = [{ mode: "url", url: chosenUrl, thumbUrl: chosenThumb }];
            }
            st.explicit = true;
        }
        renderArtworkRolePanel(normRole);
        updateArtworkToolbarState();
        updateArtworkSourceBar();
        return getArtworkState();
    }

    function deselectArtworkRole(role) {
        const normRole = normalizeArtworkRole(role || activeArtworkTab);
        const st = artworkState[normRole];
        if (!st) return getArtworkState();
        artworkSkipped = false;
        st.uploadError = "";
        st.selectedItems = [];
        st.mode = "none";
        st.selectedUrl = "";
        st.selectedThumbUrl = "";
        st.selectedDataUrl = "";
        st.explicit = true;
        renderArtworkRolePanel(normRole);
        updateArtworkToolbarState();
        updateArtworkSourceBar();
        return getArtworkState();
    }

    function setCustomArtworkUpload(role, dataUrl, fileName = "upload.png") {
        const normRole = normalizeArtworkRole(role || activeArtworkTab);
        const st = artworkState[normRole];
        if (!st) return false;
        const rawDataUrl = String(dataUrl || "").trim();
        const headerMatch = rawDataUrl.match(/^data:image\/(jpeg|jpg|png|webp);base64,([a-z0-9+/=\s]+)$/i);
        if (!headerMatch) {
            setArtworkUploadError(normRole, "Ungültiges Bildformat für den Artwork-Upload (erlaubt: JPG, PNG, WebP).");
            return false;
        }
        const b64Payload = headerMatch[2].replace(/\s+/g, "");
        const approxBytes = Math.floor((b64Payload.length * 3) / 4);
        if (approxBytes <= 0 || approxBytes > MAX_ARTWORK_UPLOAD_BYTES) {
            setArtworkUploadError(normRole, "Artwork-Upload abgelehnt (Datei leer oder größer als 15 MB).");
            return false;
        }

        const normalizedUpload = {
            dataUrl: `data:image/${headerMatch[1].toLowerCase()};base64,${b64Payload}`,
            fileName: String(fileName || "upload"),
        };

        if (normRole === "backdrop") {
            const existingUploadIdx = Array.isArray(st.selectedItems)
                ? st.selectedItems.findIndex((it) => it.mode === "upload")
                : -1;
            if (existingUploadIdx < 0 && st.selectedItems.length >= MAX_BACKDROP_SELECTION) {
                setArtworkUploadError("backdrop", `Maximal ${MAX_BACKDROP_SELECTION} Hintergrundbilder auswählbar.`);
                return false;
            }
            artworkSkipped = false;
            st.uploadError = "";
            st.customUpload = normalizedUpload;
            const uploadEntry = {
                mode: "upload",
                dataUrl: normalizedUpload.dataUrl,
                fileName: normalizedUpload.fileName,
            };
            if (existingUploadIdx >= 0) {
                st.selectedItems[existingUploadIdx] = uploadEntry;
            } else {
                st.selectedItems.push(uploadEntry);
            }
            st.explicit = true;
            syncBackdropStateFromItems(st);
        } else {
            artworkSkipped = false;
            st.uploadError = "";
            st.customUpload = normalizedUpload;
            st.mode = "upload";
            st.selectedDataUrl = normalizedUpload.dataUrl;
            st.selectedUrl = "";
            st.selectedThumbUrl = "";
            st.selectedItems = [{
                mode: "upload",
                dataUrl: normalizedUpload.dataUrl,
                fileName: normalizedUpload.fileName,
            }];
            st.explicit = true;
        }
        renderArtworkRolePanel(normRole);
        updateArtworkToolbarState();
        updateArtworkSourceBar();
        return true;
    }

    function resolveDefaultArtworkQuery() {
        const vals = nfoEditor.getValues();
        let defaultTmdbId = "";
        if (artworkOverrideTmdbId && /^\d+$/.test(artworkOverrideTmdbId)) {
            defaultTmdbId = artworkOverrideTmdbId;
        } else if (successfulProviders.has("tmdb") && /^\d+$/.test(String(successfulProviders.get("tmdb") || ""))) {
            defaultTmdbId = String(successfulProviders.get("tmdb"));
        } else if (
            selectedMovie &&
            (String(selectedMovie.provider).toLowerCase() === "tmdb" || String(selectedMovie.provider).toLowerCase() === "tmdb_movie") &&
            /^\d+$/.test(String(selectedMovie.id || ""))
        ) {
            defaultTmdbId = String(selectedMovie.id);
        }
        const query = artworkOverrideQuery || String(vals.title || (selectedMovie ? selectedMovie.name : "") || "").trim();
        const year = String(vals.year || "").trim();
        return { tmdbId: defaultTmdbId, query, year };
    }

    async function loadArtworkCandidates(opts = {}) {
        const defaults = resolveDefaultArtworkQuery();
        const resolvedTmdbId = opts.tmdbId !== undefined ? String(opts.tmdbId || "").trim() : defaults.tmdbId;
        const resolvedQuery = opts.query !== undefined ? String(opts.query || "").trim() : defaults.query;
        const resolvedYear = opts.year !== undefined ? String(opts.year || "").trim() : defaults.year;
        const markExplicit = Boolean(opts.markExplicit);
        const resetSelection = Boolean(opts.resetSelection);

        const targetKey = resolvedTmdbId ? `tmdb:${resolvedTmdbId}` : `q:${resolvedQuery}|y:${resolvedYear}`;
        if (!opts.force && artworkCandidatesLoadedKey === targetKey && !artworkLoadError && !artworkLoading) {
            renderAllArtworkPanels();
            return null;
        }
        if (!fetchFn || (!resolvedTmdbId && !resolvedQuery)) {
            renderAllArtworkPanels();
            return null;
        }

        const reqSeq = ++artworkRequestSeq;
        const reqSession = sessionSeq;
        artworkLoading = true;
        artworkLoadError = "";
        renderAllArtworkPanels();

        const params = new URLSearchParams();
        if (resolvedTmdbId) params.set("tmdb_id", resolvedTmdbId);
        if (resolvedQuery) params.set("query", resolvedQuery);
        if (resolvedYear) params.set("year", resolvedYear);
        const url = `/api/artwork/candidates?${params.toString()}`;

        try {
            const res = await fetchFn(url);
            if (reqSeq !== artworkRequestSeq || reqSession !== sessionSeq) return null;
            if (!res || !res.ok) {
                let errMsg = `HTTP ${res ? res.status : "Fehler"}`;
                if (res && typeof res.json === "function") {
                    try {
                        const errData = await res.json();
                        if (errData && (errData.error || errData.message)) {
                            errMsg = String(errData.error || errData.message);
                        }
                    } catch (_) {}
                }
                throw new Error(errMsg);
            }
            const data = await res.json();
            if (reqSeq !== artworkRequestSeq || reqSession !== sessionSeq) return null;
            if (data && (data.status === "error" || data.error)) {
                throw new Error(String(data.error || "TMDb-Bildabruf fehlgeschlagen"));
            }

            artworkLoading = false;
            artworkLoadError = "";
            artworkCandidatesLoadedKey = targetKey;
            artworkResolvedTmdbId = String((data && data.tmdb_id) || resolvedTmdbId || "");
            artworkResolvedTitle = String((data && (data.matched_title || data.resolved_title)) || resolvedQuery || "");
            artworkMatches = (data && Array.isArray(data.matches)) ? data.matches : [];

            const candsFallback = (data && data.candidates && typeof data.candidates === "object") ? data.candidates : {};
            const roleLists = {
                poster: Array.isArray(data && data.posters)
                    ? data.posters
                    : (Array.isArray(candsFallback.poster) ? candsFallback.poster : []),
                backdrop: Array.isArray(data && data.backdrops)
                    ? data.backdrops
                    : (Array.isArray(candsFallback.backdrop) ? candsFallback.backdrop : []),
                logo: Array.isArray(data && data.logos)
                    ? data.logos
                    : (Array.isArray(candsFallback.logo) ? candsFallback.logo : []),
            };
            for (const role of ARTWORK_ROLES) {
                const list = roleLists[role] || [];
                const st = artworkState[role];
                st.candidates = list;
                if (resetSelection || !st.explicit) {
                    if (list.length > 0 && list[0] && list[0].url) {
                        const firstUrl = String(list[0].url);
                        const firstThumb = String(list[0].thumb_url || list[0].preview_url || list[0].url);
                        st.selectedItems = [{ mode: "url", url: firstUrl, thumbUrl: firstThumb }];
                        st.mode = "url";
                        st.selectedUrl = firstUrl;
                        st.selectedThumbUrl = firstThumb;
                        st.selectedDataUrl = "";
                        st.explicit = Boolean(markExplicit);
                    } else if (st.customUpload) {
                        st.selectedItems = Array.isArray(st.selectedItems)
                            ? st.selectedItems.filter((it) => it && it.mode === "upload")
                            : [];
                        if (role === "backdrop") {
                            syncBackdropStateFromItems(st);
                        } else if (st.selectedItems.length > 0) {
                            st.mode = "upload";
                            st.selectedDataUrl = String(st.selectedItems[0].dataUrl || "");
                            st.selectedUrl = "";
                            st.selectedThumbUrl = "";
                        } else {
                            st.mode = st.explicit ? "none" : "auto";
                            st.selectedUrl = "";
                            st.selectedThumbUrl = "";
                            st.selectedDataUrl = "";
                        }
                    } else {
                        st.selectedItems = [];
                        st.mode = "auto";
                        st.selectedUrl = "";
                        st.selectedThumbUrl = "";
                        st.selectedDataUrl = "";
                        st.explicit = false;
                    }
                }
            }
            renderAllArtworkPanels();
            return data;
        } catch (err) {
            if (reqSeq !== artworkRequestSeq || reqSession !== sessionSeq) return null;
            artworkLoading = false;
            artworkLoadError = err && err.message ? String(err.message) : String(err || "TMDb nicht erreichbar");
            renderAllArtworkPanels();
            return null;
        }
    }

    function ensureArtworkCandidatesForStep3() {
        const defaults = resolveDefaultArtworkQuery();
        if (artworkSearchInputEl && !artworkSearchInputEl.value) {
            artworkSearchInputEl.value = defaults.query || defaults.tmdbId || "";
        }
        loadArtworkCandidates({
            tmdbId: defaults.tmdbId,
            query: defaults.query,
            year: defaults.year,
            markExplicit: false,
            resetSelection: false,
        });
    }

    function triggerManualArtworkSearch() {
        const rawInput = artworkSearchInputEl ? String(artworkSearchInputEl.value || "").trim() : "";
        if (!rawInput) return null;
        const year = String(nfoEditor.getValues().year || "").trim();
        if (/^\d+$/.test(rawInput)) {
            artworkOverrideTmdbId = rawInput;
            artworkOverrideQuery = "";
            return loadArtworkCandidates({
                tmdbId: rawInput,
                query: "",
                year: "",
                markExplicit: true,
                resetSelection: true,
                force: true,
            });
        }
        artworkOverrideTmdbId = "";
        artworkOverrideQuery = rawInput;
        return loadArtworkCandidates({
            tmdbId: "",
            query: rawInput,
            year,
            markExplicit: true,
            resetSelection: true,
            force: true,
        });
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
        if (currentStep === 3) {
            artworkSkipped = false;
            ensureArtworkCandidatesForStep3();
        }
        if (currentStep === 4) {
            renderSummary();
            loadStep4Preview();
        }
        return currentStep;
    }

    function switchArtworkTab(tabName) {
        const raw = String(tabName || "poster").trim().toLowerCase();
        if (raw === "fanart" || raw === "backdrop") {
            activeArtworkTab = "fanart";
        } else if (raw === "logo") {
            activeArtworkTab = "logo";
        } else {
            activeArtworkTab = "poster";
        }
        const tabPairs = [
            ["poster", tabPoster, posterPanel],
            ["fanart", tabFanart, fanartPanel],
            ["logo", tabLogo, logoPanel],
        ];
        for (const [key, tabEl, panelEl] of tabPairs) {
            const isActive = activeArtworkTab === key;
            if (tabEl) {
                tabEl.classList.toggle("active", isActive);
                if (typeof tabEl.setAttribute === "function") {
                    tabEl.setAttribute("aria-selected", isActive ? "true" : "false");
                }
            }
            if (panelEl) {
                panelEl.classList.toggle("active", isActive);
                panelEl.classList.toggle("hidden", !isActive);
                if (isActive) {
                    if (typeof panelEl.removeAttribute === "function") panelEl.removeAttribute("hidden");
                } else if (typeof panelEl.setAttribute === "function") {
                    panelEl.setAttribute("hidden", "");
                }
            }
        }
        updateArtworkToolbarState();
        updateArtworkSourceBar();
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
                    if (queueActive) {
                        queueCurrentError = "Metadaten-Abruf fehlgeschlagen";
                        if (queueItems[queueIndex]) queueItems[queueIndex].hadError = true;
                        renderQueueHeader();
                    }
                    showError(`Metadaten-Abruf fehlgeschlagen (${errMsg})`, () => loadMovieMetadata(movie));
                    return;
                }

                if (errProviders.length > 0) {
                    if (queueActive) {
                        queueCurrentError = `Teil-Erfolg (${errProviders.map(formatProviderLabel).join(", ")} nicht erreichbar)`;
                        if (queueItems[queueIndex]) queueItems[queueIndex].hadError = true;
                        renderQueueHeader();
                    }
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

                if (queueActive && queueCurrentError) {
                    queueCurrentError = "";
                    renderQueueHeader();
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
            if (queueActive && queueCurrentError) {
                queueCurrentError = "";
                renderQueueHeader();
            }
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
            if (queueActive) {
                queueCurrentError = "Metadaten-Abruf fehlgeschlagen";
                if (queueItems[queueIndex]) queueItems[queueIndex].hadError = true;
                renderQueueHeader();
            }
            showError(`Metadaten-Abruf fehlgeschlagen (${err.message || err})`, () => loadMovieMetadata(movie));
        }
    }

    async function selectMovieInWizard(movie, fetchMeta = true, comparisonMovies = null) {
        searchRequestSeq += 1;
        const reqSeq = ++metadataRequestSeq;
        selectedMovie = {
            id: String(movie.id || "manual"),
            name: movie.name || movie.title || "",
            provider: movie.provider || "manual",
        };
        successfulProviders.clear();
        nfoEditor.clearProviderComparison();
        resetArtworkState();

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
        const reqSeq = ++searchRequestSeq;
        const reqSession = sessionSeq;
        const reqQueueIndex = queueIndex;
        const reqProjectName = currentProjectName;
        const isStaleSearch = () => (
            reqSeq !== searchRequestSeq ||
            reqSession !== sessionSeq ||
            (queueActive && reqQueueIndex !== queueIndex) ||
            reqProjectName !== currentProjectName
        );
        hideError();
        if (searchResults) {
            searchResults.innerHTML = "";
            searchResults.appendChild(mkEl(doc, "div", { cls: "mw-wizard-loading", text: "Suche läuft..." }));
        }
        try {
            const res = await fetchFn(`/api/search?type=movie&q=${encodeURIComponent(query)}`);
            if (isStaleSearch()) return [];
            if (!res || !res.ok) throw new Error(`HTTP ${res ? res.status : "Fehler"}`);
            const items = await res.json();
            if (isStaleSearch()) return [];
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
            if (queueActive && queueCurrentError) {
                queueCurrentError = "";
                renderQueueHeader();
            }
            return items;
        } catch (err) {
            if (isStaleSearch()) return [];
            if (searchResults) searchResults.innerHTML = "";
            if (queueActive) {
                queueCurrentError = "Provider-Suche fehlgeschlagen";
                if (queueItems[queueIndex]) queueItems[queueIndex].hadError = true;
                renderQueueHeader();
            }
            showError(`Suche fehlgeschlagen: ${err.message || err}`, () => performSearch(query));
            return [];
        }
    }

    function resetCurrentMovieState() {
        resetSizeEstimate();
        searchRequestSeq += 1;
        metadataRequestSeq += 1;
        previewRequestSeq += 1;
        hasValidPreview = false;
        currentPreviewPayload = null;
        clearPreviewCheckboxState();
        hideError();
        artworkSkipped = false;
        resetArtworkState();
        switchArtworkTab("poster");
        if (searchResults) searchResults.innerHTML = "";
        selectedMovie = null;
        selectedProviders = [];
        successfulProviders.clear();
        lastSearchResults = [];
        nfoEditor.clearProviderComparison();
    }

    function loadQueueItemAt(idx, { autoSearch = true } = {}) {
        if (!queueActive || idx < 0 || idx >= queueItems.length) return false;
        queueIndex = idx;
        queueCurrentError = "";
        const item = queueItems[queueIndex];
        currentProjectName = item.projectName;
        resetCurrentMovieState();
        const initialQuery = String(item.query || item.projectName || "").trim();
        if (searchInput) searchInput.value = initialQuery;
        nfoEditor.setValues(
            { title: initialQuery, year: "", plot: "", fsk: "", genres: [] },
            true,
            { loadedFields: initialQuery ? ["title"] : [] }
        );
        renderQueueHeader();
        goToStep(1);
        updateExecuteButtonState();
        if (initialQuery && autoSearch !== false && fetchFn) {
            performSearch(initialQuery);
        }
        return true;
    }

    function skipQueueMovie() {
        if (!queueActive || isExecutingProcess || queueItems.length === 0) return false;
        if (queueItems[queueIndex]) {
            queueItems[queueIndex].status = "skipped";
        }
        if (queueIndex < queueItems.length - 1) {
            loadQueueItemAt(queueIndex + 1, { autoSearch: true });
            return true;
        }
        close({ force: true });
        return true;
    }

    function getQueueState() {
        return {
            active: queueActive,
            index: queueIndex,
            total: queueItems.length,
            currentError: queueCurrentError,
            items: queueItems.map((it) => ({ ...it })),
        };
    }

    function open(openOptions = {}) {
        sessionSeq += 1;
        if (openOptions.onProcessSuccess) onProcessSuccessCallback = openOptions.onProcessSuccess;
        if (openOptions.onClosed) onClosedCallback = openOptions.onClosed;
        if (openOptions.onPersistOptions) persistOptionsCallback = openOptions.onPersistOptions;
        if (openOptions.onLog) logFn = openOptions.onLog;
        syncWizardOptionsFromContext(openOptions);

        const normalizedQueue = normalizeQueueInput(openOptions.queue);
        if (normalizedQueue.length > 0) {
            queueActive = true;
            queueItems = normalizedQueue;
            queueIndex = 0;
            queueCurrentError = "";
            modalOverlay.classList.remove("hidden");
            modalOverlay.classList.add("active");
            loadQueueItemAt(0, { autoSearch: openOptions.autoSearch !== false });
            return;
        }

        queueActive = false;
        queueItems = [];
        queueIndex = 0;
        queueCurrentError = "";
        renderQueueHeader();

        if (openOptions.projectName !== undefined) currentProjectName = String(openOptions.projectName || "");
        resetCurrentMovieState();

        const initialQuery = String(openOptions.query ?? "").trim();
        if (searchInput) searchInput.value = initialQuery;
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
        queueActive = false;
        renderQueueHeader();
        resetSizeEstimate();
        searchRequestSeq += 1;
        metadataRequestSeq += 1;
        previewRequestSeq += 1;
        artworkRequestSeq += 1;
        artworkSessionSeq += 1;
        uploadSeqByRole.poster += 1;
        uploadSeqByRole.backdrop += 1;
        uploadSeqByRole.logo += 1;
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
                searchRequestSeq += 1;
                metadataRequestSeq += 1;
                const manualTitle = searchInput ? String(searchInput.value || "").trim() : "";
                selectedMovie = { id: "manual", name: manualTitle || "Unbekannter Film", provider: "manual" };
                selectedProviders = [];
                successfulProviders.clear();
                nfoEditor.clearProviderComparison();
                resetArtworkState();
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
    bindClick(queueSkipBtn, () => skipQueueMovie());
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
    bindClick(tabLogo, () => switchArtworkTab("logo"));
    bindClick(artworkDeselectBtn, () => deselectArtworkRole(activeArtworkTab));
    bindClick(artworkUploadBtn, () => {
        if (artworkUploadInputEl && typeof artworkUploadInputEl.click === "function") {
            artworkUploadInputEl.click();
        }
    });
    bindClick(artworkSearchBtn, () => triggerManualArtworkSearch());
    bindClick(retryBtn, () => typeof lastRetryAction === "function" && lastRetryAction());

    if (artworkSearchInputEl && typeof artworkSearchInputEl.addEventListener === "function") {
        artworkSearchInputEl.addEventListener("keydown", (e) => {
            if (e && e.key === "Enter") {
                if (typeof e.preventDefault === "function") e.preventDefault();
                triggerManualArtworkSearch();
            }
        });
    }
    if (artworkMatchSelect && typeof artworkMatchSelect.addEventListener === "function") {
        artworkMatchSelect.addEventListener("change", () => {
            const chosenId = String(artworkMatchSelect.value || "").trim();
            if (chosenId && /^\d+$/.test(chosenId)) {
                artworkOverrideTmdbId = chosenId;
                artworkOverrideQuery = "";
                loadArtworkCandidates({
                    tmdbId: chosenId,
                    query: "",
                    year: "",
                    markExplicit: true,
                    resetSelection: true,
                    force: true,
                });
            }
        });
    }
    if (artworkUploadInputEl && typeof artworkUploadInputEl.addEventListener === "function") {
        artworkUploadInputEl.addEventListener("change", () => {
            const targetRole = normalizeArtworkRole(activeArtworkTab);
            const expectedSession = sessionSeq;
            const expectedArtworkSession = artworkSessionSeq;
            const reqUploadSeq = ++uploadSeqByRole[targetRole];
            const file = artworkUploadInputEl.files && artworkUploadInputEl.files[0];
            artworkUploadInputEl.value = "";
            if (!file) return;
            const fName = String(file.name || "upload");
            const fType = String(file.type || "").toLowerCase();
            const fSize = Number(file.size || 0);
            if (fSize <= 0 || fSize > MAX_ARTWORK_UPLOAD_BYTES) {
                setArtworkUploadError(targetRole, "Artwork-Upload abgelehnt (Datei leer oder größer als 15 MB).");
                return;
            }
            const validExt = /\.(jpe?g|png|webp)$/i.test(fName);
            const validMime = /^image\/(jpeg|jpg|png|webp)$/.test(fType);
            if (!validExt && !validMime) {
                setArtworkUploadError(targetRole, "Ungültiges Bildformat für den Artwork-Upload (erlaubt: JPG, PNG, WebP).");
                return;
            }
            if (typeof globalThis.FileReader !== "function") {
                setArtworkUploadError(targetRole, "FileReader wird in dieser Umgebung nicht unterstützt.");
                return;
            }
            const reader = new globalThis.FileReader();
            const isStale = () => (
                expectedSession !== sessionSeq ||
                expectedArtworkSession !== artworkSessionSeq ||
                reqUploadSeq !== uploadSeqByRole[targetRole]
            );
            reader.onload = () => {
                if (isStale()) return;
                if (typeof reader.result === "string" && reader.result) {
                    setCustomArtworkUpload(targetRole, reader.result, fName);
                } else {
                    setArtworkUploadError(targetRole, `Eigenes Bild (${fName}) konnte nicht gelesen werden.`);
                }
            };
            reader.onerror = () => {
                if (isStale()) return;
                setArtworkUploadError(targetRole, `Fehler beim Lesen der Bilddatei (${fName}).`);
            };
            reader.onabort = () => {
                if (isStale()) return;
                setArtworkUploadError(targetRole, `Lesen der Bilddatei (${fName}) wurde abgebrochen.`);
            };
            try {
                reader.readAsDataURL(file);
            } catch (err) {
                if (!isStale()) {
                    setArtworkUploadError(targetRole, `Fehler beim Lesen der Bilddatei (${fName}): ${err && err.message ? err.message : err}`);
                }
            }
        });
    }

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
        loadArtworkCandidates,
        selectArtworkCandidate,
        deselectArtworkRole,
        setCustomArtworkUpload,
        getArtworkState,
        handleEscapeKey,
        buildMovieBasePayload,
        buildProcessPayload,
        loadStep4Preview,
        executeStep4Process,
        skipQueueMovie,
        getQueueState,
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
