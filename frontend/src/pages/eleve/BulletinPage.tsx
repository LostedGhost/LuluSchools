import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { obtenirBulletin, periodesDeLaClasse, type PeriodeOut } from "../../api/evaluations";
import { codeErreur, messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { BulletinOut } from "../../types/api";
import { Card, ErrorBanner, EmptyState, Btn, SkeletonCard } from "../../components/ui";
import { ScoreBurst } from "../../components/gamification";
import { Award, BarChart3, ChevronRight } from "lucide-react";

export function BulletinPage() {
  const profil = useEleveProfil();
  // Trimestres (primaire, secondaire) ou semestres (université) de la classe ; on ouvre
  // la période en cours.
  const [periodes, setPeriodes] = useState<PeriodeOut[]>([]);
  const [periode, setPeriode] = useState<string | null>(null);
  const [bulletin, setBulletin] = useState<BulletinOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(!!profil.classe_id);

  useEffect(() => {
    if (!profil.classe_id) return;
    periodesDeLaClasse(profil.classe_id)
      .then((res) => {
        setPeriodes(res.data);
        setPeriode((res.data.find((p) => p.courante) ?? res.data[0])?.code ?? null);
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [profil.classe_id]);

  const periodeChoisie = periodes.find((p) => p.code === periode);
  const aVenir = periodeChoisie ? new Date(periodeChoisie.debut) > new Date() : false;

  useEffect(() => {
    if (!profil.classe_id || !periode) return;
    setChargement(true);
    setErreur(null);
    setBulletin(null);
    obtenirBulletin(profil.id, profil.classe_id, periode)
      .then((res) => setBulletin(res.data))
      .catch((err) => {
        // Aucun devoir encore evalue : situation normale en debut de periode, pas une erreur.
        if (codeErreur(err) !== "aucun_devoir_evalue") setErreur(messageErreur(err, "Aucune moyenne disponible pour cette période."));
      })
      .finally(() => setChargement(false));
  }, [profil.classe_id, profil.id, periode]);

  return (
    <div className="page-content">
      <div style={{ marginBottom: "32px" }}>
        <p className="text-eyebrow">Année scolaire en cours</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Mon bulletin</h1>
      </div>

      <div className="mb-6 flex flex-wrap gap-2" role="tablist" aria-label="Période">
        {periodes.map((p) => (
          <Btn
            key={p.code}
            role="tab"
            aria-selected={periode === p.code}
            variant={periode === p.code ? "primary" : "ghost"}
            size="md"
            onClick={() => setPeriode(p.code)}
          >
            {p.libelle}
            {p.courante && <span className="sr-only"> (en cours)</span>}
          </Btn>
        ))}
      </div>

      {chargement && <SkeletonCard />}
      {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

      {!chargement && !erreur && !bulletin && (
        <EmptyState
          icon={<BarChart3 size={24} />}
          title={aVenir ? "Période à venir" : "Pas encore de moyenne"}
          desc={
            aVenir
              ? `Le ${periodeChoisie?.libelle} commence le ${new Date(periodeChoisie!.debut).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}.`
              : "Aucun devoir de cette période n'a encore été corrigé. Votre moyenne apparaîtra ici dès la première note."
          }
        />
      )}

      {bulletin && (
        <div className="grid-2">
          <Card className="text-center anim-pop-in">
            <p className="text-label" style={{ color: "var(--ink-soft)", marginBottom: "8px" }}>Moyenne générale</p>
            <ScoreBurst
              score={Math.round(bulletin.moyenne_generale * 10) / 10}
              max={100}
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
