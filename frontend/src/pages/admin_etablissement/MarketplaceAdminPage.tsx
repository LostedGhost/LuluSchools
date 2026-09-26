import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  deciderContestationMarketplace,
  listerAnnonces,
  retirerAnnonceModeration,
  reverserVendeur,
  signalementsMarketplaceEnAttente,
  traiterSignalementAnnonce,
} from "../../api/marketplace";
import { messageErreur } from "../../api/client";
import type { AnnonceMarketplaceOut, SignalementAnnonceOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  SkeletonCard,
  SuccessBanner,
  TextArea,
  TextInput,
} from "../../components/ui";
import { CheckCircle2, Flag, Landmark, ShoppingBag, Trash2, XCircle } from "lucide-react";
import { estRempli } from "../../utils/validation";

const STATUT_ANNONCE_LABEL: Record<AnnonceMarketplaceOut["statut"], string> = {
  disponible: "Disponible",
  reservee: "Réservée",
  vendue: "Vendue",
  retiree: "Retirée",
};
const STATUT_ANNONCE_TONE: Record<AnnonceMarketplaceOut["statut"], "success" | "pending" | "error" | "neutral"> = {
  disponible: "success",
  reservee: "pending",
  vendue: "neutral",
  retiree: "error",
};

export function MarketplaceAdminPage() {
  const etablissement = useAdminEtab();

  const [signalements, setSignalements] = useState<SignalementAnnonceOut[]>([]);
  const [annonces, setAnnonces] = useState<AnnonceMarketplaceOut[]>([]);
  const [decisionParId, setDecisionParId] = useState<Record<string, string>>({});
  const [motifRetraitParId, setMotifRetraitParId] = useState<Record<string, string>>({});
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    // Pas de filtre "tous statuts" côté backend (`statut` attend une valeur précise
    // de l'énumération) : deux appels ciblés sur les statuts que l'A+ peut réellement
    // vouloir modérer (disponible/réservée) plutôt qu'un mélange incluant vendue/retirée.
    Promise.all([
      signalementsMarketplaceEnAttente(etablissement.id),
      listerAnnonces(etablissement.id, { statut: "disponible", page_size: 60 }),
      listerAnnonces(etablissement.id, { statut: "reservee", page_size: 60 }),
    ])
      .then(([resSignalements, resDisponibles, resReservees]) => {
        setSignalements(resSignalements.data);
        setAnnonces([...resDisponibles.data.items, ...resReservees.data.items]);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const traiterSignalement = async (id: string) => {
    if (!decisionParId[id]?.trim()) {
      setErreur("Une décision motivée est requise pour clore ce signalement.");
      return;
    }
    setErreur(null);
    setActionEnCoursId(id);
    try {
      await traiterSignalementAnnonce(id, decisionParId[id].trim());
      setSucces("Signalement traité et clos.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const retirer = async (annonceId: string) => {
    if (!motifRetraitParId[annonceId]?.trim()) {
      setErreur("Un motif est requis pour retirer une annonce.");
      return;
    }
    setErreur(null);
    setActionEnCoursId(annonceId);
    try {
      await retirerAnnonceModeration(annonceId, motifRetraitParId[annonceId].trim());
      setSucces("Annonce retirée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de retirer cette annonce."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  // --- Litige et reversement (identifiants saisis manuellement, comme pour
  // l'arbitrage micro-jobs — aucun endpoint ne liste les contestations/transactions
  // par établissement pour l'instant, voir Limites frontend/PROJECT_MAP.md).
  const [contestationId, setContestationId] = useState("");
  const [motifDecision, setMotifDecision] = useState("");
  const [enCoursDecision, setEnCoursDecision] = useState<"acceptee" | "rejetee" | null>(null);
  const [erreurLitige, setErreurLitige] = useState<string | null>(null);
  const [succesLitige, setSuccesLitige] = useState<string | null>(null);

  const [transactionId, setTransactionId] = useState("");
  const [referencePaiement, setReferencePaiement] = useState("");
  const [enCoursReversement, setEnCoursReversement] = useState(false);

  const trancherLitige = async (decision: "acceptee" | "rejetee") => {
    if (!estRempli(contestationId)) {
      setErreurLitige("Veuillez saisir l'identifiant de la contestation.");
      return;
    }
    if (decision === "rejetee" && !estRempli(motifDecision)) {
      setErreurLitige("Un motif est requis en cas de rejet.");
      return;
    }
    setErreurLitige(null);
    setSuccesLitige(null);
    setEnCoursDecision(decision);
    try {
      await deciderContestationMarketplace(contestationId.trim(), decision, motifDecision.trim() || undefined);
      setSuccesLitige(
        decision === "acceptee"
          ? "Contestation acceptée : l'acheteur a été remboursé."
          : "Contestation rejetée : la transaction est confirmée, le vendeur peut être reversé."
      );
      setContestationId("");
      setMotifDecision("");
    } catch (err) {
      setErreurLitige(messageErreur(err, "Impossible de trancher cette contestation. Vérifiez l'identifiant."));
    } finally {
      setEnCoursDecision(null);
    }
  };

  const reverser = async () => {
    if (!estRempli(transactionId) || !estRempli(referencePaiement)) {
      setErreurLitige("Veuillez renseigner l'identifiant de la transaction et la référence du paiement effectué.");
      return;
    }
    setErreurLitige(null);
    setSuccesLitige(null);
    setEnCoursReversement(true);
    try {
      await reverserVendeur(transactionId.trim(), referencePaiement.trim());
      setSuccesLitige("Transaction marquée comme payée au vendeur.");
      setTransactionId("");
      setReferencePaiement("");
    } catch (err) {
      setErreurLitige(messageErreur(err, "Impossible de reverser cette transaction. Vérifiez qu'elle est bien confirmée."));
    } finally {
      setEnCoursReversement(false);
    }
  };

  if (chargement) {
    return <div className="page-content"><SkeletonCard /></div>;
  }

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Établissement">Marketplace étudiante</PageTitle>
      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      <div className="mb-8">
        <SectionHead
          title="Signalements en attente"
          desc="Annonces signalées par des élèves de votre établissement."
        />
        {signalements.length === 0 ? (
          <Card variant="soft"><EmptyState icon={<Flag size={24} />} title="Aucun signalement en attente" /></Card>
        ) : (
          <div className="space-y-3">
            {signalements.map((s) => (
              <Card key={s.id} className="anim-float-in">
                <p style={{ margin: "0 0 8px", fontSize: "var(--text-xs)", fontFamily: "var(--font-mono)", color: "var(--ink-faint)" }}>
                  Annonce : {s.annonce_id.slice(0, 8)}
                </p>
                <Field label="Décision" required>
                  <TextArea
                    rows={2}
                    placeholder="Ex. annonce conforme, aucune action / retirée pour non-conformité..."
                    value={decisionParId[s.id] ?? ""}
                    onChange={(e) => setDecisionParId((prev) => ({ ...prev, [s.id]: e.target.value }))}
                  />
                </Field>
                <div className="flex justify-end mt-2">
                  <Btn variant="primary" size="sm" loading={actionEnCoursId === s.id} onClick={() => traiterSignalement(s.id)} leftIcon={<CheckCircle2 size={14} />}>
                    Clore le signalement
                  </Btn>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div className="mb-8">
        <SectionHead
          title="Catalogue de l'établissement"
          desc="Retirez une annonce de votre propre initiative, sans attendre un signalement."
        />
        {annonces.length === 0 ? (
          <Card variant="soft"><EmptyState icon={<ShoppingBag size={24} />} title="Aucune annonce publiée" /></Card>
        ) : (
          <div className="space-y-3">
            {annonces.map((a) => (
              <Card key={a.id} className="anim-float-in">
                <div className="flex items-center justify-between gap-3 flex-wrap mb-2">
                  <div>
                    <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{a.titre}</p>
                    <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>{a.prix.toLocaleString("fr-FR")} FCFA</p>
                  </div>
                  <Badge tone={STATUT_ANNONCE_TONE[a.statut]}>{STATUT_ANNONCE_LABEL[a.statut]}</Badge>
                </div>
                {(a.statut === "disponible" || a.statut === "reservee") && (
                  <div className="flex gap-2 items-center flex-wrap">
                    <TextInput
                      placeholder="Motif de retrait"
                      value={motifRetraitParId[a.id] ?? ""}
                      onChange={(e) => setMotifRetraitParId((prev) => ({ ...prev, [a.id]: e.target.value }))}
                      style={{ minWidth: "220px" }}
                    />
                    <Btn variant="action" size="sm" loading={actionEnCoursId === a.id} onClick={() => retirer(a.id)} leftIcon={<Trash2 size={14} />}>
                      Retirer
                    </Btn>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      <SectionHead
        title="Litige et reversement"
        desc="Renseignez l'identifiant communiqué par l'élève concerné (aucune liste automatique pour l'instant)."
      />
      <div className="grid-2">
        <Card>
          <SectionHead
            title="Trancher une contestation"
            desc="Le montant est mis en séquestre par Kkiapay jusqu'à cette décision."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "16px" }}>
            <Field label="Identifiant de la contestation" required>
              <TextInput value={contestationId} onChange={(e) => setContestationId(e.target.value)} placeholder="ID contestation" />
            </Field>
            <Field label="Motif de la décision" helper="Obligatoire en cas de rejet.">
              <TextArea rows={3} value={motifDecision} onChange={(e) => setMotifDecision(e.target.value)} />
            </Field>
            <ErrorBanner>{erreurLitige}</ErrorBanner>
            <SuccessBanner>{succesLitige}</SuccessBanner>
            <div style={{ display: "flex", gap: "12px" }}>
              <Btn variant="primary" loading={enCoursDecision === "acceptee"} onClick={() => trancherLitige("acceptee")} leftIcon={<CheckCircle2 size={16} />}>
                Accepter (rembourser l'acheteur)
              </Btn>
              <Btn variant="action" loading={enCoursDecision === "rejetee"} onClick={() => trancherLitige("rejetee")} leftIcon={<XCircle size={16} />}>
                Rejeter (confirmer la transaction)
              </Btn>
            </div>
          </div>
        </Card>

        <Card>
          <SectionHead
            title="Reverser un vendeur"
            desc="Une fois la transaction confirmée (par l'acheteur ou tacitement après 5 jours), effectuez le virement Mobile Money manuellement puis enregistrez la référence ici."
          />
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "16px" }}>
            <Field label="Identifiant de la transaction" required>
              <TextInput value={transactionId} onChange={(e) => setTransactionId(e.target.value)} placeholder="ID transaction" />
            </Field>
            <Field label="Référence du paiement effectué" required>
              <TextInput value={referencePaiement} onChange={(e) => setReferencePaiement(e.target.value)} />
            </Field>
            <Btn variant="primary" loading={enCoursReversement} onClick={reverser} leftIcon={<Landmark size={16} />}>
              Confirmer le reversement
            </Btn>
          </div>
        </Card>
      </div>
    </div>
  );
}
