import { useEffect, useState } from "react";
import { Field, Select } from "./ui";
import { listerTerritoires } from "../api/etablissements";

/** Lot 7.6 : département puis commune (listes fermées), pour les indicateurs territoriaux. */
export function ChoixTerritoire({
  departement,
  commune,
  onChange,
  erreur,
}: {
  departement: string;
  commune: string;
  onChange: (departement: string, commune: string) => void;
  erreur?: string;
}) {
  const [territoires, setTerritoires] = useState<Record<string, string[]>>({});
  useEffect(() => {
    listerTerritoires().then(setTerritoires).catch(() => {});
  }, []);
  const communes = territoires[departement] ?? [];
  return (
    <div className="grid-2">
      <Field label="Département" required error={erreur}>
        <Select value={departement} onChange={(e) => onChange(e.target.value, "")}>
          <option value="">Choisir…</option>
          {Object.keys(territoires).map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </Select>
      </Field>
      <Field label="Commune" required>
        <Select value={commune} onChange={(e) => onChange(departement, e.target.value)} disabled={!departement}>
          <option value="">Choisir…</option>
          {communes.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </Select>
      </Field>
    </div>
  );
}
