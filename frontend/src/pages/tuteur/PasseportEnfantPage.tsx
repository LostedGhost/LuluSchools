import { useEffect, useState } from "react";
import { exporterPasseportDeMonEnfant, obtenirPasseportDeMonEnfant } from "../../api/passeport";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { PasseportOut } from "../../types/api";
import { PasseportPanel } from "../../components/passeport/PasseportPanel";
import { EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard } from "../../components/ui";
import { Users } from "lucide-react";

export function PasseportEnfantPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [passeport, setPasseport] = useState<PasseportOut | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  useEffect(() => {
    if (!enfant || !enfant.eleve_utilisateur_id) return;
    setChargement(true);
    obtenirPasseportDeMonEnfant(enfant.eleve_utilisateur_id)
      .then((res) => setPasseport(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [enfant]);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Mes enfants" title="Passeport de compétences" desc="Un récapitulatif automatique des réalisations de votre enfant." />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" />
      ) : (
        <>
          <div className="card card-soft" style={{ marginBottom: "24px", maxWidth: "360px" }}>
            <Field label="Enfant">
              <Select value={inscriptionId} onChange={(e) => setInscriptionId(e.target.value)}>
                {enfants.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.eleve_prenom} {i.eleve_nom}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {chargement ? (
            <SkeletonCard />
          ) : passeport && enfant?.eleve_utilisateur_id ? (
            <PasseportPanel
              passeport={passeport}
              exporter={async () => (await exporterPasseportDeMonEnfant(enfant.eleve_utilisateur_id!)).data}
            />
          ) : null}
        </>
      )}
    </div>
  );
}
