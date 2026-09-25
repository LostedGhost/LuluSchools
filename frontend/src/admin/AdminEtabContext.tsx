import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { monEtablissement } from "../api/etablissements";
import { messageErreur } from "../api/client";
import type { EtablissementOut } from "../types/api";
import { ErrorBanner } from "../components/ui";

const AdminEtabContext = createContext<EtablissementOut | null>(null);

export function AdminEtabProvider({ children }: { children: ReactNode }) {
  const [etablissement, setEtablissement] = useState<EtablissementOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    monEtablissement()
      .then((res) => setEtablissement(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);

  if (erreur) return <ErrorBanner>{erreur}</ErrorBanner>;
  if (!etablissement) return <div className="p-8 text-center text-slate-500">Chargement...</div>;

  return <AdminEtabContext.Provider value={etablissement}>{children}</AdminEtabContext.Provider>;
}

export function useAdminEtab(): EtablissementOut {
  const ctx = useContext(AdminEtabContext);
  if (!ctx) throw new Error("useAdminEtab doit etre utilise a l'interieur de AdminEtabProvider");
  return ctx;
}
