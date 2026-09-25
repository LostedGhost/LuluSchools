import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { mesTentatives, obtenirQuiz, tenterQuiz } from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import type { QuizOut, TentativeQuizOut } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle, PrimaryButton } from "../../components/ui";

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
      setErreur("Veuillez repondre a toutes les questions.");
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

  if (!quiz) return <ErrorBanner>{erreur}</ErrorBanner>;

  const questionsTriees = [...quiz.questions].sort((a, b) => a.ordre - b.ordre);

  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle>Quiz ({quiz.questions.length} questions)</PageTitle>
      <p className="mb-4 text-sm text-slate-500">Seuil de reussite : {quiz.seuil_reussite}%</p>

      {resultat && (
        <Card className="mb-4">
          <p className="text-lg font-semibold">
            Score : {resultat.score.toFixed(0)}%{" "}
            <Badge tone={resultat.reussie ? "green" : "red"}>
              {resultat.reussie ? "Reussi" : "Non reussi"}
            </Badge>
          </p>
        </Card>
      )}

      {tentatives.length > 0 && (
        <Card className="mb-4">
          <p className="mb-2 text-sm font-medium text-slate-700">Mes tentatives precedentes</p>
          <ul className="space-y-1 text-sm text-slate-600">
            {tentatives.map((t) => (
              <li key={t.id}>
                {t.score.toFixed(0)}% — {t.reussie ? "reussi" : "non reussi"}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card>
        <div className="space-y-6">
          {questionsTriees.map((question, idx) => (
            <div key={question.id}>
              <p className="mb-2 font-medium text-slate-900">
                {idx + 1}. {question.enonce}
              </p>
              <div className="space-y-2">
                {question.choix.map((choix, choixIdx) => (
                  <label
                    key={choixIdx}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50"
                  >
                    <input
                      type="radio"
                      name={question.id}
                      checked={reponses[question.id] === choixIdx}
                      onChange={() => choisir(question.id, choixIdx)}
                    />
                    {choix}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
        <ErrorBanner>{erreur}</ErrorBanner>
        <PrimaryButton type="button" onClick={soumettre} disabled={enCours} className="mt-4 w-full">
          {enCours ? "Envoi..." : "Valider mes reponses"}
        </PrimaryButton>
      </Card>
    </div>
  );
}
