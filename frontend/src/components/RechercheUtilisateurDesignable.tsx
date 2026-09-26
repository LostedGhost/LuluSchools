import { useEffect, useRef, useState } from "react";
import { rechercherUtilisateursDesignables } from "../api/controle_acces";
import { Field, TextInput } from "./ui";
import type { UtilisateurDesignableOut } from "../types/api";
import { X } from "lucide-react";

/**
 * UC-28 : recherche par nom pour designer un controleur (enseignant sous contrat ou
 * admin de l'etablissement), meme pattern que AffectationsClasseManager pour
 * l'affectation enseignant<->classe - remplace la saisie d'un id utilisateur brut.
 */
export function RechercheUtilisateurDesignable({
  etablissementId,
  selection,
  onSelect,
}: {
  etablissementId: string;
  selection: UtilisateurDesignableOut | null;
  onSelect: (utilisateur: UtilisateurDesignableOut | null) => void;
}) {
  const [recherche, setRecherche] = useState("");
  const [suggestions, setSuggestions] = useState<UtilisateurDesignableOut[]>([]);
  const [rechercheEnCours, setRechercheEnCours] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (recherche.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    setRechercheEnCours(true);
    debounceRef.current = setTimeout(() => {
      rechercherUtilisateursDesignables(etablissementId, recherche.trim())
        .then((res) => setSuggestions(res.data))
        .catch(() => setSuggestions([]))
        .finally(() => setRechercheEnCours(false));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recherche, etablissementId]);

  return (
    <div style={{ position: "relative" }}>
      <Field label="Utilisateur à désigner" helper="Recherche parmi les enseignants sous contrat signé et les admins de l'établissement.">
        {selection ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "8px",
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--border)",
              background: "var(--surface-2)",
            }}
          >
            <span>
              {selection.prenom} {selection.nom}
            </span>
            <button
              type="button"
              onClick={() => onSelect(null)}
              style={{ background: "none", border: "none", cursor: "pointer", display: "flex", color: "var(--ink-faint)" }}
              aria-label="Changer d'utilisateur"
            >
              <X size={16} />
            </button>
          </div>
        ) : (
          <TextInput
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher par nom ou prénom..."
          />
        )}
      </Field>
      {!selection && recherche.trim().length >= 2 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 10,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            marginTop: "4px",
            maxHeight: "220px",
            overflowY: "auto",
            boxShadow: "var(--shadow-md, 0 4px 12px rgba(0,0,0,0.08))",
          }}
        >
          {rechercheEnCours ? (
            <div style={{ padding: "10px 12px", color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>Recherche...</div>
          ) : suggestions.length === 0 ? (
            <div style={{ padding: "10px 12px", color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>
              Aucun utilisateur ne correspond.
            </div>
          ) : (
            suggestions.map((u) => (
              <button
                key={u.id}
                type="button"
                onClick={() => {
                  onSelect(u);
                  setRecherche("");
                  setSuggestions([]);
                }}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "10px 12px",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: "var(--text-sm)",
                }}
              >
                {u.prenom} {u.nom} <span style={{ color: "var(--ink-faint)" }}>({u.role})</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
