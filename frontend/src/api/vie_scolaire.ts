import { api } from "./client";
import type { EntreeVieScolaireOut, NatureEntreeVieScolaire } from "../types/api";

export interface EntreeVieScolairePayload {
  nature: NatureEntreeVieScolaire;
  matiere?: string | null;
  description: string;
  date_survenue?: string | null;
}

export function creerEntreeVieScolaire(classeId: string, eleveId: string, payload: EntreeVieScolairePayload) {
  return api.post<EntreeVieScolaireOut>(`/classes/${classeId}/eleves/${eleveId}/vie-scolaire`, payload);
}

export function listerVieScolaireEleve(classeId: string, eleveId: string) {
  return api.get<EntreeVieScolaireOut[]>(`/classes/${classeId}/eleves/${eleveId}/vie-scolaire`);
}

export function listerVieScolaireDeLaClasse(classeId: string) {
  return api.get<EntreeVieScolaireOut[]>(`/classes/${classeId}/vie-scolaire`);
}
