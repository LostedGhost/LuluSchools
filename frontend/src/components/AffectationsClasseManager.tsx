import { useEffect, useRef, useState, type FormEvent } from "react";
import { affecterEnseignant, listerAffectationsClasse, revoquerAffectation } from "../api/etablissements";
import { rechercherEnseignantsSignes } from "../api/recrutement";
import { messageErreur } from "../api/client";
import type { AffectationEnseignantOut, EnseignantSigneOut } from "../types/api";
import { Btn, EmptyState, ErrorBanner, Field, SuccessBanner, TextInput } from "./ui";
import { GraduationCap, Trash2, X } from "lucide-react";

/**
 * Gère les enseignants affectés à UNE classe précise (voir AffectationEnseignant côté
 * backend) - depuis la refonte RBAC, c'est ce lien qui détermine quelles classes un
 * enseignant peut gérer (cours/quiz/devoirs/sessions live), pas seulement son contrat
 * signé avec l'établissement. Recherche par nom (GET /etablissements/{id}/enseignants),
 * limitée aux enseignants ayant un contrat signé avec cet établissement.
 */
export function AffectationsClasseManager({ classeId, etablissementId }: { classeId: string; etablissementId: string }) {
  const [affectations, setAffectations] = useState<AffectationEnseignantOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [revocationEnCoursId, setRevocationEnCoursId] = useState<string | null>(null);

  const [nomsParId, setNomsParId] = useState<Record<string, EnseignantSigneOut>>({});
  const [recherche, setRecherche] = useState("");
  const [suggestions, setSuggestions] = useState<EnseignantSigneOut[]>([]);
  const [rechercheEnCours, setRechercheEnCours] = useState(false);
  const [enseignantSelectionne, setEnseignantSelectionne] = useState<EnseignantSigneOut | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const memoriserNoms = (liste: EnseignantSigneOut[]) => {
    setNomsParId((prev) => {
      const suivant = { ...prev };
      for (const e of liste) suivant[e.id] = e;
      return suivant;
    });
  };

  const charger = () => {
    setChargement(true);
    listerAffectationsClasse(classeId)
      .then((res) => setAffectations(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [classeId]);

  // Charge la liste complète (non filtrée) des enseignants sous contrat une fois, pour
  // pouvoir afficher un nom plutôt qu'un id brut sur les affectations déjà existantes.
  useEffect(() => {
    rechercherEnseignantsSignes(etablissementId)
      .then((res) => memoriserNoms(res.data))
      .catch(() => undefined);
  }, [etablissementId]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (recherche.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    setRechercheEnCours(true);
    debounceRef.current = setTimeout(() => {
      rechercherEnseignantsSignes(etablissementId, recherche.trim())
        .then((res) => {
          setSuggestions(res.data);
          memoriserNoms(res.data);
        })
        .catch(() => setSuggestions([]))
        .finally(() => setRechercheEnCours(false));
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recherche, etablissementId]);

  const choisir = (e: EnseignantSigneOut) => {
    setEnseignantSelectionne(e);
    setRecherche("");
    setSuggestions([]);
  };

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);
    if (!enseignantSelectionne) {
      setErreur("Sélectionnez un enseignant dans la liste.");
      return;
    }
    setEnCours(true);
    try {
      await affecterEnseignant(classeId, enseignantSelectionne.id);
      setSucces(`${enseignantSelectionne.prenom} ${enseignantSelectionne.nom} affecté(e) à cette classe.`);
      setEnseignantSelectionne(null);
      charger();
    } catch (err) {
      setErreur(
        messageErreur(
          err,
          "Impossible d'affecter cet enseignant (vérifiez qu'il a un contrat signé avec cet établissement).",
        ),
      );
    } finally {
      setEnCours(false);
    }
  };

  const revoquer = async (affectationId: string) => {
    setRevocationEnCoursId(affectationId);
    setErreur(null);
    setSucces(null);
    try {
      await revoquerAffectation(affectationId);
      setSucces("Affectation révoquée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de révoquer cette affectation."));
    } finally {
      setRevocationEnCoursId(null);
    }
  };

  return (
    <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px dashed var(--border)" }}>
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      <form onSubmit={soumettre} style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "12px" }}>
        <div style={{ flex: 1, minWidth: "220px", position: "relative" }}>
          <Field label="Enseignant" helper="Recherche parmi les enseignants sous contrat signé avec cet établissement.">
            {enseignantSelectionne ? (
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
                <span>{enseignantSelectionne.prenom} {enseignantSelectionne.nom}</span>
                <button
                  type="button"
                  onClick={() => setEnseignantSelectionne(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", display: "flex", color: "var(--ink-faint)" }}
                  aria-label="Changer d'enseignant"
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
          {!enseignantSelectionne && (recherche.trim().length >= 2) && (
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
                  Aucun enseignant sous contrat ne correspond.
                </div>
              ) : (
                suggestions.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => choisir(s)}
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
                    {s.prenom} {s.nom}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
        <Btn type="submit" variant="primary" size="sm" loading={enCours} leftIcon={<GraduationCap size={14} />}>
          Affecter
        </Btn>
      </form>

      {chargement ? null : affectations.length === 0 ? (
        <EmptyState icon={<GraduationCap size={18} />} title="Aucun enseignant affecté à cette classe" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {affectations.map((a) => {
            const enseignant = nomsParId[a.enseignant_id];
            return (
              <div
                key={a.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--surface-2)",
                }}
              >
                <span style={enseignant ? undefined : { fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>
                  {enseignant ? `${enseignant.prenom} ${enseignant.nom}` : a.enseignant_id}
                </span>
                <Btn
                  variant="ghost"
                  size="sm"
                  loading={revocationEnCoursId === a.id}
                  onClick={() => revoquer(a.id)}
                  leftIcon={<Trash2 size={14} />}
                >
                  Révoquer
                </Btn>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
