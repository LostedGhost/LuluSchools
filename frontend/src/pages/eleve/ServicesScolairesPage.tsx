import { useEleveProfil } from "../../eleve/EleveProfileContext";
import { ServicesScolairesPanel } from "../../components/services_scolaires/ServicesScolairesPanel";
import { SectionHead, ErrorBanner } from "../../components/ui";

export function ServicesScolairesPage() {
  const profil = useEleveProfil();

  return (
    <div className="page-content">
      <SectionHead eyebrow="Ma scolarité" title="Transport et cantine" />
      {!profil.etablissement_id ? (
        <ErrorBanner>Votre établissement n'a pas pu être déterminé.</ErrorBanner>
      ) : (
        <ServicesScolairesPanel etablissementId={profil.etablissement_id} />
      )}
    </div>
  );
}
