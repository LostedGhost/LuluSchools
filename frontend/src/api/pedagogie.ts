import { api } from "./client";
import type { CoursOut, LienFichierOut, QuizOut, TentativeQuizOut } from "../types/api";

export function listerCours(classeId: string) {
  return api.get<CoursOut[]>(`/classes/${classeId}/cours`);
}

export function listerQuiz(coursId: string) {
  return api.get<QuizOut[]>(`/cours/${coursId}/quiz`);
}

export function obtenirQuiz(quizId: string) {
  return api.get<QuizOut>(`/quiz/${quizId}`);
}

export function obtenirLienFichierCours(coursId: string) {
  return api.get<LienFichierOut>(`/cours/${coursId}/lien-fichier`);
}

export function tenterQuiz(quizId: string, reponses: number[]) {
  return api.post<TentativeQuizOut>(`/quiz/${quizId}/tentatives`, { reponses });
}

export function mesTentatives(quizId: string) {
  return api.get<TentativeQuizOut[]>(`/quiz/${quizId}/mes-tentatives`);
}

export function publierCours(
  classeId: string,
  titre: string,
  chapitre: string,
  format: "texte" | "pdf" | "audio" | "video",
  contenuTexte?: string,
  fichier?: File,
) {
  const formData = new FormData();
  formData.append("titre", titre);
  formData.append("chapitre", chapitre);
  formData.append("format", format);
  if (contenuTexte) formData.append("contenu_texte", contenuTexte);
  if (fichier) formData.append("fichier", fichier);
  return api.post<CoursOut>(`/classes/${classeId}/cours`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function creerQuiz(coursId: string, seuilReussite: number, nombreQuestions: number) {
  return api.post<QuizOut>(`/cours/${coursId}/quiz`, {
    seuil_reussite: seuilReussite,
    nombre_questions: nombreQuestions,
  });
}
