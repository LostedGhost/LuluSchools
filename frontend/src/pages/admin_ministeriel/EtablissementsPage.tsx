import { useEffect, useState, type FormEvent } from "react";
import { creerEtablissement, listerEtablissements } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, TypeEtablissement } from "../../types/api";
import { Badge, Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../../components/ui";

export function EtablissementsPage() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [nom, setNom] = useState("");
  const [type, setType] = useState<TypeEtablissement>("EP");
  const [statut, setStatut] = useState<"public" | "prive">("public");
  const [adminNom, setAdminNom] = useState("");
  const [adminPrenom, setAdminPrenom] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, []);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);
    setEnCours(true);
    try {
      await creerEtablissement({
        nom,
        type,
        statut,
        admin: { nom: adminNom, prenom: adminPrenom, email: adminEmail },
      });
      setSucces(`Etablissement cree. Identifiants temporaires envoyes a ${adminEmail}.`);
      setNom("");
      setAdminNom("");
      setAdminPrenom("");
      setAdminEmail("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer l'etablissement."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div>
      <PageTitle>Etablissements</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && <p className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{succes}</p>}

      <Card className="mb-4">
        <p className="mb-3 font-medium text-slate-900">Creer un etablissement</p>
        <form onSubmit={soumettre} className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <Field label="Nom">
              <TextInput value={nom} onChange={(e) => setNom(e.target.value)} required />
            </Field>
            <Field label="Type">
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={type}
                onChange={(e) => setType(e.target.value as TypeEtablissement)}
              >
                <option value="EP">Primaire (EP)</option>
                <option value="ES">Secondaire (ES)</option>
                <option value="UP">Universitaire (UP)</option>
              </select>
            </Field>
            <Field label="Statut">
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={statut}
                onChange={(e) => setStatut(e.target.value as "public" | "prive")}
              >
                <option value="public">Public</option>
                <option value="prive">Prive</option>
              </select>
            </Field>
          </div>
          <p className="text-sm font-medium text-slate-700">Administrateur de l'etablissement</p>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Nom">
              <TextInput value={adminNom} onChange={(e) => setAdminNom(e.target.value)} required />
            </Field>
            <Field label="Prenom">
              <TextInput value={adminPrenom} onChange={(e) => setAdminPrenom(e.target.value)} required />
            </Field>
            <Field label="E-mail">
              <TextInput type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} required />
            </Field>
          </div>
          <PrimaryButton type="submit" disabled={enCours}>
            {enCours ? "Creation..." : "Creer l'etablissement"}
          </PrimaryButton>
        </form>
      </Card>

      <div className="space-y-2">
        {etablissements.map((e) => (
          <Card key={e.id} className="flex items-center justify-between">
            <span>{e.nom}</span>
            <div className="flex items-center gap-2">
              <Badge tone="gray">{e.code_etablissement}</Badge>
              <Badge tone="blue">{e.type}</Badge>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
