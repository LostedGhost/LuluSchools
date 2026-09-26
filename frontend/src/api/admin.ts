import { api } from "./client";
import type {
  AdminCoursOut,
  AdminDevoirOut,
  AdminEvenementOut,
  AdminUtilisateurOut,
  JournalAuditOut,
  PageOut,
} from "../types/api";

export interface ListerUtilisateursParams {
  role?: string;
  actif?: boolean;
  q?: string;
  limit?: number;
  offset?: number;
}

export function listerUtilisateursSupervision(params: ListerUtilisateursParams = {}) {
  return api.get<PageOut<AdminUtilisateurOut>>("/admin/utilisateurs", { params });
}

export function suspendreCompte(utilisateurId: string, motif: string) {
  return api.post<AdminUtilisateurOut>(`/admin/utilisateurs/${utilisateurId}/suspendre`, { motif });
}

export function reactiverCompte(utilisateurId: string, motif?: string) {
  return api.post<AdminUtilisateurOut>(`/admin/utilisateurs/${utilisateurId}/reactiver`, { motif });
}

export interface ListerContenuParams {
  etablissement_id?: string;
  enseignant_id?: string;
  masque?: boolean;
  limit?: number;
  offset?: number;
}

export function listerCoursSupervision(params: ListerContenuParams = {}) {
  return api.get<PageOut<AdminCoursOut>>("/admin/cours", { params });
}

export function masquerCours(coursId: string, motif: string) {
  return api.post(`/cours/${coursId}/masquer`, { motif });
}

export function demasquerCours(coursId: string) {
  return api.post(`/cours/${coursId}/demasquer`);
}

export function listerDevoirsSupervision(params: ListerContenuParams = {}) {
  return api.get<PageOut<AdminDevoirOut>>("/admin/devoirs", { params });
}

export function masquerDevoir(devoirId: string, motif: string) {
  return api.post(`/devoirs/${devoirId}/masquer`, { motif });
}

export function demasquerDevoir(devoirId: string) {
  return api.post(`/devoirs/${devoirId}/demasquer`);
}

export interface ListerEvenementsParams {
  etablissement_id?: string;
  statut?: "ouvert" | "annule";
  limit?: number;
  offset?: number;
}

export function listerEvenementsSupervision(params: ListerEvenementsParams = {}) {
  return api.get<PageOut<AdminEvenementOut>>("/admin/evenements", { params });
}

export function annulerEvenement(evenementId: string) {
  return api.post(`/evenements/${evenementId}/annuler`);
}

export function listerJournalAudit(params: { cible_type?: string; limit?: number; offset?: number } = {}) {
  return api.get<PageOut<JournalAuditOut>>("/admin/journal-audit", { params });
}
