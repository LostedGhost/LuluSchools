import { api } from "./client";

/** Réglages de la barre d'accessibilité (miroir de `accessibilite/schemas.py`). */
export interface PreferencesAccessibilite {
  taille: "normal" | "grand" | "tres_grand";
  contraste: boolean;
  espacement: boolean;
  animations_reduites: boolean;
  /** "auto" : réduit si le navigateur signale l'économie de données ou un réseau lent. */
  donnees: "auto" | "reduit" | "normal";
  /** Lot 7.4 : accueil par pictogrammes lus à voix haute. */
  mode_ecoute: boolean;
  langue_audio: "fr" | "fon" | "yo";
}

export const PREFERENCES_PAR_DEFAUT: PreferencesAccessibilite = {
  taille: "normal",
  contraste: false,
  espacement: false,
  animations_reduites: false,
  donnees: "auto",
  mode_ecoute: false,
  langue_audio: "fr",
};

export function enregistrerPreferencesAccessibilite(preferences: PreferencesAccessibilite) {
  return api.put<PreferencesAccessibilite>("/me/preferences-accessibilite", preferences);
}

/** Repli de la lecture à voix haute quand le navigateur n'a pas de voix française (WAV). */
export async function syntheseVocaleServeur(texte: string): Promise<Blob> {
  const { data } = await api.post<Blob>("/accessibilite/synthese-vocale", { texte }, { responseType: "blob" });
  return data;
}
