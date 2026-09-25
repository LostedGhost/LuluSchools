import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

const DASHBOARD_PAR_ROLE: Record<string, string> = {
  tuteur: "/tuteur",
  eleve: "/eleve",
  enseignant: "/enseignant",
  admin_etablissement: "/admin-etablissement",
  admin_ministeriel: "/admin-ministeriel",
};

/**
 * Empêche l'accès aux pages publiques d'authentification (connexion, inscription)
 * quand un compte est déjà connecté — redirige directement vers son tableau de
 * bord (ou vers le changement de mot de passe si un mot de passe temporaire
 * est encore actif, cohérent avec RequireAuth).
 */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { utilisateur, chargement } = useAuth();

  if (chargement) {
    return <div className="p-8 text-center text-slate-500">Chargement...</div>;
  }

  if (utilisateur) {
    if (utilisateur.mot_de_passe_temporaire) {
      return <Navigate to="/changer-mot-de-passe" replace />;
    }
    return <Navigate to={DASHBOARD_PAR_ROLE[utilisateur.role] ?? "/"} replace />;
  }

  return <>{children}</>;
}
