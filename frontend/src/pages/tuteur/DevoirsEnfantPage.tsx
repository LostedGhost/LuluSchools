import { useEffect, useState } from "react";
import { listerDevoirs, obtenirSoumissionDeMonEnfant } from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { DevoirOut, SoumissionOut } from "../../types/api";
import { Badge, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard } from "../../components/ui";
import { Users } from "lucide-react";

const LIBELLES_STATUT: Record<string, { label: string; tone: "neutral" | "success" | "error" | "pending" }> = {
  en_correction: { label: "En correction", tone: "pending" },
  corrigee: { label: "Corrigé", tone: "success" },
  echec_correction: { label: "En révision", tone: "error" },
};

export function DevoirsEnfantPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [devoirs, setDevoirs] = useState<DevoirOut[]>([]);
  const [soumissions, setSoumissions] = useState<Record<string, SoumissionOut | null>>({});
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  useEffect(() => {
    if (!enfant || !enfant.eleve_utilisateur_id) return;
    const eleveUtilisateurId = enfant.eleve_utilisateur_id;
    setChargement(true);
    listerDevoirs(enfant.classe_id)
      .then(async (res) => {
        setDevoirs(res.data);
        const entrees = await Promise.all(
          res.data.map(async (d) => {
            try {
              return [d.id, (await obtenirSoumissionDeMonEnfant(d.id, eleveUtilisateurId)).data] as const;
            } catch {
              return [d.id, null] as const;
            }
          }),
        );
        setSoumissions(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [enfant]);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Mes enfants" title="Devoirs" desc="Suivez l'état des devoirs et les notes obtenues." />
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
          ) : devoirs.length === 0 ? (
            <EmptyState title="Aucun devoir" desc="Aucun devoir n'a encore été publié dans cette classe." />
          ) : (
            <div className="grid-2">
              {devoirs.map((devoir) => {
                const soumission = soumissions[devoir.id];
                const statutGlobal = soumission ? LIBELLES_STATUT[soumission.statut] : null;
                return (
                  <Card key={devoir.id}>
                    <h3 className="text-title" style={{ marginBottom: "4px" }}>{devoir.titre}</h3>
                    <p className="text-label" style={{ color: "var(--ink-soft)", marginBottom: "12px" }}>{devoir.matiere}</p>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "var(--text-sm)" }}>
                        Échéance : {new Date(devoir.date_limite).toLocaleDateString("fr-FR")}
                      </span>
                      {statutGlobal ? <Badge tone={statutGlobal.tone}>{statutGlobal.label}</Badge> : <Badge tone="neutral">À faire</Badge>}
                      {soumission?.note !== null && soumission?.note !== undefined && (
                        <Badge tone="magic">Note : {soumission.note}</Badge>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
