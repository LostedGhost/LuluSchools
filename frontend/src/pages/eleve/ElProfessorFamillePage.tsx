import { useEffect, useState, type FormEvent } from "react";
import {
  listerMesSessionsElProfessorFamille,
  poserQuestionElProfessorFamille,
  rejoindreSessionElProfessorFamille,
} from "../../api/el_professor_famille";
import { messageErreur } from "../../api/client";
import type { SessionElProfessorFamilleOut } from "../../types/api";
import { Btn, Card, EmptyState, ErrorBanner, SectionHead, SkeletonCard, TextArea } from "../../components/ui";
import { Bot, Send, TriangleAlert, Users } from "lucide-react";

export function ElProfessorFamillePage() {
  const [sessions, setSessions] = useState<SessionElProfessorFamilleOut[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [rejointEnCoursId, setRejointEnCoursId] = useState<string | null>(null);
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

  const rejoindre = async (id: string) => {
    setRejointEnCoursId(id);
    setErreur(null);
    try {
      const res = await rejoindreSessionElProfessorFamille(id);
      setSessions((prev) => prev.map((s) => (s.id === id ? res.data : s)));
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de rejoindre cette conversation."));
    } finally {
      setRejointEnCoursId(null);
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
        eyebrow="Espace Élève"
        title="El Professor Famille"
        desc="Un fil de discussion partagé avec votre tuteur, quand il vous y invite."
      />
      <ErrorBanner>{erreur}</ErrorBanner>

      {chargement ? (
        <SkeletonCard />
      ) : sessions.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucune invitation" desc="Votre tuteur peut vous inviter à une conversation partagée depuis son espace." />
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
                {s.sujet || "Conversation"} {!s.rejointe_le && "(à rejoindre)"}
              </button>
            ))}
          </div>

          <Card>
            {!sessionCourante ? (
              <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>Sélectionnez une conversation.</p>
            ) : !sessionCourante.rejointe_le ? (
              <div>
                <p style={{ fontSize: "var(--text-sm)", marginBottom: "12px" }}>
                  Votre tuteur vous invite à une conversation avec El Professor. Rejoignez-la pour commencer à échanger tous les deux.
                </p>
                <Btn variant="primary" size="sm" loading={rejointEnCoursId === sessionCourante.id} onClick={() => rejoindre(sessionCourante.id)}>
                  Rejoindre la conversation
                </Btn>
              </div>
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
                        background: m.role === "assistant" ? "var(--magic-tint)" : m.role === "eleve" ? "var(--primary-tint)" : "var(--reward-tint)",
                        borderRadius: "var(--radius-md)",
                        padding: "8px 12px",
                        fontSize: "var(--text-sm)",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {m.role !== "assistant" && (
                        <div style={{ fontSize: "10px", fontWeight: 700, textTransform: "uppercase", color: "var(--ink-faint)", marginBottom: "2px" }}>
                          {m.role === "eleve" ? "Vous" : "Votre tuteur"}
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
    </div>
  );
}
