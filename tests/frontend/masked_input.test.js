import test from "node:test";
import assert from "node:assert";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
    isMaskedValue,
    updateMaskedInputState,
    setMaskedInputValue,
    setupMaskedInput,
    validateMaskedInput,
    validateAllMaskedFields
} from "../../gui/static/js/masked_input.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function createMockInput(id = "settings-tmdb-key") {
    const listeners = {};
    const classSet = new Set();
    const attributes = {};

    const element = {
        id,
        value: "",
        placeholder: "",
        dataset: {},
        classList: {
            add(cls) { classSet.add(cls); },
            remove(cls) { classSet.delete(cls); },
            contains(cls) { return classSet.has(cls); }
        },
        setAttribute(name, val) { attributes[name] = String(val); },
        getAttribute(name) { return attributes[name]; },
        removeAttribute(name) { delete attributes[name]; },
        addEventListener(event, handler) {
            if (!listeners[event]) listeners[event] = [];
            listeners[event].push(handler);
        },
        dispatch(event, eventObj = {}) {
            let prevented = false;
            const e = {
                type: event,
                preventDefault: () => { prevented = true; },
                defaultPrevented: () => prevented,
                ...eventObj
            };
            if (listeners[event]) {
                for (const handler of listeners[event]) {
                    handler(e);
                }
            }
            return e;
        },
        blur() {
            if (globalThis.document && globalThis.document.activeElement === this) {
                globalThis.document.activeElement = null;
            }
            this.dispatch("blur");
        },
        focus() {
            if (globalThis.document) {
                globalThis.document.activeElement = this;
            }
            this.dispatch("focus");
        }
    };
    return element;
}

function createMockButton(id = "") {
    const listeners = {};
    const classSet = new Set();
    const attributes = {};

    return {
        id,
        style: { display: "none" },
        disabled: false,
        attributes,
        parentElement: null,
        classList: {
            add(cls) { classSet.add(cls); },
            remove(cls) { classSet.delete(cls); },
            contains(cls) { return classSet.has(cls); }
        },
        setAttribute(name, val) {
            attributes[name] = String(val);
            if (name === "disabled") this.disabled = true;
        },
        getAttribute(name) { return attributes[name]; },
        removeAttribute(name) {
            delete attributes[name];
            if (name === "disabled") this.disabled = false;
        },
        addEventListener(event, handler) {
            if (!listeners[event]) listeners[event] = [];
            listeners[event].push(handler);
        },
        focus() {
            if (globalThis.document) {
                globalThis.document.activeElement = this;
            }
            this.dispatch("focus");
        },
        blur() {
            if (globalThis.document && globalThis.document.activeElement === this) {
                globalThis.document.activeElement = null;
            }
            this.dispatch("blur");
        },
        click() {
            let prevented = false;
            const e = { type: "click", preventDefault: () => { prevented = true; }, defaultPrevented: () => prevented };
            if (listeners["click"]) {
                for (const handler of listeners["click"]) {
                    handler(e);
                }
            }
            return e;
        },
        dispatch(event, eventObj = {}) {
            let prevented = false;
            let stopped = false;
            const e = {
                type: event,
                target: this,
                preventDefault: () => { prevented = true; },
                defaultPrevented: () => prevented,
                stopPropagation: () => { stopped = true; },
                ...eventObj
            };
            if (listeners[event]) {
                for (const handler of listeners[event]) {
                    handler(e);
                }
            }
            if (!stopped && this.parentElement && typeof this.parentElement.dispatch === "function") {
                this.parentElement.dispatch(event, e);
            }
            return e;
        }
    };
}

