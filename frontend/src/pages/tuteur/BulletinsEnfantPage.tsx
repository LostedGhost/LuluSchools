import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Award } from "lucide-react";
import { messageErreur } from "../../api/client";
import { mesInscriptions } from "../../api/inscriptions";
import { BulletinDetail } from "../../components/bulletin/BulletinDetail";
import { Btn, EmptyState, ErrorBanner, PageTitle, SkeletonCard } from "../../components/ui";
import type { InscriptionAvecEleveOut } from "../../types/api";

/** Bulletins des enfants (parent) : même détail que l'écran de l'élève — moyenne générale,
 * décision du conseil, notes de chaque évaluation par matière — et le bulletin PDF. */
export function BulletinsEnfantPage() {
  const [parametres, setParametres] = useSearchParams();
  const [enfants, setEnfants] = useState<InscriptionAvecEleveOut[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    mesInscriptions()
      .then((res) => setEnfants(res.data.filter((i) => i.statut === "validee" && i.eleve_utilisateur_id)))
      .catch((err) => {
        setErreur(messageErreur(err));
        setEnfants([]);
      });
  }, []);

  const choisi = enfants?.find((e) => e.eleve_utilisateur_id === parametres.get("enfant")) ?? enfants?.[0];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Mes enfants">Bulletins</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {enfants === null ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Award size={24} />} title="Aucun enfant inscrit"
          desc="Les bulletins apparaissent ici dès qu'une inscription est validée par l'établissement." />
      ) : (
        <>
          {enfants.length > 1 && (
            <div className="mb-6 flex flex-wrap gap-2" role="tablist" aria-label="Enfant">
              {enfants.map((e) => (
                <Btn key={e.id} role="tab" aria-selected={choisi?.id === e.id} variant={choisi?.id === e.id ? "primary" : "outline"}
                  onClick={() => setParametres({ enfant: e.eleve_utilisateur_id! })}>
                  {e.eleve_prenom} {e.eleve_nom}
                </Btn>
              ))}
            </div>
          )}
          {choisi && (
            <>
              <p className="text-sm" style={{ color: "var(--ink-soft)", marginTop: 0 }}>
                Bulletin de <strong style={{ color: "var(--ink)" }}>{choisi.eleve_prenom} {choisi.eleve_nom}</strong>
              </p>
              <BulletinDetail key={choisi.id} eleveUtilisateurId={choisi.eleve_utilisateur_id!} classeId={choisi.classe_id}
                pourParent prenom={choisi.eleve_prenom} />
            </>
          )}
        </>
      )}
    </div>
  );
}
