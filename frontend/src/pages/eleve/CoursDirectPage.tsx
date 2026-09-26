import { useEffect, useState } from "react";
import { listerSessionsLive, rejoindreSessionLive } from "../../api/cours_direct";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { ParticipationLiveOut, SessionLiveOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  SectionHead,
  SkeletonCard,
} from "../../components/ui";
import { AlertTriangle, Radio, Video, VideoOff } from "lucide-react";

const STATUT_TONE: Record<SessionLiveOut["statut"], "pending" | "success" | "neutral"> = {
  planifiee: "pending",
  en_cours: "success",
  terminee: "neutral",
};

const STATUT_LABEL: Record<SessionLiveOut["statut"], string> = {
  planifiee: "Planifiée",
  en_cours: "En direct",
  terminee: "Terminée",
};

export function CoursDirectPage() {
  const profil = useEleveProfil();
  const [sessions, setSessions] = useState<SessionLiveOut[]>([]);
  const [participation, setParticipation] = useState<ParticipationLiveOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [rejointEnCoursId, setRejointEnCoursId] = useState<string | null>(null);

  const charger = () => {
    if (!profil.classe_id) {
      setChargement(false);
      return;
    }
    setChargement(true);
    listerSessionsLive(profil.classe_id)
      .then((res) => setSessions(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [profil.classe_id]);

  const rejoindre = async (sessionId: string) => {
    setRejointEnCoursId(sessionId);
    setErreur(null);
    try {
      const res = await rejoindreSessionLive(sessionId);
      setParticipation(res.data);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de rejoindre cette session."));
    } finally {
      setRejointEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <SectionHead eyebrow="Ma classe" title="Cours en direct" />
      <ErrorBanner>{erreur}</ErrorBanner>

      {participation && (
        <Card style={{ marginBottom: "24px", border: "1px solid color-mix(in srgb, var(--primary-deep) 30%, transparent)", background: "var(--primary-tint)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
            <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "var(--primary)", color: "var(--on-primary)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }} aria-hidden="true">
              <Radio size={22} />
            </div>
            <div style={{ flex: 1, minWidth: "200px" }}>
              <p style={{ margin: 0, fontWeight: 700, color: "var(--primary-deep)" }}>Vous êtes connecté(e) à la session</p>
              <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)", display: "flex", alignItems: "center", gap: "6px" }}>
                {participation.camera_autorisee ? <Video size={14} /> : <VideoOff size={14} />}
                {participation.camera_autorisee
                  ? "Votre caméra est autorisée pour cette session."
                  : "Votre caméra n'est pas autorisée — demandez à votre tuteur de donner son consentement."}
              </p>
            </div>
          </div>
        </Card>
      )}

      {chargement ? (
        <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
      ) : sessions.length === 0 ? (
        <EmptyState icon={<Video size={24} />} title="Aucune session en direct" desc="Votre enseignant n'a pas encore planifié de cours en direct pour votre classe." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {sessions.map((s) => (
            <Card key={s.id} className="anim-float-in">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
                <div>
                  <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>
                    {new Date(s.date_heure).toLocaleString("fr-FR", { dateStyle: "full", timeStyle: "short" })}
                  </p>
                  <Badge tone={STATUT_TONE[s.statut]}>{STATUT_LABEL[s.statut]}</Badge>
                </div>
                {s.statut === "en_cours" ? (
                  <Btn variant="primary" size="sm" loading={rejointEnCoursId === s.id} onClick={() => rejoindre(s.id)} leftIcon={<Radio size={14} />}>
                    Rejoindre
                  </Btn>
                ) : s.statut === "planifiee" ? (
                  <span className="text-sm" style={{ color: "var(--ink-faint)", display: "flex", alignItems: "center", gap: "6px" }}>
                    <AlertTriangle size={14} /> Pas encore démarrée
                  </span>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
