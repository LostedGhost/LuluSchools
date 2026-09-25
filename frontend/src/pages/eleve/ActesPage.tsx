import { useEffect, useState, type FormEvent } from "react";
import {
  amorcerPaiement,
  listerTypesActes,
  mesDemandesActes,
  soumettreDemandeActe,
} from "../../api/actes";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { DemandeActeOut, StatutDemandeActe, TypeActeOut } from "../../types/api";
import { Badge, Card, ErrorBanner, Field, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";
import { KkiapayButton } from "../../components/KkiapayButton";

const LIBELLES_STATUT: Record<StatutDemandeActe, { label: string; tone: "gray" | "green" | "red" | "amber" | "blue" }> = {
  soumise: { label: "En attente de paiement", tone: "amber" },
  en_traitement: { label: "En traitement", tone: "blue" },
  acceptee: { label: "Acceptee", tone: "green" },
  rejetee: { label: "Rejetee", tone: "red" },
};

export function ActesPage() {
  const profil = useEleveProfil();
  const [types, setTypes] = useState<TypeActeOut[]>([]);
  const [demandes, setDemandes] = useState<DemandeActeOut[]>([]);
  const [mode, setMode] = useState<"catalogue" | "reclamation">("catalogue");
  const [typeActeId, setTypeActeId] = useState("");
  const [referenceEvaluation, setReferenceEvaluation] = useState("");
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    mesDemandesActes()
      .then((res) => setDemandes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(() => {
    if (profil.etablissement_id) {
      listerTypesActes(profil.etablissement_id)
        .then((res) => setTypes(res.data))
        .catch((err) => setErreur(messageErreur(err)));
    }
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profil.etablissement_id]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      if (mode === "catalogue") {
        await soumettreDemandeActe({ type_acte_id: typeActeId });
      } else {
        await soumettreDemandeActe({ est_reclamation: true, reference_evaluation: referenceEvaluation, motif });
      }
      setTypeActeId("");
      setReferenceEvaluation("");
      setMotif("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre la demande."));
    } finally {
      setEnCours(false);
    }
  };

  const payer = async (demandeId: string, transactionId: string) => {
    try {
      await amorcerPaiement(demandeId, transactionId);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const typeSelectionne = types.find((t) => t.id === typeActeId);

  return (
    <div>
      <PageTitle>Actes academiques</PageTitle>

      <Card className="mb-6">
        <div className="mb-4 flex gap-2">
          <SecondaryButton
            type="button"
            onClick={() => setMode("catalogue")}
            className={mode === "catalogue" ? "border-indigo-500 text-indigo-700" : ""}
          >
            Demande d'acte
          </SecondaryButton>
          <SecondaryButton
            type="button"
            onClick={() => setMode("reclamation")}
            className={mode === "reclamation" ? "border-indigo-500 text-indigo-700" : ""}
          >
            Reclamation de note
          </SecondaryButton>
        </div>

        <form onSubmit={soumettre} className="space-y-4">
          {mode === "catalogue" ? (
            <Field label="Type d'acte">
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={typeActeId}
                onChange={(e) => setTypeActeId(e.target.value)}
                required
              >
                <option value="">Choisir...</option>
                {types.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nom} — {t.prix > 0 ? `${t.prix.toLocaleString("fr-FR")} FCFA` : "Gratuit"}
                  </option>
                ))}
              </select>
              {typeSelectionne && (
                <p className="mt-1 text-xs text-slate-500">Pieces requises : {typeSelectionne.pieces_requises}</p>
              )}
            </Field>
          ) : (
            <>
              <Field label="Reference de l'evaluation contestee">
                <TextInput
                  value={referenceEvaluation}
                  onChange={(e) => setReferenceEvaluation(e.target.value)}
                  placeholder="ex: identifiant du devoir ou du bulletin"
                  required
                />
              </Field>
              <Field label="Motif">
                <TextInput value={motif} onChange={(e) => setMotif(e.target.value)} required />
              </Field>
            </>
          )}
          <ErrorBanner>{erreur}</ErrorBanner>
          <PrimaryButton type="submit" disabled={enCours}>
            {enCours ? "Envoi..." : "Soumettre"}
          </PrimaryButton>
        </form>
      </Card>

      <div className="space-y-3">
        {demandes.map((demande) => {
          const statut = LIBELLES_STATUT[demande.statut];
          const type = types.find((t) => t.id === demande.type_acte_id);
          return (
            <Card key={demande.id} className="flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">
                  {demande.est_reclamation ? "Reclamation de note" : type?.nom ?? "Acte academique"}
                </p>
                {demande.motif_rejet && <p className="text-sm text-red-600">Motif : {demande.motif_rejet}</p>}
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={statut.tone}>{statut.label}</Badge>
                {demande.statut === "soumise" && !demande.paiement_confirme && type && (
                  <KkiapayButton
                    montant={type.prix}
                    reference={demande.id}
                    onSucces={(transactionId) => payer(demande.id, transactionId)}
                  />
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
