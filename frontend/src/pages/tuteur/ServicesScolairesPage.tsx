import { useEffect, useState } from "react";
import { mesInscriptions } from "../../api/inscriptions";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { InscriptionAvecEleveOut } from "../../types/api";
import { ServicesScolairesPanel } from "../../components/services_scolaires/ServicesScolairesPanel";
import { EmptyState, ErrorBanner, Field, Select, SectionHead, SkeletonCard } from "../../components/ui";
import { Users } from "lucide-react";

export function ServicesScolairesPage() {
  const [enfants, setEnfants] = useState<InscriptionAvecEleveOut[]>([]);
  const [classeVersEtablissement, setClasseVersEtablissement] = useState<Record<string, string>>({});
  const [inscriptionId, setInscriptionId] = useState("");
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([mesInscriptions(), listerEtablissements()])
      .then(async ([resInscriptions, resEtablissements]) => {
        const validees = resInscriptions.data.filter((i) => i.statut === "validee" && i.eleve_utilisateur_id);
        setEnfants(validees);
        if (validees.length > 0) setInscriptionId((prev) => prev || validees[0].id);

        const classesParEtab = await Promise.all(
          resEtablissements.data.map((e) => listerClasses(e.id).then((r) => r.data.map((c) => [c.id, e.id] as const))),
        );
        setClasseVersEtablissement(Object.fromEntries(classesParEtab.flat()));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, []);

  const enfantSelectionne = enfants.find((i) => i.id === inscriptionId);
  const etablissementId = enfantSelectionne ? classeVersEtablissement[enfantSelectionne.classe_id] : undefined;

  return (
    <div className="page-content">
      <SectionHead eyebrow="Mes enfants" title="Transport et cantine" />
      <ErrorBanner>{erreur}</ErrorBanner>

      {chargement ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState
          icon={<Users size={24} />}
          title="Aucun enfant inscrit"
          desc="Ces services sont disponibles une fois l'inscription de votre enfant validée."
        />
      ) : (
        <>
          <div className="card card-soft" style={{ marginBottom: "24px", maxWidth: "360px" }}>
            <Field label="Enfant">
              <Select value={inscriptionId} onChange={(e: any) => setInscriptionId(e.target.value)}>
                {enfants.map((i) => (
                  <option key={i.id} value={i.id}>{i.eleve_prenom} {i.eleve_nom}</option>
                ))}
              </Select>
            </Field>
          </div>

          {enfantSelectionne && etablissementId && (
            <ServicesScolairesPanel etablissementId={etablissementId} eleveUtilisateurId={enfantSelectionne.eleve_utilisateur_id!} />
          )}
        </>
      )}
    </div>
  );
}
