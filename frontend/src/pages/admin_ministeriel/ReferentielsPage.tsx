import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  creerReferentiel,
  listerReferentiels,
  modifierReferentiel,
  validerReferentiel,
  validerReferentielsEnLot,
  type ReferentielOut,
} from "../../api/evaluations_gouvernance";
import { messageErreur } from "../../api/client";
import { Badge, Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, Select, TextInput } from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Check, CheckCircle2, Pencil, X } from "lucide-react";
import { estRempli } from "../../utils/validation";

const TONE_STATUT: Record<ReferentielOut["statut"], "success" | "pending" | "neutral"> = {
  valide: "success",
  proposition_en_attente: "pending",
  remplace: "neutral",
};

const LABEL_STATUT: Record<ReferentielOut["statut"], string> = {
  valide: "En vigueur",
  proposition_en_attente: "Proposition en attente",
  remplace: "Remplacé",
};

function CoefficientEditable({
  referentiel,
  onEnregistrer,
}: {
  referentiel: ReferentielOut;
  onEnregistrer: (id: string, coefficient: number) => Promise<void>;
}) {
  const [edition, setEdition] = useState(false);
  const [valeur, setValeur] = useState(referentiel.coefficient);
  const [enCours, setEnCours] = useState(false);

  if (referentiel.statut !== "valide") {
    return <span className="monospace">{referentiel.coefficient}</span>;
  }

  if (!edition) {
    return (
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        onClick={(e) => { e.stopPropagation(); setEdition(true); setValeur(referentiel.coefficient); }}
        style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
      >
        <span className="monospace">{referentiel.coefficient}</span>
        <Pencil size={12} />
      </button>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "4px" }} onClick={(e) => e.stopPropagation()}>
      <input
        type="number"
        step="0.1"
        min={0.1}
        value={valeur}
        onChange={(e) => setValeur(Number(e.target.value))}
        className="field-input"
        style={{ width: "70px", padding: "4px 8px" }}
        autoFocus
      />
      <button
        type="button"
        className="btn btn-primary btn-sm"
        disabled={enCours}
        onClick={async () => {
          setEnCours(true);
          await onEnregistrer(referentiel.id, valeur);
          setEnCours(false);
          setEdition(false);
        }}
        aria-label="Enregistrer"
      >
        <Check size={12} />
      </button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEdition(false)} aria-label="Annuler">
        <X size={12} />
      </button>
    </div>
  );
}

