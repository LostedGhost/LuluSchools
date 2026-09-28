import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { messageErreur } from "../../api/client";
import {
  aTraiter,
  appliquerAffectations,
  genererDocumentActe,
  marquerRemboursementsEffectues,
  modifierParametresEtablissement,
  propositionAffectations,
  reconduireContratsEnLot,
  recruterEnUnClic,
  rejeterInscriptionsEnLot,
  reverserPrestataireEnLot,
  reverserVendeurEnLot,
  traiterSignalementsAnnoncesEnLot,
  traiterSignalementsMessagesEnLot,
  validerInscriptionsEnLot,
  type ElementATraiter,
  type PropositionAffectation,
  type SectionATraiter,
} from "../../api/administration";
import { deciderContestationMarketplace } from "../../api/marketplace";
import { deciderContestationMicroJob } from "../../api/micro_jobs";
import type { EtablissementOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, SkeletonCard, SuccessBanner, TextInput } from "../../components/ui";
import { CheckCheck, CircleCheck, Sparkles, TriangleAlert, Wand2 } from "lucide-react";
import { useConfirmation, type DemandeConfirmation } from "../../components/Modale";

const MarkdownIA = lazy(() => import("../../components/el_professor/MarkdownIA"));

/** Écran détaillé de chaque file, pour ce qui demande une lecture attentive. */
const LIENS_A_PLUS: Record<string, string> = {
  casiers: "/admin-etablissement/postes",
  notation_manuelle: "/admin-etablissement/postes",
  contestations_recrutement: "/admin-etablissement/contestations",
  actes: "/admin-etablissement/actes",
  alertes: "/admin-etablissement/alertes-el-professor",
  signalements_messages: "/admin-etablissement/signalements",
  signalements_annonces: "/admin-etablissement/marketplace",
  litiges_marketplace: "/admin-etablissement/marketplace",
};
const LIENS_A_PLUS_PLUS: Record<string, string> = {
  litiges_micro_jobs: "/admin-ministeriel/micro-jobs-arbitrage",
  reversements_micro_jobs: "/admin-ministeriel/micro-jobs-arbitrage",
  referentiels: "/admin-ministeriel/referentiels",
};

const LIBELLES_IA: Record<string, string> = {
  elevee: "Gravité élevée", moyenne: "Gravité moyenne", faible: "Gravité faible",
  acceptee: "L'IA recommande d'accepter", rejetee: "L'IA recommande de rejeter",
};
const LIBELLES_DECISION: Record<string, string> = { classer: "classer sans suite", masquer: "retirer le contenu", examiner: "à examiner" };

const fcfa = (n: number) => `${n.toLocaleString("fr-FR")} FCFA`;

