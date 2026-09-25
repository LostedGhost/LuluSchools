import { api } from "./client";
import type { ClasseOut, EtablissementOut } from "../types/api";

export function listerEtablissements() {
  return api.get<EtablissementOut[]>("/etablissements");
}

export function listerClasses(etablissementId: string) {
  return api.get<ClasseOut[]>(`/etablissements/${etablissementId}/classes`);
}

export interface EtablissementPayload {
  nom: string;
  type: "EP" | "ES" | "UP";
  statut: "public" | "prive";
  admin: { nom: string; prenom: string; email: string };
}

export function creerEtablissement(payload: EtablissementPayload) {
  return api.post<EtablissementOut>("/etablissements", payload);
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
