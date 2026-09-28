// Audit d'accessibilité automatisé (Lot 7.1), exécuté dans le navigateur (serveur de dev Vite) :
//   const a = await import("/scripts/audit_accessibilite.js");
//   await a.connexion("tuteur@…", "Password1!");            // facultatif (pages protégées)
//   a.resumer(await a.auditer(["/", "/tuteur"], { largeur: 375 }));
// Chaque page est chargée dans une iframe (même origine, donc même session), puis
// analysée par axe-core (règles WCAG 2.1 A/AA). Critère d'acceptation du lot : aucune
// violation « critical » ni « serious » sur les pages clés.

const attendre = (ms) => new Promise((r) => setTimeout(r, ms));

function chargerAxe(win) {
  if (win.axe) return Promise.resolve();
  return new Promise((resoudre, rejeter) => {
    const script = win.document.createElement("script");
    script.src = "/node_modules/axe-core/axe.min.js";
    script.onload = () => resoudre();
    script.onerror = () => rejeter(new Error("axe-core introuvable (npm install)"));
    win.document.head.appendChild(script);
  });
}

async function auditerPage(chemin, { largeur = 1280, hauteur = 900, attente = 2500, attributs = {} } = {}) {
  const iframe = document.createElement("iframe");
  iframe.style.cssText = `position:fixed;left:-10000px;top:0;width:${largeur}px;height:${hauteur}px;border:0`;
  iframe.src = chemin;
  document.body.appendChild(iframe);
  await new Promise((r) => (iframe.onload = r));
  await attendre(attente);
  const win = iframe.contentWindow;
  // Permet d'auditer aussi les modes « texte très agrandi », « contraste élevé »…
  for (const [nom, valeur] of Object.entries(attributs)) win.document.documentElement.setAttribute(nom, valeur);
  await chargerAxe(win);
  const resultat = await win.axe.run(win.document, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
  });
  iframe.remove();
  return resultat.violations.map((v) => ({
    regle: v.id,
    impact: v.impact,
    aide: v.help,
    cibles: v.nodes.slice(0, 4).map((n) => n.target.join(" ")),
    nombre: v.nodes.length,
  }));
}

export async function auditer(chemins, options = {}) {
  const resultats = {};
  for (const c of chemins) {
    try {
      resultats[c] = await auditerPage(c, options);
    } catch (e) {
      resultats[c] = [{ regle: "echec-audit", impact: "critical", aide: String(e), cibles: [], nombre: 0 }];
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

/** Résumé : { page: ["impact regle (n) : aide → cibles"] }, pages sans violation omises. */
export function resumer(resultats, impacts = ["critical", "serious", "moderate", "minor"]) {
  const c = {};
  for (const [page, violations] of Object.entries(resultats)) {
    const retenues = violations.filter((v) => impacts.includes(v.impact));
    if (retenues.length) c[page] = retenues.map((v) => `${v.impact} ${v.regle} (${v.nombre}) : ${v.aide} → ${v.cibles.join(" | ")}`);
  }
  return c;
}
