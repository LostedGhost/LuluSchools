// Audit d'ergonomie automatisé, exécuté dans le navigateur (serveur de dev Vite) :
//   const { auditer } = await import("/scripts/audit_ergonomie.js");
//   await auditer(["/tuteur", "/tuteur/services"], { largeur: 375 });
// Chaque page est chargée dans une iframe de la largeur voulue (les media queries
// s'appliquent donc comme sur un téléphone), avec la session courante (même origine).
// Relevés : débordement horizontal, valeurs techniques brutes, mots sans accents,
// « undefined »/« NaN », erreurs affichées au chargement, erreurs console, contrôles
// sans nom accessible, champs sans étiquette, images sans alternative, cibles tactiles
// trop petites.

const MOTS_SANS_ACCENT = /\b(etablissement|eleve|eleves|deja|etre|reponse|periode|matiere|evenement|donnees|reussi|resultat|annee|cree|echeance|numero|telephone|delai|reference|securite|verifie|genere|role|acces|selectionne|termine|valide|refuse|rejete|creer|modifier le)\b/i;
const VALEUR_BRUTE = /\b[a-z]+(?:_[a-z0-9]+)+\b/;
const TEXTE_CASSE = /\b(undefined|NaN|\[object Object\]|null)\b/;

const attendre = (ms) => new Promise((r) => setTimeout(r, ms));

function visible(el, win) {
  const s = win.getComputedStyle(el);
  if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0;
}

function nomAccessible(el, doc) {
  const aria = el.getAttribute("aria-label") || el.getAttribute("title");
  if (aria && aria.trim()) return aria.trim();
  const lb = el.getAttribute("aria-labelledby");
  if (lb) return lb.split(/\s+/).map((id) => doc.getElementById(id)?.textContent ?? "").join(" ").trim();
  if (el.id) {
    const l = doc.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (l && l.textContent.trim()) return l.textContent.trim();
  }
  const parentLabel = el.closest("label");
  if (parentLabel && parentLabel.textContent.trim()) return parentLabel.textContent.trim();
  if (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)) return (el.getAttribute("placeholder") ? "(placeholder seul)" : "");
  return (el.textContent || "").trim() || (el.querySelector("img[alt]")?.getAttribute("alt") ?? "");
}

function scrollParentHorizontal(el, win) {
  for (let p = el.parentElement; p; p = p.parentElement) {
    const s = win.getComputedStyle(p);
    if (["auto", "scroll", "hidden", "clip"].includes(s.overflowX)) return true;
  }
  return false;
}

function decrire(el) {
  const t = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 50);
  return `${el.tagName.toLowerCase()}${el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : ""}${t ? ` « ${t} »` : ""}`;
}

