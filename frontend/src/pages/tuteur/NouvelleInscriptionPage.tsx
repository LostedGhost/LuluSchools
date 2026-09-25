import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import { creerInscription } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import type { ClasseOut, EtablissementOut, Nationalite } from "../../types/api";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../../components/ui";

export function NouvelleInscriptionPage() {
  const navigate = useNavigate();
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [classeId, setClasseId] = useState("");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [dateNaissance, setDateNaissance] = useState("");
  const [nationalite, setNationalite] = useState<Nationalite>("nationale");
  const [consentement, setConsentement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);

  useEffect(() => {
    if (!etablissementId) {
      setClasses([]);
      return;
    }
    listerClasses(etablissementId)
      .then((res) => setClasses(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    if (!classeId) {
      setErreur("Veuillez choisir une classe.");
      return;
    }
    setEnCours(true);
    try {
      await creerInscription({
        nom,
        prenom,
        date_naissance: dateNaissance,
        classe_id: classeId,
        nationalite,
        consentement_parental_donne: consentement,
      });
      navigate("/tuteur", { replace: true });
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre l'inscription."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <PageTitle>Nouvelle inscription</PageTitle>
      <Card>
        <form onSubmit={soumettre} className="space-y-4">
          <Field label="Etablissement">
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={etablissementId}
              onChange={(e) => {
                setEtablissementId(e.target.value);
                setClasseId("");
              }}
              required
            >
              <option value="">Choisir...</option>
              {etablissements.map((etab) => (
                <option key={etab.id} value={etab.id}>
                  {etab.nom} ({etab.code_etablissement})
                </option>
              ))}
            </select>
          </Field>

          <Field label="Classe">
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={classeId}
              onChange={(e) => setClasseId(e.target.value)}
              required
              disabled={!etablissementId}
            >
              <option value="">Choisir...</option>
              {classes.map((classe) => (
                <option key={classe.id} value={classe.id}>
                  {classe.niveau} ({classe.capacite} places)
                </option>
              ))}
            </select>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Nom de l'enfant">
              <TextInput value={nom} onChange={(e) => setNom(e.target.value)} required />
            </Field>
            <Field label="Prenom de l'enfant">
              <TextInput value={prenom} onChange={(e) => setPrenom(e.target.value)} required />
            </Field>
          </div>

          <Field label="Date de naissance">
            <TextInput
              type="date"
              value={dateNaissance}
              onChange={(e) => setDateNaissance(e.target.value)}
              required
            />
          </Field>

          <Field label="Nationalite">
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={nationalite}
              onChange={(e) => setNationalite(e.target.value as Nationalite)}
            >
              <option value="nationale">Beninoise</option>
              <option value="etrangere">Etrangere</option>
            </select>
          </Field>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={consentement}
              onChange={(e) => setConsentement(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Je donne mon consentement pour cette inscription (requis si l'enfant a moins de 16 ans)
          </label>

          <ErrorBanner>{erreur}</ErrorBanner>
          <PrimaryButton type="submit" disabled={enCours} className="w-full">
            {enCours ? "Envoi..." : "Soumettre l'inscription"}
          </PrimaryButton>
        </form>
      </Card>
    </div>
  );
}
