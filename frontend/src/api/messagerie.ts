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

export function listerMessages(conversationId: string) {
  return api.get<MessageOut[]>(`/conversations/${conversationId}/messages`);
}

export function envoyerMessage(conversationId: string, contenu: string) {
  return api.post<MessageOut>(`/conversations/${conversationId}/messages`, { contenu });
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
