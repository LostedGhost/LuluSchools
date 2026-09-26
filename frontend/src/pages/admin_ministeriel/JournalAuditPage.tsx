import { useEffect, useState } from "react";
import { listerJournalAudit } from "../../api/admin";
import { messageErreur } from "../../api/client";
import type { JournalAuditOut } from "../../types/api";
import { Badge, ErrorBanner, PageTitle, Select } from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";

const PAGE_SIZE = 20;

const CIBLES = [
  { valeur: "etablissement", label: "Établissements" },
  { valeur: "utilisateur", label: "Utilisateurs" },
  { valeur: "referentiel", label: "Référentiels" },
  { valeur: "contestation_micro_job", label: "Contestations micro-job" },
  { valeur: "mission_micro_job", label: "Missions micro-job" },
  { valeur: "cours", label: "Cours" },
  { valeur: "devoir", label: "Devoirs" },
  { valeur: "evenement", label: "Événements" },
];

export function JournalAuditPage() {
  const [entrees, setEntrees] = useState<JournalAuditOut[]>([]);
  const [total, setTotal] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [page, setPage] = useState(0);
  const [filtreCible, setFiltreCible] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    setChargement(true);
    listerJournalAudit({ cible_type: filtreCible || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((res) => { setEntrees(res.data.items); setTotal(res.data.total); })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [filtreCible, page]);

  const colonnes: DataTableColumn<JournalAuditOut>[] = [
    { key: "date", header: "Date", render: (e) => new Date(e.created_at).toLocaleString("fr-FR") },
    { key: "action", header: "Action", render: (e) => <Badge tone="info">{e.action}</Badge> },
    { key: "cible", header: "Cible", render: (e) => <span className="monospace text-sm">{e.cible_type} · {e.cible_id.slice(0, 8)}</span> },
    { key: "motif", header: "Motif", render: (e) => e.motif ?? <span style={{ color: "var(--ink-faint)" }}>—</span> },
  ];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace ministériel">Journal d'audit</PageTitle>
      <p className="text-sm" style={{ color: "var(--ink-soft)", marginBottom: "var(--space-4)" }}>
        Trace en lecture seule de toute action sensible déclenchée par un compte ministériel (suspension, arbitrage, validation, masquage, annulation) — pour la traçabilité d'un mandat public.
      </p>
      <ErrorBanner>{erreur}</ErrorBanner>

      <DataTable
        columns={colonnes}
        rows={entrees}
        rowKey={(e) => e.id}
        loading={chargement}
        emptyTitle="Aucune action journalisée"
        filters={
          <Select value={filtreCible} onChange={(e) => { setPage(0); setFiltreCible(e.target.value); }} style={{ width: "240px" }}>
            <option value="">Toutes les cibles</option>
            {CIBLES.map((c) => (
              <option key={c.valeur} value={c.valeur}>{c.label}</option>
            ))}
          </Select>
        }
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
      />
    </div>
  );
}
