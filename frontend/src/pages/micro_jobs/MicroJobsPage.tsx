import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/AuthContext";
import {
  accepterOffre,
  amorcerPaiementOffre,
  annulerOffre,
  contesterMission,
  creerOffre,
  declarerFinMission,
  listerOffres,
  mesMissions,
  obtenirOffre,
  validerMission,
} from "../../api/micro_jobs";
import { messageErreur } from "../../api/client";
import type { MissionMicroJobOut, OffreMicroJobOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  SectionHead,
  SkeletonCard,
  SuccessBanner,
  TextArea,
  TextInput,
} from "../../components/ui";
import { KkiapayButton } from "../../components/KkiapayButton";
import { Briefcase, Handshake } from "lucide-react";
import { estRempli } from "../../utils/validation";

const STATUT_MISSION_TONE: Record<MissionMicroJobOut["statut"], "pending" | "success" | "error" | "neutral" | "info"> = {
  en_cours: "pending",
  terminee_declaree: "info",
  validee: "success",
  contestee: "error",
  remboursee: "neutral",
  payee: "success",
};

const STATUT_MISSION_LABEL: Record<MissionMicroJobOut["statut"], string> = {
  en_cours: "En cours",
  terminee_declaree: "Terminée — en attente de validation",
  validee: "Validée",
  contestee: "Contestée",
  remboursee: "Remboursée",
  payee: "Prestataire payé",
};

