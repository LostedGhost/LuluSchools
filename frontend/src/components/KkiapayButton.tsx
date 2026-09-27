import { useEffect, useRef } from "react";

const KKIAPAY_SCRIPT_SRC = "https://cdn.kkiapay.me/k.js";
const KKIAPAY_PUBLIC_KEY = import.meta.env.VITE_KKIAPAY_PUBLIC_KEY as string | undefined;
const KKIAPAY_SANDBOX = (import.meta.env.VITE_KKIAPAY_SANDBOX as string | undefined) !== "false";

declare global {
  interface Window {
    openKkiapayWidget?: (options: {
      amount: number;
      api_key: string;
      sandbox: boolean;
      data?: string;
      partnerId?: string;
    }) => void;
    addSuccessListener?: (callback: (response: { transactionId: string }) => void) => void;
    addFailedListener?: (callback: (error: unknown) => void) => void;
  }
}

let scriptCharge: Promise<void> | null = null;

// Le widget Kkiapay est global : ajouter un ecouteur a chaque ouverture les empilait, et un
// paiement reussi declenchait alors le rattachement a TOUTES les ressources ouvertes
// auparavant. Un seul ecouteur, enregistre une fois, route vers le paiement en cours.
let paiementEnCours: { onSucces: (transactionId: string) => void; onEchec?: () => void } | null = null;
let ecouteursInstalles = false;

function installerEcouteurs() {
  if (ecouteursInstalles) return;
  window.addSuccessListener?.((response) => {
    const courant = paiementEnCours;
    paiementEnCours = null;
    courant?.onSucces(response.transactionId);
  });
  window.addFailedListener?.(() => {
    const courant = paiementEnCours;
    paiementEnCours = null;
    courant?.onEchec?.();
  });
  ecouteursInstalles = true;
}

export type TypeRessourcePayable =
  | "acte"
  | "ticket_transport"
  | "ticket_cantine"
  | "billet"
  | "offre_micro_job"
  | "transaction_marketplace";

function chargerScriptKkiapay(): Promise<void> {
  if (scriptCharge) return scriptCharge;
  scriptCharge = new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${KKIAPAY_SCRIPT_SRC}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = KKIAPAY_SCRIPT_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Impossible de charger le widget de paiement Kkiapay."));
    document.body.appendChild(script);
  });
  return scriptCharge;
}

interface KkiapayButtonProps {
  montant: number;
  /** Type de la ressource payee : avec `reference`, forme le partnerId renvoye par le webhook. */
  typeRessource: TypeRessourcePayable;
  reference: string;
  onSucces: (transactionId: string) => void;
  onEchec?: () => void;
  disabled?: boolean;
}

export function KkiapayButton({ montant, typeRessource, reference, onSucces, onEchec, disabled }: KkiapayButtonProps) {
  const pretRef = useRef(false);

  useEffect(() => {
    chargerScriptKkiapay()
      .then(() => {
        pretRef.current = true;
      })
      .catch(() => {
        pretRef.current = false;
      });
  }, []);

  const ouvrirWidget = async () => {
    if (!KKIAPAY_PUBLIC_KEY) {
      window.alert("Paiement indisponible : cle publique Kkiapay non configuree.");
      return;
    }
    await chargerScriptKkiapay().catch(() => {
      window.alert("Impossible de charger le module de paiement, verifiez votre connexion.");
    });
    if (!window.openKkiapayWidget) {
      window.alert("Le module de paiement n'a pas pu demarrer.");
      return;
    }
    installerEcouteurs();
    paiementEnCours = { onSucces, onEchec };
    window.openKkiapayWidget({
      amount: Math.round(montant),
      api_key: KKIAPAY_PUBLIC_KEY,
      sandbox: KKIAPAY_SANDBOX,
      data: JSON.stringify({ reference }),
      // Le backend identifie la ressource payee par ce champ (webhook), jamais par un
      // identifiant de transaction fourni ensuite par le navigateur.
      partnerId: `${typeRessource}:${reference}`,
    });
  };

  return (
    <button
      type="button"
      onClick={ouvrirWidget}
      disabled={disabled}
      className="rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
    >
      Payer {montant.toLocaleString("fr-FR")} FCFA avec Kkiapay
    </button>
  );
}
