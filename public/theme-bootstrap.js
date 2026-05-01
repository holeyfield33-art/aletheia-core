try {
  var storedTheme = localStorage.getItem("aletheia-theme");
  var nextTheme = storedTheme;
  if (nextTheme !== "light" && nextTheme !== "dark") {
    nextTheme = matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  }
  document.documentElement.setAttribute("data-theme", nextTheme);
} catch (_error) {
  document.documentElement.setAttribute("data-theme", "dark");
}
