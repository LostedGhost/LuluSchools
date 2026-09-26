import { useEffect, useState, type FormEvent } from "react";
import { affecterEnseignant, listerAffectationsClasse, revoquerAffectation } from "../api/etablissements";
import { messageErreur } from "../api/client";
import type { AffectationEnseignantOut } from "../types/api";
import { Btn, EmptyState, ErrorBanner, Field, SuccessBanner, TextInput } from "./ui";
import { GraduationCap, Trash2 } from "lucide-react";
import { estRempli } from "../utils/validation";

/**
 * Gère les enseignants affectés à UNE classe précise (voir AffectationEnseignant côté
 * backend) - depuis la refonte RBAC, c'est ce lien qui détermine quelles classes un
 * enseignant peut gérer (cours/quiz/devoirs/sessions live), pas seulement son contrat
 * signé avec l'établissement. Pas de recherche par nom : comme pour les contrôleurs
 * (voir ServicesScolairesAdminPage), il faut l'identifiant interne de l'enseignant.
 */
export function AffectationsClasseManager({ classeId }: { classeId: string }) {
  const [affectations, setAffectations] = useState<AffectationEnseignantOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enseignantUtilisateurId, setEnseignantUtilisateurId] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [revocationEnCoursId, setRevocationEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    listerAffectationsClasse(classeId)
      .then((res) => setAffectations(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [classeId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);
    if (!estRempli(enseignantUtilisateurId)) {
      setErreur("Identifiant de l'enseignant requis.");
      return;
    }
    setEnCours(true);
    try {
      await affecterEnseignant(classeId, enseignantUtilisateurId.trim());
      setEnseignantUtilisateurId("");
      setSucces("Enseignant affecté à cette classe.");
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
        <div style={{ flex: 1, minWidth: "200px" }}>
          <Field label="Identifiant de l'enseignant" helper="ID interne du compte (contrat signé requis avec cet établissement).">
            <TextInput
              value={enseignantUtilisateurId}
              onChange={(e) => setEnseignantUtilisateurId(e.target.value)}
              placeholder="ID utilisateur"
            />
          </Field>
        </div>
        <Btn type="submit" variant="primary" size="sm" loading={enCours} leftIcon={<GraduationCap size={14} />}>
          Affecter
        </Btn>
      </form>

      {chargement ? null : affectations.length === 0 ? (
        <EmptyState icon={<GraduationCap size={18} />} title="Aucun enseignant affecté à cette classe" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {affectations.map((a) => (
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
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>{a.enseignant_id}</span>
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
          ))}
        </div>
      )}
    </div>
  );
}
