import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { listerMesConversationsEleve, ouvrirConversationEleve } from "../../api/el_professor";
import { listerMesSessionsElProfessorFamille, rejoindreSessionElProfessorFamille } from "../../api/el_professor_famille";
import { listerCours } from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import { ElProfessorChat, type ConversationChat } from "../../components/el_professor/ElProfessorChat";
import { OngletsElProfessor } from "../../components/el_professor/OngletsElProfessor";
import { Btn, ErrorBanner, Field, Select, TextInput } from "../../components/ui";
import type { CoursOut, SessionElProfessorFamilleOut, SessionElProfessorOut } from "../../types/api";

const SUGGESTIONS = [
  "Explique-moi une notion que je n'ai pas comprise",
  "Aide-moi à organiser mes révisions de la semaine",
  "Donne-moi un exercice d'entraînement avec des indices",
  "Comment bien rédiger une introduction ?",
];

function versConversation(s: SessionElProfessorOut): ConversationChat {
  return {
    id: s.id,
    sujet: s.sujet,
    titreParDefaut: s.cours_titre ? `Cours : ${s.cours_titre}` : "Nouvelle conversation",
    contexte: s.cours_titre ? `Cours · ${s.cours_titre}` : "Aide générale",
    creeLe: s.created_at,
    messages: s.messages,
  };
}

function versConversationFamille(s: SessionElProfessorFamilleOut): ConversationChat {
  return {
    id: s.id,
    sujet: s.sujet,
    titreParDefaut: "Fil familial",
    contexte: s.rejointe_le ? "Avec ton parent" : "Invitation en attente",
    creeLe: s.created_at,
    messages: s.messages,
    enAttente: s.rejointe_le === null,
  };
}

