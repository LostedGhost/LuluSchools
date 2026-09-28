import { api } from "./client";

/** Lot 7.4 : phrases du mode Écoute (miroir de `ecoute/router.py`). */
export interface TuileEcoute {
  cle: "bulletin" | "presences" | "devoirs" | "paiements" | "accord" | string;
  titre: string;
  phrase: string;
  lien: string;
  alerte: boolean;
  consentement_inscription_id?: string | null;
}

export interface EnfantEcoute {
  eleve_utilisateur_id: string | null;
  prenom: string;
  tuiles: TuileEcoute[];
}

export interface EcouteTuteurOut {
  accueil: string;
  enfants: EnfantEcoute[];
}

export function obtenirEcouteTuteur() {
  return api.get<EcouteTuteurOut>("/ecoute/tuteur");
}
