import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Award, BarChart3, ChevronRight, FileDown } from "lucide-react";
import { codeErreur, messageErreur } from "../../api/client";
import { obtenirBulletinDetaille, periodesDeLaClasse, telechargerBulletinPdf, type MatiereDuBulletin, type PeriodeOut } from "../../api/evaluations";
import type { BulletinOut } from "../../types/api";
import { libelle } from "../../utils/libelles";
import { ouvrirBlobPdf } from "../../utils/telechargerBlob";
import { ScoreBurst } from "../gamification";
import { Badge, Btn, Card, EmptyState, ErrorBanner, SectionHead, SkeletonCard } from "../ui";

/** Bulletin d'un élève pour une classe : onglets de période (période en cours ouverte),
 * moyenne générale, décision du conseil, PDF et détail des notes par matière. Partagé par
 * l'écran de l'élève et celui du parent (mêmes données que le bulletin PDF). */
export function BulletinDetail({ eleveUtilisateurId, classeId, pourParent = false, prenom }: {
  eleveUtilisateurId: string;
  classeId: string;
  pourParent?: boolean;
  prenom?: string;
}) {
  const profil = { id: eleveUtilisateurId, classe_id: classeId };
  // Trimestres (primaire, secondaire) ou semestres (université) de la classe ; on ouvre
  // la période en cours.
  const [periodes, setPeriodes] = useState<PeriodeOut[]>([]);
  const [periode, setPeriode] = useState<string | null>(null);
  const [bulletin, setBulletin] = useState<BulletinOut | null>(null);
  const [matieres, setMatieres] = useState<MatiereDuBulletin[]>([]);
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
  const [pdfEnCours, setPdfEnCours] = useState(false);
  const telechargerPdf = async () => {
    if (!profil.classe_id || !periode) return;
    setPdfEnCours(true);
    try {
      const res = await telechargerBulletinPdf(profil.id, profil.classe_id, periode);
      ouvrirBlobPdf(res.data, `bulletin-${prenom ? `${prenom}-` : ""}${periode}.pdf`);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de générer le bulletin pour le moment."));
    } finally {
      setPdfEnCours(false);
    }
  };
  const aVenir = periodeChoisie ? new Date(periodeChoisie.debut) > new Date() : false;

  useEffect(() => {
    if (!profil.classe_id || !periode) return;
    setChargement(true);
    setErreur(null);
    setBulletin(null);
    setMatieres([]);
    obtenirBulletinDetaille(profil.id, profil.classe_id, periode)
      .then((res) => {
        setBulletin(res.data.bulletin);
        setMatieres(res.data.matieres);
      })
      .catch((err) => {
        // Aucun devoir encore evalue : situation normale en debut de periode, pas une erreur.
        if (codeErreur(err) !== "aucun_devoir_evalue") setErreur(messageErreur(err, "Aucune moyenne disponible pour cette période."));
      })
      .finally(() => setChargement(false));
  }, [profil.classe_id, profil.id, periode]);

  return (
    <div>
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
              : `Aucun devoir de cette période n'a encore été corrigé. ${pourParent ? `La moyenne de ${prenom ?? "votre enfant"}` : "Votre moyenne"} apparaîtra ici dès la première note.`
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
                {libelle(bulletin.decision_passage)}
              </p>
            ) : (
              <p style={{ color: "var(--ink-faint)" }}>
                En attente de la décision du conseil de classe.
              </p>
            )}
          </Card>

          <div style={{ gridColumn: "1 / -1" }}>
            <Btn variant="primary" leftIcon={<FileDown size={16} />} loading={pdfEnCours} onClick={telechargerPdf} style={{ marginBottom: "12px" }}>
              Télécharger le bulletin (PDF)
            </Btn>
          </div>

          <div style={{ gridColumn: "1 / -1" }}>
            <SectionHead title="Détail par matière" desc="Chaque note est ramenée sur 100, puis pondérée par le coefficient de sa matière." />
            <div className="space-y-3">
              {matieres.map((m) => (
                <Card key={m.matiere}>
                  <div className="flex flex-wrap items-center justify-between gap-2" style={{ marginBottom: "8px" }}>
                    <h3 style={{ margin: 0, fontSize: "var(--text-lg)", color: "var(--ink)" }}>{m.matiere}</h3>
                    <span className="flex items-center gap-2">
                      <span className="text-sm" style={{ color: "var(--ink-soft)" }}>coef. {m.coefficient.toLocaleString("fr-FR")}</span>
                      <Badge tone={m.moyenne >= 50 ? "success" : "error"}>{m.moyenne.toFixed(1)} / 100</Badge>
                    </span>
                  </div>
                  <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                    {m.evaluations.map((e) => (
                      <li key={e.devoir_id} className="flex items-center gap-3" style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                        <span style={{ flex: 1, minWidth: 0 }}>
                          {pourParent ? (
                            <span style={{ color: "var(--ink)" }}>{e.titre}</span>
                          ) : (
                            <Link to={`/eleve/devoirs/${e.devoir_id}`} style={{ color: "var(--ink)" }}>{e.titre}</Link>
                          )}
                          <span className="text-sm" style={{ display: "block", color: "var(--ink-faint)" }}>
                            {new Date(e.date).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}
                          </span>
                        </span>
                        {e.note === null ? (
                          <Badge tone="error">Non rendu (0)</Badge>
                        ) : (
                          <strong style={{ color: "var(--ink)", whiteSpace: "nowrap" }}>
                            {e.note.toLocaleString("fr-FR")} / {e.total.toLocaleString("fr-FR")}
                          </strong>
                        )}
                      </li>
                    ))}
                  </ul>
                </Card>
              ))}
            </div>
            <Link to={pourParent ? "/tuteur/passeport" : "/eleve/passeport"} style={{ textDecoration: "none", display: "block", marginTop: "12px" }}>
              <Card hover style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <Award size={20} style={{ color: "var(--reward-deep)", flexShrink: 0 }} />
                <span style={{ flex: 1, fontSize: "var(--text-sm)", color: "var(--ink)" }}>
                  {pourParent
                    ? `Le passeport de compétences suit les moyennes de ${prenom ?? "votre enfant"} sur toute l'année.`
                    : "Votre passeport de compétences suit vos moyennes par matière sur toute l'année."}
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
