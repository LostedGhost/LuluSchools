import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";

const liensPlateforme = [
  { to: "/etablissements", label: "Annuaire des établissements" },
  { to: "/cartes", label: "Carte" },
];

const liensLegaux = [
  { to: "/mentions-legales", label: "Mentions légales" },
  { to: "/politique-confidentialite", label: "Politique de confidentialité" },
  { to: "/cgu", label: "Conditions générales d'utilisation" },
  { to: "/politique-cookies", label: "Cookies" },
];

export function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        marginTop: "48px",
        padding: "40px 24px 28px",
      }}
    >
      <div
        style={{
          maxWidth: "1080px",
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "28px",
        }}
      >
        <div>
          <p
            style={{
              margin: "0 0 6px",
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              color: "var(--ink)",
            }}
          >
            Lulu<span style={{ color: "var(--reward)" }}>·</span>Schools
          </p>
          <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
            Plateforme éducative nationale — République du Bénin.
          </p>
        </div>

        <nav aria-label="Plateforme">
          <p className="text-label" style={{ marginBottom: "10px" }}>Plateforme</p>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
            {liensPlateforme.map((l) => (
              <li key={l.to}>
                <Link to={l.to} style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", textDecoration: "none" }}>
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <nav aria-label="Informations légales">
          <p className="text-label" style={{ marginBottom: "10px" }}>Légal</p>
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
            {liensLegaux.map((l) => (
              <li key={l.to}>
                <Link to={l.to} style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", textDecoration: "none" }}>
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div>
          <p className="text-label" style={{ marginBottom: "10px" }}>Conception & développement</p>
          <a
            href="https://www.graciotopanou.online/"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: "var(--text-sm)",
              color: "var(--ink-soft)",
              textDecoration: "none",
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            Gracio Topanou <ExternalLink size={12} aria-hidden="true" />
          </a>
        </div>
      </div>

      <p
        className="font-mono"
        style={{
          maxWidth: "1080px",
          margin: "28px auto 0",
          fontSize: "var(--text-xs)",
          color: "var(--ink-faint)",
        }}
      >
        © {new Date().getFullYear()} LuluSchools · Tous droits réservés
      </p>
    </footer>
  );
}
