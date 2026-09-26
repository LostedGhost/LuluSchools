import type { ChampFormulaire } from "../types/api";
import { Field, Select, TextArea, TextInput } from "./ui";

/**
 * Rend un formulaire a partir d'un schema dynamique (UC-47/50/62/64) - meme moteur que
 * FormulaireBuilder, cote remplissage plutot que configuration. Les champs de type
 * "fichier" ne sont jamais rendus ici : recrutement les couvre deja via le mecanisme de
 * criteres/documents existant, actes les collecte via un upload dedie APRES la creation
 * de la demande (voir POST /demandes-actes/{id}/pieces/{champ_id}) - jamais dans ce
 * formulaire initial.
 */
export function FormulaireDynamique({
  champs,
  valeurs,
  onChange,
}: {
  champs: ChampFormulaire[];
  valeurs: Record<string, string | string[]>;
  onChange: (id: string, valeur: string | string[]) => void;
}) {
  const champsRemplissables = champs.filter((c) => c.type !== "fichier");
  if (champsRemplissables.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {champsRemplissables.map((champ) => (
        <Field key={champ.id} label={champ.label} required={champ.requis}>
          {champ.type === "texte_long" ? (
            <TextArea
              rows={3}
              value={(valeurs[champ.id] as string) ?? ""}
              onChange={(e) => onChange(champ.id, e.target.value)}
            />
          ) : champ.type === "choix_unique" ? (
            <Select value={(valeurs[champ.id] as string) ?? ""} onChange={(e) => onChange(champ.id, e.target.value)}>
              <option value="">— Choisir —</option>
              {(champ.options ?? []).map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </Select>
          ) : champ.type === "choix_multiple" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              {(champ.options ?? []).map((option) => {
                const selection = (valeurs[champ.id] as string[]) ?? [];
                return (
                  <label key={option} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "var(--text-sm)" }}>
                    <input
                      type="checkbox"
                      checked={selection.includes(option)}
                      onChange={(e) => {
                        const suivant = e.target.checked
                          ? [...selection, option]
                          : selection.filter((o) => o !== option);
                        onChange(champ.id, suivant);
                      }}
                    />
                    {option}
                  </label>
                );
              })}
            </div>
          ) : (
            <TextInput
              value={(valeurs[champ.id] as string) ?? ""}
              onChange={(e) => onChange(champ.id, e.target.value)}
            />
          )}
        </Field>
      ))}
    </div>
  );
}

export function champsFichierDe(champs: ChampFormulaire[]): ChampFormulaire[] {
  return champs.filter((c) => c.type === "fichier");
}
