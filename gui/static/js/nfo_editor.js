const VALID_FSK_VALUES = new Set(["0", "6", "12", "16", "18"]);
const ALL_FIELDS = ["title", "year", "plot", "fsk", "genres"];
const ALTERNATIVE_FIELDS = ["title", "year", "plot", "fsk"];
const SOURCE_BADGE_FIELDS = ["title", "year", "fsk", "genre", "plot"];

export function formatProviderLabel(provider) {
    const prov = String(provider || "").trim().toLowerCase();
    if (prov === "tmdb" || prov === "tmdb_movie") return "TMDb";
    if (prov === "ofdb") return "OFDb";
    if (prov === "manual") return "Manuell";
    return prov ? prov.toUpperCase() : "";
}

function syncElementClasses(el, ...initialClasses) {
    if (!el) return;
    const clean = initialClasses.filter(Boolean);
    el.className = clean.join(" ");
    if (el.classList && typeof el.classList.add === "function") {
        for (const cls of clean) {
            el.classList.add(cls);
        }
    }
}

function setElementClass(el, className, active) {
    if (!el || !className) return;
    const isOn = Boolean(active);
    if (el.classList && typeof el.classList.toggle === "function") {
        el.classList.toggle(className, isOn);
    }
    const parts = String(el.className || "").split(/\s+/).filter(Boolean);
    const has = parts.includes(className);
    if (isOn && !has) {
        parts.push(className);
        el.className = parts.join(" ");
    } else if (!isOn && has) {
        el.className = parts.filter((c) => c !== className).join(" ");
    }
}

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

export const normalizeFsk = normalizeFskValue;

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

export const parseGenres = parseGenresInput;

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

function safeSetAttribute(el, key, value) {
    if (el && typeof el.setAttribute === "function") {
        el.setAttribute(key, value);
    }
}

function normalizeSourceFieldKey(field) {
    const key = String(field || "").trim();
    if (key === "genres") return "genre";
    return SOURCE_BADGE_FIELDS.includes(key) ? key : "";
}

function createFieldWrapper(doc, labelText, fieldKey, inputEl, badgeEl = null, fieldBadgesContainer = null) {
    const wrapper = doc.createElement("div");
    syncElementClasses(wrapper, "mw-wizard-field", `mw-wizard-field-${fieldKey}`);
    safeSetAttribute(wrapper, "data-editor-field", fieldKey);

    const label = doc.createElement("label");
    syncElementClasses(label, "mw-wizard-label");
    if (inputEl.id) {
        safeSetAttribute(label, "for", inputEl.id);
    }
    label.textContent = labelText;
    if (badgeEl) {
        label.appendChild(badgeEl);
    }

    wrapper.appendChild(label);
    wrapper.appendChild(inputEl);
    if (fieldBadgesContainer) {
        wrapper.appendChild(fieldBadgesContainer);
    }
    return wrapper;
}

