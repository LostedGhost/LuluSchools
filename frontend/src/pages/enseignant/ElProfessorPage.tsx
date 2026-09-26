import { useEffect, useState, type FormEvent } from "react";
import {
  listerMesSessionsElProfessorEnseignant,
  ouvrirSessionElProfessorEnseignant,
  poserQuestionElProfessorEnseignant,
} from "../../api/el_professor_enseignant";
import { listerElevesDeLaClasse, mesClassesAffectees } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { EleveClasseOut, SalleEnseignantOut, SessionElProfessorEnseignantOut } from "../../types/api";
import { Btn, Card, ErrorBanner, Field, SectionHead, Select, SkeletonCard, TextArea } from "../../components/ui";
import { Bot, Plus, Send, TriangleAlert } from "lucide-react";

export function ElProfessorPage() {
  const [sessions, setSessions] = useState<SessionElProfessorEnseignantOut[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [salles, setSalles] = useState<SalleEnseignantOut[]>([]);
  const [elevesParSalle, setElevesParSalle] = useState<Record<string, EleveClasseOut[]>>({});
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const [nouveauSujet, setNouveauSujet] = useState("");
  const [nouvelEleveId, setNouvelEleveId] = useState("");
  const [question, setQuestion] = useState("");

  const charger = () => {
    setChargement(true);
    listerMesSessionsElProfessorEnseignant()
      .then((res) => {
        setSessions(res.data);
        if (!sessionId && res.data.length > 0) setSessionId(res.data[0].id);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  useEffect(() => {
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

  const tousLesEleves = Object.values(elevesParSalle).flat();

  const ouvrirNouvelleSession = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    try {
      const res = await ouvrirSessionElProfessorEnseignant(nouvelEleveId || undefined, nouveauSujet.trim() || undefined);
      setSessions((prev) => [res.data, ...prev]);
      setSessionId(res.data.id);
      setNouveauSujet("");
      setNouvelEleveId("");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir cette session."));
    }
  };

  const poserQuestion = async (e: FormEvent) => {
    e.preventDefault();
    if (!sessionId || !question.trim()) return;
    setErreur(null);
    setEnCours(true);
    try {
      const res = await poserQuestionElProfessorEnseignant(sessionId, question.trim());
      setSessions((prev) => prev.map((s) => (s.id === sessionId ? res.data : s)));
      setQuestion("");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'obtenir une réponse."));
    } finally {
      setEnCours(false);
    }
  };

  const sessionCourante = sessions.find((s) => s.id === sessionId) ?? null;

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Espace Enseignant"
        title="El Professor"
        desc="Un conseil sur le plan éducatif, moral, professionnel ou humain, à propos d'un élève ou d'une question générale."
      />
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card variant="soft" style={{ marginBottom: "24px" }}>
        <form onSubmit={ouvrirNouvelleSession} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ minWidth: "220px" }}>
            <Field label="Élève concerné (optionnel)">
              <Select value={nouvelEleveId} onChange={(e) => setNouvelEleveId(e.target.value)}>
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
          </div>
          <div style={{ flex: 1, minWidth: "200px" }}>
            <Field label="Sujet (optionnel)">
              <TextArea rows={1} value={nouveauSujet} onChange={(e) => setNouveauSujet(e.target.value)} placeholder="Ex. Décrochage en classe" />
            </Field>
          </div>
          <Btn type="submit" variant="primary" size="sm" leftIcon={<Plus size={14} />}>
            Nouvelle conversation
          </Btn>
        </form>
      </Card>

      {chargement ? (
        <SkeletonCard />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "20px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {sessions.map((s) => {
              const eleve = tousLesEleves.find((e) => e.utilisateur_id === s.eleve_utilisateur_id);
              return (
                <button
                  key={s.id}
                  onClick={() => setSessionId(s.id)}
                  style={{
                    textAlign: "left",
                    padding: "8px 10px",
                    borderRadius: "var(--radius-sm)",
                    border: "none",
                    cursor: "pointer",
                    background: s.id === sessionId ? "var(--primary-tint)" : "var(--surface-2)",
                    fontSize: "var(--text-sm)",
                  }}
                >
                  {s.sujet || (eleve ? `${eleve.prenom} ${eleve.nom}` : "Conversation")}
                </button>
              );
            })}
          </div>

          <Card>
            {!sessionCourante ? (
              <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>
                Ouvrez une nouvelle conversation pour commencer.
              </p>
            ) : (
              <>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "16px", maxHeight: "420px", overflowY: "auto" }}>
                  {sessionCourante.messages.length === 0 && (
                    <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Bot size={16} /> Posez votre première question.
                    </p>
                  )}
                  {sessionCourante.messages.map((m) => (
                    <div
                      key={m.id}
                      style={{
                        alignSelf: m.role === "enseignant" ? "flex-end" : "flex-start",
                        maxWidth: "85%",
                        background: m.role === "enseignant" ? "var(--primary-tint)" : "var(--magic-tint)",
                        borderRadius: "var(--radius-md)",
                        padding: "8px 12px",
                        fontSize: "var(--text-sm)",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {m.contenu.includes("⚠️") && (
                        <div style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--action-deep)", fontWeight: 700, marginBottom: "4px" }}>
                          <TriangleAlert size={14} /> Situation sensible détectée
                        </div>
                      )}
                      {m.contenu}
                    </div>
                  ))}
                </div>
                <form onSubmit={poserQuestion} style={{ display: "flex", gap: "8px" }}>
                  <TextArea
                    rows={2}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Votre question..."
                    style={{ flex: 1 }}
                  />
                  <Btn type="submit" variant="primary" loading={enCours} leftIcon={<Send size={14} />}>
                    Envoyer
                  </Btn>
                </form>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
