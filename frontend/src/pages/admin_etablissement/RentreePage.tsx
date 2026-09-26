import { useEffect, useState } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { declarerRentree, inviterTuteurs, listerRentrees } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { RentreeOut } from "../../types/api";
import { Badge, Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, SuccessBanner, TextInput } from "../../components/ui";
import { Mail, Send } from "lucide-react";
import { estRempli } from "../../utils/validation";

function anneeAcademiqueCourante(): string {
  const aujourdhui = new Date();
  const premiere = aujourdhui.getMonth() >= 8 ? aujourdhui.getFullYear() : aujourdhui.getFullYear() - 1;
  return `${premiere}-${premiere + 1}`;
}

export function RentreePage() {
  const etablissement = useAdminEtab();
  const [rentrees, setRentrees] = useState<RentreeOut[]>([]);
  const [annee, setAnnee] = useState(anneeAcademiqueCourante());
  const [chargement, setChargement] = useState(true);
  const [enCours, setEnCours] = useState(false);
  const [invitationEnCoursId, setInvitationEnCoursId] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    listerRentrees(etablissement.id)
      .then((res) => setRentrees(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const declarer = async () => {
    if (!estRempli(annee)) {
      setErreur("Précisez l'année académique.");
      return;
    }
    setEnCours(true);
    setErreur(null);
    setSucces(null);
    try {
      await declarerRentree(etablissement.id, annee.trim());
      setSucces(`Rentrée ${annee.trim()} ouverte.`);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de déclarer cette rentrée."));
    } finally {
      setEnCours(false);
    }
  };

  const inviter = async (rentreeId: string) => {
    setInvitationEnCoursId(rentreeId);
    setErreur(null);
    setSucces(null);
    try {
      const res = await inviterTuteurs(etablissement.id, rentreeId);
      setSucces(`${res.data.nb_tuteurs_notifies} tuteur(s) notifié(s) par e-mail.`);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'inviter les tuteurs."));
    } finally {
      setInvitationEnCoursId(null);
    }
  };

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Établissement">Rentrée scolaire</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && <div className="mb-4"><SuccessBanner>{succes}</SuccessBanner></div>}

      <Card className="mb-8" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
        <SectionHead
          title="Déclarer une rentrée"
          desc="Ouvre l'établissement aux (ré)inscriptions pour une année académique — ferme automatiquement toute rentrée déjà ouverte."
        />
        <div style={{ display: "flex", alignItems: "flex-end", gap: "var(--space-3)", marginTop: "var(--space-4)", flexWrap: "wrap" }}>
          <Field label="Année académique">
            <TextInput value={annee} onChange={(e) => setAnnee(e.target.value)} placeholder={anneeAcademiqueCourante()} style={{ width: "180px" }} />
          </Field>
          <Btn variant="primary" loading={enCours} onClick={declarer} leftIcon={<Send size={16} />}>
            Ouvrir la rentrée
          </Btn>
        </div>
      </Card>

      <SectionHead title="Historique des rentrées" />
      {!chargement && rentrees.length === 0 && (
        <p className="text-sm" style={{ color: "var(--ink-soft)" }}>Aucune rentrée déclarée pour l'instant.</p>
      )}
      <div className="space-y-3">
        {rentrees.map((r) => (
          <Card key={r.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "var(--space-3)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontWeight: 600, color: "var(--ink)" }}>{r.annee_academique}</span>
                <Badge tone={r.statut === "ouverte" ? "success" : "neutral"}>{r.statut === "ouverte" ? "Ouverte" : "Fermée"}</Badge>
              </div>
              <Btn
                variant="outline"
                size="sm"
                loading={invitationEnCoursId === r.id}
                onClick={() => inviter(r.id)}
                leftIcon={<Mail size={14} />}
              >
                Inviter les tuteurs déjà connus
              </Btn>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
