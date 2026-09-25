import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listerEtablissements } from "../../api/etablissements";
import { listerPostes } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, PosteOut } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle } from "../../components/ui";

export function PostesListPage() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [postes, setPostes] = useState<PosteOut[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);

  useEffect(() => {
    if (!etablissementId) {
      setPostes([]);
      return;
    }
    listerPostes(etablissementId)
      .then((res) => setPostes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  return (
    <div>
      <PageTitle>Postes ouverts</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <select
        className="mb-4 w-full max-w-md rounded-lg border border-slate-300 px-3 py-2 text-sm"
        value={etablissementId}
        onChange={(e) => setEtablissementId(e.target.value)}
      >
        <option value="">Choisir un etablissement...</option>
        {etablissements.map((etab) => (
          <option key={etab.id} value={etab.id}>
            {etab.nom} ({etab.code_etablissement})
          </option>
        ))}
      </select>

      <div className="space-y-3">
        {postes.map((poste) => (
          <Card key={poste.id} className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">{poste.titre}</p>
              <p className="text-sm text-slate-500">
                Documents requis : {poste.criteres.map((c) => c.type_document).join(", ")}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge tone={poste.statut === "ouvert" ? "green" : "gray"}>{poste.statut}</Badge>
              {poste.statut === "ouvert" && (
                <Link
                  to={`/enseignant/postes/${poste.id}/postuler`}
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Postuler
                </Link>
              )}
            </div>
          </Card>
        ))}
        {etablissementId && postes.length === 0 && (
          <p className="text-slate-500">Aucun poste pour cet etablissement.</p>
        )}
      </div>
    </div>
  );
}
