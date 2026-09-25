import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { listerCours, listerQuiz } from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { CoursOut, QuizOut } from "../../types/api";
import {
  Card,
  ErrorBanner,
  SectionHead,
  Badge,
  Btn,
  Skeleton
} from "../../components/ui";
import { Target } from "lucide-react";


export function CoursDetailPage() {
  const { coursId } = useParams<{ coursId: string }>();
  const profil = useEleveProfil();
  const navigate = useNavigate();
  
  const [cours, setCours] = useState<CoursOut | null>(null);
  const [quizzes, setQuizzes] = useState<QuizOut[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profil.classe_id || !coursId) return;
    
    setLoading(true);
    listerCours(profil.classe_id)
      .then(async (res) => {
        const found = res.data.find(c => c.id === coursId);
        if (found) {
          setCours(found);
          const qRes = await listerQuiz(found.id);
          setQuizzes(qRes.data);
        } else {
          setErreur("Cours introuvable.");
        }
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setLoading(false));
  }, [profil.classe_id, coursId]);

  if (loading) {
    return (
      <div className="page-content-narrow space-y-4">
        <Skeleton height="60px" width="70%" />
        <Skeleton height="300px" width="100%" />
      </div>
    );
  }

  if (!cours) {
    return (
      <div className="page-content-narrow">
        <ErrorBanner>{erreur || "Cours introuvable."}</ErrorBanner>
        <Btn variant="outline" onClick={() => navigate("/eleve/cours")}>Retour aux cours</Btn>
      </div>
    );
  }

  return (
    <div className="page-content-narrow">
      <Btn variant="ghost" size="sm" onClick={() => navigate("/eleve/cours")} style={{ marginBottom: 'var(--space-4)' }}>
        ← Retour aux cours
      </Btn>

      {/* Hero Section */}
      <div style={{ marginBottom: 'var(--space-8)' }} className="anim-pop-in">
        <h1 className="text-headline" style={{ marginBottom: 'var(--space-2)' }}>
          {cours.titre}
        </h1>
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', alignItems: 'center' }}>
          <Badge tone="info">{cours.chapitre}</Badge>
          <Badge tone="magic">Format: {cours.format}</Badge>
        </div>
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>

      {/* Course Content */}
      <div style={{ marginBottom: 'var(--space-8)' }} className="anim-slide-up delay-1">
        <SectionHead title="Contenu du cours" />
        <Card variant="soft">
          <div style={{ padding: 'var(--space-4)' }}>
            {cours.format === "texte" ? (
              <p style={{ color: 'var(--ink)' }}>Contenu texte non disponible (simulation de contenu pour {cours.titre}).</p>
            ) : (
              <p style={{ color: 'var(--ink)' }}>Format {cours.format} à télécharger / visualiser.</p>
            )}
            {/* Si c'était un vrai markdown on utiliserait un composant Markdown ici */}
          </div>
        </Card>
      </div>

      {/* Quizzes Section */}
      {quizzes.length > 0 && (
        <div className="anim-slide-up delay-2">
          <SectionHead title="Évaluation" desc="Teste tes connaissances pour gagner de l'XP !" />
          <div className="grid-2">
            {quizzes.map((quiz, idx) => (
              <Card key={quiz.id} style={{ border: '1px solid color-mix(in srgb, var(--reward-deep) 30%, transparent)', background: 'var(--reward-tint)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                  <div style={{ color: 'var(--reward-deep)', display: 'flex' }} aria-hidden="true"><Target size={28} /></div>
                  <div>
                    <h3 className="text-title">Quiz {idx + 1}</h3>
                    <p className="text-label" style={{ color: 'var(--reward-deep)' }}>+100 XP à gagner</p>
                  </div>
                </div>
                <Btn 
                  variant="reward" 
                  size="md" 
                  style={{ width: '100%' }}
                  onClick={() => navigate(`/eleve/quiz/${quiz.id}`)}
                >
                  Lancer le quiz ({quiz.questions.length} Q)
                </Btn>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
