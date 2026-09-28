import { api } from "./client";

/** Lot 7.6 : indicateurs de pilotage (miroir de `indicateurs/service.py`). `null` = masqué
    (moins de `seuil_anonymat` élèves) ou non calculable. */
export interface LigneDepartement {
  departement: string;
  etablissements: number;
  eleves: number | null;
  filles: number | null;
  garcons: number | null;
  indice_parite: number | null;
  taux_reussite: number | null;
}

export interface IndicateursOut {
  annee_academique: string;
  perimetre: string;
  seuil_anonymat: number;
  etablissements: { total: number; publics: number; prives: number; par_type: Record<"EP" | "ES" | "UP" | "CA", number>; sans_territoire: number };
  eleves: { total: number; filles: number | null; garcons: number | null; sexe_non_renseigne: number | null; indice_parite: number | null };
  eftp?: { eleves: number | null; part: number | null };
  reussite: { bulletins: number; taux_reussite: number | null; taux_reussite_filles: number | null; taux_reussite_garcons: number | null };
  assiduite: { absences: number; retards: number; absences_par_eleve: number | null };
  enseignants: { sous_contrat: number; eleves_par_enseignant: number | null };
  cantine: { eleves_beneficiaires: number | null; repas: number };
  inclusion: {
    cours_oraux: number;
    cours_oraux_transcrits: number;
    taux_transcription: number | null;
    comptes_mode_ecoute: number;
    comptes_reglages_accessibilite: number;
    messages_vocaux: number;
    apprenants_alphabetisation?: number;
  };
  par_departement?: LigneDepartement[];
}

export interface FiltresIndicateurs {
  annee_academique?: string;
  departement?: string;
}

export function obtenirIndicateurs(filtres: FiltresIndicateurs = {}) {
  return api.get<IndicateursOut>("/admin/indicateurs", { params: filtres });
}

export async function exporterIndicateursCsv(filtres: FiltresIndicateurs = {}): Promise<Blob> {
  const { data } = await api.get<Blob>("/admin/indicateurs.csv", { params: filtres, responseType: "blob" });
  return data;
}