function createMockDOM(fieldIds) {
    const elements = {};
    for (const id of fieldIds) {
        const input = createMockInput(id);
        const badge = {
            id: `${id}-badge`,
            textContent: "",
            className: "",
            attributes: {},
            setAttribute(name, val) { this.attributes[name] = String(val); }
        };
        const errorEl = {
            id: `${id}-error`,
            textContent: ""
        };
        const deleteBtn = createMockButton(`${id}-delete`);
        const confirmEl = {
            id: `${id}-confirm`,
            style: { display: "none" },
            attributes: {},
            listeners: {},
            setAttribute(name, val) { this.attributes[name] = String(val); },
            addEventListener(event, handler) {
                if (!this.listeners[event]) this.listeners[event] = [];
                this.listeners[event].push(handler);
            },
            dispatch(event, eventObj = {}) {
                let prevented = false;
                let stopped = false;
                const e = {
                    type: event,
                    target: eventObj.target || this,
                    preventDefault: () => { prevented = true; },
                    defaultPrevented: () => prevented,
                    stopPropagation: () => { stopped = true; },
                    ...eventObj
                };
                if (this.listeners[event]) {
                    for (const handler of this.listeners[event]) {
                        handler(e);
                    }
                }
                return e;
            }
        };
        const confirmYesBtn = createMockButton(`${id}-confirm-yes`);
        const confirmNoBtn = createMockButton(`${id}-confirm-no`);
        confirmYesBtn.parentElement = confirmEl;
        confirmNoBtn.parentElement = confirmEl;

        elements[id] = input;
        elements[`${id}-badge`] = badge;
        elements[`${id}-error`] = errorEl;
        elements[`${id}-delete`] = deleteBtn;
        elements[`${id}-confirm`] = confirmEl;
        elements[`${id}-confirm-yes`] = confirmYesBtn;
        elements[`${id}-confirm-no`] = confirmNoBtn;
    }

    const previousDoc = globalThis.document;
    globalThis.document = {
        activeElement: null,
        getElementById(id) {
            return elements[id] || null;
        }
    };

    return {
        elements,
        restore() {
            if (previousDoc) {
                globalThis.document = previousDoc;
            } else {
                delete globalThis.document;
            }
        }
    };
}

test("isMaskedValue detects masked strings correctly", () => {
    assert.strictEqual(isMaskedValue("****1234"), true);
    assert.strictEqual(isMaskedValue("****"), true);
    assert.strictEqual(isMaskedValue("abc****def"), true);
    assert.strictEqual(isMaskedValue("my_real_key"), false);
    assert.strictEqual(isMaskedValue(""), false);
    assert.strictEqual(isMaskedValue(null), false);
});

test("AC1: Clear-on-Edit clears masked field on first keypress, not on focus", () => {
    const dom = createMockDOM(["settings-tmdb-key"]);
    try {
        const input = dom.elements["settings-tmdb-key"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****1234", { configured: "Hinterlegt" });

        // Pure focus: value remains unchanged (****1234)
        input.focus();
        assert.strictEqual(input.value, "****1234");
        assert.strictEqual(input.dataset.masked, "true");

        // First keypress (character "a"): clears the mask
        const keyEvent = input.dispatch("keydown", { key: "a" });
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.masked, "false");
        assert.strictEqual(input.dataset.editing, "true");
    } finally {
        dom.restore();
    }
});

test("AC1: Clear-on-Edit with Backspace / Delete clears entire mask cleanly", () => {
    const dom = createMockDOM(["settings-tmdb-key"]);
    try {
        const input = dom.elements["settings-tmdb-key"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****1234", { configured: "Hinterlegt" });

        input.focus();
        assert.strictEqual(input.value, "****1234");

        // Backspace keypress
        const ev = input.dispatch("keydown", { key: "Backspace" });
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.masked, "false");
        assert.strictEqual(input.dataset.editing, "true");
        assert.strictEqual(ev.defaultPrevented(), true);
    } finally {
        dom.restore();
    }
});

test("AC2: Blur-Restore restores masked value when focused and left without edit", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****5678", { configured: "Hinterlegt" });

        // Focus then blur without editing
        input.focus();
        input.blur();

        assert.strictEqual(input.value, "****5678");
        assert.strictEqual(input.dataset.editing, "false");
    } finally {
        dom.restore();
    }
});

