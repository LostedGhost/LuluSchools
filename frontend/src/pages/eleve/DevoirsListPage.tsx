import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listerDevoirs, maSoumission } from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { DevoirOut, SoumissionOut } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle } from "../../components/ui";

const LIBELLES_STATUT: Record<string, { label: string; tone: "gray" | "green" | "red" | "amber" }> = {
  en_correction: { label: "Correction en cours", tone: "amber" },
  corrigee: { label: "Corrige", tone: "green" },
  echec_correction: { label: "En revision", tone: "red" },
};

export function DevoirsListPage() {
  const profil = useEleveProfil();
  const [devoirs, setDevoirs] = useState<DevoirOut[]>([]);
  const [soumissions, setSoumissions] = useState<Record<string, SoumissionOut | null>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (!profil.classe_id) return;
    listerDevoirs(profil.classe_id)
      .then(async (res) => {
        setDevoirs(res.data);
        const entrees = await Promise.all(
          res.data.map(async (d) => {
            try {
              return [d.id, (await maSoumission(d.id)).data] as const;
            } catch {
              return [d.id, null] as const;
            }
          }),
        );
        setSoumissions(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [profil.classe_id]);

  return (
    <div>
      <PageTitle>Devoirs de ma classe</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {devoirs.length === 0 && <p className="text-slate-500">Aucun devoir pour l'instant.</p>}
      <div className="space-y-3">
        {devoirs.map((devoir) => {
          const soumission = soumissions[devoir.id];
          const statut = soumission ? LIBELLES_STATUT[soumission.statut] : null;
          return (
            <Link key={devoir.id} to={`/eleve/devoirs/${devoir.id}`}>
              <Card className="flex items-center justify-between hover:border-indigo-300 hover:shadow-md">
                <div>
                  <p className="font-medium text-slate-900">{devoir.titre}</p>
                  <p className="text-sm text-slate-500">
                    {devoir.matiere} — echeance {new Date(devoir.date_limite).toLocaleDateString("fr-FR")}
                  </p>
                </div>
                <div className="text-right">
                  {statut ? (
                    <Badge tone={statut.tone}>{statut.label}</Badge>
                  ) : (
                    <Badge tone="gray">A soumettre</Badge>
                  )}
                  {soumission?.note !== null && soumission?.note !== undefined && (
                    <p className="mt-1 text-sm text-slate-500">Note : {soumission.note}</p>
                  )}
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
