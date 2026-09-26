import { useEffect, useState } from "react";
import {
  acheterTicketCantine,
  acheterTicketTransport,
  amorcerPaiementTicketCantine,
  amorcerPaiementTicketTransport,
  listerLignesTransport,
  listerTypesRepasCantine,
  mesTicketsCantine,
  mesTicketsTransport,
  rembourserTicketCantine,
  rembourserTicketTransport,
} from "../../api/services_scolaires";
import { messageErreur } from "../../api/client";
import type { LigneTransportOut, StatutTicket, TicketCantineOut, TicketTransportOut, TypeRepasCantineOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard, SuccessBanner, TextInput } from "../../components/ui";
import { KkiapayButton } from "../../components/KkiapayButton";
import { Bus, RefreshCw, Utensils } from "lucide-react";

const STATUT_TONE: Record<StatutTicket, "pending" | "success" | "neutral" | "error"> = {
  achete: "pending",
  valide: "success",
  expire: "neutral",
  rembourse: "neutral",
};

const STATUT_LABEL: Record<StatutTicket, string> = {
  achete: "En attente de validation",
  valide: "Validé",
  expire: "Expiré",
  rembourse: "Remboursé",
};

interface ServicesScolairesPanelProps {
  etablissementId: string;
  eleveUtilisateurId?: string;
}

