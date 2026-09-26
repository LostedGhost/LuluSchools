import { Link } from "react-router-dom";
import { KPITile, SectionHead } from "../../components/ui";
import { QuestCard } from "../../components/gamification";
import {
  Briefcase,
  ScrollText,
  FileText,
  BookOpen,
  PencilRuler,
  TrendingUp,
  CheckCircle2,
  Bot,
  Radio,
  Ticket,
  ShieldCheck,
  Handshake,
  MessageCircle,
} from "lucide-react";

const NAV_CARDS = [
  {
    to: "/enseignant/postes",
    icon: <Briefcase size={24} />,
    tone: "info" as const,
    title: "Postes ouverts",
    desc: "Parcourir et postuler aux offres disponibles",
  },
  {
    to: "/enseignant/candidatures",
    icon: <ScrollText size={24} />,
    tone: "primary" as const,
    title: "Mes candidatures",
    desc: "Suivre l'avancement et contester",
  },
  {
    to: "/enseignant/contrats",
    icon: <FileText size={24} />,
    tone: "reward" as const,
    title: "Mes contrats",
    desc: "Signature électronique et archivage",
  },
  {
    to: "/enseignant/cours",
    icon: <BookOpen size={24} />,
    tone: "info" as const,
    title: "Mes cours",
    desc: "Publier, générer des quiz IA",
  },
  {
    to: "/enseignant/devoirs",
    icon: <PencilRuler size={24} />,
    tone: "action" as const,
    title: "Mes devoirs",
    desc: "Créer, corriger, noter",
  },
  {
    to: "/enseignant/cours-direct",
    icon: <Radio size={24} />,
    tone: "primary" as const,
    title: "Cours en direct",
    desc: "Planifier et animer des sessions live",
  },
  {
    to: "/billetterie",
    icon: <Ticket size={24} />,
    tone: "reward" as const,
    title: "Billetterie",
    desc: "Événements de mon établissement",
  },
  {
    to: "/micro-jobs",
    icon: <Handshake size={24} />,
    tone: "action" as const,
    title: "Micro-jobs",
    desc: "Proposer ou accepter un service ponctuel",
  },
  {
    to: "/valider-acces",
    icon: <ShieldCheck size={24} />,
    tone: "info" as const,
    title: "Valider un accès",
    desc: "Si vous êtes contrôleur désigné",
  },
  {
    to: "/messagerie",
    icon: <MessageCircle size={24} />,
    tone: "info" as const,
    title: "Messagerie",
    desc: "Groupes de classe et messages privés",
  },
];

export function EnseignantDashboard() {
  return (
    <div className="page-content">
      {/* En-tête */}
      <div style={{ marginBottom: "32px" }}>
        <p className="text-eyebrow" style={{ marginBottom: "6px" }}>
          Tableau de bord enseignant
        </p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: "0 0 8px" }}>
          Espace enseignant
        </h1>
        <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-sm)", margin: 0 }}>
          Gérez votre carrière, vos cours et vos élèves depuis un seul endroit.
        </p>
      </div>

      {/* KPI rapide */}
      <div className="grid-3" style={{ marginBottom: "32px" }}>
        <KPITile
          label="Statut"
          value="Actif"
          accent="primary"
          icon={<CheckCircle2 size={24} />}
        />
        <KPITile
          label="Postes ouverts"
          value="—"
          sub="Consultez les annonces"
        />
        <KPITile
          label="Quiz générés"
          value="IA"
          accent="magic"
          icon={<Bot size={24} />}
        />
      </div>

      {/* Navigation principale */}
      <SectionHead
        eyebrow="Navigation rapide"
        title="Accéder à vos espaces"
      />
      <div className="grid-2" style={{ marginBottom: "32px" }}>
        {NAV_CARDS.map((card, i) => (
          <Link
            key={card.to}
            to={card.to}
            style={{ textDecoration: "none" }}
          >
            <div
              className="card card-hover anim-float-in"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
                animationDelay: `${i * 60}ms`,
              }}
            >
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "var(--radius-md)",
                  background: `var(--${card.tone}-tint)`,
                  color: `var(--${card.tone}-deep, var(--${card.tone}))`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {card.icon}
              </div>
              <div>
                <p
                  style={{
                    fontFamily: "var(--font-display)",
                    fontWeight: 600,
                    fontSize: "var(--text-lg)",
                    color: "var(--ink)",
                    margin: "0 0 3px",
                  }}
                >
                  {card.title}
                </p>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: 0 }}>
                  {card.desc}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Quêtes enseignant */}
      <SectionHead
        eyebrow="À faire"
        title="Actions prioritaires"
        desc="Complétez ces actions pour maintenir votre dossier à jour."
      />
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <QuestCard
          icon={<Briefcase size={20} />}
          tone="info"
          title="Consulter les postes ouverts"
          desc="De nouvelles offres peuvent être disponibles"
          href="/enseignant/postes"
        />
        <QuestCard
          icon={<BookOpen size={20} />}
          tone="magic"
          title="Publier un cours"
          desc="Partagez vos ressources pédagogiques avec vos élèves"
          href="/enseignant/cours"
        />
        <QuestCard
          icon={<PencilRuler size={20} />}
          tone="action"
          title="Créer un devoir"
          desc="Évaluez la progression de vos élèves"
          href="/enseignant/devoirs"
        />
      </div>

      {/* Bloc IA */}
      <div
        style={{
          marginTop: "32px",
          background: "var(--magic-tint)",
          border: "1px solid color-mix(in srgb, var(--magic-deep) 30%, transparent)",
          borderRadius: "var(--radius-xl)",
          padding: "32px",
          boxShadow: "var(--shadow-sm)",
          display: "flex",
          alignItems: "center",
          gap: "20px",
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "var(--radius-md)",
            background: "var(--surface)",
            color: "var(--magic-deep)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Bot size={28} aria-hidden="true" />
        </div>
        <div>
          <p
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "var(--text-xl)",
              color: "var(--magic-deep)",
              margin: "0 0 6px",
            }}
          >
            Correction IA activée
          </p>
          <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: "0 0 14px", maxWidth: "44ch" }}>
            Vos devoirs peuvent être corrigés automatiquement par l'IA. La correction finale vous appartient toujours.
          </p>
          <Link to="/enseignant/devoirs">
            <span
              className="btn btn-magic btn-sm"
              style={{ display: "inline-flex" }}
            >
              <TrendingUp size={14} />
              Voir mes devoirs
            </span>
          </Link>
        </div>
      </div>
    </div>
  );
}
