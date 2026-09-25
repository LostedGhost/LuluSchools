import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  annuairePublic,
  photosPubliques,
  type EtablissementVitrine,
  type PhotoPublique,
} from "../api/etablissements";
import { Carousel } from "../components/Carousel";
import {
  Search,
  Building2,
  GraduationCap,
  School,
  Briefcase,
  ChevronRight,
  ChevronLeft,
  ArrowLeft,
} from "lucide-react";

const TYPE_LABEL: Record<string, string> = { EP: "Primaire", ES: "Secondaire", UP: "Supérieur" };
const TYPE_ICON: Record<string, ReactNode> = {
  EP: <School size={20} />,
  ES: <Building2 size={20} />,
  UP: <GraduationCap size={20} />,
};

const PAGE_SIZE = 12;

function EtablissementCard({ etab }: { etab: EtablissementVitrine }) {
  const [photos, setPhotos] = useState<PhotoPublique[]>([]);

  useEffect(() => {
    let vivant = true;
    photosPubliques(etab.id)
      .then((res) => {
        if (vivant) setPhotos(res.data);
      })
      .catch(() => undefined);
    return () => {
      vivant = false;
    };
  }, [etab.id]);

  return (
    <div className="vitrine-card" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ padding: "var(--space-3)" }}>
        <Carousel images={photos.map((p) => ({ id: p.id, url: p.url }))} />
      </div>
      <div style={{ padding: "0 var(--space-5) var(--space-5)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
          <span
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "var(--radius-md)",
              background: "var(--primary-tint)",
              color: "var(--primary-deep)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            aria-hidden="true"
          >
            {TYPE_ICON[etab.type]}
          </span>
          <span className="chip chip-neutral" style={{ fontSize: "11px" }}>{TYPE_LABEL[etab.type]}</span>
        </div>
        <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-lg)", fontWeight: 700, margin: "0 0 6px", color: "var(--ink)" }}>
          {etab.nom}
        </h3>
        <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: "0 0 14px" }}>
          {etab.statut === "public" ? "Établissement public" : "Établissement privé"} · {etab.nb_classes} classe{etab.nb_classes > 1 ? "s" : ""}
        </p>
        {etab.nb_postes_ouverts > 0 ? (
          <Link
            to="/inscription-enseignant"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)", color: "var(--primary-deep)", textDecoration: "none" }}
          >
            <Briefcase size={14} aria-hidden="true" /> {etab.nb_postes_ouverts} poste{etab.nb_postes_ouverts > 1 ? "s" : ""} ouvert{etab.nb_postes_ouverts > 1 ? "s" : ""}
          </Link>
        ) : (
          <Link
            to="/inscription-tuteur"
            style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)", color: "var(--ink-soft)", textDecoration: "none" }}
          >
            Inscriptions ouvertes <ChevronRight size={14} aria-hidden="true" />
          </Link>
        )}
      </div>
    </div>
  );
}

export function EtablissementsAnnuairePage() {
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
        </div>
      </header>

      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "48px 24px 80px" }}>
        <p className="text-eyebrow" style={{ marginBottom: "10px" }}>Annuaire national</p>
        <h1 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
          Tous les établissements partenaires
        </h1>
        <p style={{ color: "var(--ink-soft)", maxWidth: "60ch", margin: "0 0 32px", fontSize: "var(--text-lg)" }}>
          {total} établissement{total > 1 ? "s" : ""} sur la plateforme. Recherchez par nom ou filtrez par niveau.
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
                <div className="skeleton" style={{ height: "140px", marginBottom: "16px" }} />
                <div className="skeleton" style={{ height: "18px", width: "70%", marginBottom: "10px" }} />
                <div className="skeleton" style={{ height: "14px", width: "50%" }} />
              </div>
            ))}
          </div>
        )}

        {erreur && (
          <div className="card-soft" style={{ textAlign: "center", padding: "48px 24px" }}>
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>Impossible de charger l'annuaire pour le moment.</p>
          </div>
        )}

        {items && items.length === 0 && !erreur && (
          <div className="card-soft" style={{ textAlign: "center", padding: "48px 24px" }}>
            <Building2 size={28} style={{ color: "var(--ink-faint)", marginBottom: "12px" }} aria-hidden="true" />
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>Aucun établissement ne correspond à votre recherche.</p>
          </div>
        )}

        {items && items.length > 0 && (
          <>
            <div className="grid-3">
              {items.map((etab) => (
                <EtablissementCard key={etab.id} etab={etab} />
              ))}
            </div>

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
