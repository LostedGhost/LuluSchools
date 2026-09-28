import { useEffect, useState } from "react";
import { RefreshCw, WifiOff } from "lucide-react";
import { rejouerFileAttente, useFileAttente } from "../hors_ligne/fileAttente";

/** Lot 7.5 : prévient quand le réseau tombe et montre les envois qui attendent (UC-80). */
export function BandeauHorsLigne() {
  const [horsLigne, setHorsLigne] = useState(() => typeof navigator !== "undefined" && !navigator.onLine);
  const file = useFileAttente();

  useEffect(() => {
    const maj = () => setHorsLigne(!navigator.onLine);
    window.addEventListener("online", maj);
    window.addEventListener("offline", maj);
    return () => {
      window.removeEventListener("online", maj);
      window.removeEventListener("offline", maj);
    };
  }, []);

  if (!horsLigne && file.length === 0) return null;
  const attente = file.length > 0 ? `${file.length} envoi${file.length > 1 ? "s" : ""} en attente` : "";
  return (
    <div className="bandeau-hors-ligne" role="status">
      <WifiOff size={16} aria-hidden="true" />
      <span style={{ flex: 1 }}>
        {horsLigne ? "Pas de connexion : vous voyez la dernière version enregistrée." : "Connexion revenue."}
        {attente && ` ${attente} (${file.map((e) => e.libelle).join(", ")}) : ${horsLigne ? "ils partiront au retour du réseau." : "envoi en cours."}`}
      </span>
      {!horsLigne && file.length > 0 && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void rejouerFileAttente()} style={{ gap: "6px" }}>
          <RefreshCw size={14} aria-hidden="true" /> Réessayer
        </button>
      )}
    </div>
  );
}
