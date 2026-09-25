import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { inscriptionsAValider, rejeterInscription, validerInscription } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import type { InscriptionAvecEleveOut } from "../../types/api";
import { Card, ErrorBanner, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";

export function InscriptionsAValiderPage() {
  const etablissement = useAdminEtab();
  const [inscriptions, setInscriptions] = useState<InscriptionAvecEleveOut[]>([]);
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = () => {
    inscriptionsAValider(etablissement.id)
      .then((res) => setInscriptions(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, [etablissement.id]);

  const valider = async (id: string) => {
    try {
      await validerInscription(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const rejeter = async (id: string) => {
    const motif = motifParId[id];
    if (!motif?.trim()) {
      setErreur("Veuillez indiquer un motif de rejet.");
      return;
    }
    try {
      await rejeterInscription(id, motif);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <PageTitle>Inscriptions a valider</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {inscriptions.length === 0 && <p className="text-slate-500">Aucune inscription en attente.</p>}
      <div className="space-y-3">
        {inscriptions.map((i) => (
          <Card key={i.id}>
            <div className="mb-2 flex items-center justify-between">
              <p className="font-medium text-slate-900">
                {i.eleve_prenom} {i.eleve_nom}
              </p>
              <PrimaryButton type="button" onClick={() => valider(i.id)}>
                Valider
              </PrimaryButton>
            </div>
            <div className="flex items-center gap-2">
              <TextInput
                placeholder="Motif de rejet"
                value={motifParId[i.id] ?? ""}
                onChange={(e) => setMotifParId((prev) => ({ ...prev, [i.id]: e.target.value }))}
              />
              <SecondaryButton type="button" onClick={() => rejeter(i.id)}>
                Rejeter
              </SecondaryButton>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
