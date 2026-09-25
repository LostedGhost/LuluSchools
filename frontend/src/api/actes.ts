import { api } from "./client";
import type { DemandeActeOut, TypeActeOut } from "../types/api";

export function listerTypesActes(etablissementId: string) {
  return api.get<TypeActeOut[]>(`/etablissements/${etablissementId}/types-actes`);
}

export function mesDemandesActes() {
  return api.get<DemandeActeOut[]>("/mes-demandes-actes");
}

export interface DemandeActePayload {
  type_acte_id?: string;
  est_reclamation?: boolean;
  reference_evaluation?: string;
  motif?: string;
  eleve_utilisateur_id?: string;
}

export function soumettreDemandeActe(payload: DemandeActePayload) {
  return api.post<DemandeActeOut>("/demandes-actes", payload);
}

export function amorcerPaiement(demandeId: string, transactionId: string) {
  return api.post<DemandeActeOut>(`/demandes-actes/${demandeId}/paiement/amorcer`, {
    transaction_id: transactionId,
  });
}

export function obtenirDemandeActe(demandeId: string) {
  return api.get<DemandeActeOut>(`/demandes-actes/${demandeId}`);
}

export function demandesActesEtablissement(etablissementId: string) {
  return api.get<DemandeActeOut[]>(`/etablissements/${etablissementId}/demandes-actes`);
}

export function traiterDemandeActe(demandeId: string, decision: "acceptee" | "rejetee", motifRejet?: string) {
  return api.post<DemandeActeOut>(`/demandes-actes/${demandeId}/traiter`, {
    decision,
    motif_rejet: motifRejet,
  });
}

export interface TypeActePayload {
  nom: string;
  prix: number;
  pieces_requises: string;
  condition_eligibilite?: string;
}

export function creerTypeActe(etablissementId: string, payload: TypeActePayload) {
  return api.post<TypeActeOut>(`/etablissements/${etablissementId}/types-actes`, payload);
}
