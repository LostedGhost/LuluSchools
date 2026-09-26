import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { annuairePublic, type EtablissementVitrine } from "../api/etablissements";
import { lienGoogleMaps } from "../utils/geo";
import { Search, Building2, GraduationCap, School, ArrowLeft, MapPin, Navigation } from "lucide-react";

// Corrige un problème connu de Leaflet + bundlers (Vite) : les URLs d'icônes par
// défaut, calculées depuis import.meta.url, ne résolvent pas correctement - on les
// réimporte explicitement comme assets Vite plutôt que de les laisser casser en silence.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const TYPE_LABEL: Record<string, string> = { EP: "Primaire", ES: "Secondaire", UP: "Supérieur" };
const TYPE_ICON: Record<string, typeof School> = { EP: School, ES: Building2, UP: GraduationCap };

// Centre par défaut : Cotonou, en l'absence de tout établissement géolocalisé.
const CENTRE_PAR_DEFAUT: [number, number] = [6.3703, 2.3912];
const PAGE_LIMIT = 60; // plafond serveur (voir annuaire_public côté backend)

function AjusterVue({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], 14);
    } else {
      map.fitBounds(points, { padding: [40, 40] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(points)]);
  return null;
}

function VolerVersSelection({ point }: { point: [number, number] | null }) {
  const map = useMap();
  useEffect(() => {
    if (point) map.flyTo(point, 16);
  }, [point, map]);
  return null;
}

export function CartesPage() {
  const [items, setItems] = useState<EtablissementVitrine[] | null>(null);
  const [erreur, setErreur] = useState(false);
  const [q, setQ] = useState("");
  const [type, setType] = useState<"" | "EP" | "ES" | "UP">("");
  const [selectionId, setSelectionId] = useState<string | null>(null);

  useEffect(() => {
    setItems(null);
    setErreur(false);
    setSelectionId(null);
    const t = setTimeout(async () => {
      try {
        // Recupere TOUTES les pages correspondant au filtre (une carte n'a pas de
        // pagination - on veut chaque etablissement filtre simultanement).
        const premiere = await annuairePublic({ q: q || undefined, type: type || undefined, limit: PAGE_LIMIT, offset: 0 });
        let tous = premiere.data.items;
        let recupere = tous.length;
        while (recupere < premiere.data.total) {
          const suite = await annuairePublic({ q: q || undefined, type: type || undefined, limit: PAGE_LIMIT, offset: recupere });
          tous = tous.concat(suite.data.items);
          recupere += suite.data.items.length;
          if (suite.data.items.length === 0) break;
        }
        setItems(tous);
      } catch {
        setErreur(true);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q, type]);

  const avecPosition = useMemo(
    () => (items ?? []).filter((e): e is EtablissementVitrine & { latitude: number; longitude: number } => e.latitude !== null && e.longitude !== null),
    [items],
  );
  const sansPosition = (items ?? []).filter((e) => e.latitude === null || e.longitude === null);
  const points: [number, number][] = avecPosition.map((e) => [e.latitude, e.longitude]);
  const selection = avecPosition.find((e) => e.id === selectionId) ?? null;

  return (
    <div style={{ background: "var(--bg)", color: "var(--ink)", minHeight: "100dvh" }}>
      <header
        className="card-glass"
        style={{ position: "sticky", top: 0, zIndex: 10, borderRadius: 0, borderLeft: "none", borderRight: "none", borderTop: "none" }}
      >
        <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "0 24px", height: "64px", display: "flex", alignItems: "center", gap: "16px" }}>
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

      <div style={{ maxWidth: "1280px", margin: "0 auto", padding: "48px 24px 80px" }}>
        <p className="text-eyebrow" style={{ marginBottom: "10px" }}>Cartes</p>
        <h1 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
          Se diriger vers un établissement
        </h1>
        <p style={{ color: "var(--ink-soft)", maxWidth: "60ch", margin: "0 0 32px", fontSize: "var(--text-lg)" }}>
          Carte interactive de tous les établissements partenaires (OpenStreetMap). Cliquez un repère pour ses informations, ou lancez l'itinéraire Google Maps.
        </p>

        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "24px" }}>
          <div style={{ position: "relative", flex: "1 1 280px" }}>
            <Search size={16} style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "var(--ink-faint)" }} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
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
                onClick={() => setType(t)}
              >
                {t === "" ? "Tous" : TYPE_LABEL[t]}
              </button>
            ))}
          </div>
        </div>

        {erreur && (
          <div className="card-soft" style={{ textAlign: "center", padding: "48px 24px" }}>
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>Impossible de charger la carte pour le moment.</p>
          </div>
        )}

        {items === null && !erreur && (
          <div className="skeleton" style={{ height: "560px", borderRadius: "var(--radius-lg)" }} />
        )}

        {items !== null && !erreur && (
          <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "16px", alignItems: "stretch" }}>
            <div
              className="card-soft"
              style={{ height: "560px", overflowY: "auto", padding: "var(--space-3)", display: "flex", flexDirection: "column", gap: "6px" }}
            >
              {avecPosition.length === 0 ? (
                <div style={{ textAlign: "center", padding: "24px 8px", color: "var(--ink-faint)" }}>
                  <MapPin size={22} style={{ marginBottom: "8px" }} aria-hidden="true" />
                  <p style={{ margin: 0, fontSize: "var(--text-sm)" }}>Aucun établissement géolocalisé ne correspond à votre recherche.</p>
                </div>
              ) : (
                avecPosition.map((etab) => {
                  const Icon = TYPE_ICON[etab.type];
                  const actif = etab.id === selectionId;
                  return (
                    <button
                      key={etab.id}
                      type="button"
                      onClick={() => setSelectionId(etab.id)}
                      style={{
                        display: "flex", alignItems: "center", gap: "10px", padding: "10px 12px",
                        borderRadius: "var(--radius-md)", border: "none", textAlign: "left", cursor: "pointer",
                        background: actif ? "var(--primary-tint)" : "transparent",
                        color: actif ? "var(--primary-deep)" : "var(--ink)",
                      }}
                    >
                      <Icon size={16} style={{ flexShrink: 0 }} aria-hidden="true" />
                      <span style={{ fontSize: "var(--text-sm)", fontWeight: actif ? 700 : 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {etab.nom}
                      </span>
                    </button>
                  );
                })
              )}
              {sansPosition.length > 0 && (
                <p style={{ margin: "8px 4px 0", fontSize: "var(--text-xs)", color: "var(--ink-faint)" }}>
                  + {sansPosition.length} sans position renseignée
                </p>
              )}
            </div>

            <div style={{ height: "560px", borderRadius: "var(--radius-lg)", overflow: "hidden", border: "1px solid var(--border)" }}>
              <MapContainer center={CENTRE_PAR_DEFAUT} zoom={7} style={{ height: "100%", width: "100%" }}>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <AjusterVue points={points} />
                <VolerVersSelection point={selection ? [selection.latitude, selection.longitude] : null} />
                {avecPosition.map((etab) => (
                  <Marker key={etab.id} position={[etab.latitude, etab.longitude]}>
                    <Popup>
                      <strong>{etab.nom}</strong>
                      <br />
                      {TYPE_LABEL[etab.type]} · {etab.statut === "public" ? "Public" : "Privé"}
                      <br />
                      <a
                        href={lienGoogleMaps(etab.latitude, etab.longitude)}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: "inline-flex", alignItems: "center", gap: "4px", marginTop: "6px", fontWeight: 700 }}
                      >
                        <Navigation size={12} /> Itinéraire Google Maps
                      </a>
                    </Popup>
                  </Marker>
                ))}
              </MapContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
