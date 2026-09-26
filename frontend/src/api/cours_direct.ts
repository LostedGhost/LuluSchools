import { api, getAccessToken } from "./client";
import type {
  CaptureTableauOut,
  ConsentementCameraLiveOut,
  DemandeCraieOut,
  EtatTableauOut,
  MessageSessionLiveOut,
  ParticipationLiveOut,
  PermissionEcritureOut,
  ResumeSessionLiveOut,
  SessionLiveDemarreeOut,
  SessionLiveOut,
  TraitTableauOut,
  TypeTraitTableau,
} from "../types/api";

export function listerSessionsLive(classeId: string) {
  return api.get<SessionLiveOut[]>(`/classes/${classeId}/sessions-live`);
}

export function planifierSessionLive(classeId: string, dateHeure: string) {
  return api.post<SessionLiveOut>(`/classes/${classeId}/sessions-live`, { date_heure: dateHeure });
}

export function demarrerSessionLive(sessionId: string) {
  return api.post<SessionLiveDemarreeOut>(`/sessions-live/${sessionId}/demarrer`);
}

export function terminerSessionLive(sessionId: string) {
  return api.post<SessionLiveOut>(`/sessions-live/${sessionId}/terminer`);
}

export function donnerConsentementCameraLive(eleveUtilisateurId: string) {
  return api.post<ConsentementCameraLiveOut>(`/eleves/${eleveUtilisateurId}/consentement-camera-live`);
}

export function obtenirResumeSessionLive(sessionId: string) {
  return api.get<ResumeSessionLiveOut>(`/sessions-live/${sessionId}/resume`);
}

export function rejoindreSessionLive(sessionId: string) {
  return api.post<ParticipationLiveOut>(`/sessions-live/${sessionId}/rejoindre`);
}

/* --- UC-25 : tableau collaboratif --- */

export function obtenirEtatTableau(sessionId: string) {
  return api.get<EtatTableauOut>(`/sessions-live/${sessionId}/tableau`);
}

export function ajouterPanneauTableau(sessionId: string) {
  return api.post(`/sessions-live/${sessionId}/tableau/panneaux`);
}

export function ajouterTraitTableau(
  sessionId: string,
  panneauId: string,
  type: TypeTraitTableau,
  donnees: Record<string, unknown>,
) {
  return api.post<TraitTableauOut>(`/sessions-live/${sessionId}/tableau/panneaux/${panneauId}/traits`, {
    type,
    donnees,
  });
}

export function effacerPanneauTableau(sessionId: string, panneauId: string) {
  return api.post<TraitTableauOut>(`/sessions-live/${sessionId}/tableau/panneaux/${panneauId}/effacer`);
}

export function demanderLaCraie(sessionId: string) {
  return api.post<DemandeCraieOut>(`/sessions-live/${sessionId}/demande-craie`);
}

export function listerDemandesCraie(sessionId: string) {
  return api.get<DemandeCraieOut[]>(`/sessions-live/${sessionId}/demandes-craie`);
}

export function accorderDemandeCraie(sessionId: string, demandeId: string) {
  return api.post<DemandeCraieOut>(`/sessions-live/${sessionId}/demandes-craie/${demandeId}/accorder`);
}

export function refuserDemandeCraie(sessionId: string, demandeId: string) {
  return api.post<DemandeCraieOut>(`/sessions-live/${sessionId}/demandes-craie/${demandeId}/refuser`);
}

export function preterLaCraie(sessionId: string, eleveUtilisateurId: string) {
  return api.post<PermissionEcritureOut>(`/sessions-live/${sessionId}/permissions-ecriture`, {
    eleve_utilisateur_id: eleveUtilisateurId,
  });
}

export function revoquerLaCraie(sessionId: string, eleveUtilisateurId: string) {
  return api.delete(`/sessions-live/${sessionId}/permissions-ecriture/${eleveUtilisateurId}`);
}

export function listerCapturesTableau(sessionId: string) {
  return api.get<CaptureTableauOut[]>(`/sessions-live/${sessionId}/captures`);
}

/* --- UC-25.5 : chat de session (salle sociale pre-cours incluse) --- */

export function envoyerMessageSessionLive(sessionId: string, contenu: string) {
  return api.post<MessageSessionLiveOut>(`/sessions-live/${sessionId}/messages`, { contenu });
}

export function listerMessagesSessionLive(sessionId: string) {
  return api.get<MessageSessionLiveOut[]>(`/sessions-live/${sessionId}/messages`);
}

/* --- Canal temps reel (tableau/permissions/chat + relais de signalisation WebRTC) --- */

export function ouvrirCanalTempsReelSessionLive(sessionId: string): WebSocket {
  const token = getAccessToken() ?? "";
  const protocole = window.location.protocol === "https:" ? "wss:" : "ws:";
  return new WebSocket(`${protocole}//${window.location.host}/api/v1/ws/sessions-live/${sessionId}?token=${encodeURIComponent(token)}`);
}
