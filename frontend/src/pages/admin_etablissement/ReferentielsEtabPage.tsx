import { useEffect, useMemo, useState } from "react";
import { listerReferentiels, proposerReferentiel, type ReferentielOut } from "../../api/evaluations_gouvernance";
import { listerClasses } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { Badge, Btn, Card, EmptyState, ErrorBanner, Field, PageTitle, SkeletonCard, SuccessBanner, TextInput } from "../../components/ui";
import { Scale, Search, Send } from "lucide-react";

const TONE_STATUT: Record<ReferentielOut["statut"], "success" | "pending" | "neutral"> = {
  valide: "success",
  proposition_en_attente: "pending",
  remplace: "neutral",
};

const LABEL_STATUT: Record<ReferentielOut["statut"], string> = {
  valide: "En vigueur",
  proposition_en_attente: "Proposition en attente",
  remplace: "Remplacé",
};

export function ReferentielsEtabPage() {
  const etablissement = useAdminEtab();
  const [referentiels, setReferentiels] = useState<ReferentielOut[]>([]);
  // Par défaut, seuls les niveaux enseignés dans l'établissement (sinon des centaines de
  // lignes : tous les niveaux du pays, du CI au doctorat).
  const [niveauxEtab, setNiveauxEtab] = useState<Set<string>>(new Set());
  const [tousNiveaux, setTousNiveaux] = useState(false);
  const [recherche, setRecherche] = useState("");
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [propositionOuverte, setPropositionOuverte] = useState<string | null>(null);
  const [nouveauCoefficient, setNouveauCoefficient] = useState<number>(1);
  const [enCours, setEnCours] = useState(false);

  const charger = () => {
    setChargement(true);
    listerReferentiels()
      .then((res) => setReferentiels(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);
  useEffect(() => {
    listerClasses(etablissement.id)
      .then((res) => setNiveauxEtab(new Set(res.data.map((c) => c.niveau))))
      .catch(() => setTousNiveaux(true));
  }, [etablissement.id]);

  const ouvrirProposition = (r: ReferentielOut) => {
    setPropositionOuverte(r.id);
    setNouveauCoefficient(r.coefficient);
    setSucces(null);
  };

  const soumettreProposition = async (referentielId: string) => {
    setErreur(null);
    setEnCours(true);
    try {
      await proposerReferentiel(referentielId, nouveauCoefficient);
      setPropositionOuverte(null);
      setSucces("Proposition envoyée — elle prendra effet une fois validée par le ministère.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'envoyer cette proposition."));
    } finally {
      setEnCours(false);
    }
  };

  // Un referentiel "remplace" n'a plus d'interet operationnel une fois qu'un autre
  // (valide ou en attente) couvre deja le meme niveau/matiere.
  const referentielsActifs = referentiels.filter((r) => r.statut !== "remplace");
  const filtre = recherche.trim().toLowerCase();
  const groupes = useMemo(() => {
    const visibles = referentielsActifs.filter(
      (r) =>
        (tousNiveaux || niveauxEtab.size === 0 || niveauxEtab.has(r.niveau)) &&
        (!filtre || `${r.niveau} ${r.matiere}`.toLowerCase().includes(filtre)),
    );
    const parNiveau = new Map<string, ReferentielOut[]>();
    visibles.forEach((r) => parNiveau.set(r.niveau, [...(parNiveau.get(r.niveau) ?? []), r]));
    return [...parNiveau.entries()];
  }, [referentielsActifs, tousNiveaux, niveauxEtab, filtre]);

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace établissement">Référentiels de coefficients</PageTitle>
      <p className="text-sm mb-6" style={{ color: "var(--ink-soft)" }}>
        Les coefficients sont fixés par le ministère. Vous pouvez proposer une mise à jour pour votre établissement —
        elle n'est effective qu'après validation ministérielle (UC-09).
      </p>
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      {!chargement && referentielsActifs.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div style={{ position: "relative", flex: "1 1 240px" }}>
            <Search size={16} aria-hidden="true" style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--ink-faint)" }} />
            <TextInput value={recherche} onChange={(e) => setRecherche(e.target.value)} placeholder="Rechercher un niveau ou une matière" style={{ width: "100%", paddingLeft: "36px" }} />
          </div>
          {niveauxEtab.size > 0 && (
            <label className="flex items-center gap-2 text-sm" style={{ color: "var(--ink-soft)", cursor: "pointer" }}>
              <input type="checkbox" checked={tousNiveaux} onChange={(e) => setTousNiveaux(e.target.checked)} />
              Afficher aussi les niveaux que l'établissement n'enseigne pas
            </label>
          )}
        </div>
      )}

      {chargement ? (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : referentielsActifs.length === 0 ? (
        <EmptyState
          icon={<Scale size={24} />}
          title="Aucun référentiel publié"
          desc="Le ministère n'a pas encore fixé de coefficient — revenez plus tard."
        />
      ) : groupes.length === 0 ? (
        <EmptyState icon={<Search size={24} />} title="Aucun coefficient ne correspond" desc="Modifiez la recherche ou affichez tous les niveaux." />
      ) : (
        <div className="space-y-6">
          {groupes.map(([niveau, lignes]) => (
          <section key={niveau} aria-label={niveau}>
          <h2 className="text-title" style={{ margin: "0 0 8px", color: "var(--ink)" }}>{niveau}</h2>
          <div className="space-y-3">
          {lignes.map((r) => (
            <Card key={r.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)" }}>
                <div>
                  <p style={{ fontWeight: 600, color: "var(--ink)" }}>
                    {r.matiere}
                  </p>
                  <p className="monospace text-sm" style={{ color: "var(--ink-soft)" }}>
                    Coefficient actuel : {r.coefficient}
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
                  <Badge tone={TONE_STATUT[r.statut]}>{LABEL_STATUT[r.statut]}</Badge>
                  {r.statut === "valide" && propositionOuverte !== r.id && (
                    <Btn variant="outline" size="sm" onClick={() => ouvrirProposition(r)}>
                      Proposer une mise à jour
                    </Btn>
                  )}
                </div>
              </div>

              {propositionOuverte === r.id && (
                <div className="anim-slide-up" style={{ marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px dashed var(--border)", display: "flex", alignItems: "flex-end", gap: "var(--space-3)", flexWrap: "wrap" }}>
                  <Field label="Nouveau coefficient proposé">
                    <TextInput
                      type="number"
                      step="0.1"
                      min={0}
                      value={nouveauCoefficient}
                      onChange={(e) => setNouveauCoefficient(Number(e.target.value))}
                      style={{ width: "120px" }}
                    />
                  </Field>
                  <Btn variant="primary" size="sm" loading={enCours} onClick={() => soumettreProposition(r.id)} leftIcon={<Send size={14} />}>
                    Envoyer la proposition
                  </Btn>
                  <Btn variant="ghost" size="sm" onClick={() => setPropositionOuverte(null)} disabled={enCours}>
                    Annuler
                  </Btn>
                </div>
              )}
            </Card>
          ))}
          </div>
          </section>
          ))}
        </div>
      )}
    </div>
  );
}
