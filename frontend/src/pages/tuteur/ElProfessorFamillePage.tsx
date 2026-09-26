import { useEffect, useState, type FormEvent } from "react";
import {
  listerMesSessionsElProfessorFamille,
  ouvrirSessionElProfessorFamille,
  poserQuestionElProfessorFamille,
} from "../../api/el_professor_famille";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { SessionElProfessorFamilleOut } from "../../types/api";
import { Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard, TextArea } from "../../components/ui";
import { Bot, Plus, Send, TriangleAlert, Users } from "lucide-react";

export function ElProfessorFamillePage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [sessions, setSessions] = useState<SessionElProfessorFamilleOut[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const [nouvelEleveId, setNouvelEleveId] = useState("");
  const [nouveauSujet, setNouveauSujet] = useState("");
  const [question, setQuestion] = useState("");

  useEffect(() => {
    listerMesSessionsElProfessorFamille()
      .then((res) => {
        setSessions(res.data);
        if (res.data.length > 0) setSessionId(res.data[0].id);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, []);

  useEffect(() => {
    if (enfants.length > 0 && !nouvelEleveId) setNouvelEleveId(enfants[0].eleve_utilisateur_id ?? "");
  }, [enfants, nouvelEleveId]);

  const inviter = async (e: FormEvent) => {
    e.preventDefault();
    if (!nouvelEleveId) return;
    setErreur(null);
    try {
      const res = await ouvrirSessionElProfessorFamille(nouvelEleveId, nouveauSujet.trim() || undefined);
      setSessions((prev) => [res.data, ...prev]);
      setSessionId(res.data.id);
      setNouveauSujet("");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'inviter votre enfant."));
    }
  };

  const poserQuestion = async (e: FormEvent) => {
    e.preventDefault();
    if (!sessionId || !question.trim()) return;
    setErreur(null);
    setEnCours(true);
    try {
      const res = await poserQuestionElProfessorFamille(sessionId, question.trim());
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
        eyebrow="Espace Tuteur"
        title="El Professor Famille"
        desc="Invitez votre enfant à un fil de discussion partagé : vous posez tous les deux vos questions, l'IA s'adresse à chacun."
      />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" />
      ) : (
        <>
          <Card variant="soft" style={{ marginBottom: "24px" }}>
            <form onSubmit={inviter} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ minWidth: "220px" }}>
                <Field label="Enfant à inviter">
                  <Select value={nouvelEleveId} onChange={(e) => setNouvelEleveId(e.target.value)}>
                    {enfants.map((i) => (
                      <option key={i.id} value={i.eleve_utilisateur_id ?? ""}>
                        {i.eleve_prenom} {i.eleve_nom}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              <div style={{ flex: 1, minWidth: "200px" }}>
                <Field label="Sujet (optionnel)">
                  <TextArea rows={1} value={nouveauSujet} onChange={(e) => setNouveauSujet(e.target.value)} placeholder="Ex. Orientation en 3ème" />
                </Field>
              </div>
              <Btn type="submit" variant="primary" size="sm" leftIcon={<Plus size={14} />}>
                Inviter mon enfant
              </Btn>
            </form>
          </Card>

          {chargement ? (
            <SkeletonCard />
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: "20px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {sessions.map((s) => (
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
                    {s.sujet || "Conversation"} {!s.rejointe_le && "(en attente)"}
                  </button>
                ))}
              </div>

              <Card>
                {!sessionCourante ? (
                  <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>Invitez votre enfant pour commencer.</p>
                ) : !sessionCourante.rejointe_le ? (
                  <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-sm)" }}>
                    En attente que votre enfant rejoigne cette conversation depuis son espace élève.
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
                            alignSelf: m.role === "assistant" ? "flex-start" : "flex-end",
                            maxWidth: "85%",
                            background: m.role === "assistant" ? "var(--magic-tint)" : m.role === "tuteur" ? "var(--primary-tint)" : "var(--reward-tint)",
                            borderRadius: "var(--radius-md)",
                            padding: "8px 12px",
                            fontSize: "var(--text-sm)",
                            whiteSpace: "pre-wrap",
                          }}
                        >
                          {m.role !== "assistant" && (
                            <div style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: "2px" }}>
                              {m.role === "tuteur" ? "Vous" : "Votre enfant"}
                            </div>
                          )}
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
                      <TextArea rows={2} value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Votre question..." style={{ flex: 1 }} />
                      <Btn type="submit" variant="primary" loading={enCours} leftIcon={<Send size={14} />}>
                        Envoyer
                      </Btn>
                    </form>
                  </>
                )}
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
