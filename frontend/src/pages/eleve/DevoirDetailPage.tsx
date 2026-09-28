import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { maSoumission, obtenirDevoir, obtenirLienSujetDocument, soumettreDevoirParCopieImage } from "../../api/evaluations";
import { envoyerOuMettreEnAttente } from "../../hors_ligne/fileAttente";
import { messageErreur } from "../../api/client";
import type { DevoirOut, SoumissionOut } from "../../types/api";
import {
  Badge,
  Card,
  ErrorBanner,
  Btn,
  TextArea,
  Field,
  Skeleton
} from "../../components/ui";
import { ScoreBurst, AIBadge, FloatingXPBadge } from "../../components/gamification";
import { ExternalLink, FileUp, Send } from "lucide-react";

const LIBELLES_STATUT: Record<string, { label: string; tone: "neutral" | "success" | "error" | "pending" }> = {
  en_correction: { label: "Correction en cours...", tone: "pending" },
  corrigee: { label: "Corrigé", tone: "success" },
  echec_correction: { label: "En révision par l'enseignant", tone: "error" },
};

export function DevoirDetailPage() {
  const { devoirId } = useParams<{ devoirId: string }>();
  const navigate = useNavigate();
  
  const [devoir, setDevoir] = useState<DevoirOut | null>(null);
  const [soumission, setSoumission] = useState<SoumissionOut | null | undefined>(undefined);
  const [reponses, setReponses] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [enAttente, setEnAttente] = useState(false);
  const [enCoursCopieImage, setEnCoursCopieImage] = useState(false);
  const [lienSujet, setLienSujet] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const chargerSoumission = () => {
    if (!devoirId) return;
    maSoumission(devoirId)
      .then((res) => setSoumission(res.data))
      .catch(() => setSoumission(null));
  };

  useEffect(() => {
    if (!devoirId) return;
    obtenirDevoir(devoirId)
      .then((res) => {
        setDevoir(res.data);
        if (res.data.sujet_lulufiles_file_id) {
          obtenirLienSujetDocument(devoirId)
            .then((lien) => setLienSujet(lien.data.url))
            .catch(() => undefined);
        }
      })
      .catch((err) => setErreur(messageErreur(err)));
    chargerSoumission();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [devoirId]);

  useEffect(() => {
    if (soumission?.statut === "en_correction") {
      pollRef.current = setInterval(chargerSoumission, 3000);
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [soumission?.statut]);

  const soumettreParPhoto = async (fichier: File | undefined) => {
    if (!devoirId || !fichier) return;
    setErreur(null);
    setEnCoursCopieImage(true);
    try {
      const { data } = await soumettreDevoirParCopieImage(devoirId, fichier);
      setSoumission(data);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre la photo de votre copie."));
    } finally {
      setEnCoursCopieImage(false);
    }
  };

  const soumettre = async () => {
    if (!devoir || !devoirId) return;
    if (devoir.questions.some((q) => !reponses[q.id]?.trim())) {
      setErreur("Veuillez répondre à toutes les questions.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      // Lot 7.5 : sans réseau, les réponses partent automatiquement au retour de la connexion.
      const resultat = await envoyerOuMettreEnAttente<SoumissionOut>(
        `/devoirs/${devoirId}/soumissions`,
        { reponses: devoir.questions.map((q) => ({ question_id: q.id, texte_reponse: reponses[q.id] })) },
        `Devoir « ${devoir.titre} »`,
      );
      if (resultat.statut === "envoye") setSoumission(resultat.data);
      else setEnAttente(true);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre le devoir."));
    } finally {
      setEnCours(false);
    }
  };

  if (!devoir) {
    return (
      <div className="page-content-narrow space-y-4">
        <Skeleton height="60px" width="70%" />
        <Skeleton height="300px" width="100%" />
      </div>
    );
  }

  const questionsTriees = [...devoir.questions].sort((a, b) => a.ordre - b.ordre);
  const dejaSoumis = soumission !== null && soumission !== undefined;

  return (
    <div className="page-content-narrow">
      <Btn variant="ghost" size="sm" onClick={() => navigate("/eleve/devoirs")} style={{ marginBottom: 'var(--space-4)' }}>
        ← Retour aux devoirs
      </Btn>

      <Card style={{ marginBottom: 'var(--space-6)', background: 'var(--surface-2)' }} className="anim-pop-in">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 className="text-headline" style={{ marginBottom: 'var(--space-2)' }}>{devoir.titre}</h1>
            <p className="text-label" style={{ color: 'var(--ink-soft)' }}>
              {devoir.matiere} — Échéance : {new Date(devoir.date_limite).toLocaleString("fr-FR")}
            </p>
            {lienSujet && (
              <a href={lienSujet} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "var(--text-sm)", marginTop: "6px" }}>
                <ExternalLink size={14} /> Voir le sujet (document)
              </a>
            )}
          </div>
          <FloatingXPBadge amount={150} label="Récompense" />
        </div>
      </Card>

      <ErrorBanner>{erreur}</ErrorBanner>
      {enAttente && (
        <p role="status" className="bandeau-hors-ligne" style={{ position: "static", borderRadius: "var(--radius-md)", marginBottom: "var(--space-4)" }}>
          Pas de connexion : vos réponses sont gardées sur ce téléphone et partiront toutes seules au retour du réseau.
        </p>
      )}

      {dejaSoumis && soumission && (
        <div className="anim-slide-up delay-1 space-y-6">
          <Card variant="soft">
            <h3 className="text-title" style={{ marginBottom: 'var(--space-4)' }}>Statut de la soumission</h3>
            <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'center' }}>
              <AIBadge status={soumission.statut === "corrigee" ? "done" : soumission.statut === "echec_correction" ? "error" : "pending"} />
              <Badge tone={LIBELLES_STATUT[soumission.statut].tone}>
                {LIBELLES_STATUT[soumission.statut].label}
              </Badge>
            </div>
          </Card>

          {soumission.note !== null && soumission.statut === "corrigee" && (
            <Card style={{ textAlign: 'center', padding: 'var(--space-6)', border: '1px solid color-mix(in srgb, var(--reward-deep) 30%, transparent)' }}>
              <ScoreBurst
                score={soumission.note}
                max={questionsTriees.reduce((total, q) => total + q.points_max, 0) || 20}
                label="Note finale"
                tone="success"
              />
            </Card>
          )}

          <Card>
            <h3 className="text-title" style={{ marginBottom: 'var(--space-4)' }}>Historique & Réponses</h3>
            {soumission.copie_image_lulufiles_file_id && (
              <p className="text-sm text-ink-soft italic" style={{ marginBottom: 'var(--space-4)' }}>
                Soumission par photo de copie - note globale, sans détail par question.
              </p>
            )}
            <div className="space-y-6">
              {questionsTriees.map((question, idx) => {
                const reponse = soumission.reponses.find((r) => r.question_id === question.id);
                return (
                  <div key={question.id} style={{ borderLeft: '4px solid var(--border)', paddingLeft: 'var(--space-3)' }}>
                    <p className="font-medium text-slate-700" style={{ marginBottom: 'var(--space-2)' }}>
                      Question {idx + 1} : {question.enonce}
                    </p>
                    <p className="text-sm" style={{ color: 'var(--ink-soft)', background: 'var(--surface-2)', padding: 'var(--space-2)', borderRadius: 'var(--radius-sm)' }}>
                      {reponse?.texte_reponse || "Aucune réponse fournie"}
                    </p>
                    {reponse?.points_obtenus !== null && reponse?.points_obtenus !== undefined && (
                      <p className="text-sm mt-2" style={{ color: 'var(--reward-deep)', fontWeight: 'bold' }}>
                        +{reponse.points_obtenus} / {question.points_max} pts
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {!dejaSoumis && (
        <Card className="anim-slide-up delay-1">
          <h2 className="text-title" style={{ marginBottom: 'var(--space-6)' }}>Rédige tes réponses</h2>
          <div className="space-y-6">
            {questionsTriees.map((question, idx) => (
              <Field key={question.id} label={`Question ${idx + 1} (${question.points_max} pts)`} required>
                <div style={{ marginBottom: 'var(--space-2)' }}>
                  <p className="text-sm font-medium">{question.enonce}</p>
                </div>
                <TextArea
                  rows={4}
                  value={reponses[question.id] ?? ""}
                  onChange={(e) => setReponses((prev) => ({ ...prev, [question.id]: e.target.value }))}
                  placeholder="Écris ta réponse ici..."
                />
                <div className="text-right text-xs" style={{ color: 'var(--ink-faint)', marginTop: 'var(--space-1)' }}>
                  {(reponses[question.id] || "").length} caractères
                </div>
              </Field>
            ))}

          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', margin: 'var(--space-6) 0' }}>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
            <span className="text-sm" style={{ color: 'var(--ink-faint)' }}>ou</span>
            <div style={{ flex: 1, height: '1px', background: 'var(--border)' }} />
          </div>

          <Field label="Soumettre une photo (ou un scan) de ta copie" helper="Alternative aux réponses ci-dessus : une seule note globale sera attribuée, sans détail par question.">
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
                border: '1.5px dashed var(--border-strong)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-4)',
                textAlign: 'center',
                background: 'var(--surface-2)',
                color: 'var(--ink-soft)',
                cursor: enCoursCopieImage ? 'wait' : 'pointer',
              }}
            >
              <FileUp size={18} aria-hidden="true" />
              {enCoursCopieImage ? "Envoi en cours..." : "Choisir une photo ou un PDF de ta copie"}
              <input
                type="file"
                accept="application/pdf,image/*"
                style={{ display: 'none' }}
                disabled={enCoursCopieImage}
                onChange={(e) => soumettreParPhoto(e.target.files?.[0])}
              />
            </label>
          </Field>
          
          <Btn 
            variant="action" 
            size="lg" 
            onClick={soumettre} 
            loading={enCours} 
            style={{ width: '100%', marginTop: 'var(--space-6)' }}
          >
            {enCours ? "Envoi en cours..." : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                <Send size={18} aria-hidden="true" /> Soumettre mon devoir
              </span>
            )}
          </Btn>
        </Card>
      )}
    </div>
  );
}
