import { useEffect, useState, type FormEvent } from "react";
import { listerElevesDeLaClasse, mesClassesAffectees } from "../../api/etablissements";
import { creerEntreeVieScolaire, listerVieScolaireEleve } from "../../api/vie_scolaire";
import { messageErreur } from "../../api/client";
import type { EleveClasseOut, EntreeVieScolaireOut, NatureEntreeVieScolaire, SalleEnseignantOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  SectionHead,
  Select,
  SkeletonCard,
  SuccessBanner,
  TextArea,
  TextInput,
} from "../../components/ui";
import { estRempli } from "../../utils/validation";
import { School, Star, User, Users } from "lucide-react";

const NATURE_LABEL: Record<NatureEntreeVieScolaire, string> = {
  absence: "Absence",
  retard: "Retard",
  appreciation: "Appréciation",
  incident: "Incident",
  felicitation: "Félicitation",
};

const NATURE_TONE: Record<NatureEntreeVieScolaire, "neutral" | "success" | "error" | "pending" | "info"> = {
  absence: "pending",
  retard: "pending",
  appreciation: "info",
  incident: "error",
  felicitation: "success",
};

export function MesSallesPage() {
  const [salles, setSalles] = useState<SalleEnseignantOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [salleOuverteId, setSalleOuverteId] = useState<string | null>(null);
  const [elevesParSalle, setElevesParSalle] = useState<Record<string, EleveClasseOut[]>>({});
  const [eleveOuvertId, setEleveOuvertId] = useState<string | null>(null);

  useEffect(() => {
    mesClassesAffectees()
      .then((res) => setSalles(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, []);

  const ouvrirSalle = (salleId: string) => {
    const prochaine = salleOuverteId === salleId ? null : salleId;
    setSalleOuverteId(prochaine);
    setEleveOuvertId(null);
    if (prochaine && !elevesParSalle[salleId]) {
      listerElevesDeLaClasse(salleId)
        .then((res) => setElevesParSalle((prev) => ({ ...prev, [salleId]: res.data })))
        .catch((err) => setErreur(messageErreur(err)));
    }
  };

  return (
    <div className="page-content">
      <SectionHead
        eyebrow="Espace Enseignant"
        title="Mes salles"
        desc="Les classes qui vous sont affectées pour l'année académique en cours."
      />
      <ErrorBanner>{erreur}</ErrorBanner>

      {chargement ? (
        <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
      ) : salles.length === 0 ? (
        <EmptyState icon={<School size={24} />} title="Aucune salle affectée" desc="Aucune classe ne vous a encore été affectée par l'administration de votre établissement." />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {salles.map((salle) => (
            <Card key={salle.id} className="anim-float-in">
              <div
                style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", cursor: "pointer" }}
                onClick={() => ouvrirSalle(salle.id)}
              >
                <div>
                  <p style={{ margin: 0, fontWeight: 700, color: "var(--ink)" }}>{salle.niveau}</p>
                  <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                    {salle.etablissement_nom} — {salle.effectif}/{salle.capacite} élèves — {salle.annee_academique}
                  </p>
                </div>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  {salle.est_professeur_principal && (
                    <Badge tone="magic">
                      <Star size={12} style={{ marginRight: "4px" }} /> Professeur principal
                    </Badge>
                  )}
                  <Btn variant="outline" size="sm" leftIcon={<Users size={14} />}>
                    {salleOuverteId === salle.id ? "Masquer les élèves" : "Voir les élèves"}
                  </Btn>
                </div>
              </div>

              {salleOuverteId === salle.id && (
                <div style={{ marginTop: "16px", borderTop: "1px solid var(--border)", paddingTop: "16px" }}>
                  {!elevesParSalle[salle.id] ? (
                    <SkeletonCard />
                  ) : elevesParSalle[salle.id].length === 0 ? (
                    <EmptyState icon={<User size={20} />} title="Aucun élève inscrit" />
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {elevesParSalle[salle.id].map((eleve) => (
                        <div key={eleve.eleve_id}>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "8px",
                              padding: "8px 12px",
                              borderRadius: "var(--radius-sm)",
                              background: "var(--surface-2)",
                              cursor: "pointer",
                            }}
                            onClick={() => setEleveOuvertId(eleveOuvertId === eleve.eleve_id ? null : eleve.eleve_id)}
                          >
                            <span style={{ fontSize: "var(--text-sm)" }}>
                              {eleve.prenom} {eleve.nom}
                              {eleve.matricule && (
                                <span style={{ color: "var(--ink-faint)", marginLeft: "6px", fontFamily: "var(--font-mono)" }}>
                                  {eleve.matricule}
                                </span>
                              )}
                            </span>
                            <Btn variant="ghost" size="sm">
                              {eleveOuvertId === eleve.eleve_id ? "Fermer" : "Vie scolaire"}
                            </Btn>
                          </div>
                          {eleveOuvertId === eleve.eleve_id && (
                            <VieScolaireEleve
                              classeId={salle.id}
                              eleveId={eleve.eleve_id}
                              estProfesseurPrincipal={salle.est_professeur_principal}
                            />
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
    </div>
  );
}

function VieScolaireEleve({
  classeId,
  eleveId,
  estProfesseurPrincipal,
}: {
  classeId: string;
  eleveId: string;
  estProfesseurPrincipal: boolean;
}) {
  const [entrees, setEntrees] = useState<EntreeVieScolaireOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const [nature, setNature] = useState<NatureEntreeVieScolaire>("appreciation");
  const [matiere, setMatiere] = useState("");
  const [description, setDescription] = useState("");
  const [entreeGlobale, setEntreeGlobale] = useState(false);

  const charger = () => {
    setChargement(true);
    listerVieScolaireEleve(classeId, eleveId)
      .then((res) => setEntrees(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [classeId, eleveId]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);
    if (!estRempli(description)) {
      setErreur("Veuillez décrire l'entrée.");
      return;
    }
    if (!entreeGlobale && !estRempli(matiere)) {
      setErreur("Précisez la matière, ou cochez « entrée générale » si vous êtes professeur principal.");
      return;
    }
    setEnCours(true);
    try {
      await creerEntreeVieScolaire(classeId, eleveId, {
        nature,
        matiere: entreeGlobale ? null : matiere.trim(),
        description: description.trim(),
      });
      setDescription("");
      setSucces("Entrée enregistrée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer cette entrée."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div style={{ padding: "12px", marginTop: "6px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>

      <form onSubmit={soumettre} style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "flex-end", marginBottom: "12px" }}>
        <div style={{ minWidth: "160px" }}>
          <Field label="Nature">
            <Select value={nature} onChange={(e) => setNature(e.target.value as NatureEntreeVieScolaire)}>
              {Object.entries(NATURE_LABEL).map(([valeur, libelle]) => (
                <option key={valeur} value={valeur}>{libelle}</option>
              ))}
            </Select>
          </Field>
        </div>
        {!entreeGlobale && (
          <div style={{ minWidth: "160px" }}>
            <Field label="Matière">
              <TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} placeholder="Ex. Mathématiques" />
            </Field>
          </div>
        )}
        {estProfesseurPrincipal && (
          <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "var(--text-sm)", marginBottom: "10px" }}>
            <input type="checkbox" checked={entreeGlobale} onChange={(e) => setEntreeGlobale(e.target.checked)} />
            Entrée générale (toutes matières)
          </label>
        )}
        <div style={{ flex: 1, minWidth: "220px" }}>
          <Field label="Description">
            <TextArea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
        </div>
        <Btn type="submit" variant="primary" size="sm" loading={enCours}>
          Ajouter
        </Btn>
      </form>

      {chargement ? (
        <SkeletonCard />
      ) : entrees.length === 0 ? (
        <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-faint)", margin: 0 }}>Aucune entrée de vie scolaire.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {entrees.map((entree) => (
            <div key={entree.id} style={{ display: "flex", alignItems: "baseline", gap: "8px", fontSize: "var(--text-sm)" }}>
              <Badge tone={NATURE_TONE[entree.nature]}>{NATURE_LABEL[entree.nature]}</Badge>
              {entree.matiere && <span style={{ color: "var(--ink-faint)" }}>({entree.matiere})</span>}
              <span style={{ color: "var(--ink-faint)" }}>{new Date(entree.date_survenue).toLocaleDateString("fr-FR")}</span>
              <span>{entree.description}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
