import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { listerElevesDeLaClasse } from "../../api/etablissements";
import {
  obtenirEtatTableau,
  ouvrirCanalTempsReelSessionLive,
  rejoindreSessionLive,
  terminerSessionLive,
} from "../../api/cours_direct";
import { messageErreur } from "../../api/client";
import type { EleveClasseOut, EtatTableauOut, SessionLiveOut } from "../../types/api";
import { Btn, Card, ErrorBanner, SectionHead } from "../../components/ui";
import { ChatSessionLive } from "../../components/ChatSessionLive";
import { PanneauPermissionsOrganisateur, TableauCollaboratif } from "../../components/TableauCollaboratif";
import { ArrowLeft, Radio, Users } from "lucide-react";

/**
 * Salle de classe virtuelle partagee enseignant/eleve (UC-25) : tableau collaboratif +
 * chat, y compris dans la "salle sociale" pre-cours (session encore PLANIFIEE). La visio
 * audio/video reelle (signalisation WebRTC en maillage) se branche sur le meme canal
 * WebSocket (evenements `webrtc_signal`) - non cablee dans cette page (P2 UI, la
 * signalisation serveur est deja fonctionnelle, voir cours_direct/router.py).
 */
export function SalleLivePage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { utilisateur } = useAuth();

  const sessionInitiale = (location.state as { session?: SessionLiveOut } | null)?.session ?? null;
  const [session] = useState<SessionLiveOut | null>(sessionInitiale);
  const [etat, setEtat] = useState<EtatTableauOut | null>(null);
  const [eleves, setEleves] = useState<EleveClasseOut[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [canal, setCanal] = useState<WebSocket | null>(null);
  const [canalPret, setCanalPret] = useState(false);

  const estOrganisateur = utilisateur?.role === "enseignant";

  useEffect(() => {
    if (!sessionId || !utilisateur) return;
    if (utilisateur.role === "eleve") {
      rejoindreSessionLive(sessionId).catch((err) => setErreur(messageErreur(err, "Impossible de rejoindre la session.")));
    }
  }, [sessionId, utilisateur]);

  useEffect(() => {
    if (!sessionId) return;
    const ws = ouvrirCanalTempsReelSessionLive(sessionId);
    ws.onopen = () => setCanalPret(true);
    ws.onclose = () => setCanalPret(false);
    setCanal(ws);
    return () => ws.close();
  }, [sessionId]);

  const rafraichirTableauEtat = () => {
    if (!sessionId) return;
    obtenirEtatTableau(sessionId)
      .then((res) => setEtat(res.data))
      .catch(() => undefined);
  };

  useEffect(rafraichirTableauEtat, [sessionId]);

  useEffect(() => {
    if (!session || !estOrganisateur) return;
    listerElevesDeLaClasse(session.classe_id)
      .then((res) => setEleves(res.data))
      .catch(() => undefined);
  }, [session, estOrganisateur]);

  const terminer = async () => {
    if (!sessionId) return;
    setEnCours(true);
    try {
      await terminerSessionLive(sessionId);
      navigate("/enseignant/cours-direct");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de terminer la session."));
    } finally {
      setEnCours(false);
    }
  };

  const retour = useMemo(
    () => (estOrganisateur ? "/enseignant/cours-direct" : "/eleve/cours-direct"),
    [estOrganisateur],
  );

  if (!sessionId || !utilisateur) return null;

  if (!session) {
    return (
      <div className="page-content">
        <ErrorBanner>Session introuvable - revenez à la liste des sessions et rouvrez-la depuis là.</ErrorBanner>
        <Btn variant="outline" onClick={() => navigate(retour)} leftIcon={<ArrowLeft size={14} />}>
          Retour
        </Btn>
      </div>
    );
  }

  return (
    <div className="page-content">
      <Btn variant="ghost" size="sm" onClick={() => navigate(retour)} leftIcon={<ArrowLeft size={14} />} style={{ marginBottom: "16px" }}>
        Retour
      </Btn>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
        <SectionHead
          eyebrow={session.statut === "planifiee" ? "Salle sociale - avant le cours" : "En direct"}
          title={new Date(session.date_heure).toLocaleString("fr-FR", { dateStyle: "full", timeStyle: "short" })}
          desc={
            session.statut === "planifiee"
              ? "Le professeur n'a pas encore démarré : discutez avec vos camarades en attendant, le tableau reste en lecture seule."
              : undefined
          }
        />
        {estOrganisateur && session.statut === "en_cours" && (
          <Btn variant="action" loading={enCours} onClick={terminer} leftIcon={<Radio size={14} />}>
            Terminer la session
          </Btn>
        )}
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>
      {!canalPret && <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>Connexion au canal temps réel...</p>}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 3fr) minmax(260px, 1fr)", gap: "20px", alignItems: "start" }}>
        <Card>
          <TableauCollaboratif
            sessionId={sessionId}
            estOrganisateur={estOrganisateur}
            monUtilisateurId={utilisateur.id}
            canal={canal}
          />
        </Card>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Card style={{ height: "320px" }}>
            <p style={{ margin: "0 0 8px", fontWeight: 700, fontSize: "var(--text-sm)" }}>Discussion</p>
            <div style={{ height: "calc(100% - 24px)" }}>
              <ChatSessionLive sessionId={sessionId} monUtilisateurId={utilisateur.id} canal={canal} />
            </div>
          </Card>

          {estOrganisateur && (
            <Card>
              <p style={{ margin: "0 0 8px", fontWeight: 700, fontSize: "var(--text-sm)", display: "flex", alignItems: "center", gap: "6px" }}>
                <Users size={14} /> Craie par élève
              </p>
              <PanneauPermissionsOrganisateur
                sessionId={sessionId}
                eleves={eleves}
                permissions={etat?.permissions ?? []}
                onChange={rafraichirTableauEtat}
              />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
