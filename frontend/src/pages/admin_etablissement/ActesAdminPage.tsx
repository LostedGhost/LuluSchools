import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  creerTypeActe,
  demandesActesEtablissement,
  listerTypesActes,
  traiterDemandeActe,
} from "../../api/actes";
import { messageErreur } from "../../api/client";
import type { DemandeActeOut, TypeActeOut } from "../../types/api";
import { Badge, Card, ErrorBanner, Field, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";

export function ActesAdminPage() {
  const etablissement = useAdminEtab();
  const [types, setTypes] = useState<TypeActeOut[]>([]);
  const [demandes, setDemandes] = useState<DemandeActeOut[]>([]);
  const [nom, setNom] = useState("");
  const [prix, setPrix] = useState(0);
  const [piecesRequises, setPiecesRequises] = useState("");
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    listerTypesActes(etablissement.id)
      .then((res) => setTypes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
    demandesActesEtablissement(etablissement.id)
      .then((res) => setDemandes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, [etablissement.id]);

  const soumettreType = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await creerTypeActe(etablissement.id, { nom, prix, pieces_requises: piecesRequises });
      setNom("");
      setPrix(0);
      setPiecesRequises("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer le type d'acte."));
    } finally {
      setEnCours(false);
    }
  };

  const traiter = async (id: string, decision: "acceptee" | "rejetee") => {
    if (decision === "rejetee" && !motifParId[id]?.trim()) {
      setErreur("Un motif est requis en cas de rejet.");
      return;
    }
    try {
      await traiterDemandeActe(id, decision, motifParId[id]);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  return (
    <div>
      <PageTitle>Actes academiques</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-4">
        <p className="mb-3 font-medium text-slate-900">Catalogue des actes</p>
        <form onSubmit={soumettreType} className="mb-4 flex flex-wrap items-end gap-3">
          <Field label="Nom">
            <TextInput value={nom} onChange={(e) => setNom(e.target.value)} required />
          </Field>
          <Field label="Prix (FCFA, 0 = gratuit)">
            <TextInput type="number" value={prix} onChange={(e) => setPrix(Number(e.target.value))} className="w-32" />
          </Field>
          <Field label="Pieces requises">
            <TextInput value={piecesRequises} onChange={(e) => setPiecesRequises(e.target.value)} required />
          </Field>
          <PrimaryButton type="submit" disabled={enCours}>
            {enCours ? "Creation..." : "Ajouter"}
          </PrimaryButton>
        </form>
        <div className="space-y-2">
          {types.map((t) => (
            <div key={t.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm">
              <span>{t.nom}</span>
              <span>{t.prix > 0 ? `${t.prix.toLocaleString("fr-FR")} FCFA` : "Gratuit"}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <p className="mb-3 font-medium text-slate-900">Demandes a traiter</p>
        {demandes.filter((d) => d.statut === "en_traitement").length === 0 && (
          <p className="text-slate-500">Aucune demande en attente de traitement.</p>
        )}
        <div className="space-y-3">
          {demandes
            .filter((d) => d.statut === "en_traitement")
            .map((d) => (
              <div key={d.id} className="rounded-lg border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span>{d.est_reclamation ? "Reclamation de note" : "Demande d'acte"}</span>
                  <Badge tone="blue">{d.statut}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <PrimaryButton type="button" onClick={() => traiter(d.id, "acceptee")}>
                    Accepter
                  </PrimaryButton>
                  <TextInput
                    placeholder="Motif si rejet"
                    value={motifParId[d.id] ?? ""}
                    onChange={(e) => setMotifParId((prev) => ({ ...prev, [d.id]: e.target.value }))}
                  />
                  <SecondaryButton type="button" onClick={() => traiter(d.id, "rejetee")}>
                    Rejeter
                  </SecondaryButton>
                </div>
              </div>
            ))}
        </div>
      </Card>
    </div>
  );
}
