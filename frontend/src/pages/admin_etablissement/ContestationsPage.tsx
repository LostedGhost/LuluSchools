import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { contestationsEnAttente, deciderContestation } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ContestationOut } from "../../types/api";
import { Card, ErrorBanner, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";

export function ContestationsPage() {
  const etablissement = useAdminEtab();
  const [contestations, setContestations] = useState<ContestationOut[]>([]);
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = () => {
    contestationsEnAttente(etablissement.id)
      .then((res) => setContestations(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, [etablissement.id]);

  const decider = async (id: string, decision: "acceptee" | "rejetee") => {
    if (decision === "rejetee" && !motifParId[id]?.trim()) {
      setErreur("Un motif est requis en cas de rejet.");
      return;
    }
    try {
      await deciderContestation(id, decision, motifParId[id]);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <PageTitle>Contestations en attente</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {contestations.length === 0 && <p className="text-slate-500">Aucune contestation en attente.</p>}
      <div className="space-y-3">
        {contestations.map((c) => (
          <Card key={c.id}>
            <p className="mb-2 text-slate-700">{c.motif}</p>
            <div className="flex items-center gap-2">
              <PrimaryButton type="button" onClick={() => decider(c.id, "acceptee")}>
                Accepter
              </PrimaryButton>
              <TextInput
                placeholder="Motif si rejet"
                value={motifParId[c.id] ?? ""}
                onChange={(e) => setMotifParId((prev) => ({ ...prev, [c.id]: e.target.value }))}
              />
              <SecondaryButton type="button" onClick={() => decider(c.id, "rejetee")}>
                Rejeter
              </SecondaryButton>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
