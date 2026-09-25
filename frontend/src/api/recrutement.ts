import { api } from "./client";
import type { CandidatureOut, ContestationOut, ContratOut, LienFichierOut, PosteOut } from "../types/api";

export function listerPostes(etablissementId: string) {
  return api.get<PosteOut[]>(`/etablissements/${etablissementId}/postes`);
}

export function candidaturesDuPoste(posteId: string) {
  return api.get<CandidatureOut[]>(`/postes/${posteId}/candidatures`);
}

export function obtenirPoste(posteId: string) {
  return api.get<PosteOut>(`/postes/${posteId}`);
}

export function postuler(posteId: string, types: string[], fichiers: File[], casierJudiciaire: File) {
  const formData = new FormData();
  for (const type of types) formData.append("types", type);
  for (const fichier of fichiers) formData.append("fichiers", fichier);
  formData.append("casier_judiciaire", casierJudiciaire);
  return api.post<CandidatureOut>(`/postes/${posteId}/candidatures`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function mesCandidatures() {
  return api.get<CandidatureOut[]>("/mes-candidatures");
}

export function obtenirCandidature(candidatureId: string) {
  return api.get<CandidatureOut>(`/candidatures/${candidatureId}`);
}

export function contesterCandidature(candidatureId: string, motif: string) {
  return api.post<ContestationOut>(`/candidatures/${candidatureId}/contestation`, { motif });
}

export function mesContrats() {
  return api.get<ContratOut[]>("/mes-contrats");
}

export function signerContrat(contratId: string, signatureImage: Blob) {
  const formData = new FormData();
  formData.append("signature_image", signatureImage, "signature.png");
  return api.post<ContratOut>(`/contrats/${contratId}/signer`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

// --- Vues admin d'etablissement (A+) ---

export function creerPoste(etablissementId: string, titre: string, criteres: { type_document: string; coefficient: number; seuil_minimal: number }[]) {
  return api.post<PosteOut>(`/etablissements/${etablissementId}/postes`, { titre, criteres });
}

export function candidaturesEnAttenteRevision() {
  return api.get<CandidatureOut[]>("/candidatures/en-attente-revision");
}

export function noterDocumentManuellement(documentId: string, note: number) {
  return api.post<CandidatureOut>(`/documents-candidature/${documentId}/noter-manuellement`, { note });
}

export function contestationsEnAttente(etablissementId: string) {
  return api.get<ContestationOut[]>(`/etablissements/${etablissementId}/contestations-en-attente`);
}

export function deciderContestation(contestationId: string, decision: "acceptee" | "rejetee", motifDecision?: string) {
  return api.post<ContestationOut>(`/contestations/${contestationId}/decision`, {
    decision,
    motif_decision: motifDecision,
  });
}

export function creerContrat(candidatureId: string, syllabus: string, dateFin: string) {
  return api.post<ContratOut>(`/candidatures/${candidatureId}/contrat`, { syllabus, date_fin: dateFin });
}

export function obtenirLienDocumentCandidature(documentId: string) {
  return api.get<LienFichierOut>(`/documents-candidature/${documentId}/lien`);
}

export function obtenirLienSignatureContrat(contratId: string) {
  return api.get<LienFichierOut>(`/contrats/${contratId}/lien-signature`);
}
