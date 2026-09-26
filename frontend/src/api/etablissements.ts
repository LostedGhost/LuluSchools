import { api } from "./client";
import type { AffectationEnseignantOut, ClasseOut, EtablissementOut } from "../types/api";

export function listerEtablissements() {
  return api.get<EtablissementOut[]>("/etablissements");
}

export function listerClasses(etablissementId: string) {
  return api.get<ClasseOut[]>(`/etablissements/${etablissementId}/classes`);
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

export function mesClassesAffectees() {
  return api.get<ClasseOut[]>("/mes-classes-affectees");
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
  capacite: number;
  politique_depassement: "ordre_arrivee" | "notes_concours" | "tirage_sort";
}

export function creerClasse(etablissementId: string, payload: ClassePayload) {
  return api.post<ClasseOut>(`/etablissements/${etablissementId}/classes`, payload);
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
