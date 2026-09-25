import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listerCours, listerQuiz } from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { CoursOut, QuizOut } from "../../types/api";
import {
  Badge,
  Card,
  ErrorBanner,
  SectionHead,
  EmptyState,
  SkeletonCard,
  Btn,
} from "../../components/ui";
import { Backpack, BookOpenText } from "lucide-react";

export function CoursListPage() {
  const profil = useEleveProfil();
  const [cours, setCours] = useState<CoursOut[]>([]);
  const [quizParCours, setQuizParCours] = useState<Record<string, QuizOut[]>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profil.classe_id) {
      setLoading(false);
      return;
    }
    listerCours(profil.classe_id)
      .then(async (res) => {
        setCours(res.data);
        const entrees = await Promise.all(
          res.data.map(async (c) => [c.id, (await listerQuiz(c.id)).data] as const),
        );
        setQuizParCours(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setLoading(false));
  }, [profil.classe_id]);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Mes cours" title="Apprendre et progresser" />
      <ErrorBanner>{erreur}</ErrorBanner>

      {loading ? (
        <div className="grid-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : cours.length === 0 ? (
        <EmptyState
          icon={<Backpack size={24} />}
          title="Aucun cours disponible"
          desc="Tes enseignants n'ont pas encore publié de cours pour cette classe."
        />
      ) : (
        <div className="grid-3 anim-slide-up">
          {cours.map((c, idx) => {
            const hasQuiz = (quizParCours[c.id] ?? []).length > 0;
            return (
              <Link key={c.id} to={`/eleve/cours/${c.id}`} className={`delay-${(idx % 5) + 1}`}>
                <Card hover>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)' }}>
                    <div style={{
                      width: '48px',
                      height: '48px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--primary-tint)',
                      color: 'var(--primary-deep)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <BookOpenText size={22} aria-hidden="true" />
                    </div>
                    {hasQuiz && <Badge tone="pending">Quiz disponible</Badge>}
                  </div>
                  
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: 'var(--ink)', marginBottom: 'var(--space-1)' }}>
                    {c.titre}
                  </h3>
                  
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--ink-soft)', marginBottom: 'var(--space-4)' }}>
                    Chapitre: {c.chapitre}
                  </div>
                  
                  <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                    <Btn variant={hasQuiz ? "primary" : "outline"} size="sm">
                      Voir le cours
                    </Btn>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
