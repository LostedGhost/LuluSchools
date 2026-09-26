import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { mesConversations } from "../../api/messagerie";
import { messageErreur } from "../../api/client";
import type { ConversationOut } from "../../types/api";
import { Badge, Card, EmptyState, ErrorBanner, SectionHead, SkeletonCard } from "../../components/ui";
import { MessageCircle, Users } from "lucide-react";

export function MessagerieListPage() {
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    mesConversations()
      .then((res) => setConversations(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, []);

  return (
    <div className="page-content">
      <SectionHead eyebrow="Messagerie" title="Mes conversations" />
      <ErrorBanner>{erreur}</ErrorBanner>

      {chargement ? (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : conversations.length === 0 ? (
        <EmptyState
          icon={<MessageCircle size={24} />}
          title="Aucune conversation pour l'instant"
          desc="Le groupe de votre classe apparaîtra automatiquement ici dès qu'une classe est associée à votre compte."
        />
      ) : (
        <div className="space-y-3">
          {conversations.map((c) => (
            <Link key={c.id} to={`/messagerie/${c.id}`}>
              <Card hover>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                  <div
                    style={{
                      width: "40px", height: "40px", borderRadius: "50%",
                      background: c.type === "groupe_classe" ? "var(--magic-tint)" : "var(--primary-tint)",
                      color: c.type === "groupe_classe" ? "var(--info-deep)" : "var(--primary-deep)",
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    }}
                    aria-hidden="true"
                  >
                    {c.type === "groupe_classe" ? <Users size={18} /> : <MessageCircle size={18} />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontWeight: 600, color: "var(--ink)", margin: 0 }}>
                      {c.type === "groupe_classe"
                        ? `Groupe de classe${c.classe_niveau ? ` — ${c.classe_niveau}` : ""}`
                        : `${c.autre_participant_prenom ?? ""} ${c.autre_participant_nom ?? "Conversation"}`.trim()}
                    </p>
                  </div>
                  <Badge tone={c.type === "groupe_classe" ? "magic" : "neutral"} dot={false}>
                    {c.type === "groupe_classe" ? "Classe" : "Message privé"}
                  </Badge>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