async function auditerPage(chemin, { largeur = 375, hauteur = 812, attente = 2500 } = {}) {
  const iframe = document.createElement("iframe");
  iframe.style.cssText = `position:fixed;left:-${largeur + 50}px;top:0;width:${largeur}px;height:${hauteur}px;border:0;`;
  document.body.appendChild(iframe);
  const erreursConsole = [];
  iframe.src = chemin;
  await new Promise((r) => iframe.addEventListener("load", r, { once: true }));
  const win = iframe.contentWindow;
  const origError = win.console.error.bind(win.console);
  win.console.error = (...a) => { erreursConsole.push(a.map(String).join(" ").slice(0, 200)); origError(...a); };
  win.addEventListener("error", (e) => erreursConsole.push(String(e.message).slice(0, 200)));
  await attendre(attente);
  const doc = iframe.contentDocument;
  const constats = [];
  const ajouter = (type, detail) => constats.push({ type, detail });

  if (win.location.pathname !== chemin.split("?")[0]) ajouter("redirection", win.location.pathname);

  // Débordement horizontal
  if (doc.documentElement.scrollWidth > largeur + 1) {
    const fautifs = [...doc.body.querySelectorAll("*")].filter((el) => {
      const r = el.getBoundingClientRect();
      return r.right > largeur + 1 && r.width > 0 && visible(el, win) && !scrollParentHorizontal(el, win);
    });
    const racines = fautifs.filter((el) => !fautifs.includes(el.parentElement)).slice(0, 4);
    ajouter("debordement", `${doc.documentElement.scrollWidth}px : ` + racines.map(decrire).join(" | "));
  }

  // Textes visibles
  const marcheur = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT);
  const vus = new Set();
  for (let n = marcheur.nextNode(); n; n = marcheur.nextNode()) {
    const t = n.textContent.trim();
    if (!t || !n.parentElement || !visible(n.parentElement, win)) continue;
    if (n.parentElement.closest("code, pre, script, style, .monospace, [data-technique]")) continue;
    const brut = t.match(VALEUR_BRUTE);
    if (brut && !/@|\.(com|bj|example)|https?:/.test(t) && !vus.has("b" + brut[0])) { vus.add("b" + brut[0]); ajouter("valeur-brute", `${brut[0]} dans « ${t.slice(0, 80)} »`); }
    const acc = t.match(MOTS_SANS_ACCENT);
    if (acc && !vus.has("a" + acc[0])) { vus.add("a" + acc[0]); ajouter("accent", `« ${acc[0]} » dans « ${t.slice(0, 80)} »`); }
    const casse = t.match(TEXTE_CASSE);
    if (casse && !vus.has("c" + t)) { vus.add("c" + t); ajouter("texte-casse", `« ${t.slice(0, 80)} »`); }
  }

  // Erreurs affichées
  doc.querySelectorAll('[role="alert"]').forEach((el) => {
    if (visible(el, win) && el.textContent.trim()) ajouter("erreur-affichee", el.textContent.trim().slice(0, 150));
  });

  // Contrôles
  const petits = [];
  doc.querySelectorAll("button, a[href], [role=button]").forEach((el) => {
    if (!visible(el, win)) return;
    if (!nomAccessible(el, doc)) ajouter("sans-nom", decrire(el) + " " + el.outerHTML.slice(0, 120));
    const r = el.getBoundingClientRect();
    if ((r.width < 32 || r.height < 32) && !el.closest("p, li, td, label, .prose, footer") && (el.textContent || "").trim().length < 30) petits.push(decrire(el));
  });
  if (petits.length) ajouter("cible-petite", `${petits.length} : ` + petits.slice(0, 5).join(" | "));
  doc.querySelectorAll("input:not([type=hidden]), select, textarea").forEach((el) => {
    if (!visible(el, win)) return;
    const nom = nomAccessible(el, doc);
    if (!nom || nom === "(placeholder seul)") ajouter("champ-sans-etiquette", `${el.tagName.toLowerCase()}[type=${el.type}] ${nom}`);
  });
  doc.querySelectorAll("img").forEach((el) => {
    if (visible(el, win) && !el.hasAttribute("alt")) ajouter("image-sans-alt", el.src.slice(-60));
  });
  erreursConsole.forEach((e) => ajouter("console", e));

  iframe.remove();
  return constats;
}

export async function auditer(chemins, options = {}) {
  const resultats = {};
  for (const c of chemins) {
    try {
      resultats[c] = await auditerPage(c, options);
    } catch (e) {
      resultats[c] = [{ type: "echec-audit", detail: String(e) }];
    }
  }
  return resultats;
}

/** Connexion d'un compte de test (seed local) : stocke les jetons comme l'application. */
export async function connexion(identifiant, motDePasse) {
  const r = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifiant, mot_de_passe: motDePasse }),
  });
  const d = await r.json();
  if (!r.ok) throw new Error(JSON.stringify(d));
  localStorage.setItem("lulu_access_token", d.access_token);
  localStorage.setItem("lulu_refresh_token", d.refresh_token);
}

/** Résumé lisible : { page: ["type: détail", ...] } pour les seules pages avec constats. */
export function resumer(resultats) {
  const c = {};
  for (const [k, v] of Object.entries(resultats)) if (v.length) c[k] = v.map((x) => `${x.type}: ${x.detail.slice(0, 160)}`);
  return c;
}
