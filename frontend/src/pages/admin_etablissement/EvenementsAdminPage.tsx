import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { annulerEvenement, creerEvenement, designerParrain, listerEvenements } from "../../api/billetterie";
import { designerControleur } from "../../api/controle_acces";
import { messageErreur } from "../../api/client";
import type { EvenementOut } from "../../types/api";
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
import { Ban, CalendarDays, ShieldCheck, Star, Ticket } from "lucide-react";
import { estRempli } from "../../utils/validation";

const STATUT_TONE: Record<EvenementOut["statut"], "success" | "error"> = {
  ouvert: "success",
  annule: "error",
};

export function EvenementsAdminPage() {
  const etablissement = useAdminEtab();
  const [evenements, setEvenements] = useState<EvenementOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [actionEnCoursId, setActionEnCoursId] = useState<string | null>(null);

  const [titre, setTitre] = useState("");
  const [description, setDescription] = useState("");
  const [lieu, setLieu] = useState("");
  const [dateHeure, setDateHeure] = useState("");
  const [capaciteMax, setCapaciteMax] = useState("");
  const [prixBillet, setPrixBillet] = useState("0");

  const [parrainParId, setParrainParId] = useState<Record<string, string>>({});
  const [controleurParId, setControleurParId] = useState<Record<string, string>>({});

  const charger = () => {
    setChargement(true);
    listerEvenements(etablissement.id)
      .then((res) => setEvenements(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(titre) || !estRempli(lieu) || !dateHeure || !capaciteMax) {
      setErreur("Veuillez remplir tous les champs obligatoires.");
      return;
    }
    setErreur(null);
    setEnCours(true);
    try {
      await creerEvenement(etablissement.id, {
        titre: titre.trim(),
        description: description.trim(),
        lieu: lieu.trim(),
        date_heure: new Date(dateHeure).toISOString(),
        capacite_max: Number(capaciteMax),
        prix_billet: Number(prixBillet) || 0,
      });
      setTitre("");
      setDescription("");
      setLieu("");
      setDateHeure("");
      setCapaciteMax("");
      setPrixBillet("0");
      setShowForm(false);
      setSucces("Événement créé.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer cet événement."));
    } finally {
      setEnCours(false);
    }
  };

  const annuler = async (id: string) => {
    setActionEnCoursId(id);
    setErreur(null);
    try {
      await annulerEvenement(id);
      setSucces("Événement annulé, les billets vendus sont remboursés.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const nommerParrain = async (id: string) => {
    if (!parrainParId[id]?.trim()) return;
    setActionEnCoursId(id);
    setErreur(null);
    try {
      await designerParrain(id, parrainParId[id].trim());
      setSucces("Parrain désigné.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de désigner ce parrain. Vérifiez l'identifiant."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  const nommerControleur = async (id: string) => {
    if (!controleurParId[id]?.trim()) return;
    setActionEnCoursId(id);
    setErreur(null);
    try {
      await designerControleur(etablissement.id, controleurParId[id].trim(), "evenement", id);
      setSucces("Contrôleur d'événement désigné.");
      setControleurParId((prev) => ({ ...prev, [id]: "" }));
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de désigner ce contrôleur. Vérifiez l'identifiant."));
    } finally {
      setActionEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageTitle eyebrow="Admin Établissement">Billetterie d'événements</PageTitle>
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "+ Créer un événement"}
        </Btn>
      </div>

      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      {showForm && (
        <Card className="anim-slide-up" style={{ marginBottom: "24px" }}>
          <SectionHead title="Nouvel événement" />
          <form onSubmit={soumettre} style={{ marginTop: "16px" }}>
            <div className="grid-2">
              <Field label="Titre" required>
                <TextInput value={titre} onChange={(e) => setTitre(e.target.value)} />
              </Field>
              <Field label="Lieu" required>
                <TextInput value={lieu} onChange={(e) => setLieu(e.target.value)} />
              </Field>
              <Field label="Date et heure" required>
                <TextInput type="datetime-local" value={dateHeure} onChange={(e) => setDateHeure(e.target.value)} />
              </Field>
              <Field label="Capacité maximale" required>
                <TextInput type="number" min="1" value={capaciteMax} onChange={(e) => setCapaciteMax(e.target.value)} />
              </Field>
              <Field label="Prix du billet (FCFA)" helper="0 pour un événement gratuit.">
                <TextInput type="number" min="0" value={prixBillet} onChange={(e) => setPrixBillet(e.target.value)} />
              </Field>
              <div style={{ gridColumn: "1 / -1" }}>
                <Field label="Description">
                  <TextArea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
                </Field>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <Btn type="submit" variant="primary" loading={enCours}>Créer l'événement</Btn>
              </div>
            </div>
          </form>
        </Card>
      )}

      {chargement ? (
        <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
      ) : evenements.length === 0 ? (
        <EmptyState icon={<Ticket size={24} />} title="Aucun événement" desc="Créez votre premier événement scolaire." />
      ) : (
        <div className="space-y-4">
          {evenements.map((ev) => (
            <Card key={ev.id} className="anim-float-in">
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "16px", flexWrap: "wrap", marginBottom: "12px" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <CalendarDays size={16} style={{ color: "var(--ink-faint)" }} />
                    <h3 style={{ margin: 0, fontFamily: "var(--font-display)", fontWeight: 700 }}>{ev.titre}</h3>
                    <Badge tone={STATUT_TONE[ev.statut]}>{ev.statut === "ouvert" ? "Ouvert" : "Annulé"}</Badge>
                  </div>
                  <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                    {ev.lieu} — {new Date(ev.date_heure).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" })}
                  </p>
                  <p style={{ margin: "4px 0 0", fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
                    {ev.prix_billet > 0 ? `${ev.prix_billet.toLocaleString("fr-FR")} FCFA` : "Gratuit"} — capacité {ev.capacite_max}
                    {ev.parrain_utilisateur_id && ` — parrainé`}
                  </p>
                </div>
                {ev.statut === "ouvert" && (
                  <Btn variant="action" size="sm" loading={actionEnCoursId === ev.id} onClick={() => annuler(ev.id)} leftIcon={<Ban size={14} />}>
                    Annuler l'événement
                  </Btn>
                )}
              </div>

              {ev.statut === "ouvert" && (
                <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", paddingTop: "12px", borderTop: "1px dashed var(--border)" }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flex: 1, minWidth: "240px" }}>
                    <Field label="Désigner un parrain (ID utilisateur)">
                      <TextInput
                        value={parrainParId[ev.id] ?? ""}
                        onChange={(e) => setParrainParId((prev) => ({ ...prev, [ev.id]: e.target.value }))}
                      />
                    </Field>
                    <Btn variant="outline" size="sm" onClick={() => nommerParrain(ev.id)} leftIcon={<Star size={14} />}>OK</Btn>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flex: 1, minWidth: "240px" }}>
                    <Field label="Désigner un contrôleur (ID utilisateur)">
                      <TextInput
                        value={controleurParId[ev.id] ?? ""}
                        onChange={(e) => setControleurParId((prev) => ({ ...prev, [ev.id]: e.target.value }))}
                      />
                    </Field>
                    <Btn variant="outline" size="sm" onClick={() => nommerControleur(ev.id)} leftIcon={<ShieldCheck size={14} />}>OK</Btn>
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
