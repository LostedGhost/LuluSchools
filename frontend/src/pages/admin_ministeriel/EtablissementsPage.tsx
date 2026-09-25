import { useEffect, useState, type FormEvent } from "react";
import { creerEtablissement, listerEtablissements } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, TypeEtablissement } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  Select,
  SkeletonCard,
  SuccessBanner,
  TextInput,
} from "../../components/ui";
import { Building2 } from "lucide-react";
import { estRempli, estEmailValide } from "../../utils/validation";

export function EtablissementsPage() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [nom, setNom] = useState("");
  const [type, setType] = useState<TypeEtablissement>("EP");
  const [statut, setStatut] = useState<"public" | "prive">("public");
  const [adminNom, setAdminNom] = useState("");
  const [adminPrenom, setAdminPrenom] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [champErreurs, setChampErreurs] = useState<{ nom?: string; adminNom?: string; adminPrenom?: string; adminEmail?: string }>({});

  const charger = () => {
    setChargement(true);
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);

    const erreurs: typeof champErreurs = {};
    if (!estRempli(nom)) erreurs.nom = "Nom de l'établissement requis.";
    if (!estRempli(adminNom)) erreurs.adminNom = "Nom de l'administrateur requis.";
    if (!estRempli(adminPrenom)) erreurs.adminPrenom = "Prénom de l'administrateur requis.";
    if (!estEmailValide(adminEmail)) erreurs.adminEmail = "Adresse e-mail invalide.";
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await creerEtablissement({
        nom,
        type,
        statut,
        admin: { nom: adminNom, prenom: adminPrenom, email: adminEmail },
      });
      setSucces(`Établissement créé. Identifiants temporaires envoyés à ${adminEmail}.`);
      setNom("");
      setAdminNom("");
      setAdminPrenom("");
      setAdminEmail("");
      setShowForm(false);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer l'établissement."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="page-content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <PageTitle eyebrow="Espace ministériel">Établissements</PageTitle>
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "+ Créer un établissement"}
        </Btn>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && (
        <div className="mb-4">
          <SuccessBanner>{succes}</SuccessBanner>
        </div>
      )}

      {showForm && (
        <Card className="mb-8 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
          <SectionHead title="Créer un établissement" desc="Provisionne aussi le premier compte A+, avec mot de passe temporaire envoyé par e-mail." />
          <form onSubmit={soumettre} noValidate className="space-y-4" style={{ marginTop: "var(--space-4)" }}>
            <div className="grid-3">
              <Field label="Nom" error={champErreurs.nom}>
                <TextInput value={nom} onChange={(e) => setNom(e.target.value)} />
              </Field>
              <Field label="Type">
                <Select value={type} onChange={(e) => setType(e.target.value as TypeEtablissement)}>
                  <option value="EP">Primaire (EP)</option>
                  <option value="ES">Secondaire (ES)</option>
                  <option value="UP">Universitaire (UP)</option>
                </Select>
              </Field>
              <Field label="Statut">
                <Select value={statut} onChange={(e) => setStatut(e.target.value as "public" | "prive")}>
                  <option value="public">Public</option>
                  <option value="prive">Privé</option>
                </Select>
              </Field>
            </div>
            <p className="text-eyebrow">Administrateur de l'établissement</p>
            <div className="grid-3">
              <Field label="Nom" error={champErreurs.adminNom}>
                <TextInput value={adminNom} onChange={(e) => setAdminNom(e.target.value)} />
              </Field>
              <Field label="Prénom" error={champErreurs.adminPrenom}>
                <TextInput value={adminPrenom} onChange={(e) => setAdminPrenom(e.target.value)} />
              </Field>
              <Field label="E-mail" error={champErreurs.adminEmail}>
                <TextInput type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} />
              </Field>
            </div>
            <Btn type="submit" variant="primary" loading={enCours}>
              Créer l'établissement
            </Btn>
          </form>
        </Card>
      )}

      <SectionHead title="Établissements du réseau" />
      {chargement ? (
        <div className="grid-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : etablissements.length === 0 ? (
        <EmptyState icon={<Building2 size={24} />} title="Aucun établissement" desc="Créez le premier établissement du réseau ci-dessus." />
      ) : (
        <div className="grid-3">
          {etablissements.map((e) => (
            <Card key={e.id}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-2)" }}>
                <div style={{
                  width: "40px", height: "40px", borderRadius: "var(--radius-md)",
                  background: "var(--primary-tint)", color: "var(--primary-deep)",
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }} aria-hidden="true">
                  <Building2 size={20} />
                </div>
                <span style={{ fontWeight: 600, color: "var(--ink)" }}>{e.nom}</span>
              </div>
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <Badge tone="neutral">{e.code_etablissement}</Badge>
                <Badge tone="info">{e.type}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
