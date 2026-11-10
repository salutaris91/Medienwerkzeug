export function escapeHTML(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function formatDestinationHtml(destination) {
    return escapeHTML(destination ?? "").replace(/\r?\n/g, "<br>");
}

export function renderPreviewDestination(destEl, destination) {
    if (!destEl) return "";
    const html = formatDestinationHtml(destination);
    destEl.innerHTML = html;
    return html;
}

export function createPreviewCheckbox(item, checked = true, groupName = "renames") {
    const rawOld = (typeof item === "object" && item !== null) ? (item.old || "") : (item || "");
    const rawNew = (typeof item === "object" && item !== null) ? (item.new || "") : "";
    const safeOld = escapeHTML(rawOld);
    const safeNew = escapeHTML(rawNew);
    const safeGroup = escapeHTML(groupName);
    return `<label class="mw-wizard-result-item"><input type="checkbox" class="preview-cb-${safeGroup}" data-old="${safeOld}" data-new="${safeNew}" ${checked ? "checked" : ""}><div class="mw-wizard-result-item-body"><div class="mw-wizard-result-item-old">${safeOld}</div>${rawNew ? `<div class="mw-wizard-result-item-new">${safeNew}</div>` : ""}</div></label>`;
}

export function renderPreviewList(containerEl, items, groupName, emptyMessage = "Keine Einträge.", checked = true) {
    if (!containerEl) return "";
    const list = Array.isArray(items) ? items : [];
    const resolveChecked = (entry) => (typeof checked === "function" ? Boolean(checked(entry, groupName)) : Boolean(checked));
    const html = list.length > 0
        ? list.map((entry) => createPreviewCheckbox(entry, resolveChecked(entry), groupName)).join("")
        : `<div class="mw-wizard-result-empty">${escapeHTML(emptyMessage)}</div>`;
    containerEl.innerHTML = html;
    return html;
}

export function renderSimilarExistingHint(similarBox, similarText, similarExisting, options = {}) {
    const idPrefix = options.idPrefix || "preview-similar";
    const logFn = typeof options.onLog === "function"
        ? options.onLog
        : (typeof globalThis.appendConsoleLog === "function" ? globalThis.appendConsoleLog : null);

    try {
        if (similarBox && similarBox.classList) {
            similarBox.classList.add("hidden");
        }
        if (similarText) {
            similarText.innerHTML = "";
        }
        if (!similarExisting || !similarBox || !similarText) {
            return false;
        }

        const exactRaw = Array.isArray(similarExisting.exact) ? similarExisting.exact : [];
        const similarRaw = Array.isArray(similarExisting.similar) ? similarExisting.similar : [];

        const exactFolderSet = new Set(
            exactRaw
                .map((item) => (item && typeof item === "object" ? item.folder : item))
                .filter(Boolean)
        );
        const similarItems = similarRaw.filter((item) => {
            const folderName = item && typeof item === "object" ? item.folder : item;
            return folderName && !exactFolderSet.has(folderName);
        });

        if (exactRaw.length === 0 && similarItems.length === 0) {
            return false;
        }

        const renderItem = (item, itemClass) => {
            const rawFolder = (item && typeof item === "object") ? (item.folder || "") : String(item || "");
            const rawRel = (item && typeof item === "object") ? (item.relative_path || "") : "";
            const rawOverlap = (item && typeof item === "object" && item.overlap !== undefined) ? item.overlap : "";
            const safeFolder = escapeHTML(rawFolder);
            const safeRel = escapeHTML(rawRel);
            const safeOverlap = escapeHTML(rawOverlap);
            const relSuffix = (rawRel && rawRel !== rawFolder)
                ? ` <span class="mw-wizard-similar-rel">(${safeRel})</span>`
                : "";
            const overlapAttr = safeOverlap !== "" ? ` data-overlap="${safeOverlap}"` : "";
            return `<li class="${itemClass}"${overlapAttr}><strong>${safeFolder}</strong>${relSuffix}</li>`;
        };

        let sectionsHtml = "";

        if (exactRaw.length > 0) {
            const exactListHtml = exactRaw.map((item) => renderItem(item, "similar-exact-item")).join("");
            sectionsHtml += `<div id="${idPrefix}-exact" class="mw-wizard-similar-section"><div class="mw-wizard-similar-exact-heading">Diesen Film hast du schon auf dem NAS:</div><ul class="mw-wizard-similar-list">${exactListHtml}</ul></div>`;
        }

        if (similarItems.length > 0) {
            const visibleItems = similarItems.slice(0, 5);
            const hiddenItems = similarItems.slice(5);
            const visibleListHtml = visibleItems.map((item) => renderItem(item, "similar-fuzzy-item similar-fuzzy-visible")).join("");
            let moreHtml = "";
            if (hiddenItems.length > 0) {
                const hiddenListHtml = hiddenItems.map((item) => renderItem(item, "similar-fuzzy-item similar-fuzzy-collapsed")).join("");
                moreHtml = `<details id="${idPrefix}-more" class="mw-wizard-similar-more"><summary class="mw-wizard-similar-summary">Weitere ${escapeHTML(hiddenItems.length)} Treffer anzeigen</summary><ul class="mw-wizard-similar-list">${hiddenListHtml}</ul></details>`;
            }
            sectionsHtml += `<div id="${idPrefix}-fuzzy" class="mw-wizard-similar-section"><div class="mw-wizard-similar-fuzzy-heading">Ähnliche Titel – gehören evtl. dazu:</div><ul id="${idPrefix}-fuzzy-visible-list" class="mw-wizard-similar-list">${visibleListHtml}</ul>${moreHtml}</div>`;
        }

        similarText.innerHTML = sectionsHtml;
        similarBox.classList.remove("hidden");
        return true;
    } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        if (typeof console !== "undefined" && typeof console.error === "function") {
            console.error("[PreviewRender]: Fehler beim Rendern des #91-Hinweises:", err);
        }
        if (logFn) {
            try {
                logFn(`[System]: Hinweis auf ähnliche Titel konnte nicht dargestellt werden (${msg}).`);
            } catch (_) {}
        }
        try {
            if (similarBox && similarBox.classList) similarBox.classList.add("hidden");
        } catch (_) {}
        return false;
    }
}

