import { useState } from "react";
import { Btn, Field, TextInput } from "./ui";
import { LocateFixed } from "lucide-react";

interface LocationPickerProps {
  latitude: string;
  longitude: string;
  onChange: (latitude: string, longitude: string) => void;
  aideTexte?: string;
}

/**
 * Saisie manuelle de latitude/longitude, avec un raccourci "Utiliser ma position
 * actuelle" (API Geolocation du navigateur) pour la personne physiquement sur place
 * (A+ dans son propre établissement, A++ en visite) - la saisie manuelle reste
 * disponible en secours (navigateur sans permission, coordonnées connues à l'avance).
 */
export function LocationPicker({ latitude, longitude, onChange, aideTexte }: LocationPickerProps) {
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const utiliserMaPosition = () => {
    if (!("geolocation" in navigator)) {
      setErreur("Votre navigateur ne permet pas la géolocalisation. Saisissez les coordonnées manuellement.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        onChange(position.coords.latitude.toFixed(6), position.coords.longitude.toFixed(6));
        setEnCours(false);
      },
      () => {
        setErreur("Position indisponible ou refusée. Saisissez les coordonnées manuellement.");
        setEnCours(false);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };

  return (
    <div style={{ gridColumn: "1 / -1" }}>
      <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", marginBottom: "8px" }}>
        <Btn type="button" variant="outline" size="sm" loading={enCours} onClick={utiliserMaPosition} leftIcon={<LocateFixed size={14} />}>
          Utiliser ma position actuelle
        </Btn>
        <span className="text-sm" style={{ color: "var(--ink-faint)" }}>
          {aideTexte ?? "À utiliser si vous êtes physiquement sur place — sinon, saisissez les coordonnées ci-dessous."}
        </span>
      </div>
      {erreur && <p className="text-sm" style={{ color: "var(--action-deep)", margin: "0 0 8px" }}>{erreur}</p>}
      <div className="grid-2">
        <Field label="Latitude" required helper="Entre -90 et 90">
          <TextInput
            type="number"
            step="any"
            min="-90"
            max="90"
            value={latitude}
            onChange={(e) => onChange(e.target.value, longitude)}
          />
        </Field>
        <Field label="Longitude" required helper="Entre -180 et 180">
          <TextInput
            type="number"
            step="any"
            min="-180"
            max="180"
            value={longitude}
            onChange={(e) => onChange(latitude, e.target.value)}
          />
        </Field>
      </div>
    </div>
  );
}
