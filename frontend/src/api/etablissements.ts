import { api } from "./client";
import type {
  AffectationEnseignantOut,
  ClasseOut,
  ConsoleCoursOut,
  ConsoleEleveOut,
  ConsoleEnseignantOut,
  ConsoleNoteOut,
  ConsoleTuteurOut,
  EleveClasseOut,
  EtablissementOut,
  PageOut,
  RentreeOut,
  SalleEnseignantOut,
  VieScolaireOut,
} from "../types/api";

export function listerEtablissements() {
  return api.get<EtablissementOut[]>("/etablissements");
}

export function listerClasses(etablissementId: string, anneeAcademique?: string) {
  return api.get<ClasseOut[]>(`/etablissements/${etablissementId}/classes`, {
    params: anneeAcademique ? { annee_academique: anneeAcademique } : undefined,
  });
}

export function affecterEnseignant(classeId: string, enseignantUtilisateurId: string) {
  return api.post<AffectationEnseignantOut>(`/classes/${classeId}/affectations`, {
    enseignant_utilisateur_id: enseignantUtilisateurId,
  });
}

export function listerAffectationsClasse(classeId: string) {
  return api.get<AffectationEnseignantOut[]>(`/classes/${classeId}/affectations`);
}

export function revoquerAffectation(affectationId: string) {
  return api.delete(`/affectations/${affectationId}`);
}

export function mesClassesAffectees(options: { toutesAnnees?: boolean; anneeAcademique?: string } = {}) {
  return api.get<SalleEnseignantOut[]>("/mes-classes-affectees", {
    params: { toutes_annees: options.toutesAnnees, annee_academique: options.anneeAcademique },
  });
}

export function listerElevesDeLaClasse(classeId: string) {
  return api.get<EleveClasseOut[]>(`/classes/${classeId}/eleves`);
}

export function designerProfesseurPrincipal(classeId: string, enseignantUtilisateurId: string) {
  return api.post<AffectationEnseignantOut>(`/classes/${classeId}/professeur-principal`, {
    enseignant_utilisateur_id: enseignantUtilisateurId,
  });
}

export interface EtablissementPayload {
  nom: string;
  type: "EP" | "ES" | "UP";
  statut: "public" | "prive";
  admin: { nom: string; prenom: string; email: string };
  latitude: number;
  longitude: number;
}

export function creerEtablissement(payload: EtablissementPayload) {
  return api.post<EtablissementOut>("/etablissements", payload);
}

export function mettreAJourLocalisation(etablissementId: string, latitude: number, longitude: number) {
  return api.post<EtablissementOut>(`/etablissements/${etablissementId}/localisation`, { latitude, longitude });
}

export interface ClassePayload {
  niveau: string;
  filiere?: string | null;
  annee_academique?: string;
  capacite: number;
  politique_depassement: "ordre_arrivee" | "notes_concours" | "tirage_sort";
}

export function creerClasse(etablissementId: string, payload: ClassePayload) {
  return api.post<ClasseOut>(`/etablissements/${etablissementId}/classes`, payload);
}

export function reconduireClasses(etablissementId: string, classeIds: string[], nouvelleAnnee: string) {
  return api.post<ClasseOut[]>(`/etablissements/${etablissementId}/classes/reconduire`, {
    classe_ids: classeIds,
    nouvelle_annee: nouvelleAnnee,
  });
}

export function monEtablissement() {
  return api.get<EtablissementOut>("/etablissements/mon-etablissement");
}

export interface EtablissementVitrine {
  id: string;
  nom: string;
  type: "EP" | "ES" | "UP";
  statut: "public" | "prive";
  nb_classes: number;
  nb_postes_ouverts: number;
  latitude: number | null;
  longitude: number | null;
}

export interface PosteVitrine {
  id: string;
  titre: string;
  etablissement_id: string;
  etablissement_nom: string;
  etablissement_type: "EP" | "ES" | "UP";
}

export interface VitrinePublique {
  etablissements: EtablissementVitrine[];
  postes_ouverts: PosteVitrine[];
  totaux: { etablissements: number; classes: number; postes_ouverts: number };
}

