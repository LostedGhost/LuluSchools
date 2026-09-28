import { useEleveProfil } from "../../eleve/EleveProfileContext";
import { BulletinDetail } from "../../components/bulletin/BulletinDetail";
import { EmptyState } from "../../components/ui";

export function BulletinPage() {
  const profil = useEleveProfil();
  return (
    <div className="page-content">
      <div style={{ marginBottom: "32px" }}>
        <p className="text-eyebrow">Année scolaire en cours</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Mon bulletin</h1>
      </div>
      {profil.classe_id ? (
        <BulletinDetail eleveUtilisateurId={profil.id} classeId={profil.classe_id} />
      ) : (
        <EmptyState title="Pas encore inscrit" desc="Votre bulletin apparaîtra ici une fois votre inscription validée." />
      )}
    </div>
  );
}
