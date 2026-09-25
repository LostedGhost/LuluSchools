import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, School, Send, User } from "lucide-react";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import { creerInscription } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import type { ClasseOut, EtablissementOut, Nationalite } from "../../types/api";
import { Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, Select, TextInput } from "../../components/ui";
import { estRempli, erreurDateNaissance } from "../../utils/validation";

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
  const [champErreurs, setChampErreurs] = useState<{
    nom?: string;
    prenom?: string;
    dateNaissance?: string;
    etablissementId?: string;
    classeId?: string;
  }>({});

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

    const erreurs: typeof champErreurs = {};
    if (!estRempli(nom)) erreurs.nom = "Nom requis.";
    if (!estRempli(prenom)) erreurs.prenom = "Prénom requis.";
    const erreurDate = erreurDateNaissance(dateNaissance);
    if (erreurDate) erreurs.dateNaissance = erreurDate;
    if (!estRempli(etablissementId)) erreurs.etablissementId = "Veuillez choisir un établissement.";
    if (!estRempli(classeId)) erreurs.classeId = "Veuillez choisir une classe.";
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

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
    <div className="page-content-narrow">
      {/* Lien retour */}
      <div style={{ marginBottom: "16px" }}>
        <Link
          to="/tuteur"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            color: "var(--ink-faint)",
            fontSize: "var(--text-sm)",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          <ArrowLeft size={16} /> Retour au tableau de bord
        </Link>
      </div>

      <PageTitle eyebrow="Espace Tuteur">Nouvelle inscription</PageTitle>

      <form onSubmit={soumettre} noValidate style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Section 1 : Informations élève */}
        <Card className="anim-float-in delay-1">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-sm)",
                background: "var(--primary-tint)",
                border: "2px solid var(--primary-deep)",
                color: "var(--primary-deep)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <User size={20} />
            </div>
            <div>
              <SectionHead
                eyebrow="Étape 1 sur 3"
                title="Informations de l'élève"
                desc="Renseignez l'état civil de l'enfant à inscrire."
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
            <div className="grid-2">
              <Field label="Nom de l'enfant" required error={champErreurs.nom}>
                <TextInput
                  placeholder="Ex: Dossou"
                  value={nom}
                  onChange={(e) => setNom(e.target.value)}
                />
              </Field>
              <Field label="Prénom de l'enfant" required error={champErreurs.prenom}>
                <TextInput
                  placeholder="Ex: Koffi"
                  value={prenom}
                  onChange={(e) => setPrenom(e.target.value)}
                />
              </Field>
            </div>

            <div className="grid-2">
              <Field label="Date de naissance" required error={champErreurs.dateNaissance}>
                <TextInput
                  type="date"
                  value={dateNaissance}
                  onChange={(e) => setDateNaissance(e.target.value)}
                  max={new Date().toISOString().slice(0, 10)}
                />
              </Field>

              <Field label="Nationalité" required>
                <Select
                  value={nationalite}
                  onChange={(e) => setNationalite(e.target.value as Nationalite)}
                  required
                >
                  <option value="nationale">Béninoise</option>
                  <option value="etrangere">Étrangère</option>
                </Select>
              </Field>
            </div>
          </div>
        </Card>

        {/* Section 2 : Informations école */}
        <Card className="anim-float-in delay-2">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-sm)",
                background: "var(--reward-tint)",
                border: "2px solid var(--reward-deep)",
                color: "var(--reward-deep)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <School size={20} />
            </div>
            <div>
              <SectionHead
                eyebrow="Étape 2 sur 3"
                title="Informations école"
                desc="Sélectionnez l'établissement et la classe souhaitée."
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
            <Field
              label="Établissement scolaire"
              helper="Choisissez l'école pour afficher les classes disponibles"
              required
              error={champErreurs.etablissementId}
            >
              <Select
                value={etablissementId}
                onChange={(e) => {
                  setEtablissementId(e.target.value);
                  setClasseId("");
                }}
              >
                <option value="">Sélectionner un établissement...</option>
                {etablissements.map((etab) => (
                  <option key={etab.id} value={etab.id}>
                    {etab.nom} ({etab.code_etablissement})
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              label="Classe demandée"
              helper={
                !etablissementId
                  ? "Veuillez d'abord sélectionner un établissement"
                  : classes.length === 0
                  ? "Aucune classe configurée pour cet établissement"
                  : undefined
              }
              required
              error={champErreurs.classeId}
            >
              <Select
                value={classeId}
                onChange={(e) => setClasseId(e.target.value)}
                disabled={!etablissementId || classes.length === 0}
              >
                <option value="">
                  {etablissementId ? "Sélectionner une classe..." : "Choisir d'abord un établissement"}
                </option>
                {classes.map((classe) => (
                  <option key={classe.id} value={classe.id}>
                    {classe.niveau} ({classe.capacite} places)
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        </Card>

        {/* Section 3 : Consentement & Confirmation */}
        <Card className="anim-float-in delay-3">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-sm)",
                background: "var(--magic-tint)",
                border: "2px solid var(--magic-deep)",
                color: "var(--magic-deep)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CheckCircle2 size={20} />
            </div>
            <div>
              <SectionHead
                eyebrow="Étape 3 sur 3"
                title="Consentement & Validation"
                desc="Confirmation requise pour soumettre le dossier."
              />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "18px", marginTop: "16px" }}>
            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "14px",
                cursor: "pointer",
                background: "var(--surface-2)",
                padding: "16px 18px",
                borderRadius: "var(--radius-md)",
                border: "2px solid var(--border)",
              }}
            >
              <input
                type="checkbox"
                checked={consentement}
                onChange={(e) => setConsentement(e.target.checked)}
                style={{
                  marginTop: "3px",
                  width: "18px",
                  height: "18px",
                  accentColor: "var(--primary)",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              />
              <div style={{ fontSize: "var(--text-sm)", color: "var(--ink)", lineHeight: 1.5 }}>
                <strong style={{ display: "block", marginBottom: "2px", color: "var(--ink)" }}>
                  Consentement parental formel
                </strong>
                Je donne mon consentement légal pour cette inscription scolaire sur la plateforme nationale Lulu·Schools (requis si l'enfant a moins de 16 ans).
              </div>
            </label>

            {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "8px" }}>
              <Btn
                type="submit"
                variant="primary"
                size="lg"
                loading={enCours}
                leftIcon={<Send size={18} />}
                style={{ flex: 1, minWidth: "220px" }}
              >
                {enCours ? "Envoi du dossier…" : "Soumettre l'inscription"}
              </Btn>

              <Btn
                type="button"
                variant="outline"
                size="lg"
                onClick={() => navigate("/tuteur")}
              >
                Annuler
              </Btn>
            </div>
          </div>
        </Card>
      </form>
    </div>
  );
}
