import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
}

function navPourRole(role: string | undefined): NavItem[] {
  if (role === "tuteur") {
    return [
      { to: "/tuteur", label: "Mes enfants" },
      { to: "/tuteur/nouvelle-inscription", label: "Nouvelle inscription" },
    ];
  }
  if (role === "eleve") {
    return [
      { to: "/eleve", label: "Tableau de bord" },
      { to: "/eleve/cours", label: "Cours" },
      { to: "/eleve/devoirs", label: "Devoirs" },
      { to: "/eleve/bulletin", label: "Bulletin" },
      { to: "/eleve/actes", label: "Actes academiques" },
    ];
  }
  return [];
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { utilisateur, seDeconnecter } = useAuth();
  const items = navPourRole(utilisateur?.role);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-indigo-700">LuluSchools</span>
          </div>
          {utilisateur && (
            <div className="flex items-center gap-4 text-sm text-slate-600">
              <span>
                {utilisateur.prenom} {utilisateur.nom}
              </span>
              <button
                type="button"
                onClick={seDeconnecter}
                className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100"
              >
                Deconnexion
              </button>
            </div>
          )}
        </div>
        {items.length > 0 && (
          <nav className="mx-auto flex max-w-5xl gap-1 px-4 pb-2">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-indigo-100 text-indigo-700" : "text-slate-600 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}
