import { api } from "./client";
import type { AlerteElProfessorOut, SessionElProfessorTuteurOut } from "../types/api";

export function ouvrirSessionElProfessorTuteur(eleveUtilisateurId: string, sujet?: string) {
  return api.post<SessionElProfessorTuteurOut>("/el-professor-tuteur/sessions", {
    eleve_utilisateur_id: eleveUtilisateurId,
    sujet: sujet ?? null,
  });
}

export function listerMesSessionsElProfessorTuteur() {
  return api.get<SessionElProfessorTuteurOut[]>("/el-professor-tuteur/sessions");
}

export function poserQuestionElProfessorTuteur(sessionId: string, question: string) {
  return api.post<SessionElProfessorTuteurOut>(`/el-professor-tuteur/sessions/${sessionId}/messages`, {
    question,
  });
}

export function alertesElProfessorDeMonEnfant(eleveUtilisateurId: string) {
  return api.get<AlerteElProfessorOut[]>(`/mes-enfants/${eleveUtilisateurId}/alertes-el-professor`);
}
