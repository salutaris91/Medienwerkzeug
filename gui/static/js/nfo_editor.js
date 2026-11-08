const VALID_FSK_VALUES = new Set(["0", "6", "12", "16", "18"]);
const ALL_FIELDS = ["title", "year", "plot", "fsk", "genres"];

export function normalizeFskValue(rawValue) {
    if (rawValue === null || rawValue === undefined) return "";
    const text = String(rawValue).trim();
    if (!text) return "";
    if (VALID_FSK_VALUES.has(text)) return text;
    const match = text.match(/\b(0|6|12|16|18)\b/);
    if (match && VALID_FSK_VALUES.has(match[1])) {
        return match[1];
    }
    return "";
}

export function parseGenresInput(rawValue) {
    if (Array.isArray(rawValue)) {
        const seen = new Set();
        const result = [];
        for (const item of rawValue) {
            const cleaned = String(item ?? "").trim();
            if (!cleaned) continue;
            const key = cleaned.toLowerCase();
            if (!seen.has(key)) {
                seen.add(key);
                result.push(cleaned);
            }
        }
        return result;
    }
    if (rawValue === null || rawValue === undefined) return [];
    const parts = String(rawValue).split(/[,;]/);
    return parseGenresInput(parts);
}

export function formatGenresValue(genres) {
    if (Array.isArray(genres)) {
        return parseGenresInput(genres).join(", ");
    }
    if (typeof genres === "string") {
        return parseGenresInput(genres).join(", ");
    }
    return "";
}

function normalizeSnapshot(data = {}) {
    return {
        title: String(data.title ?? data.name ?? "").trim(),
        year: String(data.year ?? "").trim(),
        plot: String(data.plot ?? data.overview ?? "").trim(),
        fsk: normalizeFskValue(data.fsk ?? data.mpaa ?? ""),
        genres: parseGenresInput(data.genres ?? data.genre ?? []),
    };
}

function fieldValuesEqual(fieldKey, a, b) {
    if (fieldKey === "genres") {
        if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false;
        return a.every((val, idx) => val === b[idx]);
    }
    return String(a ?? "") === String(b ?? "");
}

function hasNonEmptyFieldValue(fieldKey, val) {
    if (fieldKey === "genres") {
        return Array.isArray(val) && val.length > 0;
    }
    return String(val ?? "").trim() !== "";
}

function snapshotsEqual(a, b) {
    if (!a || !b) return false;
    return ALL_FIELDS.every((key) => fieldValuesEqual(key, a[key], b[key]));
}

function createFieldWrapper(doc, labelText, fieldKey, inputEl) {
    const wrapper = doc.createElement("div");
    wrapper.className = `mw-wizard-field mw-wizard-field-${fieldKey}`;
    wrapper.setAttribute("data-editor-field", fieldKey);

    const label = doc.createElement("label");
    label.className = "mw-wizard-label";
    if (inputEl.id) {
        label.setAttribute("for", inputEl.id);
    }
    label.textContent = labelText;

    wrapper.appendChild(label);
    wrapper.appendChild(inputEl);
    return wrapper;
}

