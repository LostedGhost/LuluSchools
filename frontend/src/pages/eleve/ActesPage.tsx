import { useEffect, useState, type FormEvent } from "react";
import {
  amorcerPaiement,
  listerTypesActes,
  mesDemandesActes,
  obtenirLienDocumentActe,
  soumettreDemandeActe,
  televerserPieceJointeActe,
} from "../../api/actes";
import { messageErreur } from "../../api/client";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import type { DemandeActeOut, StatutDemandeActe, TypeActeOut } from "../../types/api";
import { Badge, Card, ErrorBanner, Field, Select, TextArea, TextInput, Btn, EmptyState } from "../../components/ui";
import { KkiapayButton } from "../../components/KkiapayButton";
import { FormulaireDynamique, champsFichierDe } from "../../components/FormulaireDynamique";
import { Download, FileStack, FlagTriangleRight, ScrollText, Upload } from "lucide-react";
import { estRempli } from "../../utils/validation";
import { eligibiliteBourseScientifique, type EligibiliteBourse } from "../../api/insertion";

const LIBELLES_STATUT: Record<StatutDemandeActe, { label: string; tone: "neutral" | "success" | "error" | "pending" | "info" }> = {
  soumise: { label: "En attente de paiement", tone: "pending" },
  en_traitement: { label: "En traitement", tone: "info" },
  acceptee: { label: "Acceptée", tone: "success" },
  rejetee: { label: "Rejetée", tone: "error" },
};

