import { api } from "./client";

export type StatutReferentiel = "valide" | "proposition_en_attente" | "remplace";

export interface ReferentielOut {
  id: string;
  niveau: string;
  matiere: string;
  coefficient: number;
  statut: StatutReferentiel;
  propose_pour_id: string | null;
}

export function listerReferentiels() {
  return api.get<ReferentielOut[]>("/referentiels-coefficients");
}

export function creerReferentiel(niveau: string, matiere: string, coefficient: number) {
  return api.post<ReferentielOut>("/referentiels-coefficients", { niveau, matiere, coefficient });
}

export function proposerReferentiel(referentielId: string, coefficient: number) {
  return api.post<ReferentielOut>(`/referentiels-coefficients/${referentielId}/proposition`, { coefficient });
}

export function validerReferentiel(referentielId: string) {
  return api.post<ReferentielOut>(`/referentiels-coefficients/${referentielId}/valider`);
}
