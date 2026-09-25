import { useEffect, useState } from "react";
import { obtenirBulletin } from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { BulletinOut } from "../../types/api";
import { Card, ErrorBanner, PageTitle } from "../../components/ui";

const PERIODES = ["trimestre1", "trimestre2", "trimestre3"];

export function BulletinPage() {
  const profil = useEleveProfil();
  const [periode, setPeriode] = useState(PERIODES[0]);
  const [bulletin, setBulletin] = useState<BulletinOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);

  useEffect(() => {
    if (!profil.classe_id) return;
    setChargement(true);
    setErreur(null);
    setBulletin(null);
    obtenirBulletin(profil.id, profil.classe_id, periode)
      .then((res) => setBulletin(res.data))
      .catch((err) => setErreur(messageErreur(err, "Aucune moyenne disponible pour cette periode.")))
      .finally(() => setChargement(false));
  }, [profil.classe_id, profil.id, periode]);

  return (
    <div className="mx-auto max-w-lg">
      <PageTitle>Mon bulletin</PageTitle>

      <div className="mb-4 flex gap-2">
        {PERIODES.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPeriode(p)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              periode === p ? "bg-indigo-600 text-white" : "bg-white text-slate-600 border border-slate-300"
            }`}
          >
            {p.replace("trimestre", "Trimestre ")}
          </button>
        ))}
      </div>

      {chargement && <p className="text-slate-500">Chargement...</p>}
      {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

      {bulletin && (
        <Card>
          <p className="text-sm text-slate-500">Moyenne generale</p>
          <p className="mb-4 text-3xl font-semibold text-indigo-700">
            {bulletin.moyenne_generale.toFixed(2)} / 100
          </p>
          {bulletin.valide_par_conseil ? (
            <p className="text-sm text-slate-700">
              Decision du conseil : <strong>{bulletin.decision_passage}</strong>
            </p>
          ) : (
            <p className="text-sm text-slate-500">En attente de la decision du conseil de classe.</p>
          )}
        </Card>
      )}
    </div>
  );
}
