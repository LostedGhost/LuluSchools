import { useEffect, useState } from "react";
import { obtenirRadarFamilial } from "../../api/radar_familial";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { RadarFamilialOut } from "../../types/api";
import { Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard } from "../../components/ui";
import { Radar, Users } from "lucide-react";

export function RadarFamilialPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [radar, setRadar] = useState<RadarFamilialOut | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  useEffect(() => {
    if (!enfant || !enfant.eleve_utilisateur_id) return;
    setChargement(true);
    obtenirRadarFamilial(enfant.eleve_utilisateur_id)
      .then((res) => setRadar(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [enfant]);

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Mes enfants"
        title="Radar familial"
        desc="Un résumé de la semaine écoulée, généré à partir de la vie scolaire, des devoirs corrigés et des sessions suivies."
      />
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
          ) : radar ? (
            <Card>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px", color: "var(--primary-deep)", fontWeight: 700 }}>
                <Radar size={18} /> {radar.periode_debut} → {radar.periode_fin}
              </div>
              <p style={{ margin: "0 0 16px", fontSize: "var(--text-sm)", whiteSpace: "pre-wrap" }}>{radar.resume}</p>
              {radar.sources.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "var(--text-xs)", color: "var(--ink-soft)" }}>
                  {radar.sources.map((source, i) => (
                    <li key={i}>{source}</li>
                  ))}
                </ul>
              )}
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}
