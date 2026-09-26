import type { ChampFormulaire, TypeChampFormulaire } from "../types/api";
import { Btn, Field, Select, TextInput } from "./ui";
import { Plus, Trash2 } from "lucide-react";

const LABEL_TYPE: Record<TypeChampFormulaire, string> = {
  texte_court: "Texte court",
  texte_long: "Texte long",
  fichier: "Fichier",
  choix_unique: "Choix unique",
  choix_multiple: "Choix multiple",
};

function slugifier(label: string, existants: string[]): string {
  const base = label
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "champ";
  let id = base;
  let compteur = 2;
  while (existants.includes(id)) {
    id = `${base}_${compteur}`;
    compteur += 1;
  }
  return id;
}

/**
 * Constructeur de formulaire dynamique (UC-47/50/62/64) : un seul composant, réutilisé
 * pour configurer aussi bien un poste de recrutement qu'un type d'acte académique - même
 * moteur des deux côtés (voir app/core/formulaire.py côté backend).
 */
export function FormulaireBuilder({
  champs,
  onChange,
}: {
  champs: ChampFormulaire[];
  onChange: (champs: ChampFormulaire[]) => void;
}) {
  const ajouterChamp = () => {
    const id = slugifier("nouveau champ", champs.map((c) => c.id));
    onChange([...champs, { id, label: "", type: "texte_court", requis: false, options: null }]);
  };

  const modifierChamp = (index: number, patch: Partial<ChampFormulaire>) => {
    const suivant = [...champs];
    suivant[index] = { ...suivant[index], ...patch };
    onChange(suivant);
  };

  const supprimerChamp = (index: number) => {
    onChange(champs.filter((_, i) => i !== index));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      {champs.map((champ, index) => (
        <div
          key={index}
          style={{
            display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end",
            padding: "12px", background: "var(--surface-2)", borderRadius: "var(--radius-md)",
          }}
        >
          <Field label="Intitulé">
            <TextInput
              value={champ.label}
              onChange={(e) =>
                modifierChamp(index, {
                  label: e.target.value,
                  id: champ.id.startsWith("nouveau_champ") || champ.id === "" ? slugifier(e.target.value, champs.filter((_, i) => i !== index).map((c) => c.id)) : champ.id,
                })
              }
              placeholder="Ex. Disponibilité"
              style={{ minWidth: "180px" }}
            />
          </Field>
          <Field label="Type">
            <Select
              value={champ.type}
              onChange={(e) => modifierChamp(index, { type: e.target.value as TypeChampFormulaire })}
              style={{ width: "160px" }}
            >
              {Object.entries(LABEL_TYPE).map(([valeur, label]) => (
                <option key={valeur} value={valeur}>{label}</option>
              ))}
            </Select>
          </Field>
          {(champ.type === "choix_unique" || champ.type === "choix_multiple") && (
            <Field label="Options (séparées par des virgules)">
              <TextInput
                value={(champ.options ?? []).join(", ")}
                onChange={(e) =>
                  modifierChamp(index, {
                    options: e.target.value.split(",").map((o) => o.trim()).filter(Boolean),
                  })
                }
                placeholder="Ex. Oui, Non"
                style={{ minWidth: "200px" }}
              />
            </Field>
          )}
          <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "var(--text-sm)", paddingBottom: "10px" }}>
            <input type="checkbox" checked={champ.requis} onChange={(e) => modifierChamp(index, { requis: e.target.checked })} />
            Requis
          </label>
          <Btn type="button" variant="ghost" size="sm" onClick={() => supprimerChamp(index)} leftIcon={<Trash2 size={14} />}>
            Retirer
          </Btn>
        </div>
      ))}
      <Btn type="button" variant="outline" size="sm" onClick={ajouterChamp} leftIcon={<Plus size={14} />}>
        Ajouter un champ
      </Btn>
    </div>
  );
}
