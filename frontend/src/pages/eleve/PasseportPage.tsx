import { useEffect, useState } from "react";
import { exporterMonPasseport, obtenirMonPasseport } from "../../api/passeport";
import { messageErreur } from "../../api/client";
import type { PasseportOut } from "../../types/api";
import { PasseportPanel } from "../../components/passeport/PasseportPanel";
import { ErrorBanner, SectionHead, SkeletonCard } from "../../components/ui";

export function PasseportPage() {
  const [passeport, setPasseport] = useState<PasseportOut | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    obtenirMonPasseport()
      .then((res) => setPasseport(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, []);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Mon parcours" title="Passeport de compétences" desc="Un récapitulatif automatique de vos quiz réussis, cours suivis et moyennes." />
      <ErrorBanner>{erreur}</ErrorBanner>

      {chargement ? (
        <SkeletonCard />
      ) : passeport ? (
        <PasseportPanel passeport={passeport} exporter={async () => (await exporterMonPasseport()).data} />
      ) : null}
    </div>
  );
}
