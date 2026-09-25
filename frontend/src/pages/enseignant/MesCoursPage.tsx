import { useEffect, useState, type FormEvent } from "react";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import { creerQuiz, listerCours, listerQuiz, obtenirLienFichierCours, publierCours } from "../../api/pedagogie";
import { mesContrats } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ClasseOut, CoursOut, EtablissementOut, FormatCours, QuizOut } from "../../types/api";
import {
  Btn,
  Field,
  TextInput,
  TextArea,
  Select,
  ErrorBanner,
  Badge,
  SectionHead,
  EmptyState,
  Skeleton,
} from "../../components/ui";
import { School, BookOpen, ExternalLink } from "lucide-react";
import { estRempli } from "../../utils/validation";

const LABEL_FORMAT: Record<FormatCours, string> = {
  texte: "Texte",
  pdf: "Document PDF",
  audio: "Audio",
  video: "Vidéo",
};

const ACCEPT_PAR_FORMAT: Record<FormatCours, string | undefined> = {
  texte: undefined,
  pdf: "application/pdf",
  audio: "audio/*",
  video: "video/*",
};

const MATIERES = [
  "Mathématiques",
  "Français",
  "Histoire-Géographie",
  "Sciences de la Vie et de la Terre (SVT)",
  "Physique-Chimie",
  "Philosophie",
  "Anglais",
  "Espagnol",
  "Informatique / Technologie",
  "Sciences Économiques et Sociales",
  "Éducation Civique",
  "Autre",
];

