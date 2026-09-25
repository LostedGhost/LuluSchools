import { api } from "./client";
import type { BulletinOut, DevoirOut, SoumissionOut } from "../types/api";

export function listerDevoirs(classeId: string) {
  return api.get<DevoirOut[]>(`/classes/${classeId}/devoirs`);
}

export function obtenirDevoir(devoirId: string) {
  return api.get<DevoirOut>(`/devoirs/${devoirId}`);
}

export interface ReponsePayload {
  question_id: string;
  texte_reponse: string;
}

export function soumettreDevoir(devoirId: string, reponses: ReponsePayload[]) {
  return api.post<SoumissionOut>(`/devoirs/${devoirId}/soumissions`, { reponses });
}

export function maSoumission(devoirId: string) {
  return api.get<SoumissionOut>(`/devoirs/${devoirId}/ma-soumission`);
}

export function obtenirSoumission(soumissionId: string) {
  return api.get<SoumissionOut>(`/soumissions/${soumissionId}`);
}

export function obtenirBulletin(eleveUtilisateurId: string, classeId: string, periode: string) {
  return api.get<BulletinOut>(`/eleves/${eleveUtilisateurId}/bulletins`, {
    params: { classe_id: classeId, periode },
  });
}

export interface QuestionDevoirPayload {
  enonce: string;
  bareme_reponse: string;
  points_max: number;
}

export function creerDevoir(
  classeId: string,
  titre: string,
  matiere: string,
  dateLimite: string,
  bareme: "rigide" | "flexible",
  questions: QuestionDevoirPayload[],
) {
  return api.post<DevoirOut>(`/classes/${classeId}/devoirs`, {
    titre,
    matiere,
    date_limite: dateLimite,
    bareme,
    questions,
  });
}

export function soumissionsARevoir(devoirId: string) {
  return api.get<SoumissionOut[]>(`/devoirs/${devoirId}/soumissions-a-revoir`);
}

export interface CorrectionManuellePayload {
  question_id: string;
  points_obtenus: number;
}

export function corrigerSoumission(soumissionId: string, reponses: CorrectionManuellePayload[]) {
  return api.post<SoumissionOut>(`/soumissions/${soumissionId}/corriger`, { reponses });
}
