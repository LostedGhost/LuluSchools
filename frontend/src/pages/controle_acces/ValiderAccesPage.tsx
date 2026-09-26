import { useState } from "react";
import { validerTicketCantine, validerTicketTransport } from "../../api/services_scolaires";
import { validerBillet } from "../../api/billetterie";
import { messageErreur } from "../../api/client";
import type { ServiceControle } from "../../types/api";
import { Badge, Btn, Card, ErrorBanner, Field, Select, SectionHead, SuccessBanner, TextInput } from "../../components/ui";
import { Bus, ShieldCheck, Ticket, Utensils } from "lucide-react";

const SERVICE_OPTIONS: { value: ServiceControle; label: string; icon: typeof Bus }[] = [
  { value: "transport", label: "Ticket de transport", icon: Bus },
  { value: "cantine", label: "Ticket de cantine", icon: Utensils },
  { value: "evenement", label: "Billet d'événement", icon: Ticket },
];

export function ValiderAccesPage() {
  const [service, setService] = useState<ServiceControle>("transport");
  const [ticketId, setTicketId] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  const valider = async () => {
    if (!ticketId.trim()) {
      setErreur("Veuillez saisir l'identifiant du ticket ou du billet.");
      return;
    }
    setErreur(null);
    setSucces(null);
    setEnCours(true);
    try {
      if (service === "transport") await validerTicketTransport(ticketId.trim());
      else if (service === "cantine") await validerTicketCantine(ticketId.trim());
      else await validerBillet(ticketId.trim());
      setSucces("Accès validé avec succès.");
      setTicketId("");
    } catch (err) {
      setErreur(messageErreur(err, "Validation impossible : identifiant invalide, paiement non confirmé, ou vous n'êtes pas le contrôleur désigné."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="page-content-narrow">
      <SectionHead eyebrow="Contrôle d'accès" title="Valider un ticket ou un billet" />
      <Card>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Field label="Type d'accès">
            <Select value={service} onChange={(e: any) => setService(e.target.value as ServiceControle)}>
              {SERVICE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="Identifiant du ticket / billet" required helper="Communiqué par l'élève ou le tuteur lors de l'achat.">
            <TextInput
              value={ticketId}
              onChange={(e) => setTicketId(e.target.value)}
              placeholder="ID du ticket"
              onKeyDown={(e) => e.key === "Enter" && valider()}
            />
          </Field>

          <ErrorBanner>{erreur}</ErrorBanner>
          <SuccessBanner>{succes}</SuccessBanner>

          <Btn variant="primary" loading={enCours} onClick={valider} leftIcon={<ShieldCheck size={16} />}>
            Valider l'accès
          </Btn>
        </div>
      </Card>

      <p className="text-sm" style={{ color: "var(--ink-faint)", marginTop: "16px" }}>
        <Badge tone="info">Astuce</Badge> Vous devez être désigné comme contrôleur de ce service par l'administration de l'établissement pour pouvoir valider un accès.
      </p>
    </div>
  );
}
