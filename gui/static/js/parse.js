/**
 * Filename and episode parsing helper functions.
 */

/**
 * Cleans a filename to produce a title for manual searching.
 * 
 * @param {string} filename - The filename to clean.
 * @returns {string} The cleaned title.
 */
export function cleanFilenameForManualTitle(filename) {
    if (!filename) return "";
    let name = filename.substring(0, filename.lastIndexOf('.')) || filename;
    name = name.replace(/s\d+e\d+/gi, "");
    name = name.replace(/\b\d+x\d+\b/gi, "");
    name = name.replace(/\b(ep|episode|folge|f|e|ep\.)\s*\d+\b/gi, "");
    name = name.replace(/[._\-]/g, " ");
    name = name.replace(/\s+/g, " ").trim();
    return name;
}

/**
 * Guesses the episode number from a filename.
 * 
 * @param {string} filename - The filename to inspect.
 * @returns {number|null} The guessed episode number, or null.
 */
export function guessEpisodeNumber(filename) {
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

/**
 * Guesses the season and episode pattern from a filename.
 * 
 * @param {string} filename - The filename to inspect.
 * @returns {string|null} The SxxExx representation, or null.
 */
export function guessSeasonAndEpisode(filename) {
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
