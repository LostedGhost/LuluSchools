import { useEffect, useState } from "react";
import { apprenantsAdultes, type ApprenantAdulte } from "../../api/alphabetisation";
import { messageErreur } from "../../api/client";
import { EmptyState, ErrorBanner, SectionHead, Skeleton } from "../ui";

/** Lot 7.7 : les adultes inscrits dans les classes d'un centre d'alphabétisation (A+). */
export function ApprenantsAdultesPanel({ etablissementId }: { etablissementId: string }) {
  const [apprenants, setApprenants] = useState<ApprenantAdulte[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    apprenantsAdultes(etablissementId)
      .then((r) => setApprenants(r.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  return (
    <section style={{ marginTop: "var(--space-8)" }} aria-label="Apprenants adultes">
      <SectionHead eyebrow="Centre d'alphabétisation" title="Apprenants adultes" desc="Parents et adultes inscrits sur leur propre compte ; les leçons se publient comme des cours ordinaires." />
      <ErrorBanner>{erreur}</ErrorBanner>
      {!apprenants ? (
        !erreur && <Skeleton height="120px" />
      ) : apprenants.length === 0 ? (
        <EmptyState title="Aucun apprenant pour l'instant" desc="Les adultes s'inscrivent depuis « Apprendre à lire »." />
      ) : (
        <div className="table-defilante" tabIndex={0} role="region" aria-label="Liste des apprenants adultes">
          <table className="indicateurs-table">
            <thead>
              <tr>
                <th scope="col">Nom</th>
                <th scope="col">Classe</th>
                <th scope="col">Téléphone</th>
                <th scope="col">Inscrit le</th>
              </tr>
            </thead>
            <tbody>
              {apprenants.map((a) => (
                <tr key={`${a.utilisateur_id}-${a.classe_id}`}>
                  <th scope="row">{a.prenom} {a.nom}</th>
                  <td>{a.niveau}</td>
                  <td>{a.telephone ?? "—"}</td>
                  <td>{new Date(a.inscrit_le).toLocaleDateString("fr-FR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
