import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { annuairePublic, type EtablissementVitrine } from "../api/etablissements";
import { lienGoogleMaps } from "../utils/geo";
import {
  Search,
  Building2,
  GraduationCap,
  School,
  ChevronRight,
  ChevronLeft,
  ArrowLeft,
  MapPin,
  Navigation,
} from "lucide-react";

const TYPE_LABEL: Record<string, string> = { EP: "Primaire", ES: "Secondaire", UP: "Supérieur" };
const TYPE_ICON: Record<string, typeof School> = { EP: School, ES: Building2, UP: GraduationCap };

const PAGE_SIZE = 12;

export function CartesPage() {
  const [items, setItems] = useState<EtablissementVitrine[] | null>(null);
  const [total, setTotal] = useState(0);
  const [erreur, setErreur] = useState(false);
  const [q, setQ] = useState("");
  const [type, setType] = useState<"" | "EP" | "ES" | "UP">("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    setItems(null);
    setErreur(false);
    const t = setTimeout(() => {
      annuairePublic({ q: q || undefined, type: type || undefined, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
        .then((res) => {
          setItems(res.data.items);
          setTotal(res.data.total);
        })
        .catch(() => setErreur(true));
    }, 250);
    return () => clearTimeout(t);
  }, [q, type, page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const itemsAvecPosition = items?.filter((e) => e.latitude !== null && e.longitude !== null) ?? [];
  const itemsSansPosition = items?.filter((e) => e.latitude === null || e.longitude === null) ?? [];

  return (
    <div style={{ background: "var(--bg)", color: "var(--ink)", minHeight: "100dvh" }}>
      <header
        className="card-glass"
        style={{ position: "sticky", top: 0, zIndex: 10, borderRadius: 0, borderLeft: "none", borderRight: "none", borderTop: "none" }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px", height: "64px", display: "flex", alignItems: "center", gap: "16px" }}>
          <Link to="/" style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--ink-soft)", fontWeight: 600, fontSize: "var(--text-sm)", textDecoration: "none" }}>
            <ArrowLeft size={16} /> Accueil
          </Link>
          <span style={{ fontFamily: "var(--font-brand)", fontSize: "var(--text-xl)", color: "var(--ink)" }}>
            Lulu<span style={{ color: "var(--primary)" }}>·</span>Schools
          </span>
          <Link to="/etablissements" style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--ink-soft)", fontWeight: 600, fontSize: "var(--text-sm)", textDecoration: "none" }}>
            <Building2 size={16} /> Annuaire
          </Link>
        </div>
      </header>

      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "48px 24px 80px" }}>
        <p className="text-eyebrow" style={{ marginBottom: "10px" }}>Cartes</p>
        <h1 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
          Se diriger vers un établissement
        </h1>
        <p style={{ color: "var(--ink-soft)", maxWidth: "60ch", margin: "0 0 32px", fontSize: "var(--text-lg)" }}>
          Retrouvez la position de chaque établissement partenaire et ouvrez l'itinéraire dans Google Maps.
        </p>

        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "32px" }}>
          <div style={{ position: "relative", flex: "1 1 280px" }}>
            <Search size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--ink-faint)" }} />
            <input
              value={q}
              onChange={(e) => {
                setPage(0);
                setQ(e.target.value);
              }}
              placeholder="Rechercher un établissement..."
              className="field-input"
              style={{ width: "100%", paddingLeft: "40px" }}
            />
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            {(["", "EP", "ES", "UP"] as const).map((t) => (
              <button
                key={t || "tous"}
                type="button"
                className={`btn ${type === t ? "btn-primary" : "btn-outline"} btn-sm`}
                onClick={() => {
                  setPage(0);
                  setType(t);
                }}
              >
                {t === "" ? "Tous" : TYPE_LABEL[t]}
              </button>
            ))}
          </div>
        </div>

        {items === null && !erreur && (
          <div className="grid-3">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="vitrine-card">
                <div className="skeleton" style={{ height: "18px", width: "70%", marginBottom: "10px" }} />
                <div className="skeleton" style={{ height: "14px", width: "50%" }} />
              </div>
            ))}
          </div>
        )}

        {erreur && (
          <div className="card-soft" style={{ textAlign: "center", padding: "48px 24px" }}>
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>Impossible de charger la carte pour le moment.</p>
          </div>
        )}

        {items && items.length === 0 && !erreur && (
          <div className="card-soft" style={{ textAlign: "center", padding: "48px 24px" }}>
            <MapPin size={28} style={{ color: "var(--ink-faint)", marginBottom: "12px" }} aria-hidden="true" />
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>Aucun établissement ne correspond à votre recherche.</p>
          </div>
        )}

        {items && items.length > 0 && (
          <>
            <div className="grid-3">
              {itemsAvecPosition.map((etab) => {
                const Icon = TYPE_ICON[etab.type];
                return (
                  <a
                    key={etab.id}
                    href={lienGoogleMaps(etab.latitude!, etab.longitude!)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="vitrine-card card-hover"
                    style={{ textDecoration: "none", color: "inherit", display: "block" }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
                      <span
                        style={{
                          width: "40px", height: "40px", borderRadius: "var(--radius-md)",
                          background: "var(--primary-tint)", color: "var(--primary-deep)",
                          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                        }}
                        aria-hidden="true"
                      >
                        <Icon size={20} />
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-base)", fontWeight: 700, margin: 0, color: "var(--ink)" }}>
                          {etab.nom}
                        </h3>
                        <span className="chip chip-neutral" style={{ fontSize: "11px", marginTop: "4px" }}>{TYPE_LABEL[etab.type]}</span>
                      </div>
                    </div>
                    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)", color: "var(--primary-deep)" }}>
                      <Navigation size={14} aria-hidden="true" /> Itinéraire Google Maps
                    </div>
                  </a>
                );
              })}
            </div>

            {itemsSansPosition.length > 0 && (
              <p style={{ marginTop: "24px", fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
                {itemsSansPosition.length} établissement{itemsSansPosition.length > 1 ? "s" : ""} de cette page n'{itemsSansPosition.length > 1 ? "ont" : "a"} pas encore de position renseignée.
              </p>
            )}

            {totalPages > 1 && (
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "16px", marginTop: "40px" }}>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  <ChevronLeft size={14} /> Précédent
                </button>
                <span style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                  Page {page + 1} / {totalPages}
                </span>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  disabled={page + 1 >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                >
                  Suivant <ChevronRight size={14} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
