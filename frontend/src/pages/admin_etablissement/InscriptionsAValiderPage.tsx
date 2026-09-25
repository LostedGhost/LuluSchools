import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { inscriptionsAValider, rejeterInscription, validerInscription } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import type { InscriptionAvecEleveOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  PageTitle,
  SectionHead,
  SkeletonCard,
  SuccessBanner,
  TextInput,
} from "../../components/ui";
import { CheckCircle2, XCircle, RefreshCw, AlertCircle, Backpack, Check } from "lucide-react";

export function InscriptionsAValiderPage() {
  const etablissement = useAdminEtab();
  const [inscriptions, setInscriptions] = useState<InscriptionAvecEleveOut[]>([]);
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [rejetIdOuvert, setRejetIdOuvert] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [chargement, setChargement] = useState(true);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    inscriptionsAValider(etablissement.id)
      .then((res) => {
        setInscriptions(res.data);
        setErreur(null);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const valider = async (id: string) => {
    setErreur(null);
    setSucces(null);
    setActionEnCoursId(id);
    try {
      await validerInscription(id);
      setSucces("Inscription validée avec succès !");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const rejeter = async (id: string) => {
    const motif = motifParId[id];
    if (!motif?.trim()) {
      setErreur("Veuillez indiquer un motif de rejet.");
      return;
    }
    setErreur(null);
    setSucces(null);
    setActionEnCoursId(id);
    try {
      await rejeterInscription(id, motif.trim());
      setSucces("Inscription rejetée.");
      setRejetIdOuvert(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageTitle eyebrow="Admin Établissement">
          Inscriptions à valider
        </PageTitle>
        <div className="flex items-center gap-2">
          <Btn
            variant="outline"
            size="sm"
            onClick={charger}
            loading={chargement}
            leftIcon={<RefreshCw size={14} />}
          >
            Actualiser
          </Btn>
          <Badge tone={inscriptions.length > 0 ? "pending" : "neutral"}>
            {inscriptions.length} en attente
          </Badge>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      <div className="mb-6">
        <SectionHead
          title="Demandes d'inscription soumises"
          desc="Vérifiez les informations des élèves candidats avant de confirmer leur intégration dans l'établissement."
        />
      </div>

      {chargement && inscriptions.length === 0 ? (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : inscriptions.length === 0 ? (
        <Card variant="soft" className="anim-float-in">
          <EmptyState
            icon={<Backpack size={24} />}
            title="Aucune inscription en attente"
            desc="Toutes les demandes d'inscription pour cet établissement ont été traitées. Les nouvelles candidatures s'afficheront ici."
          />
        </Card>
      ) : (
        <div className="space-y-4">
          {inscriptions.map((i, idx) => {
            const isRejetOpen = rejetIdOuvert === i.id;
            const isBusy = actionEnCoursId === i.id;
            const delayClass = `delay-${(idx % 3) + 1}`;

            return (
              <Card
                key={i.id}
                className={`anim-float-in ${delayClass} transition-all`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <span
                        style={{
                          fontFamily: "var(--font-display)",
                          fontSize: "var(--text-lg)",
                          fontWeight: 700,
                          color: "var(--ink)",
                        }}
                      >
                        {i.eleve_prenom} {i.eleve_nom}
                      </span>
                      <Badge tone="pending">En attente</Badge>
                      {i.consentement_parental_horodatage && (
                        <Badge tone="info" dot={false}>
                          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                            <Check size={12} aria-hidden="true" /> Consentement parental
                          </span>
                        </Badge>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      {i.eleve_matricule ? (
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            background: "var(--surface-2)",
                            padding: "3px 8px",
                            borderRadius: "var(--radius-xs)",
                            border: "1px solid var(--border)",
                            color: "var(--ink-soft)",
                            fontWeight: 600,
                          }}
                        >
                          Matricule : {i.eleve_matricule}
                        </span>
                      ) : (
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            background: "var(--surface-2)",
                            padding: "3px 8px",
                            borderRadius: "var(--radius-xs)",
                            border: "1px dashed var(--border)",
                            color: "var(--ink-faint)",
                          }}
                        >
                          Sans matricule
                        </span>
                      )}

                      <span
                        className="text-xs"
                        style={{ color: "var(--ink-faint)" }}
                      >
                        Réf. dossier :{" "}
                        <span style={{ fontFamily: "var(--font-mono)" }}>
                          {i.id.slice(0, 8)}
                        </span>
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Btn
                      variant="primary"
                      size="md"
                      onClick={() => valider(i.id)}
                      loading={isBusy}
                      leftIcon={<CheckCircle2 size={16} />}
                    >
                      Valider
                    </Btn>
                    <Btn
                      variant="action"
                      size="md"
                      onClick={() =>
                        setRejetIdOuvert(isRejetOpen ? null : i.id)
                      }
                      disabled={isBusy}
                      leftIcon={<XCircle size={16} />}
                    >
                      Rejeter
                    </Btn>
                  </div>
                </div>

                {/* Formulaire de rejet accordéon / dépliable */}
                {isRejetOpen && (
                  <div
                    className="mt-4 pt-4 anim-slide-up"
                    style={{
                      borderTop: "2px dashed var(--border)",
                      background: "var(--surface-2)",
                      borderRadius: "var(--radius-md)",
                      padding: "var(--space-4)",
                    }}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle size={16} style={{ color: "var(--action)" }} />
                      <span
                        className="text-xs font-bold"
                        style={{ color: "var(--action-deep)" }}
                      >
                        Spécifier le motif du rejet
                      </span>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-2 items-center">
                      <div className="w-full flex-1">
                        <TextInput
                          placeholder="Ex: Pièces justificatives non conformes, effectif complet..."
                          value={motifParId[i.id] ?? ""}
                          onChange={(e) =>
                            setMotifParId((prev) => ({
                              ...prev,
                              [i.id]: e.target.value,
                            }))
                          }
                          autoFocus
                        />
                      </div>
                      <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto justify-end">
                        <Btn
                          variant="action"
                          size="sm"
                          onClick={() => rejeter(i.id)}
                          loading={isBusy}
                        >
                          Confirmer le rejet
                        </Btn>
                        <Btn
                          variant="ghost"
                          size="sm"
                          onClick={() => setRejetIdOuvert(null)}
                          disabled={isBusy}
                        >
                          Annuler
                        </Btn>
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
