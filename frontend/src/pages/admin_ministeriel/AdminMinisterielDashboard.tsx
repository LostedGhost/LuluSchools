import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  KPITile,
  SectionHead,
  Btn,
  Skeleton,
} from "../../components/ui";
import { listerEtablissements } from "../../api/etablissements";
import {
  listerReferentiels,
  type ReferentielOut,
} from "../../api/evaluations_gouvernance";
import type { EtablissementOut } from "../../types/api";
import {
  Building2,
  BookOpen,
  ArrowRight,
  RefreshCw,
  Landmark,
  CheckCircle2,
  FileCheck,
  Scale,
  Clock,
  Ruler,
  GraduationCap,
  Gavel,
} from "lucide-react";

export function AdminMinisterielDashboard() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [referentiels, setReferentiels] = useState<ReferentielOut[]>([]);
  const [loading, setLoading] = useState(true);

  const chargerDonnees = async () => {
    setLoading(true);
    try {
      const [resEtabs, resRefs] = await Promise.allSettled([
        listerEtablissements(),
        listerReferentiels(),
      ]);

      if (resEtabs.status === "fulfilled") {
        setEtablissements(resEtabs.value.data);
      }
      if (resRefs.status === "fulfilled") {
        setReferentiels(resRefs.value.data);
      }
    } catch {
      // Fallback silencieux
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    chargerDonnees();
  }, []);

  // Calculs statistiques
  const totalEtabs = etablissements.length;
  const countPublic = etablissements.filter((e) => e.statut === "public").length;
  const countPrive = etablissements.filter((e) => e.statut === "prive").length;
  const countEP = etablissements.filter((e) => e.type === "EP").length;
  const countES = etablissements.filter((e) => e.type === "ES").length;
  const countUP = etablissements.filter((e) => e.type === "UP").length;

  const totalRefs = referentiels.length;
  const countEnAttente = referentiels.filter(
    (r) => r.statut === "proposition_en_attente"
  ).length;
  const countValides = referentiels.filter((r) => r.statut === "valide").length;

  const modules = [
    {
      to: "/admin-ministeriel/etablissements",
      label: "Établissements & Homologations",
      desc: "Création d'institutions d'enseignement (EP, ES, UP), accréditations officielles et affectation des administrateurs d'établissements.",
      icon: Building2,
      tone: "magic" as const,
      accentVar: "var(--magic)",
      tintVar: "var(--magic-tint)",
      deepVar: "var(--magic-deep)",
      count: totalEtabs,
      badgeLabel:
        loading ? "Chargement..." : `${totalEtabs} homologué(s)`,
      urgent: false,
    },
    {
      to: "/admin-ministeriel/referentiels",
      label: "Référentiels de Coefficients",
      desc: "Gouvernance nationale des pondérations de bulletin, validation des coefficients officiels et arbitrage des propositions déposées.",
      icon: BookOpen,
      tone: "reward" as const,
      accentVar: "var(--reward)",
      tintVar: "var(--reward-tint)",
      deepVar: "var(--reward-deep)",
      count: countEnAttente,
      badgeLabel:
        loading
          ? "Chargement..."
          : countEnAttente > 0
          ? `${countEnAttente} à arbitrer`
          : `${countValides} validé(s)`,
      urgent: countEnAttente > 0,
    },
    {
      to: "/admin-ministeriel/micro-jobs-arbitrage",
      label: "Arbitrage Micro-jobs",
      desc: "Tranchez les contestations de missions entre membres de la communauté et validez les reversements aux prestataires.",
      icon: Gavel,
      tone: "primary" as const,
      accentVar: "var(--primary)",
      tintVar: "var(--primary-tint)",
      deepVar: "var(--primary-deep)",
      count: null,
      badgeLabel: "Arbitrer",
      urgent: false,
    },
  ];

  return (
    <div className="page-content">
      {/* ── Hero Entête Ministérielle ── */}
      <div
        className="card anim-float-in"
        style={{
          border: "1px solid var(--border)",
          boxShadow: "var(--shadow-md)",
          background:
            "linear-gradient(135deg, var(--surface) 0%, var(--magic-tint) 100%)",
          padding: "var(--space-6) var(--space-8)",
          marginBottom: "var(--space-8)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Symbole d'arrière-plan */}
        <div
          style={{
            position: "absolute",
            right: "-20px",
            bottom: "-35px",
            opacity: 0.06,
            userSelect: "none",
            pointerEvents: "none",
            color: "var(--magic-deep)",
          }}
          aria-hidden="true"
        >
          <Landmark size={170} strokeWidth={1.2} />
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
              <span className="text-eyebrow" style={{ color: "var(--magic-deep)" }}>
                MINISTÈRE DE L&apos;ÉDUCATION NATIONALE
              </span>
              <Badge tone="magic" dot>
                Gouvernance Centrale
              </Badge>
              <Badge tone="info" dot={false}>
                Réseau LuluSchools
              </Badge>
              <Badge tone="neutral" dot={false}>
                Portail de Régulation
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
              <span style={{ display: "inline-flex", color: "var(--magic-deep)" }} aria-hidden="true">
                <Scale size={32} />
              </span>
              <span>Administration Ministérielle</span>
            </h1>

            <p
              style={{
                color: "var(--ink-soft)",
                fontSize: "var(--text-base)",
                margin: 0,
                maxWidth: "760px",
              }}
            >
              Pilotage stratégique du réseau éducatif national. Supervisez
              l&apos;ensemble des établissements scolaires et supérieurs, régulez les
              normes d&apos;évaluation et assurez la conformité des barèmes académiques.
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
              onClick={chargerDonnees}
              loading={loading}
              leftIcon={<RefreshCw size={15} />}
            >
              Actualiser
            </Btn>
            <span
              className="font-mono text-xs"
              style={{ color: "var(--ink-faint)" }}
            >
              Supervision Nationale
            </span>
          </div>
        </div>

        {/* Bannière de propositions en attente d'arbitrage */}
        {countEnAttente > 0 && (
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
                <Clock size={22} />
              </span>
              <div>
                <strong style={{ color: "var(--action-deep)" }}>
                  {countEnAttente} proposition(s) de pondération en attente d&apos;approbation
                </strong>
                <p
                  style={{
                    margin: 0,
                    fontSize: "0.85rem",
                    color: "var(--ink-soft)",
                  }}
                >
                  Des modifications de coefficients ont été soumises pour arbitrage
                  ministériel avant application aux bulletins officiels.
                </p>
              </div>
            </div>
            <Link to="/admin-ministeriel/referentiels">
              <Btn variant="action" size="sm" rightIcon={<ArrowRight size={14} />}>
                Arbitrer
              </Btn>
            </Link>
          </div>
        )}
      </div>

      {/* ── Indicateurs Nationaux ── */}
      <div style={{ marginBottom: "var(--space-8)" }}>
        <SectionHead
          eyebrow="SUPERVISION NATIONALE"
          title="Indicateurs de Pilotage Ministériel"
          desc="Vue globale sur le maillage des établissements et le système de notation"
        />

        <div className="grid-4" style={{ marginTop: "var(--space-4)" }}>
          <KPITile
            label="Établissements homologués"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                totalEtabs
              )
            }
            accent="magic"
            icon={<Landmark size={24} />}
            sub={
              loading
                ? "Chargement..."
                : `${countPublic} publics • ${countPrive} privés`
            }
          />

          <KPITile
            label="Propositions à valider"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                countEnAttente
              )
            }
            accent={countEnAttente > 0 ? "action" : "magic"}
            icon={<Clock size={24} />}
            sub={
              countEnAttente > 0
                ? "Arbitrage urgent requis"
                : "Aucune requête en attente"
            }
          />

          <KPITile
            label="Référentiels actifs"
            value={
              loading ? (
                <Skeleton height="32px" width="60px" />
              ) : (
                countValides
              )
            }
            accent="reward"
            icon={<Ruler size={24} />}
            sub={`${countValides} sur ${totalRefs} pondérations certifiées`}
          />

          <KPITile
            label="Couverture académique"
            value={loading ? <Skeleton height="32px" width="60px" /> : 3}
            accent="primary"
            icon={<GraduationCap size={24} />}
            sub="Filières EP, ES & UP"
          />
        </div>
      </div>

      {/* ── Modules de Pilotage Ministériel ── */}
      <div style={{ marginBottom: "var(--space-8)" }}>
        <SectionHead
          eyebrow="ESPACE DÉCISIONNEL"
          title="Missions & Portails Ministériels"
          desc="Accédez aux interfaces de régulation et de gestion administrative"
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
                    animationDelay: `${index * 80}ms`,
                    border: "1px solid var(--border)",
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  <div>
                    {/* En-tête de carte : Icône teintée + Badge statut */}
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
                            : mod.tone === "magic"
                            ? "magic"
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

                  {/* Bouton d'action */}
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
                    <span>Accéder au portail</span>
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

      {/* ── Cartographie du Réseau & Normes Académiques ── */}
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
            marginBottom: "var(--space-5)",
          }}
        >
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "var(--radius-sm)",
              background: "var(--magic-tint)",
              color: "var(--magic-deep)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Landmark size={24} />
          </div>
          <div>
            <h4
              className="text-title"
              style={{ margin: 0, fontSize: "1.1rem", color: "var(--ink)" }}
            >
              Cartographie & Règles de Gouvernance LuluSchools
            </h4>
            <span style={{ fontSize: "0.825rem", color: "var(--ink-soft)" }}>
              Directives nationales et intégrité du système éducatif dématérialisé
            </span>
          </div>
        </div>

        <div className="grid-3" style={{ gap: "var(--space-4)" }}>
          <div
            style={{
              padding: "var(--space-4)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="text-eyebrow" style={{ marginBottom: "6px" }}>
              RÉPARTITION INSTITUTIONNELLE
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.875rem",
                  color: "var(--ink)",
                }}
              >
                <span>Établissements Primaires (EP) :</span>
                <strong>{countEP}</strong>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.875rem",
                  color: "var(--ink)",
                }}
              >
                <span>Enseignement Secondaire (ES) :</span>
                <strong>{countES}</strong>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.875rem",
                  color: "var(--ink)",
                }}
              >
                <span>Universités & Supérieur (UP) :</span>
                <strong>{countUP}</strong>
              </div>
            </div>
          </div>

          <div
            style={{
              padding: "var(--space-4)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="text-eyebrow" style={{ marginBottom: "6px" }}>
              STATUT DES CODES D&apos;HOMOLOGATION
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "6px",
                color: "var(--ink)",
                fontWeight: 700,
              }}
            >
              <CheckCircle2 size={18} color="var(--primary)" />
              <span>Génération Cryptographique</span>
            </div>
            <p
              style={{
                margin: 0,
                fontSize: "0.8rem",
                color: "var(--ink-soft)",
                lineHeight: 1.4,
              }}
            >
              Chaque établissement reçoit un code unique non-falsifiable garantissant
              l&apos;authenticité des diplômes et relevés de notes émis.
            </p>
          </div>

          <div
            style={{
              padding: "var(--space-4)",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="text-eyebrow" style={{ marginBottom: "6px" }}>
              COMMISSION DES PONDÉRATIONS
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "6px",
                color: "var(--ink)",
                fontWeight: 700,
              }}
            >
              <FileCheck size={18} color="var(--magic)" />
              <span>{countValides} Pondérations Standardisées</span>
            </div>
            <p
              style={{
                margin: 0,
                fontSize: "0.8rem",
                color: "var(--ink-soft)",
                lineHeight: 1.4,
              }}
            >
              Les pondérations régissent les moyennes pondérées et la délivrance des
              diplômes au sein de la république scolaire numérique.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
