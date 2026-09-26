import { useEffect, useState, type FormEvent } from "react";
import {
  alertesDepassementPlafond,
  approuverValidationParentale,
  definirPlafondFamilial,
  obtenirPlafondFamilial,
  obtenirReleveFinancier,
  refuserValidationParentale,
  validationsEnAttente,
} from "../../api/coffre_fort";
import { messageErreur } from "../../api/client";
import { useMesEnfants } from "../../tuteur/useMesEnfants";
import type { AlerteDepassementPlafondOut, ReleveFinancierOut, ValidationParentaleOut } from "../../types/api";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, SectionHead, Select, SkeletonCard, SuccessBanner, TextInput } from "../../components/ui";
import { TriangleAlert, Users, Wallet } from "lucide-react";

const LABEL_MODULE: Record<string, string> = {
  micro_job: "Micro-jobs",
  marketplace: "Marketplace",
  acte: "Acte académique",
};

export function CoffreFortPage() {
  const { enfants, chargement: chargementEnfants, erreur: erreurEnfants } = useMesEnfants();
  const [inscriptionId, setInscriptionId] = useState("");
  const [plafondHebdo, setPlafondHebdo] = useState("");
  const [seuilValidation, setSeuilValidation] = useState("");
  const [releve, setReleve] = useState<ReleveFinancierOut | null>(null);
  const [validations, setValidations] = useState<ValidationParentaleOut[]>([]);
  const [alertes, setAlertes] = useState<AlerteDepassementPlafondOut[]>([]);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enregistrement, setEnregistrement] = useState(false);
  const [decisionEnCoursId, setDecisionEnCoursId] = useState<string | null>(null);

  useEffect(() => {
    if (enfants.length > 0 && !inscriptionId) setInscriptionId(enfants[0].id);
  }, [enfants, inscriptionId]);

  const enfant = enfants.find((i) => i.id === inscriptionId);

  const recharger = (eleveUtilisateurId: string) => {
    setChargement(true);
    Promise.all([
      obtenirPlafondFamilial(eleveUtilisateurId),
      obtenirReleveFinancier(eleveUtilisateurId),
      validationsEnAttente(eleveUtilisateurId),
      alertesDepassementPlafond(eleveUtilisateurId),
    ])
      .then(([resPlafond, resReleve, resValidations, resAlertes]) => {
        setPlafondHebdo(resPlafond.data?.plafond_hebdomadaire?.toString() ?? "");
        setSeuilValidation(resPlafond.data?.seuil_validation?.toString() ?? "");
        setReleve(resReleve.data);
        setValidations(resValidations.data);
        setAlertes(resAlertes.data);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(() => {
    if (!enfant || !enfant.eleve_utilisateur_id) return;
    recharger(enfant.eleve_utilisateur_id);
  }, [enfant]);

  const enregistrerPlafond = async (e: FormEvent) => {
    e.preventDefault();
    if (!enfant?.eleve_utilisateur_id) return;
    setErreur(null);
    setSucces(null);
    setEnregistrement(true);
    try {
      await definirPlafondFamilial(enfant.eleve_utilisateur_id, {
        plafond_hebdomadaire: plafondHebdo.trim() ? Number(plafondHebdo) : null,
        seuil_validation: seuilValidation.trim() ? Number(seuilValidation) : null,
      });
      setSucces("Configuration enregistrée.");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer la configuration."));
    } finally {
      setEnregistrement(false);
    }
  };

  const decider = async (validationId: string, decision: "approuver" | "refuser") => {
    setDecisionEnCoursId(validationId);
    setErreur(null);
    try {
      if (decision === "approuver") await approuverValidationParentale(validationId);
      else await refuserValidationParentale(validationId);
      if (enfant?.eleve_utilisateur_id) recharger(enfant.eleve_utilisateur_id);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer votre décision."));
    } finally {
      setDecisionEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Mes enfants"
        title="Coffre-fort familial"
        desc="Optionnel : définissez un plafond de dépense hebdomadaire et/ou un seuil de validation obligatoire. Sans configuration, aucune limite ne s'applique."
      />
      <ErrorBanner>{erreurEnfants ?? erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      {chargementEnfants ? (
        <SkeletonCard />
      ) : enfants.length === 0 ? (
        <EmptyState icon={<Users size={24} />} title="Aucun enfant inscrit" />
      ) : (
        <>
          <div className="card card-soft" style={{ marginBottom: "24px", maxWidth: "360px" }}>
            <Field label="Enfant">
              <Select value={inscriptionId} onChange={(e) => setInscriptionId(e.target.value)}>
                {enfants.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.eleve_prenom} {i.eleve_nom}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          {chargement ? (
            <SkeletonCard />
          ) : (
            <>
              <Card style={{ marginBottom: "24px" }}>
                <form onSubmit={enregistrerPlafond} style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end" }}>
                  <div style={{ minWidth: "220px" }}>
                    <Field label="Plafond hebdomadaire (FCFA)">
                      <TextInput type="number" min={0} value={plafondHebdo} onChange={(e) => setPlafondHebdo(e.target.value)} placeholder="Aucun" />
                    </Field>
                  </div>
                  <div style={{ minWidth: "220px" }}>
                    <Field label="Seuil de validation obligatoire (FCFA)">
                      <TextInput type="number" min={0} value={seuilValidation} onChange={(e) => setSeuilValidation(e.target.value)} placeholder="Aucun" />
                    </Field>
                  </div>
                  <Btn type="submit" variant="primary" size="sm" loading={enregistrement}>
                    Enregistrer
                  </Btn>
                </form>
              </Card>

              {validations.length > 0 && (
                <Card style={{ marginBottom: "24px", borderColor: "var(--action-deep)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px", color: "var(--action-deep)", fontWeight: 700 }}>
                    <TriangleAlert size={16} /> Dépenses en attente de votre validation
                  </div>
                  {validations.map((v) => (
                    <div key={v.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px", marginBottom: "8px" }}>
                      <span style={{ fontSize: "var(--text-sm)" }}>
                        {LABEL_MODULE[v.module] ?? v.module} — {v.montant} FCFA
                      </span>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <Btn variant="primary" size="sm" loading={decisionEnCoursId === v.id} onClick={() => decider(v.id, "approuver")}>
                          Approuver
                        </Btn>
                        <Btn variant="outline" size="sm" loading={decisionEnCoursId === v.id} onClick={() => decider(v.id, "refuser")}>
                          Refuser
                        </Btn>
                      </div>
                    </div>
                  ))}
                </Card>
              )}

              {releve && (
                <>
                  <SectionHead eyebrow="Relevé" title="Activité financière" />
                  <div className="grid-3" style={{ marginBottom: "24px" }}>
                    <Card><Wallet size={18} /><p style={{ margin: "8px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>Ventes marketplace</p><p style={{ margin: 0, fontWeight: 700 }}>{releve.ventes_marketplace} FCFA</p></Card>
                    <Card><Wallet size={18} /><p style={{ margin: "8px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>Dépenses (achats, micro-jobs, actes)</p><p style={{ margin: 0, fontWeight: 700 }}>{releve.achats_marketplace + releve.depenses_micro_jobs + releve.frais_actes} FCFA</p></Card>
                    <Card><Wallet size={18} /><p style={{ margin: "8px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>Solde net</p><p style={{ margin: 0, fontWeight: 700 }}>{releve.solde_net} FCFA</p></Card>
                  </div>
                </>
              )}

              {alertes.length > 0 && (
                <>
                  <SectionHead eyebrow="Historique" title="Dépassements de plafond" />
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {alertes.map((a) => (
                      <div key={a.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "var(--text-sm)" }}>{LABEL_MODULE[a.module] ?? a.module}</span>
                        <Badge tone="pending">{a.montant_semaine} / {a.plafond} FCFA cette semaine</Badge>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
