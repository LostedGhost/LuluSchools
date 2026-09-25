import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  creerTypeActe,
  demandesActesEtablissement,
  listerTypesActes,
  traiterDemandeActe,
} from "../../api/actes";
import { messageErreur } from "../../api/client";
import type { DemandeActeOut, TypeActeOut } from "../../types/api";
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
import { Check, FileText, ScrollText, X } from "lucide-react";
import { estRempli } from "../../utils/validation";

export function ActesAdminPage() {
  const etablissement = useAdminEtab();
  const [types, setTypes] = useState<TypeActeOut[]>([]);
  const [demandes, setDemandes] = useState<DemandeActeOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [nom, setNom] = useState("");
  const [prix, setPrix] = useState(0);
  const [piecesRequises, setPiecesRequises] = useState("");
  const [motifParId, setMotifParId] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [champErreurs, setChampErreurs] = useState<{ nom?: string; prix?: string; piecesRequises?: string }>({});

  const charger = () => {
    setChargement(true);
    Promise.all([listerTypesActes(etablissement.id), demandesActesEtablissement(etablissement.id)])
      .then(([resTypes, resDemandes]) => {
        setTypes(resTypes.data);
        setDemandes(resDemandes.data);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const soumettreType = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);

    const erreurs: typeof champErreurs = {};
    if (!estRempli(nom)) erreurs.nom = "Nom requis.";
    if (!Number.isFinite(prix) || prix < 0) erreurs.prix = "Le prix doit être 0 ou positif.";
    if (!estRempli(piecesRequises)) erreurs.piecesRequises = "Pièces requises non renseignées.";
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await creerTypeActe(etablissement.id, { nom, prix, pieces_requises: piecesRequises });
      setNom("");
      setPrix(0);
      setPiecesRequises("");
      setShowForm(false);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le type d'acte."));
    } finally {
      setEnCours(false);
    }
  };

  const traiter = async (id: string, decision: "acceptee" | "rejetee") => {
    if (decision === "rejetee" && !motifParId[id]?.trim()) {
      setErreur("Un motif est requis en cas de rejet.");
      return;
    }
    try {
      await traiterDemandeActe(id, decision, motifParId[id]);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    }
  };

  const demandesATraiter = demandes.filter((d) => d.statut === "en_traitement");

  return (
    <div className="page-content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <PageTitle eyebrow="Espace établissement">Actes académiques</PageTitle>
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "+ Ajouter un type d'acte"}
        </Btn>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>

      {showForm && (
        <Card className="mb-8 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
          <SectionHead title="Nouveau type d'acte" desc="Ex. attestation de succès, diplôme, certification de copie." />
          <form onSubmit={soumettreType} noValidate style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: "var(--space-3)", marginTop: "var(--space-4)" }}>
            <Field label="Nom" error={champErreurs.nom}>
              <TextInput value={nom} onChange={(e) => setNom(e.target.value)} />
            </Field>
            <Field label="Prix (FCFA, 0 = gratuit)" error={champErreurs.prix}>
              <TextInput type="number" min={0} value={prix} onChange={(e) => setPrix(Number(e.target.value))} style={{ width: "140px" }} />
            </Field>
            <Field label="Pièces requises" error={champErreurs.piecesRequises}>
              <TextInput value={piecesRequises} onChange={(e) => setPiecesRequises(e.target.value)} placeholder="Ex. CIP, acte de naissance" />
            </Field>
            <Btn type="submit" variant="primary" loading={enCours}>
              Ajouter
            </Btn>
          </form>
        </Card>
      )}

      {chargement ? (
        <SkeletonCard />
      ) : (
        <>
          <SectionHead title="Catalogue des actes" />
          {types.length === 0 ? (
            <EmptyState icon={<FileText size={24} />} title="Aucun type d'acte" desc="Ajoutez le premier type d'acte proposé par votre établissement." />
          ) : (
            <div className="grid-3 mb-8">
              {types.map((t) => (
                <Card key={t.id}>
                  <p style={{ fontWeight: 600, color: "var(--ink)", marginBottom: "4px" }}>{t.nom}</p>
                  <p className="monospace text-sm" style={{ color: "var(--ink-soft)", marginBottom: "8px" }}>
                    {t.prix > 0 ? `${t.prix.toLocaleString("fr-FR")} FCFA` : "Gratuit"}
                  </p>
                  <p className="text-sm" style={{ color: "var(--ink-faint)" }}>{t.pieces_requises}</p>
                </Card>
              ))}
            </div>
          )}

          <SectionHead title="Demandes à traiter" />
          {demandesATraiter.length === 0 ? (
            <EmptyState icon={<ScrollText size={24} />} title="Aucune demande en attente" desc="Toutes les demandes ont été traitées." />
          ) : (
            <div className="space-y-3">
              {demandesATraiter.map((d) => (
                <Card key={d.id}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
                    <div>
                      <span style={{ fontWeight: 600, color: "var(--ink)" }}>
                        {d.eleve_prenom} {d.eleve_nom}
                      </span>
                      {d.eleve_matricule && (
                        <span className="monospace text-sm" style={{ color: "var(--ink-faint)", marginLeft: "8px" }}>
                          {d.eleve_matricule}
                        </span>
                      )}
                    </div>
                    <Badge tone="pending">{d.est_reclamation ? "Réclamation de note" : "Demande d'acte"}</Badge>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
                    <Btn variant="primary" size="sm" onClick={() => traiter(d.id, "acceptee")} leftIcon={<Check size={14} />}>
                      Accepter
                    </Btn>
                    <TextInput
                      placeholder="Motif si rejet"
                      value={motifParId[d.id] ?? ""}
                      onChange={(e) => setMotifParId((prev) => ({ ...prev, [d.id]: e.target.value }))}
                      style={{ flex: 1, minWidth: "180px" }}
                    />
                    <Btn variant="outline" size="sm" onClick={() => traiter(d.id, "rejetee")} leftIcon={<X size={14} />}>
                      Rejeter
                    </Btn>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
