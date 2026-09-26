import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { consulterVieScolaire } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { VieScolaireOut } from "../../types/api";
import { Badge, Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, SkeletonCard, TextInput } from "../../components/ui";
import { Search, User } from "lucide-react";

const TONE_STATUT: Record<string, "success" | "pending" | "error"> = {
  validee: "success",
  soumise: "pending",
  en_attente_consentement_parental: "pending",
  rejetee: "error",
};

/**
 * UC-41/42/57 (lot admin etablissement) : le dossier complet d'un eleve/etudiant n'est
 * accessible que si l'etablissement a deja recu au moins une Inscription de sa part
 * (verifie serveur, voir GET /eleves/{id}/vie-scolaire) - droit de lecture permanent une
 * fois acquis, meme si la demande a ete rejetee ou concerne une autre annee.
 */
export function VieScolairePage() {
  const { eleveUtilisateurId } = useParams<{ eleveUtilisateurId?: string }>();
  const navigate = useNavigate();
  const [idRecherche, setIdRecherche] = useState(eleveUtilisateurId ?? "");
  const [dossier, setDossier] = useState<VieScolaireOut | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const rechercher = (id: string) => {
    if (!id.trim()) return;
    setChargement(true);
    setErreur(null);
    setDossier(null);
    consulterVieScolaire(id.trim())
      .then((res) => setDossier(res.data))
      .catch((err) => setErreur(messageErreur(err, "Impossible de consulter ce dossier.")))
      .finally(() => setChargement(false));
  };

  useEffect(() => {
    if (eleveUtilisateurId) rechercher(eleveUtilisateurId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eleveUtilisateurId]);

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Établissement">Vie scolaire</PageTitle>
      <p className="text-sm" style={{ color: "var(--ink-soft)", marginBottom: "var(--space-4)" }}>
        Historique complet d'un élève/étudiant — accessible dès que votre établissement a reçu au moins une demande d'inscription de sa part, même rejetée ou d'une autre année.
      </p>

      <Card className="mb-6">
        <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-end", flexWrap: "wrap" }}>
          <Field label="Identifiant utilisateur de l'élève" helper="Accessible depuis la fiche d'une demande d'inscription.">
            <TextInput
              value={idRecherche}
              onChange={(e) => setIdRecherche(e.target.value)}
              placeholder="UUID de l'élève"
              style={{ minWidth: "320px" }}
            />
          </Field>
          <Btn
            variant="primary"
            loading={chargement}
            leftIcon={<Search size={16} />}
            onClick={() => navigate(`/admin-etablissement/vie-scolaire/${idRecherche.trim()}`)}
          >
            Consulter
          </Btn>
        </div>
      </Card>

      <ErrorBanner>{erreur}</ErrorBanner>

      {chargement && <SkeletonCard />}

      {dossier && (
        <>
          <Card className="mb-6" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
            <div style={{ display: "flex", gap: "var(--space-4)", alignItems: "center" }}>
              {dossier.photo_url ? (
                <img
                  src={dossier.photo_url}
                  alt=""
                  style={{ width: "72px", height: "72px", borderRadius: "var(--radius-md)", objectFit: "cover" }}
                />
              ) : (
                <div
                  style={{
                    width: "72px", height: "72px", borderRadius: "var(--radius-md)", background: "var(--primary-tint)",
                    display: "flex", alignItems: "center", justifyContent: "center", color: "var(--primary-deep)",
                  }}
                >
                  <User size={28} />
                </div>
              )}
              <div>
                <h2 className="text-title" style={{ margin: "0 0 4px" }}>{dossier.prenom} {dossier.nom}</h2>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {dossier.matricule && <Badge tone="neutral">{dossier.matricule}</Badge>}
                  <Badge tone={dossier.est_etudiant ? "magic" : "info"}>{dossier.est_etudiant ? "Étudiant" : "Élève"}</Badge>
                </div>
              </div>
            </div>
          </Card>

          <SectionHead title="Inscriptions" desc="Tous établissements et années confondus." />
          <div className="space-y-3 mb-8">
            {dossier.inscriptions.map((i) => (
              <Card key={i.id}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)" }}>
                  <div>
                    <strong style={{ color: "var(--ink)" }}>{i.etablissement_nom}</strong>
                    <span className="text-sm" style={{ color: "var(--ink-soft)", marginLeft: "8px" }}>
                      {i.classe_niveau}{i.classe_filiere ? ` ${i.classe_filiere}` : ""} — {i.annee_academique}
                    </span>
                  </div>
                  <Badge tone={TONE_STATUT[i.statut] ?? "neutral"}>{i.statut}</Badge>
                </div>
              </Card>
            ))}
          </div>

          <SectionHead title="Bulletins" />
          <div className="space-y-3">
            {dossier.bulletins.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--ink-faint)" }}>Aucun bulletin disponible.</p>
            ) : (
              dossier.bulletins.map((b, idx) => (
                <Card key={idx}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)" }}>
                    <div>
                      <strong style={{ color: "var(--ink)" }}>{b.etablissement_nom}</strong>
                      <span className="text-sm" style={{ color: "var(--ink-soft)", marginLeft: "8px" }}>{b.periode}</span>
                    </div>
                    <span className="monospace" style={{ fontWeight: 700, color: "var(--primary-deep)" }}>
                      {b.moyenne_generale.toFixed(2)}/20 {b.decision_passage ? `— ${b.decision_passage}` : ""}
                    </span>
                  </div>
                </Card>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
