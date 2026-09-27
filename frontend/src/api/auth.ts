import { api, storeTokens } from "./client";
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

export function creerCompteEnseignant(payload: InscriptionTuteurPayload) {
  return api.post<TuteurOut>("/auth/enseignants", payload);
}

export function verifierOtpEnseignant(email: string, code: string) {
  return api.post("/auth/enseignants/verify-otp", { email, code });
}

export function connexion(identifiant: string, mot_de_passe: string) {
  return api.post<TokenPair>("/auth/login", { identifiant, mot_de_passe });
}

export async function changerMotDePasse(ancien_mot_de_passe: string, nouveau_mot_de_passe: string) {
  const reponse = await api.post<MeOut & { access_token: string; refresh_token: string }>("/auth/change-password", {
    ancien_mot_de_passe,
    nouveau_mot_de_passe,
  });
  // Le changement ferme toutes les autres sessions : la session courante recoit une paire neuve.
  storeTokens({
    access_token: reponse.data.access_token,
    refresh_token: reponse.data.refresh_token,
    token_type: "bearer",
    doit_changer_mot_de_passe: false,
  });
  return reponse;
}

export function renvoyerCodeOtp(email: string) {
  return api.post<{ message: string }>("/auth/otp/renvoyer", { email });
}

export function demanderReinitialisation(identifiant: string) {
  return api.post<{ message: string }>("/auth/mot-de-passe-oublie", { identifiant });
}

export function reinitialiserMotDePasse(identifiant: string, code: string, nouveau_mot_de_passe: string) {
  return api.post<{ message: string }>("/auth/mot-de-passe-oublie/confirmer", {
    identifiant,
    code,
    nouveau_mot_de_passe,
  });
}

export function monProfil() {
  return api.get<MeOut>("/me");
}
