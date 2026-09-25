import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { creerClasse, listerClasses } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { ClasseOut, PolitiqueDepassement } from "../../types/api";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../../components/ui";

const LIBELLES_POLITIQUE: Record<PolitiqueDepassement, string> = {
  ordre_arrivee: "Ordre d'arrivee",
  notes_concours: "Notes de concours",
  tirage_sort: "Tirage au sort",
};

export function ClassesPage() {
  const etablissement = useAdminEtab();
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [niveau, setNiveau] = useState("");
  const [capacite, setCapacite] = useState(30);
  const [politique, setPolitique] = useState<PolitiqueDepassement>("ordre_arrivee");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    listerClasses(etablissement.id)
      .then((res) => setClasses(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, [etablissement.id]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await creerClasse(etablissement.id, { niveau, capacite, politique_depassement: politique });
      setNiveau("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer la classe."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div>
      <PageTitle>Classes</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-4">
        <form onSubmit={soumettre} className="flex flex-wrap items-end gap-3">
          <Field label="Niveau">
            <TextInput value={niveau} onChange={(e) => setNiveau(e.target.value)} required />
          </Field>
          <Field label="Capacite">
            <TextInput
              type="number"
              value={capacite}
              onChange={(e) => setCapacite(Number(e.target.value))}
              required
              className="w-24"
            />
          </Field>
          <Field label="Politique de depassement">
            <select
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={politique}
              onChange={(e) => setPolitique(e.target.value as PolitiqueDepassement)}
            >
              <option value="ordre_arrivee">Ordre d'arrivee</option>
              <option value="notes_concours">Notes de concours</option>
              <option value="tirage_sort">Tirage au sort</option>
            </select>
          </Field>
          <PrimaryButton type="submit" disabled={enCours}>
            {enCours ? "Creation..." : "Creer"}
          </PrimaryButton>
        </form>
      </Card>

      <div className="space-y-3">
        {classes.map((c) => (
          <Card key={c.id} className="flex items-center justify-between">
            <p className="font-medium text-slate-900">{c.niveau}</p>
            <p className="text-sm text-slate-500">
              {c.capacite} places — {LIBELLES_POLITIQUE[c.politique_depassement]}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
