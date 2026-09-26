import { api } from "./client";
import type { AlerteElProfessorOut, SessionElProfessorEnseignantOut } from "../types/api";

export function ouvrirSessionElProfessorEnseignant(eleveUtilisateurId?: string, sujet?: string) {
  return api.post<SessionElProfessorEnseignantOut>("/el-professor-enseignant/sessions", {
    eleve_utilisateur_id: eleveUtilisateurId ?? null,
    sujet: sujet ?? null,
  });
}

export function listerMesSessionsElProfessorEnseignant() {
  return api.get<SessionElProfessorEnseignantOut[]>("/el-professor-enseignant/sessions");
}

export function obtenirSessionElProfessorEnseignant(sessionId: string) {
  return api.get<SessionElProfessorEnseignantOut>(`/el-professor-enseignant/sessions/${sessionId}`);
}

export function poserQuestionElProfessorEnseignant(sessionId: string, question: string) {
  return api.post<SessionElProfessorEnseignantOut>(`/el-professor-enseignant/sessions/${sessionId}/messages`, {
    question,
  });
}

export function listerAlertesElProfessor(etablissementId: string) {
  return api.get<AlerteElProfessorOut[]>(`/etablissements/${etablissementId}/alertes-el-professor`);
}

export function traiterAlerteElProfessor(alerteId: string) {
  return api.post<AlerteElProfessorOut>(`/alertes-el-professor/${alerteId}/traiter`);
}
