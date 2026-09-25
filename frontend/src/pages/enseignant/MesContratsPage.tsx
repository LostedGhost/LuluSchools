import { useEffect, useState } from "react";
import { mesContrats, signerContrat } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ContratOut } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle } from "../../components/ui";
import { SignatureCanvas } from "../../components/SignatureCanvas";

export function MesContratsPage() {
  const [contrats, setContrats] = useState<ContratOut[]>([]);
  const [contratASigner, setContratASigner] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    mesContrats()
      .then((res) => setContrats(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, []);

  const signer = async (contratId: string, blob: Blob) => {
    setEnCours(true);
    setErreur(null);
    try {
      await signerContrat(contratId, blob);
      setContratASigner(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div>
      <PageTitle>Mes contrats</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {contrats.length === 0 && <p className="text-slate-500">Aucun contrat pour l'instant.</p>}
      <div className="space-y-3">
        {contrats.map((c) => (
          <Card key={c.id}>
            <div className="mb-2 flex items-center justify-between">
              <p className="font-medium text-slate-900">Contrat jusqu'au {c.date_fin}</p>
              <Badge tone={c.statut === "signe" ? "green" : "amber"}>
                {c.statut === "signe" ? "Signe" : "En attente de signature"}
              </Badge>
            </div>
            <p className="mb-2 text-sm text-slate-600">{c.syllabus}</p>
            {c.statut === "en_attente_signature" &&
              (contratASigner === c.id ? (
                <SignatureCanvas enCours={enCours} onSigner={(blob) => signer(c.id, blob)} />
              ) : (
                <button
                  type="button"
                  onClick={() => setContratASigner(c.id)}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Signer ce contrat
                </button>
              ))}
          </Card>
        ))}
      </div>
    </div>
  );
}
