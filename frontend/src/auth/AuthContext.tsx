import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { isAxiosError } from "axios";
import { connexion, monProfil } from "../api/auth";
import { clearTokens, getAccessToken, storeTokens } from "../api/client";
import type { MeOut } from "../types/api";

interface AuthContextValue {
  utilisateur: MeOut | null;
  chargement: boolean;
  seConnecter: (identifiant: string, motDePasse: string) => Promise<MeOut>;
  seDeconnecter: () => void;
  rafraichirUtilisateur: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<MeOut | null>(null);
  const [chargement, setChargement] = useState(true);

  const rafraichirUtilisateur = useCallback(async () => {
    if (!getAccessToken()) {
      setUtilisateur(null);
      return;
    }
    try {
      const { data } = await monProfil();
      setUtilisateur(data);
    } catch (erreur) {
      // Hors ligne (pas de réponse du serveur) : on garde la session, l'application reste
      // utilisable sur les contenus déjà en cache (Lot 7.5). Seul un refus réel déconnecte.
      if (isAxiosError(erreur) && !erreur.response) return;
      clearTokens();
      setUtilisateur(null);
    }
  }, []);

  useEffect(() => {
    rafraichirUtilisateur().finally(() => setChargement(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const seConnecter = useCallback(async (identifiant: string, motDePasse: string) => {
    const { data: tokens } = await connexion(identifiant, motDePasse);
    storeTokens(tokens);
    const { data: profil } = await monProfil();
    setUtilisateur(profil);
    return profil;
  }, []);

  const seDeconnecter = useCallback(() => {
    clearTokens();
    setUtilisateur(null);
    // Téléphone partagé : les cours et bulletins gardés pour le hors ligne partent aussi.
    navigator.serviceWorker?.controller?.postMessage({ type: "vider-donnees" });
  }, []);

  return (
    <AuthContext.Provider value={{ utilisateur, chargement, seConnecter, seDeconnecter, rafraichirUtilisateur }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit etre utilise a l'interieur de AuthProvider");
  return ctx;
}
