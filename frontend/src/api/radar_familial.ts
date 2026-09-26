import { api } from "./client";
import type { RadarFamilialOut } from "../types/api";

export function obtenirRadarFamilial(eleveUtilisateurId: string, debut?: string, fin?: string) {
  return api.get<RadarFamilialOut>(`/mes-enfants/${eleveUtilisateurId}/radar-familial`, {
    params: { debut, fin },
  });
}
