import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { signalementsEnAttente, traiterSignalement } from "../../api/messagerie";
import { messageErreur } from "../../api/client";
import type { SignalementOut } from "../../types/api";
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
} from "../../components/ui";
import { CheckCircle2, Flag, RefreshCw } from "lucide-react";

export function SignalementsPage() {
  const etablissement = useAdminEtab();
  const [signalements, setSignalements] = useState<SignalementOut[]>([]);
  const [decisionParId, setDecisionParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    signalementsEnAttente(etablissement.id)
      .then((res) => {
        setSignalements(res.data);
        setErreur(null);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const traiter = async (id: string) => {
    if (!decisionParId[id]?.trim()) {
      setErreur("Une décision motivée est requise pour clore ce signalement.");
      return;
    }
    setErreur(null);
    setSucces(null);
    setActionEnCoursId(id);
    try {
      await traiterSignalement(id, decisionParId[id].trim());
      setSucces("Signalement traité et clos.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageTitle eyebrow="Admin Établissement">Messages signalés</PageTitle>
        <div className="flex items-center gap-2">
          <Btn variant="outline" size="sm" onClick={charger} loading={chargement} leftIcon={<RefreshCw size={14} />}>
            Actualiser
          </Btn>
          <Badge tone={signalements.length > 0 ? "pending" : "neutral"}>
            {signalements.length} en attente
          </Badge>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      <div className="mb-6">
        <SectionHead
          title="Modération de la messagerie"
          desc="Examinez les messages signalés par un membre de l'établissement et clôturez chaque dossier avec la décision prise."
        />
      </div>

      {chargement && signalements.length === 0 ? (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : signalements.length === 0 ? (
        <Card variant="soft" className="anim-float-in">
          <EmptyState
            icon={<Flag size={24} />}
            title="Aucun signalement en attente"
            desc="Aucun message de la messagerie interne n'a été signalé pour le moment."
          />
        </Card>
      ) : (
        <div className="space-y-6">
          {signalements.map((s) => {
            const isBusy = actionEnCoursId === s.id;
            return (
              <Card key={s.id} className="anim-float-in">
                <div className="flex items-center gap-3 pb-4 mb-4 border-b" style={{ borderColor: "var(--border)" }}>
                  <div
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "var(--radius-sm)",
                      background: "var(--action-tint)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "var(--action-deep)",
                    }}
                  >
                    <Flag size={18} />
                  </div>
                  <div>
                    <h3 className="m-0" style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-lg)", fontWeight: 700, color: "var(--ink)" }}>
                      Message signalé
                    </h3>
                    <span className="text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--ink-faint)" }}>
                      ID message : {s.message_id.slice(0, 8)}
                    </span>
                  </div>
                  <Badge tone="pending">En attente</Badge>
                </div>

                <div style={{ background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "var(--space-4)" }}>
                  <Field label="Décision et suite donnée" helper="Cette décision est enregistrée et le signalement est clos." required>
                    <TextArea
                      placeholder="Ex. : message supprimé et élève averti, aucune suite nécessaire..."
                      value={decisionParId[s.id] ?? ""}
                      onChange={(e) => setDecisionParId((prev) => ({ ...prev, [s.id]: e.target.value }))}
                      rows={2}
                    />
                  </Field>
                  <div className="flex justify-end mt-4">
                    <Btn variant="primary" onClick={() => traiter(s.id)} loading={isBusy} leftIcon={<CheckCircle2 size={16} />}>
                      Clore le signalement
                    </Btn>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
