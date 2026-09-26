import { useEffect, useState, type FormEvent } from "react";
import { mesClassesAffectees } from "../../api/etablissements";
import {
  corrigerSoumission,
  creerDevoir,
  listerDevoirs,
  questionsAvecBareme,
  soumissionsARevoir,
  type QuestionDevoirPayload,
} from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import type { BaremeDevoir, ClasseOut, DevoirOut, SoumissionOut } from "../../types/api";
import { Card, ErrorBanner, Field, SectionHead, Btn, TextInput, Select, EmptyState } from "../../components/ui";
import { AIBadge } from "../../components/gamification";
import { estRempli, erreurDateFuture } from "../../utils/validation";

export function MesDevoirsPage() {
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [classeId, setClasseId] = useState("");
  const [devoirs, setDevoirs] = useState<DevoirOut[]>([]);
  const [aRevoirParDevoir, setARevoirParDevoir] = useState<Record<string, SoumissionOut[]>>({});
  const [baremeParDevoir, setBaremeParDevoir] = useState<Record<string, Record<string, string>>>({});

  const [titre, setTitre] = useState("");
  const [matiere, setMatiere] = useState("");
  const [dateLimite, setDateLimite] = useState("");
  const [bareme, setBareme] = useState<BaremeDevoir>("flexible");
  const [questions, setQuestions] = useState<QuestionDevoirPayload[]>([
    { enonce: "", bareme_reponse: "", points_max: 10 },
  ]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [pointsParReponse, setPointsParReponse] = useState<Record<string, number>>({});
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    mesClassesAffectees()
      .then((res) => setClasses(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);

  const chargerDevoirs = () => {
    if (!classeId) return;
    listerDevoirs(classeId)
      .then(async (res) => {
        setDevoirs(res.data);
        const entrees = await Promise.all(
          res.data.map(async (d) => [d.id, (await soumissionsARevoir(d.id)).data] as const),
        );
        const devoirsARevoir = entrees.filter(([, soumissions]) => soumissions.length > 0);
        setARevoirParDevoir(Object.fromEntries(entrees));

        // Bareme charge seulement pour les devoirs ayant reellement une revision en
        // attente (endpoint reserve au proprietaire, evite des appels inutiles).
        const baremeEntrees = await Promise.all(
          devoirsARevoir.map(async ([devoirId]) => {
            const bareme = await questionsAvecBareme(devoirId);
            return [devoirId, Object.fromEntries(bareme.data.map((q) => [q.id, q.bareme_reponse]))] as const;
          }),
        );
        setBaremeParDevoir(Object.fromEntries(baremeEntrees));
      })
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(chargerDevoirs, [classeId]);

  const ajouterQuestion = () => {
    setQuestions((prev) => [...prev, { enonce: "", bareme_reponse: "", points_max: 10 }]);
  };

  const majQuestion = (index: number, champ: keyof QuestionDevoirPayload, valeur: string) => {
    setQuestions((prev) =>
      prev.map((q, i) => (i === index ? { ...q, [champ]: champ === "points_max" ? Number(valeur) : valeur } : q)),
    );
  };

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!classeId) return;
    setErreur(null);

    if (!estRempli(titre)) {
      setErreur("Veuillez saisir un titre pour le devoir.");
      return;
    }
    if (!estRempli(matiere)) {
      setErreur("Veuillez saisir la matière.");
      return;
    }
    const erreurDate = erreurDateFuture(dateLimite);
    if (erreurDate) {
      setErreur(`Date limite invalide : ${erreurDate}`);
      return;
    }
    for (const [i, q] of questions.entries()) {
      if (!estRempli(q.enonce) || !estRempli(q.bareme_reponse)) {
        setErreur(`Question ${i + 1} : l'énoncé et le barème sont requis.`);
        return;
      }
      if (!Number.isFinite(q.points_max) || q.points_max <= 0) {
        setErreur(`Question ${i + 1} : les points max doivent être supérieurs à 0.`);
        return;
      }
    }

    setEnCours(true);
    try {
      await creerDevoir(classeId, titre, matiere, new Date(dateLimite).toISOString(), bareme, questions);
      setTitre("");
      setMatiere("");
      setDateLimite("");
      setQuestions([{ enonce: "", bareme_reponse: "", points_max: 10 }]);
      setIsCreating(false);
      chargerDevoirs();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le devoir."));
    } finally {
      setEnCours(false);
    }
  };

  const corrigerManuel = async (soumission: SoumissionOut, devoir: DevoirOut) => {
    for (const q of devoir.questions) {
      const points = pointsParReponse[`${soumission.id}:${q.id}`] ?? 0;
      if (!Number.isFinite(points) || points < 0 || points > q.points_max) {
        setErreur(`La note doit être comprise entre 0 et ${q.points_max} pour chaque question.`);
        return;
      }
    }
    setErreur(null);
    const reponses = devoir.questions.map((q) => ({
      question_id: q.id,
      points_obtenus: pointsParReponse[`${soumission.id}:${q.id}`] ?? 0,
    }));
    try {
      await corrigerSoumission(soumission.id, reponses);
      chargerDevoirs();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div className="page-content">
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
        <SectionHead 
          title="Mes devoirs"
          desc="Gérez vos devoirs et supervisez les corrections IA." 
        />
        {classeId && (
          <Btn variant="primary" onClick={() => setIsCreating(!isCreating)}>
            {isCreating ? "Annuler la création" : "+ Créer un devoir"}
          </Btn>
        )}
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-8 card-soft">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <Field label="Classe">
              <Select value={classeId} onChange={(e) => setClasseId(e.target.value)}>
                <option value="">Sélectionner...</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.niveau}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
        </div>
      </Card>

      {classes.length === 0 && (
        <EmptyState title="Aucune classe affectée" desc="Aucune classe ne vous a encore été affectée par l'administration de votre établissement." />
      )}

      {classeId && isCreating && (
        <Card className="mb-8 anim-slide-up border-2" style={{ borderColor: 'var(--primary)' }}>
          <h3 className="text-title text-ink mb-4">Créer un nouveau devoir</h3>
          <form onSubmit={soumettre} className="space-y-6">
            <div className="grid-2">
              <Field label="Titre">
                <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} required />
              </Field>
              <Field label="Matière">
                <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} required />
              </Field>
            </div>
            <div className="grid-2">
              <Field label="Date limite">
                <TextInput
                  type="datetime-local"
                  value={dateLimite}
                  onChange={(e) => setDateLimite(e.target.value)}
                  required
                />
              </Field>
              <Field label="Barème">
                <Select
                  value={bareme}
                  onChange={(e) => setBareme(e.target.value as BaremeDevoir)}
                >
                  <option value="flexible">Flexible (crédit partiel)</option>
                  <option value="rigide">Rigide (tout ou rien)</option>
                </Select>
              </Field>
            </div>

            <div className="space-y-4">
              <h4 className="text-sm font-bold text-ink text-eyebrow">Questions</h4>
              {questions.map((q, i) => (
                <div key={i} className="space-y-3 rounded-lg p-4 bg-slate-50 border" style={{ borderColor: 'var(--border)', backgroundColor: 'var(--surface-2)' }}>
                  <Field label={`Question ${i + 1}`}>
                    <TextInput value={q.enonce} onChange={(e) => majQuestion(i, "enonce", e.target.value)} required />
                  </Field>
                  <Field label="Barème de correction (instruction pour l'IA)">
                    <TextInput
                      value={q.bareme_reponse}
                      onChange={(e) => majQuestion(i, "bareme_reponse", e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Points max">
                    <TextInput
                      type="number"
                      value={q.points_max.toString()}
                      onChange={(e) => majQuestion(i, "points_max", e.target.value)}
                      required
                    />
                  </Field>
                </div>
              ))}
              <Btn type="button" variant="ghost" onClick={ajouterQuestion}>
                + Ajouter une question
              </Btn>
            </div>
            <div className="flex justify-end border-t pt-4" style={{ borderColor: 'var(--border)' }}>
              <Btn type="submit" variant="primary" disabled={enCours} loading={enCours}>
                {enCours ? "Création..." : "Créer le devoir"}
              </Btn>
            </div>
          </form>
        </Card>
      )}

      {classeId && !isCreating && devoirs.length === 0 && (
        <EmptyState title="Aucun devoir" desc="Créez votre premier devoir pour cette classe." />
      )}

      {classeId && devoirs.length > 0 && (
        <div className="space-y-6">
          {devoirs.map((devoir, idx) => (
            <Card key={devoir.id} className={`anim-float-in delay-${(idx % 5) + 1}`}>
              <div className="flex justify-between items-start mb-4 border-b pb-4" style={{ borderColor: 'var(--border)' }}>
                <div>
                  <h3 className="text-title text-ink mb-1">{devoir.titre}</h3>
                  <p className="text-sm text-ink-soft">{devoir.matiere}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <AIBadge status={(aRevoirParDevoir[devoir.id] ?? []).length > 0 ? "error" : "done"} />
                </div>
              </div>
              
              {(aRevoirParDevoir[devoir.id] ?? []).length > 0 ? (
                <div className="mt-4 space-y-4">
                  <h4 className="text-sm font-medium" style={{ color: 'var(--action-deep)' }}>
                    Soumissions nécessitant une correction manuelle :
                  </h4>
                  {aRevoirParDevoir[devoir.id].map((s) => (
                    <div key={s.id} className="space-y-4 rounded-lg p-4 border" style={{ borderColor: 'var(--action-tint)', backgroundColor: 'var(--surface)' }}>
                      {devoir.questions.map((q) => {
                        const reponse = s.reponses.find((r) => r.question_id === q.id);
                        const cle = `${s.id}:${q.id}`;
                        return (
                          <div key={q.id} className="text-sm pb-3 border-b border-dashed last:border-0" style={{ borderColor: 'var(--border)' }}>
                            <p className="font-medium text-ink mb-2">{q.enonce}</p>
                            {baremeParDevoir[devoir.id]?.[q.id] && (
                              <p className="text-xs mb-2" style={{ color: 'var(--reward-deep)' }}>
                                <strong>Barème attendu :</strong> {baremeParDevoir[devoir.id][q.id]}
                              </p>
                            )}
                            <div className="bg-slate-50 p-3 rounded mb-3 text-ink-soft italic">
                              {reponse?.texte_reponse || "Aucune réponse fournie"}
                            </div>
                            <div className="flex items-center gap-3">
                              <Field label="Note">
                                <div className="flex items-center gap-2">
                                  <TextInput
                                    type="number"
                                    min={0}
                                    max={q.points_max}
                                    value={pointsParReponse[cle] ?? ""}
                                    onChange={(e) =>
                                      setPointsParReponse((prev) => ({ ...prev, [cle]: Number(e.target.value) }))
                                    }
                                    className="w-24"
                                  />
                                  <span className="text-ink-soft font-mono">/ {q.points_max} pts</span>
                                </div>
                              </Field>
                            </div>
                          </div>
                        );
                      })}
                      <div className="flex justify-end pt-2">
                        <Btn type="button" variant="action" onClick={() => corrigerManuel(s, devoir)}>
                          Valider la correction
                        </Btn>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-ink-soft">Toutes les soumissions ont été corrigées avec succès par l'IA.</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
