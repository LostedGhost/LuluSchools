import { api } from "./client";

/** Lot 7.8 : EFTP et insertion (miroir de `insertion/router.py`). */
export interface OffreStage {
  id: string;
  etablissement_id: string;
  entreprise: string;
  intitule: string;
  description: string;
  lieu: string;
  filiere: string | null;
  duree_semaines: number;
  date_limite: string;
  contact: string;
  active: boolean;
  created_at: string;
  ma_candidature?: "envoyee" | "retenue" | "non_retenue" | null;
  nombre_candidatures?: number | null;
}

export interface OffreStagePayload {
  entreprise: string;
  intitule: string;
  description: string;
  lieu: string;
  filiere?: string | null;
  duree_semaines: number;
  date_limite: string;
  contact: string;
}

export interface CandidatureStage {
  id: string;
  offre_id: string;
  eleve_utilisateur_id: string;
  eleve_nom: string;
  eleve_prenom: string;
  message: string;
  statut: "envoyee" | "retenue" | "non_retenue";
  created_at: string;
}

export interface CompetenceMetier {
  id: string;
  intitule: string;
  niveau: "initie" | "confirme" | "maitrise";
  valide_par_id: string;
  created_at: string;
}

export interface EligibiliteBourse {
  eligible: boolean;
  moyenne_sur_20: number | null;
  seuil_sur_20: number;
  matieres: string[];
  explication: string;
}

export const offresPourMoi = () => api.get<OffreStage[]>("/stages");
export const candidaterStage = (offreId: string, message: string) =>
  api.post<CandidatureStage>(`/stages/${offreId}/candidatures`, { message });

export const offresEtablissement = (etablissementId: string) =>
  api.get<OffreStage[]>(`/etablissements/${etablissementId}/stages`);
export const publierOffreStage = (etablissementId: string, payload: OffreStagePayload) =>
  api.post<OffreStage>(`/etablissements/${etablissementId}/stages`, payload);
export const cloturerOffreStage = (offreId: string) => api.post<OffreStage>(`/stages/${offreId}/cloturer`);
export const candidaturesOffre = (offreId: string) => api.get<CandidatureStage[]>(`/stages/${offreId}/candidatures`);
export const deciderCandidatureStage = (candidatureId: string, statut: "retenue" | "non_retenue") =>
  api.post<CandidatureStage>(`/candidatures-stage/${candidatureId}/decision`, { statut });

export const competencesMetier = (eleveUtilisateurId: string) =>
  api.get<CompetenceMetier[]>(`/eleves/${eleveUtilisateurId}/competences-metier`);
export const validerCompetenceMetier = (eleveUtilisateurId: string, intitule: string, niveau: CompetenceMetier["niveau"]) =>
  api.post<CompetenceMetier>(`/eleves/${eleveUtilisateurId}/competences-metier`, { intitule, niveau });

export const eligibiliteBourseScientifique = (eleveUtilisateurId?: string) =>
  api.get<EligibiliteBourse>("/bourses/eligibilite-scientifique", {
    params: eleveUtilisateurId ? { eleve_utilisateur_id: eleveUtilisateurId } : {},
  });