export function collectPreviewSelection(root) {
    const groupContainers = {
        renames: root && root.listRenames ? root.listRenames : null,
        subs: root && root.listSubs ? root.listSubs : null,
        junk: root && root.listJunk ? root.listJunk : null,
    };
    const fallbackScope = (root && typeof root.querySelectorAll === "function")
        ? root
        : (root && root.root && typeof root.root.querySelectorAll === "function"
            ? root.root
            : (!root && typeof document !== "undefined" ? document : null));

    const getOld = (cb) => (cb.dataset && cb.dataset.old !== undefined ? cb.dataset.old : cb.getAttribute("data-old")) || "";
    const getNew = (cb) => (cb.dataset && cb.dataset.new !== undefined ? cb.dataset.new : cb.getAttribute("data-new")) || "";

    const collectChecked = (group) => {
        const scope = (groupContainers[group] && typeof groupContainers[group].querySelectorAll === "function")
            ? groupContainers[group]
            : fallbackScope;
        if (!scope || typeof scope.querySelectorAll !== "function") return [];
        const allItems = Array.from(scope.querySelectorAll(`.preview-cb-${group}`));
        if (allItems.length > 0) {
            return allItems.filter((cb) => Boolean(cb && cb.checked));
        }
        return Array.from(scope.querySelectorAll(`.preview-cb-${group}:checked`)).filter((cb) => Boolean(cb && cb.checked));
    };

    const explicit_renames = collectChecked("renames").map((cb) => ({ old: getOld(cb), new: getNew(cb) }));
    const explicit_subs = collectChecked("subs").map((cb) => ({ old: getOld(cb), new: getNew(cb) }));
    const explicit_junk = collectChecked("junk").map((cb) => getOld(cb));

    return { explicit_renames, explicit_subs, explicit_junk };
}

export function renderPreviewData(targets = {}, data = {}, options = {}) {
    renderSimilarExistingHint(targets.similarBox, targets.similarText, data ? data.similar_existing : null, options);
    renderPreviewDestination(targets.dest, data ? data.destination : "");
    const checkedForGroup = (groupName) =>
        typeof options.isItemChecked === "function"
            ? (entry) => options.isItemChecked(entry, groupName)
            : true;
    renderPreviewList(
        targets.listRenames,
        data && Array.isArray(data.renames) ? data.renames : [],
        "renames",
        options.emptyRenamesMessage || "Keine Videos gefunden.",
        checkedForGroup("renames")
    );
    renderPreviewList(
        targets.listSubs,
        data && Array.isArray(data.subs) ? data.subs : [],
        "subs",
        options.emptySubsMessage || "Keine Untertitel/Extras gefunden.",
        checkedForGroup("subs")
    );
    renderPreviewList(
        targets.listJunk,
        data && Array.isArray(data.junk) ? data.junk : [],
        "junk",
        options.emptyJunkMessage || "Keine Müll-Dateien gefunden! Ordner ist sauber.",
        checkedForGroup("junk")
    );
}

export default {
    escapeHTML,
    formatDestinationHtml,
    renderPreviewDestination,
    createPreviewCheckbox,
    renderPreviewList,
    renderSimilarExistingHint,
    collectPreviewSelection,
    renderPreviewData,
};
