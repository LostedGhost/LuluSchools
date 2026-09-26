import { useEffect, useState } from "react";
import {
  deciderContestationMicroJob,
  listerContestationsMicroJob,
  listerMissionsAReverser,
  reverserPrestataire,
} from "../../api/micro_jobs";
import { messageErreur } from "../../api/client";
import type { ContestationMicroJobDetailOut, MissionAReverserOut } from "../../types/api";
import { Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, SuccessBanner, TextArea, TextInput } from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { CheckCircle2, Landmark, Phone, XCircle } from "lucide-react";
import { estRempli } from "../../utils/validation";

function formaterMontant(montant: number): string {
  return `${montant.toLocaleString("fr-FR")} FCFA`;
}

export function MicroJobsArbitragePage() {
  const [contestations, setContestations] = useState<ContestationMicroJobDetailOut[]>([]);
  const [chargementContestations, setChargementContestations] = useState(true);
  const [contestationSelectionnee, setContestationSelectionnee] = useState<ContestationMicroJobDetailOut | null>(null);
  const [motifDecision, setMotifDecision] = useState("");
  const [enCoursDecision, setEnCoursDecision] = useState<"acceptee" | "rejetee" | null>(null);
  const [erreurDecision, setErreurDecision] = useState<string | null>(null);
  const [succesDecision, setSuccesDecision] = useState<string | null>(null);

  const [missions, setMissions] = useState<MissionAReverserOut[]>([]);
  const [chargementMissions, setChargementMissions] = useState(true);
  const [missionSelectionnee, setMissionSelectionnee] = useState<MissionAReverserOut | null>(null);
  const [referencePaiement, setReferencePaiement] = useState("");
  const [enCoursReversement, setEnCoursReversement] = useState(false);
  const [erreurReversement, setErreurReversement] = useState<string | null>(null);
  const [succesReversement, setSuccesReversement] = useState<string | null>(null);

  const chargerContestations = () => {
    setChargementContestations(true);
    listerContestationsMicroJob("en_attente")
      .then((res) => setContestations(res.data))
      .catch((err) => setErreurDecision(messageErreur(err)))
      .finally(() => setChargementContestations(false));
  };

  const chargerMissions = () => {
    setChargementMissions(true);
    listerMissionsAReverser()
      .then((res) => setMissions(res.data))
      .catch((err) => setErreurReversement(messageErreur(err)))
      .finally(() => setChargementMissions(false));
  };

  useEffect(() => {
    chargerContestations();
    chargerMissions();
  }, []);

  const trancher = async (decision: "acceptee" | "rejetee") => {
    if (!contestationSelectionnee) return;
    if (decision === "rejetee" && !estRempli(motifDecision)) {
      setErreurDecision("Un motif est requis en cas de rejet.");
      return;
    }
    setErreurDecision(null);
    setSuccesDecision(null);
    setEnCoursDecision(decision);
    try {
      await deciderContestationMicroJob(contestationSelectionnee.id, decision, motifDecision.trim() || undefined);
      setSuccesDecision(
        decision === "acceptee"
          ? "Contestation acceptée : la mission a été remboursée au client."
          : "Contestation rejetée : la mission est validée, le prestataire peut être payé."
      );
      setContestationSelectionnee(null);
      setMotifDecision("");
      chargerContestations();
    } catch (err) {
      setErreurDecision(messageErreur(err, "Impossible de trancher cette contestation."));
    } finally {
      setEnCoursDecision(null);
    }
  };

  const reverser = async () => {
    if (!missionSelectionnee) return;
    if (!estRempli(referencePaiement)) {
      setErreurReversement("Veuillez renseigner la référence du paiement effectué.");
      return;
    }
    setErreurReversement(null);
    setSuccesReversement(null);
    setEnCoursReversement(true);
    try {
      await reverserPrestataire(missionSelectionnee.id, referencePaiement.trim());
      setSuccesReversement("Mission marquée comme payée au prestataire.");
      setMissionSelectionnee(null);
      setReferencePaiement("");
      chargerMissions();
    } catch (err) {
      setErreurReversement(messageErreur(err, "Impossible de reverser cette mission."));
    } finally {
      setEnCoursReversement(false);
    }
  };

  const colonnesContestations: DataTableColumn<ContestationMicroJobDetailOut>[] = [
    { key: "offre", header: "Mission", render: (c) => <span style={{ fontWeight: 600 }}>{c.offre_titre}</span> },
    { key: "prix", header: "Montant", render: (c) => formaterMontant(c.prix) },
    { key: "client", header: "Client", render: (c) => `${c.client_prenom} ${c.client_nom}` },
    { key: "prestataire", header: "Prestataire", render: (c) => `${c.prestataire_prenom} ${c.prestataire_nom}` },
    {
      key: "motif",
      header: "Motif",
      render: (c) => <span style={{ color: "var(--ink-soft)" }}>{c.motif.length > 60 ? `${c.motif.slice(0, 60)}...` : c.motif}</span>,
    },
  ];

  const colonnesMissions: DataTableColumn<MissionAReverserOut>[] = [
    { key: "offre", header: "Mission", render: (m) => <span style={{ fontWeight: 600 }}>{m.offre_titre}</span> },
    { key: "prix", header: "Montant", render: (m) => formaterMontant(m.prix_paye) },
    { key: "prestataire", header: "Prestataire", render: (m) => `${m.prestataire_prenom} ${m.prestataire_nom}` },
    {
      key: "telephone",
      header: "Contact",
      render: (m) =>
        m.prestataire_telephone ? (
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <Phone size={12} /> {m.prestataire_telephone}
          </span>
        ) : (
          <span style={{ color: "var(--ink-faint)" }}>Non renseigné</span>
        ),
    },
  ];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Ministériel">Arbitrage des micro-jobs</PageTitle>

      <SectionHead
        title="Contestations en attente"
        desc="Cliquez une ligne pour voir le détail complet et trancher — le montant est en séquestre chez Kkiapay jusqu'à cette décision (voir ADR-008)."
      />
      <DataTable
        columns={colonnesContestations}
        rows={contestations}
        rowKey={(c) => c.id}
        loading={chargementContestations}
        emptyTitle="Aucune contestation en attente"
        emptyDesc="Toutes les contestations ont été tranchées."
        onRowClick={(c) => { setContestationSelectionnee(c); setMotifDecision(""); setErreurDecision(null); setSuccesDecision(null); }}
      />

      {contestationSelectionnee && (
        <Card className="mt-4 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
          <SectionHead title={`Contestation — ${contestationSelectionnee.offre_titre}`} />
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
            <p className="text-sm" style={{ color: "var(--ink-soft)" }}>
              <strong>Montant :</strong> {formaterMontant(contestationSelectionnee.prix)} ·{" "}
              <strong>Client :</strong> {contestationSelectionnee.client_prenom} {contestationSelectionnee.client_nom} ·{" "}
              <strong>Prestataire :</strong> {contestationSelectionnee.prestataire_prenom} {contestationSelectionnee.prestataire_nom}
            </p>
            <p style={{ color: "var(--ink)" }}><strong>Motif de la contestation :</strong> {contestationSelectionnee.motif}</p>
          </div>
          <Field label="Motif de la décision" helper="Obligatoire en cas de rejet." >
            <TextArea rows={3} value={motifDecision} onChange={(e) => setMotifDecision(e.target.value)} />
          </Field>
          <ErrorBanner>{erreurDecision}</ErrorBanner>
          <SuccessBanner>{succesDecision}</SuccessBanner>
          <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
            <Btn variant="primary" loading={enCoursDecision === "acceptee"} onClick={() => trancher("acceptee")} leftIcon={<CheckCircle2 size={16} />}>
              Accepter (rembourser le client)
            </Btn>
            <Btn variant="action" loading={enCoursDecision === "rejetee"} onClick={() => trancher("rejetee")} leftIcon={<XCircle size={16} />}>
              Rejeter (payer le prestataire)
            </Btn>
            <Btn variant="ghost" onClick={() => setContestationSelectionnee(null)}>Fermer</Btn>
          </div>
        </Card>
      )}

      <div style={{ marginTop: "var(--space-8)" }}>
        <SectionHead
          title="Reversements en attente"
          desc="Missions validées : effectuez le virement Mobile Money manuellement (contact déjà connu) puis enregistrez la référence ici."
        />
        <DataTable
          columns={colonnesMissions}
          rows={missions}
          rowKey={(m) => m.id}
          loading={chargementMissions}
          emptyTitle="Aucun reversement en attente"
          onRowClick={(m) => { setMissionSelectionnee(m); setReferencePaiement(""); setErreurReversement(null); setSuccesReversement(null); }}
        />

        {missionSelectionnee && (
          <Card className="mt-4 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
            <SectionHead title={`Reverser — ${missionSelectionnee.offre_titre}`} />
            <p className="text-sm" style={{ color: "var(--ink-soft)", marginTop: "8px" }}>
              <strong>Prestataire :</strong> {missionSelectionnee.prestataire_prenom} {missionSelectionnee.prestataire_nom}
              {missionSelectionnee.prestataire_telephone && ` · ${missionSelectionnee.prestataire_telephone}`} ·{" "}
              <strong>Montant :</strong> {formaterMontant(missionSelectionnee.prix_paye)}
            </p>
            <Field label="Référence du paiement effectué" required helper="Référence de la transaction Mobile Money envoyée manuellement au prestataire.">
              <TextInput value={referencePaiement} onChange={(e) => setReferencePaiement(e.target.value)} />
            </Field>
            <ErrorBanner>{erreurReversement}</ErrorBanner>
            <SuccessBanner>{succesReversement}</SuccessBanner>
            <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
              <Btn variant="primary" loading={enCoursReversement} onClick={reverser} leftIcon={<Landmark size={16} />}>
                Confirmer le reversement
              </Btn>
              <Btn variant="ghost" onClick={() => setMissionSelectionnee(null)}>Fermer</Btn>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
