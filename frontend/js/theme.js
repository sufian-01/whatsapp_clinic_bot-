/**
 * Theme Manager Module: Handles dark/light theme persistence and toggling.
 */

export const ThemeManager = {
  init() {
    const theme = this.getTheme();
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("crm_theme", theme);
  },
  getTheme() {
    return localStorage.getItem("crm_theme") || "light";
  },
  setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("crm_theme", theme);
    const btn = document.getElementById("header-theme-toggle");
    if (btn) btn.textContent = theme === "dark" ? "☀️" : "🌙";
  },
  toggle() {
    const current = this.getTheme();
    const next = current === "dark" ? "light" : "dark";
    this.setTheme(next);
    return next;
  },
};

