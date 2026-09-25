import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { obtenirPoste, postuler } from "../../api/recrutement";
import { listerEtablissements } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, PosteOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  Skeleton,
  TextArea,
  TextInput,
} from "../../components/ui";
import {
  Briefcase,
  Building2,
  BookOpen,
  ShieldCheck,
  Send,
  CheckCircle2,
  ArrowLeft,
  FileText,
  Lock,
} from "lucide-react";

export function PostulerPage() {
  const { posteId } = useParams<{ posteId: string }>();
  const navigate = useNavigate();
  const [poste, setPoste] = useState<PosteOut | null>(null);
  const [etablissement, setEtablissement] = useState<EtablissementOut | null>(null);
  const [fichiers, setFichiers] = useState<Record<string, File>>({});
  const [casierJudiciaire, setCasierJudiciaire] = useState<File | null>(null);
  const [lettreMotivation, setLettreMotivation] = useState("");
  const [lienPortfolio, setLienPortfolio] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    if (!posteId) return;
    setChargement(true);

    Promise.all([obtenirPoste(posteId), listerEtablissements()])
      .then(([posteRes, etabsRes]) => {
        setPoste(posteRes.data);
        const etabTrouve = etabsRes.data.find(
          (e) => e.id === posteRes.data.etablissement_id
        );
        if (etabTrouve) {
          setEtablissement(etabTrouve);
        }
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [posteId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!poste || !posteId) return;
    const types = poste.criteres.map((c) => c.type_document);
    if (types.some((t) => !fichiers[t]) || !casierJudiciaire) {
      setErreur(
        "Veuillez fournir tous les documents demandés, dont le casier judiciaire."
      );
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      await postuler(
        posteId,
        types,
        types.map((t) => fichiers[t]),
        casierJudiciaire
      );
      navigate("/enseignant/candidatures", { replace: true });
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre la candidature."));
    } finally {
      setEnCours(false);
    }
  };

  if (chargement) {
    return (
      <div className="page-content-narrow">
        <div className="space-y-4">
          <Skeleton height="40px" width="60%" />
          <Skeleton height="120px" width="100%" />
          <Skeleton height="300px" width="100%" />
        </div>
      </div>
    );
  }

  if (!poste) {
    return (
      <div className="page-content-narrow">
        <Card variant="soft" className="anim-float-in text-center py-12">
          <ErrorBanner>{erreur || "Poste introuvable ou fermé."}</ErrorBanner>
          <div className="mt-4">
            <Btn variant="outline" onClick={() => navigate(-1)}>
              Retour aux opportunités
            </Btn>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="page-content-narrow anim-float-in">
      {/* Bouton retour rapide */}
      <div className="mb-4">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-xs font-bold hover:underline cursor-pointer"
          style={{ color: "var(--ink-soft)" }}
        >
          <ArrowLeft size={14} /> Retour à la liste des postes
        </button>
      </div>

      {/* En-tête principal */}
      <PageTitle eyebrow="Recrutement Enseignant">
        Postuler à l'offre
      </PageTitle>

      {/* Carte Récapitulatif du Poste */}
      <Card className="mb-8" style={{ background: "var(--surface)" }}>
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--primary-tint)",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "var(--primary-deep)",
                }}
              >
                <Briefcase size={18} />
              </span>
              <h2
                className="m-0"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "var(--text-2xl)",
                  fontWeight: 700,
                  color: "var(--ink)",
                }}
              >
                {poste.titre}
              </h2>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-sm" style={{ color: "var(--ink-soft)" }}>
              <div className="flex items-center gap-1.5 font-medium">
                <Building2 size={16} style={{ color: "var(--primary)" }} />
                <span>
                  {etablissement ? etablissement.nom : "Établissement d'accueil"}
                </span>
                {etablissement && (
                  <span
                    className="text-xs px-2 py-0.5 rounded"
                    style={{
                      background: "var(--surface-2)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {etablissement.code_etablissement}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5 font-medium">
                <BookOpen size={16} style={{ color: "var(--reward-deep)" }} />
                <span>Matière / Discipline associée</span>
              </div>
            </div>
          </div>

          <Badge tone={poste.statut === "ouvert" ? "success" : "neutral"}>
            {poste.statut === "ouvert" ? "Recrutement ouvert" : poste.statut}
          </Badge>
        </div>

        {/* Critères requis */}
        <div
          className="mt-5 pt-4"
          style={{ borderTop: "2px dashed var(--border)" }}
        >
          <p
            className="text-xs font-bold uppercase tracking-wider mb-2"
            style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono)" }}
          >
            Pièces d'évaluation requises par la commission :
          </p>
          <div className="flex flex-wrap gap-2">
            {poste.criteres.map((crit) => (
              <span
                key={crit.type_document}
                className="chip chip-neutral"
                style={{ fontSize: "11px", padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: "5px" }}
              >
                <FileText size={12} aria-hidden="true" /> {crit.type_document} (Coeff. {crit.coefficient}, Min.{" "}
                {crit.seuil_minimal}/20)
              </span>
            ))}
            <span
              className="chip chip-magic"
              style={{ fontSize: "11px", padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: "5px" }}
            >
              <Lock size={12} aria-hidden="true" /> Casier judiciaire obligatoire
            </span>
          </div>
        </div>
      </Card>

      {/* Stepper visuel multi-étapes */}
      <div className="mb-6 flex items-center justify-between text-xs font-bold px-2" style={{ color: "var(--ink-soft)" }}>
        <div className="flex items-center gap-2">
          <span
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              background: "var(--primary)",
              color: "white",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            1
          </span>
          <span>Motivation</span>
        </div>
        <div style={{ flex: 1, height: "2px", background: "var(--border)", margin: "0 12px" }} />
        <div className="flex items-center gap-2">
          <span
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              background: "var(--primary)",
              color: "white",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            2
          </span>
          <span>Justificatifs</span>
        </div>
        <div style={{ flex: 1, height: "2px", background: "var(--border)", margin: "0 12px" }} />
        <div className="flex items-center gap-2">
          <span
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              background: "var(--primary)",
              color: "white",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            3
          </span>
          <span>Casier judiciaire</span>
        </div>
      </div>

      <div className="mb-6">
        <ErrorBanner>{erreur}</ErrorBanner>
      </div>

      {/* Formulaire complet */}
      <form onSubmit={soumettre} className="space-y-6">
        {/* Étape 1 : Motivation et Liens */}
        <Card>
          <SectionHead
            eyebrow="Étape 1"
            title="Motivation & Références"
            desc="Présentez brièvement vos atouts pédagogiques et vos références en ligne."
          />
          <div className="space-y-4">
            <Field
              label="Lettre ou note de motivation"
              helper="Détaillez vos méthodes d'enseignement, vos expériences passées et votre projet pour la classe."
            >
              <TextArea
                placeholder="Madame, Monsieur les membres du conseil pédagogique..."
                value={lettreMotivation}
                onChange={(e) => setLettreMotivation(e.target.value)}
                rows={4}
              />
            </Field>

            <Field
              label="Lien externe ou portfolio pédagogique (facultatif)"
              helper="URL vers votre CV en ligne, LinkedIn, mémoire ou blog pédagogique"
            >
              <TextInput
                type="url"
                placeholder="https://..."
                value={lienPortfolio}
                onChange={(e) => setLienPortfolio(e.target.value)}
              />
            </Field>
          </div>
        </Card>

        {/* Étape 2 : Justificatifs demandés par le poste */}
        <Card>
          <SectionHead
            eyebrow="Étape 2"
            title="Dossier de candidature & Documents"
            desc="Téléversez les fichiers au format PDF ou image requis pour l'évaluation par l'IA et la commission."
          />

          <div className="space-y-4">
            {poste.criteres.map((critere) => {
              const fileSelected = fichiers[critere.type_document];

              return (
                <div
                  key={critere.type_document}
                  style={{
                    border: "2px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-4)",
                    background: fileSelected
                      ? "var(--surface-2)"
                      : "var(--surface)",
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-sm" style={{ color: "var(--ink)" }}>
                      {critere.type_document}
                    </span>
                    <span
                      className="text-xs"
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--ink-soft)",
                      }}
                    >
                      Pondération : Coeff {critere.coefficient} (Seuil {critere.seuil_minimal}/20)
                    </span>
                  </div>

                  <Field label={`Fichier pour ${critere.type_document}`} required>
                    <div className="flex items-center gap-3">
                      <input
                        type="file"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            setFichiers((prev) => ({
                              ...prev,
                              [critere.type_document]: file,
                            }));
                          }
                        }}
                        className="field-input text-sm cursor-pointer"
                        required
                      />
                      {fileSelected && (
                        <div
                          className="shrink-0 flex items-center gap-1 text-xs font-bold"
                          style={{ color: "var(--primary-deep)" }}
                        >
                          <CheckCircle2 size={16} /> Prêt
                        </div>
                      )}
                    </div>
                  </Field>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Étape 3 : Casier judiciaire (Art. 395) */}
        <Card>
          <SectionHead
            eyebrow="Étape 3"
            title="Extrait de casier judiciaire (Art. 395)"
            desc="Exigence légale stricte pour tout encadrement d'élèves mineurs au sein de la plateforme."
          />

          <div
            className="mb-4 p-3 rounded-[var(--radius-md)] flex items-start gap-3"
            style={{
              background: "var(--info-tint)",
              border: "1.5px solid var(--info-deep)",
              color: "var(--info-deep)",
            }}
          >
            <ShieldCheck size={20} className="shrink-0 mt-0.5" />
            <div className="text-xs leading-relaxed">
              <strong className="block mb-0.5">Confidentialité garantie :</strong>
              Conformément à l'Article 395 du code éducatif, ce document est
              chiffré à la source, stocké localement et n'est jamais divulgué
              publiquement.
            </div>
          </div>

          <Field label="Casier judiciaire (bulletin n°3 récent)" required>
            <div className="flex items-center gap-3">
              <input
                type="file"
                onChange={(e) => setCasierJudiciaire(e.target.files?.[0] ?? null)}
                className="field-input text-sm cursor-pointer"
                required
              />
              {casierJudiciaire && (
                <div
                  className="shrink-0 flex items-center gap-1 text-xs font-bold"
                  style={{ color: "var(--primary-deep)" }}
                >
                  <CheckCircle2 size={16} /> Fichier joint
                </div>
              )}
            </div>
          </Field>
        </Card>

        {/* Actions de validation */}
        <div className="flex flex-col-reverse sm:flex-row items-center justify-between gap-4 pt-4">
          <Btn
            type="button"
            variant="ghost"
            size="md"
            onClick={() => navigate(-1)}
            disabled={enCours}
          >
            Annuler
          </Btn>

          <Btn
            type="submit"
            variant="primary"
            size="lg"
            loading={enCours}
            leftIcon={<Send size={18} />}
            className="w-full sm:w-auto"
          >
            {enCours ? "Envoi du dossier..." : "Envoyer ma candidature"}
          </Btn>
        </div>
      </form>
    </div>
  );
}
