import { useEffect, useState, type FormEvent } from "react";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import { creerQuiz, listerCours, listerQuiz, publierCours } from "../../api/pedagogie";
import { mesContrats } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ClasseOut, CoursOut, EtablissementOut, FormatCours, QuizOut } from "../../types/api";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../../components/ui";

export function MesCoursPage() {
  const [etablissementIds, setEtablissementIds] = useState<string[]>([]);
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [classeId, setClasseId] = useState("");
  const [cours, setCours] = useState<CoursOut[]>([]);
  const [quizParCours, setQuizParCours] = useState<Record<string, QuizOut[]>>({});

  const [titre, setTitre] = useState("");
  const [chapitre, setChapitre] = useState("");
  const [format, setFormat] = useState<FormatCours>("texte");
  const [contenuTexte, setContenuTexte] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  useEffect(() => {
    mesContrats()
      .then((res) => {
        const ids = Array.from(
          new Set(res.data.filter((c) => c.statut === "signe").map((c) => c.etablissement_id)),
        );
        setEtablissementIds(ids);
      })
      .catch((err) => setErreur(messageErreur(err)));
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!etablissementId) return;
    listerClasses(etablissementId)
      .then((res) => setClasses(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  const chargerCours = () => {
    if (!classeId) return;
    listerCours(classeId)
      .then(async (res) => {
        setCours(res.data);
        const entrees = await Promise.all(
          res.data.map(async (c) => [c.id, (await listerQuiz(c.id)).data] as const),
        );
        setQuizParCours(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(chargerCours, [classeId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!classeId) return;
    setErreur(null);
    setEnCours(true);
    try {
      await publierCours(classeId, titre, chapitre, format, contenuTexte || undefined);
      setTitre("");
      setChapitre("");
      setContenuTexte("");
      chargerCours();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de publier le cours."));
    } finally {
      setEnCours(false);
    }
  };

  const genererQuiz = async (coursId: string) => {
    setErreur(null);
    try {
      await creerQuiz(coursId, 80, 5);
      chargerCours();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de generer le quiz."));
    }
  };

  return (
    <div>
      <PageTitle>Mes cours</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <div className="mb-4 flex gap-3">
        <select
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={etablissementId}
          onChange={(e) => {
            setEtablissementId(e.target.value);
            setClasseId("");
          }}
        >
          <option value="">Etablissement...</option>
          {etablissementIds.map((id) => (
            <option key={id} value={id}>
              {etablissements.find((e) => e.id === id)?.nom ?? id}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={classeId}
          onChange={(e) => setClasseId(e.target.value)}
          disabled={!etablissementId}
        >
          <option value="">Classe...</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.niveau}
            </option>
          ))}
        </select>
      </div>

      {classeId && (
        <>
          <Card className="mb-4">
            <p className="mb-3 font-medium text-slate-900">Publier un nouveau cours</p>
            <form onSubmit={soumettre} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Titre">
                  <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} required />
                </Field>
                <Field label="Chapitre">
                  <TextInput value={chapitre} onChange={(e) => setChapitre(e.target.value)} required />
                </Field>
              </div>
              <Field label="Format">
                <select
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  value={format}
                  onChange={(e) => setFormat(e.target.value as FormatCours)}
                >
                  <option value="texte">Texte</option>
                  <option value="pdf">PDF</option>
                  <option value="audio">Audio</option>
                </select>
              </Field>
              <Field label="Contenu texte (requis pour generer un quiz)">
                <textarea
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  rows={3}
                  value={contenuTexte}
                  onChange={(e) => setContenuTexte(e.target.value)}
                />
              </Field>
              <PrimaryButton type="submit" disabled={enCours}>
                {enCours ? "Publication..." : "Publier"}
              </PrimaryButton>
            </form>
          </Card>

          <div className="space-y-3">
            {cours.map((c) => (
              <Card key={c.id}>
                <p className="font-medium text-slate-900">{c.titre}</p>
                <p className="mb-2 text-sm text-slate-500">{c.chapitre}</p>
                <div className="flex flex-wrap items-center gap-2">
                  {(quizParCours[c.id] ?? []).map((quiz, idx) => (
                    <span key={quiz.id} className="rounded-lg bg-indigo-50 px-3 py-1 text-sm text-indigo-700">
                      Quiz {idx + 1} ({quiz.questions.length}q)
                    </span>
                  ))}
                  <button
                    type="button"
                    onClick={() => genererQuiz(c.id)}
                    className="rounded-lg border border-indigo-300 px-3 py-1 text-sm text-indigo-700 hover:bg-indigo-50"
                  >
                    + Generer un quiz (IA)
                  </button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
