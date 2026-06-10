export function applyTheme(themeName) {
    if (themeName === "apple-silver") themeName = "apple-black";
    if (!themeName) themeName = "deep-space";
    localStorage.setItem("app_theme", themeName);

    const themes = ["theme-deep-space", "theme-nordic-slate", "theme-amber-warmth", "theme-apple-black", "theme-superfood-light"];

    // Prüfe View-Transition Support für flüssige Farbübergänge
    if (document.startViewTransition) {
        document.startViewTransition(() => {
            themes.forEach(t => document.body.classList.remove(t));
            document.body.classList.add("theme-" + themeName);
        });
    } else {
        themes.forEach(t => document.body.classList.remove(t));
        document.body.classList.add("theme-" + themeName);
    }
}
