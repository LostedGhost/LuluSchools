import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { listerAlertesElProfessor, traiterAlerteElProfessor } from "../../api/el_professor_enseignant";
import { messageErreur } from "../../api/client";
import type { AlerteElProfessorOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, PageTitle, SectionHead, SkeletonCard } from "../../components/ui";
import { CheckCircle2, TriangleAlert } from "lucide-react";

/** Qui parlait à El Professor quand le signal a été détecté. */
const ORIGINES: Record<string, string> = {
  eleve: "Conversation d'un élève",
  enseignant: "Conversation d'un enseignant",
  tuteur: "Conversation d'un tuteur",
  famille: "Fil familial",
};

export function AlertesElProfessorPage() {
  const etablissement = useAdminEtab();
  const [alertes, setAlertes] = useState<AlerteElProfessorOut[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    listerAlertesElProfessor(etablissement.id)
      .then((res) => setAlertes(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const traiter = async (id: string) => {
    setActionEnCoursId(id);
    setErreur(null);
    try {
      await traiterAlerteElProfessor(id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const enAttente = alertes.filter((a) => !a.traite);
  const traitees = alertes.filter((a) => a.traite);

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Établissement">Alertes El Professor</PageTitle>
      <SectionHead
        title="Signaux de sécurité détectés"
        desc="El Professor prépare une alerte quand la conversation d'un enseignant avec l'assistant IA laisse apparaître un signal de danger (maltraitance, violence, détresse...). À traiter sans délai."
      />
      <div className="mb-6">
        <ErrorBanner>{erreur}</ErrorBanner>
      </div>

      {chargement ? (
        <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
      ) : alertes.length === 0 ? (
        <EmptyState icon={<TriangleAlert size={24} />} title="Aucune alerte" desc="Aucun signal de danger n'a été détecté pour le moment." />
      ) : (
        <div className="space-y-6">
          {enAttente.map((a) => (
            <Card key={a.id} style={{ border: "1px solid color-mix(in srgb, var(--action-deep) 40%, transparent)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", flexWrap: "wrap" }}>
                <TriangleAlert size={18} style={{ color: "var(--action-deep)" }} />
                <Badge tone="error">Non traitée</Badge>
                <Badge tone="info">{ORIGINES[a.origine] ?? a.origine}</Badge>
                <span style={{ fontSize: "var(--text-xs)", color: "var(--ink-faint)" }}>
                  {new Date(a.created_at).toLocaleString("fr-FR")}
                </span>
              </div>
              <p style={{ margin: "0 0 12px", fontSize: "var(--text-sm)" }}>{a.motif}</p>
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <Btn variant="action" loading={actionEnCoursId === a.id} onClick={() => traiter(a.id)} leftIcon={<CheckCircle2 size={14} />}>
                  Marquer comme traitée
                </Btn>
              </div>
            </Card>
          ))}
          {traitees.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>Traitées ({traitees.length})</p>
              {traitees.map((a) => (
                <Card key={a.id} variant="soft">
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Badge tone="success">Traitée</Badge>
                    <span style={{ fontSize: "var(--text-sm)" }}>{a.motif}</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
