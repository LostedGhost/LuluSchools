import { useEffect, useState, type FormEvent } from "react";
import { messageErreur } from "../../api/client";
import {
  candidaturesOffre,
  cloturerOffreStage,
  deciderCandidatureStage,
  offresEtablissement,
  publierOffreStage,
  type CandidatureStage,
  type OffreStage,
  type OffreStagePayload,
} from "../../api/insertion";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { useConfirmation } from "../../components/Modale";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Skeleton, SuccessBanner, TextArea, TextInput } from "../../components/ui";

/* Lot 7.8 — l'établissement publie les stages de ses entreprises partenaires (qui n'ont
   pas de compte) et transmet leur réponse aux candidats. */

const VIDE: OffreStagePayload = { entreprise: "", intitule: "", description: "", lieu: "", filiere: "", duree_semaines: 8, date_limite: "", contact: "" };
const LIBELLES = { envoyee: "Reçue", retenue: "Retenue", non_retenue: "Non retenue" } as const;

function Candidatures({ offre }: { offre: OffreStage }) {
  const [liste, setListe] = useState<CandidatureStage[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  useEffect(() => {
    candidaturesOffre(offre.id).then((r) => setListe(r.data)).catch((err) => setErreur(messageErreur(err)));
  }, [offre.id]);
  const decider = async (c: CandidatureStage, statut: "retenue" | "non_retenue") => {
    try {
      const res = await deciderCandidatureStage(c.id, statut);
      setListe((l) => l?.map((x) => (x.id === c.id ? res.data : x)) ?? null);
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };
  if (!liste) return erreur ? <ErrorBanner>{erreur}</ErrorBanner> : <Skeleton height="60px" />;
  if (liste.length === 0) return <p style={{ color: "var(--ink-soft)" }}>Aucune candidature pour le moment.</p>;
  return (
    <>
    <ErrorBanner>{erreur}</ErrorBanner>
    <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "10px" }}>
      {liste.map((c) => (
        <li key={c.id} style={{ borderTop: "1px solid var(--border)", paddingTop: "10px" }}>
          <strong>{c.eleve_prenom} {c.eleve_nom}</strong> <Badge tone={c.statut === "retenue" ? "success" : c.statut === "non_retenue" ? "neutral" : "pending"}>{LIBELLES[c.statut]}</Badge>
          <p style={{ margin: "6px 0", color: "var(--ink-soft)" }}>{c.message}</p>
          {c.statut === "envoyee" && (
            <div style={{ display: "flex", gap: "8px" }}>
              <Btn size="sm" variant="primary" onClick={() => decider(c, "retenue")}>Retenue par l'entreprise</Btn>
              <Btn size="sm" variant="ghost" onClick={() => decider(c, "non_retenue")}>Non retenue</Btn>
            </div>
          )}
        </li>
      ))}
    </ul>
    </>
  );
}

export function StagesAdminPage() {
  const etablissement = useAdminEtab();
  const confirmer = useConfirmation();
  const [offres, setOffres] = useState<OffreStage[] | null>(null);
  const [form, setForm] = useState(VIDE);
  const [ouverte, setOuverte] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  const charger = () => {
    offresEtablissement(etablissement.id).then((r) => setOffres(r.data)).catch((err) => setErreur(messageErreur(err)));
  };
  useEffect(charger, [etablissement.id]);

  const maj = (partiel: Partial<OffreStagePayload>) => setForm((f) => ({ ...f, ...partiel }));

  const publier = async (e: FormEvent) => {
    e.preventDefault();
    setEnvoi(true);
    setErreur(null);
    try {
      await publierOffreStage(etablissement.id, { ...form, filiere: form.filiere?.trim() || null });
      setSucces("Offre publiée : elle est visible par vos élèves.");
      setForm(VIDE);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de publier l'offre."));
    } finally {
      setEnvoi(false);
    }
  };

  const cloturer = async (o: OffreStage) => {
    if (!(await confirmer({ titre: "Clôturer cette offre ?", message: "Elle ne sera plus visible des élèves.", action: "Clôturer" }))) return;
    try {
      await cloturerOffreStage(o.id);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const valide = form.entreprise.trim() && form.intitule.trim() && form.description.trim().length >= 10 && form.lieu.trim() && form.date_limite && form.contact.trim();

  return (
    <div className="page-content">
      <SectionHead eyebrow="Insertion" title="Stages" desc="Publiez les offres de vos entreprises partenaires ; vous transmettez leur réponse aux élèves." />
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      <Card>
        <form onSubmit={publier} style={{ display: "grid", gap: "12px" }}>
          <div className="grid-2">
            <Field label="Entreprise" required><TextInput value={form.entreprise} onChange={(e) => maj({ entreprise: e.target.value })} /></Field>
            <Field label="Intitulé du stage" required><TextInput value={form.intitule} onChange={(e) => maj({ intitule: e.target.value })} /></Field>
            <Field label="Lieu" required><TextInput value={form.lieu} onChange={(e) => maj({ lieu: e.target.value })} /></Field>
            <Field label="Filière concernée" helper="Laisser vide : toutes les filières."><TextInput value={form.filiere ?? ""} onChange={(e) => maj({ filiere: e.target.value })} /></Field>
            <Field label="Durée (semaines)" required><TextInput type="number" min={1} max={52} value={form.duree_semaines} onChange={(e) => maj({ duree_semaines: Number(e.target.value) })} /></Field>
            <Field label="Date limite de candidature" required><TextInput type="date" value={form.date_limite} onChange={(e) => maj({ date_limite: e.target.value })} /></Field>
          </div>
          <Field label="Description" required><TextArea rows={3} value={form.description} onChange={(e) => maj({ description: e.target.value })} /></Field>
          <Field label="Contact de l'entreprise" required helper="Ne sera pas affiché aux élèves tant que vous ne le leur transmettez pas.">
            <TextInput value={form.contact} onChange={(e) => maj({ contact: e.target.value })} />
          </Field>
          <Btn type="submit" variant="primary" loading={envoi} disabled={!valide}>Publier l'offre</Btn>
        </form>
      </Card>

      <div style={{ marginTop: "var(--space-6)", display: "grid", gap: "var(--space-4)" }}>
        {!offres ? (
          <Skeleton height="120px" />
        ) : offres.length === 0 ? (
          <EmptyState title="Aucune offre publiée" desc="Vos offres apparaîtront ici avec leurs candidatures." />
        ) : (
          offres.map((o) => (
            <Card key={o.id}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
                <div>
                  <p className="text-eyebrow" style={{ margin: 0 }}>{o.entreprise}</p>
                  <h2 className="text-title" style={{ margin: "2px 0" }}>{o.intitule}</h2>
                  <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                    {o.nombre_candidatures ?? 0} candidature(s) · jusqu'au {new Date(o.date_limite).toLocaleDateString("fr-FR")}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  {o.active ? <Badge tone="success">Ouverte</Badge> : <Badge tone="neutral">Clôturée</Badge>}
                  <Btn size="sm" variant="outline" onClick={() => setOuverte(ouverte === o.id ? null : o.id)}>
                    {ouverte === o.id ? "Masquer" : "Candidatures"}
                  </Btn>
                  {o.active && <Btn size="sm" variant="ghost" onClick={() => cloturer(o)}>Clôturer</Btn>}
                </div>
              </div>
              {ouverte === o.id && <div style={{ marginTop: "12px" }}><Candidatures offre={o} /></div>}
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
