import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  candidaturesDuPoste,
  candidaturesEnAttenteRevision,
  creerContrat,
  creerPoste,
  listerPostes,
  noterDocumentManuellement,
} from "../../api/recrutement";
import { messageErreur } from "../../api/client";
import type { CandidatureOut, CritereDocument, PosteOut } from "../../types/api";
import { Badge, Card, ErrorBanner, Field, PageTitle, PrimaryButton, SecondaryButton, TextInput } from "../../components/ui";

export function RecrutementPage() {
  const etablissement = useAdminEtab();
  const [postes, setPostes] = useState<PosteOut[]>([]);
  const [enRevision, setEnRevision] = useState<CandidatureOut[]>([]);
  const [titre, setTitre] = useState("");
  const [criteres, setCriteres] = useState<CritereDocument[]>([
    { type_document: "cv", coefficient: 1, seuil_minimal: 60 },
  ]);
  const [notesParDocument, setNotesParDocument] = useState<Record<string, number>>({});
  const [posteSelectionne, setPosteSelectionne] = useState<string | null>(null);
  const [candidaturesPoste, setCandidaturesPoste] = useState<CandidatureOut[]>([]);
  const [syllabusParCandidature, setSyllabusParCandidature] = useState<Record<string, string>>({});
  const [dateFinParCandidature, setDateFinParCandidature] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    listerPostes(etablissement.id)
      .then((res) => setPostes(res.data))
      .catch((err) => setErreur(messageErreur(err)));
    candidaturesEnAttenteRevision()
      .then((res) => setEnRevision(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  useEffect(charger, [etablissement.id]);

  const ajouterCritere = () => {
    setCriteres((prev) => [...prev, { type_document: "", coefficient: 1, seuil_minimal: 60 }]);
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
    setEnCours(true);
    try {
      await creerPoste(etablissement.id, titre, criteres);
      setTitre("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer le poste."));
    } finally {
      setEnCours(false);
    }
  };

  const noter = async (documentId: string) => {
    const note = notesParDocument[documentId];
    if (note === undefined) {
      setErreur("Veuillez indiquer une note.");
      return;
    }
    try {
      await noterDocumentManuellement(documentId, note);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const voirCandidatures = (posteId: string) => {
    setPosteSelectionne(posteId);
    candidaturesDuPoste(posteId)
      .then((res) => setCandidaturesPoste(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };

  const creerLeContrat = async (candidatureId: string) => {
    const syllabus = syllabusParCandidature[candidatureId];
    const dateFin = dateFinParCandidature[candidatureId];
    if (!syllabus?.trim() || !dateFin) {
      setErreur("Veuillez renseigner le syllabus et la date de fin.");
      return;
    }
    try {
      await creerContrat(candidatureId, syllabus, dateFin);
      if (posteSelectionne) voirCandidatures(posteSelectionne);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer le contrat."));
    }
  };

  return (
    <div>
      <PageTitle>Recrutement</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>

      <Card className="mb-4">
        <p className="mb-3 font-medium text-slate-900">Ouvrir un poste</p>
        <form onSubmit={soumettre} className="space-y-3">
          <Field label="Titre du poste">
            <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} required />
          </Field>
          {criteres.map((c, i) => (
            <div key={i} className="flex items-end gap-2">
              <Field label="Type de document">
                <TextInput
                  value={c.type_document}
                  onChange={(e) => majCritere(i, "type_document", e.target.value)}
                  required
                />
              </Field>
              <Field label="Coefficient">
                <TextInput
                  type="number"
                  value={c.coefficient}
                  onChange={(e) => majCritere(i, "coefficient", e.target.value)}
                  className="w-20"
                />
              </Field>
              <Field label="Seuil minimal">
                <TextInput
                  type="number"
                  value={c.seuil_minimal}
                  onChange={(e) => majCritere(i, "seuil_minimal", e.target.value)}
                  className="w-20"
                />
              </Field>
            </div>
          ))}
          <SecondaryButton type="button" onClick={ajouterCritere}>
            + Ajouter un critere
          </SecondaryButton>
          <div>
            <PrimaryButton type="submit" disabled={enCours}>
              {enCours ? "Creation..." : "Ouvrir le poste"}
            </PrimaryButton>
          </div>
        </form>
      </Card>

      <Card className="mb-4">
        <p className="mb-3 font-medium text-slate-900">Postes de l'etablissement</p>
        <div className="space-y-2">
          {postes.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2">
              <span>{p.titre}</span>
              <div className="flex items-center gap-2">
                <Badge tone={p.statut === "ouvert" ? "success" : "neutral"}>{p.statut}</Badge>
                <SecondaryButton type="button" onClick={() => voirCandidatures(p.id)}>
                  Voir les candidatures
                </SecondaryButton>
              </div>
            </div>
          ))}
        </div>

        {posteSelectionne && (
          <div className="mt-4 space-y-3 border-t border-slate-200 pt-4">
            <p className="text-sm font-medium text-slate-700">Candidatures de ce poste</p>
            {candidaturesPoste.length === 0 && <p className="text-sm text-slate-500">Aucune candidature.</p>}
            {candidaturesPoste.map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm">Candidature {c.id.slice(0, 8)}</span>
                  <Badge tone={c.statut === "retenue" ? "success" : c.statut === "rejetee" ? "error" : "neutral"}>
                    {c.statut} {c.score !== null && `(${c.score.toFixed(1)})`}
                  </Badge>
                </div>
                {c.statut === "en_evaluation" && c.score !== null && (
                  <div className="flex flex-wrap items-end gap-2">
                    <Field label="Syllabus">
                      <TextInput
                        value={syllabusParCandidature[c.id] ?? ""}
                        onChange={(e) =>
                          setSyllabusParCandidature((prev) => ({ ...prev, [c.id]: e.target.value }))
                        }
                      />
                    </Field>
                    <Field label="Date de fin">
                      <TextInput
                        type="date"
                        value={dateFinParCandidature[c.id] ?? ""}
                        onChange={(e) =>
                          setDateFinParCandidature((prev) => ({ ...prev, [c.id]: e.target.value }))
                        }
                      />
                    </Field>
                    <PrimaryButton type="button" onClick={() => creerLeContrat(c.id)}>
                      Creer le contrat
                    </PrimaryButton>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {enRevision.length > 0 && (
        <Card>
          <p className="mb-3 font-medium text-red-600">Candidatures en attente de revision manuelle</p>
          <div className="space-y-3">
            {enRevision.map((c) =>
              c.documents
                .filter((d) => d.statut === "echec_notation")
                .map((d) => (
                  <div key={d.id} className="flex items-center justify-between rounded-lg bg-red-50 px-3 py-2">
                    <span className="text-sm">
                      Candidature {c.id.slice(0, 8)} — document {d.type_document}
                    </span>
                    <div className="flex items-center gap-2">
                      <TextInput
                        type="number"
                        min={0}
                        max={100}
                        placeholder="Note /100"
                        className="w-24"
                        value={notesParDocument[d.id] ?? ""}
                        onChange={(e) =>
                          setNotesParDocument((prev) => ({ ...prev, [d.id]: Number(e.target.value) }))
                        }
                      />
                      <SecondaryButton type="button" onClick={() => noter(d.id)}>
                        Noter
                      </SecondaryButton>
                    </div>
                  </div>
                )),
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
