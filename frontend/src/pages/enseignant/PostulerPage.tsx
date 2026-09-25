import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { obtenirPoste, postuler } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { PosteOut } from "../../types/api";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton } from "../../components/ui";

export function PostulerPage() {
  const { posteId } = useParams<{ posteId: string }>();
  const navigate = useNavigate();
  const [poste, setPoste] = useState<PosteOut | null>(null);
  const [fichiers, setFichiers] = useState<Record<string, File>>({});
  const [casierJudiciaire, setCasierJudiciaire] = useState<File | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    if (!posteId) return;
    obtenirPoste(posteId)
      .then((res) => setPoste(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [posteId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!poste || !posteId) return;
    const types = poste.criteres.map((c) => c.type_document);
    if (types.some((t) => !fichiers[t]) || !casierJudiciaire) {
      setErreur("Veuillez fournir tous les documents demandes, dont le casier judiciaire.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      await postuler(
        posteId,
        types,
        types.map((t) => fichiers[t]),
        casierJudiciaire,
      );
      navigate("/enseignant/candidatures", { replace: true });
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre la candidature."));
    } finally {
      setEnCours(false);
    }
  };

  if (!poste) return <ErrorBanner>{erreur}</ErrorBanner>;

  return (
    <div className="mx-auto max-w-lg">
      <PageTitle>Postuler : {poste.titre}</PageTitle>
      <Card>
        <form onSubmit={soumettre} className="space-y-4">
          {poste.criteres.map((critere) => (
            <Field key={critere.type_document} label={`Document : ${critere.type_document}`}>
              <input
                type="file"
                onChange={(e) =>
                  setFichiers((prev) => ({ ...prev, [critere.type_document]: e.target.files![0] }))
                }
                className="block w-full text-sm"
                required
              />
            </Field>
          ))}
          <Field label="Casier judiciaire (stocke localement, jamais partage - Art. 395)">
            <input
              type="file"
              onChange={(e) => setCasierJudiciaire(e.target.files?.[0] ?? null)}
              className="block w-full text-sm"
              required
            />
          </Field>
          <ErrorBanner>{erreur}</ErrorBanner>
          <PrimaryButton type="submit" disabled={enCours} className="w-full">
            {enCours ? "Envoi..." : "Soumettre ma candidature"}
          </PrimaryButton>
        </form>
      </Card>
    </div>
  );
}
