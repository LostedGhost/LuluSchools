import { api } from "./client";
import type {
  AnnonceMarketplaceDetailOut,
  AnnonceMarketplaceOut,
  AnnoncesMarketplacePage,
  CategorieAnnonce,
  ContestationMarketplaceOut,
  EtatArticle,
  SignalementAnnonceOut,
  StatutAnnonce,
  TransactionMarketplaceOut,
} from "../types/api";

export interface FiltresAnnonces {
  categorie?: CategorieAnnonce;
  etat?: EtatArticle;
  prix_min?: number;
  prix_max?: number;
  statut?: StatutAnnonce;
  page?: number;
  page_size?: number;
}

export function listerAnnonces(etablissementId: string, filtres: FiltresAnnonces = {}) {
  return api.get<AnnoncesMarketplacePage>(`/etablissements/${etablissementId}/marketplace/annonces`, {
    params: filtres,
  });
}

export function obtenirAnnonce(annonceId: string) {
  return api.get<AnnonceMarketplaceDetailOut>(`/marketplace/annonces/${annonceId}`);
}

export function publierAnnonce(
  etablissementId: string,
  donnees: { titre: string; description: string; categorie: CategorieAnnonce; etat: EtatArticle; prix: number },
  photos: File[],
) {
  const formData = new FormData();
  formData.append("titre", donnees.titre);
  formData.append("description", donnees.description);
  formData.append("categorie", donnees.categorie);
  formData.append("etat", donnees.etat);
  formData.append("prix", String(donnees.prix));
  for (const photo of photos) formData.append("photos", photo);
  return api.post<AnnonceMarketplaceDetailOut>(
    `/etablissements/${etablissementId}/marketplace/annonces`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
}

export function retirerMaAnnonce(annonceId: string) {
  return api.delete(`/marketplace/annonces/${annonceId}`);
}

export function signalerAnnonce(annonceId: string) {
  return api.post<SignalementAnnonceOut>(`/marketplace/annonces/${annonceId}/signaler`);
}

export function mesAnnonces() {
  return api.get<AnnonceMarketplaceOut[]>("/mes-annonces-marketplace");
}

export function reserverAnnonce(annonceId: string) {
  return api.post<TransactionMarketplaceOut>(`/marketplace/annonces/${annonceId}/reserver`);
}

export function amorcerPaiementTransaction(transactionId: string, transactionKkiapayId: string) {
  return api.post<TransactionMarketplaceOut>(`/marketplace/transactions/${transactionId}/paiement/amorcer`, {
    transaction_id: transactionKkiapayId,
  });
}

export function annulerTransaction(transactionId: string) {
  return api.post<TransactionMarketplaceOut>(`/marketplace/transactions/${transactionId}/annuler`);
}

export function declarerRemise(transactionId: string) {
  return api.post<TransactionMarketplaceOut>(`/marketplace/transactions/${transactionId}/declarer-remise`);
}

export function confirmerReception(transactionId: string) {
  return api.post<TransactionMarketplaceOut>(`/marketplace/transactions/${transactionId}/confirmer`);
}

export function contesterTransaction(transactionId: string, motif: string) {
  return api.post<ContestationMarketplaceOut>(`/marketplace/transactions/${transactionId}/contester`, { motif });
}

export function mesTransactions() {
  return api.get<TransactionMarketplaceOut[]>("/mes-transactions-marketplace");
}

// --- Vue admin d'établissement (A+) ---

export function signalementsMarketplaceEnAttente(etablissementId: string) {
  return api.get<SignalementAnnonceOut[]>(`/etablissements/${etablissementId}/marketplace/signalements`);
}

export function traiterSignalementAnnonce(signalementId: string, decision: string) {
  return api.post<SignalementAnnonceOut>(`/marketplace/signalements/${signalementId}/traiter`, { decision });
}

export function retirerAnnonceModeration(annonceId: string, motif: string) {
  return api.post<AnnonceMarketplaceOut>(`/marketplace/annonces/${annonceId}/retirer`, { motif });
}

export function deciderContestationMarketplace(
  contestationId: string,
  decision: "acceptee" | "rejetee",
  decisionMotif?: string,
) {
  return api.post<ContestationMarketplaceOut>(`/marketplace/contestations/${contestationId}/decision`, {
    decision,
    decision_motif: decisionMotif,
  });
}

export function reverserVendeur(transactionId: string, referencePaiement: string) {
  return api.post<TransactionMarketplaceOut>(`/marketplace/transactions/${transactionId}/reverser-vendeur`, {
    reference_paiement: referencePaiement,
  });
}