test("AC2: Escape key restores original masked value", () => {
    const dom = createMockDOM(["settings-whatsapp-apikey"]);
    try {
        const input = dom.elements["settings-whatsapp-apikey"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****9999", { configured: "Hinterlegt" });

        input.focus();
        input.dispatch("keydown", { key: "x" });
        input.value = "partial_new";

        // Press Escape
        input.dispatch("keydown", { key: "Escape" });
        assert.strictEqual(input.value, "****9999");
        assert.strictEqual(input.dataset.editing, "false");
    } finally {
        dom.restore();
    }
});

test("AC3: Validation Gate marks field with **** as invalid and blocks submit", () => {
    const dom = createMockDOM(["settings-tmdb-key"]);
    try {
        const input = dom.elements["settings-tmdb-key"];
        const errorEl = dom.elements["settings-tmdb-key-error"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****1234");

        // Simulate user partially modifying to ****1235
        input.value = "****1235";

        const result = validateMaskedInput(input);
        assert.strictEqual(result.valid, false);
        assert.strictEqual(result.changed, true);
        assert.ok(result.error && result.error.includes("Maskierungszeichen"));
        assert.strictEqual(input.classList.contains("is-invalid"), true);
        assert.strictEqual(input.getAttribute("aria-invalid"), "true");
        assert.ok(errorEl.textContent.includes("Maskierungszeichen"));
    } finally {
        dom.restore();
    }
});

test("AC4: Dirty-Tracking includes only modified fields across all 6 fields", () => {
    const fieldIds = [
        "settings-tmdb-key",
        "settings-tvdb-key",
        "settings-telegram-token",
        "settings-telegram-chat-id",
        "settings-whatsapp-apikey",
        "settings-whatsapp-phone"
    ];
    const dom = createMockDOM(fieldIds);
    try {
        // Setup all 6 with pristine values
        setMaskedInputValue(dom.elements["settings-tmdb-key"], "****tmdb");
        setMaskedInputValue(dom.elements["settings-tvdb-key"], "****tvdb");
        setMaskedInputValue(dom.elements["settings-telegram-token"], "****tgtoken");
        setMaskedInputValue(dom.elements["settings-telegram-chat-id"], "****chatid");
        setMaskedInputValue(dom.elements["settings-whatsapp-apikey"], "****waapi");
        setMaskedInputValue(dom.elements["settings-whatsapp-phone"], "****waphone");

        // Only modify telegram-token and tmdb-key
        dom.elements["settings-telegram-token"].value = "new_tg_token_123";
        dom.elements["settings-tmdb-key"].value = "new_tmdb_key_456";

        const validation = validateAllMaskedFields(fieldIds);
        assert.strictEqual(validation.valid, true);
        assert.strictEqual(validation.errors.length, 0);

        const changed = validation.changedFields;
        assert.strictEqual(Object.keys(changed).length, 2);
        assert.strictEqual(changed["settings-telegram-token"], "new_tg_token_123");
        assert.strictEqual(changed["settings-tmdb-key"], "new_tmdb_key_456");
        assert.strictEqual("settings-tvdb-key" in changed, false);
        assert.strictEqual("settings-telegram-chat-id" in changed, false);
        assert.strictEqual("settings-whatsapp-apikey" in changed, false);
        assert.strictEqual("settings-whatsapp-phone" in changed, false);
    } finally {
        dom.restore();
    }
});

test("AC5: Trimming removes leading and trailing whitespace from input values", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        setMaskedInputValue(input, "****old");
        input.value = "   my_trimmed_token   ";

        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.value, "my_trimmed_token");
    } finally {
        dom.restore();
    }
});

