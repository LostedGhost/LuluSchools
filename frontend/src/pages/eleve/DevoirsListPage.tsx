import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listerDevoirs, maSoumission } from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { DevoirOut, SoumissionOut } from "../../types/api";
import { Badge, Card, ErrorBanner, SectionHead, EmptyState, SkeletonCard, Btn } from "../../components/ui";
import { FloatingXPBadge } from "../../components/gamification";
import { PartyPopper } from "lucide-react";

const LIBELLES_STATUT: Record<string, { label: string; tone: "neutral" | "success" | "error" | "pending" }> = {
  en_correction: { label: "En correction", tone: "pending" },
  corrigee: { label: "Corrigé", tone: "success" },
  echec_correction: { label: "En révision", tone: "error" },
};

type FilterStatus = 'tous' | 'en_cours' | 'corriges';

export function DevoirsListPage() {
  const profil = useEleveProfil();
  const [devoirs, setDevoirs] = useState<DevoirOut[]>([]);
  const [soumissions, setSoumissions] = useState<Record<string, SoumissionOut | null>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filtre, setFiltre] = useState<FilterStatus>('tous');

  useEffect(() => {
    if (!profil.classe_id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    listerDevoirs(profil.classe_id)
      .then(async (res) => {
        setDevoirs(res.data);
        const entrees = await Promise.all(
          res.data.map(async (d) => {
            try {
              return [d.id, (await maSoumission(d.id)).data] as const;
            } catch {
              return [d.id, null] as const;
            }
          }),
        );
        setSoumissions(Object.fromEntries(entrees));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setLoading(false));
  }, [profil.classe_id]);

  const devoirsFiltres = devoirs.filter(d => {
    const s = soumissions[d.id];
    if (filtre === 'tous') return true;
    if (filtre === 'en_cours') return !s || s.statut === 'en_correction' || s.statut === 'echec_correction';
    if (filtre === 'corriges') return s && s.statut === 'corrigee';
    return true;
  });

  const getUrgencyInfo = (devoir: DevoirOut, soumission: SoumissionOut | null) => {
    if (soumission) return { label: 'Soumis', tone: 'success' as const };
    const now = new Date();
    const limit = new Date(devoir.date_limite);
    const diff = limit.getTime() - now.getTime();
    if (diff < 0) return { label: 'En retard', tone: 'error' as const };
    if (diff < 24 * 60 * 60 * 1000) return { label: 'Urgent <24h', tone: 'error' as const };
    return { label: 'À venir', tone: 'pending' as const };
  };

  return (
    <div className="page-content">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 'var(--space-6)' }}>
        <SectionHead 
          eyebrow={`Total : ${devoirs.length}`} 
          title="Mes devoirs"
        />
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <Btn variant={filtre === 'tous' ? 'primary' : 'outline'} size="sm" onClick={() => setFiltre('tous')}>Tous</Btn>
          <Btn variant={filtre === 'en_cours' ? 'primary' : 'outline'} size="sm" onClick={() => setFiltre('en_cours')}>En cours</Btn>
          <Btn variant={filtre === 'corriges' ? 'primary' : 'outline'} size="sm" onClick={() => setFiltre('corriges')}>Corrigés</Btn>
        </div>
      </div>
      
      <ErrorBanner>{erreur}</ErrorBanner>

      {loading ? (
        <div className="grid-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : devoirsFiltres.length === 0 ? (
        <EmptyState
          icon={<PartyPopper size={24} />}
          title="Aucun devoir !"
          desc={filtre === 'tous' ? "Tu n'as aucun devoir pour le moment. Profites-en pour réviser !" : "Aucun devoir ne correspond à ce filtre."}
        />
      ) : (
        <div className="grid-2 anim-slide-up">
          {devoirsFiltres.map((devoir, idx) => {
            const soumission = soumissions[devoir.id];
            const statutGlobal = soumission ? LIBELLES_STATUT[soumission.statut] : null;
            const urgency = getUrgencyInfo(devoir, soumission);

            return (
              <Link key={devoir.id} to={`/eleve/devoirs/${devoir.id}`} className={`delay-${(idx % 5) + 1}`}>
                <Card hover style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)' }}>
                    <div>
                      <h3 className="text-title" style={{ marginBottom: 'var(--space-1)' }}>{devoir.titre}</h3>
                      <p className="text-label" style={{ color: 'var(--ink-soft)' }}>
                        {devoir.matiere}
                      </p>
                    </div>
                    <FloatingXPBadge amount={150} />
                  </div>
                  
                  <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <div style={{ display: 'flex', gap: 'var(--space-2)', flexDirection: 'column' }}>
                      <span className="text-sm">
                        Échéance : <strong>{new Date(devoir.date_limite).toLocaleDateString("fr-FR")}</strong>
                      </span>
                      <Badge tone={urgency.tone}>{urgency.label}</Badge>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      {statutGlobal ? (
                        <Badge tone={statutGlobal.tone}>{statutGlobal.label}</Badge>
                      ) : (
                        <Badge tone="neutral">À faire</Badge>
                      )}
                      {soumission?.note !== null && soumission?.note !== undefined && (
                        <div style={{ marginTop: 'var(--space-2)' }}>
                          <Badge tone="magic">Note : {soumission.note}</Badge>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