function FormulaireNouvelle({
  cours,
  coursInitial,
  onCreee,
}: {
  cours: CoursOut[];
  coursInitial?: string;
  onCreee: (s: SessionElProfessorOut) => void;
}) {
  const [coursId, setCoursId] = useState(coursInitial ?? "");
  const [sujet, setSujet] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const creer = async (e: FormEvent) => {
    e.preventDefault();
    setEnCours(true);
    setErreur(null);
    try {
      const res = await ouvrirConversationEleve(coursId || undefined, sujet.trim() || undefined);
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
      <Field label="Sur quoi ?">
        <Select value={coursId} onChange={(e) => setCoursId(e.target.value)}>
          <option value="">Aide générale (toutes matières)</option>
          {cours.map((c) => (
            <option key={c.id} value={c.id}>
              Cours : {c.titre}
            </option>
          ))}
        </Select>
      </Field>
      {!coursId && (
        <Field label="Titre (optionnel)">
          <TextInput value={sujet} maxLength={200} onChange={(e) => setSujet(e.target.value)} placeholder="Ex. Révisions de maths" />
        </Field>
      )}
      <Btn type="submit" size="sm" loading={enCours}>
        Commencer
      </Btn>
    </form>
  );
}

export function ElProfessorElevePage({ ongletInitial = "perso" }: { ongletInitial?: "perso" | "famille" }) {
  const profil = useEleveProfil();
  const [params, setParams] = useSearchParams();
  const [onglet, setOnglet] = useState<"perso" | "famille">(params.get("onglet") === "famille" ? "famille" : ongletInitial);
  const [erreur, setErreur] = useState<string | null>(null);

  const [conversations, setConversations] = useState<ConversationChat[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [cours, setCours] = useState<CoursOut[]>([]);

  const [famille, setFamille] = useState<ConversationChat[]>([]);
  const [familleActiveId, setFamilleActiveId] = useState<string | null>(null);
  const [chargementFamille, setChargementFamille] = useState(true);
  const [rejointEnCours, setRejointEnCours] = useState(false);

  const coursDemande = params.get("cours");

  useEffect(() => {
    listerMesConversationsEleve()
      .then((res) => setConversations(res.data.map(versConversation)))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
    listerMesSessionsElProfessorFamille()
      .then((res) => setFamille(res.data.map(versConversationFamille)))
      .catch(() => undefined)
      .finally(() => setChargementFamille(false));
  }, []);

  useEffect(() => {
    if (!profil.classe_id) return;
    listerCours(profil.classe_id)
      .then((res) => setCours(res.data))
      .catch(() => undefined);
  }, [profil.classe_id]);

  // Arrivée depuis la page d'un cours : ouvre (ou reprend) la conversation de ce cours.
  useEffect(() => {
    if (!coursDemande) return;
    ouvrirConversationEleve(coursDemande)
      .then((res) => {
        const conversation = versConversation(res.data);
        setConversations((prec) => (prec.some((c) => c.id === conversation.id) ? prec : [conversation, ...prec]));
        setActiveId(conversation.id);
        setOnglet("perso");
      })
      .catch((err) => setErreur(messageErreur(err, "Impossible d'ouvrir la conversation de ce cours.")))
      .finally(() => {
        params.delete("cours");
        setParams(params, { replace: true });
      });
  }, [coursDemande, params, setParams]);

  const rejoindre = async (id: string) => {
    setRejointEnCours(true);
    try {
      const res = await rejoindreSessionElProfessorFamille(id);
      setFamille((prec) => prec.map((c) => (c.id === id ? versConversationFamille(res.data) : c)));
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de rejoindre ce fil."));
    } finally {
      setRejointEnCours(false);
    }
  };

  const invitationsEnAttente = famille.filter((c) => c.enAttente).length;

  return (
    <div className="page-content">
      <div style={{ marginBottom: "16px" }}>
        <p className="text-eyebrow">Assistant pédagogique</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>
          El Professor
        </h1>
      </div>
      <OngletsElProfessor
        onglet={onglet}
        onChange={setOnglet}
        libellePerso="Mes conversations"
        libelleFamille="Avec ma famille"
        pastilleFamille={invitationsEnAttente}
      />
      <ErrorBanner>{erreur}</ErrorBanner>

      {onglet === "perso" ? (
        <ElProfessorChat
          persona="eleve"
          roleUtilisateur="eleve"
          conversations={conversations}
          setConversations={setConversations}
          chargement={chargement}
          activeId={activeId}
          setActiveId={setActiveId}
          tutoiement
          suggestions={SUGGESTIONS}
          formulaireNouvelle={(fermer) => (
            <FormulaireNouvelle
              cours={cours}
              onCreee={(s) => {
                const conversation = versConversation(s);
                setConversations((prec) => (prec.some((c) => c.id === conversation.id) ? prec : [conversation, ...prec]));
                setActiveId(conversation.id);
                fermer();
              }}
            />
          )}
        />
      ) : (
        <ElProfessorChat
          persona="famille"
          roleUtilisateur="eleve"
          conversations={famille}
          setConversations={setFamille}
          chargement={chargementFamille}
          activeId={familleActiveId}
          setActiveId={setFamilleActiveId}
          tutoiement
          peutGerer={() => false}
          libelleAuteur={(role) => (role === "tuteur" ? "Ton parent" : null)}
          suggestions={["Comment mieux nous organiser pour les devoirs ?", "Comment parler de mon orientation ?"]}
          ecritureBloquee={(c) => (c.enAttente ? "Rejoins ce fil pour pouvoir y écrire." : null)}
          bandeau={(c) =>
            !c.enAttente ? null : (
              <div style={{ margin: "12px 16px 0", padding: "12px", borderRadius: "var(--radius-md)", background: "var(--info-tint)", display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                <span style={{ flex: 1, minWidth: "200px", fontSize: "var(--text-sm)", color: "var(--ink)" }}>
                  Ton parent t'invite à discuter avec El Professor dans un fil partagé : vous y verrez tous les deux les questions et les réponses.
                </span>
                <Btn size="sm" loading={rejointEnCours} onClick={() => rejoindre(c.id)}>
                  Rejoindre
                </Btn>
              </div>
            )
          }
          formulaireNouvelle={() => (
            <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
              Un fil familial s'ouvre à l'invitation de ton parent, depuis son espace. Tu le retrouveras ici.
            </p>
          )}
        />
      )}
    </div>
  );
}
