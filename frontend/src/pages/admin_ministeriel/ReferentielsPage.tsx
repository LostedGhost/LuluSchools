import { useEffect, useState, type FormEvent } from "react";
import { creerReferentiel, listerReferentiels, validerReferentiel, type ReferentielOut } from "../../api/evaluations_gouvernance";
import { messageErreur } from "../../api/client";
import { Badge, Card, ErrorBanner, Field, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";

export function ReferentielsPage() {
  const [referentiels, setReferentiels] = useState<ReferentielOut[]>([]);
  const [niveau, setNiveau] = useState("");
  const [matiere, setMatiere] = useState("");
  const [coefficient, setCoefficient] = useState(1);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    listerReferentiels()
      .then((res) => setReferentiels(res.data))
      .catch((err) => setErreur(messageErreur(err)));
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
      setErreur(messageErreur(err, "Impossible de creer le referentiel."));
    } finally {
      setEnCours(false);
    }
  };

  const valider = async (id: string) => {
    try {
      await validerReferentiel(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <PageTitle>Referentiels de coefficients</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-4">
        <p className="mb-3 font-medium text-slate-900">Fixer un referentiel national</p>
        <form onSubmit={soumettre} className="flex flex-wrap items-end gap-3">
          <Field label="Niveau">
            <TextInput value={niveau} onChange={(e) => setNiveau(e.target.value)} required />
          </Field>
          <Field label="Matiere">
            <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} required />
          </Field>
          <Field label="Coefficient">
            <TextInput
              type="number"
              step="0.1"
              value={coefficient}
              onChange={(e) => setCoefficient(Number(e.target.value))}
              className="w-24"
            />
          </Field>
          <PrimaryButton type="submit" disabled={enCours}>
            {enCours ? "Creation..." : "Fixer"}
          </PrimaryButton>
        </form>
      </Card>

      <div className="space-y-2">
        {referentiels.map((r) => (
          <Card key={r.id} className="flex items-center justify-between">
            <span>
              {r.niveau} — {r.matiere} — coefficient {r.coefficient}
            </span>
            <div className="flex items-center gap-2">
              <Badge tone={r.statut === "valide" ? "green" : r.statut === "proposition_en_attente" ? "amber" : "gray"}>
                {r.statut}
              </Badge>
              {r.statut === "proposition_en_attente" && (
                <SecondaryButton type="button" onClick={() => valider(r.id)}>
                  Valider
                </SecondaryButton>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
