import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import {
  alertesElProfessorDeMonEnfant,
  listerMesSessionsElProfessorTuteur,
  ouvrirSessionElProfessorTuteur,
} from "../../api/el_professor_tuteur";
import { listerMesSessionsElProfessorFamille, ouvrirSessionElProfessorFamille } from "../../api/el_professor_famille";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import { ElProfessorChat, type ConversationChat } from "../../components/el_professor/ElProfessorChat";
import { OngletsElProfessor } from "../../components/el_professor/OngletsElProfessor";
import { Btn, Card, EmptyState, ErrorBanner, Field, Select, SkeletonCard, TextInput } from "../../components/ui";
import type { AlerteElProfessorOut, SessionElProfessorFamilleOut, SessionElProfessorTuteurOut } from "../../types/api";
import { TriangleAlert, Users } from "lucide-react";

const SUGGESTIONS = [
  "Comment aider mon enfant à mieux s'organiser pour ses devoirs ?",
  "Mon enfant manque de motivation, que puis-je faire ?",
  "Comment accompagner son orientation ?",
];

const SUGGESTIONS_FAMILLE = [
  "Comment nous organiser ensemble pour les révisions ?",
  "Quels objectifs nous fixer pour ce trimestre ?",
];

function versConversation(s: SessionElProfessorTuteurOut): ConversationChat {
  return {
    id: s.id,
    sujet: s.sujet,
    titreParDefaut: "Nouvelle conversation",
    reference: s.eleve_utilisateur_id,
    creeLe: s.created_at,
    messages: s.messages,
  };
}

function versConversationFamille(s: SessionElProfessorFamilleOut): ConversationChat {
  return {
    id: s.id,
    sujet: s.sujet,
    titreParDefaut: "Fil familial",
    reference: s.eleve_utilisateur_id,
    creeLe: s.created_at,
    messages: s.messages,
    enAttente: s.rejointe_le === null,
  };
}

