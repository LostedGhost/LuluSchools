import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "../../auth/AuthContext";
import {
  accepterOffre,
  amorcerPaiementMission,
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
      await creerOffre(titre.trim(), description.trim(), Number(prix));
      setTitre("");
      setDescription("");
      setPrix("");
      setShowForm(false);
      setSucces("Offre publiée sur la place de marché.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de publier cette offre."));
    } finally {
      setEnCoursCreation(false);
    }
  };

  const accepter = async (offreId: string) => {
    setActionEnCoursId(offreId);
    setErreur(null);
    try {
      await accepterOffre(offreId);
      setSucces("Offre acceptée. Procédez au paiement dans « Mes missions ».");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'accepter cette offre."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const payer = async (missionId: string, transactionId: string) => {
    setActionEnCoursId(missionId);
    setErreur(null);
    try {
      await amorcerPaiementMission(missionId, transactionId);
      setSucces("Paiement transmis, en cours de confirmation.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
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
        <SectionHead eyebrow="Place de marché" title="Micro-jobs entre membres de la communauté" />
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "+ Proposer un service"}
        </Btn>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {showForm && (
        <Card className="anim-slide-up" style={{ marginBottom: "24px" }}>
          <form onSubmit={publierOffre} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <Field label="Titre du service" required>
              <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Ex. Cours particulier de maths, niveau 3ème" />
            </Field>
            <Field label="Description" required>
              <TextArea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <Field label="Prix (FCFA)" required>
              <TextInput type="number" min="0" value={prix} onChange={(e) => setPrix(e.target.value)} />
            </Field>
            <Btn type="submit" variant="primary" loading={enCoursCreation}>Publier l'offre</Btn>
          </form>
        </Card>
      )}

      <div style={{ marginBottom: "32px" }}>
        <SectionHead title="Offres disponibles" />
        {offres.length === 0 ? (
          <EmptyState icon={<Briefcase size={24} />} title="Aucune offre disponible" desc="Soyez le premier à proposer un service." />
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
                    {o.prestataire_id !== utilisateur?.id && (
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
              const estClient = m.client_id === utilisateur?.id;
              const estPrestataire = offre?.prestataire_id === utilisateur?.id;
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
                    {estClient && m.statut === "en_cours" && !m.paiement_confirme && (
                      <KkiapayButton montant={m.prix_paye} reference={m.id} onSucces={(txId) => payer(m.id, txId)} disabled={actionEnCoursId === m.id} />
                    )}
                    {estPrestataire && m.statut === "en_cours" && m.paiement_confirme && (
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
