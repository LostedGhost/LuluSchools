import { api } from "./client";
import type { CoursOut, QuizOut, TentativeQuizOut } from "../types/api";

export function listerCours(classeId: string) {
  return api.get<CoursOut[]>(`/classes/${classeId}/cours`);
}

export function listerQuiz(coursId: string) {
  return api.get<QuizOut[]>(`/cours/${coursId}/quiz`);
}

export function obtenirQuiz(quizId: string) {
  return api.get<QuizOut>(`/quiz/${quizId}`);
}

export function tenterQuiz(quizId: string, reponses: number[]) {
  return api.post<TentativeQuizOut>(`/quiz/${quizId}/tentatives`, { reponses });
}

export function mesTentatives(quizId: string) {
  return api.get<TentativeQuizOut[]>(`/quiz/${quizId}/mes-tentatives`);
}
