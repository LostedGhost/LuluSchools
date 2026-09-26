import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { creerClasse, listerClasses } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { ClasseOut, PolitiqueDepassement } from "../../types/api";
import { AffectationsClasseManager } from "../../components/AffectationsClasseManager";
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
import { PlusCircle, RefreshCw, Users, Layers, School, GraduationCap } from "lucide-react";
import { estRempli, erreurEntierPositif } from "../../utils/validation";

const LIBELLES_POLITIQUE: Record<
  PolitiqueDepassement,
  { label: string; tone: "info" | "magic" | "neutral" }
> = {
  ordre_arrivee: { label: "Ordre d'arrivée", tone: "info" },
  notes_concours: { label: "Notes de concours", tone: "magic" },
  tirage_sort: { label: "Tirage au sort", tone: "neutral" },
};

export function ClassesPage() {
  const etablissement = useAdminEtab();
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [niveau, setNiveau] = useState("");
  const [capacite, setCapacite] = useState(30);
  const [politique, setPolitique] = useState<PolitiqueDepassement>("ordre_arrivee");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [chargement, setChargement] = useState(true);
  const [champErreurs, setChampErreurs] = useState<{ niveau?: string; capacite?: string }>({});
  const [classeOuverteId, setClasseOuverteId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    listerClasses(etablissement.id)
      .then((res) => {
        setClasses(res.data);
        setErreur(null);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);

    const erreurs: typeof champErreurs = {};
    if (!estRempli(niveau)) erreurs.niveau = "Nom ou niveau de la classe requis.";
    const erreurCap = erreurEntierPositif(capacite, { min: 1, max: 200 });
    if (erreurCap) erreurs.capacite = erreurCap;
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await creerClasse(etablissement.id, {
        niveau: niveau.trim(),
        capacite,
        politique_depassement: politique,
      });
      setSucces(`Classe "${niveau.trim()}" créée avec succès !`);
      setNiveau("");
      setCapacite(30);
      setPolitique("ordre_arrivee");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer la classe."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="page-content">
      {/* En-tête de page */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageTitle eyebrow="Admin Établissement">Classes et niveaux</PageTitle>
        <div className="flex items-center gap-2">
          <Btn
            variant="outline"
            size="sm"
            onClick={charger}
            loading={chargement}
            leftIcon={<RefreshCw size={14} />}
          >
            Actualiser
          </Btn>
          <Badge tone="magic">{classes.length} classes actives</Badge>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {/* Formulaire de création de classe */}
      <Card className="mb-8 anim-float-in">
        <div className="mb-4">
          <SectionHead
            eyebrow="Configuration"
            title="Créer une nouvelle classe"
            desc="Définissez le niveau, l'effectif maximal et la règle de sélection des inscriptions."
          />
        </div>

        <form onSubmit={soumettre} noValidate className="space-y-4">
          <div className="grid-2">
            <Field
              label="Niveau ou Nom de la classe"
              helper="Ex : 6ème A, Seconde C, CM2, CP1"
              required
              error={champErreurs.niveau}
            >
              <TextInput
                placeholder="Ex : 6ème A"
                value={niveau}
                onChange={(e) => setNiveau(e.target.value)}
              />
            </Field>

            <Field
              label="Capacité maximale"
              helper="Nombre de places ouvertes aux élèves (1 à 200)"
              required
              error={champErreurs.capacite}
            >
              <TextInput
                type="number"
                min={1}
                max={200}
                value={capacite}
                onChange={(e) => setCapacite(Number(e.target.value))}
              />
            </Field>
          </div>

          <div className="grid-2">
            <Field
              label="Politique de dépassement"
              helper="Critère de sélection en cas de surplus d'inscriptions"
            >
              <Select
                value={politique}
                onChange={(e) =>
                  setPolitique(e.target.value as PolitiqueDepassement)
                }
              >
                <option value="ordre_arrivee">
                  Ordre d'arrivée (Premier arrivé, premier inscrit)
                </option>
                <option value="notes_concours">
                  Notes de concours (Classement au mérite)
                </option>
                <option value="tirage_sort">
                  Tirage au sort (Attribution aléatoire)
                </option>
              </Select>
            </Field>

            <div className="flex items-end justify-start sm:justify-end pb-1">
              <Btn
                type="submit"
                variant="primary"
                size="md"
                loading={enCours}
                leftIcon={<PlusCircle size={16} />}
                className="w-full sm:w-auto"
              >
                Créer la classe
              </Btn>
            </div>
          </div>
        </form>
      </Card>

      {/* Liste des classes */}
      <div className="mb-4">
        <SectionHead
          title="Classes et promotions enregistrées"
          desc="Consultez la répartition des capacités d'accueil par niveau d'enseignement."
        />
      </div>

      {chargement && classes.length === 0 ? (
        <div className="grid-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : classes.length === 0 ? (
        <Card variant="soft" className="anim-float-in">
          <EmptyState
            icon={<School size={24} />}
            title="Aucune classe enregistrée"
            desc="Vous n'avez pas encore configuré de classe pour cet établissement. Utilisez le formulaire ci-dessus pour créer votre première promotion."
          />
        </Card>
      ) : (
        <div className="grid-2">
          {classes.map((c, idx) => {
            const pol = LIBELLES_POLITIQUE[c.politique_depassement] || {
              label: c.politique_depassement,
              tone: "neutral" as const,
            };
            const delayClass = `delay-${(idx % 3) + 1}`;

            return (
              <Card
                key={c.id}
                className={`anim-float-in ${delayClass} card-hover flex flex-col justify-between`}
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-2">
                      <div
                        style={{
                          width: "36px",
                          height: "36px",
                          borderRadius: "var(--radius-sm)",
                          background: "var(--primary-tint)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "var(--primary-deep)",
                        }}
                      >
                        <Layers size={20} />
                      </div>
                      <div>
                        <h3
                          className="m-0"
                          style={{
                            fontFamily: "var(--font-display)",
                            fontSize: "var(--text-xl)",
                            fontWeight: 700,
                            color: "var(--ink)",
                          }}
                        >
                          {c.niveau}
                        </h3>
                        <span
                          className="text-xs"
                          style={{
                            fontFamily: "var(--font-mono)",
                            color: "var(--ink-faint)",
                          }}
                        >
                          ID: {c.id.slice(0, 8)}
                        </span>
                      </div>
                    </div>

                    <Badge tone={pol.tone}>
                      {pol.label}
                    </Badge>
                  </div>
                </div>

                <div
                  className="mt-4 pt-3 flex items-center justify-between"
                  style={{ borderTop: "2px dashed var(--border)" }}
                >
                  <div className="flex items-center gap-2">
                    <Users size={16} style={{ color: "var(--ink-soft)" }} />
                    <span
                      className="text-sm font-semibold"
                      style={{ color: "var(--ink-soft)" }}
                    >
                      Capacité :{" "}
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontWeight: 700,
                          color: "var(--primary-deep)",
                        }}
                      >
                        {c.capacite} places
                      </span>
                    </span>
                  </div>

                  <span
                    className="text-xs"
                    style={{ color: "var(--ink-faint)" }}
                  >
                    Ouvert aux inscriptions
                  </span>
                </div>

                <Btn
                  variant="ghost"
                  size="sm"
                  className="mt-2 w-full"
                  leftIcon={<GraduationCap size={14} />}
                  onClick={() => setClasseOuverteId(classeOuverteId === c.id ? null : c.id)}
                >
                  {classeOuverteId === c.id ? "Masquer les enseignants affectés" : "Gérer les enseignants affectés"}
                </Btn>
                {classeOuverteId === c.id && (
                  <AffectationsClasseManager classeId={c.id} etablissementId={etablissement.id} />
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
