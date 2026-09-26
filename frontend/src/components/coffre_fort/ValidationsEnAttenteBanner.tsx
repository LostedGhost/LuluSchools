import { useEffect, useState } from "react";
import { mesValidationsEnAttente } from "../../api/coffre_fort";
import type { ValidationParentaleOut } from "../../types/api";
import { TriangleAlert } from "lucide-react";

const LABEL_MODULE: Record<string, string> = {
  micro_job: "une offre de micro-job",
  marketplace: "un achat sur le marketplace",
  acte: "une demande d'acte",
};

/** UC-35.2 : "jamais un blocage silencieux" - l'élève doit pouvoir constater que l'une
 * de ses dépenses attend une validation de son tuteur, même s'il ne peut rien y faire
 * lui-même (juste patienter ou en parler à son tuteur). */
export function ValidationsEnAttenteBanner() {
  const [validations, setValidations] = useState<ValidationParentaleOut[]>([]);

  useEffect(() => {
    mesValidationsEnAttente()
      .then((res) => setValidations(res.data))
      .catch(() => undefined);
  }, []);

  if (validations.length === 0) return null;

  return (
    <div
      style={{
        background: "var(--action-tint)",
        border: "1px solid color-mix(in srgb, var(--action-deep) 30%, transparent)",
        borderRadius: "var(--radius-lg)",
        padding: "14px 18px",
        display: "flex",
        alignItems: "flex-start",
        gap: "10px",
        marginBottom: "24px",
      }}
    >
      <TriangleAlert size={18} style={{ color: "var(--action-deep)", flexShrink: 0, marginTop: "2px" }} />
      <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--action-deep)", fontWeight: 600 }}>
        {validations.length === 1 ? "Une dépense" : `${validations.length} dépenses`} attend
        {validations.length === 1 ? "" : "ent"} la validation de votre tuteur avant de pouvoir continuer :{" "}
        {validations.map((v) => LABEL_MODULE[v.module] ?? v.module).join(", ")}.
      </p>
    </div>
  );
}
