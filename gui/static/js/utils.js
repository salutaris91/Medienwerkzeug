/**
 * General utility functions for the frontend.
 */

/**
 * Cleans search suffixes and bracketed channel tags from a series/movie name.
 * 
 * @param {string} name - The original name to clean.
 * @returns {string} The cleaned name.
 */
export function cleanSeriesName(name) {
    if (!name) return "";
    // Remove search suffixes in parentheses (case-insensitive)
    let cleaned = name.replace(/\s*\((Mediathek\s+(Serie|Film)\s+aus\s+URL|Freie\s+Mediathek-Suche|fernsehserien\.de\s+URL|\d*\s*Videos?\s+via\s+URL)\)/gi, '');
    // Remove trailing channel tag in brackets, e.g., [ARTE], [ARTE.DE], [TMDB_TV], [US]
    let prev;
    do {
        prev = cleaned;
        cleaned = cleaned.replace(/\s*\[[a-zA-Z0-9\._-]+\]\s*$/, '');
    } while (cleaned !== prev);
    // Replace underscores with spaces
    cleaned = cleaned.replace(/_/g, ' ');
    return cleaned.trim();
}
