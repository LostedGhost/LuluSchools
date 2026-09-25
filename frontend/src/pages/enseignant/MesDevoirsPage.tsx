import { useEffect, useState, type FormEvent } from "react";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import {
  corrigerSoumission,
  creerDevoir,
  listerDevoirs,
  soumissionsARevoir,
  type QuestionDevoirPayload,
} from "../../api/evaluations";
import { mesContrats } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { BaremeDevoir, ClasseOut, DevoirOut, EtablissementOut, SoumissionOut } from "../../types/api";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";

export function MesDevoirsPage() {
  const [etablissementIds, setEtablissementIds] = useState<string[]>([]);
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [classeId, setClasseId] = useState("");
  const [devoirs, setDevoirs] = useState<DevoirOut[]>([]);
  const [aRevoirParDevoir, setARevoirParDevoir] = useState<Record<string, SoumissionOut[]>>({});

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

  const chargerDevoirs = () => {
    if (!classeId) return;
    listerDevoirs(classeId)
      .then(async (res) => {
        setDevoirs(res.data);
        const entrees = await Promise.all(
          res.data.map(async (d) => [d.id, (await soumissionsARevoir(d.id)).data] as const),
        );
        setARevoirParDevoir(Object.fromEntries(entrees));
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
    setEnCours(true);
    try {
      await creerDevoir(classeId, titre, matiere, new Date(dateLimite).toISOString(), bareme, questions);
      setTitre("");
      setMatiere("");
      setDateLimite("");
      setQuestions([{ enonce: "", bareme_reponse: "", points_max: 10 }]);
      chargerDevoirs();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer le devoir."));
    } finally {
      setEnCours(false);
    }
  };

  const corrigerManuel = async (soumission: SoumissionOut, devoir: DevoirOut) => {
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
    <div>
      <PageTitle>Mes devoirs</PageTitle>
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
            <p className="mb-3 font-medium text-slate-900">Creer un nouveau devoir</p>
            <form onSubmit={soumettre} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <Field label="Titre">
                  <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} required />
                </Field>
                <Field label="Matiere">
                  <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} required />
                </Field>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Date limite">
                  <TextInput
                    type="datetime-local"
                    value={dateLimite}
                    onChange={(e) => setDateLimite(e.target.value)}
                    required
                  />
                </Field>
                <Field label="Bareme">
                  <select
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    value={bareme}
                    onChange={(e) => setBareme(e.target.value as BaremeDevoir)}
                  >
                    <option value="flexible">Flexible (credit partiel)</option>
                    <option value="rigide">Rigide (tout ou rien)</option>
                  </select>
                </Field>
              </div>

              {questions.map((q, i) => (
                <div key={i} className="space-y-2 rounded-lg border border-slate-200 p-3">
                  <Field label={`Question ${i + 1}`}>
                    <TextInput value={q.enonce} onChange={(e) => majQuestion(i, "enonce", e.target.value)} required />
                  </Field>
                  <Field label="Bareme de correction (instruction pour l'IA)">
                    <TextInput
                      value={q.bareme_reponse}
                      onChange={(e) => majQuestion(i, "bareme_reponse", e.target.value)}
                      required
                    />
                  </Field>
                  <Field label="Points max">
                    <TextInput
                      type="number"
                      value={q.points_max}
                      onChange={(e) => majQuestion(i, "points_max", e.target.value)}
                      required
                    />
                  </Field>
                </div>
              ))}
              <SecondaryButton type="button" onClick={ajouterQuestion}>
                + Ajouter une question
              </SecondaryButton>
              <div>
                <PrimaryButton type="submit" disabled={enCours}>
                  {enCours ? "Creation..." : "Creer le devoir"}
                </PrimaryButton>
              </div>
            </form>
          </Card>

          <div className="space-y-3">
            {devoirs.map((devoir) => (
              <Card key={devoir.id}>
                <p className="font-medium text-slate-900">{devoir.titre}</p>
                <p className="mb-2 text-sm text-slate-500">{devoir.matiere}</p>
                {(aRevoirParDevoir[devoir.id] ?? []).length > 0 && (
                  <div className="mt-2 space-y-3">
                    <p className="text-sm font-medium text-red-600">Soumissions en echec de correction IA :</p>
                    {aRevoirParDevoir[devoir.id].map((s) => (
                      <div key={s.id} className="space-y-2 rounded-lg bg-red-50 p-3">
                        {devoir.questions.map((q) => {
                          const reponse = s.reponses.find((r) => r.question_id === q.id);
                          const cle = `${s.id}:${q.id}`;
                          return (
                            <div key={q.id} className="text-sm">
                              <p className="text-slate-700">{q.enonce}</p>
                              <p className="mb-1 text-slate-600">{reponse?.texte_reponse}</p>
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
                                <span className="text-slate-500">/ {q.points_max} points</span>
                              </div>
                            </div>
                          );
                        })}
                        <SecondaryButton type="button" onClick={() => corrigerManuel(s, devoir)}>
                          Valider la correction
                        </SecondaryButton>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
