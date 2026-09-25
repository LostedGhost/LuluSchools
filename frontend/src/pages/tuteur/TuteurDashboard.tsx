import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { donnerConsentementParental, mesInscriptions } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import type { InscriptionAvecEleveOut, StatutInscription } from "../../types/api";
import { Badge, Card, ErrorBanner, PageTitle, PrimaryButton, SecondaryButton } from "../../components/ui";

const LIBELLES_STATUT: Record<StatutInscription, { label: string; tone: "gray" | "green" | "red" | "amber" }> = {
  en_attente_consentement_parental: { label: "Consentement parental requis", tone: "amber" },
  soumise: { label: "En attente de validation", tone: "gray" },
  validee: { label: "Validee", tone: "green" },
  rejetee: { label: "Rejetee", tone: "red" },
};

export function TuteurDashboard() {
  const [inscriptions, setInscriptions] = useState<InscriptionAvecEleveOut[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCoursId, setEnCoursId] = useState<string | null>(null);

  const charger = () => {
    mesInscriptions()
      .then((res) => setInscriptions(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, []);

  const donnerConsentement = async (id: string) => {
    setEnCoursId(id);
    setErreur(null);
    try {
      await donnerConsentementParental(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCoursId(null);
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <PageTitle>Mes enfants</PageTitle>
        <Link to="/tuteur/nouvelle-inscription">
          <PrimaryButton type="button">+ Nouvelle inscription</PrimaryButton>
        </Link>
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>

      {inscriptions === null && <p className="text-slate-500">Chargement...</p>}
      {inscriptions?.length === 0 && (
        <Card>
          <p className="text-slate-600">
            Aucune inscription pour l'instant. Commencez par inscrire un enfant dans un etablissement.
          </p>
        </Card>
      )}

      <div className="space-y-3">
        {inscriptions?.map((inscription) => {
          const statut = LIBELLES_STATUT[inscription.statut];
          return (
            <Card key={inscription.id} className="flex items-center justify-between">
              <div>
                <p className="font-medium text-slate-900">
                  {inscription.eleve_prenom} {inscription.eleve_nom}
                </p>
                {inscription.eleve_matricule && (
                  <p className="text-sm text-slate-500">Matricule : {inscription.eleve_matricule}</p>
                )}
                {inscription.motif_rejet && (
                  <p className="mt-1 text-sm text-red-600">Motif du rejet : {inscription.motif_rejet}</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={statut.tone}>{statut.label}</Badge>
                {inscription.statut === "en_attente_consentement_parental" && (
                  <SecondaryButton
                    type="button"
                    disabled={enCoursId === inscription.id}
                    onClick={() => donnerConsentement(inscription.id)}
                  >
                    Donner mon consentement
                  </SecondaryButton>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
