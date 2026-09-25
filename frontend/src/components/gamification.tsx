// LuluSchools — Composants de progression élève (usage restreint à l'espace élève)
import type { ReactNode } from "react";
import { Flame, Lock, Sparkles, Trophy, Zap, Bot, TriangleAlert, Check } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   XPBar — Barre de progression expérience
   ═══════════════════════════════════════════════════════════════ */

export function XPBar({
  current,
  max,
  level,
  label,
}: {
  current: number;
  max: number;
  level?: number | string;
  label?: string;
}) {
  const pct = Math.min(100, Math.round((current / max) * 100));
  return (
    <div>
      <div className="xp-label">
        <span>
          {level !== undefined ? (
            <>
              <strong style={{ color: "var(--ink)", fontFamily: "var(--font-display)" }}>
                Niveau {level}
              </strong>
              {label && <span style={{ marginLeft: "6px" }}>{label}</span>}
            </>
          ) : (
            label
          )}
        </span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>
          {current.toLocaleString("fr-FR")} / {max.toLocaleString("fr-FR")} XP
        </span>
      </div>
      <div className="xp-track" role="progressbar" aria-valuenow={current} aria-valuemin={0} aria-valuemax={max}>
        <div className="xp-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   LevelBadge — Médaillon de niveau
   ═══════════════════════════════════════════════════════════════ */

type MedalVariant = "gold" | "green" | "magic" | "locked";

const VARIANT_ICON: Record<MedalVariant, ReactNode> = {
  gold: <Trophy size={18} />,
  magic: <Sparkles size={18} />,
  locked: <Lock size={16} />,
  green: <Check size={18} />,
};

export function LevelBadge({
  level,
  variant = "green",
  size = 52,
}: {
  level?: number | string;
  variant?: MedalVariant;
  size?: number;
}) {
  return (
    <div
      className={`medal medal-${variant}`}
      style={{ width: size, height: size }}
      aria-label={`Niveau ${level ?? ""} — ${variant}`}
    >
      {level !== undefined && variant !== "locked" ? (
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: size * 0.36,
            lineHeight: 1,
          }}
        >
          {level}
        </span>
      ) : (
        VARIANT_ICON[variant]
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MedalRow — Rangée de médaillons
   ═══════════════════════════════════════════════════════════════ */

export interface MedalDef {
  id: string;
  label: string;
  variant: MedalVariant;
  icon?: ReactNode;
}

export function MedalRow({ medals }: { medals: MedalDef[] }) {
  return (
    <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
      {medals.map((m) => (
        <div
          key={m.id}
          className={`medal medal-${m.variant}`}
          title={m.label}
          aria-label={m.label}
          style={{ width: 44, height: 44 }}
        >
          {m.icon ?? VARIANT_ICON[m.variant]}
        </div>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   StreakPill — Série de jours
   ═══════════════════════════════════════════════════════════════ */

export function StreakPill({ days }: { days: number }) {
  return (
    <div className="streak-pill" aria-label={`Série de ${days} jours`}>
      <Flame size={15} aria-hidden="true" />
      <span>
        {days} jour{days > 1 ? "s" : ""} de suite
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   FloatingXPBadge — Badge XP flottant hero
   ═══════════════════════════════════════════════════════════════ */

export function FloatingXPBadge({ amount, label = "XP" }: { amount: string | number; label?: string }) {
  return (
    <div className="badge-xp">
      +{amount}
      <span style={{ fontSize: "0.55em", display: "block", lineHeight: 1 }}>{label}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   QuestCard — Carte d'activité / mission
   ═══════════════════════════════════════════════════════════════ */

type QuestTone = "primary" | "reward" | "action" | "magic" | "info";

export function QuestCard({
  icon,
  tone = "primary",
  title,
  desc,
  xp,
  onClick,
  href,
}: {
  icon: ReactNode;
  tone?: QuestTone;
  title: string;
  desc?: string;
  xp?: string | number | null;
  onClick?: () => void;
  href?: string;
}) {
  const Tag = href ? "a" : onClick ? "button" : "div";
  return (
    <Tag
      className="quest-card"
      onClick={onClick}
      href={href as string}
      style={{ cursor: onClick || href ? "pointer" : "default" }}
    >
      <div className={`quest-icon quest-icon-${tone}`} aria-hidden="true">
        {icon}
      </div>
      <div className="quest-body">
        <p className="quest-title">{title}</p>
        {desc && <p className="quest-desc">{desc}</p>}
      </div>
      {xp != null && (
        <div className="quest-xp">+{xp} XP</div>
      )}
    </Tag>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ProgressCard3D — Carte profil élève, profondeur de perspective
   ═══════════════════════════════════════════════════════════════ */

export function ProgressCard3D({
  name,
  matricule,
  niveau,
  classe,
  xpCurrent,
  xpMax,
  level,
  streakDays,
  medals,
  offset = false,
  tiltStyle,
}: {
  name: string;
  matricule?: string;
  niveau?: string;
  classe?: string;
  xpCurrent: number;
  xpMax: number;
  level: number;
  streakDays?: number;
  medals?: MedalDef[];
  offset?: boolean;
  tiltStyle?: React.CSSProperties;
}) {
  return (
    <div
      className="card card-3d"
      style={{
        width: "300px",
        position: "absolute",
        top: offset ? "70px" : "10px",
        left: offset ? "0" : "40px",
        zIndex: offset ? 1 : 2,
        opacity: offset ? 0.55 : 1,
        filter: offset ? "saturate(.65)" : "none",
        transform: offset
          ? "perspective(1200px) rotateY(-14deg) rotateX(5deg) translateZ(-40px)"
          : "perspective(1200px) rotateY(-6deg) rotateX(2deg)",
        ...tiltStyle,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "14px",
        }}
      >
        <div>
          <div
            style={{
              fontWeight: 700,
              fontSize: "var(--text-lg)",
              fontFamily: "var(--font-display)",
            }}
          >
            {name}
          </div>
          {(matricule || classe) && (
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--ink-faint)",
              }}
            >
              {matricule && <span>{matricule}</span>}
              {matricule && classe && <span> · </span>}
              {classe && <span>{classe} {niveau && `· ${niveau}`}</span>}
            </div>
          )}
        </div>
        {streakDays !== undefined && streakDays > 0 && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              fontWeight: 700,
              color: "var(--reward-deep)",
              fontSize: "var(--text-sm)",
            }}
          >
            <Flame size={15} aria-hidden="true" /> {streakDays}
          </div>
        )}
      </div>

      <XPBar current={xpCurrent} max={xpMax} level={level} />

      {medals && medals.length > 0 && (
        <div style={{ marginTop: "16px" }}>
          <MedalRow medals={medals} />
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   AchievementToast — Notification +XP
   ═══════════════════════════════════════════════════════════════ */

export function AchievementToast({
  title,
  xp,
  icon,
}: {
  title: string;
  xp: number;
  icon?: ReactNode;
}) {
  return (
    <div className="toast anim-slide-up">
      <span
        style={{
          width: 40, height: 40, borderRadius: "var(--radius-md)",
          background: "var(--reward-tint)", color: "var(--reward-deep)",
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}
        aria-hidden="true"
      >
        {icon ?? <Trophy size={20} />}
      </span>
      <div>
        <div
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "var(--text-lg)",
            color: "var(--ink)",
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-sm)",
            color: "var(--reward-deep)",
            fontWeight: 700,
          }}
        >
          +{xp} XP
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   ScoreBurst — Affichage d'un score
   ═══════════════════════════════════════════════════════════════ */

export function ScoreBurst({
  score,
  max,
  label,
  tone = "primary",
}: {
  score: number | string;
  max?: number | string;
  label?: string;
  tone?: "primary" | "reward" | "action" | "success" | "error" | "magic";
}) {
  const colorMap: Record<string, string> = {
    primary: "var(--primary-deep)",
    reward:  "var(--reward-deep)",
    action:  "var(--action-deep)",
    success: "var(--primary-deep)",
    error:   "var(--action-deep)",
    magic:   "var(--info-deep)",
  };
  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "4px",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "var(--text-5xl)",
          fontWeight: 700,
          color: colorMap[tone] ?? colorMap.primary,
          lineHeight: 1,
        }}
      >
        {score}
        {max !== undefined && (
          <span
            style={{
              fontSize: "var(--text-xl)",
              color: "var(--ink-faint)",
              fontWeight: 600,
            }}
          >
            /{max}
          </span>
        )}
      </div>
      {label && (
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-xs)",
            color: "var(--ink-faint)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
          }}
        >
          {label}
        </span>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   AIBadge — Indicateur correction IA
   ═══════════════════════════════════════════════════════════════ */

export function AIBadge({ status }: { status: "pending" | "done" | "error" }) {
  const configs = {
    pending: { color: "var(--reward-deep)", bg: "var(--reward-tint)", label: "IA en cours…", icon: <Zap size={13} /> },
    done:    { color: "var(--primary-deep)", bg: "var(--primary-tint)", label: "Corrigé par IA", icon: <Bot size={13} /> },
    error:   { color: "var(--action-deep)", bg: "var(--action-tint)", label: "Révision requise", icon: <TriangleAlert size={13} /> },
  };
  const c = configs[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 12px",
        borderRadius: "var(--radius-pill)",
        background: c.bg,
        color: c.color,
        fontWeight: 600,
        fontSize: "var(--text-xs)",
      }}
    >
      {c.icon} {c.label}
    </span>
  );
}
