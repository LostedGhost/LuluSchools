import { api } from "./client";
import type { LigneTransportOut, TicketCantineOut, TicketTransportOut, TypeRepasCantineOut } from "../types/api";

// --- Transport (UC-11) ---

export function listerLignesTransport(etablissementId: string) {
  return api.get<LigneTransportOut[]>(`/etablissements/${etablissementId}/lignes-transport`);
}

export function creerLigneTransport(etablissementId: string, nom: string, prix: number, capacite: number) {
  return api.post<LigneTransportOut>(`/etablissements/${etablissementId}/lignes-transport`, {
    nom,
    prix,
    capacite_par_trajet: capacite,
  });
}

export function acheterTicketTransport(ligneId: string, dateTrajet: string, eleveUtilisateurId?: string) {
  return api.post<TicketTransportOut>(`/lignes-transport/${ligneId}/tickets`, {
    date_trajet: dateTrajet,
    eleve_utilisateur_id: eleveUtilisateurId,
  });
}

export function amorcerPaiementTicketTransport(ticketId: string, transactionId: string) {
  return api.post<TicketTransportOut>(`/tickets-transport/${ticketId}/paiement/amorcer`, {
    transaction_id: transactionId,
  });
}

export function validerTicketTransport(ticketId: string) {
  return api.post<TicketTransportOut>(`/tickets-transport/${ticketId}/valider`);
}

export function rembourserTicketTransport(ticketId: string) {
  return api.post<TicketTransportOut>(`/tickets-transport/${ticketId}/rembourser`);
}

export function mesTicketsTransport() {
  return api.get<TicketTransportOut[]>("/mes-tickets-transport");
}

// --- Cantine (UC-12) ---

export function listerTypesRepasCantine(etablissementId: string) {
  return api.get<TypeRepasCantineOut[]>(`/etablissements/${etablissementId}/types-repas-cantine`);
}

export function creerTypeRepasCantine(etablissementId: string, nom: string, prix: number, capacite: number) {
  return api.post<TypeRepasCantineOut>(`/etablissements/${etablissementId}/types-repas-cantine`, {
    nom,
    prix,
    capacite_par_jour: capacite,
  });
}

export function acheterTicketCantine(typeRepasId: string, dateService: string, eleveUtilisateurId?: string) {
  return api.post<TicketCantineOut>(`/types-repas-cantine/${typeRepasId}/tickets`, {
    date_service: dateService,
    eleve_utilisateur_id: eleveUtilisateurId,
  });
}

export function amorcerPaiementTicketCantine(ticketId: string, transactionId: string) {
  return api.post<TicketCantineOut>(`/tickets-cantine/${ticketId}/paiement/amorcer`, {
    transaction_id: transactionId,
  });
}

export function validerTicketCantine(ticketId: string) {
  return api.post<TicketCantineOut>(`/tickets-cantine/${ticketId}/valider`);
}

export function rembourserTicketCantine(ticketId: string) {
  return api.post<TicketCantineOut>(`/tickets-cantine/${ticketId}/rembourser`);
}

export function mesTicketsCantine() {
  return api.get<TicketCantineOut[]>("/mes-tickets-cantine");
}
