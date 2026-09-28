import { api } from "./client";
import type { ConversationOut, MessageOut, SignalementOut } from "../types/api";

export function mesConversations() {
  return api.get<ConversationOut[]>("/conversations");
}

export function creerConversationDm(participantId: string) {
  return api.post<ConversationOut>("/conversations", { participant_id: participantId });
}

export function conversationClasse(classeId: string) {
  return api.get<ConversationOut>(`/classes/${classeId}/conversation`);
}

export const TAILLE_PAGE_MESSAGES = 100;

/** Du plus récent au plus ancien ; `avant` = id du plus ancien message déjà affiché. */
export function listerMessages(conversationId: string, avant?: string) {
  return api.get<MessageOut[]>(`/conversations/${conversationId}/messages`, {
    params: { limite: TAILLE_PAGE_MESSAGES, ...(avant ? { avant } : {}) },
  });
}

export function envoyerMessage(conversationId: string, contenu: string) {
  return api.post<MessageOut>(`/conversations/${conversationId}/messages`, { contenu });
}

/** Lot 7.4 : message vocal (parler au lieu d'écrire). */
export function envoyerMessageVocal(conversationId: string, audio: Blob, dureeSecondes: number) {
  const formData = new FormData();
  const extension = audio.type.includes("ogg") ? "ogg" : audio.type.includes("mp4") ? "m4a" : "webm";
  formData.append("audio", audio, `message-vocal.${extension}`);
  formData.append("duree_secondes", String(dureeSecondes));
  return api.post<MessageOut>(`/conversations/${conversationId}/messages-vocaux`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export function masquerMessage(messageId: string) {
  return api.delete(`/messages/${messageId}`);
}

export function signalerMessage(messageId: string) {
  return api.post<SignalementOut>(`/messages/${messageId}/signaler`);
}

export function signalementsEnAttente(etablissementId: string) {
  return api.get<SignalementOut[]>(`/etablissements/${etablissementId}/signalements`);
}

export function traiterSignalement(signalementId: string, decision: string) {
  return api.post<SignalementOut>(`/signalements/${signalementId}/traiter`, { decision });
}