test("AC6: Decoupled Key Presence indicator works for short keys (****) and empty keys", () => {
    const dom = createMockDOM(["settings-tvdb-key", "settings-whatsapp-phone"]);
    try {
        const shortKeyInput = dom.elements["settings-tvdb-key"];
        const shortKeyBadge = dom.elements["settings-tvdb-key-badge"];

        // Short key (<= 8 chars) masked to plain "****"
        setMaskedInputValue(shortKeyInput, "****", { configured: "Hinterlegt", unconfigured: "Nicht konfiguriert" });
        assert.strictEqual(shortKeyInput.dataset.hasKey, "true");
        assert.strictEqual(shortKeyBadge.textContent, "✓");
        assert.strictEqual(shortKeyBadge.className, "masked-key-badge badge-configured");

        // Unconfigured empty key
        const emptyInput = dom.elements["settings-whatsapp-phone"];
        const emptyBadge = dom.elements["settings-whatsapp-phone-badge"];
        setMaskedInputValue(emptyInput, "", { configured: "Hinterlegt", unconfigured: "Nicht konfiguriert" });
        assert.strictEqual(emptyInput.dataset.hasKey, "false");
        assert.strictEqual(emptyBadge.textContent, "○");
        assert.strictEqual(emptyBadge.className, "masked-key-badge badge-unconfigured");
    } finally {
        dom.restore();
    }
});

test("AC12: Whitespace-only input is rejected and marked as invalid", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        setMaskedInputValue(input, "****token");
        input.value = "    ";

        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, false);
        assert.strictEqual(input.classList.contains("is-invalid"), true);
        assert.ok(res.error && res.error.includes("Leerzeichen"));
    } finally {
        dom.restore();
    }
});

test("W1: Blur-Restore restores masked value when user triggers Clear-on-Edit but blurs with empty input", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        const badge = dom.elements["settings-telegram-token-badge"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****5678", { configured: "Hinterlegt" });

        input.focus();
        // Clear-on-Edit triggered by backspace or keypress
        input.dispatch("keydown", { key: "Backspace" });
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.editing, "true");

        // User blurs without entering any new key
        input.blur();

        // Must restore original masked value and editing state
        assert.strictEqual(input.value, "****5678");
        assert.strictEqual(input.dataset.editing, "false");
        assert.strictEqual(input.dataset.masked, "true");
        assert.strictEqual(badge.textContent, "✓");
        assert.strictEqual(badge.className, "masked-key-badge badge-configured");

        // Validation must not mark as changed
        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, false);
    } finally {
        dom.restore();
    }
});

test("W1: Blur-Restore restores masked value when user enters whitespace and blurs", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****5678", { configured: "Hinterlegt" });

        input.focus();
        input.dispatch("keydown", { key: " " });
        input.value = "   ";

        // User blurs
        input.blur();

        assert.strictEqual(input.value, "****5678");
        assert.strictEqual(input.dataset.editing, "false");
        assert.strictEqual(input.dataset.masked, "true");
    } finally {
        dom.restore();
    }
});

test("W1: Validation treats field cleared via Clear-on-Edit without new value as unchanged (changed=false)", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****5678", { configured: "Hinterlegt" });

        input.focus();
        input.dispatch("keydown", { key: "Backspace" });
        assert.strictEqual(input.value, "");

        // Direct validation before blur
        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, false);
        assert.strictEqual(res.value, "****5678");
    } finally {
        dom.restore();
    }
});

test("W1: User clears field, types a new valid key, blurs -> new key is preserved and validation reports changed=true", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        const badge = dom.elements["settings-telegram-token-badge"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****5678", { configured: "Hinterlegt" });

        input.focus();
        input.dispatch("keydown", { key: "x" });
        input.value = "new_real_secret_token";
        input.dispatch("input");

        // User blurs
        input.blur();

        // Real new value is kept
        assert.strictEqual(input.value, "new_real_secret_token");
        assert.strictEqual(input.dataset.editing, "true");
        assert.strictEqual(badge.textContent, "✓");
        assert.strictEqual(badge.className, "masked-key-badge badge-valid");

        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, true);
        assert.strictEqual(res.value, "new_real_secret_token");
    } finally {
        dom.restore();
    }
});

