import { useEffect, useState } from "react";
import { listerEtablissements } from "../../api/etablissements";
import { acheterBillet, amorcerPaiementBillet, listerEvenements, mesBillets, rembourserBillet } from "../../api/billetterie";
import { messageErreur } from "../../api/client";
import type { BilletEvenementOut, EtablissementOut, EvenementOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, Select, SectionHead, SkeletonCard, SuccessBanner } from "../../components/ui";
import { KkiapayButton } from "../../components/KkiapayButton";
import { CalendarDays, Ticket } from "lucide-react";

const STATUT_TONE: Record<BilletEvenementOut["statut"], "pending" | "success" | "neutral"> = {
  achete: "pending",
  valide: "success",
  expire: "neutral",
  rembourse: "neutral",
};

const STATUT_LABEL: Record<BilletEvenementOut["statut"], string> = {
  achete: "En attente de validation",
  valide: "Validé",
  expire: "Expiré",
  rembourse: "Remboursé",
};

export function BilletteriePage() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [evenements, setEvenements] = useState<EvenementOut[]>([]);
  const [mesBilletsList, setMesBilletsList] = useState<BilletEvenementOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [achatEnCoursId, setAchatEnCoursId] = useState<string | null>(null);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  useEffect(() => {
    listerEtablissements()
      .then((res) => {
        setEtablissements(res.data);
        if (res.data.length > 0) setEtablissementId((prev) => prev || res.data[0].id);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
    chargerMesBillets();
  }, []);

  const chargerMesBillets = () => {
    mesBillets()
      .then((res) => setMesBilletsList(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(() => {
    if (!etablissementId) return;
    listerEvenements(etablissementId)
      .then((res) => setEvenements(res.data.filter((e) => e.statut === "ouvert")))
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  const acheter = async (evenementId: string) => {
    setAchatEnCoursId(evenementId);
    setErreur(null);
    try {
      await acheterBillet(evenementId);
      setSucces("Billet réservé.");
      chargerMesBillets();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de réserver ce billet."));
    } finally {
      setAchatEnCoursId(null);
    }
  };

  const payer = async (billetId: string, transactionId: string) => {
    setActionEnCoursId(billetId);
    setErreur(null);
    try {
      await amorcerPaiementBillet(billetId, transactionId);
      setSucces("Paiement transmis, en cours de confirmation.");
      chargerMesBillets();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const rembourser = async (billetId: string) => {
    setActionEnCoursId(billetId);
    setErreur(null);
    try {
      await rembourserBillet(billetId);
      setSucces("Billet remboursé.");
      chargerMesBillets();
    } catch (err) {
      setErreur(messageErreur(err, "Le délai de remboursement (48h avant l'événement) est peut-être dépassé."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const evenementDuBillet = (billet: BilletEvenementOut) => evenements.find((e) => e.id === billet.evenement_id);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Vie scolaire" title="Billetterie d'événements" />
      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {mesBilletsList.length > 0 && (
        <div style={{ marginBottom: "32px" }}>
          <SectionHead title="Mes billets" />
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {mesBilletsList.map((b) => {
              const ev = evenementDuBillet(b);
              return (
                <Card key={b.id}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                    <div>
                      <p style={{ margin: 0, fontWeight: 600 }}>{ev?.titre ?? "Événement"}</p>
                      <Badge tone={STATUT_TONE[b.statut]}>{STATUT_LABEL[b.statut]}</Badge>
                    </div>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      {b.statut === "achete" && !b.paiement_confirme && b.prix_paye > 0 && (
                        <KkiapayButton montant={b.prix_paye} reference={b.id} onSucces={(txId) => payer(b.id, txId)} disabled={actionEnCoursId === b.id} />
                      )}
                      {b.statut === "achete" && (
                        <Btn variant="outline" size="sm" loading={actionEnCoursId === b.id} onClick={() => rembourser(b.id)}>
                          Rembourser
                        </Btn>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      <SectionHead title="Événements ouverts" desc="Choisissez un établissement pour voir ses événements à venir." />
      <div className="card card-soft" style={{ marginBottom: "24px", maxWidth: "360px" }}>
        <Field label="Établissement">
          <Select value={etablissementId} onChange={(e: any) => setEtablissementId(e.target.value)}>
            {etablissements.map((e) => (
              <option key={e.id} value={e.id}>{e.nom}</option>
            ))}
          </Select>
        </Field>
      </div>

      {chargement ? (
        <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
      ) : evenements.length === 0 ? (
        <EmptyState icon={<Ticket size={24} />} title="Aucun événement ouvert" desc="Cet établissement n'a pas d'événement à venir pour le moment." />
      ) : (
        <div className="space-y-4">
          {evenements.map((ev) => {
            const dejaAchete = mesBilletsList.some((b) => b.evenement_id === ev.id && b.statut !== "rembourse" && b.statut !== "expire");
            return (
              <Card key={ev.id} className="anim-float-in">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <CalendarDays size={16} style={{ color: "var(--ink-faint)" }} />
                      <h3 style={{ margin: 0, fontFamily: "var(--font-display)", fontWeight: 700 }}>{ev.titre}</h3>
                    </div>
                    <p style={{ margin: "4px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                      {ev.lieu} — {new Date(ev.date_heure).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" })}
                    </p>
                    {ev.description && <p style={{ margin: "6px 0 0", fontSize: "var(--text-sm)", color: "var(--ink)" }}>{ev.description}</p>}
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ margin: "0 0 8px", fontWeight: 700, color: "var(--primary-deep)" }}>
                      {ev.prix_billet > 0 ? `${ev.prix_billet.toLocaleString("fr-FR")} FCFA` : "Gratuit"}
                    </p>
                    {dejaAchete ? (
                      <Badge tone="success">Déjà réservé</Badge>
                    ) : (
                      <Btn variant="primary" size="sm" loading={achatEnCoursId === ev.id} onClick={() => acheter(ev.id)}>
                        Réserver un billet
                      </Btn>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
