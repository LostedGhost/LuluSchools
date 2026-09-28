import { useState } from "react";
import { mettreAJourLocalisation, mettreAJourTerritoire } from "../api/etablissements";
import { ChoixTerritoire } from "./ChoixTerritoire";
import { messageErreur } from "../api/client";
import { lienGoogleMaps } from "../utils/geo";
import { LocationPicker } from "./LocationPicker";
import { Btn, ErrorBanner, SectionHead, SuccessBanner } from "./ui";
import { MapPin } from "lucide-react";

/**
 * Position de l'établissement (A+ : le sien uniquement, voir backend) - la
 * géolocalisation navigateur est adaptée ici puisque l'A+ est généralement
 * physiquement sur place, contrairement à l'A++ qui gère à distance.
 */
export function LocalisationEtablissementManager({
  etablissementId,
  latitude,
  longitude,
  departement: departementInitial = null,
  commune: communeInitiale = null,
}: {
  etablissementId: string;
  latitude: number | null;
  longitude: number | null;
  departement?: string | null;
  commune?: string | null;
}) {
  // Lot 7.6 : département et commune (indicateurs du ministère par territoire).
  const [departement, setDepartement] = useState(departementInitial ?? "");
  const [commune, setCommune] = useState(communeInitiale ?? "");
  const [territoireEnregistre, setTerritoireEnregistre] = useState(!!communeInitiale);

  const [modeEdition, setModeEdition] = useState(false);
  const [lat, setLat] = useState(latitude?.toString() ?? "");
  const [lng, setLng] = useState(longitude?.toString() ?? "");
  const [positionActuelle, setPositionActuelle] = useState<{ lat: number; lng: number } | null>(
    latitude !== null && longitude !== null ? { lat: latitude, lng: longitude } : null,
  );
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  const enregistrer = async () => {
    const latNum = Number(lat);
    const lngNum = Number(lng);
    if (Number.isNaN(latNum) || Number.isNaN(lngNum) || latNum < -90 || latNum > 90 || lngNum < -180 || lngNum > 180) {
      setErreur("Coordonnées invalides.");
      return;
    }
    setEnCours(true);
    setErreur(null);
    try {
      await mettreAJourLocalisation(etablissementId, latNum, lngNum);
      setPositionActuelle({ lat: latNum, lng: lngNum });
      setSucces("Localisation enregistrée.");
      setModeEdition(false);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer la localisation."));
    } finally {
      setEnCours(false);
    }
  };

  const enregistrerTerritoire = async () => {
    if (!departement || !commune) {
      setErreur("Choisissez le département et la commune.");
      return;
    }
    setErreur(null);
    try {
      await mettreAJourTerritoire(etablissementId, departement, commune);
      setTerritoireEnregistre(true);
      setSucces("Département et commune enregistrés.");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer le département et la commune."));
    }
  };

  return (
    <div style={{ marginTop: "var(--space-8)" }}>
      <SectionHead eyebrow="Établissement" title="Localisation" desc="Utilisée sur votre page de présentation publique et dans la section Cartes." />
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      {modeEdition ? (
        <div className="card">
          <LocationPicker latitude={lat} longitude={lng} onChange={(l, g) => { setLat(l); setLng(g); }} />
          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            <Btn size="sm" variant="primary" loading={enCours} onClick={enregistrer}>Enregistrer</Btn>
            <Btn size="sm" variant="ghost" onClick={() => setModeEdition(false)}>Annuler</Btn>
          </div>
        </div>
      ) : (
        <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
          {positionActuelle ? (
            <a
              href={lienGoogleMaps(positionActuelle.lat, positionActuelle.lng)}
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: "inline-flex", alignItems: "center", gap: "6px", color: "var(--primary-deep)", fontWeight: 600 }}
            >
              <MapPin size={16} /> Voir sur Google Maps
            </a>
          ) : (
            <span style={{ color: "var(--ink-faint)" }}>Aucune position renseignée pour le moment.</span>
          )}
          <Btn size="sm" variant="outline" onClick={() => setModeEdition(true)}>
            {positionActuelle ? "Modifier la localisation" : "Renseigner la localisation"}
          </Btn>
        </div>
      )}
      <div className="card" style={{ marginTop: "12px" }}>
        {!territoireEnregistre && (
          <p style={{ margin: "0 0 10px", color: "var(--ink-soft)" }}>
            Indiquez le département et la commune : sans eux, votre établissement n'apparaît pas dans les statistiques territoriales du ministère.
          </p>
        )}
        <ChoixTerritoire
          departement={departement}
          commune={commune}
          onChange={(d, c) => { setDepartement(d); setCommune(c); setTerritoireEnregistre(false); }}
        />
        {!territoireEnregistre && (
          <Btn size="sm" variant="primary" onClick={enregistrerTerritoire} style={{ marginTop: "10px" }}>
            Enregistrer le département et la commune
          </Btn>
        )}
      </div>
    </div>
  );
}
