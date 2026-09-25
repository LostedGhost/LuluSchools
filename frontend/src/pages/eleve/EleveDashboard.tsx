import { Link } from "react-router-dom";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import { Card, KPITile, SectionHead, EmptyState, Btn } from "../../components/ui";
import {
  XPBar,
  StreakPill,
  MedalRow,
  QuestCard,
  LevelBadge,
  type MedalDef,
} from "../../components/gamification";
import { BookOpen, ClipboardList, Trophy, FileText, ClipboardCheck, Target, PenLine, Flag } from "lucide-react";

/* Données de gamification simulées (à remplacer par des vraies API quand disponibles) */
const DEMO_STREAK = 12;
const DEMO_XP = { current: 680, max: 1000, level: 4 };
const DEMO_MEDALS: MedalDef[] = [
  { id: "m1", label: "Premier quiz réussi", variant: "green" },
  { id: "m2", label: "Champion de la semaine", variant: "gold" },
  { id: "m3", label: "Maître des maths", variant: "magic" },
  { id: "m4", label: "À débloquer", variant: "locked" },
  { id: "m5", label: "À débloquer", variant: "locked" },
];

export function EleveDashboard() {
  const profil = useEleveProfil();

  /* ── État : pas encore inscrit ── */
  if (!profil.classe_id) {
    return (
      <div className="page-content">
        <div style={{ marginBottom: "8px" }}>
          <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>
            Bienvenue, {profil.prenom}
          </h1>
        </div>
        <div className="card" style={{ marginTop: "24px", maxWidth: "480px" }}>
          <EmptyState
            icon={<ClipboardCheck size={24} />}
            title="Inscription en attente"
            desc="Aucune inscription validée pour l'instant. Votre tuteur doit soumettre et faire valider une inscription avant que vous puissiez accéder à vos cours."
          />
        </div>
      </div>
    );
  }

  /* ── Dashboard complet ── */
  return (
    <div className="page-content">
      {/* ── En-tête personnalisé ── */}
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
            Tableau de bord élève
          </p>
          <h1
            className="text-headline"
            style={{ color: "var(--ink)", margin: "0 0 8px" }}
          >
            Salut, {profil.prenom}
          </h1>
          <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-sm)", margin: 0, fontFamily: "var(--font-mono)" }}>
            {profil.matricule} · {profil.niveau}
          </p>
        </div>
        <StreakPill days={DEMO_STREAK} />
      </div>

      {/* ── Profil XP ── */}
      <div
        className="card"
        style={{ marginBottom: "24px", background: "var(--surface-2)", borderColor: "var(--border-strong)" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "20px",
            flexWrap: "wrap",
            marginBottom: "20px",
          }}
        >
          <LevelBadge level={DEMO_XP.level} variant="green" size={72} />
          <div style={{ flex: 1, minWidth: "200px" }}>
            <XPBar
              current={DEMO_XP.current}
              max={DEMO_XP.max}
              level={DEMO_XP.level}
            />
          </div>
        </div>
        <MedalRow medals={DEMO_MEDALS} />
      </div>

      {/* ── KPI Tiles ── */}
      <div className="grid-3" style={{ marginBottom: "32px" }}>
        <KPITile
          label="Niveau actuel"
          value={DEMO_XP.level}
          accent="primary"
          icon={<Target size={24} />}
        />
        <KPITile
          label="Classe"
          value={profil.niveau ?? "—"}
          sub="EP01 · En cours"
        />
        <KPITile
          label="Série active"
          value={`${DEMO_STREAK}j`}
          accent="reward"
          icon={<Flag size={24} />}
        />
      </div>

      {/* ── Raccourcis de navigation ── */}
      <div style={{ marginBottom: "32px" }}>
        <SectionHead
          eyebrow="Navigation rapide"
          title="Accéder à vos activités"
        />
        <div className="grid-2">
          {[
            {
              to: "/eleve/cours",
              icon: <BookOpen size={24} />,
              tone: "info" as const,
              title: "Cours",
              desc: "Consulter les cours et lancer des quiz",
            },
            {
              to: "/eleve/devoirs",
              icon: <ClipboardList size={24} />,
              tone: "primary" as const,
              title: "Devoirs",
              desc: "Soumettre et suivre mes devoirs",
            },
            {
              to: "/eleve/bulletin",
              icon: <Trophy size={24} />,
              tone: "reward" as const,
              title: "Bulletin",
              desc: "Voir ma moyenne par matière",
            },
            {
              to: "/eleve/actes",
              icon: <FileText size={24} />,
              tone: "magic" as const,
              title: "Actes académiques",
              desc: "Demandes d'actes et réclamations",
            },
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              style={{ textDecoration: "none" }}
            >
              <div
                className="card card-hover"
                style={{ display: "flex", alignItems: "center", gap: "16px" }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "var(--radius-md)",
                    background: `var(--${item.tone}-tint)`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: `var(--${item.tone}-deep, var(--${item.tone}))`,
                    flexShrink: 0,
                  }}
                >
                  {item.icon}
                </div>
                <div>
                  <div
                    style={{
                      fontFamily: "var(--font-display)",
                      fontWeight: 600,
                      fontSize: "var(--text-lg)",
                      color: "var(--ink)",
                    }}
                  >
                    {item.title}
                  </div>
                  <div style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                    {item.desc}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ── Quêtes du jour ── */}
      <div>
        <SectionHead
          eyebrow="Aujourd'hui"
          title="Quêtes du jour"
          desc="Complétez ces activités pour gagner des XP et faire avancer votre progression."
        />
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <QuestCard
            icon={<BookOpen size={20} />}
            tone="info"
            title="Consulter un cours"
            desc="Lisez au moins un cours aujourd'hui"
            xp={10}
            href="/eleve/cours"
          />
          <QuestCard
            icon={<Target size={20} />}
            tone="reward"
            title="Tenter un quiz"
            desc="Obtenez au moins 60% à un quiz"
            xp={25}
            href="/eleve/cours"
          />
          <QuestCard
            icon={<PenLine size={20} />}
            tone="primary"
            title="Rendre un devoir"
            desc="Soumettez un devoir en attente"
            xp={40}
            href="/eleve/devoirs"
          />
        </div>
      </div>

      {/* ── Bulletin rapide ── */}
      <div style={{ marginTop: "32px" }}>
        <Card variant="flat">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <p className="text-eyebrow" style={{ marginBottom: "4px" }}>Bulletin · Trimestre en cours</p>
              <div
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "var(--text-5xl)",
                  fontWeight: 700,
                  color: "var(--primary-deep)",
                  lineHeight: 1,
                }}
              >
                —
                <span style={{ fontSize: "var(--text-xl)", color: "var(--ink-faint)", fontWeight: 600 }}>
                  /20
                </span>
              </div>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-faint)", marginTop: "6px" }}>
                Les résultats s'afficheront dès que des devoirs seront corrigés.
              </p>
            </div>
            <Link to="/eleve/bulletin">
              <Btn variant="outline" size="sm">
                Voir le bulletin
              </Btn>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
