import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  Badge,
  KPITile,
  SectionHead,
  Btn,
  Skeleton,
} from "../../components/ui";
import { inscriptionsAValider } from "../../api/inscriptions";
import { listerClasses } from "../../api/etablissements";
import { listerPostes, contestationsEnAttente } from "../../api/recrutement";
import { demandesActesEtablissement } from "../../api/actes";
import {
  School,
  UserCheck,
  Briefcase,
  Scale,
  FileText,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  Building2,
  ShieldCheck,
  Award,
  Landmark,
  ClipboardList,
  AlertTriangle,
} from "lucide-react";

interface EtabMetrics {
  inscriptionsEnAttente: number | null;
  classesCount: number | null;
  postesCount: number | null;
  contestationsCount: number | null;
  demandesActesCount: number | null;
}

export function AdminEtabDashboard() {
  const etablissement = useAdminEtab();

  const [metrics, setMetrics] = useState<EtabMetrics>({
    inscriptionsEnAttente: null,
    classesCount: null,
    postesCount: null,
    contestationsCount: null,
    demandesActesCount: null,
  });
  const [loading, setLoading] = useState(true);

  const chargerMetriques = async () => {
    setLoading(true);
    try {
      const [resInscriptions, resClasses, resPostes, resContestations, resActes] =
        await Promise.allSettled([
          inscriptionsAValider(etablissement.id),
          listerClasses(etablissement.id),
          listerPostes(etablissement.id),
          contestationsEnAttente(etablissement.id),
          demandesActesEtablissement(etablissement.id),
        ]);

      setMetrics({
        inscriptionsEnAttente:
          resInscriptions.status === "fulfilled"
            ? resInscriptions.value.data.length
            : 0,
        classesCount:
          resClasses.status === "fulfilled" ? resClasses.value.data.length : 0,
        postesCount:
          resPostes.status === "fulfilled" ? resPostes.value.data.length : 0,
        contestationsCount:
          resContestations.status === "fulfilled"
            ? resContestations.value.data.length
            : 0,
        demandesActesCount:
          resActes.status === "fulfilled" ? resActes.value.data.length : 0,
      });
    } catch {
      // Fallback gracieux si une requête échoue
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    chargerMetriques();
  }, [etablissement.id]);

  const typeLabels: Record<string, string> = {
    EP: "Enseignement Primaire",
    ES: "Enseignement Secondaire",
    UP: "Université / Pôle Supérieur",
  };

  const pendingUrgentCount =
    (metrics.inscriptionsEnAttente ?? 0) + (metrics.contestationsCount ?? 0);

  const modules = [
    {
      to: "/admin-etablissement/inscriptions",
      label: "Inscriptions à valider",
      desc: "Examinez les candidatures d'élèves en attente de validation et vérifiez le consentement parental.",
      icon: UserCheck,
      tone: "action" as const,
      accentVar: "var(--action)",
      tintVar: "var(--action-tint)",
      deepVar: "var(--action-deep)",
      count: metrics.inscriptionsEnAttente,
      badgeLabel:
        metrics.inscriptionsEnAttente !== null
          ? `${metrics.inscriptionsEnAttente} à traiter`
          : "En cours",
      urgent: (metrics.inscriptionsEnAttente ?? 0) > 0,
    },
    {
      to: "/admin-etablissement/classes",
      label: "Classes & Niveaux",
      desc: "Configurez les niveaux, capacités maximales et règles de dépassement d'effectif par classe.",
      icon: School,
      tone: "primary" as const,
      accentVar: "var(--primary)",
      tintVar: "var(--primary-tint)",
      deepVar: "var(--primary-deep)",
      count: metrics.classesCount,
      badgeLabel:
        metrics.classesCount !== null
          ? `${metrics.classesCount} classe(s)`
          : "Gérer",
      urgent: false,
    },
    {
      to: "/admin-etablissement/postes",
      label: "Recrutement Enseignants",
      desc: "Créez les fiches de postes avec coefficients, barèmes automatisés par IA et consultez les candidatures.",
      icon: Briefcase,
      tone: "reward" as const,
      accentVar: "var(--reward)",
      tintVar: "var(--reward-tint)",
      deepVar: "var(--reward-deep)",
      count: metrics.postesCount,
      badgeLabel:
        metrics.postesCount !== null
          ? `${metrics.postesCount} offre(s)`
          : "Campagnes",
      urgent: false,
    },
    {
      to: "/admin-etablissement/contestations",
      label: "Contestations & Litiges",
      desc: "Traitez les requêtes d'arbitrage déposées par les candidats suite aux notations de recrutement.",
      icon: Scale,
      tone: "pending" as const,
      accentVar: "var(--action)",
      tintVar: "var(--action-tint)",
      deepVar: "var(--action-deep)",
      count: metrics.contestationsCount,
      badgeLabel:
        metrics.contestationsCount !== null
          ? `${metrics.contestationsCount} en attente`
          : "Arbitrage",
      urgent: (metrics.contestationsCount ?? 0) > 0,
    },
    {
      to: "/admin-etablissement/actes",
      label: "Actes Académiques",
      desc: "Catalogue des certificats et diplômes, traitement des demandes payantes réglées via Kkiapay.",
      icon: FileText,
      tone: "magic" as const,
      accentVar: "var(--magic)",
      tintVar: "var(--magic-tint)",
      deepVar: "var(--magic-deep)",
      count: metrics.demandesActesCount,
      badgeLabel:
        metrics.demandesActesCount !== null
          ? `${metrics.demandesActesCount} demande(s)`
          : "Catalogue",
      urgent: false,
    },
  ];

  return (
    <div className="page-content">
      {/* ── Entête Hero Établissement ── */}
      <div
        className="card anim-float-in"
        style={{
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-md)",
          background:
            "linear-gradient(135deg, var(--surface) 0%, var(--reward-tint) 100%)",
          padding: "var(--space-6) var(--space-8)",
          marginBottom: "var(--space-8)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Décoration d'arrière-plan */}
        <div
          style={{
            position: "absolute",
            right: "-20px",
            bottom: "-30px",
            opacity: 0.06,
            userSelect: "none",
            pointerEvents: "none",
            color: "var(--reward-deep)",
          }}
          aria-hidden="true"
        >
          <Landmark size={160} strokeWidth={1.2} />
        </div>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "var(--space-4)",
            position: "relative",
            zIndex: 1,
          }}
        >
          <div style={{ flex: "1 1 500px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
                marginBottom: "var(--space-2)",
                flexWrap: "wrap",
              }}
            >
              <span className="text-eyebrow" style={{ color: "var(--reward-deep)" }}>
                ADMINISTRATION D&apos;ÉTABLISSEMENT
              </span>
              <Badge tone="success" dot>
                {etablissement.statut === "public" ? "Secteur Public" : "Secteur Privé"}
              </Badge>
              <Badge tone="info" dot={false}>
                Code: {etablissement.code_etablissement}
              </Badge>
              <Badge tone="magic" dot={false}>
                {typeLabels[etablissement.type] || etablissement.type}
              </Badge>
            </div>

            <h1
              className="text-headline"
              style={{
                margin: "var(--space-1) 0 var(--space-2)",
                color: "var(--ink)",
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
              }}
            >
              <span style={{ display: "inline-flex", color: "var(--reward-deep)" }} aria-hidden="true">
                <School size={32} />
              </span>
              <span>{etablissement.nom}</span>
            </h1>

            <p
              style={{
                color: "var(--ink-soft)",
                fontSize: "var(--text-base)",
                margin: 0,
                maxWidth: "760px",
              }}
            >
              Tableau de bord de pilotage pédagogique, administratif et des ressources
              humaines. Gérez les inscriptions d&apos;élèves, le corps professoral et les
              certificats officiels.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: "var(--space-2)",
            }}
          >
            <Btn
              variant="outline"
              size="sm"
              onClick={chargerMetriques}
              loading={loading}
              leftIcon={<RefreshCw size={15} />}
            >
              Actualiser
            </Btn>
            <span
              className="font-mono text-xs"
              style={{ color: "var(--ink-faint)" }}
            >
              ID: {etablissement.id.slice(0, 8)}...
            </span>
          </div>
        </div>

        {/* Bannière d'alerte si dossiers urgents */}
        {pendingUrgentCount > 0 && (
          <div
            className="anim-pop-in"
            style={{
              marginTop: "var(--space-5)",
              padding: "var(--space-3) var(--space-4)",
              background: "var(--surface)",
              borderRadius: "var(--radius-md)",
              border: "1px solid color-mix(in srgb, var(--action-deep) 30%, transparent)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "var(--space-3)",
              boxShadow: "var(--shadow-xs)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <span style={{ display: "inline-flex", color: "var(--action-deep)" }} aria-hidden="true">
                <AlertTriangle size={22} />
              </span>
              <div>
                <strong style={{ color: "var(--action-deep)" }}>
                  {pendingUrgentCount} action(s) prioritaire(s) requise(s)
                </strong>
                <p
                  style={{
                    margin: 0,
                    fontSize: "0.85rem",
                    color: "var(--ink-soft)",
                  }}
                >
                  {(metrics.inscriptionsEnAttente ?? 0) > 0 &&
                    `${metrics.inscriptionsEnAttente} dossier(s) d'inscription à valider. `}
                  {(metrics.contestationsCount ?? 0) > 0 &&
                    `${metrics.contestationsCount} contestation(s) de recrutement en attente d'arbitrage.`}
                </p>
              </div>
            </div>
            <Link to="/admin-etablissement/inscriptions">
              <Btn variant="action" size="sm" rightIcon={<ArrowRight size={14} />}>
                Examiner
              </Btn>
            </Link>
          </div>
        )}
      </div>

      {/* ── Section KPIs Clés ── */}
      <div style={{ marginBottom: "var(--space-8)" }}>
        <SectionHead
          eyebrow="VUE D'ENSEMBLE"
          title="Indicateurs de l'Établissement"
          desc="Mesures en temps réel des effectifs, classes et processus en cours"
        />

        <div className="grid-4" style={{ marginTop: "var(--space-4)" }}>
          <KPITile
            label="Inscriptions en attente"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                metrics.inscriptionsEnAttente ?? 0
              )
            }
            accent={
              (metrics.inscriptionsEnAttente ?? 0) > 0 ? "action" : "reward"
            }
            icon={<ClipboardList size={24} />}
            sub="Dossiers d'élèves à valider"
          />

          <KPITile
            label="Classes configurées"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                metrics.classesCount ?? 0
              )
            }
            accent="primary"
            icon={<School size={24} />}
            sub="Niveaux & capacités d'accueil"
          />

          <KPITile
            label="Postes de recrutement"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                metrics.postesCount ?? 0
              )
            }
            accent="reward"
            icon={<Briefcase size={24} />}
            sub="Campagnes avec scoring IA"
          />

          <KPITile
            label="Litiges & Contestations"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                metrics.contestationsCount ?? 0
              )
            }
            accent={
              (metrics.contestationsCount ?? 0) > 0 ? "action" : "magic"
            }
            icon={<Scale size={24} />}
            sub="Candidatures sous révision"
          />
        </div>
      </div>

      {/* ── Modules de Navigation ── */}
      <div style={{ marginBottom: "var(--space-8)" }}>
        <SectionHead
          eyebrow="ESPACE OPÉRATIONNEL"
          title="Modules de Gestion de l'Établissement"
          desc="Sélectionnez un domaine pour piloter les activités scolaires et administratives"
        />

        <div
          className="grid-2"
          style={{
            marginTop: "var(--space-5)",
            gap: "var(--space-5)",
          }}
        >
          {modules.map((mod, index) => {
            const IconComponent = mod.icon;
            return (
              <Link
                key={mod.to}
                to={mod.to}
                style={{ textDecoration: "none", color: "inherit" }}
              >
                <div
                  className="card card-hover anim-float-in"
                  style={{
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    padding: "var(--space-6)",
                    animationDelay: `${index * 60}ms`,
                    border: "1px solid var(--border)",
                    boxShadow: "var(--shadow-sm)",
                    position: "relative",
                  }}
                >
                  <div>
                    {/* Ligne haute : Icône teintée + Badge d'état */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        marginBottom: "var(--space-4)",
                      }}
                    >
                      <div
                        style={{
                          width: "48px",
                          height: "48px",
                          borderRadius: "var(--radius-md)",
                          background: mod.tintVar,
                          color: mod.deepVar,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <IconComponent size={24} strokeWidth={2} />
                      </div>

                      <Badge
                        tone={
                          mod.urgent
                            ? "error"
                            : mod.tone === "action"
                            ? "pending"
                            : mod.tone === "magic"
                            ? "magic"
                            : mod.tone === "reward"
                            ? "neutral"
                            : "success"
                        }
                      >
                        {mod.badgeLabel}
                      </Badge>
                    </div>

                    {/* Titre & Description */}
                    <h3
                      className="text-title"
                      style={{
                        margin: "0 0 var(--space-2)",
                        fontSize: "1.25rem",
                        color: "var(--ink)",
                      }}
                    >
                      {mod.label}
                    </h3>
                    <p
                      style={{
                        margin: 0,
                        color: "var(--ink-soft)",
                        fontSize: "0.925rem",
                        lineHeight: 1.5,
                      }}
                    >
                      {mod.desc}
                    </p>
                  </div>

                  {/* Ligne basse : Bouton d'action */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "flex-end",
                      marginTop: "var(--space-5)",
                      paddingTop: "var(--space-3)",
                      borderTop: "1px dashed var(--border)",
                      color: mod.deepVar,
                      fontWeight: 700,
                      fontSize: "0.875rem",
                      gap: "var(--space-2)",
                    }}
                  >
                    <span>Ouvrir l&apos;interface</span>
                    <div
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "var(--radius-pill)",
                        background: mod.tintVar,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <ArrowRight size={15} />
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* ── Fiche d'Identité Institutionnelle & Sécurité ── */}
      <div
        className="card anim-float-in"
        style={{
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
          background: "var(--surface)",
          padding: "var(--space-6)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-3)",
            marginBottom: "var(--space-4)",
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "var(--radius-sm)",
              background: "var(--reward-tint)",
              color: "var(--reward-deep)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ShieldCheck size={24} />
          </div>
          <div>
            <h4
              className="text-title"
              style={{ margin: 0, fontSize: "1.1rem", color: "var(--ink)" }}
            >
              Fiche Institutionnelle & Conformité LuluSchools
            </h4>
            <span
              style={{
                fontSize: "0.825rem",
                color: "var(--ink-soft)",
              }}
            >
              Homologation active sous la tutelle du Ministère de l&apos;Éducation
            </span>
          </div>
        </div>

        <div className="grid-3" style={{ gap: "var(--space-4)" }}>
          <div
            style={{
              padding: "var(--space-3) var(--space-4)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="text-eyebrow" style={{ marginBottom: "4px" }}>
              RÉGIME JURIDIQUE
            </div>
            <div
              style={{
                fontWeight: 700,
                color: "var(--ink)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <CheckCircle2 size={16} color="var(--primary)" />
              {etablissement.statut === "public"
                ? "Établissement Public National"
                : "Établissement d'Enseignement Privé"}
            </div>
            <p
              style={{
                fontSize: "0.8rem",
                color: "var(--ink-soft)",
                margin: "4px 0 0",
              }}
            >
              Agrément ministériel vérifié et actif
            </p>
          </div>

          <div
            style={{
              padding: "var(--space-3) var(--space-4)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="text-eyebrow" style={{ marginBottom: "4px" }}>
              NIVEAU D&apos;ENSEIGNEMENT
            </div>
            <div
              style={{
                fontWeight: 700,
                color: "var(--ink)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Building2 size={16} color="var(--reward-deep)" />
              {typeLabels[etablissement.type] || etablissement.type}
            </div>
            <p
              style={{
                fontSize: "0.8rem",
                color: "var(--ink-soft)",
                margin: "4px 0 0",
              }}
            >
              Code national : {etablissement.code_etablissement}
            </p>
          </div>

          <div
            style={{
              padding: "var(--space-3) var(--space-4)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="text-eyebrow" style={{ marginBottom: "4px" }}>
              SERVICES INTÉGRÉS
            </div>
            <div
              style={{
                fontWeight: 700,
                color: "var(--ink)",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <Award size={16} color="var(--magic)" />
              Scoring IA & Paiements Kkiapay
            </div>
            <p
              style={{
                fontSize: "0.8rem",
                color: "var(--ink-soft)",
                margin: "4px 0 0",
              }}
            >
              Modules de recrutement et actes dématérialisés
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
