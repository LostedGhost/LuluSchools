import { api } from "./client";
import type { MeOut, TokenPair, TuteurOut } from "../types/api";

export interface InscriptionTuteurPayload {
  nom: string;
  prenom: string;
  email: string;
  telephone?: string;
  mot_de_passe: string;
}

export function creerCompteTuteur(payload: InscriptionTuteurPayload) {
  return api.post<TuteurOut>("/auth/tuteurs", payload);
}

export function verifierOtpTuteur(email: string, code: string) {
  return api.post("/auth/tuteurs/verify-otp", { email, code });
}

export function connexion(identifiant: string, mot_de_passe: string) {
  return api.post<TokenPair>("/auth/login", { identifiant, mot_de_passe });
}

export function changerMotDePasse(ancien_mot_de_passe: string, nouveau_mot_de_passe: string) {
  return api.post<MeOut>("/auth/change-password", { ancien_mot_de_passe, nouveau_mot_de_passe });
}

export function monProfil() {
  return api.get<MeOut>("/me");
}
