import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  candidaturesDuPoste,
  candidaturesEnAttenteRevision,
  creerContrat,
  creerPoste,
  listerContratsEtablissement,
  listerPostes,
  noterDocumentManuellement,
  obtenirLienDocumentCandidature,
  proposerReconduction,
} from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { CandidatureOut, ChampFormulaire, ContratAvecEnseignantOut, CritereDocument, PosteOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  SkeletonCard,
  SuccessBanner,
  TextArea,
  TextInput,
} from "../../components/ui";
import { FormulaireBuilder } from "../../components/FormulaireBuilder";
import { Briefcase, ExternalLink, FileSignature, FileWarning, Plus, RefreshCw, Trash2, Users } from "lucide-react";
import { estRempli, erreurDateFuture } from "../../utils/validation";

const RECONDUCTION_FENETRE_JOURS = 30;

function dansLaFenetreDeReconduction(dateFin: string): boolean {
  const jours = Math.ceil((new Date(dateFin).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  return jours <= RECONDUCTION_FENETRE_JOURS;
}

const TONE_CANDIDATURE: Record<CandidatureOut["statut"], "success" | "error" | "pending"> = {
  retenue: "success",
  rejetee: "error",
  en_evaluation: "pending",
};

export function RecrutementPage() {
  const etablissement = useAdminEtab();
  const [postes, setPostes] = useState<PosteOut[]>([]);
  const [enRevision, setEnRevision] = useState<CandidatureOut[]>([]);
  const [contrats, setContrats] = useState<ContratAvecEnseignantOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [titre, setTitre] = useState("");
  const [description, setDescription] = useState("");
  const [matiere, setMatiere] = useState("");
  const [remunerationMin, setRemunerationMin] = useState("");
  const [remunerationMax, setRemunerationMax] = useState("");
  const [schemaFormulaire, setSchemaFormulaire] = useState<ChampFormulaire[]>([]);
  const [criteres, setCriteres] = useState<CritereDocument[]>([
    { type_document: "cv", coefficient: 1, seuil_minimal: 60 },
  ]);
  const [notesParDocument, setNotesParDocument] = useState<Record<string, number>>({});
  const [posteSelectionne, setPosteSelectionne] = useState<string | null>(null);
  const [candidaturesPoste, setCandidaturesPoste] = useState<CandidatureOut[]>([]);
  const [chargementCandidatures, setChargementCandidatures] = useState(false);
  const [syllabusParCandidature, setSyllabusParCandidature] = useState<Record<string, string>>({});
  const [dateFinParCandidature, setDateFinParCandidature] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [lienEnCoursId, setLienEnCoursId] = useState<string | null>(null);
  const [titreErreur, setTitreErreur] = useState<string | null>(null);
  const [criteresErreurs, setCriteresErreurs] = useState<Record<number, string>>({});
  const [reconductionOuvertePour, setReconductionOuvertePour] = useState<string | null>(null);
  const [syllabusReconduction, setSyllabusReconduction] = useState("");
  const [dateFinReconduction, setDateFinReconduction] = useState("");
  const [enCoursReconduction, setEnCoursReconduction] = useState(false);
  const [succesReconduction, setSuccesReconduction] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    Promise.all([listerPostes(etablissement.id), candidaturesEnAttenteRevision(), listerContratsEtablissement(etablissement.id)])
      .then(([resPostes, resRevision, resContrats]) => {
        setPostes(resPostes.data);
        setEnRevision(resRevision.data);
        setContrats(resContrats.data);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const ajouterCritere = () => {
    setCriteres((prev) => [...prev, { type_document: "", coefficient: 1, seuil_minimal: 60 }]);
  };

  const retirerCritere = (i: number) => {
    setCriteres((prev) => prev.filter((_, idx) => idx !== i));
  };

  const majCritere = (i: number, champ: keyof CritereDocument, valeur: string) => {
    setCriteres((prev) =>
      prev.map((c, idx) =>
        idx === i ? { ...c, [champ]: champ === "type_document" ? valeur : Number(valeur) } : c,
      ),
    );
  };

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setTitreErreur(null);

    let titreValide = true;
    if (!estRempli(titre)) {
      setTitreErreur("Titre du poste requis.");
      titreValide = false;
    }

    const erreursCriteres: Record<number, string> = {};
    criteres.forEach((c, i) => {
      if (!estRempli(c.type_document)) {
        erreursCriteres[i] = "Type de document requis.";
      } else if (!Number.isFinite(c.coefficient) || c.coefficient <= 0) {
        erreursCriteres[i] = "Coefficient requis (supérieur à 0).";
      } else if (!Number.isFinite(c.seuil_minimal) || c.seuil_minimal < 0 || c.seuil_minimal > 100) {
        erreursCriteres[i] = "Seuil minimal entre 0 et 100.";
      }
    });
    setCriteresErreurs(erreursCriteres);

    if (!titreValide || Object.keys(erreursCriteres).length > 0) return;

    setEnCours(true);
    try {
      await creerPoste(etablissement.id, {
        titre,
        description: description || undefined,
        matiere: matiere || undefined,
        remuneration_min: remunerationMin ? Number(remunerationMin) : undefined,
        remuneration_max: remunerationMax ? Number(remunerationMax) : undefined,
        schema_formulaire: schemaFormulaire.filter((c) => c.label.trim()).length > 0
          ? schemaFormulaire.filter((c) => c.label.trim())
          : undefined,
        criteres,
      });
      setTitre("");
      setDescription("");
      setMatiere("");
      setRemunerationMin("");
      setRemunerationMax("");
      setSchemaFormulaire([]);
      setCriteres([{ type_document: "cv", coefficient: 1, seuil_minimal: 60 }]);
      setCriteresErreurs({});
      setShowForm(false);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le poste."));
    } finally {
      setEnCours(false);
    }
  };

  const noter = async (documentId: string) => {
    const note = notesParDocument[documentId];
    if (note === undefined || !Number.isFinite(note)) {
      setErreur("Veuillez indiquer une note avant de valider.");
      return;
    }
    if (note < 0 || note > 100) {
      setErreur("La note doit être comprise entre 0 et 100.");
      return;
    }
    setErreur(null);
    try {
      await noterDocumentManuellement(documentId, note);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const voirDocument = async (documentId: string) => {
    setLienEnCoursId(documentId);
    setErreur(null);
    try {
      const res = await obtenirLienDocumentCandidature(documentId);
      window.open(res.data.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'ouvrir ce document pour le moment."));
    } finally {
      setLienEnCoursId(null);
    }
  };

  const voirCandidatures = (posteId: string) => {
    setPosteSelectionne(posteId);
    setChargementCandidatures(true);
    candidaturesDuPoste(posteId)
      .then((res) => setCandidaturesPoste(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargementCandidatures(false));
  };

  const creerLeContrat = async (candidatureId: string) => {
    const syllabus = syllabusParCandidature[candidatureId];
    const dateFin = dateFinParCandidature[candidatureId];
    if (!syllabus?.trim() || !dateFin) {
      setErreur("Veuillez renseigner le syllabus et la date de fin avant de créer le contrat.");
      return;
    }
    const erreurDate = erreurDateFuture(dateFin);
    if (erreurDate) {
      setErreur(`Date de fin invalide : ${erreurDate}`);
      return;
    }
    setErreur(null);
    try {
      await creerContrat(candidatureId, syllabus, dateFin);
      if (posteSelectionne) voirCandidatures(posteSelectionne);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le contrat."));
    }
  };

  const ouvrirReconduction = (contratId: string) => {
    setReconductionOuvertePour((prev) => (prev === contratId ? null : contratId));
    setSyllabusReconduction("");
    setDateFinReconduction("");
    setErreur(null);
    setSuccesReconduction(null);
  };

  const proposerLaReconduction = async (contratId: string) => {
    if (!syllabusReconduction.trim() || !dateFinReconduction) {
      setErreur("Veuillez renseigner le syllabus et la nouvelle date de fin avant de proposer la reconduction.");
      return;
    }
    const erreurDate = erreurDateFuture(dateFinReconduction);
    if (erreurDate) {
      setErreur(`Date de fin invalide : ${erreurDate}`);
      return;
    }
    setErreur(null);
    setEnCoursReconduction(true);
    try {
      await proposerReconduction(contratId, syllabusReconduction, dateFinReconduction);
      setSuccesReconduction("Reconduction proposée : l'enseignant peut désormais la signer depuis son espace contrats.");
      setReconductionOuvertePour(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de proposer cette reconduction."));
    } finally {
      setEnCoursReconduction(false);
    }
  };

  return (
    <div className="page-content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <PageTitle eyebrow="Espace établissement">Recrutement</PageTitle>
        <Btn variant="primary" leftIcon={<Plus size={16} />} onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "Ouvrir un poste"}
        </Btn>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>

      {showForm && (
        <Card className="mb-8 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
          <SectionHead title="Ouvrir un nouveau poste" desc="Chaque critère de document sera noté sur 100 par l'IA à la candidature." />
          <form onSubmit={soumettre} noValidate className="space-y-4" style={{ marginTop: "var(--space-4)" }}>
            <Field label="Titre du poste" required error={titreErreur}>
              <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} placeholder="Ex. Professeur de mathématiques" />
            </Field>
            <Field label="Description">
              <TextArea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Détails de l'annonce, missions, profil recherché..." />
            </Field>
            <div className="grid-3">
              <Field label="Matière recherchée">
                <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} placeholder="Ex. Mathématiques" />
              </Field>
              <Field label="Rémunération min.">
                <TextInput type="number" value={remunerationMin} onChange={(e) => setRemunerationMin(e.target.value)} />
              </Field>
              <Field label="Rémunération max. (optionnel)">
                <TextInput type="number" value={remunerationMax} onChange={(e) => setRemunerationMax(e.target.value)} />
              </Field>
            </div>
            <div className="space-y-3">
              <span className="text-eyebrow">Formulaire de candidature (optionnel)</span>
              <p className="text-sm" style={{ color: "var(--ink-soft)", margin: 0 }}>
                Champs supplémentaires demandés au candidat, en plus des documents notés par l'IA ci-dessous.
              </p>
              <FormulaireBuilder champs={schemaFormulaire} onChange={setSchemaFormulaire} />
            </div>
            <div className="space-y-3">
              <span className="text-eyebrow">Critères de document</span>
              {criteres.map((c, i) => (
                <div key={i} style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end", flexWrap: "wrap" }}>
                  <Field label="Type de document" error={criteresErreurs[i]}>
                    <TextInput value={c.type_document} onChange={(e) => majCritere(i, "type_document", e.target.value)} />
                  </Field>
                  <Field label="Coefficient">
                    <TextInput type="number" step="0.1" value={c.coefficient} onChange={(e) => majCritere(i, "coefficient", e.target.value)} style={{ width: "90px" }} />
                  </Field>
                  <Field label="Seuil minimal">
                    <TextInput type="number" value={c.seuil_minimal} onChange={(e) => majCritere(i, "seuil_minimal", e.target.value)} style={{ width: "90px" }} />
                  </Field>
                  {criteres.length > 1 && (
                    <Btn type="button" variant="ghost" size="sm" onClick={() => retirerCritere(i)} aria-label="Retirer ce critère">
                      <Trash2 size={16} />
                    </Btn>
                  )}
                </div>
              ))}
              <Btn type="button" variant="outline" size="sm" onClick={ajouterCritere}>
                + Ajouter un critère
              </Btn>
            </div>
            <Btn type="submit" variant="primary" loading={enCours}>
              Ouvrir le poste
            </Btn>
          </form>
        </Card>
      )}

      {chargement ? (
        <div className="grid-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : (
        <>
          <SectionHead title="Postes de l'établissement" />
          {postes.length === 0 ? (
            <EmptyState
              icon={<Briefcase size={24} />}
              title="Aucun poste ouvert"
              desc="Ouvrez un poste pour commencer à recevoir des candidatures."
            />
          ) : (
            <div className="space-y-3 mb-8">
              {postes.map((p) => (
                <Card key={p.id} hover={posteSelectionne !== p.id} onClick={() => voirCandidatures(p.id)}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)", flexWrap: "wrap" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                      <Briefcase size={18} style={{ color: "var(--primary-deep)" }} aria-hidden="true" />
                      <span style={{ fontWeight: 600, color: "var(--ink)" }}>{p.titre}</span>
                    </div>
                    <Badge tone={p.statut === "ouvert" ? "success" : p.statut === "non_pourvu" ? "error" : "neutral"}>
                      {p.statut === "ouvert" ? "Ouvert" : p.statut === "pourvu" ? "Pourvu" : "Non pourvu"}
                    </Badge>
                  </div>

                  {posteSelectionne === p.id && (
                    <div className="anim-slide-up" style={{ marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px dashed var(--border)" }} onClick={(e) => e.stopPropagation()}>
                      {chargementCandidatures ? (
                        <SkeletonCard />
                      ) : candidaturesPoste.length === 0 ? (
                        <EmptyState icon={<Users size={20} />} title="Aucune candidature pour l'instant" />
                      ) : (
                        <div className="space-y-3">
                          {candidaturesPoste.map((c) => (
                            <div key={c.id} style={{ background: "var(--surface-2)", borderRadius: "var(--radius-md)", padding: "var(--space-4)" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-2)", marginBottom: "var(--space-2)" }}>
                                <span style={{ fontWeight: 600, color: "var(--ink)" }}>
                                  {c.enseignant_prenom} {c.enseignant_nom}
                                </span>
                                <Badge tone={TONE_CANDIDATURE[c.statut]}>
                                  {c.statut === "en_evaluation" ? "En évaluation" : c.statut === "retenue" ? "Retenue" : "Rejetée"}
                                  {c.score !== null ? ` — ${c.score.toFixed(1)}/100` : ""}
                                </Badge>
                              </div>
                              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "var(--space-2)" }}>
                                {c.documents.map((d) => (
                                  <Btn
                                    key={d.id}
                                    variant="ghost"
                                    size="sm"
                                    disabled={!d.lulufiles_file_id}
                                    loading={lienEnCoursId === d.id}
                                    onClick={() => voirDocument(d.id)}
                                    rightIcon={<ExternalLink size={12} />}
                                  >
                                    {d.type_document} {d.note_ia !== null ? `(${d.note_ia}/100)` : "(en attente)"}
                                  </Btn>
                                ))}
                              </div>
                              {c.reponses_formulaire && Object.keys(c.reponses_formulaire).length > 0 && (
                                <div style={{ marginBottom: "var(--space-2)", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                                  {Object.entries(c.reponses_formulaire).map(([champ, valeur]) => (
                                    <div key={champ}>
                                      <strong>{champ}</strong> : {Array.isArray(valeur) ? valeur.join(", ") : String(valeur)}
                                    </div>
                                  ))}
                                </div>
                              )}
                              {c.statut === "en_evaluation" && c.score !== null && (
                                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: "var(--space-2)" }}>
                                  <Field label="Syllabus">
                                    <TextInput
                                      value={syllabusParCandidature[c.id] ?? ""}
                                      onChange={(e) => setSyllabusParCandidature((prev) => ({ ...prev, [c.id]: e.target.value }))}
                                    />
                                  </Field>
                                  <Field label="Date de fin">
                                    <TextInput
                                      type="date"
                                      value={dateFinParCandidature[c.id] ?? ""}
                                      onChange={(e) => setDateFinParCandidature((prev) => ({ ...prev, [c.id]: e.target.value }))}
                                    />
                                  </Field>
                                  <Btn variant="primary" size="sm" onClick={() => creerLeContrat(c.id)}>
                                    Créer le contrat
                                  </Btn>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}

          <SectionHead
            title="Contrats de l'établissement"
            desc="Un contrat signé peut être reconduit dans les 30 jours précédant son échéance."
          />
          {succesReconduction && <SuccessBanner>{succesReconduction}</SuccessBanner>}
          {contrats.length === 0 ? (
            <EmptyState icon={<FileSignature size={24} />} title="Aucun contrat pour l'instant" />
          ) : (
            <div className="space-y-3 mb-8">
              {contrats.map((c) => {
                const reconductible = c.statut === "signe" && dansLaFenetreDeReconduction(c.date_fin);
                return (
                  <Card key={c.id}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-3)", flexWrap: "wrap" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
                        <FileSignature size={18} style={{ color: "var(--primary-deep)" }} aria-hidden="true" />
                        <span style={{ fontWeight: 600, color: "var(--ink)" }}>
                          {c.enseignant_prenom} {c.enseignant_nom}
                        </span>
                        <span style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)" }}>
                          Échéance : {new Date(c.date_fin).toLocaleDateString("fr-FR")}
                        </span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                        <Badge tone={c.statut === "signe" ? "success" : "pending"}>
                          {c.statut === "signe" ? "Signé" : "En attente de signature"}
                        </Badge>
                        {reconductible && (
                          <Btn
                            variant="outline"
                            size="sm"
                            leftIcon={<RefreshCw size={14} />}
                            onClick={() => ouvrirReconduction(c.id)}
                          >
                            {reconductionOuvertePour === c.id ? "Annuler" : "Proposer une reconduction"}
                          </Btn>
                        )}
                      </div>
                    </div>
                    {reconductionOuvertePour === c.id && (
                      <div
                        className="anim-slide-up"
                        style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: "var(--space-2)", marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px dashed var(--border)" }}
                      >
                        <Field label="Nouveau syllabus">
                          <TextInput value={syllabusReconduction} onChange={(e) => setSyllabusReconduction(e.target.value)} />
                        </Field>
                        <Field label="Nouvelle date de fin">
                          <TextInput type="date" value={dateFinReconduction} onChange={(e) => setDateFinReconduction(e.target.value)} />
                        </Field>
                        <Btn variant="primary" size="sm" loading={enCoursReconduction} onClick={() => proposerLaReconduction(c.id)}>
                          Envoyer la proposition
                        </Btn>
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}

          {enRevision.length > 0 && (
            <>
              <SectionHead title="Révision manuelle requise" desc="L'IA n'a pas pu noter ces documents — une notation manuelle est nécessaire." />
              <div className="space-y-3">
                {enRevision.map((c) =>
                  c.documents
                    .filter((d) => d.statut === "echec_notation")
                    .map((d) => (
                      <Card key={d.id} style={{ borderColor: "var(--action-tint)" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                            <FileWarning size={18} style={{ color: "var(--action-deep)" }} aria-hidden="true" />
                            <span style={{ color: "var(--ink)" }}>
                              <strong>{c.enseignant_prenom} {c.enseignant_nom}</strong> — document {d.type_document}
                            </span>
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                            <Btn
                              variant="ghost"
                              size="sm"
                              disabled={!d.lulufiles_file_id}
                              loading={lienEnCoursId === d.id}
                              onClick={() => voirDocument(d.id)}
                              rightIcon={<ExternalLink size={12} />}
                            >
                              Voir le document
                            </Btn>
                            <TextInput
                              type="number"
                              min={0}
                              max={100}
                              placeholder="Note /100"
                              style={{ width: "100px" }}
                              value={notesParDocument[d.id] ?? ""}
                              onChange={(e) => setNotesParDocument((prev) => ({ ...prev, [d.id]: Number(e.target.value) }))}
                            />
                            <Btn variant="action" size="sm" onClick={() => noter(d.id)}>
                              Valider la note
                            </Btn>
                          </div>
                        </div>
                      </Card>
                    )),
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
