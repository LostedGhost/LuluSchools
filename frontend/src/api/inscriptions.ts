import { api } from "./client";
import type { EleveMeOut, InscriptionAvecEleveOut, InscriptionOut, Nationalite } from "../types/api";

export interface InscriptionPayload {
  nom: string;
  prenom: string;
  date_naissance: string;
  classe_id: string;
  nationalite: Nationalite;
  consentement_parental_donne: boolean;
}

export function creerInscription(payload: InscriptionPayload) {
  return api.post<InscriptionOut>("/inscriptions", payload);
}

export function donnerConsentementParental(inscriptionId: string) {
  return api.post<InscriptionOut>(`/inscriptions/${inscriptionId}/consentement-parental`);
}

export function mesInscriptions() {
  return api.get<InscriptionAvecEleveOut[]>("/tuteurs/me/inscriptions");
}

export function monProfilEleve() {
  return api.get<EleveMeOut>("/eleves/me");
}

export function inscriptionsAValider(etablissementId: string) {
  return api.get<InscriptionAvecEleveOut[]>(`/etablissements/${etablissementId}/inscriptions-a-valider`);
}

export function validerInscription(inscriptionId: string) {
  return api.post<InscriptionOut>(`/inscriptions/${inscriptionId}/valider`);
}

export function rejeterInscription(inscriptionId: string, motif: string) {
  return api.post<InscriptionOut>(`/inscriptions/${inscriptionId}/rejeter`, { motif });
}
