import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { maSoumission, obtenirDevoir, soumettreDevoir } from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import type { DevoirOut, SoumissionOut } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle, PrimaryButton } from "../../components/ui";

const LIBELLES_STATUT: Record<string, { label: string; tone: "gray" | "green" | "red" | "amber" }> = {
  en_correction: { label: "Correction en cours...", tone: "amber" },
  corrigee: { label: "Corrige", tone: "green" },
  echec_correction: { label: "En revision par l'enseignant", tone: "red" },
};

export function DevoirDetailPage() {
  const { devoirId } = useParams<{ devoirId: string }>();
  const [devoir, setDevoir] = useState<DevoirOut | null>(null);
  const [soumission, setSoumission] = useState<SoumissionOut | null | undefined>(undefined);
  const [reponses, setReponses] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const chargerSoumission = () => {
    if (!devoirId) return;
    maSoumission(devoirId)
      .then((res) => setSoumission(res.data))
      .catch(() => setSoumission(null));
  };

  useEffect(() => {
    if (!devoirId) return;
    obtenirDevoir(devoirId)
      .then((res) => setDevoir(res.data))
      .catch((err) => setErreur(messageErreur(err)));
    chargerSoumission();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devoirId]);

  useEffect(() => {
    if (soumission?.statut === "en_correction") {
      pollRef.current = setInterval(chargerSoumission, 3000);
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [soumission?.statut]);

  const soumettre = async () => {
    if (!devoir || !devoirId) return;
    if (devoir.questions.some((q) => !reponses[q.id]?.trim())) {
      setErreur("Veuillez repondre a toutes les questions.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      const { data } = await soumettreDevoir(
        devoirId,
        devoir.questions.map((q) => ({ question_id: q.id, texte_reponse: reponses[q.id] })),
      );
      setSoumission(data);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre le devoir."));
    } finally {
      setEnCours(false);
    }
  };

  if (!devoir) return <ErrorBanner>{erreur}</ErrorBanner>;

  const questionsTriees = [...devoir.questions].sort((a, b) => a.ordre - b.ordre);
  const dejaSoumis = soumission !== null && soumission !== undefined;

  return (
    <div className="mx-auto max-w-2xl">
      <PageTitle>{devoir.titre}</PageTitle>
      <p className="mb-4 text-sm text-slate-500">
        {devoir.matiere} — echeance {new Date(devoir.date_limite).toLocaleString("fr-FR")}
      </p>

      {dejaSoumis && soumission && (
        <Card className="mb-4">
          <div className="mb-3 flex items-center justify-between">
            <p className="font-medium text-slate-900">Ma soumission</p>
            <Badge tone={LIBELLES_STATUT[soumission.statut].tone}>
              {LIBELLES_STATUT[soumission.statut].label}
            </Badge>
          </div>
          {soumission.note !== null && (
            <p className="mb-2 text-lg font-semibold">Note : {soumission.note}</p>
          )}
          <div className="space-y-3">
            {questionsTriees.map((question, idx) => {
              const reponse = soumission.reponses.find((r) => r.question_id === question.id);
              return (
                <div key={question.id} className="border-t border-slate-100 pt-3">
                  <p className="text-sm font-medium text-slate-700">
                    {idx + 1}. {question.enonce}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">{reponse?.texte_reponse}</p>
                  {reponse?.points_obtenus !== null && reponse?.points_obtenus !== undefined && (
                    <p className="mt-1 text-sm text-indigo-600">
                      {reponse.points_obtenus} / {question.points_max} points
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {!dejaSoumis && (
        <Card>
          <div className="space-y-6">
            {questionsTriees.map((question, idx) => (
              <div key={question.id}>
                <p className="mb-2 font-medium text-slate-900">
                  {idx + 1}. {question.enonce} ({question.points_max} pts)
                </p>
                <textarea
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  rows={3}
                  value={reponses[question.id] ?? ""}
                  onChange={(e) => setReponses((prev) => ({ ...prev, [question.id]: e.target.value }))}
                />
              </div>
            ))}
          </div>
          <ErrorBanner>{erreur}</ErrorBanner>
          <PrimaryButton type="button" onClick={soumettre} disabled={enCours} className="mt-4 w-full">
            {enCours ? "Envoi..." : "Soumettre le devoir"}
          </PrimaryButton>
        </Card>
      )}
    </div>
  );
}
