import { useEffect, useState } from "react";
import { BookOpenCheck, MapPin, Volume2 } from "lucide-react";
import { messageErreur } from "../../api/client";
import { classesAlphabetisation, inscrireAlphabetisation, type ClasseAlphabetisation } from "../../api/alphabetisation";
import { listerCours, listerQuiz } from "../../api/pedagogie";
import { lireTexte } from "../../accessibilite/lecteurVocal";
import { QuizOral } from "../../components/alphabetisation/QuizOral";
import { TranscriptionCours } from "../../components/transcription/LecteurCours";
import { Btn, Card, EmptyState, ErrorBanner, SectionHead, Skeleton, SuccessBanner } from "../../components/ui";
import type { CoursOut, QuizOut } from "../../types/api";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.7 — « Apprendre à lire » : un parent suit une classe d'un centre
   d'alphabétisation avec son propre compte. Leçons courtes à écouter, quiz oral.
   (PAG 2021-2026, axe 5, action 4 : alphabétisation et éducation des adultes.)
   ═══════════════════════════════════════════════════════════════ */

const dire = (texte: string) => void lireTexte(texte).catch(() => {});

function Lecon({ cours }: { cours: CoursOut }) {
  const [quiz, setQuiz] = useState<QuizOut[] | null>(null);
  useEffect(() => {
    listerQuiz(cours.id).then((r) => setQuiz(r.data)).catch(() => setQuiz([]));
  }, [cours.id]);
  const texte = cours.transcription ?? cours.contenu_texte ?? "";
  return (
    <Card>
      <h3 className="text-title" style={{ margin: 0 }}>{cours.titre}</h3>
      <p className="text-eyebrow" style={{ margin: "4px 0 0" }}>{cours.chapitre}</p>
      {texte && <TranscriptionCours texte={texte} titre="La leçon" />}
      {quiz?.map((q) => (
        <div key={q.id} style={{ marginTop: "var(--space-5)" }}>
          <h4 style={{ margin: "0 0 8px" }}>Je m'entraîne</h4>
          <QuizOral quizId={q.id} />
        </div>
      ))}
    </Card>
  );
}

export function AlphabetisationPage() {
  const [classes, setClasses] = useState<ClasseAlphabetisation[] | null>(null);
  const [cours, setCours] = useState<Record<string, CoursOut[]>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);

  const charger = () => {
    classesAlphabetisation()
      .then(async (res) => {
        setClasses(res.data);
        const miennes = res.data.filter((c) => c.inscrit);
        const entrees = await Promise.all(miennes.map(async (c) => [c.classe_id, (await listerCours(c.classe_id)).data] as const));
        setCours(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)));
  };
  useEffect(charger, []);

  const inscrire = async (classe: ClasseAlphabetisation) => {
    setEnCours(classe.classe_id);
    setErreur(null);
    try {
      await inscrireAlphabetisation(classe.classe_id);
      setSucces(`Vous êtes inscrit au ${classe.centre_nom}.`);
      dire(`Bienvenue. Vous êtes inscrit au ${classe.centre_nom}. Vos leçons sont maintenant sur cette page.`);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(null);
    }
  };

  const miennes = classes?.filter((c) => c.inscrit) ?? [];
  const autres = classes?.filter((c) => !c.inscrit) ?? [];

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="APPRENDRE À LIRE"
        title="Alphabétisation des adultes"
        desc="Des leçons courtes à écouter et des exercices qui se lisent à voix haute, sur votre téléphone, à votre rythme."
      />
      <Btn
        variant="ghost"
        onClick={() => dire("Cette page vous permet d'apprendre à lire, à écrire et à compter. Touchez un haut-parleur pour écouter.")}
        leftIcon={<Volume2 size={18} aria-hidden="true" />}
        style={{ marginBottom: "var(--space-4)" }}
      >
        Écouter l'explication
      </Btn>
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      {!classes ? (
        <Skeleton height="200px" />
      ) : (
        <>
          {miennes.map((classe) => (
            <section key={classe.classe_id} style={{ marginBottom: "var(--space-8)" }} aria-label={classe.niveau}>
              <h2 className="text-title">{classe.niveau} — {classe.centre_nom}</h2>
              <div style={{ display: "grid", gap: "var(--space-4)" }}>
                {(cours[classe.classe_id] ?? []).map((c) => <Lecon key={c.id} cours={c} />)}
                {cours[classe.classe_id]?.length === 0 && (
                  <EmptyState icon={<BookOpenCheck size={28} />} title="Pas encore de leçon" desc="L'alphabétiseur publiera bientôt la première leçon." />
                )}
              </div>
            </section>
          ))}

          <SectionHead
            title={miennes.length ? "Autres centres" : "Choisir un centre près de chez vous"}
            desc="L'inscription est gratuite et se fait avec votre compte."
          />
          {autres.length === 0 ? (
            <EmptyState icon={<MapPin size={28} />} title="Aucun autre centre disponible" desc="Revenez plus tard : de nouveaux centres ouvrent chaque année." />
          ) : (
            <div className="grid-2">
              {autres.map((c) => (
                <Card key={c.classe_id}>
                  <h3 className="text-title" style={{ margin: 0 }}>{c.centre_nom}</h3>
                  <p style={{ margin: "4px 0", color: "var(--ink-soft)" }}>
                    {c.niveau}
                    {c.commune ? ` · ${c.commune} (${c.departement})` : ""}
                  </p>
                  <p style={{ margin: "0 0 10px", fontSize: "var(--text-sm)" }}>
                    {c.places_restantes > 0 ? `${c.places_restantes} place(s) libre(s)` : "Complet"}
                  </p>
                  <Btn variant="primary" disabled={c.places_restantes === 0} loading={enCours === c.classe_id} onClick={() => inscrire(c)}>
                    M'inscrire
                  </Btn>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