export function ServicesScolairesPanel({ etablissementId, eleveUtilisateurId }: ServicesScolairesPanelProps) {
  const [lignes, setLignes] = useState<LigneTransportOut[]>([]);
  const [types, setTypes] = useState<TypeRepasCantineOut[]>([]);
  const [ticketsTransport, setTicketsTransport] = useState<TicketTransportOut[]>([]);
  const [ticketsCantine, setTicketsCantine] = useState<TicketCantineOut[]>([]);
  const [ligneChoisie, setLigneChoisie] = useState("");
  const [dateTrajet, setDateTrajet] = useState("");
  const [typeChoisi, setTypeChoisi] = useState("");
  const [dateService, setDateService] = useState("");
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<"transport" | "cantine" | null>(null);
  const [actionTicketId, setActionTicketId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    setErreur(null);
    Promise.all([
      listerLignesTransport(etablissementId),
      listerTypesRepasCantine(etablissementId),
      mesTicketsTransport(),
      mesTicketsCantine(),
    ])
      .then(([resLignes, resTypes, resTicketsT, resTicketsC]) => {
        setLignes(resLignes.data);
        setTypes(resTypes.data);
        setTicketsTransport(
          eleveUtilisateurId ? resTicketsT.data.filter((t) => t.utilisateur_id === eleveUtilisateurId) : resTicketsT.data,
        );
        setTicketsCantine(
          eleveUtilisateurId ? resTicketsC.data.filter((t) => t.utilisateur_id === eleveUtilisateurId) : resTicketsC.data,
        );
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissementId, eleveUtilisateurId]);

  const acheterTransport = async () => {
    if (!ligneChoisie || !dateTrajet) {
      setErreur("Veuillez choisir une ligne et une date.");
      return;
    }
    setErreur(null);
    setEnCours("transport");
    try {
      await acheterTicketTransport(ligneChoisie, new Date(dateTrajet).toISOString(), eleveUtilisateurId);
      setSucces("Ticket de transport réservé. Procédez au paiement ci-dessous.");
      setDateTrajet("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de réserver ce ticket."));
    } finally {
      setEnCours(null);
    }
  };

  const acheterCantine = async () => {
    if (!typeChoisi || !dateService) {
      setErreur("Veuillez choisir un service et une date.");
      return;
    }
    setErreur(null);
    setEnCours("cantine");
    try {
      await acheterTicketCantine(typeChoisi, new Date(dateService).toISOString(), eleveUtilisateurId);
      setSucces("Ticket de cantine réservé. Procédez au paiement ci-dessous.");
      setDateService("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de réserver ce ticket."));
    } finally {
      setEnCours(null);
    }
  };

  const payerTransport = async (ticketId: string, transactionId: string) => {
    setActionTicketId(ticketId);
    setErreur(null);
    try {
      await amorcerPaiementTicketTransport(ticketId, transactionId);
      setSucces("Paiement transmis, en cours de confirmation.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionTicketId(null);
    }
  };

  const payerCantine = async (ticketId: string, transactionId: string) => {
    setActionTicketId(ticketId);
    setErreur(null);
    try {
      await amorcerPaiementTicketCantine(ticketId, transactionId);
      setSucces("Paiement transmis, en cours de confirmation.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionTicketId(null);
    }
  };

  const rembourserTransport = async (ticketId: string) => {
    setActionTicketId(ticketId);
    setErreur(null);
    try {
      await rembourserTicketTransport(ticketId);
      setSucces("Ticket remboursé.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Le délai de remboursement (avant 18h la veille) est peut-être dépassé."));
    } finally {
      setActionTicketId(null);
    }
  };

  const rembourserCantine = async (ticketId: string) => {
    setActionTicketId(ticketId);
    setErreur(null);
    try {
      await rembourserTicketCantine(ticketId);
      setSucces("Ticket remboursé.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Le délai de remboursement (avant 18h la veille) est peut-être dépassé."));
    } finally {
      setActionTicketId(null);
    }
  };

  if (chargement) {
    return <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>;
  }

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {/* Transport */}
      <div>
        <SectionHead title="Transport scolaire" desc="Réservez un ticket de transport pour une date donnée." />
        {lignes.length === 0 ? (
          <EmptyState icon={<Bus size={24} />} title="Aucune ligne de transport" desc="Cet établissement n'a pas encore configuré de ligne de transport." />
        ) : (
          <Card variant="soft" style={{ marginBottom: "16px" }}>
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ flex: 1, minWidth: "200px" }}>
                <Field label="Ligne">
                  <Select value={ligneChoisie} onChange={(e: any) => setLigneChoisie(e.target.value)}>
                    <option value="">Choisir une ligne...</option>
                    {lignes.map((l) => (
                      <option key={l.id} value={l.id}>{l.nom} — {l.prix.toLocaleString("fr-FR")} FCFA</option>
                    ))}
                  </Select>
                </Field>
              </div>
              <div style={{ flex: 1, minWidth: "180px" }}>
                <Field label="Date du trajet">
                  <TextInput type="date" value={dateTrajet} onChange={(e) => setDateTrajet(e.target.value)} />
                </Field>
              </div>
              <Btn variant="primary" loading={enCours === "transport"} onClick={acheterTransport} leftIcon={<Bus size={16} />}>
                Réserver
              </Btn>
            </div>
          </Card>
        )}

        {ticketsTransport.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {ticketsTransport.map((t) => (
              <Card key={t.id} className="anim-float-in">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                  <div>
                    <p style={{ margin: 0, fontWeight: 600, color: "var(--ink)" }}>
                      {new Date(t.date_trajet).toLocaleDateString("fr-FR")} — {t.prix_paye.toLocaleString("fr-FR")} FCFA
                    </p>
                    <Badge tone={STATUT_TONE[t.statut]}>{STATUT_LABEL[t.statut]}</Badge>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    {t.statut === "achete" && !t.paiement_confirme && (
                      <KkiapayButton montant={t.prix_paye} reference={t.id} onSucces={(txId) => payerTransport(t.id, txId)} disabled={actionTicketId === t.id} />
                    )}
                    {t.statut === "achete" && (
                      <Btn variant="outline" size="sm" loading={actionTicketId === t.id} onClick={() => rembourserTransport(t.id)}>
                        Rembourser
                      </Btn>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Cantine */}
      <div>
        <SectionHead title="Cantine scolaire" desc="Réservez un ticket de repas pour une date donnée." />
        {types.length === 0 ? (
          <EmptyState icon={<Utensils size={24} />} title="Aucun service de cantine" desc="Cet établissement n'a pas encore configuré de service de cantine." />
        ) : (
          <Card variant="soft" style={{ marginBottom: "16px" }}>
            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end" }}>
              <div style={{ flex: 1, minWidth: "200px" }}>
                <Field label="Service">
                  <Select value={typeChoisi} onChange={(e: any) => setTypeChoisi(e.target.value)}>
                    <option value="">Choisir un service...</option>
                    {types.map((t) => (
                      <option key={t.id} value={t.id}>{t.nom} — {t.prix.toLocaleString("fr-FR")} FCFA</option>
                    ))}
                  </Select>
                </Field>
              </div>
              <div style={{ flex: 1, minWidth: "180px" }}>
                <Field label="Date du repas">
                  <TextInput type="date" value={dateService} onChange={(e) => setDateService(e.target.value)} />
                </Field>
              </div>
              <Btn variant="primary" loading={enCours === "cantine"} onClick={acheterCantine} leftIcon={<Utensils size={16} />}>
                Réserver
              </Btn>
            </div>
          </Card>
        )}

        {ticketsCantine.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {ticketsCantine.map((t) => (
              <Card key={t.id} className="anim-float-in">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                  <div>
                    <p style={{ margin: 0, fontWeight: 600, color: "var(--ink)" }}>
                      {new Date(t.date_service).toLocaleDateString("fr-FR")} — {t.prix_paye.toLocaleString("fr-FR")} FCFA
                    </p>
                    <Badge tone={STATUT_TONE[t.statut]}>{STATUT_LABEL[t.statut]}</Badge>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    {t.statut === "achete" && !t.paiement_confirme && (
                      <KkiapayButton montant={t.prix_paye} reference={t.id} onSucces={(txId) => payerCantine(t.id, txId)} disabled={actionTicketId === t.id} />
                    )}
                    {t.statut === "achete" && (
                      <Btn variant="outline" size="sm" loading={actionTicketId === t.id} onClick={() => rembourserCantine(t.id)}>
                        Rembourser
                      </Btn>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Btn variant="ghost" size="sm" onClick={charger} leftIcon={<RefreshCw size={14} />}>
        Actualiser les statuts de paiement
      </Btn>
    </div>
  );
}
