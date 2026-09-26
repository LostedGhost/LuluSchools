import { useEffect, useState, type FormEvent } from "react";
import { listerClasses, listerEtablissements } from "../../api/etablissements";
import { demarrerSessionLive, listerSessionsLive, planifierSessionLive, terminerSessionLive } from "../../api/cours_direct";
import { mesContrats } from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { ClasseOut, EtablissementOut, SessionLiveDemarreeOut, SessionLiveOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  Select,
  TextInput,
  SectionHead,
  SkeletonCard,
  SuccessBanner,
} from "../../components/ui";
import { Radio, Video, School } from "lucide-react";

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

export function SessionsLivePage() {
  const [etablissementIds, setEtablissementIds] = useState<string[]>([]);
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [etablissementId, setEtablissementId] = useState("");
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [classeId, setClasseId] = useState("");
  const [sessions, setSessions] = useState<SessionLiveOut[]>([]);
  const [dateHeure, setDateHeure] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);
  const [sessionActive, setSessionActive] = useState<SessionLiveDemarreeOut | null>(null);

  useEffect(() => {
    mesContrats()
      .then((res) => {
        const ids = Array.from(new Set(res.data.filter((c) => c.statut === "signe").map((c) => c.etablissement_id)));
        setEtablissementIds(ids);
        if (ids.length > 0) setEtablissementId((prev) => prev || ids[0]);
      })
      .catch((err) => setErreur(messageErreur(err)));
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!etablissementId) {
      setClasses([]);
      return;
    }
    listerClasses(etablissementId)
      .then((res) => {
        setClasses(res.data);
        if (res.data.length > 0) setClasseId((prev) => prev || res.data[0].id);
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [etablissementId]);

  const chargerSessions = () => {
    if (!classeId) {
      setSessions([]);
      return;
    }
    setChargement(true);
    listerSessionsLive(classeId)
      .then((res) => setSessions(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(chargerSessions, [classeId]);

  const planifier = async (e: FormEvent) => {
    e.preventDefault();
    if (!classeId || !dateHeure) {
      setErreur("Veuillez sélectionner une classe et une date.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      await planifierSessionLive(classeId, new Date(dateHeure).toISOString());
      setDateHeure("");
      setSucces("Session en direct planifiée.");
      chargerSessions();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de planifier cette session."));
    } finally {
      setEnCours(false);
    }
  };

  const demarrer = async (sessionId: string) => {
    setActionEnCoursId(sessionId);
    setErreur(null);
    try {
      const res = await demarrerSessionLive(sessionId);
      setSessionActive(res.data);
      chargerSessions();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de démarrer cette session."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const terminer = async (sessionId: string) => {
    setActionEnCoursId(sessionId);
    setErreur(null);
    try {
      await terminerSessionLive(sessionId);
      if (sessionActive?.id === sessionId) setSessionActive(null);
      chargerSessions();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de terminer cette session."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "32px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <p className="text-eyebrow" style={{ marginBottom: "6px" }}>Espace Enseignant</p>
          <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Cours en direct</h1>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {sessionActive && (
        <Card style={{ marginBottom: "24px", border: "1px solid color-mix(in srgb, var(--primary-deep) 30%, transparent)", background: "var(--primary-tint)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
            <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "var(--primary)", color: "var(--on-primary)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }} aria-hidden="true">
              <Radio size={22} />
            </div>
            <div style={{ flex: 1, minWidth: "200px" }}>
              <p style={{ margin: 0, fontWeight: 700, color: "var(--primary-deep)" }}>Vous êtes en direct</p>
              <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                Vos élèves peuvent désormais rejoindre cette session depuis leur espace.
              </p>
            </div>
            <Btn variant="action" loading={actionEnCoursId === sessionActive.id} onClick={() => terminer(sessionActive.id)}>
              Terminer la session
            </Btn>
          </div>
        </Card>
      )}

      {/* Sélecteur classe */}
      <div className="card card-soft" style={{ display: "flex", gap: "16px", marginBottom: "28px", flexWrap: "wrap", alignItems: "flex-end" }}>
        <div style={{ flex: 1, minWidth: "220px" }}>
          <Field label="Établissement">
            <Select value={etablissementId} onChange={(e: any) => { setEtablissementId(e.target.value); setClasseId(""); }}>
              <option value="">Sélectionner un établissement...</option>
              {etablissementIds.map((id) => (
                <option key={id} value={id}>{etablissements.find((e) => e.id === id)?.nom ?? id}</option>
              ))}
            </Select>
          </Field>
        </div>
        <div style={{ flex: 1, minWidth: "200px" }}>
          <Field label="Classe / Niveau">
            <Select value={classeId} onChange={(e: any) => setClasseId(e.target.value)} disabled={!etablissementId}>
              <option value="">Sélectionner une classe...</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.niveau}</option>
              ))}
            </Select>
          </Field>
        </div>
      </div>

      {classeId && (
        <div className="card" style={{ marginBottom: "28px" }}>
          <SectionHead title="Planifier une nouvelle session" desc="Vos élèves verront la session apparaître dans leur espace dès qu'elle est planifiée." />
          <form onSubmit={planifier} style={{ display: "flex", gap: "16px", alignItems: "flex-end", flexWrap: "wrap", marginTop: "16px" }}>
            <div style={{ flex: 1, minWidth: "220px" }}>
              <Field label="Date et heure" required>
                <TextInput type="datetime-local" value={dateHeure} onChange={(e) => setDateHeure(e.target.value)} required />
              </Field>
            </div>
            <Btn type="submit" variant="primary" loading={enCours}>Planifier</Btn>
          </form>
        </div>
      )}

      {!classeId ? (
        <EmptyState icon={<School size={24} />} title="Sélectionnez une classe" desc="Choisissez un établissement et une classe pour gérer vos sessions en direct." />
      ) : chargement ? (
        <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
      ) : sessions.length === 0 ? (
        <EmptyState icon={<Video size={24} />} title="Aucune session planifiée" desc="Planifiez votre première session en direct pour cette classe." />
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
                <div style={{ display: "flex", gap: "8px" }}>
                  {s.statut === "planifiee" && (
                    <Btn variant="primary" size="sm" loading={actionEnCoursId === s.id} onClick={() => demarrer(s.id)} leftIcon={<Radio size={14} />}>
                      Démarrer
                    </Btn>
                  )}
                  {s.statut === "en_cours" && (
                    <Btn variant="action" size="sm" loading={actionEnCoursId === s.id} onClick={() => terminer(s.id)}>
                      Terminer
                    </Btn>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
