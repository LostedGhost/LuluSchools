import { useEffect, useState } from "react";
import { contesterCandidature, mesCandidatures } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { CandidatureOut, StatutCandidature } from "../../types/api";
import { Badge, Card, ErrorBanner, SectionHead, Btn, TextInput, Field, EmptyState } from "../../components/ui";
import { ScoreBurst } from "../../components/gamification";

const LIBELLES: Record<StatutCandidature, { label: string; tone: "neutral" | "success" | "error" }> = {
  en_evaluation: { label: "En évaluation", tone: "neutral" },
  retenue: { label: "Retenue", tone: "success" },
  rejetee: { label: "Rejetée", tone: "error" },
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
    <div className="page-content">
      <SectionHead 
        title="Mes candidatures"
        desc="Suivez l'état d'avancement de vos candidatures aux différents postes." 
      />
      
      <ErrorBanner>{erreur}</ErrorBanner>
      
      {candidatures.length === 0 ? (
        <EmptyState 
          title="Aucune candidature" 
          desc="Vous n'avez pas encore postulé à des offres." 
        />
      ) : (
        <div className="grid-2">
          {candidatures.map((c, idx) => (
            <Card key={c.id} className={`anim-float-in delay-${(idx % 5) + 1} flex flex-col`}>
              <div className="mb-4 flex items-center justify-between border-b pb-4" style={{ borderColor: 'var(--border)' }}>
                <div className="flex items-center gap-3">
                  <Badge tone={LIBELLES[c.statut].tone}>{LIBELLES[c.statut].label}</Badge>
                </div>
                {c.score !== null && (
                  <ScoreBurst score={Number(c.score.toFixed(1))} label="Score IA" tone="magic" />
                )}
              </div>
              
              <div className="flex-1 mb-4">
                <h4 className="text-sm font-bold text-ink mb-2 text-eyebrow">Documents fournis</h4>
                <ul className="space-y-2 text-sm text-ink-soft">
                  {c.documents.map((d) => (
                    <li key={d.id} className="flex items-center justify-between bg-slate-50 p-2 rounded-md" style={{ backgroundColor: 'var(--surface-2)' }}>
                      <span>{d.type_document}</span>
                      <div className="flex items-center gap-2">
                        <Badge tone={d.statut === "note" ? "success" : d.statut === "echec_notation" ? "error" : "neutral"}>
                          {d.statut}
                        </Badge>
                        {d.note_ia !== null && <span className="text-xs font-mono text-magic">{d.note_ia}/10</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              {c.statut === "rejetee" && (
                <div className="mt-auto pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
                  <Field label="Contester la décision">
                    <div className="flex items-center gap-2">
                      <TextInput
                        placeholder="Motif de contestation..."
                        value={motifParId[c.id] ?? ""}
                        onChange={(e) => setMotifParId((prev) => ({ ...prev, [c.id]: e.target.value }))}
                      />
                      <Btn variant="action" size="sm" onClick={() => contester(c.id)}>
                        Contester
                      </Btn>
                    </div>
                  </Field>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
