import { api } from "./client";

/** Lot 7.7 : alphabétisation et éducation des adultes (miroir de `alphabetisation/router.py`). */
export interface ClasseAlphabetisation {
  classe_id: string;
  niveau: string;
  centre_id: string;
  centre_nom: string;
  departement: string | null;
  commune: string | null;
  places_restantes: number;
  inscrit: boolean;
}

export interface ApprenantAdulte {
  utilisateur_id: string;
  nom: string;
  prenom: string;
  telephone: string | null;
  classe_id: string;
  niveau: string;
  inscrit_le: string;
}

export interface EssaiQuizOut {
  score: number;
  reussie: boolean;
  bonnes_reponses: number[];
}

export function classesAlphabetisation() {
  return api.get<ClasseAlphabetisation[]>("/alphabetisation/classes");
}

export function inscrireAlphabetisation(classeId: string) {
  return api.post<ClasseAlphabetisation>("/alphabetisation/inscriptions", { classe_id: classeId });
}

export function apprenantsAdultes(etablissementId: string) {
  return api.get<ApprenantAdulte[]>(`/etablissements/${etablissementId}/apprenants-adultes`);
}

/** Entraînement noté mais jamais enregistré (quiz oral des adultes). */
export function essayerQuiz(quizId: string, reponses: number[]) {
  return api.post<EssaiQuizOut>(`/quiz/${quizId}/essai`, { reponses });
}
