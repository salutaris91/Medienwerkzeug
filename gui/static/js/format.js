/**
 * Formatting utilities for the frontend.
 */

/**
 * Formats a number of bytes into a human-readable string (e.g. KB, MB, GB, TB).
 * 
 * @param {number} bytes - The number of bytes to format.
 * @returns {string} The formatted byte string.
 */
export function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = 2;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}
