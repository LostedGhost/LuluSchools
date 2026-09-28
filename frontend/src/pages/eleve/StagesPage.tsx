import { useEffect, useState } from "react";
import { Briefcase, CalendarClock, MapPin } from "lucide-react";
import { messageErreur } from "../../api/client";
import { candidaterStage, offresPourMoi, type OffreStage } from "../../api/insertion";
import { Modale } from "../../components/Modale";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Skeleton, SuccessBanner, TextArea } from "../../components/ui";

/* Lot 7.8 — offres de stage des entreprises partenaires de l'établissement
   (PAG : programme de stages au profit des jeunes, EFTP). */

const STATUTS = {
  envoyee: { texte: "Candidature envoyée", ton: "pending" },
  retenue: { texte: "Retenue", ton: "success" },
  non_retenue: { texte: "Non retenue", ton: "neutral" },
} as const;

export function StagesPage() {
  const [offres, setOffres] = useState<OffreStage[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [cible, setCible] = useState<OffreStage | null>(null);
  const [message, setMessage] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const charger = () => {
    offresPourMoi().then((r) => setOffres(r.data)).catch((err) => setErreur(messageErreur(err)));
  };
  useEffect(charger, []);

  const envoyer = async () => {
    if (!cible) return;
    setEnvoi(true);
    setErreur(null);
    try {
      await candidaterStage(cible.id, message.trim());
      setSucces(`Candidature envoyée à ${cible.entreprise}. L'établissement vous tiendra informé.`);
      setCible(null);
      setMessage("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Insertion"
        title="Stages"
        desc="Offres d'entreprises partenaires de votre établissement. Votre établissement transmet votre candidature et vous annonce la réponse."
      />
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>
      {!offres ? (
        <Skeleton height="180px" />
      ) : offres.length === 0 ? (
        <EmptyState icon={<Briefcase size={28} />} title="Aucune offre ouverte" desc="Revenez bientôt : votre établissement publie les offres au fil de l'année." />
      ) : (
        <div className="grid-2">
          {offres.map((o) => (
            <Card key={o.id}>
              <p className="text-eyebrow" style={{ margin: 0 }}>{o.entreprise}</p>
              <h2 className="text-title" style={{ margin: "4px 0 8px" }}>{o.intitule}</h2>
              <p style={{ margin: "0 0 10px", color: "var(--ink-soft)" }}>{o.description}</p>
              <p style={{ display: "flex", gap: "14px", flexWrap: "wrap", margin: "0 0 12px", fontSize: "var(--text-sm)" }}>
                <span className="stage-meta"><MapPin size={14} aria-hidden="true" /> {o.lieu}</span>
                <span className="stage-meta">{o.duree_semaines} semaines</span>
                <span className="stage-meta"><CalendarClock size={14} aria-hidden="true" /> Jusqu'au {new Date(o.date_limite).toLocaleDateString("fr-FR")}</span>
              </p>
              {o.ma_candidature ? (
                <Badge tone={STATUTS[o.ma_candidature].ton}>{STATUTS[o.ma_candidature].texte}</Badge>
              ) : (
                <Btn variant="primary" onClick={() => setCible(o)}>Postuler</Btn>
              )}
            </Card>
          ))}
        </div>
      )}
      <Modale
        ouvert={!!cible}
        titre={cible ? `Postuler — ${cible.intitule}` : ""}
        onFermer={() => setCible(null)}
        pied={
          <>
            <Btn variant="ghost" onClick={() => setCible(null)}>Annuler</Btn>
            <Btn variant="primary" onClick={envoyer} loading={envoi} disabled={message.trim().length < 10}>Envoyer</Btn>
          </>
        }
      >
        <Field label="Votre message à l'entreprise" required helper="Pourquoi ce stage vous intéresse, ce que vous savez déjà faire (10 caractères au moins).">
          <TextArea rows={5} value={message} onChange={(e) => setMessage(e.target.value)} />
        </Field>
      </Modale>
    </div>
  );
}
