import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { monProfilEleve } from "../api/inscriptions";
import { messageErreur } from "../api/client";
import type { EleveMeOut } from "../types/api";
import { ErrorBanner } from "../components/ui";

interface EleveProfileContextValue {
  profil: EleveMeOut;
}

const EleveProfileContext = createContext<EleveProfileContextValue | null>(null);

export function EleveProfileProvider({ children }: { children: ReactNode }) {
  const [profil, setProfil] = useState<EleveMeOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    monProfilEleve()
      .then((res) => setProfil(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);

  if (erreur) return <ErrorBanner>{erreur}</ErrorBanner>;
  if (!profil) return <div className="p-8 text-center text-slate-500">Chargement du profil...</div>;

  return <EleveProfileContext.Provider value={{ profil }}>{children}</EleveProfileContext.Provider>;
}

export function useEleveProfil(): EleveMeOut {
  const ctx = useContext(EleveProfileContext);
  if (!ctx) throw new Error("useEleveProfil doit etre utilise a l'interieur de EleveProfileProvider");
  return ctx.profil;
}
