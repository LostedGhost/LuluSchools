/* Avatar — Composant avatar rôle-spécifique */
import type { ReactNode } from "react";
import { Users, GraduationCap, BookOpen, Building2, Landmark } from "lucide-react";

type Role =
  | "tuteur"
  | "eleve"
  | "enseignant"
  | "admin_etablissement"
  | "admin_ministeriel";

const ROLE_CONFIGS: Record<
  Role,
  { bg: string; color: string; icon: ReactNode; label: string }
> = {
  tuteur: {
    bg: "var(--info-tint)",
    color: "var(--info-deep)",
    icon: <Users size={16} />,
    label: "Tuteur",
  },
  eleve: {
    bg: "var(--primary-tint)",
    color: "var(--primary-deep)",
    icon: <GraduationCap size={16} />,
    label: "Élève",
  },
  enseignant: {
    bg: "var(--info-tint)",
    color: "var(--info-deep)",
    icon: <BookOpen size={16} />,
    label: "Enseignant",
  },
  admin_etablissement: {
    bg: "var(--reward-tint)",
    color: "var(--reward-deep)",
    icon: <Building2 size={16} />,
    label: "Admin Établissement",
  },
  admin_ministeriel: {
    bg: "var(--surface-2)",
    color: "var(--ink)",
    icon: <Landmark size={16} />,
    label: "Admin Ministériel",
  },
};

function getInitials(prenom?: string, nom?: string): string {
  const p = prenom?.[0]?.toUpperCase() ?? "";
  const n = nom?.[0]?.toUpperCase() ?? "";
  return p + n || "?";
}

export function Avatar({
  role,
  prenom,
  nom,
  size = 40,
  showInitials = true,
}: {
  role: Role | string;
  prenom?: string;
  nom?: string;
  size?: number;
  showInitials?: boolean;
}) {
  const cfg =
    ROLE_CONFIGS[role as Role] ?? ROLE_CONFIGS.eleve;
  const initials = getInitials(prenom, nom);
  const showLetters = showInitials && initials !== "?";

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: cfg.bg,
        border: `1.5px solid color-mix(in srgb, ${cfg.color} 30%, transparent)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.38,
        fontFamily: "var(--font-display)",
        fontWeight: 700,
        color: cfg.color,
        flexShrink: 0,
        userSelect: "none",
      }}
      aria-label={`${cfg.label} ${prenom ?? ""} ${nom ?? ""}`}
      title={`${cfg.label} — ${prenom ?? ""} ${nom ?? ""}`}
    >
      {showLetters ? initials : cfg.icon}
    </div>
  );
}

export function RolePill({ role }: { role: Role | string }) {
  const cfg = ROLE_CONFIGS[role as Role];
  if (!cfg) return null;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "5px",
        padding: "3px 10px",
        borderRadius: "var(--radius-pill)",
        background: cfg.bg,
        color: cfg.color,
        fontSize: "var(--text-xs)",
        fontWeight: 600,
      }}
    >
      {cfg.icon} {cfg.label}
    </span>
  );
}