test("W1 / Decision A: Cleared input badge does not claim key removal (Roadmap Item #59)", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        const badge = dom.elements["settings-telegram-token-badge"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****5678", { configured: "Hinterlegt" });

        input.focus();
        input.dispatch("keydown", { key: "Backspace" });
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.editing, "true");

        // State update when cleared
        updateMaskedInputState(input);

        assert.notStrictEqual(badge.attributes["title"], "Wird entfernt");
        assert.strictEqual(badge.attributes["title"], "Unverändert (Löschen nicht unterstützt)");
        assert.strictEqual(badge.textContent, "○");
    } finally {
        dom.restore();
    }
});

// ============================================================================
// Roadmap Item #59: Expliziter Löschweg für maskierte Key-Felder (AK1–AK7)
// ============================================================================

test("Item 59 AK1: Configured key (dataset.hasKey='true') offers visible delete button", () => {
    const dom = createMockDOM(["settings-tmdb-key", "settings-telegram-token"]);
    try {
        const tmdbInput = dom.elements["settings-tmdb-key"];
        const tmdbDeleteBtn = dom.elements["settings-tmdb-key-delete"];
        setupMaskedInput(tmdbInput);
        setMaskedInputValue(tmdbInput, "****1234", { configured: "Hinterlegt" });

        assert.strictEqual(tmdbInput.dataset.hasKey, "true");
        assert.strictEqual(tmdbDeleteBtn.style.display, "");
        assert.strictEqual(tmdbDeleteBtn.disabled, false);
        assert.strictEqual(tmdbDeleteBtn.attributes["aria-hidden"], "false");
    } finally {
        dom.restore();
    }
});

test("Item 59 AK2: Unconfigured key (dataset.hasKey='false') does not offer active delete button", () => {
    const dom = createMockDOM(["settings-whatsapp-apikey"]);
    try {
        const waInput = dom.elements["settings-whatsapp-apikey"];
        const waDeleteBtn = dom.elements["settings-whatsapp-apikey-delete"];
        setupMaskedInput(waInput);
        setMaskedInputValue(waInput, "", { unconfigured: "Nicht konfiguriert" });

        assert.strictEqual(waInput.dataset.hasKey, "false");
        assert.strictEqual(waDeleteBtn.style.display, "none");
        assert.strictEqual(waDeleteBtn.disabled, true);
        assert.strictEqual(waDeleteBtn.attributes["aria-hidden"], "true");
    } finally {
        dom.restore();
    }
});