export function ReferentielsPage() {
  const [referentiels, setReferentiels] = useState<ReferentielOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [niveau, setNiveau] = useState("");
  const [matiere, setMatiere] = useState("");
  const [coefficient, setCoefficient] = useState(1);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [validationEnCoursId, setValidationEnCoursId] = useState<string | null>(null);
  const [champErreurs, setChampErreurs] = useState<{ niveau?: string; matiere?: string; coefficient?: string }>({});

  const [recherche, setRecherche] = useState("");
  const [filtreStatut, setFiltreStatut] = useState<"" | ReferentielOut["statut"]>("");
  const [selection, setSelection] = useState<Set<string>>(new Set());
  const [validationLotEnCours, setValidationLotEnCours] = useState(false);

  const charger = () => {
    setChargement(true);
    listerReferentiels()
      .then((res) => setReferentiels(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  // UC-30 (délégué) : autocomplétion niveau/matière à partir des valeurs déjà en base -
  // pas de nouvel endpoint, purement dérivé de la liste déjà chargée.
  const niveauxConnus = useMemo(() => Array.from(new Set(referentiels.map((r) => r.niveau))).sort(), [referentiels]);
  const matieresConnues = useMemo(() => Array.from(new Set(referentiels.map((r) => r.matiere))).sort(), [referentiels]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);

    const erreurs: typeof champErreurs = {};
    if (!estRempli(niveau)) erreurs.niveau = "Niveau requis.";
    if (!estRempli(matiere)) erreurs.matiere = "Matière requise.";
    if (!Number.isFinite(coefficient) || coefficient <= 0) erreurs.coefficient = "Coefficient requis (supérieur à 0).";
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await creerReferentiel(niveau, matiere, coefficient);
      setNiveau("");
      setMatiere("");
      setCoefficient(1);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le référentiel."));
    } finally {
      setEnCours(false);
    }
  };

  const valider = async (id: string) => {
    setValidationEnCoursId(id);
    try {
      await validerReferentiel(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setValidationEnCoursId(null);
    }
  };

  const enregistrerCoefficient = async (id: string, coefficientValeur: number) => {
    setErreur(null);
    try {
      await modifierReferentiel(id, coefficientValeur);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de modifier ce référentiel."));
    }
  };

  const validerLot = async () => {
    const idsEligibles = referentielsActifs
      .filter((r) => selection.has(r.id) && r.statut === "proposition_en_attente")
      .map((r) => r.id);
    if (idsEligibles.length === 0) {
      setErreur("Sélectionnez au moins une proposition en attente pour valider en masse.");
      return;
    }
    setValidationLotEnCours(true);
    setErreur(null);
    try {
      await validerReferentielsEnLot(idsEligibles);
      setSelection(new Set());
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de valider ces propositions."));
    } finally {
      setValidationLotEnCours(false);
    }
  };

  const referentielsActifs = referentiels.filter((r) => r.statut !== "remplace" || filtreStatut === "remplace");
  const referentielsFiltres = referentielsActifs.filter((r) => {
    if (recherche && !`${r.niveau} ${r.matiere}`.toLowerCase().includes(recherche.toLowerCase())) return false;
    if (filtreStatut && r.statut !== filtreStatut) return false;
    return true;
  });

  const colonnes: DataTableColumn<ReferentielOut>[] = [
    { key: "niveau", header: "Niveau", render: (r) => <span style={{ fontWeight: 600 }}>{r.niveau}</span> },
    { key: "matiere", header: "Matière", render: (r) => r.matiere },
    {
      key: "coefficient",
      header: "Coefficient",
      render: (r) => <CoefficientEditable referentiel={r} onEnregistrer={enregistrerCoefficient} />,
    },
    { key: "statut", header: "Statut", render: (r) => <Badge tone={TONE_STATUT[r.statut]}>{LABEL_STATUT[r.statut]}</Badge> },
    {
      key: "actions",
      header: "",
      render: (r) =>
        r.statut === "proposition_en_attente" ? (
          <Btn variant="outline" size="sm" loading={validationEnCoursId === r.id} onClick={() => valider(r.id)}>
            Valider
          </Btn>
        ) : null,
    },
  ];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace ministériel">Référentiels de coefficients</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-8" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
        <SectionHead title="Fixer un référentiel national" desc="Coefficient par niveau et matière, applicable à tous les établissements." />
        <form onSubmit={soumettre} noValidate style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
          <Field label="Niveau" error={champErreurs.niveau} helper={niveauxConnus.length > 0 ? `Déjà utilisés : ${niveauxConnus.slice(0, 6).join(", ")}` : undefined}>
            <TextInput value={niveau} onChange={(e) => setNiveau(e.target.value)} placeholder="Ex. CE1" list="niveaux-connus" />
            <datalist id="niveaux-connus">
              {niveauxConnus.map((n) => <option key={n} value={n} />)}
            </datalist>
          </Field>
          <Field label="Matière" error={champErreurs.matiere}>
            <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} placeholder="Ex. Mathématiques" list="matieres-connues" />
            <datalist id="matieres-connues">
              {matieresConnues.map((m) => <option key={m} value={m} />)}
            </datalist>
          </Field>
          <Field label="Coefficient" error={champErreurs.coefficient}>
            <TextInput
              type="number"
              step="0.1"
              min={0.1}
              value={coefficient}
              onChange={(e) => setCoefficient(Number(e.target.value))}
              style={{ width: "100px" }}
            />
          </Field>
          <Btn type="submit" variant="primary" loading={enCours}>
            Fixer
          </Btn>
        </form>
      </Card>

      <SectionHead title="Référentiels" desc="Coefficient modifiable directement pour un référentiel en vigueur ; validation groupée pour les propositions en attente." />
      <DataTable
        columns={colonnes}
        rows={referentielsFiltres}
        rowKey={(r) => r.id}
        loading={chargement}
        emptyTitle="Aucun référentiel"
        emptyDesc="Fixez le premier référentiel national ci-dessus."
        searchValue={recherche}
        onSearchChange={setRecherche}
        searchPlaceholder="Rechercher par niveau ou matière..."
        filters={
          <Select value={filtreStatut} onChange={(e) => setFiltreStatut(e.target.value as "" | ReferentielOut["statut"])} style={{ width: "220px" }}>
            <option value="">Tous statuts</option>
            <option value="valide">En vigueur</option>
            <option value="proposition_en_attente">Propositions en attente</option>
            <option value="remplace">Remplacés</option>
          </Select>
        }
        selectable
        selectedIds={selection}
        onSelectionChange={setSelection}
        bulkActions={[
          {
            label: "Valider la sélection",
            icon: <CheckCircle2 size={14} />,
            variant: "primary",
            loading: validationLotEnCours,
            onClick: validerLot,
          },
        ]}
      />
    </div>
  );
}
