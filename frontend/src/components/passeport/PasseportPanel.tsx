import { useState } from "react";
import { messageErreur } from "../../api/client";
import type { PasseportOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, SectionHead } from "../../components/ui";
import { Award, BookOpen, Download, Sparkles, Trophy } from "lucide-react";

export function PasseportPanel({
  passeport,
  exporter,
}: {
  passeport: PasseportOut;
  exporter: () => Promise<{ lien: string }>;
}) {
  const [exportEnCours, setExportEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const telecharger = async () => {
    setExportEnCours(true);
    setErreur(null);
    try {
      const { lien } = await exporter();
      window.open(lien, "_blank", "noopener,noreferrer");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de générer le PDF."));
    } finally {
      setExportEnCours(false);
    }
  };

  return (
    <div>
      <ErrorBanner>{erreur}</ErrorBanner>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "24px" }}>
        <h2 className="text-title" style={{ margin: 0 }}>
          {passeport.eleve_prenom} {passeport.eleve_nom}
        </h2>
        <Btn variant="primary" size="sm" loading={exportEnCours} leftIcon={<Download size={14} />} onClick={telecharger}>
          Exporter en PDF
        </Btn>
      </div>

      {passeport.badges.length > 0 && (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "24px" }}>
          {passeport.badges.map((badge) => (
            <Badge key={badge.id} tone="magic">
              <Sparkles size={12} style={{ marginRight: "4px" }} />
              {badge.label}
            </Badge>
          ))}
        </div>
      )}

      <SectionHead eyebrow="Résultats" title="Moyennes par matière" />
      {passeport.moyennes_par_matiere.length === 0 ? (
        <EmptyState icon={<Trophy size={20} />} title="Aucune moyenne disponible" />
      ) : (
        <div className="grid-3" style={{ marginBottom: "28px" }}>
          {passeport.moyennes_par_matiere.map((m) => (
            <Card key={m.matiere}>
              <p style={{ margin: "0 0 4px", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>{m.matiere}</p>
              <p style={{ margin: 0, fontWeight: 700, fontSize: "var(--text-lg)" }}>{m.moyenne.toFixed(1)}/100</p>
            </Card>
          ))}
        </div>
      )}

      {passeport.competences_metier && passeport.competences_metier.length > 0 && (
        <>
          <SectionHead eyebrow="Métier" title="Compétences professionnelles validées" />
          <div className="grid-3" style={{ marginBottom: "28px" }}>
            {passeport.competences_metier.map((c, i) => (
              <Card key={`${c.intitule}-${i}`}>
                <p style={{ margin: "0 0 4px", fontWeight: 700 }}>{c.intitule}</p>
                <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>Niveau : {c.niveau}</p>
              </Card>
            ))}
          </div>
        </>
      )}

      <SectionHead eyebrow="Progression" title="Quiz réussis" />
      {passeport.quiz_reussis.length === 0 ? (
        <EmptyState icon={<Award size={20} />} title="Aucun quiz réussi pour le moment" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "28px" }}>
          {passeport.quiz_reussis.map((q) => (
            <div key={q.quiz_id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
              <span style={{ fontSize: "var(--text-sm)" }}>
                {q.cours_titre} <span style={{ color: "var(--ink-faint)" }}>({q.cours_chapitre})</span>
              </span>
              <Badge tone="success">{q.score.toFixed(0)}%</Badge>
            </div>
          ))}
        </div>
      )}

      <SectionHead eyebrow="Historique" title="Cours suivis" />
      {passeport.cours_suivis.length === 0 ? (
        <EmptyState icon={<BookOpen size={20} />} title="Aucun cours enregistré" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {passeport.cours_suivis.map((c) => (
            <div key={c.id} className="card" style={{ fontSize: "var(--text-sm)" }}>
              {c.titre} <span style={{ color: "var(--ink-faint)" }}>({c.chapitre})</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
