import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { contestationsEnAttente, deciderContestation } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ContestationOut } from "../../types/api";
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
import {
  CheckCircle2,
  XCircle,
  RefreshCw,
  Scale,
  FileText,
  Clock,
  AlertTriangle,
} from "lucide-react";

const STATUT_CONFIG: Record<
  string,
  { label: string; tone: "pending" | "success" | "error" }
> = {
  en_attente: { label: "En attente", tone: "pending" },
  traitee: { label: "Traitée", tone: "success" },
  acceptee: { label: "Approuvée", tone: "success" },
  rejetee: { label: "Rejetée", tone: "error" },
};

export function ContestationsPage() {
  const etablissement = useAdminEtab();
  const [contestations, setContestations] = useState<ContestationOut[]>([]);
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    contestationsEnAttente(etablissement.id)
      .then((res) => {
        setContestations(res.data);
        setErreur(null);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const decider = async (id: string, decision: "acceptee" | "rejetee") => {
    if (decision === "rejetee" && !motifParId[id]?.trim()) {
      setErreur("Un motif est requis en cas de rejet d'une contestation.");
      return;
    }
    setErreur(null);
    setSucces(null);
    setActionEnCoursId(id);
    try {
      await deciderContestation(id, decision, motifParId[id]?.trim());
      setSucces(
        decision === "acceptee"
          ? "Contestation approuvée avec succès !"
          : "Contestation rejetée."
      );
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      {/* En-tête de la page */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageTitle eyebrow="Admin Établissement">
          Contestations et litiges
        </PageTitle>
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
          <Badge tone={contestations.length > 0 ? "pending" : "neutral"}>
            {contestations.length} dossier{contestations.length > 1 ? "s" : ""}
          </Badge>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      <div className="mb-6">
        <SectionHead
          title="Dossiers de litige en attente d'arbitrage"
          desc="Examinez les contestations relatives aux candidatures et évaluations. Toute décision de rejet doit être rigoureusement motivée."
        />
      </div>

      {chargement && contestations.length === 0 ? (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : contestations.length === 0 ? (
        <Card variant="soft" className="anim-float-in">
          <EmptyState
            icon={<Scale size={24} />}
            title="Aucune contestation en attente"
            desc="Tous les litiges et réclamations ont été résolus ou arbitrés par la direction de l'établissement."
          />
        </Card>
      ) : (
        <div className="space-y-6">
          {contestations.map((c, idx) => {
            const isBusy = actionEnCoursId === c.id;
            const statutInfo = STATUT_CONFIG[c.statut] || {
              label: c.statut,
              tone: "pending" as const,
            };
            const delayClass = `delay-${(idx % 3) + 1}`;

            return (
              <Card
                key={c.id}
                className={`anim-float-in ${delayClass} transition-all`}
              >
                {/* En-tête du litige */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b" style={{ borderColor: "var(--border)" }}>
                  <div className="flex items-center gap-3">
                    <div
                      style={{
                        width: "40px",
                        height: "40px",
                        borderRadius: "var(--radius-sm)",
                        background: "var(--reward-tint)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--reward-deep)",
                      }}
                    >
                      <Scale size={20} />
                    </div>
                    <div>
                      <h3
                        className="m-0"
                        style={{
                          fontFamily: "var(--font-display)",
                          fontSize: "var(--text-lg)",
                          fontWeight: 700,
                          color: "var(--ink)",
                        }}
                      >
                        Contestataire — Dossier #{c.candidature_id.slice(0, 8)}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: "var(--ink-faint)" }}>
                        <span className="flex items-center gap-1">
                          <FileText size={12} />
                          Contestation ID :{" "}
                          <span style={{ fontFamily: "var(--font-mono)" }}>
                            {c.id.slice(0, 8)}
                          </span>
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock size={12} />
                          Statut commission : Actif
                        </span>
                      </div>
                    </div>
                  </div>

                  <Badge tone={statutInfo.tone}>
                    {statutInfo.label}
                  </Badge>
                </div>

                {/* Motif formulé par le contestataire */}
                <div className="mb-5">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle size={15} style={{ color: "var(--reward-deep)" }} />
                    <span
                      className="text-xs font-bold uppercase tracking-wider"
                      style={{ color: "var(--ink-soft)", fontFamily: "var(--font-mono)" }}
                    >
                      Motif de la contestation formulé par le candidat
                    </span>
                  </div>
                  <div
                    style={{
                      background: "var(--surface-2)",
                      border: "1.5px solid var(--border)",
                      borderRadius: "var(--radius-md)",
                      padding: "var(--space-4)",
                      color: "var(--ink)",
                      fontSize: "var(--text-sm)",
                      lineHeight: 1.5,
                      fontStyle: "italic",
                    }}
                  >
                    "{c.motif}"
                  </div>
                </div>

                {/* Formulaire d'arbitrage */}
                <div
                  style={{
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    padding: "var(--space-4)",
                  }}
                >
                  <Field
                    label="Motivation et conclusions de l'arbitrage"
                    helper="Exigez des justificatifs complémentaires ou détaillez les motifs légaux de la décision."
                    required
                  >
                    <TextArea
                      placeholder="Indiquez les conclusions de la commission d'arbitrage (obligatoire pour un rejet)..."
                      value={motifParId[c.id] ?? ""}
                      onChange={(e) =>
                        setMotifParId((prev) => ({
                          ...prev,
                          [c.id]: e.target.value,
                        }))
                      }
                      rows={3}
                    />
                  </Field>

                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3 mt-4">
                    <Btn
                      type="button"
                      variant="action"
                      size="md"
                      onClick={() => decider(c.id, "rejetee")}
                      loading={isBusy}
                      leftIcon={<XCircle size={16} />}
                    >
                      Rejeter
                    </Btn>
                    <Btn
                      type="button"
                      variant="primary"
                      size="md"
                      onClick={() => decider(c.id, "acceptee")}
                      loading={isBusy}
                      leftIcon={<CheckCircle2 size={16} />}
                    >
                      Approuver la contestation
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
