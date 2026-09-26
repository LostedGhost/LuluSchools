import { useEffect, useState } from "react";
import { listerVieScolaireEleve } from "../../api/vie_scolaire";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { EntreeVieScolaireOut, NatureEntreeVieScolaire } from "../../types/api";
import { Badge, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard } from "../../components/ui";
import { Users } from "lucide-react";

const LIBELLES_NATURE: Record<NatureEntreeVieScolaire, { label: string; tone: "success" | "pending" | "error" | "info" | "neutral" }> = {
  absence: { label: "Absence", tone: "pending" },
  retard: { label: "Retard", tone: "pending" },
  appreciation: { label: "Appréciation", tone: "info" },
  incident: { label: "Incident", tone: "error" },
  felicitation: { label: "Félicitation", tone: "success" },
};

export function VieScolaireEnfantPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [entrees, setEntrees] = useState<EntreeVieScolaireOut[]>([]);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  useEffect(() => {
    if (!enfant) return;
    setChargement(true);
    listerVieScolaireEleve(enfant.classe_id, enfant.eleve_id)
      .then((res) => setEntrees(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [enfant]);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Mes enfants" title="Vie scolaire" desc="Absences, retards, appréciations et incidents consignés par les enseignants." />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" desc="Ce suivi est disponible une fois l'inscription de votre enfant validée." />
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
          ) : entrees.length === 0 ? (
            <EmptyState title="Aucune entrée" desc="Rien n'a encore été consigné pour cet enfant." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {entrees.map((entree) => {
                const libelle = LIBELLES_NATURE[entree.nature];
                return (
                  <div key={entree.id} className="card" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                      <Badge tone={libelle.tone}>{libelle.label}</Badge>
                      {entree.matiere && (
                        <span style={{ fontSize: "var(--text-xs)", color: "var(--ink-soft)" }}>{entree.matiere}</span>
                      )}
                      <span style={{ fontSize: "var(--text-xs)", color: "var(--ink-faint)", fontFamily: "var(--font-mono)" }}>
                        {entree.date_survenue}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink)" }}>{entree.description}</p>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
