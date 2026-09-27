import { User, Users } from "lucide-react";

/** Onglets « mes conversations » / « fil familial » des espaces élève et tuteur. */
export function OngletsElProfessor({
  onglet,
  onChange,
  libellePerso,
  libelleFamille,
  pastilleFamille = 0,
}: {
  onglet: "perso" | "famille";
  onChange: (o: "perso" | "famille") => void;
  libellePerso: string;
  libelleFamille: string;
  pastilleFamille?: number;
}) {
  const style = (actif: boolean) => ({
    display: "inline-flex",
    alignItems: "center",
    gap: "6px",
    padding: "8px 14px",
    border: "none",
    borderRadius: "var(--radius-pill)",
    background: actif ? "var(--primary)" : "var(--surface-2)",
    color: actif ? "var(--on-primary)" : "var(--ink-soft)",
    fontWeight: 600,
    fontSize: "var(--text-sm)",
    cursor: "pointer",
  });
  return (
    <div role="tablist" style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
      <button type="button" role="tab" aria-selected={onglet === "perso"} style={style(onglet === "perso")} onClick={() => onChange("perso")}>
        <User size={15} /> {libellePerso}
      </button>
      <button type="button" role="tab" aria-selected={onglet === "famille"} style={style(onglet === "famille")} onClick={() => onChange("famille")}>
        <Users size={15} /> {libelleFamille}
        {pastilleFamille > 0 && (
          <span
            style={{
              minWidth: "18px",
              height: "18px",
              padding: "0 5px",
              borderRadius: "var(--radius-pill)",
              background: "var(--action)",
              color: "var(--on-action)",
              fontSize: "var(--text-xs)",
              display: "inline-grid",
              placeItems: "center",
            }}
            aria-label={`${pastilleFamille} invitation(s) en attente`}
          >
            {pastilleFamille}
          </span>
        )}
      </button>
    </div>
  );
}
