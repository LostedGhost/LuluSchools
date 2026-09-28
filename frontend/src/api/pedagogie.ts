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
  transcription?: string,
  sousTitres?: File,
) {
  const formData = new FormData();
  formData.append("titre", titre);
  formData.append("chapitre", chapitre);
  formData.append("format", format);
  if (contenuTexte) formData.append("contenu_texte", contenuTexte);
  if (fichier) formData.append("fichier", fichier);
  if (transcription) formData.append("transcription", transcription);
  if (sousTitres) formData.append("sous_titres", sousTitres);
  return api.post<CoursOut>(`/classes/${classeId}/cours`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

// --- Lot 7.3 : transcriptions et sous-titres (handicap auditif) ---

export function enregistrerTranscription(coursId: string, transcription: string, sousTitresVtt?: string | null) {
  return api.put<CoursOut>(`/cours/${coursId}/transcription`, {
    transcription,
    sous_titres_vtt: sousTitresVtt ?? null,
  });
}

/** Proposition de l'IA : jamais enregistrée tant que l'enseignant ne l'a pas validée. */
export function proposerMiseEnFormeTranscription(coursId: string, transcription: string) {
  return api.post<{ transcription: string }>(`/cours/${coursId}/transcription/mise-en-forme`, { transcription });
}

/** Texte WebVTT : lu en JavaScript (une balise <track> ne transmet pas le jeton d'accès). */
export async function obtenirSousTitres(coursId: string): Promise<string> {
  const { data } = await api.get<string>(`/cours/${coursId}/sous-titres`, { responseType: "text" });
  return data;
}

export function creerQuiz(coursId: string, seuilReussite: number, nombreQuestions: number) {
  return api.post<QuizOut>(`/cours/${coursId}/quiz`, {
    seuil_reussite: seuilReussite,
    nombre_questions: nombreQuestions,
  });
}

// --- Assistant El Professor (UC-14) ---
