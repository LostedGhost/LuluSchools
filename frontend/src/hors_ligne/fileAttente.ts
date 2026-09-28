import { useSyncExternalStore } from "react";
import { isAxiosError } from "axios";
import { api } from "../api/client";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.5 (UC-80) — file d'attente des envois hors ligne.
   Un envoi qui n'obtient AUCUNE réponse (pas de réseau) est gardé sur l'appareil et
   rejoué au retour du réseau, avec la même clé `X-Cle-Idempotence` : le serveur
   renvoie alors la réponse déjà produite au lieu de refaire l'action (absence,
   message ou copie jamais enregistré deux fois — voir backend app/core/idempotence.py).
   Seuls des envois de texte y passent (devoirs, messages, vie scolaire) : jamais un
   paiement ni un fichier.
   ═══════════════════════════════════════════════════════════════ */

export interface EnvoiEnAttente {
  cle: string;
  url: string;
  corps: unknown;
  libelle: string;
  cree_le: string;
  utilisateur_id: string;
}

export type ResultatEnvoi<T> = { statut: "envoye"; data: T } | { statut: "en_attente" };

const STOCKAGE = "lulu-file-attente";
const abonnes = new Set<() => void>();
let cache: EnvoiEnAttente[] = lire();
let rejeuEnCours = false;

function lire(): EnvoiEnAttente[] {
  try {
    return JSON.parse(localStorage.getItem(STOCKAGE) ?? "[]") as EnvoiEnAttente[];
  } catch {
    return [];
  }
}

function ecrire(file: EnvoiEnAttente[]) {
  cache = file;
  try {
    localStorage.setItem(STOCKAGE, JSON.stringify(file));
  } catch {
    /* stockage plein ou indisponible : la file vit le temps de la session */
  }
  abonnes.forEach((notifier) => notifier());
}

export function useFileAttente(): EnvoiEnAttente[] {
  return useSyncExternalStore(
    (notifier) => {
      abonnes.add(notifier);
      return () => abonnes.delete(notifier);
    },
    () => cache,
  );
}

/** Pas de réponse du tout = réseau absent (une erreur 4xx/5xx, elle, a bien une réponse). */
function sansReseau(erreur: unknown): boolean {
  return isAxiosError(erreur) && !erreur.response;
}

function utilisateurCourant(): string {
  try {
    const jeton = localStorage.getItem("lulu_access_token") ?? "";
    return (JSON.parse(atob(jeton.split(".")[1] ?? "")) as { sub?: string }).sub ?? "";
  } catch {
    return "";
  }
}

/**
 * Envoie tout de suite ; sans réseau, garde l'envoi pour plus tard et renvoie
 * `{ statut: "en_attente" }` (l'écran l'annonce au lieu d'afficher une erreur).
 */
export async function envoyerOuMettreEnAttente<T>(url: string, corps: unknown, libelle: string): Promise<ResultatEnvoi<T>> {
  const cle = crypto.randomUUID();
  try {
    const { data } = await api.post<T>(url, corps, { headers: { "X-Cle-Idempotence": cle } });
    return { statut: "envoye", data };
  } catch (erreur) {
    if (!sansReseau(erreur)) throw erreur;
    ecrire([...cache, { cle, url, corps, libelle, cree_le: new Date().toISOString(), utilisateur_id: utilisateurCourant() }]);
    return { statut: "en_attente" };
  }
}

/** Rejoue la file dans l'ordre ; s'arrête au premier envoi encore sans réseau. */
export async function rejouerFileAttente(): Promise<void> {
  if (rejeuEnCours || cache.length === 0 || !navigator.onLine) return;
  rejeuEnCours = true;
  const moi = utilisateurCourant();
  try {
    for (const envoi of [...cache]) {
      if (envoi.utilisateur_id !== moi) continue; // jamais envoyé au nom d'un autre compte
      try {
        await api.post(envoi.url, envoi.corps, { headers: { "X-Cle-Idempotence": envoi.cle } });
      } catch (erreur) {
        if (sansReseau(erreur)) return;
        // Refus définitif (devoir clos, déjà rendu…) : l'envoi sort de la file.
      }
      ecrire(cache.filter((e) => e.cle !== envoi.cle));
    }
  } finally {
    rejeuEnCours = false;
  }
}

/** Déconnexion : les envois d'un compte ne restent pas sur un téléphone partagé. */
export function viderFileAttente() {
  ecrire([]);
}

if (typeof window !== "undefined") {
  window.addEventListener("online", () => void rejouerFileAttente());
  window.addEventListener("storage", (e) => e.key === STOCKAGE && ecrire(lire()));
}