export function ATraiterPage({ etablissement }: { etablissement?: EtablissementOut }) {
  const { utilisateur } = useAuth();
  const ministere = utilisateur?.role === "admin_ministeriel";
  const [sections, setSections] = useState<SectionATraiter[] | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);
  const [admissionAuto, setAdmissionAuto] = useState(!!etablissement?.admission_automatique);
  const [propositions, setPropositions] = useState<PropositionAffectation[] | null>(null);
  const [references, setReferences] = useState<Record<string, string>>({});
  const [motifRejet, setMotifRejet] = useState("");
  const confirmer = useConfirmation();

  const charger = useCallback(() => {
    aTraiter()
      .then((res) => setSections(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, []);
  useEffect(charger, [charger]);

  const agir = async (cle: string, action: () => Promise<string>, confirmation?: DemandeConfirmation) => {
    if (confirmation && !(await confirmer(confirmation))) return;
    setEnCours(cle);
    setErreur(null);
    setSucces(null);
    try {
      setSucces(await action());
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(null);
    }
  };

  const total = useMemo(() => (sections ?? []).reduce((n, s) => n + s.nombre, 0), [sections]);
  const liens = ministere ? LIENS_A_PLUS_PLUS : LIENS_A_PLUS;

  const actions = (section: SectionATraiter) => {
    const ids = section.elements.map((e) => e.id);
    switch (section.cle) {
      case "inscriptions":
        return (
          <div className="flex flex-wrap items-center gap-2">
            <Btn size="sm" leftIcon={<CheckCheck size={14} />} loading={enCours === section.cle}
              onClick={() => agir(section.cle, async () => {
                const r = (await validerInscriptionsEnLot(ids)).data;
                return `${r.validees.length} inscription(s) validée(s)` + (r.refusees.length ? `, ${r.refusees.length} non validée(s) (${r.refusees[0].message})` : ".");
              }, {
                titre: `Valider ${ids.length} inscription(s) ?`,
                message: "Les élèves sont admis dans l'ordre d'arrivée, dans la limite des places, et les familles sont prévenues.",
                action: "Tout valider",
              })}>
              Tout valider ({ids.length})
            </Btn>
            <TextInput value={motifRejet} onChange={(e) => setMotifRejet(e.target.value)} placeholder="Motif de rejet commun" style={{ maxWidth: "240px" }} />
            <Btn size="sm" variant="outline" disabled={motifRejet.trim().length < 3}
              onClick={() => agir(section.cle, async () => `${(await rejeterInscriptionsEnLot(ids, motifRejet.trim())).data.validees.length} inscription(s) rejetée(s).`, {
                titre: `Rejeter ${ids.length} inscription(s) ?`,
                message: <>Chaque famille recevra ce motif : « {motifRejet.trim()} ». Cette décision est définitive.</>,
                action: "Tout rejeter",
                danger: true,
              })}>
              Tout rejeter
            </Btn>
          </div>
        );
      case "reconductions":
        return etablissement && (
          <Btn size="sm" leftIcon={<CheckCheck size={14} />} loading={enCours === section.cle}
            onClick={() => agir(section.cle, async () => `${(await reconduireContratsEnLot(etablissement.id)).data.length} proposition(s) de reconduction envoyée(s) aux enseignants.`, {
              titre: `Proposer la reconduction de ${section.nombre} contrat(s) ?`,
              message: "Chaque enseignant reçoit un nouveau contrat d'un an, avec le même syllabus, à signer depuis son espace.",
              action: "Tout reconduire",
            })}>
            Tout reconduire
          </Btn>
        );
      case "affectations":
        return etablissement && (
          <Btn size="sm" variant="magic" leftIcon={<Wand2 size={14} />} loading={enCours === section.cle}
            onClick={() => agir(section.cle, async () => {
              const r = (await propositionAffectations(etablissement.id)).data;
              setPropositions(r);
              return r.length ? `${r.length} affectation(s) proposée(s) : vérifiez puis appliquez.` : "Aucun enseignant disponible à proposer.";
            })}>
            Calculer une proposition
          </Btn>
        );
      case "signalements_messages":
      case "signalements_annonces":
        return (
          <Btn size="sm" variant="magic" leftIcon={<Sparkles size={14} />} loading={enCours === section.cle}
            onClick={() => agir(section.cle, async () => {
              const f = section.cle === "signalements_messages" ? traiterSignalementsMessagesEnLot : traiterSignalementsAnnoncesEnLot;
              const r = (await f(ids)).data;
              return `${r.traites.length} signalement(s) traité(s) selon la suggestion de l'IA ; ${r.ignores.length} laissé(s) pour un examen humain.`;
            }, {
              titre: "Appliquer les suggestions de l'IA ?",
              message: "Les contenus que l'IA propose de retirer seront masqués, les autres classés sans suite. Les signalements « à examiner » restent pour vous.",
              action: "Appliquer",
            })}>
            Appliquer les suggestions de l'IA
          </Btn>
        );
      case "remboursements":
        return (
          <Btn size="sm" variant="outline" loading={enCours === section.cle}
            onClick={() => agir(section.cle, async () => `${(await marquerRemboursementsEffectues(ids)).data.length} remboursement(s) marqué(s) comme effectué(s).`, {
              titre: `Confirmer ${ids.length} remboursement(s) ?`,
              message: "Ne confirmez que si vous avez réellement remboursé ces paiements (Mobile Money ou espèces) : ils disparaîtront de la liste.",
              action: "J'ai remboursé",
            })}>
            J'ai remboursé ces paiements
          </Btn>
        );
      default:
        return null;
    }
  };

  const ligne = (section: SectionATraiter, e: ElementATraiter) => {
    let bouton = null;
    if (section.cle === "a_recruter") {
      bouton = (
        <Btn size="sm" loading={enCours === e.id}
          onClick={() => agir(e.id, async () => { await recruterEnUnClic(e.id); return "Contrat créé : l'enseignant peut le signer depuis son espace."; })}>
          Recruter
        </Btn>
      );
    } else if (section.cle === "actes" && e.groupe === "auto") {
      bouton = (
        <Btn size="sm" variant="outline" loading={enCours === e.id}
          onClick={() => agir(e.id, async () => { await genererDocumentActe(e.id); return "Document généré et livré."; })}>
          Générer
        </Btn>
      );
    } else if (section.cle === "litiges_marketplace" || section.cle === "litiges_micro_jobs") {
      const decider = section.cle === "litiges_marketplace" ? deciderContestationMarketplace : deciderContestationMicroJob;
      bouton = (
        <div className="flex gap-2">
          <Btn size="sm" loading={enCours === e.id}
            onClick={() => agir(e.id, async () => { await decider(e.id, "acceptee"); return "Litige accepté : remboursement lancé via Kkiapay."; }, {
              titre: "Accepter ce litige ?",
              message: "Le plaignant est remboursé automatiquement et l'autre partie ne sera pas payée. Cette décision est définitive.",
              action: "Accepter et rembourser",
              danger: true,
            })}>
            Accepter
          </Btn>
          <Btn size="sm" variant="outline"
            onClick={() => agir(e.id, async () => { await decider(e.id, "rejetee", e.ia && e.ia_niveau === "rejetee" ? e.ia : "Contestation non fondée après examen des faits."); return "Litige rejeté : la transaction est maintenue."; }, {
              titre: "Rejeter ce litige ?",
              message: "La transaction est maintenue et le bénéficiaire sera payé. Cette décision est définitive.",
              action: "Rejeter",
            })}>
            Rejeter
          </Btn>
        </div>
      );
    }
    return (
      <div key={e.id} className="flex flex-wrap items-start gap-3 py-3" style={{ borderTop: "1px solid var(--border)" }}>
        <div style={{ flex: 1, minWidth: "220px" }}>
          <p style={{ margin: 0, fontWeight: 600, color: "var(--ink)", fontSize: "var(--text-sm)" }}>
            {e.libelle}
            {e.montant != null && <span style={{ fontWeight: 400, color: "var(--ink-soft)" }}> — {fcfa(e.montant)}</span>}
          </p>
          {e.detail && section.cle.startsWith("signalements") ? (
            <p className="text-sm" style={{ margin: "2px 0 0", color: "var(--ink-soft)" }}>Suggestion : {LIBELLES_DECISION[e.detail] ?? e.detail}</p>
          ) : e.detail ? (
            <p className="text-sm" style={{ margin: "2px 0 0", color: "var(--ink-soft)" }}>{e.detail}</p>
          ) : null}
          {(e.ia || e.ia_niveau) && (
            <div style={{ marginTop: "6px", padding: "8px 10px", borderRadius: "var(--radius-sm)", background: "var(--magic-tint)", fontSize: "var(--text-sm)" }}>
              <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontWeight: 600, color: "var(--magic-deep)" }}>
                <Sparkles size={13} /> {e.ia_niveau ? LIBELLES_IA[e.ia_niveau] ?? "Analyse de l'IA" : "Analyse de l'IA"}
              </span>
              {e.ia && (
                <Suspense fallback={<p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{e.ia}</p>}>
                  <MarkdownIA texte={e.ia} />
                </Suspense>
              )}
            </div>
          )}
        </div>
        {bouton}
      </div>
    );
  };

  const reversements = (section: SectionATraiter) => {
    const groupes = new Map<string, ElementATraiter[]>();
    section.elements.forEach((e) => groupes.set(e.groupe ?? e.id, [...(groupes.get(e.groupe ?? e.id) ?? []), e]));
    const lot = section.cle === "reversements_marketplace" ? reverserVendeurEnLot : reverserPrestataireEnLot;
    return [...groupes.entries()].map(([groupe, elements]) => {
      const totalGroupe = elements.reduce((n, e) => n + (e.montant ?? 0), 0);
      const reference = references[groupe] ?? "";
      return (
        <div key={groupe} className="py-3" style={{ borderTop: "1px solid var(--border)" }}>
          <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{elements[0].detail} — {fcfa(totalGroupe)}</p>
          <p className="text-sm" style={{ margin: "2px 0 8px", color: "var(--ink-soft)" }}>{elements.map((e) => e.libelle).join(" · ")}</p>
          <div className="flex flex-wrap gap-2">
            <TextInput value={reference} placeholder="Référence du virement Mobile Money" style={{ maxWidth: "280px" }}
              onChange={(ev) => setReferences((r) => ({ ...r, [groupe]: ev.target.value }))} />
            <Btn size="sm" disabled={reference.trim().length < 3} loading={enCours === groupe}
              onClick={() => agir(groupe, async () => {
                const r = (await lot(elements.map((e) => e.id), reference.trim())).data;
                return `Virement de ${fcfa(r.montant_total)} enregistré pour ${r.reverses.length} opération(s).`;
              }, {
                titre: `Enregistrer un virement de ${fcfa(totalGroupe)} ?`,
                message: <>Bénéficiaire : {elements[0].detail}. Référence : « {reference.trim()} ». Vérifiez le montant envoyé avant de confirmer.</>,
                action: "Confirmer le virement",
              })}>
              Confirmer le virement
            </Btn>
          </div>
        </div>
      );
    });
  };

  return (
    <div className="page-content">
      <div style={{ marginBottom: "20px" }}>
        <p className="text-eyebrow">{ministere ? "Administration ministérielle" : etablissement?.nom}</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>À traiter</h1>
        <p className="text-sm" style={{ color: "var(--ink-soft)", margin: "4px 0 0" }}>
          Tout ce qui attend une décision, au même endroit. Ce qui peut l'être est automatisé ou groupé ; l'IA prépare le reste,
          vous décidez.
        </p>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && <SuccessBanner>{succes}</SuccessBanner>}

      {etablissement && (
        <Card variant="soft" style={{ marginBottom: "16px" }}>
          <label className="flex items-start gap-3" style={{ cursor: "pointer" }}>
            <input type="checkbox" checked={admissionAuto} style={{ marginTop: "4px" }}
              onChange={(e) => {
                const valeur = e.target.checked;
                setAdmissionAuto(valeur);
                void agir("parametres", async () => {
                  await modifierParametresEtablissement(etablissement.id, valeur);
                  return valeur ? "Admission automatique activée." : "Admission automatique désactivée.";
                });
              }} />
            <span>
              <strong style={{ color: "var(--ink)" }}>Admission automatique des inscriptions</strong>
              <span className="text-sm" style={{ display: "block", color: "var(--ink-soft)" }}>
                Pour les classes à l'ordre d'arrivée, une inscription complète est validée dès qu'il reste une place. Les refus,
                concours et tirages au sort restent vos décisions.
              </span>
            </span>
          </label>
        </Card>
      )}

      {propositions && propositions.length > 0 && etablissement && (
        <Card style={{ marginBottom: "16px", border: "1px solid var(--magic)" }}>
          <p style={{ margin: "0 0 8px", fontWeight: 700 }}>Affectations proposées ({propositions.length})</p>
          {propositions.map((p, i) => (
            <div key={`${p.classe_id}-${p.enseignant_utilisateur_id}`} className="flex flex-wrap items-center gap-2 py-2" style={{ borderTop: "1px solid var(--border)", fontSize: "var(--text-sm)" }}>
              <span style={{ flex: 1, minWidth: "220px" }}>
                <strong>{p.classe}</strong> ← {p.enseignant}{p.matiere ? ` (${p.matiere})` : ""} {p.principal && <Badge tone="info">Principal</Badge>}
                <span style={{ display: "block", color: "var(--ink-faint)" }}>{p.motif}</span>
              </span>
              <Btn size="sm" variant="ghost" onClick={() => setPropositions(propositions.filter((_, j) => j !== i))}>Retirer</Btn>
            </div>
          ))}
          <Btn size="sm" style={{ marginTop: "8px" }} loading={enCours === "appliquer"}
            onClick={() => agir("appliquer", async () => {
              const r = (await appliquerAffectations(etablissement.id, propositions)).data;
              setPropositions(null);
              return `${r.affectations_creees} affectation(s) créée(s).`;
            })}>
            Appliquer
          </Btn>
        </Card>
      )}

      {sections === null ? (
        <SkeletonCard />
      ) : total === 0 ? (
        <EmptyState icon={<CircleCheck size={24} />} title="Rien à traiter" desc="Toutes les files sont vides. Bravo !" />
      ) : (
        <div className="space-y-4">
          {sections.map((section) => (
            <Card key={section.cle} style={section.urgent ? { border: "1px solid var(--action-deep)" } : undefined}>
              <div className="flex flex-wrap items-start justify-between gap-3" style={{ marginBottom: "8px" }}>
                <div style={{ flex: 1, minWidth: "240px" }}>
                  <h2 className="text-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                    {section.urgent && <TriangleAlert size={18} style={{ color: "var(--action-deep)" }} />}
                    {section.titre} <Badge tone={section.urgent ? "error" : "neutral"}>{section.nombre}</Badge>
                  </h2>
                  <p className="text-sm" style={{ margin: "4px 0 0", color: "var(--ink-soft)" }}>{section.description}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {actions(section)}
                  {liens[section.cle] && <Link to={liens[section.cle]} className="btn btn-ghost btn-sm">Ouvrir l'écran</Link>}
                </div>
              </div>
              {section.cle.startsWith("reversements") ? reversements(section) : section.elements.map((e) => ligne(section, e))}
              {section.nombre > section.elements.length && (
                <p className="text-sm" style={{ color: "var(--ink-faint)", marginTop: "8px" }}>
                  … et {section.nombre - section.elements.length} autre(s).
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
