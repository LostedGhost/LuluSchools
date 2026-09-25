import { api } from "./client";
import type { ContestationMicroJobOut, MissionMicroJobOut, OffreMicroJobOut } from "../types/api";

export function listerOffres() {
  return api.get<OffreMicroJobOut[]>("/micro-jobs/offres");
}

export function obtenirOffre(offreId: string) {
  return api.get<OffreMicroJobOut>(`/micro-jobs/offres/${offreId}`);
}

export function creerOffre(titre: string, description: string, prix: number) {
  return api.post<OffreMicroJobOut>("/micro-jobs/offres", { titre, description, prix });
}

export function accepterOffre(offreId: string) {
  return api.post<MissionMicroJobOut>(`/micro-jobs/offres/${offreId}/accepter`);
}

export function amorcerPaiementMission(missionId: string, transactionId: string) {
  return api.post<MissionMicroJobOut>(`/missions-micro-job/${missionId}/paiement/amorcer`, {
    transaction_id: transactionId,
  });
}

export function declarerFinMission(missionId: string) {
  return api.post<MissionMicroJobOut>(`/missions-micro-job/${missionId}/declarer-fin`);
}

export function validerMission(missionId: string) {
  return api.post<MissionMicroJobOut>(`/missions-micro-job/${missionId}/valider`);
}

export function contesterMission(missionId: string, motif: string) {
  return api.post<ContestationMicroJobOut>(`/missions-micro-job/${missionId}/contester`, { motif });
}

export function deciderContestationMicroJob(contestationId: string, decision: "acceptee" | "rejetee", decisionMotif?: string) {
  return api.post<ContestationMicroJobOut>(`/contestations-micro-job/${contestationId}/decision`, {
    decision,
    decision_motif: decisionMotif,
  });
}

export function reverserPrestataire(missionId: string, referencePaiement: string) {
  return api.post<MissionMicroJobOut>(`/missions-micro-job/${missionId}/reverser-prestataire`, {
    reference_paiement: referencePaiement,
  });
}

export function mesMissions() {
  return api.get<MissionMicroJobOut[]>("/mes-missions-micro-job");
}
