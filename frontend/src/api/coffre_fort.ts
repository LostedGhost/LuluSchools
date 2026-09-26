import { api } from "./client";
import type {
  AlerteDepassementPlafondOut,
  PlafondFamilialOut,
  ReleveFinancierOut,
  ValidationParentaleOut,
} from "../types/api";

export function obtenirPlafondFamilial(eleveUtilisateurId: string) {
  return api.get<PlafondFamilialOut | null>(`/mes-enfants/${eleveUtilisateurId}/coffre-fort/plafond`);
}

export function definirPlafondFamilial(
  eleveUtilisateurId: string,
  payload: { plafond_hebdomadaire: number | null; seuil_validation: number | null },
) {
  return api.put<PlafondFamilialOut>(`/mes-enfants/${eleveUtilisateurId}/coffre-fort/plafond`, payload);
}

export function obtenirReleveFinancier(eleveUtilisateurId: string, debut?: string, fin?: string) {
  return api.get<ReleveFinancierOut>(`/mes-enfants/${eleveUtilisateurId}/coffre-fort/releve`, {
    params: { debut, fin },
  });
}

export function validationsEnAttente(eleveUtilisateurId: string) {
  return api.get<ValidationParentaleOut[]>(`/mes-enfants/${eleveUtilisateurId}/coffre-fort/validations-en-attente`);
}

export function approuverValidationParentale(validationId: string) {
  return api.post<ValidationParentaleOut>(`/coffre-fort/validations/${validationId}/approuver`);
}

export function refuserValidationParentale(validationId: string, motifRefus?: string) {
  return api.post<ValidationParentaleOut>(`/coffre-fort/validations/${validationId}/refuser`, {
    motif_refus: motifRefus ?? null,
  });
}

export function alertesDepassementPlafond(eleveUtilisateurId: string) {
  return api.get<AlerteDepassementPlafondOut[]>(`/mes-enfants/${eleveUtilisateurId}/coffre-fort/alertes`);
}

export function mesValidationsEnAttente() {
  return api.get<ValidationParentaleOut[]>("/coffre-fort/mes-validations-en-attente");
}