export function ActesPage() {
  const profil = useEleveProfil();
  const [types, setTypes] = useState<TypeActeOut[]>([]);
  const [demandes, setDemandes] = useState<DemandeActeOut[]>([]);
  const [mode, setMode] = useState<"catalogue" | "reclamation">("catalogue");
  const [typeActeId, setTypeActeId] = useState("");
  const [referenceEvaluation, setReferenceEvaluation] = useState("");
  const [motif, setMotif] = useState("");
  const [reponsesFormulaire, setReponsesFormulaire] = useState<Record<string, string | string[]>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [champErreurs, setChampErreurs] = useState<{ typeActeId?: string; referenceEvaluation?: string; motif?: string }>({});
  const [televersementEnCours, setTeleversementEnCours] = useState<string | null>(null);
  const [lienEnCoursId, setLienEnCoursId] = useState<string | null>(null);

  const charger = () => {
    mesDemandesActes()
      .then((res) => setDemandes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(() => {
    if (profil.etablissement_id) {
      listerTypesActes(profil.etablissement_id)
        .then((res) => setTypes(res.data))
        .catch((err) => setErreur(messageErreur(err)));
    }
    charger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profil.etablissement_id]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);

    const erreurs: typeof champErreurs = {};
    if (mode === "catalogue") {
      if (!estRempli(typeActeId)) erreurs.typeActeId = "Veuillez choisir un type d'acte.";
    } else {
      if (!estRempli(referenceEvaluation)) erreurs.referenceEvaluation = "Référence requise.";
      if (!estRempli(motif) || motif.trim().length < 10) {
        erreurs.motif = "Veuillez détailler le motif (10 caractères minimum).";
      }
    }
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      if (mode === "catalogue") {
        await soumettreDemandeActe({
          type_acte_id: typeActeId,
          reponses_formulaire: Object.keys(reponsesFormulaire).length > 0 ? reponsesFormulaire : undefined,
        });
      } else {
        await soumettreDemandeActe({ est_reclamation: true, reference_evaluation: referenceEvaluation, motif });
      }
      setTypeActeId("");
      setReferenceEvaluation("");
      setMotif("");
      setReponsesFormulaire({});
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de soumettre la demande."));
    } finally {
      setEnCours(false);
    }
  };

  const payer = async (demandeId: string, transactionId: string) => {
    try {
      await amorcerPaiement(demandeId, transactionId);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const televerserPiece = async (demandeId: string, champId: string, fichier: File | undefined) => {
    if (!fichier) return;
    setTeleversementEnCours(`${demandeId}:${champId}`);
    setErreur(null);
    try {
      await televerserPieceJointeActe(demandeId, champId, fichier);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'envoyer cette pièce jointe."));
    } finally {
      setTeleversementEnCours(null);
    }
  };

  const telechargerDocument = async (demandeId: string) => {
    setLienEnCoursId(demandeId);
    setErreur(null);
    try {
      const res = await obtenirLienDocumentActe(demandeId);
      window.open(res.data.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setErreur(messageErreur(err, "Document pas encore disponible."));
    } finally {
      setLienEnCoursId(null);
    }
  };

  const typeSelectionne = types.find((t) => t.id === typeActeId);
  const estBourse = typeSelectionne?.critere_automatique === "bourse_scientifique";

  return (
    <div className="page-content">
      <div style={{ marginBottom: "32px" }}>
        <p className="text-eyebrow">Administration</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>Actes académiques</h1>
        <p style={{ color: "var(--ink-soft)", marginTop: "8px" }}>Gérez vos demandes d'actes et réclamations de notes.</p>
      </div>

      <div className="grid-2">
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          <h2 className="text-title">Mes demandes passées</h2>
          {demandes.length === 0 ? (
            <EmptyState icon={<FileStack size={24} />} title="Aucune demande" desc="Vous n'avez pas encore fait de demande." />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {demandes.map((demande, index) => {
                const statut = LIBELLES_STATUT[demande.statut];
                const type = types.find((t) => t.id === demande.type_acte_id);
                return (
                  <Card key={demande.id} className={`anim-slide-up delay-${(index % 5) + 1}`} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <span style={{ color: "var(--ink-faint)", display: "inline-flex" }} aria-hidden="true">
                          {demande.est_reclamation ? <FlagTriangleRight size={18} /> : <ScrollText size={18} />}
                        </span>
                        <p className="font-bold text-ink" style={{ margin: 0 }}>
                          {demande.est_reclamation ? "Réclamation de note" : type?.nom ?? "Acte académique"}
                        </p>
                      </div>
                      {demande.motif_rejet && <p className="text-sm" style={{ color: "var(--action-deep)" }}>Motif : {demande.motif_rejet}</p>}
                      {type && champsFichierDe(type.schema_formulaire ?? []).map((champ) => {
                        const dejaEnvoye = !!demande.reponses_formulaire?.[champ.id];
                        const cle = `${demande.id}:${champ.id}`;
                        return (
                          <div key={champ.id} style={{ marginTop: "6px" }}>
                            {dejaEnvoye ? (
                              <span className="text-sm" style={{ color: "var(--primary-deep)" }}>✓ {champ.label} envoyée</span>
                            ) : (
                              <>
                                <input
                                  type="file"
                                  id={`piece-${cle}`}
                                  style={{ display: "none" }}
                                  onChange={(e) => televerserPiece(demande.id, champ.id, e.target.files?.[0])}
                                />
                                <label htmlFor={`piece-${cle}`} className="btn btn-outline btn-sm" style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                                  <Upload size={12} /> {televersementEnCours === cle ? "Envoi..." : `Envoyer : ${champ.label}`}
                                </label>
                              </>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <Badge tone={statut.tone}>{statut.label}</Badge>
                      {demande.statut === "soumise" && !demande.paiement_confirme && type && (
                        <KkiapayButton
                          montant={type.prix}
                          typeRessource="acte"
                          reference={demande.id}
                          onSucces={(transactionId) => payer(demande.id, transactionId)}
                        />
                      )}
                      {demande.document_final_lulufiles_id && (
                        <Btn
                          variant="outline"
                          size="sm"
                          loading={lienEnCoursId === demande.id}
                          onClick={() => telechargerDocument(demande.id)}
                          leftIcon={<Download size={14} />}
                        >
                          Télécharger
                        </Btn>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        <div>
          <h2 className="text-title" style={{ marginBottom: "24px" }}>Nouvelle demande</h2>
          <Card variant="soft">
            <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
              <Btn
                variant={mode === "catalogue" ? "primary" : "ghost"}
                size="sm"
                onClick={() => setMode("catalogue")}
              >
                Demande d'acte
              </Btn>
              <Btn
                variant={mode === "reclamation" ? "primary" : "ghost"}
                size="sm"
                onClick={() => setMode("reclamation")}
              >
                Réclamation de note
              </Btn>
            </div>

            <form onSubmit={soumettre} noValidate style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {mode === "catalogue" ? (
                <Field label="Type d'acte" required error={champErreurs.typeActeId}>
                  <Select
                    value={typeActeId}
                    onChange={(e: any) => setTypeActeId(e.target.value)}
                  >
                    <option value="">Choisir...</option>
                    {types.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.nom} — {t.prix > 0 ? `${t.prix.toLocaleString("fr-FR")} FCFA` : "Gratuit"}
                      </option>
                    ))}
                  </Select>
                  {typeSelectionne && (
                    <p className="text-sm" style={{ color: "var(--ink-soft)", marginTop: "4px" }}>
                      Pièces requises : {typeSelectionne.pieces_requises}
                    </p>
                  )}
                  {estBourse && <EligibiliteBourseBandeau />}
                  {typeSelectionne?.schema_formulaire && typeSelectionne.schema_formulaire.length > 0 && (
                    <div style={{ marginTop: "12px" }}>
                      <FormulaireDynamique
                        champs={typeSelectionne.schema_formulaire}
                        valeurs={reponsesFormulaire}
                        onChange={(id, valeur) => setReponsesFormulaire((prev) => ({ ...prev, [id]: valeur }))}
                      />
                    </div>
                  )}
                </Field>
              ) : (
                <>
                  <Field label="Référence de l'évaluation contestée" required error={champErreurs.referenceEvaluation}>
                    <TextInput
                      value={referenceEvaluation}
                      onChange={(e: any) => setReferenceEvaluation(e.target.value)}
                      placeholder="ex: identifiant du devoir ou du bulletin"
                    />
                  </Field>
                  <Field label="Motif de la réclamation" required error={champErreurs.motif}>
                    <TextArea
                      value={motif}
                      onChange={(e: any) => setMotif(e.target.value)}
                    />
                  </Field>
                </>
              )}
              {erreur && <ErrorBanner>{erreur}</ErrorBanner>}
              <Btn variant="primary" size="md" loading={enCours} type="submit" style={{ width: "100%", marginTop: "8px" }}>
                Soumettre la demande
              </Btn>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}

/** Lot 7.8 : pré-contrôle de la bourse scientifique (la règle est revérifiée à l'envoi). */
function EligibiliteBourseBandeau() {
  const [resultat, setResultat] = useState<EligibiliteBourse | null>(null);
  useEffect(() => {
    eligibiliteBourseScientifique().then((r) => setResultat(r.data)).catch(() => {});
  }, []);
  if (!resultat) return null;
  return (
    <p
      role="status"
      style={{
        marginTop: "8px", padding: "10px 12px", borderRadius: "var(--radius-md)",
        background: resultat.eligible ? "var(--primary-tint)" : "var(--reward-tint, #FDF0DB)", color: "var(--ink)",
      }}
    >
      <strong>{resultat.eligible ? "Vous êtes éligible." : "Pas encore éligible."}</strong> {resultat.explication}
      {resultat.matieres.length > 0 && <> Matières prises en compte : {resultat.matieres.join(", ")}.</>}
    </p>
  );
}
