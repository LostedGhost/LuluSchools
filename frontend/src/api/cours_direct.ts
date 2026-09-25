import { api } from "./client";
import type { ConsentementCameraLiveOut, ParticipationLiveOut, SessionLiveDemarreeOut, SessionLiveOut } from "../types/api";

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

export function rejoindreSessionLive(sessionId: string) {
  return api.post<ParticipationLiveOut>(`/sessions-live/${sessionId}/rejoindre`);
}
