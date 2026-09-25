import { useEffect, useState } from "react";
import { listerReferentiels, proposerReferentiel, type ReferentielOut } from "../../api/evaluations_gouvernance";
import { messageErreur } from "../../api/client";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, PageTitle, SkeletonCard, TextInput } from "../../components/ui";
import { Scale, Send } from "lucide-react";

const TONE_STATUT: Record<ReferentielOut["statut"], "success" | "pending" | "neutral"> = {
  valide: "success",
  proposition_en_attente: "pending",
  remplace: "neutral",
};

const LABEL_STATUT: Record<ReferentielOut["statut"], string> = {
  valide: "En vigueur",
  proposition_en_attente: "Proposition en attente",
  remplace: "Remplacé",
};

export function ReferentielsEtabPage() {
  const [referentiels, setReferentiels] = useState<ReferentielOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [propositionOuverte, setPropositionOuverte] = useState<string | null>(null);
  const [nouveauCoefficient, setNouveauCoefficient] = useState<number>(1);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    setChargement(true);
    listerReferentiels()
      .then((res) => setReferentiels(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  const ouvrirProposition = (r: ReferentielOut) => {
    setPropositionOuverte(r.id);
    setNouveauCoefficient(r.coefficient);
    setSucces(null);
  };

  const soumettreProposition = async (referentielId: string) => {
    setErreur(null);
    setEnCours(true);
    try {
      await proposerReferentiel(referentielId, nouveauCoefficient);
      setPropositionOuverte(null);
      setSucces("Proposition envoyée — elle prendra effet une fois validée par le ministère.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'envoyer cette proposition."));
    } finally {
      setEnCours(false);
    }
  };

  // Un referentiel "remplace" n'a plus d'interet operationnel une fois qu'un autre
  // (valide ou en attente) couvre deja le meme niveau/matiere.
  const referentielsActifs = referentiels.filter((r) => r.statut !== "remplace");

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace établissement">Référentiels de coefficients</PageTitle>
      <p className="text-sm mb-6" style={{ color: "var(--ink-soft)" }}>
        Les coefficients sont fixés par le ministère. Vous pouvez proposer une mise à jour pour votre établissement —
        elle n'est effective qu'après validation ministérielle (UC-09).
      </p>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && (
        <div className="mb-4">
          <Badge tone="success">{succes}</Badge>
        </div>
      )}

      {chargement ? (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : referentielsActifs.length === 0 ? (
        <EmptyState
          icon={<Scale size={24} />}
          title="Aucun référentiel publié"
          desc="Le ministère n'a pas encore fixé de coefficient — revenez plus tard."
        />
      ) : (
        <div className="space-y-3">
          {referentielsActifs.map((r) => (
            <Card key={r.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)" }}>
                <div>
                  <p style={{ fontWeight: 600, color: "var(--ink)" }}>
                    {r.niveau} — {r.matiere}
                  </p>
                  <p className="monospace text-sm" style={{ color: "var(--ink-soft)" }}>
                    Coefficient actuel : {r.coefficient}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <Badge tone={TONE_STATUT[r.statut]}>{LABEL_STATUT[r.statut]}</Badge>
                  {r.statut === "valide" && propositionOuverte !== r.id && (
                    <Btn variant="outline" size="sm" onClick={() => ouvrirProposition(r)}>
                      Proposer une mise à jour
                    </Btn>
                  )}
                </div>
              </div>

              {propositionOuverte === r.id && (
                <div className="anim-slide-up" style={{ marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px dashed var(--border)", display: "flex", alignItems: "flex-end", gap: "var(--space-3)", flexWrap: "wrap" }}>
                  <Field label="Nouveau coefficient proposé">
                    <TextInput
                      type="number"
                      step="0.1"
                      min={0}
                      value={nouveauCoefficient}
                      onChange={(e) => setNouveauCoefficient(Number(e.target.value))}
                      style={{ width: "120px" }}
                    />
                  </Field>
                  <Btn variant="primary" size="sm" loading={enCours} onClick={() => soumettreProposition(r.id)} leftIcon={<Send size={14} />}>
                    Envoyer la proposition
                  </Btn>
                  <Btn variant="ghost" size="sm" onClick={() => setPropositionOuverte(null)} disabled={enCours}>
                    Annuler
                  </Btn>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
