import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listerCours, listerQuiz } from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { CoursOut, QuizOut } from "../../types/api";
import { Card, ErrorBanner, PageTitle } from "../../components/ui";

export function CoursListPage() {
  const profil = useEleveProfil();
  const [cours, setCours] = useState<CoursOut[]>([]);
  const [quizParCours, setQuizParCours] = useState<Record<string, QuizOut[]>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!profil.classe_id) return;
    listerCours(profil.classe_id)
      .then(async (res) => {
        setCours(res.data);
        const entrees = await Promise.all(
          res.data.map(async (c) => [c.id, (await listerQuiz(c.id)).data] as const),
        );
        setQuizParCours(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [profil.classe_id]);

  return (
    <div>
      <PageTitle>Cours de ma classe</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {cours.length === 0 && <p className="text-slate-500">Aucun cours publie pour l'instant.</p>}
      <div className="space-y-3">
        {cours.map((c) => (
          <Card key={c.id}>
            <p className="font-medium text-slate-900">{c.titre}</p>
            <p className="text-sm text-slate-500">{c.chapitre}</p>
            {(quizParCours[c.id] ?? []).length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {quizParCours[c.id].map((quiz, idx) => (
                  <Link
                    key={quiz.id}
                    to={`/eleve/quiz/${quiz.id}`}
                    className="rounded-lg bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
                  >
                    Quiz {idx + 1} ({quiz.questions.length} questions)
                  </Link>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
