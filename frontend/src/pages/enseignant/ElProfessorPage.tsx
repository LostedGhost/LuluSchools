import { useEffect, useMemo, useState, type FormEvent } from "react";
import { listerMesSessionsElProfessorEnseignant, ouvrirSessionElProfessorEnseignant } from "../../api/el_professor_enseignant";
import { listerElevesDeLaClasse, mesClassesAffectees } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import { ElProfessorChat, type ConversationChat } from "../../components/el_professor/ElProfessorChat";
import { Btn, ErrorBanner, Field, Select, TextInput } from "../../components/ui";
import type { EleveClasseOut, SalleEnseignantOut, SessionElProfessorEnseignantOut } from "../../types/api";

const SUGGESTIONS = [
  "Comment gérer un élève qui perturbe régulièrement le cours ?",
  "Propose-moi une séquence de 4 séances sur les fractions",
  "Comment différencier un exercice pour une classe hétérogène ?",
  "Aide-moi à rédiger une appréciation de bulletin bienveillante",
];

function versConversation(s: SessionElProfessorEnseignantOut): ConversationChat {
  return {
    id: s.id,
    sujet: s.sujet,
    titreParDefaut: "Nouvelle conversation",
    reference: s.eleve_utilisateur_id,
    creeLe: s.created_at,
    messages: s.messages,
  };
}

function FormulaireNouvelle({
  salles,
  elevesParSalle,
  onCreee,
}: {
  salles: SalleEnseignantOut[];
  elevesParSalle: Record<string, EleveClasseOut[]>;
  onCreee: (s: SessionElProfessorEnseignantOut) => void;
}) {
  const [eleveId, setEleveId] = useState("");
  const [sujet, setSujet] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const creer = async (e: FormEvent) => {
    e.preventDefault();
    setEnCours(true);
    setErreur(null);
    try {
      const res = await ouvrirSessionElProfessorEnseignant(eleveId || undefined, sujet.trim() || undefined);
      onCreee(res.data);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir cette conversation."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <form onSubmit={creer} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <ErrorBanner>{erreur}</ErrorBanner>
      <Field label="Élève concerné (optionnel)">
        <Select value={eleveId} onChange={(e) => setEleveId(e.target.value)}>
          <option value="">Question générale</option>
          {salles.map((salle) =>
            (elevesParSalle[salle.id] ?? [])
              .filter((e) => e.utilisateur_id)
              .map((eleve) => (
                <option key={eleve.eleve_id} value={eleve.utilisateur_id ?? ""}>
                  {eleve.prenom} {eleve.nom} ({salle.niveau})
                </option>
              )),
          )}
        </Select>
      </Field>
      <Field label="Sujet (optionnel)">
        <TextInput value={sujet} maxLength={200} onChange={(e) => setSujet(e.target.value)} placeholder="Ex. Décrochage en classe" />
      </Field>
      <Btn type="submit" size="sm" loading={enCours}>
        Commencer
      </Btn>
    </form>
  );
}

export function ElProfessorPage() {
  const [conversations, setConversations] = useState<ConversationChat[]>([]);
  const [chargement, setChargement] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [salles, setSalles] = useState<SalleEnseignantOut[]>([]);
  const [elevesParSalle, setElevesParSalle] = useState<Record<string, EleveClasseOut[]>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    listerMesSessionsElProfessorEnseignant()
      .then((res) => setConversations(res.data.map(versConversation)))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
    mesClassesAffectees()
      .then((res) => {
        setSalles(res.data);
        res.data.forEach((s) => {
          listerElevesDeLaClasse(s.id)
            .then((r) => setElevesParSalle((prev) => ({ ...prev, [s.id]: r.data })))
            .catch(() => undefined);
        });
      })
      .catch(() => undefined);
  }, []);

  // Le nom de l'élève concerné arrive après les conversations : calculé à l'affichage.
  const affichees = useMemo(() => {
    const noms = new Map<string, string>();
    Object.values(elevesParSalle)
      .flat()
      .forEach((e) => e.utilisateur_id && noms.set(e.utilisateur_id, `${e.prenom} ${e.nom}`));
    return conversations.map((c) => ({
      ...c,
      contexte: c.reference ? noms.get(c.reference) ?? "Élève" : "Question générale",
    }));
  }, [conversations, elevesParSalle]);

  return (
    <div className="page-content">
      <div style={{ marginBottom: "16px" }}>
        <p className="text-eyebrow">Espace Enseignant</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>
          El Professor
        </h1>
        <p className="text-sm" style={{ color: "var(--ink-soft)", margin: "4px 0 0" }}>
          Un conseil éducatif, moral, professionnel ou humain — sur un élève précis ou votre pratique en général.
        </p>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>
      <ElProfessorChat
        persona="enseignant"
        roleUtilisateur="enseignant"
        conversations={affichees}
        setConversations={setConversations}
        chargement={chargement}
        activeId={activeId}
        setActiveId={setActiveId}
        suggestions={SUGGESTIONS}
        formulaireNouvelle={(fermer) => (
          <FormulaireNouvelle
            salles={salles}
            elevesParSalle={elevesParSalle}
            onCreee={(s) => {
              setConversations((prec) => [versConversation(s), ...prec]);
              setActiveId(s.id);
              fermer();
            }}
          />
        )}
      />
    </div>
  );
}
