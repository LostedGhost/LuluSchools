import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { donnerConsentementParental, mesInscriptions } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import type { InscriptionAvecEleveOut, StatutInscription } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  KPITile,
  SectionHead,
  Skeleton,
} from "../../components/ui";
import type { ReactNode } from "react";
import { UserPlus, ChevronRight, AlertCircle, Clock, CheckCircle2, XCircle, GraduationCap, ClipboardList, TriangleAlert } from "lucide-react";

type BadgeToneLocal = "neutral" | "success" | "error" | "pending";

const LIBELLES_STATUT: Record<
  StatutInscription,
  { label: string; tone: BadgeToneLocal }
> = {
  en_attente_consentement_parental: {
    label: "Consentement requis",
    tone: "pending",
  },
  soumise: { label: "En attente de validation", tone: "neutral" },
  validee: { label: "Validée", tone: "success" },
  rejetee: { label: "Rejetée", tone: "error" },
};

const STATUS_ICON: Record<StatutInscription, ReactNode> = {
  en_attente_consentement_parental: <TriangleAlert size={15} />,
  soumise: <Clock size={15} />,
  validee: <CheckCircle2 size={15} />,
  rejetee: <XCircle size={15} />,
};

export function TuteurDashboard() {
  const [inscriptions, setInscriptions] = useState<InscriptionAvecEleveOut[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCoursId, setEnCoursId] = useState<string | null>(null);

  const charger = () => {
    mesInscriptions()
      .then((res) => setInscriptions(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, []);

  const donnerConsentement = async (id: string) => {
    setEnCoursId(id);
    setErreur(null);
    try {
      await donnerConsentementParental(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCoursId(null);
    }
  };

  /* Stats calculées */
  const validees = inscriptions?.filter((i) => i.statut === "validee").length ?? 0;
  const enAttente = inscriptions?.filter((i) => i.statut !== "validee" && i.statut !== "rejetee").length ?? 0;
  const consentementRequis = inscriptions?.filter((i) => i.statut === "en_attente_consentement_parental").length ?? 0;

  return (
    <div className="page-content">
      {/* En-tête */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <div>
          <p className="text-eyebrow" style={{ marginBottom: "6px" }}>
            Tableau de bord tuteur
          </p>
          <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>
            Mes enfants
          </h1>
        </div>
        <Link to="/tuteur/nouvelle-inscription">
          <Btn variant="primary" leftIcon={<UserPlus size={16} />}>
            Nouvelle inscription
          </Btn>
        </Link>
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>

      {/* KPI */}
      {inscriptions && inscriptions.length > 0 && (
        <div className="grid-3" style={{ marginBottom: "32px" }}>
          <KPITile label="Inscriptions actives" value={validees} accent="primary" icon={<CheckCircle2 size={24} />} />
          <KPITile label="En cours de traitement" value={enAttente} icon={<Clock size={24} />} />
          {consentementRequis > 0 ? (
            <KPITile label="Consentement requis" value={consentementRequis} accent="action" icon={<TriangleAlert size={24} />} />
          ) : (
            <KPITile label="Refusées" value={inscriptions.filter((i) => i.statut === "rejetee").length} />
          )}
        </div>
      )}

      {/* Alerte consentement */}
      {consentementRequis > 0 && (
        <div
          style={{
            background: "var(--action-tint)",
            border: "1px solid color-mix(in srgb, var(--action-deep) 30%, transparent)",
            borderRadius: "var(--radius-lg)",
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "24px",
            boxShadow: "var(--shadow-xs)",
          }}
        >
          <AlertCircle size={20} style={{ color: "var(--action-deep)", flexShrink: 0 }} />
          <p style={{ margin: 0, fontSize: "var(--text-sm)", fontWeight: 700, color: "var(--action-deep)" }}>
            {consentementRequis} inscription{consentementRequis > 1 ? "s nécessitent" : " nécessite"} votre consentement parental. Voir ci-dessous.
          </p>
        </div>
      )}

      {/* Liste */}
      <SectionHead
        eyebrow="Dossiers"
        title="Inscriptions"
        desc={
          inscriptions
            ? `${inscriptions.length} dossier${inscriptions.length > 1 ? "s" : ""} au total`
            : undefined
        }
      />

      {/* Skeleton */}
      {inscriptions === null && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ flex: 1 }}>
                <Skeleton height="18px" width="160px" className="mb-2" />
                <Skeleton height="12px" width="100px" />
              </div>
              <Skeleton height="28px" width="100px" />
            </div>
          ))}
        </div>
      )}

      {/* Vide */}
      {inscriptions?.length === 0 && (
        <Card>
          <EmptyState
            icon={<ClipboardList size={24} />}
            title="Aucune inscription"
            desc="Commencez par inscrire un enfant dans un établissement."
            action={
              <Link to="/tuteur/nouvelle-inscription">
                <Btn variant="primary" size="sm" leftIcon={<UserPlus size={14} />}>
                  Inscrire un enfant
                </Btn>
              </Link>
            }
          />
        </Card>
      )}

      {/* Cartes d'inscription */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {inscriptions?.map((inscription, i) => {
          const statut = LIBELLES_STATUT[inscription.statut];
          const needsConsent = inscription.statut === "en_attente_consentement_parental";

          return (
            <div
              key={inscription.id}
              className="card anim-float-in"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "16px",
                animationDelay: `${i * 40}ms`,
                borderColor: needsConsent ? "var(--action-deep)" : undefined,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "50%",
                    background: "var(--primary-tint)",
                    color: "var(--primary-deep)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <GraduationCap size={22} aria-hidden="true" />
                </div>
                <div>
                  <p
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 700,
                      fontSize: "var(--text-base)",
                      color: "var(--ink)",
                      margin: "0 0 3px",
                    }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ display: "inline-flex", color: "var(--ink-soft)" }} aria-hidden="true">
                        {STATUS_ICON[inscription.statut]}
                      </span>
                      {inscription.eleve_prenom} {inscription.eleve_nom}
                    </span>
                  </p>
                  {inscription.eleve_matricule && (
                    <p
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--ink-faint)",
                        margin: 0,
                      }}
                    >
                      {inscription.eleve_matricule}
                    </p>
                  )}
                  {inscription.motif_rejet && (
                    <p
                      style={{
                        fontSize: "var(--text-xs)",
                        color: "var(--action-deep)",
                        margin: "4px 0 0",
                        fontWeight: 600,
                      }}
                    >
                      Motif du rejet : {inscription.motif_rejet}
                    </p>
                  )}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
                <Badge tone={statut.tone}>{statut.label}</Badge>
                {needsConsent && (
                  <Btn
                    variant="action"
                    size="sm"
                    loading={enCoursId === inscription.id}
                    onClick={() => donnerConsentement(inscription.id)}
                    rightIcon={<ChevronRight size={14} />}
                  >
                    Donner mon consentement
                  </Btn>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
