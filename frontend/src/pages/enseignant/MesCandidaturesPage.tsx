import { useEffect, useState } from "react";
import { contesterCandidature, mesCandidatures } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { CandidatureOut, StatutCandidature } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle, SecondaryButton, TextInput } from "../../components/ui";

const LIBELLES: Record<StatutCandidature, { label: string; tone: "gray" | "green" | "red" }> = {
  en_evaluation: { label: "En evaluation", tone: "gray" },
  retenue: { label: "Retenue", tone: "green" },
  rejetee: { label: "Rejetee", tone: "red" },
};

export function MesCandidaturesPage() {
  const [candidatures, setCandidatures] = useState<CandidatureOut[]>([]);
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = () => {
    mesCandidatures()
      .then((res) => setCandidatures(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, []);

  const contester = async (candidatureId: string) => {
    const motif = motifParId[candidatureId];
    if (!motif?.trim()) {
      setErreur("Veuillez indiquer un motif de contestation.");
      return;
    }
    try {
      await contesterCandidature(candidatureId, motif);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <PageTitle>Mes candidatures</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {candidatures.length === 0 && <p className="text-slate-500">Aucune candidature pour l'instant.</p>}
      <div className="space-y-3">
        {candidatures.map((c) => (
          <Card key={c.id}>
            <div className="mb-2 flex items-center justify-between">
              <Badge tone={LIBELLES[c.statut].tone}>{LIBELLES[c.statut].label}</Badge>
              {c.score !== null && <p className="text-sm text-slate-600">Score : {c.score.toFixed(1)}</p>}
            </div>
            <ul className="mb-2 text-sm text-slate-600">
              {c.documents.map((d) => (
                <li key={d.id}>
                  {d.type_document} : {d.statut} {d.note_ia !== null && `(${d.note_ia})`}
                </li>
              ))}
            </ul>
            {c.statut === "rejetee" && (
              <div className="flex items-center gap-2">
                <TextInput
                  placeholder="Motif de contestation"
                  value={motifParId[c.id] ?? ""}
                  onChange={(e) => setMotifParId((prev) => ({ ...prev, [c.id]: e.target.value }))}
                />
                <SecondaryButton type="button" onClick={() => contester(c.id)}>
                  Contester
                </SecondaryButton>
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
