import { useEffect, useState, type FormEvent } from "react";
import { creerReferentiel, listerReferentiels, validerReferentiel, type ReferentielOut } from "../../api/evaluations_gouvernance";
import { messageErreur } from "../../api/client";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, PageTitle, SectionHead, SkeletonCard, TextInput } from "../../components/ui";
import { Scale } from "lucide-react";

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

export function ReferentielsPage() {
  const [referentiels, setReferentiels] = useState<ReferentielOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [niveau, setNiveau] = useState("");
  const [matiere, setMatiere] = useState("");
  const [coefficient, setCoefficient] = useState(1);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [validationEnCoursId, setValidationEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    listerReferentiels()
      .then((res) => setReferentiels(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await creerReferentiel(niveau, matiere, coefficient);
      setNiveau("");
      setMatiere("");
      setCoefficient(1);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le référentiel."));
    } finally {
      setEnCours(false);
    }
  };

  const valider = async (id: string) => {
    setValidationEnCoursId(id);
    try {
      await validerReferentiel(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setValidationEnCoursId(null);
    }
  };

  const referentielsActifs = referentiels.filter((r) => r.statut !== "remplace");

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace ministériel">Référentiels de coefficients</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-8" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
        <SectionHead title="Fixer un référentiel national" desc="Coefficient par niveau et matière, applicable à tous les établissements." />
        <form onSubmit={soumettre} style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
          <Field label="Niveau">
            <TextInput value={niveau} onChange={(e) => setNiveau(e.target.value)} placeholder="Ex. CE1" required />
          </Field>
          <Field label="Matière">
            <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} placeholder="Ex. Mathématiques" required />
          </Field>
          <Field label="Coefficient">
            <TextInput
              type="number"
              step="0.1"
              value={coefficient}
              onChange={(e) => setCoefficient(Number(e.target.value))}
              style={{ width: "100px" }}
            />
          </Field>
          <Btn type="submit" variant="primary" loading={enCours}>
            Fixer
          </Btn>
        </form>
      </Card>

      <SectionHead title="Référentiels" />
      {chargement ? (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : referentielsActifs.length === 0 ? (
        <EmptyState icon={<Scale size={24} />} title="Aucun référentiel" desc="Fixez le premier référentiel national ci-dessus." />
      ) : (
        <div className="space-y-3">
          {referentielsActifs.map((r) => (
            <Card key={r.id}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)" }}>
                <div>
                  <p style={{ fontWeight: 600, color: "var(--ink)" }}>
                    {r.niveau} — {r.matiere}
                  </p>
                  <p className="monospace text-sm" style={{ color: "var(--ink-soft)" }}>Coefficient {r.coefficient}</p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                  <Badge tone={TONE_STATUT[r.statut]}>{LABEL_STATUT[r.statut]}</Badge>
                  {r.statut === "proposition_en_attente" && (
                    <Btn variant="outline" size="sm" loading={validationEnCoursId === r.id} onClick={() => valider(r.id)}>
                      Valider
                    </Btn>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
