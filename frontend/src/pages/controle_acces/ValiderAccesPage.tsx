import { useEffect, useRef, useState } from "react";
import { validerTicketCantine, validerTicketTransport } from "../../api/services_scolaires";
import { validerBillet } from "../../api/billetterie";
import { messageErreur } from "../../api/client";
import type { ServiceControle } from "../../types/api";
import { Badge, Btn, Card, ErrorBanner, Field, Select, SectionHead, SuccessBanner, TextInput } from "../../components/ui";
import { Bus, Camera, Keyboard, ShieldCheck, Ticket, Utensils } from "lucide-react";

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
  const [mode, setMode] = useState<"manuel" | "scan">("manuel");
  const [scanSupporte, setScanSupporte] = useState(true);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const boucleRef = useRef<number | null>(null);

  useEffect(() => {
    if (mode !== "scan") return;
    if (!("BarcodeDetector" in window)) {
      setScanSupporte(false);
      return;
    }
    setScanSupporte(true);
    let arrete = false;
    // "BarcodeDetector" n'est pas encore dans les types DOM par défaut de TypeScript.
    const detecteur = new (window as any).BarcodeDetector({ formats: ["qr_code"] });

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((stream) => {
        if (arrete) {
          stream.getTracks().forEach((piste) => piste.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
        const boucle = async () => {
          if (arrete || !videoRef.current) return;
          try {
            const codes = await detecteur.detect(videoRef.current);
            if (codes.length > 0) {
              traiterJeton(codes[0].rawValue as string);
              return;
            }
          } catch {
            // image pas encore prête pour la détection, on continue la boucle
          }
          boucleRef.current = requestAnimationFrame(boucle);
        };
        boucleRef.current = requestAnimationFrame(boucle);
      })
      .catch(() => setErreur("Impossible d'accéder à la caméra. Vérifiez les autorisations du navigateur."));

    return () => {
      arrete = true;
      if (boucleRef.current) cancelAnimationFrame(boucleRef.current);
      streamRef.current?.getTracks().forEach((piste) => piste.stop());
      streamRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const traiterJeton = (jeton: string) => {
    const [type, id] = jeton.split(":");
    if (!type || !id || !SERVICE_OPTIONS.some((o) => o.value === type)) {
      setErreur("QR code non reconnu.");
      return;
    }
    setErreur(null);
    setService(type as ServiceControle);
    setTicketId(id);
    setMode("manuel");
  };

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

      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <Btn variant={mode === "manuel" ? "primary" : "ghost"} size="sm" onClick={() => setMode("manuel")} leftIcon={<Keyboard size={14} />}>
          Saisie manuelle
        </Btn>
        <Btn variant={mode === "scan" ? "primary" : "ghost"} size="sm" onClick={() => setMode("scan")} leftIcon={<Camera size={14} />}>
          Scanner un QR code
        </Btn>
      </div>

      {mode === "scan" && (
        <Card style={{ marginBottom: "16px" }}>
          {scanSupporte ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", alignItems: "center" }}>
              <video ref={videoRef} muted playsInline style={{ width: "100%", maxWidth: "360px", borderRadius: "12px", background: "#000" }} />
              <p className="text-sm" style={{ color: "var(--ink-soft)" }}>Placez le QR code du ticket devant la caméra.</p>
            </div>
          ) : (
            <ErrorBanner>
              Le scan de QR code n'est pas pris en charge par ce navigateur. Utilisez la saisie manuelle.
            </ErrorBanner>
          )}
        </Card>
      )}

      <Card>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Field label="Type d'accès">
            <Select value={service} onChange={(e: any) => setService(e.target.value as ServiceControle)}>
              {SERVICE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </Field>
          <Field label="Identifiant du ticket / billet" required helper="Communiqué par l'élève ou le tuteur lors de l'achat, ou obtenu en scannant le QR code.">
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
