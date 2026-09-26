import { useState } from "react";
import { deciderContestationMicroJob, reverserPrestataire } from "../../api/micro_jobs";
import { messageErreur } from "../../api/client";
import { Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, SuccessBanner, TextArea, TextInput } from "../../components/ui";
import { CheckCircle2, Landmark, XCircle } from "lucide-react";
import { estRempli } from "../../utils/validation";

export function MicroJobsArbitragePage() {
  const [contestationId, setContestationId] = useState("");
  const [motifDecision, setMotifDecision] = useState("");
  const [enCoursDecision, setEnCoursDecision] = useState<"acceptee" | "rejetee" | null>(null);
  const [erreurDecision, setErreurDecision] = useState<string | null>(null);
  const [succesDecision, setSuccesDecision] = useState<string | null>(null);

  const [missionId, setMissionId] = useState("");
  const [referencePaiement, setReferencePaiement] = useState("");
  const [enCoursReversement, setEnCoursReversement] = useState(false);
  const [erreurReversement, setErreurReversement] = useState<string | null>(null);
  const [succesReversement, setSuccesReversement] = useState<string | null>(null);

  const trancher = async (decision: "acceptee" | "rejetee") => {
    if (!estRempli(contestationId)) {
      setErreurDecision("Veuillez saisir l'identifiant de la contestation.");
      return;
    }
    if (decision === "rejetee" && !estRempli(motifDecision)) {
      setErreurDecision("Un motif est requis en cas de rejet.");
      return;
    }
    setErreurDecision(null);
    setSuccesDecision(null);
    setEnCoursDecision(decision);
    try {
      await deciderContestationMicroJob(contestationId.trim(), decision, motifDecision.trim() || undefined);
      setSuccesDecision(
        decision === "acceptee"
          ? "Contestation acceptée : la mission a été remboursée au client."
          : "Contestation rejetée : la mission est validée, le prestataire peut être payé."
      );
      setContestationId("");
      setMotifDecision("");
    } catch (err) {
      setErreurDecision(messageErreur(err, "Impossible de trancher cette contestation. Vérifiez l'identifiant."));
    } finally {
      setEnCoursDecision(null);
    }
  };

  const reverser = async () => {
    if (!estRempli(missionId) || !estRempli(referencePaiement)) {
      setErreurReversement("Veuillez renseigner l'identifiant de la mission et la référence du paiement effectué.");
      return;
    }
    setErreurReversement(null);
    setSuccesReversement(null);
    setEnCoursReversement(true);
    try {
      await reverserPrestataire(missionId.trim(), referencePaiement.trim());
      setSuccesReversement("Mission marquée comme payée au prestataire.");
      setMissionId("");
      setReferencePaiement("");
    } catch (err) {
      setErreurReversement(messageErreur(err, "Impossible de reverser cette mission. Vérifiez qu'elle est bien validée."));
    } finally {
      setEnCoursReversement(false);
    }
  };

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Ministériel">Arbitrage des micro-jobs</PageTitle>

      <div className="grid-2">
        <Card>
          <SectionHead
            title="Trancher une contestation"
            desc="Le montant a été mis en séquestre par Kkiapay jusqu'à cette décision (aucun transfert tiers automatique n'existe côté Kkiapay — voir ADR-008)."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "16px" }}>
            <Field label="Identifiant de la contestation" required>
              <TextInput value={contestationId} onChange={(e) => setContestationId(e.target.value)} placeholder="ID contestation" />
            </Field>
            <Field label="Motif de la décision" helper="Obligatoire en cas de rejet.">
              <TextArea rows={3} value={motifDecision} onChange={(e) => setMotifDecision(e.target.value)} />
            </Field>
            <ErrorBanner>{erreurDecision}</ErrorBanner>
            <SuccessBanner>{succesDecision}</SuccessBanner>
            <div style={{ display: "flex", gap: "12px" }}>
              <Btn variant="primary" loading={enCoursDecision === "acceptee"} onClick={() => trancher("acceptee")} leftIcon={<CheckCircle2 size={16} />}>
                Accepter (rembourser le client)
              </Btn>
              <Btn variant="action" loading={enCoursDecision === "rejetee"} onClick={() => trancher("rejetee")} leftIcon={<XCircle size={16} />}>
                Rejeter (payer le prestataire)
              </Btn>
            </div>
          </div>
        </Card>

        <Card>
          <SectionHead
            title="Reverser un prestataire"
            desc="Une fois la mission validée (par le client ou tacitement après 5 jours), effectuez le virement Mobile Money manuellement puis enregistrez la référence ici."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "16px" }}>
            <Field label="Identifiant de la mission" required>
              <TextInput value={missionId} onChange={(e) => setMissionId(e.target.value)} placeholder="ID mission" />
            </Field>
            <Field label="Référence du paiement effectué" required helper="Référence de la transaction Mobile Money envoyée manuellement au prestataire.">
              <TextInput value={referencePaiement} onChange={(e) => setReferencePaiement(e.target.value)} />
            </Field>
            <ErrorBanner>{erreurReversement}</ErrorBanner>
            <SuccessBanner>{succesReversement}</SuccessBanner>
            <Btn variant="primary" loading={enCoursReversement} onClick={reverser} leftIcon={<Landmark size={16} />}>
              Confirmer le reversement
            </Btn>
          </div>
        </Card>
      </div>
    </div>
  );
}
