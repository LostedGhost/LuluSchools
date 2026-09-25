import { api } from "./client";
import type { BilletEvenementOut, EvenementOut } from "../types/api";

export function listerEvenements(etablissementId: string) {
  return api.get<EvenementOut[]>(`/etablissements/${etablissementId}/evenements`);
}

export function obtenirEvenement(evenementId: string) {
  return api.get<EvenementOut>(`/evenements/${evenementId}`);
}

export function creerEvenement(
  etablissementId: string,
  data: { titre: string; description: string; lieu: string; date_heure: string; capacite_max: number; prix_billet: number },
) {
  return api.post<EvenementOut>(`/etablissements/${etablissementId}/evenements`, data);
}

export function designerParrain(evenementId: string, utilisateurId: string) {
  return api.post<EvenementOut>(`/evenements/${evenementId}/parrain`, { utilisateur_id: utilisateurId });
}

export function annulerEvenement(evenementId: string) {
  return api.post<EvenementOut>(`/evenements/${evenementId}/annuler`);
}

export function acheterBillet(evenementId: string) {
  return api.post<BilletEvenementOut>(`/evenements/${evenementId}/billets`);
}

export function amorcerPaiementBillet(billetId: string, transactionId: string) {
  return api.post<BilletEvenementOut>(`/billets/${billetId}/paiement/amorcer`, { transaction_id: transactionId });
}

export function validerBillet(billetId: string) {
  return api.post<BilletEvenementOut>(`/billets/${billetId}/valider`);
}

export function rembourserBillet(billetId: string) {
  return api.post<BilletEvenementOut>(`/billets/${billetId}/rembourser`);
}

export function mesBillets() {
  return api.get<BilletEvenementOut[]>("/mes-billets");
}
