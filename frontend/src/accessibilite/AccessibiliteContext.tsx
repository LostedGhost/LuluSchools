import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  enregistrerPreferencesAccessibilite,
  PREFERENCES_PAR_DEFAUT,
  type PreferencesAccessibilite,
} from "../api/accessibilite";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.2 — préférences d'accessibilité. Appliquées comme attributs sur <html>
   (data-taille, data-contraste…), que `index.css` traduit en styles : aucune page n'a
   besoin de les connaître. Conservées dans le navigateur (visiteur anonyme) et
   synchronisées sur le compte une fois connecté (téléphone partagé, cybercafé).
   ═══════════════════════════════════════════════════════════════ */

const CLE_LOCALE = "ls-accessibilite";

function lirePreferencesLocales(): PreferencesAccessibilite {
  try {
    const brut = localStorage.getItem(CLE_LOCALE);
    if (brut) return { ...PREFERENCES_PAR_DEFAUT, ...(JSON.parse(brut) as Partial<PreferencesAccessibilite>) };
  } catch {
    /* stockage indisponible (navigation privée) : réglages par défaut */
  }
  return PREFERENCES_PAR_DEFAUT;
}

function ecrirePreferencesLocales(preferences: PreferencesAccessibilite) {
  try {
    localStorage.setItem(CLE_LOCALE, JSON.stringify(preferences));
  } catch {
    /* sans stockage, les réglages valent pour la session en cours seulement */
  }
}

interface ConnexionReseau extends EventTarget {
  saveData?: boolean;
  effectiveType?: string;
}

function connexionReseau(): ConnexionReseau | null {
  return (navigator as Navigator & { connection?: ConnexionReseau }).connection ?? null;
}

/** Vrai si le navigateur signale l'économie de données ou un réseau 2G/3G. */
function reseauLentDetecte(): boolean {
  const connexion = connexionReseau();
  if (!connexion) return false;
  return !!connexion.saveData || ["slow-2g", "2g", "3g"].includes(connexion.effectiveType ?? "");
}

function useReseauLent(): boolean {
  const [lent, setLent] = useState(reseauLentDetecte);
  useEffect(() => {
    const connexion = connexionReseau();
    if (!connexion) return undefined;
    const surChangement = () => setLent(reseauLentDetecte());
    connexion.addEventListener("change", surChangement);
    return () => connexion.removeEventListener("change", surChangement);
  }, []);
  return lent;
}

interface AccessibiliteValeur {
  preferences: PreferencesAccessibilite;
  modifier: (partiel: Partial<PreferencesAccessibilite>) => void;
  reinitialiser: () => void;
  /** Mode « données réduites » effectif (choisi, ou détecté en mode automatique). */
  donneesReduites: boolean;
  reseauLent: boolean;
}

const AccessibiliteCtx = createContext<AccessibiliteValeur>({
  preferences: PREFERENCES_PAR_DEFAUT,
  modifier: () => {},
  reinitialiser: () => {},
  donneesReduites: false,
  reseauLent: false,
});

function estParDefaut(preferences: PreferencesAccessibilite): boolean {
  return (Object.keys(PREFERENCES_PAR_DEFAUT) as (keyof PreferencesAccessibilite)[]).every(
    (cle) => preferences[cle] === PREFERENCES_PAR_DEFAUT[cle],
  );
}

export function AccessibiliteProvider({ children }: { children: ReactNode }) {
  const { utilisateur } = useAuth();
  const [preferences, setPreferences] = useState(lirePreferencesLocales);
  const reseauLent = useReseauLent();
  const donneesReduites = preferences.donnees === "reduit" || (preferences.donnees === "auto" && reseauLent);
  const minuterie = useRef<number | undefined>(undefined);
  const utilisateurSynchronise = useRef<string | null>(null);

  // À la connexion : les réglages du compte l'emportent ; un compte encore vierge reprend
  // ceux choisis avant de se connecter (ex. texte agrandi sur la page de connexion).
  useEffect(() => {
    if (!utilisateur) {
      utilisateurSynchronise.current = null;
      return;
    }
    if (utilisateurSynchronise.current === utilisateur.id) return;
    utilisateurSynchronise.current = utilisateur.id;
    const duCompte = utilisateur.preferences_accessibilite;
    if (duCompte) {
      const fusion = { ...PREFERENCES_PAR_DEFAUT, ...duCompte };
      setPreferences(fusion);
      ecrirePreferencesLocales(fusion);
    } else {
      const locales = lirePreferencesLocales();
      if (!estParDefaut(locales)) enregistrerPreferencesAccessibilite(locales).catch(() => {});
    }
  }, [utilisateur]);

  useEffect(() => {
    const racine = document.documentElement;
    racine.dataset.taille = preferences.taille;
    racine.toggleAttribute("data-contraste", preferences.contraste);
    racine.toggleAttribute("data-espacement", preferences.espacement);
    racine.toggleAttribute("data-animations-reduites", preferences.animations_reduites);
    racine.toggleAttribute("data-donnees-reduites", donneesReduites);
  }, [preferences, donneesReduites]);

  const appliquer = useCallback(
    (suivantes: PreferencesAccessibilite) => {
      setPreferences(suivantes);
      ecrirePreferencesLocales(suivantes);
      if (!utilisateur) return;
      // Regroupe les clics rapprochés (ex. A+ puis A++) en un seul enregistrement.
      window.clearTimeout(minuterie.current);
      minuterie.current = window.setTimeout(() => {
        enregistrerPreferencesAccessibilite(suivantes).catch(() => {});
      }, 800);
    },
    [utilisateur],
  );

  const modifier = useCallback(
    (partiel: Partial<PreferencesAccessibilite>) => appliquer({ ...preferences, ...partiel }),
    [appliquer, preferences],
  );
  const reinitialiser = useCallback(() => appliquer(PREFERENCES_PAR_DEFAUT), [appliquer]);

  return (
    <AccessibiliteCtx.Provider value={{ preferences, modifier, reinitialiser, donneesReduites, reseauLent }}>
      {children}
    </AccessibiliteCtx.Provider>
  );
}

export function useAccessibilite() {
  return useContext(AccessibiliteCtx);
}

/** Raccourci pour les composants lourds (3D, images, médias) : vrai = s'abstenir. */
export function useDonneesReduites(): boolean {
  return useContext(AccessibiliteCtx).donneesReduites;
}
