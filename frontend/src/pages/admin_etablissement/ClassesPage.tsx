import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { creerClasse, listerClasses, reconduireClasses } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { ClasseOut, PolitiqueDepassement } from "../../types/api";
import { AffectationsClasseManager } from "../../components/AffectationsClasseManager";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import {
  Badge,
  Btn,
  Card,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  Select,
  SuccessBanner,
  TextInput,
} from "../../components/ui";
import { PlusCircle, RefreshCw, Users, Layers, GraduationCap, Repeat } from "lucide-react";
import { estRempli, erreurEntierPositif } from "../../utils/validation";

const LIBELLES_POLITIQUE: Record<
  PolitiqueDepassement,
  { label: string; tone: "info" | "magic" | "neutral" }
> = {
  ordre_arrivee: { label: "Ordre d'arrivée", tone: "info" },
  notes_concours: { label: "Notes de concours", tone: "magic" },
  tirage_sort: { label: "Tirage au sort", tone: "neutral" },
};

// UC-43/58 (lot admin etablissement) : taxonomie nationale reprise de scripts/seed_mega.py
// - niveau reste un <select> ferme cote frontend, mais une colonne texte libre cote
// backend (aucune enumeration DB) : la filiere/serie (A1/B/C/D, F2/G1...) et les
// filieres universitaires ne sont PAS standardisables globalement, elles restent en
// texte libre avec autocompletion (voir plus bas).
const NIVEAUX_PAR_TYPE: Record<"EP" | "ES" | "UP", string[]> = {
  EP: ["Maternelle 1", "Maternelle 2", "CI", "CP", "CE1", "CE2", "CM1", "CM2"],
  ES: ["6ème", "5ème", "4ème", "3ème", "2nde", "1ère", "Terminale"],
  UP: ["1ère année de Licence", "2ème année de Licence", "3ème année de Licence", "1ère année de Master", "2ème année de Master"],
};

function anneeAcademiqueCourante(): string {
  const aujourdhui = new Date();
  const premiere = aujourdhui.getMonth() >= 8 ? aujourdhui.getFullYear() : aujourdhui.getFullYear() - 1;
  return `${premiere}-${premiere + 1}`;
}

