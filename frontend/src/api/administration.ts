import { api } from "./client";
import type { EtablissementOut } from "../types/api";

/* Boîte « À traiter » de l'A+ et de l'A++ : files d'attente de tous les modules, actions
   groupées et automatisations (voir backend app/modules/administration/a_traiter.py). */

export interface ElementATraiter {
  id: string;
  libelle: string;
  detail: string | null;
  ia: string | null;
  ia_niveau: string | null;
  groupe: string | null;
  montant: number | null;
}

export interface SectionATraiter {
  cle: string;
  titre: string;
  description: string;
  urgent: boolean;
  nombre: number;
  elements: ElementATraiter[];
}

export interface PropositionAffectation {
  classe_id: string;
  classe: string;
  enseignant_utilisateur_id: string;
  enseignant: string;
  matiere: string | null;
  principal: boolean;
  motif: string;
}

export interface ResultatLot {
  validees: string[];
  refusees: { id: string; code: string; message: string }[];
}

export const aTraiter = () => api.get<SectionATraiter[]>("/administration/a-traiter");

export const validerInscriptionsEnLot = (ids: string[]) =>
  api.post<ResultatLot>("/inscriptions/valider-en-lot", { inscription_ids: ids });

export const rejeterInscriptionsEnLot = (ids: string[], motif: string) =>
  api.post<ResultatLot>("/inscriptions/rejeter-en-lot", { inscription_ids: ids, motif });

export const modifierParametresEtablissement = (etablissementId: string, admissionAutomatique: boolean) =>
  api.patch<EtablissementOut>(`/etablissements/${etablissementId}/parametres`, { admission_automatique: admissionAutomatique });

export const recruterEnUnClic = (candidatureId: string) => api.post(`/candidatures/${candidatureId}/recruter`);

export const reconduireContratsEnLot = (etablissementId: string) =>
  api.post<unknown[]>(`/etablissements/${etablissementId}/contrats/reconduire-en-lot`);

export const propositionAffectations = (etablissementId: string) =>
  api.get<PropositionAffectation[]>(`/etablissements/${etablissementId}/affectations/proposition`);

export const appliquerAffectations = (etablissementId: string, lignes: PropositionAffectation[]) =>
  api.post<{ affectations_creees: number }>(`/etablissements/${etablissementId}/affectations/appliquer`, { lignes });

export const traiterSignalementsMessagesEnLot = (ids: string[], decision?: string) =>
  api.post<{ traites: string[]; ignores: string[] }>("/signalements/traiter-en-lot", { signalement_ids: ids, decision });

export const traiterSignalementsAnnoncesEnLot = (ids: string[], decision?: string) =>
  api.post<{ traites: string[]; ignores: string[] }>("/marketplace/signalements/traiter-en-lot", { signalement_ids: ids, decision });

export const reverserVendeurEnLot = (ids: string[], reference: string) =>
  api.post<{ reverses: string[]; montant_total: number }>("/marketplace/transactions/reverser-en-lot", { ids, reference_paiement: reference });

export const reverserPrestataireEnLot = (ids: string[], reference: string) =>
  api.post<{ reverses: string[]; montant_total: number }>("/missions-micro-job/reverser-en-lot", { ids, reference_paiement: reference });

export const marquerRemboursementsEffectues = (ids: string[]) =>
  api.post<string[]>("/administration/remboursements/effectues", { ids });

export const genererDocumentActe = (demandeId: string) => api.post(`/demandes-actes/${demandeId}/generer-document`);
