import { api } from "./client";
import type { BulletinOut, DevoirOut, DevoirProprietaireOut, LienFichierOut, NatureEvaluation, SoumissionOut } from "../types/api";

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

export function obtenirSoumissionDeMonEnfant(devoirId: string, eleveUtilisateurId: string) {
  return api.get<SoumissionOut>(`/devoirs/${devoirId}/soumission-de/${eleveUtilisateurId}`);
}

export interface PeriodeOut {
  code: string;
  libelle: string;
  debut: string;
  fin: string;
  courante: boolean;
}

/** Trimestres (primaire, secondaire) ou semestres (université) de l'année de la classe. */
export function periodesDeLaClasse(classeId: string) {
  return api.get<PeriodeOut[]>(`/classes/${classeId}/periodes`);
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
  nature: NatureEvaluation = "sommative",
) {
  return api.post<DevoirOut>(`/classes/${classeId}/devoirs`, {
    titre,
    matiere,
    date_limite: dateLimite,
    bareme,
    nature,
    questions,
  });
}

export function televerserSujetDocument(devoirId: string, fichier: File) {
  const formData = new FormData();
  formData.append("fichier", fichier);
  return api.post<DevoirOut>(`/devoirs/${devoirId}/sujet-document`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function obtenirLienSujetDocument(devoirId: string) {
  return api.get<LienFichierOut>(`/devoirs/${devoirId}/sujet-document/lien`);
}

export function televerserBaremeDocument(devoirId: string, fichier: File) {
  const formData = new FormData();
  formData.append("fichier", fichier);
  return api.post<DevoirProprietaireOut>(`/devoirs/${devoirId}/bareme-document`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function obtenirLienBaremeDocument(devoirId: string) {
  return api.get<LienFichierOut>(`/devoirs/${devoirId}/bareme-document/lien`);
}

export function soumettreDevoirParCopieImage(devoirId: string, fichier: File) {
  const formData = new FormData();
  formData.append("fichier", fichier);
  return api.post<SoumissionOut>(`/devoirs/${devoirId}/soumissions/copie-image`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function corrigerNoteGlobale(soumissionId: string, note: number) {
  return api.post<SoumissionOut>(`/soumissions/${soumissionId}/corriger-note-globale`, { note });
}

export function soumissionsARevoir(devoirId: string) {
  return api.get<SoumissionOut[]>(`/devoirs/${devoirId}/soumissions-a-revoir`);
}

export interface QuestionAvecBareme {
  id: string;
  ordre: number;
  enonce: string;
  bareme_reponse: string;
  points_max: number;
}

export function questionsAvecBareme(devoirId: string) {
  return api.get<QuestionAvecBareme[]>(`/devoirs/${devoirId}/questions-bareme`);
}

export interface CorrectionManuellePayload {
  question_id: string;
  points_obtenus: number;
}

export function corrigerSoumission(soumissionId: string, reponses: CorrectionManuellePayload[]) {
  return api.post<SoumissionOut>(`/soumissions/${soumissionId}/corriger`, { reponses });
}

export interface EvaluationDuBulletin {
  devoir_id: string;
  titre: string;
  date: string;
  note: number | null; // null : copie non rendue après l'échéance (compte 0)
  total: number;
  sur_100: number;
}

export interface MatiereDuBulletin {
  matiere: string;
  coefficient: number;
  moyenne: number;
  evaluations: EvaluationDuBulletin[];
}

/** Bulletin et détail par matière (chaque évaluation et sa note), comme le bulletin PDF. */
export function obtenirBulletinDetaille(eleveUtilisateurId: string, classeId: string, periode: string) {
  return api.get<{ bulletin: BulletinOut; matieres: MatiereDuBulletin[] }>(`/eleves/${eleveUtilisateurId}/bulletins/detail`, {
    params: { classe_id: classeId, periode },
  });
}

/** Bulletin officiel d'une période, en PDF (blob : l'appel porte le jeton d'authentification). */
export function telechargerBulletinPdf(eleveUtilisateurId: string, classeId: string, periode: string) {
  return api.get<Blob>(`/eleves/${eleveUtilisateurId}/bulletins/pdf`, {
    params: { classe_id: classeId, periode },
    responseType: "blob",
  });
}

/** Décision du conseil de classe (fige le bulletin ; « admis » déclenche le certificat de réussite). */
export function validerPassage(bulletinId: string, decision: string) {
  return api.post<BulletinOut>(`/bulletins/${bulletinId}/valider-passage`, { decision });
}