export function MicroJobsPage() {
  const { utilisateur } = useAuth();
  const estEleve = utilisateur?.role === "eleve";
  const [offres, setOffres] = useState<OffreMicroJobOut[]>([]);
  const [missions, setMissions] = useState<MissionMicroJobOut[]>([]);
  const [offreParMission, setOffreParMission] = useState<Record<string, OffreMicroJobOut>>({});
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);
  const [motifContestationParId, setMotifContestationParId] = useState<Record<string, string>>({});

  const [showForm, setShowForm] = useState(false);
  const [titre, setTitre] = useState("");
  const [description, setDescription] = useState("");
  const [prix, setPrix] = useState("");
  const [enCoursCreation, setEnCoursCreation] = useState(false);
  const [offreEnAttentePaiement, setOffreEnAttentePaiement] = useState<OffreMicroJobOut | null>(null);

  const charger = () => {
    setChargement(true);
    Promise.all([listerOffres(), mesMissions()])
      .then(async ([resOffres, resMissions]) => {
        setOffres(resOffres.data);
        setMissions(resMissions.data);
        const connues = new Map<string, OffreMicroJobOut>();
        resOffres.data.forEach((o) => connues.set(o.id, o));
        const idsManquants = Array.from(new Set(resMissions.data.map((m) => m.offre_id))).filter((id) => !connues.has(id));
        const offresManquantes = await Promise.all(idsManquants.map((id) => obtenirOffre(id).then((r) => r.data)));
        offresManquantes.forEach((o) => connues.set(o.id, o));
        setOffreParMission(Object.fromEntries(connues));
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  const publierOffre = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(titre) || !estRempli(description) || !prix) {
      setErreur("Veuillez remplir tous les champs de l'offre.");
      return;
    }
    setErreur(null);
    setEnCoursCreation(true);
    try {
      const res = await creerOffre(titre.trim(), description.trim(), Number(prix));
      setTitre("");
      setDescription("");
      setPrix("");
      setShowForm(false);
      setOffreEnAttentePaiement(res.data);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de publier cette offre."));
    } finally {
      setEnCoursCreation(false);
    }
  };

  const payerOffre = async (offreId: string, transactionId: string) => {
    setActionEnCoursId(offreId);
    setErreur(null);
    try {
      await amorcerPaiementOffre(offreId, transactionId);
      setSucces("Paiement transmis. Votre offre sera visible sur la place de marché dès sa confirmation.");
      setOffreEnAttentePaiement(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer ce paiement."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const annulerOffreNonPayee = async (offreId: string) => {
    setActionEnCoursId(offreId);
    setErreur(null);
    try {
      await annulerOffre(offreId);
      setOffreEnAttentePaiement(null);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'annuler cette offre."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const accepter = async (offreId: string) => {
    setActionEnCoursId(offreId);
    setErreur(null);
    try {
      await accepterOffre(offreId);
      setSucces("Offre acceptée. Le paiement était déjà sécurisé par le client, vous pouvez commencer.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'accepter cette offre."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const declarerFin = async (missionId: string) => {
    setActionEnCoursId(missionId);
    setErreur(null);
    try {
      await declarerFinMission(missionId);
      setSucces("Fin de mission déclarée. Le client dispose de 5 jours pour valider ou contester.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de déclarer cette mission terminée."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const valider = async (missionId: string) => {
    setActionEnCoursId(missionId);
    setErreur(null);
    try {
      await validerMission(missionId);
      setSucces("Mission validée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const contester = async (missionId: string) => {
    if (!motifContestationParId[missionId]?.trim()) {
      setErreur("Veuillez détailler le motif de la contestation.");
      return;
    }
    setActionEnCoursId(missionId);
    setErreur(null);
    try {
      await contesterMission(missionId, motifContestationParId[missionId].trim());
      setSucces("Mission contestée, un agent ministériel va arbitrer le litige.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de contester cette mission."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  if (chargement) {
    return <div className="page-content"><SkeletonCard /></div>;
  }

  return (
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <SectionHead
          eyebrow="Place de marché"
          title="Micro-jobs entre membres de la communauté"
          desc="Publiez une demande et payez-la immédiatement : elle apparaît sur la place de marché dès le paiement confirmé, prête à être acceptée."
        />
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "+ Publier une demande"}
        </Btn>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {offreEnAttentePaiement && (
        <Card className="anim-pop-in" style={{ marginBottom: "24px", border: "1px solid color-mix(in srgb, var(--action-deep) 30%, transparent)", background: "var(--action-tint)" }}>
          <p style={{ margin: "0 0 4px", fontWeight: 700, color: "var(--action-deep)" }}>Paiement requis pour publier « {offreEnAttentePaiement.titre} »</p>
          <p style={{ margin: "0 0 12px", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
            Le montant est sécurisé (séquestre) jusqu'à ce qu'un prestataire termine et que vous validiez le travail. Tant que ce n'est pas payé, votre offre n'est visible de personne.
          </p>
          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <KkiapayButton
              montant={offreEnAttentePaiement.prix}
              reference={offreEnAttentePaiement.id}
              onSucces={(txId) => payerOffre(offreEnAttentePaiement.id, txId)}
              disabled={actionEnCoursId === offreEnAttentePaiement.id}
            />
            <Btn variant="ghost" size="sm" loading={actionEnCoursId === offreEnAttentePaiement.id} onClick={() => annulerOffreNonPayee(offreEnAttentePaiement.id)}>
              Annuler cette offre
            </Btn>
          </div>
        </Card>
      )}

      {showForm && (
        <Card className="anim-slide-up" style={{ marginBottom: "24px" }}>
          <form onSubmit={publierOffre} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <Field label="Titre de la demande" required>
              <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Ex. Cours particulier de maths, niveau 3ème" />
            </Field>
            <Field label="Description" required>
              <TextArea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <Field label="Prix (FCFA)" required helper="À payer immédiatement après publication pour rendre l'offre visible.">
              <TextInput type="number" min="0" value={prix} onChange={(e) => setPrix(e.target.value)} />
            </Field>
            <Btn type="submit" variant="primary" loading={enCoursCreation}>Publier et payer</Btn>
          </form>
        </Card>
      )}

      <div style={{ marginBottom: "32px" }}>
        <SectionHead title="Offres disponibles" desc="Paiement déjà confirmé — acceptez-en une pour être rémunéré une fois le travail validé." />
        {offres.length === 0 ? (
          <EmptyState icon={<Briefcase size={24} />} title="Aucune offre disponible" desc="Soyez le premier à publier une demande." />
        ) : (
          <div className="space-y-3">
            {offres.map((o) => (
              <Card key={o.id} className="anim-float-in">
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: "200px" }}>
                    <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{o.titre}</p>
                    <p style={{ margin: "2px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>{o.description}</p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <p style={{ margin: "0 0 8px", fontWeight: 700, color: "var(--primary-deep)" }}>{o.prix.toLocaleString("fr-FR")} FCFA</p>
                    {o.client_id === utilisateur?.id ? (
                      <Badge tone="info">Votre demande</Badge>
                    ) : estEleve ? (
                      <Badge tone="neutral">Réservé aux adultes</Badge>
                    ) : (
                      <Btn variant="primary" size="sm" loading={actionEnCoursId === o.id} onClick={() => accepter(o.id)} leftIcon={<Handshake size={14} />}>
                        Accepter
                      </Btn>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <SectionHead title="Mes missions" desc="En tant que client ou en tant que prestataire." />
        {missions.length === 0 ? (
          <EmptyState icon={<Handshake size={24} />} title="Aucune mission en cours" />
        ) : (
          <div className="space-y-3">
            {missions.map((m) => {
              const offre = offreParMission[m.offre_id];
              const estClient = offre?.client_id === utilisateur?.id;
              const estPrestataire = m.prestataire_id === utilisateur?.id;
              return (
                <Card key={m.id} className="anim-float-in">
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", marginBottom: "8px" }}>
                    <div>
                      <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{offre?.titre ?? "Mission"}</p>
                      <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
                        {estClient ? "Vous êtes le client" : "Vous êtes le prestataire"} — {m.prix_paye.toLocaleString("fr-FR")} FCFA
                      </p>
                    </div>
                    <Badge tone={STATUT_MISSION_TONE[m.statut]}>{STATUT_MISSION_LABEL[m.statut]}</Badge>
                  </div>

                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                    {estPrestataire && m.statut === "en_cours" && (
                      <Btn variant="primary" size="sm" loading={actionEnCoursId === m.id} onClick={() => declarerFin(m.id)}>
                        Déclarer la mission terminée
                      </Btn>
                    )}
                    {estClient && m.statut === "terminee_declaree" && (
                      <>
                        <Btn variant="primary" size="sm" loading={actionEnCoursId === m.id} onClick={() => valider(m.id)}>
                          Valider la mission
                        </Btn>
                        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                          <TextInput
                            placeholder="Motif de contestation"
                            value={motifContestationParId[m.id] ?? ""}
                            onChange={(e) => setMotifContestationParId((prev) => ({ ...prev, [m.id]: e.target.value }))}
                            style={{ minWidth: "200px" }}
                          />
                          <Btn variant="action" size="sm" loading={actionEnCoursId === m.id} onClick={() => contester(m.id)}>
                            Contester
                          </Btn>
                        </div>
                      </>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