export function ClassesPage() {
  const etablissement = useAdminEtab();
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [niveau, setNiveau] = useState("");
  const [filiere, setFiliere] = useState("");
  const [anneeAcademique, setAnneeAcademique] = useState("");
  const [capacite, setCapacite] = useState(30);
  const [politique, setPolitique] = useState<PolitiqueDepassement>("ordre_arrivee");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [chargement, setChargement] = useState(true);
  const [champErreurs, setChampErreurs] = useState<{ niveau?: string; capacite?: string }>({});
  const [classeOuverteId, setClasseOuverteId] = useState<string | null>(null);

  const [filtreAnnee, setFiltreAnnee] = useState("");
  const [selection, setSelection] = useState<Set<string>>(new Set());
  const [nouvelleAnneeReconduction, setNouvelleAnneeReconduction] = useState("");
  const [enCoursReconduction, setEnCoursReconduction] = useState(false);

  const niveauxDisponibles = NIVEAUX_PAR_TYPE[etablissement.type];

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

  const anneesConnues = useMemo(
    () => Array.from(new Set(classes.map((c) => c.annee_academique))).sort().reverse(),
    [classes],
  );
  const filieresConnues = useMemo(
    () => Array.from(new Set(classes.map((c) => c.filiere).filter((f): f is string => !!f))).sort(),
    [classes],
  );
  const classesFiltrees = useMemo(
    () => (filtreAnnee ? classes.filter((c) => c.annee_academique === filtreAnnee) : classes),
    [classes, filtreAnnee],
  );

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);

    const erreurs: typeof champErreurs = {};
    if (!estRempli(niveau)) erreurs.niveau = "Niveau requis.";
    const erreurCap = erreurEntierPositif(capacite, { min: 1, max: 200 });
    if (erreurCap) erreurs.capacite = erreurCap;
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await creerClasse(etablissement.id, {
        niveau,
        filiere: filiere.trim() || null,
        annee_academique: anneeAcademique.trim() || undefined,
        capacite,
        politique_depassement: politique,
      });
      setSucces(`Classe "${niveau}${filiere ? ` ${filiere}` : ""}" créée avec succès !`);
      setNiveau("");
      setFiliere("");
      setCapacite(30);
      setPolitique("ordre_arrivee");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer la classe."));
    } finally {
      setEnCours(false);
    }
  };

  const reconduire = async () => {
    if (!estRempli(nouvelleAnneeReconduction)) {
      setErreur("Précisez l'année académique cible pour la reconduction.");
      return;
    }
    setEnCoursReconduction(true);
    setErreur(null);
    try {
      const res = await reconduireClasses(etablissement.id, Array.from(selection), nouvelleAnneeReconduction.trim());
      setSucces(`${res.data.length} classe(s) reconduite(s) vers ${nouvelleAnneeReconduction.trim()}.`);
      setSelection(new Set());
      setNouvelleAnneeReconduction("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de reconduire ces classes."));
    } finally {
      setEnCoursReconduction(false);
    }
  };

  const colonnes: DataTableColumn<ClasseOut>[] = [
    {
      key: "niveau",
      header: "Classe",
      render: (c) => (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Layers size={16} style={{ color: "var(--primary-deep)" }} />
          <span style={{ fontWeight: 600 }}>{c.niveau}{c.filiere ? ` ${c.filiere}` : ""}</span>
        </div>
      ),
    },
    { key: "annee", header: "Année académique", render: (c) => <Badge tone="info">{c.annee_academique}</Badge> },
    {
      key: "capacite",
      header: "Capacité",
      render: (c) => (
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <Users size={14} /> {c.capacite}
        </span>
      ),
    },
    {
      key: "politique",
      header: "Politique de dépassement",
      render: (c) => {
        const pol = LIBELLES_POLITIQUE[c.politique_depassement] ?? { label: c.politique_depassement, tone: "neutral" as const };
        return <Badge tone={pol.tone}>{pol.label}</Badge>;
      },
    },
    {
      key: "actions",
      header: "",
      render: (c) => (
        <div style={{ display: "flex", gap: "8px" }}>
          <Link to={`/admin-etablissement/console?classe_id=${c.id}`}>
            <Btn variant="ghost" size="sm" leftIcon={<GraduationCap size={14} />}>Console</Btn>
          </Link>
          <Btn
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); setClasseOuverteId(classeOuverteId === c.id ? null : c.id); }}
          >
            {classeOuverteId === c.id ? "Masquer enseignants" : "Enseignants"}
          </Btn>
        </div>
      ),
    },
  ];

  return (
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageTitle eyebrow="Admin Établissement">Classes et niveaux</PageTitle>
        <div className="flex items-center gap-2">
          <Btn variant="outline" size="sm" onClick={charger} loading={chargement} leftIcon={<RefreshCw size={14} />}>
            Actualiser
          </Btn>
          <Badge tone="magic">{classes.length} classe(s)</Badge>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      <Card className="mb-8 anim-float-in">
        <SectionHead
          eyebrow="Configuration"
          title="Créer une nouvelle classe"
          desc="Le niveau dépend du type de votre établissement ; la filière/section (A, B, C... ou une filière universitaire) reste libre."
        />
        <form onSubmit={soumettre} noValidate className="space-y-4" style={{ marginTop: "var(--space-4)" }}>
          <div className="grid-3">
            <Field label="Niveau" required error={champErreurs.niveau}>
              <Select value={niveau} onChange={(e) => setNiveau(e.target.value)}>
                <option value="">— Choisir —</option>
                {niveauxDisponibles.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </Select>
            </Field>
            <Field label={etablissement.type === "UP" ? "Filière" : "Filière / section (A, B, C...)"}>
              <TextInput
                value={filiere}
                onChange={(e) => setFiliere(e.target.value)}
                placeholder={etablissement.type === "UP" ? "Ex. Informatique de Gestion" : "Ex. A"}
                list="filieres-connues"
              />
              <datalist id="filieres-connues">
                {filieresConnues.map((f) => <option key={f} value={f} />)}
              </datalist>
            </Field>
            <Field label="Année académique" helper={`Par défaut : ${anneeAcademiqueCourante()} (ou la rentrée ouverte)`}>
              <TextInput value={anneeAcademique} onChange={(e) => setAnneeAcademique(e.target.value)} placeholder={anneeAcademiqueCourante()} />
            </Field>
          </div>
          <div className="grid-2">
            <Field label="Capacité maximale" required error={champErreurs.capacite}>
              <TextInput type="number" min={1} max={200} value={capacite} onChange={(e) => setCapacite(Number(e.target.value))} />
            </Field>
            <Field label="Politique de dépassement">
              <Select value={politique} onChange={(e) => setPolitique(e.target.value as PolitiqueDepassement)}>
                <option value="ordre_arrivee">Ordre d'arrivée</option>
                <option value="notes_concours">Notes de concours</option>
                <option value="tirage_sort">Tirage au sort</option>
              </Select>
            </Field>
          </div>
          <Btn type="submit" variant="primary" loading={enCours} leftIcon={<PlusCircle size={16} />}>
            Créer la classe
          </Btn>
        </form>
      </Card>

      <SectionHead
        title="Classes et promotions enregistrées"
        desc="Sélectionnez des classes pour les reconduire vers une nouvelle année académique."
      />

      <DataTable
        columns={colonnes}
        rows={classesFiltrees}
        rowKey={(c) => c.id}
        loading={chargement}
        emptyTitle="Aucune classe enregistrée"
        emptyDesc="Utilisez le formulaire ci-dessus pour créer votre première classe."
        filters={
          <Select value={filtreAnnee} onChange={(e) => setFiltreAnnee(e.target.value)} style={{ width: "200px" }}>
            <option value="">Toutes les années</option>
            {anneesConnues.map((a) => <option key={a} value={a}>{a}</option>)}
          </Select>
        }
        selectable
        selectedIds={selection}
        onSelectionChange={setSelection}
        bulkActions={[
          {
            label: "Reconduire",
            icon: <Repeat size={14} />,
            variant: "primary",
            loading: enCoursReconduction,
            onClick: reconduire,
          },
        ]}
      />

      {selection.size > 0 && (
        <div style={{ marginTop: "10px", maxWidth: "320px" }}>
          <Field label="Nouvelle année académique" helper="Ex. 2027-2028">
            <TextInput value={nouvelleAnneeReconduction} onChange={(e) => setNouvelleAnneeReconduction(e.target.value)} placeholder={anneeAcademiqueCourante()} />
          </Field>
        </div>
      )}

      {classeOuverteId && (
        <div style={{ marginTop: "var(--space-4)" }}>
          <AffectationsClasseManager classeId={classeOuverteId} etablissementId={etablissement.id} />
        </div>
      )}
    </div>
  );
}