test("Item 59 AK3: First click on delete button opens confirmation prompt without clearing input", () => {
    const dom = createMockDOM(["settings-tmdb-key"]);
    try {
        const input = dom.elements["settings-tmdb-key"];
        const deleteBtn = dom.elements["settings-tmdb-key-delete"];
        const confirmEl = dom.elements["settings-tmdb-key-confirm"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****tmdb_secret", { configured: "Hinterlegt" });

        // First click on delete button (×)
        deleteBtn.click();

        // Must show confirmation prompt
        assert.strictEqual(confirmEl.style.display, "flex");
        // Must hide delete button while confirmation is open
        assert.strictEqual(deleteBtn.style.display, "none");
        // Must NOT change input value yet
        assert.strictEqual(input.value, "****tmdb_secret");
        // Must NOT mark as deleted yet
        assert.notStrictEqual(input.dataset.deleted, "true");
    } finally {
        dom.restore();
    }
});

test("Item 59 AK4: Canceling confirmation prompt restores field to original state", () => {
    const dom = createMockDOM(["settings-telegram-token"]);
    try {
        const input = dom.elements["settings-telegram-token"];
        const deleteBtn = dom.elements["settings-telegram-token-delete"];
        const confirmEl = dom.elements["settings-telegram-token-confirm"];
        const cancelBtn = dom.elements["settings-telegram-token-confirm-no"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****tg_token", { configured: "Hinterlegt" });

        // Step 1: Click delete button
        deleteBtn.click();
        assert.strictEqual(confirmEl.style.display, "flex");

        // Step 2: Click cancel (Abbrechen)
        cancelBtn.click();

        // Confirmation prompt must be hidden
        assert.strictEqual(confirmEl.style.display, "none");
        // Delete button visible again
        assert.strictEqual(deleteBtn.style.display, "");
        // Original value unchanged
        assert.strictEqual(input.value, "****tg_token");
        assert.strictEqual(input.dataset.deleted, "false");

        // Validation gate treats it as unchanged
        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, false);
        assert.strictEqual(res.value, "****tg_token");
    } finally {
        dom.restore();
    }
});

test("Item 59 AK5: Confirming deletion clears input, marks delete flag, and validateMaskedInput reports changed=true with value=''", () => {
    const dom = createMockDOM(["settings-tmdb-key"]);
    try {
        const input = dom.elements["settings-tmdb-key"];
        const deleteBtn = dom.elements["settings-tmdb-key-delete"];
        const confirmEl = dom.elements["settings-tmdb-key-confirm"];
        const confirmYesBtn = dom.elements["settings-tmdb-key-confirm-yes"];
        const badge = dom.elements["settings-tmdb-key-badge"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****tmdb_key", { configured: "Hinterlegt" });

        // Step 1: Click delete button
        deleteBtn.click();
        // Step 2: Click confirm delete (Löschen)
        confirmYesBtn.click();

        // Confirmation prompt closed
        assert.strictEqual(confirmEl.style.display, "none");
        // Delete button hidden
        assert.strictEqual(deleteBtn.style.display, "none");
        // Value cleared
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.deleted, "true");
        assert.strictEqual(badge.textContent, "○");
        assert.strictEqual(badge.attributes["title"], "Wird beim Speichern gelöscht");

        // Validation returns valid=true, changed=true, value=""
        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, true);
        assert.strictEqual(res.value, "");

        // validateAllMaskedFields includes key with empty string payload
        const allRes = validateAllMaskedFields(["settings-tmdb-key"]);
        assert.strictEqual(allRes.valid, true);
        assert.strictEqual(allRes.changedFields["settings-tmdb-key"], "");

        // Blur does NOT restore original value
        input.blur();
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.deleted, "true");
    } finally {
        dom.restore();
    }
});

test("Item 59 AK6: Clear-on-Edit without delete confirmation preserves W1 protection (changed=false)", () => {
    const dom = createMockDOM(["settings-tvdb-key"]);
    try {
        const input = dom.elements["settings-tvdb-key"];
        const badge = dom.elements["settings-tvdb-key-badge"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****tvdb_key", { configured: "Hinterlegt" });

        // User triggers Clear-on-Edit via keypress without using explicit delete button
        input.focus();
        input.dispatch("keydown", { key: "Backspace" });
        assert.strictEqual(input.value, "");
        assert.strictEqual(input.dataset.editing, "true");
        assert.notStrictEqual(input.dataset.deleted, "true");

        // Direct validation before blur: treated as unchanged
        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, false);
        assert.strictEqual(res.value, "****tvdb_key");

        // On blur: restored
        input.blur();
        assert.strictEqual(input.value, "****tvdb_key");
        assert.strictEqual(input.dataset.editing, "false");
    } finally {
        dom.restore();
    }
});

test("Item 59 AK7: Masked value with **** is rejected and marked invalid regardless of delete flow", () => {
    const dom = createMockDOM(["settings-telegram-chat-id"]);
    try {
        const input = dom.elements["settings-telegram-chat-id"];
        const errorEl = dom.elements["settings-telegram-chat-id-error"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****chat_123");

        // User typed masking chars
        input.value = "****invalid";
        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, false);
        assert.strictEqual(res.changed, true);
        assert.ok(res.error && res.error.includes("Maskierungszeichen"));
        assert.ok(errorEl.textContent.includes("Maskierungszeichen"));
    } finally {
        dom.restore();
    }
});