function FormulaireNouvelle({
  enfants,
  libelleAction,
  onCreer,
}: {
  enfants: { id: string; eleve_utilisateur_id: string | null; eleve_prenom: string; eleve_nom: string }[];
  libelleAction: string;
  onCreer: (eleveId: string, sujet: string | undefined) => Promise<void>;
}) {
  const avecCompte = enfants.filter((e) => e.eleve_utilisateur_id);
  const [eleveId, setEleveId] = useState(avecCompte[0]?.eleve_utilisateur_id ?? "");
  const [sujet, setSujet] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  if (avecCompte.length === 0) {
    return <p style={{ margin: 0, fontSize: "var(--text-sm)" }}>Aucun enfant avec un compte élève actif.</p>;
  }

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setEnCours(true);
    setErreur(null);
    try {
      await onCreer(eleveId, sujet.trim() || undefined);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir cette conversation."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <form onSubmit={soumettre} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <ErrorBanner>{erreur}</ErrorBanner>
      <Field label="Enfant concerné">
        <Select value={eleveId} onChange={(e) => setEleveId(e.target.value)}>
          {avecCompte.map((e) => (
            <option key={e.id} value={e.eleve_utilisateur_id ?? ""}>
              {e.eleve_prenom} {e.eleve_nom}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Sujet (optionnel)">
        <TextInput value={sujet} maxLength={200} onChange={(e) => setSujet(e.target.value)} placeholder="Ex. Motivation en baisse" />
      </Field>
      <Btn type="submit" size="sm" loading={enCours}>
        {libelleAction}
      </Btn>
    </form>
  );
}

export function ElProfessorTuteurPage({ ongletInitial = "perso" }: { ongletInitial?: "perso" | "famille" }) {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [params] = useSearchParams();
  const [onglet, setOnglet] = useState<"perso" | "famille">(params.get("onglet") === "famille" ? "famille" : ongletInitial);
  const [erreur, setErreur] = useState<string | null>(null);
  const [alertes, setAlertes] = useState<AlerteElProfessorOut[]>([]);

  const [conversations, setConversations] = useState<ConversationChat[]>([]);
  const [famille, setFamille] = useState<ConversationChat[]>([]);
  const [chargement, setChargement] = useState(true);
  const [chargementFamille, setChargementFamille] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [familleActiveId, setFamilleActiveId] = useState<string | null>(null);

  useEffect(() => {
    listerMesSessionsElProfessorTuteur()
      .then((res) => setConversations(res.data.map(versConversation)))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
    listerMesSessionsElProfessorFamille()
      .then((res) => setFamille(res.data.map(versConversationFamille)))
      .catch(() => undefined)
      .finally(() => setChargementFamille(false));
  }, []);

  // Les prénoms des enfants arrivent à part : libellés calculés à l'affichage.
  const prenoms = useMemo(() => {
    const table = new Map<string, string>();
    enfants.forEach((e) => e.eleve_utilisateur_id && table.set(e.eleve_utilisateur_id, e.eleve_prenom));
    return table;
  }, [enfants]);
  const conversationsAffichees = useMemo(
    () => conversations.map((c) => ({ ...c, contexte: (c.reference && prenoms.get(c.reference)) || null })),
    [conversations, prenoms],
  );
  const familleAffichee = useMemo(
    () =>
      famille.map((c) => {
        const prenom = (c.reference && prenoms.get(c.reference)) || "votre enfant";
        return {
          ...c,
          titreParDefaut: `Fil avec ${prenom}`,
          contexte: c.enAttente ? `En attente de ${prenom}` : `Avec ${prenom}`,
        };
      }),
    [famille, prenoms],
  );

  useEffect(() => {
    const ids = enfants.map((e) => e.eleve_utilisateur_id).filter((id): id is string => !!id);
    Promise.all(ids.map((id) => alertesElProfessorDeMonEnfant(id).then((r) => r.data).catch(() => [])))
      .then((listes) => setAlertes(listes.flat().filter((a) => !a.traite)))
      .catch(() => undefined);
  }, [enfants]);

  const nomEnfant = (id: string | null) => {
    const enfant = enfants.find((e) => e.eleve_utilisateur_id === id);
    return enfant ? `${enfant.eleve_prenom} ${enfant.eleve_nom}` : "votre enfant";
  };

  return (
    <div className="page-content">
      <div style={{ marginBottom: "16px" }}>
        <p className="text-eyebrow">Espace Tuteur</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>
          El Professor
        </h1>
        <p className="text-sm" style={{ color: "var(--ink-soft)", margin: "4px 0 0" }}>
          Un conseil sur la scolarité, le comportement ou l'orientation de votre enfant — seul, ou dans un fil partagé avec lui.
        </p>
      </div>
      <OngletsElProfessor onglet={onglet} onChange={setOnglet} libellePerso="Mes conversations" libelleFamille="Avec mon enfant" />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {alertes.length > 0 && (
        <Card style={{ marginBottom: "16px", borderColor: "var(--action-deep)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", color: "var(--action-deep)", fontWeight: 700 }}>
            <TriangleAlert size={16} /> Alertes de sécurité transmises à l'établissement
          </div>
          {alertes.map((a) => (
            <p key={a.id} style={{ fontSize: "var(--text-sm)", margin: "0 0 6px" }}>
              <strong>{nomEnfant(a.eleve_utilisateur_id)}</strong> — {a.motif}
            </p>
          ))}
        </Card>
      )}

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" desc="El Professor vous conseille à propos d'un enfant inscrit." />
      ) : onglet === "perso" ? (
        <ElProfessorChat
          persona="tuteur"
          roleUtilisateur="tuteur"
          conversations={conversationsAffichees}
          setConversations={setConversations}
          chargement={chargement}
          activeId={activeId}
          setActiveId={setActiveId}
          suggestions={SUGGESTIONS}
          formulaireNouvelle={(fermer) => (
            <FormulaireNouvelle
              enfants={enfants}
              libelleAction="Commencer"
              onCreer={async (eleveId, sujet) => {
                const res = await ouvrirSessionElProfessorTuteur(eleveId, sujet);
                setConversations((prec) => [versConversation(res.data), ...prec]);
                setActiveId(res.data.id);
                fermer();
              }}
            />
          )}
        />
      ) : (
        <ElProfessorChat
          persona="famille"
          roleUtilisateur="tuteur"
          conversations={familleAffichee}
          setConversations={setFamille}
          chargement={chargementFamille}
          activeId={familleActiveId}
          setActiveId={setFamilleActiveId}
          suggestions={SUGGESTIONS_FAMILLE}
          libelleAuteur={(role) => (role === "eleve" ? "Votre enfant" : null)}
          ecritureBloquee={(c) =>
            c.enAttente ? "Votre enfant doit d'abord accepter l'invitation, depuis son espace El Professor." : null
          }
          formulaireNouvelle={(fermer) => (
            <FormulaireNouvelle
              enfants={enfants}
              libelleAction="Inviter mon enfant"
              onCreer={async (eleveId, sujet) => {
                const res = await ouvrirSessionElProfessorFamille(eleveId, sujet);
                setFamille((prec) => [versConversationFamille(res.data), ...prec]);
                setFamilleActiveId(res.data.id);
                fermer();
              }}
            />
          )}
        />
      )}
    </div>
  );
}
