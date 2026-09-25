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
