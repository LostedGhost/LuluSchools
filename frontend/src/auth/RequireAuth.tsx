import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { Role } from "../types/api";

export function RequireAuth({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { utilisateur, chargement } = useAuth();
  const location = useLocation();

  if (chargement) {
    return <div className="p-8 text-center text-slate-500">Chargement...</div>;
  }

  if (!utilisateur) {
    return <Navigate to="/connexion" state={{ from: location }} replace />;
  }

  if (utilisateur.mot_de_passe_temporaire && location.pathname !== "/changer-mot-de-passe") {
    return <Navigate to="/changer-mot-de-passe" replace />;
  }

  if (roles && !roles.includes(utilisateur.role)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
