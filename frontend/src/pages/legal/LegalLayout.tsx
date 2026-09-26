import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

export function LegalLayout({
  eyebrow,
  title,
  majLe,
  children,
}: {
  eyebrow: string;
  title: string;
  majLe: string;
  children: ReactNode;
}) {
  return (
    <div className="page-content" style={{ maxWidth: "760px", margin: "0 auto" }}>
      <Link
        to="/"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "var(--text-sm)",
          color: "var(--ink-faint)",
          textDecoration: "none",
          marginBottom: "24px",
        }}
      >
        <ArrowLeft size={14} /> Retour à l'accueil
      </Link>
      <p className="text-eyebrow" style={{ marginBottom: "10px" }}>{eyebrow}</p>
      <h1 className="text-headline" style={{ margin: "0 0 8px", color: "var(--ink)" }}>{title}</h1>
      <p className="font-mono" style={{ fontSize: "var(--text-xs)", color: "var(--ink-faint)", marginBottom: "32px" }}>
        Dernière mise à jour : {majLe}
      </p>
      <div className="legal-prose">{children}</div>
    </div>
  );
}
