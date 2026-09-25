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
    }) => void;
    addSuccessListener?: (callback: (response: { transactionId: string }) => void) => void;
    addFailedListener?: (callback: (error: unknown) => void) => void;
  }
}

let scriptCharge: Promise<void> | null = null;

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
  reference: string;
  onSucces: (transactionId: string) => void;
  onEchec?: () => void;
  disabled?: boolean;
}

export function KkiapayButton({ montant, reference, onSucces, onEchec, disabled }: KkiapayButtonProps) {
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
    window.addSuccessListener?.((response) => onSucces(response.transactionId));
    window.addFailedListener?.(() => onEchec?.());
    window.openKkiapayWidget({
      amount: Math.round(montant),
      api_key: KKIAPAY_PUBLIC_KEY,
      sandbox: KKIAPAY_SANDBOX,
      data: JSON.stringify({ reference }),
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
