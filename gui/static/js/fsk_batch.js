export function osBasename(path) {
    if (!path) return "";
    return path.split('/').pop().split('\\').pop();
}

export function formatFskLabel(fskVal) {
    if (fskVal === null || fskVal === undefined) return "Keine";
    const str = String(fskVal).trim();
    return str.startsWith("FSK") ? str : `FSK ${str}`;
}
