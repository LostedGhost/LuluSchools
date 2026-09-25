import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { mesTentatives, obtenirQuiz, tenterQuiz } from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import type { QuizOut, TentativeQuizOut } from "../../types/api";
import { Badge, Card, ErrorBanner, Btn } from "../../components/ui";
import { ScoreBurst } from "../../components/gamification";

export function QuizPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const [quiz, setQuiz] = useState<QuizOut | null>(null);
  const [reponses, setReponses] = useState<Record<string, number>>({});
  const [tentatives, setTentatives] = useState<TentativeQuizOut[]>([]);
  const [resultat, setResultat] = useState<TentativeQuizOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    if (!quizId) return;
    obtenirQuiz(quizId)
      .then((res) => setQuiz(res.data))
      .catch((err) => setErreur(messageErreur(err)));
    mesTentatives(quizId)
      .then((res) => setTentatives(res.data))
      .catch(() => undefined);
  };

  useEffect(charger, [quizId]);

  const choisir = (questionId: string, index: number) => {
    setReponses((prev) => ({ ...prev, [questionId]: index }));
  };

  const soumettre = async () => {
    if (!quiz || !quizId) return;
    const questionsTriees = [...quiz.questions].sort((a, b) => a.ordre - b.ordre);
    if (questionsTriees.some((q) => reponses[q.id] === undefined)) {
      setErreur("Veuillez répondre à toutes les questions.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      const { data } = await tenterQuiz(
        quizId,
        questionsTriees.map((q) => reponses[q.id]),
      );
      setResultat(data);
      setReponses({});
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  };

  if (!quiz) return <div className="page-content page-content-narrow"><ErrorBanner>{erreur}</ErrorBanner></div>;

  const questionsTriees = [...quiz.questions].sort((a, b) => a.ordre - b.ordre);
  const totalQuestions = questionsTriees.length;
  const repondues = Object.keys(reponses).length;
  const progressPercent = totalQuestions > 0 ? (repondues / totalQuestions) * 100 : 0;

  return (
    <div className="page-content page-content-narrow">
      <div style={{ marginBottom: "32px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <p className="text-eyebrow">Évaluation Continue</p>
          <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Quiz ({totalQuestions} questions)</h1>
        </div>
        <Badge tone="magic">Terminer = +25 XP</Badge>
      </div>

      <div style={{ width: "100%", height: "8px", backgroundColor: "var(--surface-2)", borderRadius: "var(--radius-pill)", overflow: "hidden", marginBottom: "24px" }}>
        <div style={{ width: `${progressPercent}%`, height: "100%", backgroundColor: "var(--primary)", transition: "width 0.3s ease" }}></div>
      </div>
      <p className="text-sm" style={{ color: "var(--ink-soft)", marginBottom: "32px" }}>Seuil de réussite : {quiz.seuil_reussite}%</p>

      {resultat && (
        <Card className="anim-burst" style={{ marginBottom: "32px", textAlign: "center", border: "2px solid var(--primary)" }}>
          <ScoreBurst
            score={resultat.score}
            max={100}
            label="/ 100"
            tone={resultat.reussie ? "success" : "error"}
          />
          <div style={{ marginTop: "16px" }}>
            <Badge tone={resultat.reussie ? "success" : "error"}>
              {resultat.reussie ? "Réussi — bien joué !" : "Non réussi, continue tes efforts !"}
            </Badge>
          </div>
        </Card>
      )}

      {tentatives.length > 0 && !resultat && (
        <Card variant="soft" style={{ marginBottom: "32px" }}>
          <p className="text-label" style={{ marginBottom: "12px", color: "var(--ink-soft)" }}>Mes tentatives précédentes</p>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {tentatives.map((t) => (
              <li key={t.id}>
                <Badge tone={t.reussie ? "success" : "error"}>{t.score.toFixed(0)}%</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
        {questionsTriees.map((question, idx) => (
          <Card key={question.id} className="anim-slide-up" style={{ animationDelay: `${idx * 0.1}s` }}>
            <p className="text-display" style={{ fontSize: "2rem", color: "var(--primary-tint)", marginBottom: "16px", opacity: 0.5 }}>
              Q{idx + 1}
            </p>
            <p className="text-title" style={{ marginBottom: "24px" }}>
              {question.enonce}
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {question.choix.map((choix, choixIdx) => {
                const isSelected = reponses[question.id] === choixIdx;
                return (
                  <button
                    key={choixIdx}
                    type="button"
                    onClick={() => choisir(question.id, choixIdx)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "16px",
                      borderRadius: "var(--radius-md)",
                      border: isSelected ? "2px solid var(--primary)" : "2px solid var(--border)",
                      backgroundColor: isSelected ? "var(--primary-tint)" : "var(--surface)",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.2s ease"
                    }}
                  >
                    <div style={{
                      width: "20px",
                      height: "20px",
                      borderRadius: "50%",
                      border: isSelected ? "6px solid var(--primary)" : "2px solid var(--border)",
                      flexShrink: 0
                    }} />
                    <span style={{ fontWeight: isSelected ? "600" : "400", color: "var(--ink)" }}>{choix}</span>
                  </button>
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      <div style={{ marginTop: "32px" }}>
        {erreur && <ErrorBanner>{erreur}</ErrorBanner>}
        <Btn
          variant="primary"
          size="lg"
          loading={enCours}
          onClick={soumettre}
          style={{ width: "100%", marginTop: "16px" }}
        >
          Valider mes réponses
        </Btn>
      </div>
    </div>
  );
}