export function vitrinePublique() {
  return api.get<VitrinePublique>("/etablissements/vitrine-publique");
}

export interface AnnuairePublique {
  items: EtablissementVitrine[];
  total: number;
  limit: number;
  offset: number;
}

export function annuairePublic(params: { type?: "EP" | "ES" | "UP"; q?: string; limit?: number; offset?: number } = {}) {
  return api.get<AnnuairePublique>("/etablissements/annuaire-public", { params });
}

export interface PhotoPublique {
  id: string;
  url: string;
  ordre: number;
}

export function photosPubliques(etablissementId: string) {
  return api.get<PhotoPublique[]>(`/etablissements/${etablissementId}/photos-publiques`);
}

export interface PhotoOut {
  id: string;
  ordre: number;
}

export function ajouterPhotoEtablissement(etablissementId: string, fichier: File) {
  const formData = new FormData();
  formData.append("fichier", fichier);
  return api.post<PhotoOut>(`/etablissements/${etablissementId}/photos`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function supprimerPhotoEtablissement(etablissementId: string, photoId: string) {
  return api.delete(`/etablissements/${etablissementId}/photos/${photoId}`);
}

export function modifierDescriptionEtablissement(etablissementId: string, description: string | null) {
  return api.patch<EtablissementOut>(`/etablissements/${etablissementId}/description`, { description });
}

export function actionGroupeeEtablissements(ids: string[], action: "suspendre" | "reactiver", motif: string) {
  return api.post<EtablissementOut[]>("/etablissements/action-groupee", { ids, action, motif });
}

// ═══════════════════════════════════════════════════════════════
// Rentrée scolaire (UC-39/40/55/56)
// ═══════════════════════════════════════════════════════════════

export function declarerRentree(etablissementId: string, anneeAcademique: string) {
  return api.post<RentreeOut>(`/etablissements/${etablissementId}/rentrees`, { annee_academique: anneeAcademique });
}

export function listerRentrees(etablissementId: string) {
  return api.get<RentreeOut[]>(`/etablissements/${etablissementId}/rentrees`);
}

export function inviterTuteurs(etablissementId: string, rentreeId: string) {
  return api.post<{ nb_tuteurs_notifies: number }>(
    `/etablissements/${etablissementId}/rentrees/${rentreeId}/inviter-tuteurs`,
  );
}

// ═══════════════════════════════════════════════════════════════
// Vie scolaire (UC-41/42/57)
// ═══════════════════════════════════════════════════════════════

export function consulterVieScolaire(eleveUtilisateurId: string) {
  return api.get<VieScolaireOut>(`/eleves/${eleveUtilisateurId}/vie-scolaire`);
}

// ═══════════════════════════════════════════════════════════════
// Console établissement (UC-45/46/60/61)
// ═══════════════════════════════════════════════════════════════

export interface ConsoleParams {
  classe_id?: string;
  annee_academique?: string;
  limit?: number;
  offset?: number;
}

export function consoleEleves(etablissementId: string, params: ConsoleParams = {}) {
  return api.get<PageOut<ConsoleEleveOut>>(`/etablissements/${etablissementId}/console/eleves`, { params });
}

export function consoleEnseignants(etablissementId: string, params: ConsoleParams = {}) {
  return api.get<PageOut<ConsoleEnseignantOut>>(`/etablissements/${etablissementId}/console/enseignants`, { params });
}

export function consoleTuteurs(etablissementId: string, params: ConsoleParams = {}) {
  return api.get<PageOut<ConsoleTuteurOut>>(`/etablissements/${etablissementId}/console/tuteurs`, { params });
}

export function consoleCours(etablissementId: string, params: ConsoleParams = {}) {
  return api.get<PageOut<ConsoleCoursOut>>(`/etablissements/${etablissementId}/console/cours`, { params });
}

export function consoleNotes(etablissementId: string, params: ConsoleParams & { periode?: string } = {}) {
  return api.get<PageOut<ConsoleNoteOut>>(`/etablissements/${etablissementId}/console/notes`, { params });
}
