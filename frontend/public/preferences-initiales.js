// Appliqué avant le premier rendu (script bloquant dans <head>, autorisé par la CSP
// script-src 'self') : thème et réglages d'accessibilité sans flash au chargement.
// Doit rester aligné sur layout/AppLayout.tsx (ls-theme) et
// accessibilite/AccessibiliteContext.tsx (ls-accessibilite).
(function () {
  var racine = document.documentElement;
  try {
    var theme = localStorage.getItem("ls-theme");
    if (!theme) theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    racine.setAttribute("data-theme", theme);
    var p = JSON.parse(localStorage.getItem("ls-accessibilite") || "{}");
    if (p.taille) racine.setAttribute("data-taille", p.taille);
    if (p.contraste) racine.setAttribute("data-contraste", "");
    if (p.espacement) racine.setAttribute("data-espacement", "");
    if (p.animations_reduites) racine.setAttribute("data-animations-reduites", "");
  } catch {
    /* stockage indisponible : réglages par défaut */
  }
})();
