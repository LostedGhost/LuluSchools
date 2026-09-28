import { libelle } from "../../utils/libelles";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  consoleCours,
  consoleEleves,
  consoleEnseignants,
  consoleNotes,
  consoleTuteurs,
  listerClasses,
} from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type {
  ClasseOut,
  ConsoleCoursOut,
  ConsoleEleveOut,
  ConsoleEnseignantOut,
  ConsoleNoteOut,
  ConsoleTuteurOut,
} from "../../types/api";
import { Badge, ErrorBanner, PageTitle, Select } from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";

const PAGE_SIZE = 20;

type Objet = "eleves" | "enseignants" | "tuteurs" | "cours" | "notes";

const LABEL_OBJET: Record<Objet, string> = {
  eleves: "Élèves",
  enseignants: "Enseignants",
  tuteurs: "Tuteurs",
  cours: "Cours",
  notes: "Notes / bulletins",
};

/**
 * Console de pilotage établissement (UC-45/46/60/61) : pivote sur une classe (optionnelle)
 * et une année académique (optionnelle) pour n'importe quel objet de la plateforme -
 * réutilise le composant DataTable générique (Phase 5) plutôt que d'en réinventer un.
 */
export function ConsoleEtablissementPage() {
  const etablissement = useAdminEtab();
  const [searchParams, setSearchParams] = useSearchParams();
  const classeId = searchParams.get("classe_id") ?? "";
  const [objet, setObjet] = useState<Objet>("eleves");
  const [anneeAcademique, setAnneeAcademique] = useState("");
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [page, setPage] = useState(0);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);

  const [eleves, setEleves] = useState<ConsoleEleveOut[]>([]);
  const [enseignants, setEnseignants] = useState<ConsoleEnseignantOut[]>([]);
  const [tuteurs, setTuteurs] = useState<ConsoleTuteurOut[]>([]);
  const [cours, setCours] = useState<ConsoleCoursOut[]>([]);
  const [notes, setNotes] = useState<ConsoleNoteOut[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    listerClasses(etablissement.id).then((res) => setClasses(res.data)).catch(() => undefined);
  }, [etablissement.id]);

  const anneesConnues = useMemo(
    () => Array.from(new Set(classes.map((c) => c.annee_academique))).sort().reverse(),
    [classes],
  );

  useEffect(() => {
    setChargement(true);
    setErreur(null);
    const params = { classe_id: classeId || undefined, annee_academique: anneeAcademique || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE };
    const requete =
      objet === "eleves" ? consoleEleves(etablissement.id, params)
      : objet === "enseignants" ? consoleEnseignants(etablissement.id, params)
      : objet === "tuteurs" ? consoleTuteurs(etablissement.id, params)
      : objet === "cours" ? consoleCours(etablissement.id, params)
      : consoleNotes(etablissement.id, params);

    requete
      .then((res) => {
        setTotal(res.data.total);
        if (objet === "eleves") setEleves(res.data.items as ConsoleEleveOut[]);
        else if (objet === "enseignants") setEnseignants(res.data.items as ConsoleEnseignantOut[]);
        else if (objet === "tuteurs") setTuteurs(res.data.items as ConsoleTuteurOut[]);
        else if (objet === "cours") setCours(res.data.items as ConsoleCoursOut[]);
        else setNotes(res.data.items as ConsoleNoteOut[]);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etablissement.id, objet, classeId, anneeAcademique, page]);

  const colonnesEleves: DataTableColumn<ConsoleEleveOut>[] = [
    { key: "nom", header: "Élève", render: (r) => `${r.prenom} ${r.nom}` },
    { key: "matricule", header: "Matricule", render: (r) => r.matricule ?? "—" },
    { key: "classe", header: "Classe", render: (r) => `${r.classe_niveau}${r.classe_filiere ? ` ${r.classe_filiere}` : ""}` },
    { key: "statut", header: "Statut", render: (r) => <Badge tone="info">{r.statut_inscription}</Badge> },
  ];
  const colonnesEnseignants: DataTableColumn<ConsoleEnseignantOut>[] = [
    { key: "nom", header: "Enseignant", render: (r) => `${r.prenom} ${r.nom}` },
    { key: "classe", header: "Classe", render: (r) => `${r.classe_niveau}${r.classe_filiere ? ` ${r.classe_filiere}` : ""}` },
  ];
  const colonnesTuteurs: DataTableColumn<ConsoleTuteurOut>[] = [
    { key: "nom", header: "Tuteur", render: (r) => `${r.prenom} ${r.nom}` },
    { key: "email", header: "E-mail", render: (r) => r.email ?? "—" },
    { key: "enfants", header: "Enfant(s) dans le périmètre", render: (r) => r.nb_enfants_dans_le_perimetre },
  ];
  const colonnesCours: DataTableColumn<ConsoleCoursOut>[] = [
    { key: "titre", header: "Cours", render: (r) => r.titre },
    { key: "chapitre", header: "Chapitre", render: (r) => r.chapitre },
    { key: "classe", header: "Classe", render: (r) => r.classe_niveau },
    { key: "enseignant", header: "Enseignant", render: (r) => `${r.enseignant_prenom} ${r.enseignant_nom}` },
  ];
  const colonnesNotes: DataTableColumn<ConsoleNoteOut>[] = [
    { key: "eleve", header: "Élève", render: (r) => `${r.eleve_prenom} ${r.eleve_nom}` },
    { key: "classe", header: "Classe", render: (r) => r.classe_niveau },
    { key: "periode", header: "Période", render: (r) => libelle(r.periode) },
    { key: "moyenne", header: "Moyenne", render: (r) => r.moyenne_generale.toFixed(2) },
    { key: "decision", header: "Décision", render: (r) => r.decision_passage ?? "—" },
  ];

  const classeActuelle = classes.find((c) => c.id === classeId);

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Établissement">Console établissement</PageTitle>
      <p className="text-sm" style={{ color: "var(--ink-soft)", marginBottom: "var(--space-4)" }}>
        Filtrez par classe et par année académique pour n'importe quel objet de la plateforme — retirez le filtre classe pour voir tout l'établissement.
      </p>
      <ErrorBanner>{erreur}</ErrorBanner>

      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "16px" }}>
        <Select aria-label="Données affichées" value={objet} onChange={(e) => { setPage(0); setObjet(e.target.value as Objet); }} style={{ width: "200px" }}>
          {Object.entries(LABEL_OBJET).map(([valeur, label]) => (
            <option key={valeur} value={valeur}>{label}</option>
          ))}
        </Select>
        <Select
          aria-label="Classe"
          value={classeId}
          onChange={(e) => { setPage(0); setSearchParams(e.target.value ? { classe_id: e.target.value } : {}); }}
          style={{ width: "240px" }}
        >
          <option value="">Tout l'établissement</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.niveau}{c.filiere ? ` ${c.filiere}` : ""} — {c.annee_academique}
            </option>
          ))}
        </Select>
        <Select value={anneeAcademique} onChange={(e) => { setPage(0); setAnneeAcademique(e.target.value); }} style={{ width: "180px" }}>
          <option value="">Toutes les années</option>
          {anneesConnues.map((a) => <option key={a} value={a}>{a}</option>)}
        </Select>
      </div>

      {classeActuelle && (
        <p className="text-sm" style={{ color: "var(--ink-faint)", marginBottom: "12px" }}>
          Filtré sur <strong>{classeActuelle.niveau}{classeActuelle.filiere ? ` ${classeActuelle.filiere}` : ""}</strong> ({classeActuelle.annee_academique})
        </p>
      )}

      {objet === "eleves" && (
        <DataTable columns={colonnesEleves} rows={eleves} rowKey={(r) => `${r.eleve_id}-${r.classe_id}`} loading={chargement} emptyTitle="Aucun élève" page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      )}
      {objet === "enseignants" && (
        <DataTable columns={colonnesEnseignants} rows={enseignants} rowKey={(r) => `${r.utilisateur_id}-${r.classe_id}`} loading={chargement} emptyTitle="Aucun enseignant" page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      )}
      {objet === "tuteurs" && (
        <DataTable columns={colonnesTuteurs} rows={tuteurs} rowKey={(r) => r.utilisateur_id} loading={chargement} emptyTitle="Aucun tuteur" page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      )}
      {objet === "cours" && (
        <DataTable columns={colonnesCours} rows={cours} rowKey={(r) => r.id} loading={chargement} emptyTitle="Aucun cours" page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      )}
      {objet === "notes" && (
        <DataTable columns={colonnesNotes} rows={notes} rowKey={(r) => `${r.eleve_id}-${r.classe_id}-${r.periode}`} loading={chargement} emptyTitle="Aucune note" page={page} pageSize={PAGE_SIZE} total={total} onPageChange={setPage} />
      )}
    </div>
  );
}
