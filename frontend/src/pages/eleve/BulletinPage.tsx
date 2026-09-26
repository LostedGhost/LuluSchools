import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { obtenirBulletin } from "../../api/evaluations";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { BulletinOut } from "../../types/api";
import { Card, ErrorBanner, EmptyState, Btn } from "../../components/ui";
import { ScoreBurst } from "../../components/gamification";
import { Award, BarChart3, ChevronRight } from "lucide-react";

const PERIODES = ["trimestre1", "trimestre2", "trimestre3"];

export function BulletinPage() {
  const profil = useEleveProfil();
  const [periode, setPeriode] = useState(PERIODES[0]);
  const [bulletin, setBulletin] = useState<BulletinOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);

  useEffect(() => {
    if (!profil.classe_id) return;
    setChargement(true);
    setErreur(null);
    setBulletin(null);
    obtenirBulletin(profil.id, profil.classe_id, periode)
      .then((res) => setBulletin(res.data))
      .catch((err) => setErreur(messageErreur(err, "Aucune moyenne disponible pour cette periode.")))
      .finally(() => setChargement(false));
  }, [profil.classe_id, profil.id, periode]);

  return (
    <div className="page-content">
      <div style={{ marginBottom: "32px" }}>
        <p className="text-eyebrow">Année scolaire en cours</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Mon bulletin</h1>
      </div>

      <div className="mb-6 flex gap-2">
        {PERIODES.map((p) => (
          <Btn
            key={p}
            variant={periode === p ? "primary" : "ghost"}
            size="md"
            onClick={() => setPeriode(p)}
          >
            {p.replace("trimestre", "Trimestre ")}
          </Btn>
        ))}
      </div>

      {chargement && <p className="text-slate-500">Chargement...</p>}
      {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

      {!chargement && !erreur && !bulletin && (
        <EmptyState
          icon={<BarChart3 size={24} />}
          title="Aucun bulletin disponible"
          desc="Les moyennes pour ce trimestre ne sont pas encore publiées."
        />
      )}

      {bulletin && (
        <div className="grid-2">
          <Card className="text-center anim-pop-in">
            <p className="text-label" style={{ color: "var(--ink-soft)", marginBottom: "8px" }}>Moyenne générale</p>
            <ScoreBurst
              score={bulletin.moyenne_generale}
              max={100}
              label="/ 100"
              tone={bulletin.moyenne_generale >= 50 ? "success" : "error"}
            />
          </Card>
          
          <Card variant="soft" className="anim-pop-in delay-1">
            <p className="text-label" style={{ color: "var(--ink-soft)", marginBottom: "8px" }}>Appréciation générale</p>
            {bulletin.valide_par_conseil ? (
              <p className="text-title" style={{ color: "var(--ink)" }}>
                {bulletin.decision_passage}
              </p>
            ) : (
              <p style={{ color: "var(--ink-faint)" }}>
                En attente de la décision du conseil de classe.
              </p>
            )}
          </Card>

          <div style={{ gridColumn: "1 / -1" }}>
            <Link to="/eleve/passeport" style={{ textDecoration: "none" }}>
              <Card hover style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Award size={20} style={{ color: "var(--reward-deep)", flexShrink: 0 }} />
                <span style={{ flex: 1, fontSize: "var(--text-sm)", color: "var(--ink)" }}>
                  Pour le détail de vos moyennes par matière, consultez votre passeport de compétences.
                </span>
                <ChevronRight size={16} style={{ color: "var(--ink-faint)" }} />
              </Card>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
