import { api } from "./client";
import type { SessionElProfessorFamilleOut } from "../types/api";

export function ouvrirSessionElProfessorFamille(eleveUtilisateurId: string, sujet?: string) {
  return api.post<SessionElProfessorFamilleOut>("/el-professor-famille/sessions", {
    eleve_utilisateur_id: eleveUtilisateurId,
    sujet: sujet ?? null,
  });
}

export function listerMesSessionsElProfessorFamille() {
  return api.get<SessionElProfessorFamilleOut[]>("/el-professor-famille/sessions");
}

export function obtenirSessionElProfessorFamille(sessionId: string) {
  return api.get<SessionElProfessorFamilleOut>(`/el-professor-famille/sessions/${sessionId}`);
}

export function rejoindreSessionElProfessorFamille(sessionId: string) {
  return api.post<SessionElProfessorFamilleOut>(`/el-professor-famille/sessions/${sessionId}/rejoindre`);
}

export function poserQuestionElProfessorFamille(sessionId: string, question: string) {
  return api.post<SessionElProfessorFamilleOut>(`/el-professor-famille/sessions/${sessionId}/messages`, {
    question,
  });
}
