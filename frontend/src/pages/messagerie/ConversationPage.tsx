import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { listerMessages, masquerMessage, mesConversations, envoyerMessage, signalerMessage } from "../../api/messagerie";
import { messageErreur } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import type { ConversationOut, MessageOut } from "../../types/api";
import { Btn, EmptyState, ErrorBanner, Skeleton, TextArea } from "../../components/ui";
import { ArrowLeft, Flag, MessageCircle, Send, Trash2, Users } from "lucide-react";

export function ConversationPage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { utilisateur } = useAuth();
  const navigate = useNavigate();

  const [conversation, setConversation] = useState<ConversationOut | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [contenu, setContenu] = useState("");
  const [chargement, setChargement] = useState(true);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const finDuFil = useRef<HTMLDivElement>(null);

  const charger = () => {
    if (!conversationId) return;
    Promise.all([mesConversations(), listerMessages(conversationId)])
      .then(([resConversations, resMessages]) => {
        const trouvee = resConversations.data.find((c) => c.id === conversationId) ?? null;
        setConversation(trouvee);
        setMessages([...resMessages.data].reverse());
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [conversationId]);
  useEffect(() => {
    finDuFil.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const envoyer = async (e: FormEvent) => {
    e.preventDefault();
    if (!conversationId || !contenu.trim()) return;
    setEnvoiEnCours(true);
    setErreur(null);
    try {
      const res = await envoyerMessage(conversationId, contenu.trim());
      setMessages((prev) => [...prev, res.data]);
      setContenu("");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'envoyer ce message."));
    } finally {
      setEnvoiEnCours(false);
    }
  };

  const masquer = async (messageId: string) => {
    try {
      await masquerMessage(messageId);
      setMessages((prev) => prev.filter((m) => m.id !== messageId));
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const signaler = async (messageId: string) => {
    setSucces(null);
    setErreur(null);
    try {
      await signalerMessage(messageId);
      setSucces("Message signalé à l'administration de l'établissement.");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de signaler ce message."));
    }
  };

  const titre = conversation
    ? conversation.type === "groupe_classe"
      ? `Groupe de classe${conversation.classe_niveau ? ` — ${conversation.classe_niveau}` : ""}`
      : `${conversation.autre_participant_prenom ?? ""} ${conversation.autre_participant_nom ?? ""}`.trim() || "Conversation"
    : "Conversation";

  if (chargement) {
    return (
      <div className="page-content-narrow space-y-3">
        <Skeleton height="32px" width="240px" />
        <Skeleton height="400px" />
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="page-content-narrow">
        <ErrorBanner>{erreur || "Conversation introuvable."}</ErrorBanner>
        <Btn variant="outline" onClick={() => navigate("/messagerie")}>
          Retour aux conversations
        </Btn>
      </div>
    );
  }

  return (
    <div className="page-content-narrow" style={{ display: "flex", flexDirection: "column", height: "calc(100dvh - var(--space-8) * 2)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-4)" }}>
        <Btn variant="ghost" size="sm" onClick={() => navigate("/messagerie")} aria-label="Retour aux conversations">
          <ArrowLeft size={16} />
        </Btn>
        <div style={{
          width: "36px", height: "36px", borderRadius: "50%",
          background: conversation.type === "groupe_classe" ? "var(--magic-tint)" : "var(--primary-tint)",
          color: conversation.type === "groupe_classe" ? "var(--info-deep)" : "var(--primary-deep)",
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }} aria-hidden="true">
          {conversation.type === "groupe_classe" ? <Users size={16} /> : <MessageCircle size={16} />}
        </div>
        <h1 className="text-title" style={{ color: "var(--ink)", margin: 0 }}>{titre}</h1>
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && (
        <div style={{ marginBottom: "var(--space-3)" }}>
          <p className="text-sm" style={{ color: "var(--primary-deep)" }}>{succes}</p>
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: "var(--space-3)", padding: "var(--space-2) 0" }}>
        {messages.length === 0 ? (
          <EmptyState icon={<MessageCircle size={24} />} title="Aucun message" desc="Envoyez le premier message de cette conversation." />
        ) : (
          messages.map((m) => {
            const estMoi = m.auteur_id === utilisateur?.id;
            return (
              <div key={m.id} style={{ display: "flex", flexDirection: "column", alignItems: estMoi ? "flex-end" : "flex-start" }}>
                {!estMoi && conversation.type === "groupe_classe" && (
                  <span className="text-eyebrow" style={{ marginBottom: "2px", fontSize: "11px" }}>
                    {m.auteur_prenom} {m.auteur_nom}
                  </span>
                )}
                <div
                  style={{
                    maxWidth: "75%",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-lg)",
                    background: estMoi ? "var(--primary)" : "var(--surface-2)",
                    color: estMoi ? "var(--on-primary)" : "var(--ink)",
                  }}
                >
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{m.contenu}</p>
                </div>
                <div style={{ display: "flex", gap: "4px", marginTop: "2px" }}>
                  <button
                    type="button"
                    onClick={() => masquer(m.id)}
                    className="btn btn-ghost btn-sm"
                    style={{ padding: "2px 6px", fontSize: "11px", color: "var(--ink-faint)" }}
                    aria-label="Masquer ce message pour moi"
                  >
                    <Trash2 size={12} />
                  </button>
                  {!estMoi && (
                    <button
                      type="button"
                      onClick={() => signaler(m.id)}
                      className="btn btn-ghost btn-sm"
                      style={{ padding: "2px 6px", fontSize: "11px", color: "var(--action-deep)" }}
                      aria-label="Signaler ce message"
                    >
                      <Flag size={12} />
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={finDuFil} />
      </div>

      <form onSubmit={envoyer} style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end", paddingTop: "var(--space-3)" }}>
        <div style={{ flex: 1 }}>
          <TextArea
            value={contenu}
            onChange={(e) => setContenu(e.target.value)}
            placeholder="Écrire un message..."
            rows={1}
            style={{ minHeight: "44px" }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                envoyer(e as unknown as FormEvent);
              }
            }}
          />
        </div>
        <Btn type="submit" variant="primary" loading={envoiEnCours} disabled={!contenu.trim()} aria-label="Envoyer">
          <Send size={16} />
        </Btn>
      </form>
    </div>
  );
}
