import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function DashboardRedirect() {
  const { utilisateur } = useAuth();
  if (!utilisateur) return <Navigate to="/connexion" replace />;
  if (utilisateur.role === "tuteur") return <Navigate to="/tuteur" replace />;
  if (utilisateur.role === "eleve") return <Navigate to="/eleve" replace />;
  if (utilisateur.role === "enseignant") return <Navigate to="/enseignant" replace />;
  if (utilisateur.role === "admin_etablissement") return <Navigate to="/admin-etablissement" replace />;
  if (utilisateur.role === "admin_ministeriel") return <Navigate to="/admin-ministeriel" replace />;
  return (
    <div className="p-8 text-center text-slate-600">
      Aucun tableau de bord n'est encore disponible pour votre role ({utilisateur.role}).
    </div>
  );
}