export function renderNfoEditor(container, initialData = {}, options = {}) {
    if (!container) {
        throw new Error("renderNfoEditor requires a valid container element");
    }
    const doc = container.ownerDocument || document;
    const prefix = options.idPrefix || "mw-nfo-editor";

    container.innerHTML = "";
    if (container.children && container.children.length > 0) {
        container.children.length = 0;
    }

    const root = doc.createElement("div");
    root.className = "mw-wizard-nfo-editor";

    const topRow = doc.createElement("div");
    topRow.className = "mw-wizard-field-row";

    const titleInput = doc.createElement("input");
    titleInput.type = "text";
    titleInput.id = `${prefix}-title`;
    titleInput.className = "mw-wizard-input";
    titleInput.placeholder = "Filmtitel...";
    titleInput.setAttribute("data-field", "title");

    const yearInput = doc.createElement("input");
    yearInput.type = "text";
    yearInput.id = `${prefix}-year`;
    yearInput.className = "mw-wizard-input";
    yearInput.placeholder = "z. B. 2024";
    yearInput.setAttribute("data-field", "year");

    topRow.appendChild(createFieldWrapper(doc, "Titel", "title", titleInput));
    topRow.appendChild(createFieldWrapper(doc, "Jahr", "year", yearInput));

    const metaRow = doc.createElement("div");
    metaRow.className = "mw-wizard-field-row";

    const fskSelect = doc.createElement("select");
    fskSelect.id = `${prefix}-fsk`;
    fskSelect.className = "mw-wizard-select";
    fskSelect.setAttribute("data-field", "fsk");

    const fskOptions = [
        { value: "", label: "Keine Angabe" },
        { value: "0", label: "FSK 0" },
        { value: "6", label: "FSK 6" },
        { value: "12", label: "FSK 12" },
        { value: "16", label: "FSK 16" },
        { value: "18", label: "FSK 18" },
    ];
    for (const optDef of fskOptions) {
        const opt = doc.createElement("option");
        opt.value = optDef.value;
        opt.textContent = optDef.label;
        fskSelect.appendChild(opt);
    }

    const genresInput = doc.createElement("input");
    genresInput.type = "text";
    genresInput.id = `${prefix}-genres`;
    genresInput.className = "mw-wizard-input";
    genresInput.placeholder = "z. B. Drama, Sci-Fi";
    genresInput.setAttribute("data-field", "genres");

    metaRow.appendChild(createFieldWrapper(doc, "FSK", "fsk", fskSelect));
    metaRow.appendChild(createFieldWrapper(doc, "Genre", "genres", genresInput));

    const plotTextarea = doc.createElement("textarea");
    plotTextarea.id = `${prefix}-plot`;
    plotTextarea.className = "mw-wizard-textarea";
    plotTextarea.rows = 4;
    plotTextarea.placeholder = "Handlung / Beschreibung...";
    plotTextarea.setAttribute("data-field", "plot");

    root.appendChild(topRow);
    root.appendChild(metaRow);
    root.appendChild(createFieldWrapper(doc, "Plot", "plot", plotTextarea));
    container.appendChild(root);

    let baseline = normalizeSnapshot(initialData);
    let isInternalDomWrite = false;
    const touchedFields = new Set();
    const loadedFields = new Set();

    function instrumentElementValue(el, fieldKey) {
        if (!el) return;
        const proto = Object.getPrototypeOf(el);
        const desc = Object.getOwnPropertyDescriptor(el, "value")
            || (proto ? Object.getOwnPropertyDescriptor(proto, "value") : null);
        if (desc && typeof desc.get === "function" && typeof desc.set === "function") {
            Object.defineProperty(el, "value", {
                configurable: true,
                enumerable: desc.enumerable ?? true,
                get() {
                    return desc.get.call(this);
                },
                set(v) {
                    desc.set.call(this, v);
                    if (!isInternalDomWrite) {
                        touchedFields.add(fieldKey);
                    }
                },
            });
        } else {
            let currentVal = String(el.value ?? "");
            Object.defineProperty(el, "value", {
                configurable: true,
                enumerable: true,
                get() {
                    return currentVal;
                },
                set(v) {
                    currentVal = String(v ?? "");
                    if (!isInternalDomWrite) {
                        touchedFields.add(fieldKey);
                    }
                },
            });
        }
    }

    instrumentElementValue(titleInput, "title");
    instrumentElementValue(yearInput, "year");
    instrumentElementValue(plotTextarea, "plot");
    instrumentElementValue(fskSelect, "fsk");
    instrumentElementValue(genresInput, "genres");

    function applyValuesToDom(snap) {
        isInternalDomWrite = true;
        try {
            titleInput.value = snap.title;
            yearInput.value = snap.year;
            plotTextarea.value = snap.plot;
            fskSelect.value = snap.fsk;
            genresInput.value = formatGenresValue(snap.genres);
        } finally {
            isInternalDomWrite = false;
        }
    }

    for (const key of ALL_FIELDS) {
        if (hasNonEmptyFieldValue(key, baseline[key]) || (initialData && Object.prototype.hasOwnProperty.call(initialData, key) && initialData[key] !== undefined)) {
            loadedFields.add(key);
        }
    }
    applyValuesToDom(baseline);

    function getValues() {
        return {
            title: String(titleInput.value ?? "").trim(),
            year: String(yearInput.value ?? "").trim(),
            plot: String(plotTextarea.value ?? "").trim(),
            fsk: normalizeFskValue(fskSelect.value),
            genres: parseGenresInput(genresInput.value),
        };
    }

    function setValues(newData = {}, markClean = true, setOptions = {}) {
        const normalized = normalizeSnapshot(newData);
        applyValuesToDom(normalized);
        if (markClean) {
            baseline = normalized;
            touchedFields.clear();
            loadedFields.clear();
            if (Array.isArray(setOptions.loadedFields)) {
                for (const key of setOptions.loadedFields) {
                    if (ALL_FIELDS.includes(key)) loadedFields.add(key);
                }
            } else {
                for (const key of ALL_FIELDS) {
                    if (hasNonEmptyFieldValue(key, normalized[key]) || (newData && Object.prototype.hasOwnProperty.call(newData, key) && newData[key] !== undefined)) {
                        loadedFields.add(key);
                    }
                }
            }
        }
        return normalized;
    }

    function applyProviderMetadata(providerData = {}) {
        const currentVals = getValues();
        for (const key of ALL_FIELDS) {
            if (!fieldValuesEqual(key, currentVals[key], baseline[key])) {
                touchedFields.add(key);
            }
        }
        const providerSnap = normalizeSnapshot({
            title: (providerData.title !== undefined && providerData.title !== "") ? providerData.title : (providerData.name ?? baseline.title ?? ""),
            year: providerData.year ?? "",
            plot: providerData.plot ?? providerData.overview ?? "",
            fsk: providerData.fsk ?? providerData.mpaa ?? "",
            genres: providerData.genres ?? providerData.genre ?? [],
        });
        baseline = providerSnap;
        for (const key of ALL_FIELDS) {
            loadedFields.add(key);
        }
        const mergedDomValues = {
            title: touchedFields.has("title") ? currentVals.title : providerSnap.title,
            year: touchedFields.has("year") ? currentVals.year : providerSnap.year,
            plot: touchedFields.has("plot") ? currentVals.plot : providerSnap.plot,
            fsk: touchedFields.has("fsk") ? currentVals.fsk : providerSnap.fsk,
            genres: touchedFields.has("genres") ? currentVals.genres : providerSnap.genres,
        };
        applyValuesToDom(mergedDomValues);
        return getValues();
    }

    function resetToInitial() {
        applyValuesToDom(baseline);
        touchedFields.clear();
        return { ...baseline, genres: [...baseline.genres] };
    }

    function isDirty() {
        return !snapshotsEqual(getValues(), baseline) || touchedFields.size > 0;
    }

    function buildMovieOverrides() {
        const vals = getValues();
        return {
            title: vals.title,
            year: vals.year,
            plot: vals.plot,
            fsk: vals.fsk,
            genres: vals.genres,
        };
    }

    function buildWizardMovieOverrides() {
        const vals = getValues();
        const movie = {};
        for (const key of ALL_FIELDS) {
            if (!fieldValuesEqual(key, vals[key], baseline[key])) {
                touchedFields.add(key);
            }
            const val = vals[key];
            if (hasNonEmptyFieldValue(key, val)) {
                movie[key] = val;
            } else if (hasNonEmptyFieldValue(key, baseline[key]) || touchedFields.has(key)) {
                movie[key] = val;
            }
        }
        return { movie };
    }

    function getNfoOverrides() {
        return {
            movie: buildMovieOverrides(),
        };
    }

    const bindFieldEvents = (el, fieldKey) => {
        if (!el || typeof el.addEventListener !== "function") return;
        const handler = () => {
            touchedFields.add(fieldKey);
            if (typeof options.onChange === "function") {
                options.onChange(getValues(), isDirty());
            }
        };
        el.addEventListener("input", handler);
        el.addEventListener("change", handler);
    };

    bindFieldEvents(titleInput, "title");
    bindFieldEvents(yearInput, "year");
    bindFieldEvents(plotTextarea, "plot");
    bindFieldEvents(fskSelect, "fsk");
    bindFieldEvents(genresInput, "genres");

    const controller = {
        container,
        elements: {
            title: titleInput,
            year: yearInput,
            plot: plotTextarea,
            fsk: fskSelect,
            genres: genresInput,
        },
        getValues,
        setValues,
        applyProviderMetadata,
        resetToInitial,
        isDirty,
        buildMovieOverrides,
        buildWizardMovieOverrides,
        getNfoOverrides,
    };

    container._nfoEditor = controller;
    return controller;
}

export function getNfoEditorValues(target) {
    if (!target) {
        return { title: "", year: "", plot: "", fsk: "", genres: [] };
    }
    if (typeof target.getValues === "function") {
        return target.getValues();
    }
    if (target._nfoEditor && typeof target._nfoEditor.getValues === "function") {
        return target._nfoEditor.getValues();
    }
    return normalizeSnapshot(target);
}

export function buildMovieNfoOverrides(target) {
    const vals = getNfoEditorValues(target);
    return {
        movie: {
            title: vals.title,
            year: vals.year,
            plot: vals.plot,
            fsk: vals.fsk,
            genres: vals.genres,
        },
    };
}

export default {
    renderNfoEditor,
    getNfoEditorValues,
    buildMovieNfoOverrides,
    normalizeFskValue,
    parseGenresInput,
    formatGenresValue,
};
