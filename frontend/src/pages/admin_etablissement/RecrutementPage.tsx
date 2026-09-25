import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  candidaturesDuPoste,
  candidaturesEnAttenteRevision,
  creerContrat,
  creerPoste,
  listerPostes,
  noterDocumentManuellement,
  obtenirLienDocumentCandidature,
} from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { CandidatureOut, CritereDocument, PosteOut } from "../../types/api";
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
  TextInput,
} from "../../components/ui";
import { Briefcase, ExternalLink, FileWarning, Plus, Trash2, Users } from "lucide-react";
import { estRempli, erreurDateFuture } from "../../utils/validation";

const TONE_CANDIDATURE: Record<CandidatureOut["statut"], "success" | "error" | "pending"> = {
  retenue: "success",
  rejetee: "error",
  en_evaluation: "pending",
};

export function RecrutementPage() {
  const etablissement = useAdminEtab();
  const [postes, setPostes] = useState<PosteOut[]>([]);
  const [enRevision, setEnRevision] = useState<CandidatureOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [titre, setTitre] = useState("");
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

  const charger = () => {
    setChargement(true);
    Promise.all([listerPostes(etablissement.id), candidaturesEnAttenteRevision()])
      .then(([resPostes, resRevision]) => {
        setPostes(resPostes.data);
        setEnRevision(resRevision.data);
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
      await creerPoste(etablissement.id, titre, criteres);
      setTitre("");
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
