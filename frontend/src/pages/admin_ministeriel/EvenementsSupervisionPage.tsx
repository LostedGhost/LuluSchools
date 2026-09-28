import { useEffect, useState } from "react";
import { annulerEvenement, listerEvenementsSupervision } from "../../api/admin";
import { messageErreur } from "../../api/client";
import type { AdminEvenementOut } from "../../types/api";
import { Badge, Btn, ErrorBanner, PageTitle, Select, SuccessBanner } from "../../components/ui";
import { Modale } from "../../components/Modale";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { CalendarX, MapPin } from "lucide-react";

const PAGE_SIZE = 15;

export function EvenementsSupervisionPage() {
  const [evenements, setEvenements] = useState<AdminEvenementOut[]>([]);
  const [total, setTotal] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [page, setPage] = useState(0);
  const [filtreStatut, setFiltreStatut] = useState<"" | "ouvert" | "annule">("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [cibleAnnulation, setCibleAnnulation] = useState<AdminEvenementOut | null>(null);
  const [enCoursAnnulation, setEnCoursAnnulation] = useState(false);

  const charger = () => {
    setChargement(true);
    listerEvenementsSupervision({ statut: filtreStatut || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((res) => { setEvenements(res.data.items); setTotal(res.data.total); })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [filtreStatut, page]);

  const confirmerAnnulation = async () => {
    if (!cibleAnnulation) return;
    setEnCoursAnnulation(true);
    setErreur(null);
    try {
      await annulerEvenement(cibleAnnulation.id);
      setSucces(`« ${cibleAnnulation.titre} » annulé — les billets déjà achetés seront remboursés.`);
      setCibleAnnulation(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'annuler cet événement."));
    } finally {
      setEnCoursAnnulation(false);
    }
  };

  const colonnes: DataTableColumn<AdminEvenementOut>[] = [
    { key: "titre", header: "Événement", render: (e) => <span style={{ fontWeight: 600 }}>{e.titre}</span> },
    { key: "etablissement", header: "Établissement", render: (e) => e.etablissement_nom },
    {
      key: "lieu",
      header: "Lieu",
      render: (e) => (
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <MapPin size={12} /> {e.lieu}
        </span>
      ),
    },
    { key: "date", header: "Date", render: (e) => new Date(e.date_heure).toLocaleString("fr-FR") },
    { key: "statut", header: "Statut", render: (e) => (e.statut === "annule" ? <Badge tone="error">Annulé</Badge> : <Badge tone="success">Ouvert</Badge>) },
    {
      key: "actions",
      header: "",
      render: (e) =>
        e.statut === "ouvert" ? (
          <Btn size="sm" variant="action" leftIcon={<CalendarX size={14} />} onClick={() => setCibleAnnulation(e)}>
            Annuler
          </Btn>
        ) : null,
    },
  ];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace ministériel">Supervision des événements</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && <div className="mb-4"><SuccessBanner>{succes}</SuccessBanner></div>}

      <Modale
        ouvert={cibleAnnulation !== null}
        onFermer={() => setCibleAnnulation(null)}
        titre={`Annuler « ${cibleAnnulation?.titre ?? ""} » ?`}
        pied={
          <>
            <Btn variant="ghost" onClick={() => setCibleAnnulation(null)}>Fermer</Btn>
            <Btn variant="action" loading={enCoursAnnulation} onClick={confirmerAnnulation}>Annuler l'événement</Btn>
          </>
        }
      >
        <p className="text-sm" style={{ color: "var(--ink-soft)", margin: 0 }}>
          Tous les billets déjà achetés ou validés seront automatiquement remboursés. Cette action est définitive et journalisée dans le journal d'audit ministériel.
        </p>
        <ErrorBanner>{erreur}</ErrorBanner>
      </Modale>

      <DataTable
        columns={colonnes}
        rows={evenements}
        rowKey={(e) => e.id}
        loading={chargement}
        emptyTitle="Aucun événement"
        filters={
          <Select value={filtreStatut} onChange={(e) => { setPage(0); setFiltreStatut(e.target.value as "" | "ouvert" | "annule"); }} style={{ width: "160px" }}>
            <option value="">Tous statuts</option>
            <option value="ouvert">Ouverts</option>
            <option value="annule">Annulés</option>
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
