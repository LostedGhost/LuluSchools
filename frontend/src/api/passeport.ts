import { api } from "./client";
import type { PasseportExportOut, PasseportOut } from "../types/api";

export function obtenirMonPasseport() {
  return api.get<PasseportOut>("/eleves/me/passeport");
}

export function exporterMonPasseport() {
  return api.post<PasseportExportOut>("/eleves/me/passeport/export-pdf");
}

export function obtenirPasseportDeMonEnfant(eleveUtilisateurId: string) {
  return api.get<PasseportOut>(`/mes-enfants/${eleveUtilisateurId}/passeport`);
}

export function exporterPasseportDeMonEnfant(eleveUtilisateurId: string) {
  return api.post<PasseportExportOut>(`/mes-enfants/${eleveUtilisateurId}/passeport/export-pdf`);
}
