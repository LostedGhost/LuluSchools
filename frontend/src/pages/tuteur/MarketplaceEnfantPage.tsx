import { useEffect, useState } from "react";
import { libelle } from "../../utils/libelles";
import { annoncesDeMonEnfant, transactionsDeMonEnfant } from "../../api/marketplace";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { AnnonceMarketplaceOut, TransactionMarketplaceOut } from "../../types/api";
import { Badge, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard } from "../../components/ui";
import { ShoppingBag, Users } from "lucide-react";

const TONE_STATUT_ANNONCE: Record<string, "neutral" | "success" | "error" | "pending"> = {
  disponible: "neutral",
  reservee: "pending",
  vendue: "success",
  retiree: "error",
};

const TONE_STATUT_TRANSACTION: Record<string, "neutral" | "success" | "error" | "pending"> = {
  en_attente_paiement: "pending",
  paiement_confirme: "pending",
  remise_declaree: "pending",
  confirmee: "success",
  contestee: "error",
  finalisee: "success",
  remboursee: "error",
  annulee: "error",
};

export function MarketplaceEnfantPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [annonces, setAnnonces] = useState<AnnonceMarketplaceOut[]>([]);
  const [transactions, setTransactions] = useState<TransactionMarketplaceOut[]>([]);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  useEffect(() => {
    if (!enfant || !enfant.eleve_utilisateur_id) return;
    const eleveUtilisateurId = enfant.eleve_utilisateur_id;
    setChargement(true);
    Promise.all([annoncesDeMonEnfant(eleveUtilisateurId), transactionsDeMonEnfant(eleveUtilisateurId)])
      .then(([resAnnonces, resTransactions]) => {
        setAnnonces(resAnnonces.data);
        setTransactions(resTransactions.data);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [enfant]);

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Mes enfants"
        title="Marketplace"
        desc="Consultation en lecture seule des annonces et transactions de votre enfant (≥16 ans) — vous ne pouvez pas publier ni acheter à sa place."
      />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" desc="Cette consultation est disponible une fois l'inscription de votre enfant validée." />
      ) : (
        <>
          <div className="card card-soft" style={{ marginBottom: "24px", maxWidth: "360px" }}>
            <Field label="Enfant">
              <Select value={inscriptionId} onChange={(e) => setInscriptionId(e.target.value)}>
                {enfants.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.eleve_prenom} {i.eleve_nom}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {chargement ? (
            <SkeletonCard />
          ) : (
            <>
              <SectionHead eyebrow="Ventes" title="Annonces publiées" />
              {annonces.length === 0 ? (
                <EmptyState icon={<ShoppingBag size={24} />} title="Aucune annonce" />
              ) : (
                <div className="grid-2" style={{ marginBottom: "32px" }}>
                  {annonces.map((a) => (
                    <Card key={a.id}>
                      <h3 className="text-title" style={{ marginBottom: "4px" }}>{a.titre}</h3>
                      <p style={{ margin: "0 0 8px", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>{a.prix} FCFA</p>
                      <Badge tone={TONE_STATUT_ANNONCE[a.statut] ?? "neutral"}>{libelle(a.statut)}</Badge>
                    </Card>
                  ))}
                </div>
              )}

              <SectionHead eyebrow="Historique" title="Transactions" />
              {transactions.length === 0 ? (
                <EmptyState title="Aucune transaction" />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {transactions.map((t) => (
                    <div key={t.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                      <span style={{ fontSize: "var(--text-sm)" }}>{t.prix_paye} FCFA</span>
                      <Badge tone={TONE_STATUT_TRANSACTION[t.statut] ?? "neutral"}>{libelle(t.statut)}</Badge>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
