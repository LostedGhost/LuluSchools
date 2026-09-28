import { useEffect, useRef, useState, type FormEvent } from "react";
import { envoyerMessageSessionLive, listerMessagesSessionLive } from "../api/cours_direct";
import { messageErreur } from "../api/client";
import type { EvenementTempsReelSessionLive, MessageSessionLiveOut } from "../types/api";
import { Btn, ErrorBanner, TextInput } from "./ui";
import { Send } from "lucide-react";

/** UC-25.5 : chat de la session, y compris dans la "salle sociale" avant l'arrivee du
 * professeur (session encore PLANIFIEE) - voir cours_direct.envoyer_message_session_live. */
export function ChatSessionLive({
  sessionId,
  monUtilisateurId,
  canal,
}: {
  sessionId: string;
  monUtilisateurId: string;
  canal: WebSocket | null;
}) {
  const [messages, setMessages] = useState<MessageSessionLiveOut[]>([]);
  const [contenu, setContenu] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const finDeListe = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listerMessagesSessionLive(sessionId)
      .then((res) => setMessages(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [sessionId]);

  useEffect(() => {
    if (!canal) return;
    const gestionnaire = (evt: MessageEvent) => {
      let message: EvenementTempsReelSessionLive;
      try {
        message = JSON.parse(evt.data);
      } catch {
        return;
      }
      if (message.type === "message") {
        setMessages((prev) => (prev.some((m) => m.id === message.message.id) ? prev : [...prev, message.message]));
      }
    };
    canal.addEventListener("message", gestionnaire);
    return () => canal.removeEventListener("message", gestionnaire);
  }, [canal]);

  useEffect(() => {
    finDeListe.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const envoyer = async (e: FormEvent) => {
    e.preventDefault();
    if (!contenu.trim()) return;
    setEnCours(true);
    setErreur(null);
    try {
      const res = await envoyerMessageSessionLive(sessionId, contenu.trim());
      setMessages((prev) => (prev.some((m) => m.id === res.data.id) ? prev : [...prev, res.data]));
      setContenu("");
    } catch (err) {
      setErreur(messageErreur(err, "Message non envoyé."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <ErrorBanner>{erreur}</ErrorBanner>
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px", padding: "4px" }}>
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              alignSelf: m.auteur_id === monUtilisateurId ? "flex-end" : "flex-start",
              maxWidth: "80%",
              background: m.auteur_id === monUtilisateurId ? "var(--primary-tint)" : "var(--surface-2)",
              borderRadius: "var(--radius-md)",
              padding: "6px 10px",
              fontSize: "var(--text-sm)",
            }}
          >
            {m.contenu}
          </div>
        ))}
        <div ref={finDeListe} />
      </div>
      <form onSubmit={envoyer} style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
        <TextInput
          value={contenu}
          onChange={(e) => setContenu(e.target.value)}
          placeholder="Écrire un message…"
          style={{ flex: 1 }}
        />
        <Btn type="submit" size="sm" variant="primary" loading={enCours} leftIcon={<Send size={14} />}>
          Envoyer
        </Btn>
      </form>
    </div>
  );
}
