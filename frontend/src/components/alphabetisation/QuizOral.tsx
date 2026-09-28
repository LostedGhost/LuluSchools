import { useEffect, useState } from "react";
import { CheckCircle2, Volume2, XCircle } from "lucide-react";
import { messageErreur } from "../../api/client";
import { obtenirQuiz } from "../../api/pedagogie";
import { essayerQuiz, type EssaiQuizOut } from "../../api/alphabetisation";
import { lireTexte } from "../../accessibilite/lecteurVocal";
import { Btn, ErrorBanner, Skeleton } from "../ui";
import type { QuizOut } from "../../types/api";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.7 — quiz oral pour adultes en alphabétisation : chaque question et chaque
   réponse se font lire à voix haute ; les réponses sont de grands boutons numérotés.
   Entraînement libre : le résultat n'est jamais enregistré.
   ═══════════════════════════════════════════════════════════════ */

const dire = (texte: string) => void lireTexte(texte).catch(() => {});

export function QuizOral({ quizId }: { quizId: string }) {
  const [quiz, setQuiz] = useState<QuizOut | null>(null);
  const [reponses, setReponses] = useState<(number | null)[]>([]);
  const [resultat, setResultat] = useState<EssaiQuizOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  useEffect(() => {
    obtenirQuiz(quizId)
      .then((res) => {
        setQuiz(res.data);
        setReponses(res.data.questions.map(() => null));
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [quizId]);

  if (!quiz) return erreur ? <ErrorBanner>{erreur}</ErrorBanner> : <Skeleton height="120px" />;

  const questionAVoixHaute = (i: number) => {
    const q = quiz.questions[i];
    dire(`Question ${i + 1}. ${q.enonce} ${q.choix.map((c, j) => `Réponse ${j + 1} : ${c}.`).join(" ")}`);
  };

  const valider = async () => {
    setEnvoi(true);
    setErreur(null);
    try {
      const res = await essayerQuiz(quiz.id, reponses.map((r) => r ?? -1));
      setResultat(res.data);
      const bonnes = res.data.bonnes_reponses.filter((b, i) => b === reponses[i]).length;
      dire(
        `${res.data.reussie ? "Bravo !" : "Continuez, vous progressez."} ${bonnes} bonne${bonnes > 1 ? "s" : ""} réponse${bonnes > 1 ? "s" : ""} sur ${quiz.questions.length}.`,
      );
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="quiz-oral">
      <ErrorBanner>{erreur}</ErrorBanner>
      {quiz.questions.map((q, i) => (
        <fieldset key={i} className="quiz-oral-question">
          <legend>
            <button type="button" className="quiz-oral-ecouter" onClick={() => questionAVoixHaute(i)} aria-label={`Écouter la question ${i + 1}`}>
              <Volume2 size={24} aria-hidden="true" />
            </button>
            <span>{q.enonce}</span>
          </legend>
          <div className="quiz-oral-choix">
            {q.choix.map((choix, j) => {
              const bonne = resultat?.bonnes_reponses[i] === j;
              const fausse = resultat && reponses[i] === j && !bonne;
              return (
                <button
                  key={j}
                  type="button"
                  className={`quiz-oral-reponse ${reponses[i] === j ? "choisie" : ""} ${bonne ? "bonne" : ""} ${fausse ? "fausse" : ""}`}
                  aria-pressed={reponses[i] === j}
                  disabled={!!resultat}
                  onClick={() => {
                    setReponses((r) => r.map((x, k) => (k === i ? j : x)));
                    dire(choix);
                  }}
                >
                  <span className="quiz-oral-numero" aria-hidden="true">{j + 1}</span>
                  <span>{choix}</span>
                  {bonne && <CheckCircle2 size={22} aria-label="bonne réponse" />}
                  {fausse && <XCircle size={22} aria-label="réponse fausse" />}
                </button>
              );
            })}
          </div>
        </fieldset>
      ))}
      {resultat ? (
        <Btn
          variant="ghost"
          onClick={() => {
            setResultat(null);
            setReponses(quiz.questions.map(() => null));
          }}
        >
          Recommencer
        </Btn>
      ) : (
        <Btn variant="primary" size="lg" onClick={valider} loading={envoi} disabled={reponses.some((r) => r === null)}>
          Vérifier mes réponses
        </Btn>
      )}
    </div>
  );
}