export function renderNfoEditor(container, initialData = {}, onChangeOrOptions = null, maybeOptions = {}) {
    if (!container) {
        throw new Error("renderNfoEditor requires a valid container element");
    }
    const directOnChange = typeof onChangeOrOptions === "function" ? onChangeOrOptions : null;
    const options = directOnChange
        ? (maybeOptions || {})
        : ((onChangeOrOptions && typeof onChangeOrOptions === "object") ? onChangeOrOptions : (maybeOptions || {}));
    const optionsOnChange = typeof options.onChange === "function" ? options.onChange : null;

    const doc = container.ownerDocument || document;
    const prefix = options.idPrefix || "mw-nfo-editor";
    const showSourceBadges = options.showSourceBadges === true;
    const titleLabelText = options.titleLabel || "Titel";

    container.innerHTML = "";

    const sourceBadges = {};
    const fieldSources = {
        title: "",
        year: "",
        fsk: "",
        genre: "",
        plot: "",
    };
    const fieldBadgeContainers = {};
    const providerBadgesByField = {
        title: {},
        year: {},
        genres: {},
        fsk: {},
        plot: {},
    };
    const selectedProvidersByField = {
        title: new Set(),
        year: new Set(),
        genres: new Set(),
        fsk: new Set(),
        plot: new Set(),
    };
    const initialSelectedProvidersByField = {
        title: new Set(),
        year: new Set(),
        genres: new Set(),
        fsk: new Set(),
        plot: new Set(),
    };
    let currentComparisonData = null;

    function createFieldBadgesContainer(fieldKey) {
        const badgesDiv = doc.createElement("div");
        badgesDiv.id = `${prefix}-badges-${fieldKey}`;
        syncElementClasses(badgesDiv, "mw-wizard-field-badges", "hidden");
        safeSetAttribute(badgesDiv, "data-field-badges", fieldKey);
        fieldBadgeContainers[fieldKey] = badgesDiv;
        return badgesDiv;
    }

    function createSourceBadge(sourceField) {
        if (!showSourceBadges) return null;
        const badge = doc.createElement("span");
        badge.className = "nfo-agent-source-badge";
        if (badge.classList && typeof badge.classList.add === "function") {
            badge.classList.add("nfo-agent-source-badge");
        }
        safeSetAttribute(badge, "data-source-field", sourceField);
        sourceBadges[sourceField] = badge;
        if (sourceField === "genre") {
            sourceBadges.genres = badge;
        }
        return badge;
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
    safeSetAttribute(titleInput, "data-field", "title");

    const yearInput = doc.createElement("input");
    yearInput.type = "text";
    yearInput.id = `${prefix}-year`;
    yearInput.className = "mw-wizard-input";
    yearInput.placeholder = "z. B. 2024";
    safeSetAttribute(yearInput, "data-field", "year");

    const titleFieldWrapper = createFieldWrapper(
        doc,
        titleLabelText,
        "title",
        titleInput,
        createSourceBadge("title"),
        createFieldBadgesContainer("title")
    );
    const titleLabel = titleFieldWrapper.children && titleFieldWrapper.children[0] ? titleFieldWrapper.children[0] : null;
    topRow.appendChild(titleFieldWrapper);
    topRow.appendChild(
        createFieldWrapper(doc, "Jahr", "year", yearInput, createSourceBadge("year"), createFieldBadgesContainer("year"))
    );

    const metaRow = doc.createElement("div");
    metaRow.className = "mw-wizard-field-row";

    const fskSelect = doc.createElement("select");
    fskSelect.id = `${prefix}-fsk`;
    fskSelect.className = "mw-wizard-select";
    safeSetAttribute(fskSelect, "data-field", "fsk");

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
    safeSetAttribute(genresInput, "data-field", "genres");

    metaRow.appendChild(
        createFieldWrapper(doc, "Genre", "genres", genresInput, createSourceBadge("genre"), createFieldBadgesContainer("genres"))
    );
    metaRow.appendChild(
        createFieldWrapper(doc, "FSK", "fsk", fskSelect, createSourceBadge("fsk"), createFieldBadgesContainer("fsk"))
    );

    const plotTextarea = doc.createElement("textarea");
    plotTextarea.id = `${prefix}-plot`;
    plotTextarea.className = "mw-wizard-textarea";
    plotTextarea.rows = 3;
    plotTextarea.placeholder = "Handlung / Beschreibung...";
    safeSetAttribute(plotTextarea, "data-field", "plot");

    root.appendChild(topRow);
    root.appendChild(metaRow);
    root.appendChild(
        createFieldWrapper(doc, "Plot", "plot", plotTextarea, createSourceBadge("plot"), createFieldBadgesContainer("plot"))
    );
    container.appendChild(root);

    let baseline = normalizeSnapshot(initialData);
    let isInternalDomWrite = false;
    const touchedFields = new Set();
    const loadedFields = new Set();

    function updateFieldBadgeSelectionDom(fieldKey) {
        const badgeMap = providerBadgesByField[fieldKey] || {};
        const selectedSet = selectedProvidersByField[fieldKey] || new Set();
        for (const [prov, btn] of Object.entries(badgeMap)) {
            if (!btn || btn.disabled) continue;
            const isSel = selectedSet.has(prov);
            setElementClass(btn, "selected", isSel);
            safeSetAttribute(btn, "aria-pressed", isSel ? "true" : "false");
        }
    }

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
                        if (selectedProvidersByField[fieldKey]) {
                            selectedProvidersByField[fieldKey].clear();
                            updateFieldBadgeSelectionDom(fieldKey);
                        }
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
                        if (selectedProvidersByField[fieldKey]) {
                            selectedProvidersByField[fieldKey].clear();
                            updateFieldBadgeSelectionDom(fieldKey);
                        }
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
        const parsedGenres = parseGenresInput(genresInput.value);
        const result = {
            title: String(titleInput.value ?? "").trim(),
            year: String(yearInput.value ?? "").trim(),
            plot: String(plotTextarea.value ?? "").trim(),
            fsk: normalizeFskValue(fskSelect.value),
            genres: parsedGenres,
        };
        Object.defineProperty(result, "genre", {
            value: parsedGenres,
            enumerable: false,
            configurable: true,
        });
        return result;
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
        for (const key of ALL_FIELDS) {
            selectedProvidersByField[key] = new Set(initialSelectedProvidersByField[key]);
            updateFieldBadgeSelectionDom(key);
        }
        return { ...baseline, genres: [...baseline.genres] };
    }

    function clearProviderComparison() {
        currentComparisonData = null;
        for (const key of ALL_FIELDS) {
            selectedProvidersByField[key].clear();
            initialSelectedProvidersByField[key].clear();
            providerBadgesByField[key] = {};
            const containerEl = fieldBadgeContainers[key];
            if (containerEl) {
                containerEl.innerHTML = "";
                setElementClass(containerEl, "hidden", true);
            }
        }
    }

    function getProviderComparison() {
        return currentComparisonData;
    }

    function notifyChangeListeners(changedFieldKey) {
        const sourceKey = changedFieldKey === "genres" ? "genre" : changedFieldKey;
        const currentValues = getValues();
        const dirty = isDirty();
        if (directOnChange) {
            directOnChange(currentValues, sourceKey, dirty);
        }
        if (optionsOnChange) {
            optionsOnChange(currentValues, dirty);
        }
    }

    function handleProviderBadgeClick(fieldKey, prov) {
        if (!currentComparisonData || !currentComparisonData.providers || !currentComparisonData.providers[prov]) return;
        const entry = currentComparisonData.providers[prov];
        if (entry.status !== "ok" || !hasNonEmptyFieldValue(fieldKey, entry.fields[fieldKey])) return;

        if (fieldKey === "genres") {
            const sel = selectedProvidersByField.genres;
            if (sel.has(prov)) {
                if (sel.size > 1) {
                    sel.delete(prov);
                } else {
                    sel.clear();
                    sel.add(prov);
                }
            } else {
                sel.add(prov);
            }
            const combined = [];
            for (const p of currentComparisonData.provider_order) {
                if (sel.has(p) && currentComparisonData.providers[p]?.status === "ok") {
                    combined.push(...(currentComparisonData.providers[p].fields.genres || []));
                }
            }
            const unionGenres = parseGenresInput(combined);
            isInternalDomWrite = true;
            try {
                genresInput.value = formatGenresValue(unionGenres);
            } finally {
                isInternalDomWrite = false;
            }
        } else {
            selectedProvidersByField[fieldKey] = new Set([prov]);
            const newVal = entry.fields[fieldKey];
            isInternalDomWrite = true;
            try {
                if (fieldKey === "title") titleInput.value = newVal;
                else if (fieldKey === "year") yearInput.value = newVal;
                else if (fieldKey === "plot") plotTextarea.value = newVal;
                else if (fieldKey === "fsk") fskSelect.value = newVal;
            } finally {
                isInternalDomWrite = false;
            }
        }

        touchedFields.add(fieldKey);
        updateFieldBadgeSelectionDom(fieldKey);
        const sourceKey = fieldKey === "genres" ? "genre" : fieldKey;
        if (showSourceBadges || directOnChange) {
            const activeLabels = Array.from(selectedProvidersByField[fieldKey]).map(formatProviderLabel);
            setFieldSource(sourceKey, activeLabels.join(" + ") || formatProviderLabel(prov));
        }
        notifyChangeListeners(fieldKey);
    }

    function setProviderComparison(comparisonData, _comparisonOptions = {}) {
        if (!comparisonData || typeof comparisonData !== "object" || !comparisonData.providers || typeof comparisonData.providers !== "object") {
            clearProviderComparison();
            return getValues();
        }

        const rawOrder = Array.isArray(comparisonData.provider_order) && comparisonData.provider_order.length > 0
            ? comparisonData.provider_order
            : Object.keys(comparisonData.providers);
        const providerOrder = [];
        const normalizedProviders = {};
        let hasAnyOkProvider = false;

        for (const rawProv of rawOrder) {
            const prov = String(rawProv || "").trim().toLowerCase() === "tmdb_movie"
                ? "tmdb"
                : String(rawProv || "").trim().toLowerCase();
            const rawEntry = comparisonData.providers[rawProv] ?? comparisonData.providers[prov];
            if (!prov || !rawEntry || providerOrder.includes(prov)) continue;
            providerOrder.push(prov);
            const isError = String(rawEntry.status || "").toLowerCase() === "error" || Boolean(rawEntry.error);
            if (!isError) hasAnyOkProvider = true;
            normalizedProviders[prov] = {
                provider: prov,
                movie_id: String(rawEntry.movie_id ?? rawEntry.id ?? ""),
                status: isError ? "error" : "ok",
                error: isError ? String(rawEntry.error || "Nicht erreichbar") : null,
                fields: isError ? normalizeSnapshot({}) : normalizeSnapshot(rawEntry.fields || rawEntry || {}),
            };
        }

        if (providerOrder.length === 0) {
            clearProviderComparison();
            return getValues();
        }

        currentComparisonData = {
            providers: normalizedProviders,
            provider_order: providerOrder,
        };

        const currentVals = getValues();
        for (const key of ALL_FIELDS) {
            if (!fieldValuesEqual(key, currentVals[key], baseline[key])) {
                touchedFields.add(key);
            }
        }

        if (hasAnyOkProvider) {
            const mergedBaseline = {
                title: "",
                year: "",
                plot: "",
                fsk: "",
                genres: [],
            };

            for (const fieldKey of ALTERNATIVE_FIELDS) {
                let winnerProv = null;
                for (const prov of providerOrder) {
                    const entry = normalizedProviders[prov];
                    if (entry.status === "ok" && hasNonEmptyFieldValue(fieldKey, entry.fields[fieldKey])) {
                        winnerProv = prov;
                        break;
                    }
                }
                if (winnerProv) {
                    mergedBaseline[fieldKey] = normalizedProviders[winnerProv].fields[fieldKey];
                    initialSelectedProvidersByField[fieldKey] = new Set([winnerProv]);
                } else {
                    mergedBaseline[fieldKey] = fieldKey === "title" ? (baseline.title || "") : "";
                    initialSelectedProvidersByField[fieldKey] = new Set();
                }
            }

            const genreContributors = [];
            const combinedGenres = [];
            for (const prov of providerOrder) {
                const entry = normalizedProviders[prov];
                if (entry.status === "ok" && hasNonEmptyFieldValue("genres", entry.fields.genres)) {
                    genreContributors.push(prov);
                    combinedGenres.push(...entry.fields.genres);
                }
            }
            mergedBaseline.genres = parseGenresInput(combinedGenres);
            initialSelectedProvidersByField.genres = new Set(genreContributors);

            baseline = normalizeSnapshot(mergedBaseline);
            for (const key of ALL_FIELDS) {
                loadedFields.add(key);
            }

            const mergedDomValues = {};
            for (const key of ALL_FIELDS) {
                if (touchedFields.has(key)) {
                    selectedProvidersByField[key] = new Set();
                    mergedDomValues[key] = currentVals[key];
                } else {
                    selectedProvidersByField[key] = new Set(initialSelectedProvidersByField[key]);
                    mergedDomValues[key] = baseline[key];
                    if (showSourceBadges) {
                        const sourceKey = key === "genres" ? "genre" : key;
                        const labels = Array.from(selectedProvidersByField[key]).map(formatProviderLabel);
                        if (labels.length > 0) setFieldSource(sourceKey, labels.join(" + "));
                    }
                }
            }
            applyValuesToDom(mergedDomValues);
        } else {
            for (const key of ALL_FIELDS) {
                selectedProvidersByField[key] = new Set();
                initialSelectedProvidersByField[key] = new Set();
            }
        }

        for (const fieldKey of ALL_FIELDS) {
            const badgeContainer = fieldBadgeContainers[fieldKey];
            providerBadgesByField[fieldKey] = {};
            if (!badgeContainer) continue;
            badgeContainer.innerHTML = "";
            setElementClass(badgeContainer, "hidden", false);

            for (const prov of providerOrder) {
                const entry = normalizedProviders[prov];
                const provLabel = formatProviderLabel(prov);
                const val = entry.fields[fieldKey];
                const isErr = entry.status === "error";
                const isEmpty = !isErr && !hasNonEmptyFieldValue(fieldKey, val);
                const isSelected = !isErr && !isEmpty && selectedProvidersByField[fieldKey].has(prov);

                let displayValue = "";
                if (isErr) {
                    displayValue = `${provLabel}: nicht erreichbar`;
                } else if (isEmpty) {
                    displayValue = fieldKey === "fsk" ? `${provLabel}: keine FSK` : `${provLabel}: keine Daten`;
                } else if (fieldKey === "fsk") {
                    displayValue = `FSK ${val}`;
                } else if (fieldKey === "genres") {
                    displayValue = formatGenresValue(val);
                } else {
                    displayValue = String(val);
                }

                const badgeBtn = doc.createElement("button");
                badgeBtn.type = "button";
                safeSetAttribute(badgeBtn, "data-provider", prov);
                safeSetAttribute(badgeBtn, "data-field", fieldKey);
                safeSetAttribute(badgeBtn, "aria-pressed", isSelected ? "true" : "false");

                const classes = ["mw-wizard-provider-badge"];
                if (isErr) {
                    classes.push("error", "mw-wizard-badge-error");
                    badgeBtn.disabled = true;
                    safeSetAttribute(badgeBtn, "disabled", "disabled");
                } else if (isEmpty) {
                    classes.push("empty", "mw-wizard-badge-empty");
                    badgeBtn.disabled = true;
                    safeSetAttribute(badgeBtn, "disabled", "disabled");
                } else if (isSelected) {
                    classes.push("selected");
                }
                syncElementClasses(badgeBtn, ...classes);

                const nameSpan = doc.createElement("span");
                syncElementClasses(nameSpan, "mw-wizard-provider-name");
                nameSpan.textContent = provLabel;

                const valSpan = doc.createElement("span");
                syncElementClasses(valSpan, "mw-wizard-provider-value");
                valSpan.textContent = displayValue;

                badgeBtn.appendChild(nameSpan);
                badgeBtn.appendChild(valSpan);

                badgeBtn.addEventListener("click", () => {
                    if (isErr || isEmpty || badgeBtn.disabled) return;
                    handleProviderBadgeClick(fieldKey, prov);
                });

                badgeContainer.appendChild(badgeBtn);
                providerBadgesByField[fieldKey][prov] = badgeBtn;
            }
        }

        return getValues();
    }

    function isDirty() {
        return !snapshotsEqual(getValues(), baseline);
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

    function setFieldSource(field, labelText = "") {
        const key = normalizeSourceFieldKey(field);
        if (!key) return;
        const text = String(labelText ?? "");
        fieldSources[key] = text;
        if (sourceBadges[key]) {
            sourceBadges[key].textContent = text;
        }
    }

    function getFieldSource(field) {
        const key = normalizeSourceFieldKey(field);
        if (!key) return "";
        if (sourceBadges[key]) {
            return String(sourceBadges[key].textContent ?? "");
        }
        return fieldSources[key] || "";
    }

    function clearFieldSources(defaultText = "") {
        for (const key of SOURCE_BADGE_FIELDS) {
            setFieldSource(key, defaultText);
        }
    }

    const bindFieldEvents = (el, fieldKey) => {
        if (!el || typeof el.addEventListener !== "function") return;
        const sourceKey = fieldKey === "genres" ? "genre" : fieldKey;
        const handler = () => {
            touchedFields.add(fieldKey);
            if (selectedProvidersByField[fieldKey]) {
                selectedProvidersByField[fieldKey].clear();
                updateFieldBadgeSelectionDom(fieldKey);
            }
            if (showSourceBadges || directOnChange) {
                setFieldSource(sourceKey, "manuell");
            }
            const currentValues = getValues();
            const dirty = isDirty();
            if (directOnChange) {
                directOnChange(currentValues, sourceKey, dirty);
            }
            if (optionsOnChange) {
                optionsOnChange(currentValues, dirty);
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
            titleInput,
            yearInput,
            plotInput: plotTextarea,
            fskSelect,
            genreInput: genresInput,
            titleLabel,
            sourceBadges,
            fieldBadges: fieldBadgeContainers,
            providerBadges: providerBadgesByField,
        },
        sourceBadges,
        fieldBadges: fieldBadgeContainers,
        providerBadges: providerBadgesByField,
        getValues,
        setValues,
        applyProviderMetadata,
        setProviderComparison,
        getProviderComparison,
        clearProviderComparison,
        resetToInitial,
        isDirty,
        buildMovieOverrides,
        buildWizardMovieOverrides,
        getNfoOverrides,
        setFieldSource,
        getFieldSource,
        clearFieldSources,
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

export function buildWizardMovieOverrides(target) {
    if (target && typeof target.buildWizardMovieOverrides === "function") {
        return target.buildWizardMovieOverrides();
    }
    if (target && target._nfoEditor && typeof target._nfoEditor.buildWizardMovieOverrides === "function") {
        return target._nfoEditor.buildWizardMovieOverrides();
    }
    return buildMovieNfoOverrides(target);
}

export default {
    renderNfoEditor,
    getNfoEditorValues,
    buildMovieNfoOverrides,
    buildWizardMovieOverrides,
    normalizeFskValue,
    normalizeFsk,
    parseGenresInput,
    parseGenres,
    formatGenresValue,
    formatProviderLabel,
};
