import { useEffect, useState, type FormEvent } from "react";
import {
  alertesElProfessorDeMonEnfant,
  listerMesSessionsElProfessorTuteur,
  ouvrirSessionElProfessorTuteur,
  poserQuestionElProfessorTuteur,
} from "../../api/el_professor_tuteur";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { AlerteElProfessorOut, SessionElProfessorTuteurOut } from "../../types/api";
import { Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard, TextArea } from "../../components/ui";
import { Bot, Plus, Send, TriangleAlert, Users } from "lucide-react";

export function ElProfessorTuteurPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [sessions, setSessions] = useState<SessionElProfessorTuteurOut[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [alertes, setAlertes] = useState<AlerteElProfessorOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const [nouvelEleveId, setNouvelEleveId] = useState("");
  const [nouveauSujet, setNouveauSujet] = useState("");
  const [question, setQuestion] = useState("");

  useEffect(() => {
    listerMesSessionsElProfessorTuteur()
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

  useEffect(() => {
    if (!nouvelEleveId) return;
    alertesElProfessorDeMonEnfant(nouvelEleveId)
      .then((res) => setAlertes(res.data))
      .catch(() => undefined);
  }, [nouvelEleveId]);

  const ouvrirNouvelleSession = async (e: FormEvent) => {
    e.preventDefault();
    if (!nouvelEleveId) return;
    setErreur(null);
    try {
      const res = await ouvrirSessionElProfessorTuteur(nouvelEleveId, nouveauSujet.trim() || undefined);
      setSessions((prev) => [res.data, ...prev]);
      setSessionId(res.data.id);
      setNouveauSujet("");
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
      const res = await poserQuestionElProfessorTuteur(sessionId, question.trim());
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
        title="El Professor"
        desc="Un conseil sur la scolarité, le comportement ou l'orientation de votre enfant."
      />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" />
      ) : (
        <>
          <Card variant="soft" style={{ marginBottom: "24px" }}>
            <form onSubmit={ouvrirNouvelleSession} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ minWidth: "220px" }}>
                <Field label="Enfant concerné">
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
                  <TextArea rows={1} value={nouveauSujet} onChange={(e) => setNouveauSujet(e.target.value)} placeholder="Ex. Motivation en baisse" />
                </Field>
              </div>
              <Btn type="submit" variant="primary" size="sm" leftIcon={<Plus size={14} />}>
                Nouvelle conversation
              </Btn>
            </form>
          </Card>

          {alertes.length > 0 && (
            <Card style={{ marginBottom: "24px", borderColor: "var(--action-deep)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px", color: "var(--action-deep)", fontWeight: 700 }}>
                <TriangleAlert size={16} /> Alertes de sécurité
              </div>
              {alertes.map((a) => (
                <p key={a.id} style={{ fontSize: "var(--text-sm)", margin: "0 0 6px" }}>{a.motif}</p>
              ))}
            </Card>
          )}

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
                    {s.sujet || "Conversation"}
                  </button>
                ))}
              </div>

              <Card>
                {!sessionCourante ? (
                  <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>Ouvrez une nouvelle conversation pour commencer.</p>
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
                            alignSelf: m.role === "tuteur" ? "flex-end" : "flex-start",
                            maxWidth: "85%",
                            background: m.role === "tuteur" ? "var(--primary-tint)" : "var(--magic-tint)",
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
