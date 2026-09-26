import { useEffect, useRef, useState, type FormEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  listerCours,
  listerQuiz,
  obtenirLienFichierCours,
  ouvrirSessionElProfessor,
  poserQuestionElProfessor,
} from "../../api/pedagogie";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { CoursOut, QuizOut, SessionElProfessorOut } from "../../types/api";
import {
  Card,
  ErrorBanner,
  SectionHead,
  Badge,
  Btn,
  Skeleton,
  TextArea,
} from "../../components/ui";
import { Target, FileText, Headphones, Video, ExternalLink, Sparkles, Send } from "lucide-react";

const LABEL_FORMAT: Record<CoursOut["format"], string> = {
  texte: "Texte",
  pdf: "Document PDF",
  audio: "Audio",
  video: "Vidéo",
};

const ICONE_FORMAT: Record<CoursOut["format"], typeof FileText> = {
  texte: FileText,
  pdf: FileText,
  audio: Headphones,
  video: Video,
};

export function CoursDetailPage() {
  const { coursId } = useParams<{ coursId: string }>();
  const profil = useEleveProfil();
  const navigate = useNavigate();

  const [cours, setCours] = useState<CoursOut | null>(null);
  const [quizzes, setQuizzes] = useState<QuizOut[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lienFichier, setLienFichier] = useState<string | null>(null);
  const [chargementLien, setChargementLien] = useState(false);

  const [sessionElProf, setSessionElProf] = useState<SessionElProfessorOut | null>(null);
  const [chatOuvert, setChatOuvert] = useState(false);
  const [chargementChat, setChargementChat] = useState(false);
  const [question, setQuestion] = useState("");
  const [envoiQuestion, setEnvoiQuestion] = useState(false);
  const [erreurChat, setErreurChat] = useState<string | null>(null);
  const finDuChat = useRef<HTMLDivElement>(null);

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

  const ouvrirFichier = async () => {
    if (!cours) return;
    setChargementLien(true);
    setErreur(null);
    try {
      const res = await obtenirLienFichierCours(cours.id);
      window.open(res.data.url, "_blank", "noopener,noreferrer");
      setLienFichier(res.data.url);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir ce fichier pour le moment."));
    } finally {
      setChargementLien(false);
    }
  };

  useEffect(() => {
    finDuChat.current?.scrollIntoView({ behavior: "smooth" });
  }, [sessionElProf?.messages.length]);

  const ouvrirElProfessor = async () => {
    if (!cours) return;
    setChatOuvert(true);
    if (sessionElProf) return;
    setChargementChat(true);
    setErreurChat(null);
    try {
      const res = await ouvrirSessionElProfessor(cours.id);
      setSessionElProf(res.data);
    } catch (err) {
      setErreurChat(messageErreur(err, "Impossible d'ouvrir El Professor pour le moment."));
    } finally {
      setChargementChat(false);
    }
  };

  const envoyerQuestion = async (e: FormEvent) => {
    e.preventDefault();
    if (!sessionElProf || !question.trim()) return;
    setEnvoiQuestion(true);
    setErreurChat(null);
    try {
      const res = await poserQuestionElProfessor(sessionElProf.id, question.trim());
      setSessionElProf(res.data);
      setQuestion("");
    } catch (err) {
      setErreurChat(messageErreur(err, "El Professor n'a pas pu répondre, réessayez."));
    } finally {
      setEnvoiQuestion(false);
    }
  };

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
              cours.contenu_texte ? (
                <p style={{ color: 'var(--ink)', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{cours.contenu_texte}</p>
              ) : (
                <p style={{ color: 'var(--ink-soft)' }}>Ce cours n'a pas encore de contenu texte renseigné.</p>
              )
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
                <div style={{
                  width: '48px', height: '48px', borderRadius: 'var(--radius-md)',
                  background: 'var(--primary-tint)', color: 'var(--primary-deep)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }} aria-hidden="true">
                  {(() => { const Icone = ICONE_FORMAT[cours.format]; return <Icone size={22} />; })()}
                </div>
                <div style={{ flex: 1, minWidth: '160px' }}>
                  <p style={{ color: 'var(--ink)', fontWeight: 600, marginBottom: '2px' }}>{LABEL_FORMAT[cours.format]}</p>
                  <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--text-sm)' }}>
                    S'ouvre dans un nouvel onglet.
                  </p>
                </div>
                <Btn variant="primary" onClick={ouvrirFichier} loading={chargementLien} rightIcon={<ExternalLink size={16} />}>
                  {lienFichier ? "Rouvrir le fichier" : "Ouvrir le fichier"}
                </Btn>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* El Professor — assistant IA */}
      <div style={{ marginBottom: 'var(--space-8)' }} className="anim-slide-up delay-1">
        <SectionHead
          title="El Professor"
          desc="Pose une question sur ce cours à l'assistant pédagogique, disponible à tout moment."
        />
        <Card style={{ border: '1px solid color-mix(in srgb, var(--info-deep) 25%, transparent)', background: 'var(--magic-tint)' }}>
          {!chatOuvert ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
              <div style={{
                width: '48px', height: '48px', borderRadius: 'var(--radius-md)',
                background: 'var(--info-deep)', color: 'var(--on-primary)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }} aria-hidden="true">
                <Sparkles size={22} />
              </div>
              <div style={{ flex: 1, minWidth: '160px' }}>
                <p style={{ color: 'var(--ink)', fontWeight: 600, marginBottom: '2px' }}>Une question sur ce cours ?</p>
                <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--text-sm)' }}>
                  El Professor répond à tes questions en te guidant, sans te donner les réponses des devoirs.
                </p>
              </div>
              <Btn variant="magic" onClick={ouvrirElProfessor} leftIcon={<Sparkles size={16} />}>
                Discuter avec El Professor
              </Btn>
            </div>
          ) : (
            <div>
              <ErrorBanner>{erreurChat}</ErrorBanner>
              {chargementChat ? (
                <Skeleton height="120px" />
              ) : (
                <>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', maxHeight: '360px', overflowY: 'auto', marginBottom: 'var(--space-3)' }}>
                    {sessionElProf?.messages.length === 0 && (
                      <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--text-sm)' }}>
                        Pose ta première question ci-dessous.
                      </p>
                    )}
                    {sessionElProf?.messages.map((m) => (
                      <div key={m.id} style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === "eleve" ? "flex-end" : "flex-start" }}>
                        <div
                          style={{
                            maxWidth: '85%',
                            padding: '10px 14px',
                            borderRadius: 'var(--radius-lg)',
                            background: m.role === "eleve" ? 'var(--primary)' : 'var(--surface)',
                            color: m.role === "eleve" ? 'var(--on-primary)' : 'var(--ink)',
                            border: m.role === "eleve" ? 'none' : '1px solid var(--border)',
                          }}
                        >
                          <p style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 'var(--text-sm)' }}>{m.contenu}</p>
                        </div>
                      </div>
                    ))}
                    <div ref={finDuChat} />
                  </div>
                  <form onSubmit={envoyerQuestion} style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'flex-end' }}>
                    <div style={{ flex: 1 }}>
                      <TextArea
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Écris ta question..."
                        rows={1}
                        style={{ minHeight: '44px' }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            envoyerQuestion(e as unknown as FormEvent);
                          }
                        }}
                      />
                    </div>
                    <Btn type="submit" variant="magic" loading={envoiQuestion} disabled={!question.trim()} aria-label="Envoyer la question">
                      <Send size={16} />
                    </Btn>
                  </form>
                </>
              )}
            </div>
          )}
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