test("Item 59: Escape key resets delete confirmation and restores original value without bypassing focus path", () => {
    // Restrisiko-Hinweis (ADR 5): Node-Mock prueft logische Verdrahtung und Fokus-Weitergabe
    // im DOM-Modell, ersetzt jedoch keinen vollstaendigen Browser-Integrationstest.
    const dom = createMockDOM(["settings-whatsapp-phone"]);
    try {
        const input = dom.elements["settings-whatsapp-phone"];
        const deleteBtn = dom.elements["settings-whatsapp-phone-delete"];
        const confirmEl = dom.elements["settings-whatsapp-phone-confirm"];
        const confirmNoBtn = dom.elements["settings-whatsapp-phone-confirm-no"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****phone_456");

        deleteBtn.click();
        assert.strictEqual(confirmEl.style.display, "flex");
        assert.strictEqual(deleteBtn.style.display, "none");

        // AK3: Focus must be transferred to confirmNoBtn (Abbrechen), NOT left on inputEl
        assert.strictEqual(globalThis.document.activeElement, confirmNoBtn);
        assert.notStrictEqual(globalThis.document.activeElement, input);

        // AK4: Dispatch Escape from the currently focused element (confirmNoBtn, not input)
        globalThis.document.activeElement.dispatch("keydown", { key: "Escape" });
        assert.strictEqual(confirmEl.style.display, "none");
        assert.strictEqual(input.value, "****phone_456");
        assert.strictEqual(input.dataset.deleted, "false");

        // AK5: Focus returned to inputEl after cancellation
        assert.strictEqual(globalThis.document.activeElement, input);
    } finally {
        dom.restore();
    }
});

test("Item 59: Typing a new value after delete confirmation resets delete flag", () => {
    const dom = createMockDOM(["settings-tmdb-key"]);
    try {
        const input = dom.elements["settings-tmdb-key"];
        const deleteBtn = dom.elements["settings-tmdb-key-delete"];
        const confirmYesBtn = dom.elements["settings-tmdb-key-confirm-yes"];
        setupMaskedInput(input);
        setMaskedInputValue(input, "****old_key");

        // Delete key
        deleteBtn.click();
        confirmYesBtn.click();
        assert.strictEqual(input.dataset.deleted, "true");

        // User changes mind and types a new key
        input.value = "my_brand_new_key_789";
        input.dispatch("input");
        assert.strictEqual(input.dataset.deleted, "false");

        const res = validateMaskedInput(input);
        assert.strictEqual(res.valid, true);
        assert.strictEqual(res.changed, true);
        assert.strictEqual(res.value, "my_brand_new_key_789");
    } finally {
        dom.restore();
    }
});

test("Item 59 DOM Structure: All 6 masked-key-field blocks in index.html contain delete button and confirmation dialog", () => {
    const indexHtmlPath = path.resolve(__dirname, "../../gui/static/index.html");
    const indexHtml = fs.readFileSync(indexHtmlPath, "utf8");

    const expectedFieldIds = [
        "settings-tmdb-key",
        "settings-tvdb-key",
        "settings-telegram-token",
        "settings-telegram-chat-id",
        "settings-whatsapp-apikey",
        "settings-whatsapp-phone"
    ];

    for (const fieldId of expectedFieldIds) {
        assert.ok(
            indexHtml.includes(`id="${fieldId}-delete"`),
            `index.html must contain delete button for field ${fieldId}`
        );
        assert.ok(
            indexHtml.includes(`id="${fieldId}-confirm"`),
            `index.html must contain confirmation container for field ${fieldId}`
        );
        assert.ok(
            indexHtml.includes(`id="${fieldId}-confirm-yes"`),
            `index.html must contain confirmation Yes button for field ${fieldId}`
        );
        assert.ok(
            indexHtml.includes(`id="${fieldId}-confirm-no"`),
            `index.html must contain confirmation No button for field ${fieldId}`
        );
    }
});
