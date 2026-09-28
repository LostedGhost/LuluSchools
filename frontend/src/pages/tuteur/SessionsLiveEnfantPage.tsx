import { useEffect, useState } from "react";
import { libelle } from "../../utils/libelles";
import { listerSessionsLive, obtenirResumeSessionLive } from "../../api/cours_direct";
import { messageErreur, codeErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { SessionLiveOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard } from "../../components/ui";
import { Radio, Users } from "lucide-react";

export function SessionsLiveEnfantPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [sessions, setSessions] = useState<SessionLiveOut[]>([]);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [resumes, setResumes] = useState<Record<string, string>>({});
  const [enCoursId, setEnCoursId] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  useEffect(() => {
    if (!enfant) return;
    setChargement(true);
    listerSessionsLive(enfant.classe_id)
      .then((res) => setSessions(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, [enfant]);

  const voirResume = async (sessionId: string) => {
    setEnCoursId(sessionId);
    setErreur(null);
    try {
      const res = await obtenirResumeSessionLive(sessionId);
      setResumes((prev) => ({ ...prev, [sessionId]: res.data.contenu }));
    } catch (err) {
      if (codeErreur(err) === "introuvable") {
        setResumes((prev) => ({ ...prev, [sessionId]: "Aucun résumé n'est disponible pour cette session." }));
      } else {
        setErreur(messageErreur(err, "Impossible d'obtenir le résumé."));
      }
    } finally {
      setEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Mes enfants"
        title="Cours en direct"
        desc="Vous ne rejoignez jamais une session en direct : consultez un résumé une fois la session terminée."
      />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" />
      ) : (
        <>
          <div className="card card-soft" style={{ marginBottom: "24px", maxWidth: "360px" }}>
            <Field label="Enfant">
              <Select value={inscriptionId} onChange={(e) => setInscriptionId(e.target.value)}>
                {enfants.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.eleve_prenom} {i.eleve_nom}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {chargement ? (
            <SkeletonCard />
          ) : sessions.length === 0 ? (
            <EmptyState icon={<Radio size={24} />} title="Aucune session" desc="Aucune session en direct n'a encore eu lieu dans cette classe." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {sessions.map((s) => (
                <Card key={s.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                    <span style={{ fontSize: "var(--text-sm)" }}>{new Date(s.date_heure).toLocaleString("fr-FR")}</span>
                    <Badge tone={s.statut === "terminee" ? "success" : s.statut === "en_cours" ? "pending" : "neutral"}>{libelle(s.statut)}</Badge>
                  </div>
                  {s.statut === "terminee" && (
                    <div style={{ marginTop: "12px" }}>
                      {resumes[s.id] ? (
                        <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink)", whiteSpace: "pre-wrap" }}>{resumes[s.id]}</p>
                      ) : (
                        <Btn variant="outline" size="sm" loading={enCoursId === s.id} onClick={() => voirResume(s.id)}>
                          Voir le résumé
                        </Btn>
                      )}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
