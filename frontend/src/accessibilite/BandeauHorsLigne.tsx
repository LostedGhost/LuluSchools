import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

/** Lot 7.5 : prévient quand le réseau tombe (les contenus déjà consultés restent lisibles). */
export function BandeauHorsLigne() {
  const [horsLigne, setHorsLigne] = useState(() => typeof navigator !== "undefined" && !navigator.onLine);

  useEffect(() => {
    const maj = () => setHorsLigne(!navigator.onLine);
    window.addEventListener("online", maj);
    window.addEventListener("offline", maj);
    return () => {
      window.removeEventListener("online", maj);
      window.removeEventListener("offline", maj);
    };
  }, []);

  if (!horsLigne) return null;
  return (
    <div className="bandeau-hors-ligne" role="status">
      <WifiOff size={16} aria-hidden="true" />
      <span>Pas de connexion : vous voyez la dernière version enregistrée. Vos envois partiront au retour du réseau.</span>
    </div>
  );
}
