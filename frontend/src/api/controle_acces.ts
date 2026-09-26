import { api } from "./client";
import type { DesignationControleurOut, ServiceControle, UtilisateurDesignableOut } from "../types/api";

export function rechercherUtilisateursDesignables(etablissementId: string, q?: string) {
  return api.get<UtilisateurDesignableOut[]>(`/etablissements/${etablissementId}/utilisateurs-designables`, {
    params: q ? { q } : undefined,
  });
}

export function listerControleurs(etablissementId: string) {
  return api.get<DesignationControleurOut[]>(`/etablissements/${etablissementId}/controleurs`);
}

export function designerControleur(
  etablissementId: string,
  utilisateurId: string,
  service: ServiceControle,
  evenementId?: string,
) {
  return api.post<DesignationControleurOut>(`/etablissements/${etablissementId}/controleurs`, {
    utilisateur_id: utilisateurId,
    service,
    evenement_id: evenementId,
  });
}

export function revoquerControleur(designationId: string) {
  return api.delete(`/controleurs/${designationId}`);
}