export function MesCoursPage() {
  const [etablissementIds, setEtablissementIds] = useState<string[]>([]);
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [classeId, setClasseId] = useState("");
  const [formClasseId, setFormClasseId] = useState("");
  const [cours, setCours] = useState<CoursOut[]>([]);
  const [quizParCours, setQuizParCours] = useState<Record<string, QuizOut[]>>({});

  const [titre, setTitre] = useState("");
  const [chapitre, setChapitre] = useState("");
  const [format, setFormat] = useState<FormatCours>("texte");
  const [contenuTexte, setContenuTexte] = useState("");
  const [fichier, setFichier] = useState<File | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [formErreur, setFormErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [chargementCours, setChargementCours] = useState(false);
  const [generatingQuizId, setGeneratingQuizId] = useState<string | null>(null);
  const [viewingCoursId, setViewingCoursId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [chargementLienId, setChargementLienId] = useState<string | null>(null);

  useEffect(() => {
    mesContrats()
      .then((res) => {
        const ids = Array.from(
          new Set(res.data.filter((c) => c.statut === "signe").map((c) => c.etablissement_id)),
        );
        setEtablissementIds(ids);
        if (ids.length > 0) {
          setEtablissementId((prev) => prev || ids[0]);
        }
      })
      .catch((err) => setErreur(messageErreur(err)));
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!etablissementId) {
      setClasses([]);
      return;
    }
    listerClasses(etablissementId)
      .then((res) => {
        setClasses(res.data);
        if (res.data.length > 0) {
          setClasseId((prev) => prev || res.data[0].id);
          setFormClasseId((prev) => prev || res.data[0].id);
        }
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  const chargerCours = () => {
    if (!classeId) {
      setCours([]);
      return;
    }
    setChargementCours(true);
    listerCours(classeId)
      .then(async (res) => {
        setCours(res.data);
        const entrees = await Promise.all(
          res.data.map(async (c) => [c.id, (await listerQuiz(c.id)).data] as const),
        );
        setQuizParCours(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargementCours(false));
  };

  useEffect(chargerCours, [classeId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(titre)) {
      setFormErreur("Veuillez saisir un titre pour le cours.");
      return;
    }
    if (!estRempli(chapitre)) {
      setFormErreur("Veuillez sélectionner une matière.");
      return;
    }
    const targetClasseId = formClasseId || classeId;
    if (!targetClasseId) {
      setFormErreur("Veuillez sélectionner une classe.");
      return;
    }
    if (format !== "texte" && !fichier) {
      setFormErreur(`Veuillez joindre un fichier ${LABEL_FORMAT[format].toLowerCase()}.`);
      return;
    }
    if (format === "texte" && !contenuTexte.trim()) {
      setFormErreur("Veuillez saisir le contenu du cours.");
      return;
    }
    setFormErreur(null);
    setEnCours(true);
    try {
      await publierCours(
        targetClasseId,
        titre,
        chapitre,
        format,
        format === "texte" ? contenuTexte : undefined,
        format !== "texte" ? fichier ?? undefined : undefined,
      );
      setTitre("");
      setChapitre("");
      setContenuTexte("");
      setFichier(null);
      setFormat("texte");
      setShowForm(false);
      if (classeId !== targetClasseId) {
        setClasseId(targetClasseId);
      } else {
        chargerCours();
      }
    } catch (err) {
      setFormErreur(messageErreur(err, "Impossible de publier le cours."));
    } finally {
      setEnCours(false);
    }
  };

  const voirFichier = async (coursId: string) => {
    setChargementLienId(coursId);
    setErreur(null);
    try {
      const res = await obtenirLienFichierCours(coursId);
      window.open(res.data.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir ce fichier pour le moment."));
    } finally {
      setChargementLienId(null);
    }
  };

  const genererQuiz = async (coursId: string) => {
    setErreur(null);
    setGeneratingQuizId(coursId);
    try {
      await creerQuiz(coursId, 80, 5);
      chargerCours();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de générer le quiz."));
    } finally {
      setGeneratingQuizId(null);
    }
  };

  const handleToggleForm = () => {
    if (!showForm && !formClasseId && classeId) {
      setFormClasseId(classeId);
    }
    setShowForm((prev) => !prev);
  };

  return (
    <div className="page-content">
      {/* Page Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "32px" }}>
        <div>
          <p className="text-eyebrow" style={{ marginBottom: "6px" }}>Espace Enseignant</p>
          <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Mes cours</h1>
        </div>
        <button className="btn btn-primary" onClick={handleToggleForm}>
          {showForm ? "Fermer le formulaire" : "+ Créer un cours"}
        </button>
      </div>

      {erreur && (
        <div style={{ marginBottom: "24px" }}>
          <ErrorBanner>{erreur}</ErrorBanner>
        </div>
      )}

      {/* Creation form (toggle visible) */}
      {showForm && (
        <div className="card anim-slide-up" style={{ marginBottom: "24px" }}>
          <SectionHead
            title="Nouveau cours"
            desc="Remplissez les informations ci-dessous pour publier un nouveau cours."
          />
          {formErreur && (
            <div style={{ marginTop: "16px" }}>
              <ErrorBanner>{formErreur}</ErrorBanner>
            </div>
          )}
          <form onSubmit={soumettre} style={{ marginTop: "20px" }}>
            <div className="grid-2">
              <Field label="Titre du cours" required>
                <TextInput
                  placeholder="Ex. Introduction aux équations différentielles"
                  value={titre}
                  onChange={(e: any) => setTitre(e.target.value)}
                  required
                />
              </Field>

              <Field label="Matière" required>
                <Select
                  value={chapitre}
                  onChange={(e: any) => setChapitre(e.target.value)}
                  required
                >
                  <option value="">Sélectionner une matière...</option>
                  {MATIERES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </Select>
              </Field>

              <Field label="Classe / Niveau" required>
                <Select
                  value={formClasseId}
                  onChange={(e: any) => {
                    setFormClasseId(e.target.value);
                    if (!classeId) setClasseId(e.target.value);
                  }}
                  required
                >
                  <option value="">Sélectionner une classe...</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.niveau}
                    </option>
                  ))}
                </Select>
              </Field>

              <Field label="Format" required>
                <Select
                  value={format}
                  onChange={(e: any) => {
                    setFormat(e.target.value as FormatCours);
                    setFichier(null);
                    setFormErreur(null);
                  }}
                  required
                >
                  {(Object.keys(LABEL_FORMAT) as FormatCours[]).map((f) => (
                    <option key={f} value={f}>
                      {LABEL_FORMAT[f]}
                    </option>
                  ))}
                </Select>
              </Field>

              {format === "texte" ? (
                <div style={{ gridColumn: "1 / -1" }}>
                  <Field
                    label="Contenu"
                    required
                    helper="Le contenu texte servira de base à l'IA pour générer automatiquement des quiz d'évaluation."
                  >
                    <TextArea
                      rows={5}
                      placeholder="Saisissez ou collez le contenu du cours..."
                      value={contenuTexte}
                      onChange={(e: any) => setContenuTexte(e.target.value)}
                    />
                  </Field>
                </div>
              ) : (
                <div style={{ gridColumn: "1 / -1" }}>
                  <Field
                    label={`Fichier ${LABEL_FORMAT[format].toLowerCase()}`}
                    required
                    helper="50 Mo max (200 Mo pour une vidéo)."
                  >
                    <input
                      type="file"
                      accept={ACCEPT_PAR_FORMAT[format]}
                      onChange={(e) => setFichier(e.target.files?.[0] ?? null)}
                      className="field-input"
                      required
                    />
                  </Field>
                </div>
              )}

              <div
                style={{
                  gridColumn: "1 / -1",
                  display: "flex",
                  gap: "12px",
                  alignItems: "center",
                  marginTop: "8px",
                }}
              >
                <Btn variant="primary" type="submit" loading={enCours}>
                  Publier
                </Btn>
                <Btn
                  variant="ghost"
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setFormErreur(null);
                  }}
                >
                  Annuler
                </Btn>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Class filter card */}
      <div
        className="card card-soft"
        style={{
          display: "flex",
          gap: "16px",
          marginBottom: "28px",
          flexWrap: "wrap",
          alignItems: "flex-end",
        }}
      >
        <div style={{ flex: 1, minWidth: "220px" }}>
          <Field label="Établissement">
            <Select
              value={etablissementId}
              onChange={(e: any) => {
                setEtablissementId(e.target.value);
                setClasseId("");
                setFormClasseId("");
              }}
            >
              <option value="">Sélectionner un établissement...</option>
              {etablissementIds.map((id) => (
                <option key={id} value={id}>
                  {etablissements.find((e) => e.id === id)?.nom ?? id}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <div style={{ flex: 1, minWidth: "200px" }}>
          <Field label="Classe / Niveau">
            <Select
              value={classeId}
              onChange={(e: any) => {
                setClasseId(e.target.value);
                setFormClasseId(e.target.value);
              }}
              disabled={!etablissementId}
            >
              <option value="">Toutes les classes...</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.niveau}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </div>

      {/* Course List / Empty States */}
      {!classeId ? (
        <EmptyState
          icon={<School size={24} />}
          title="Sélectionnez une classe"
          desc="Veuillez choisir un établissement et une classe pour afficher les cours."
        />
      ) : chargementCours ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Skeleton height="88px" />
          <Skeleton height="88px" />
          <Skeleton height="88px" />
        </div>
      ) : cours.length === 0 ? (
        <EmptyState
          icon={<BookOpen size={24} />}
          title="Aucun cours"
          desc="Créez votre premier cours et publiez-le pour vos élèves."
          action={
            !showForm ? (
              <Btn
                variant="primary"
                onClick={handleToggleForm}
                style={{ marginTop: "16px" }}
              >
                + Créer un cours
              </Btn>
            ) : undefined
          }
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {cours.map((c, index) => {
            const classeAssociee = classes.find((cl) => cl.id === c.classe_id);
            const nomClasse = classeAssociee ? classeAssociee.niveau : "Classe";
            const isViewing = viewingCoursId === c.id;

            return (
              <div
                key={c.id}
                className={`card card-hover anim-float-in delay-${(index % 5) + 1}`}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "16px",
                    flexWrap: "wrap",
                  }}
                >
                  {/* Left: colored icon box with course details */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "16px",
                      minWidth: 0,
                      flex: 1,
                    }}
                  >
                    <div
                      style={{
                        width: "48px",
                        height: "48px",
                        minWidth: "48px",
                        borderRadius: "var(--radius-md)",
                        backgroundColor: "var(--magic-tint)",
                        color: "var(--magic-deep)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <BookOpen size={22} aria-hidden="true" />
                    </div>

                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          flexWrap: "wrap",
                          marginBottom: "4px",
                        }}
                      >
                        <h3
                          className="font-display font-bold"
                          style={{
                            fontFamily: "var(--font-display)",
                            fontWeight: 700,
                            fontSize: "1.125rem",
                            color: "var(--ink)",
                            margin: 0,
                          }}
                        >
                          {c.titre}
                        </h3>
                        <Badge tone="success">Publié</Badge>
                      </div>
                      <p
                        className="font-mono text-sm"
                        style={{ color: "var(--ink-faint)", margin: 0 }}
                      >
                        {c.chapitre ? `${c.chapitre} • ` : ""}{nomClasse}
                      </p>
                    </div>
                  </div>

                  {/* Right side: Actions */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      flexShrink: 0,
                    }}
                  >
                    <Btn
                      variant="outline"
                      size="sm"
                      loading={generatingQuizId === c.id}
                      onClick={() => genererQuiz(c.id)}
                    >
                      Quiz IA
                    </Btn>
                    <Btn
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setViewingCoursId(isViewing ? null : c.id)
                      }
                    >
                      {isViewing ? "Masquer" : "Voir"}
                    </Btn>
                  </div>
                </div>

                {/* Quizzes generated */}
                {quizParCours[c.id] && quizParCours[c.id].length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      alignItems: "center",
                      gap: "8px",
                      marginTop: "14px",
                      paddingTop: "12px",
                      borderTop: "1px dashed var(--border)",
                    }}
                  >
                    <span className="text-eyebrow" style={{ fontSize: "0.75rem" }}>
                      Quiz générés :
                    </span>
                    {quizParCours[c.id].map((quiz, idx) => (
                      <Badge key={quiz.id} tone="info">
                        Quiz {idx + 1} ({quiz.questions.length} questions)
                      </Badge>
                    ))}
                  </div>
                )}

                {/* Detailed view preview */}
                {isViewing && (
                  <div
                    className="anim-slide-up"
                    style={{
                      marginTop: "16px",
                      paddingTop: "16px",
                      borderTop: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "10px",
                      }}
                    >
                      <span className="text-eyebrow">Détails du cours</span>
                      <Badge tone="neutral">Format : {c.format}</Badge>
                    </div>
                    <div
                      style={{
                        background: "var(--surface-2)",
                        padding: "16px",
                        borderRadius: "var(--radius-md)",
                        color: "var(--ink)",
                        fontSize: "0.95rem",
                      }}
                    >
                      <p style={{ margin: 0 }}>
                        <strong>Matière :</strong> {c.chapitre || "Non renseignée"}
                      </p>
                      <p style={{ margin: "6px 0 0" }}>
                        <strong>Classe :</strong> {nomClasse}
                      </p>
                      {c.lulufiles_file_id && (
                        <div style={{ marginTop: "10px" }}>
                          <Btn
                            variant="outline"
                            size="sm"
                            loading={chargementLienId === c.id}
                            onClick={() => voirFichier(c.id)}
                            rightIcon={<ExternalLink size={14} />}
                          >
                            Voir le fichier
                          </Btn>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
