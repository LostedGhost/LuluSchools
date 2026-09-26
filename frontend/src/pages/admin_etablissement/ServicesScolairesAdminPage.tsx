import { useEffect, useState, type FormEvent } from "react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import {
  creerLigneTransport,
  creerTypeRepasCantine,
  listerLignesTransport,
  listerTypesRepasCantine,
} from "../../api/services_scolaires";
import { designerControleur, listerControleurs, revoquerControleur } from "../../api/controle_acces";
import { messageErreur } from "../../api/client";
import type { DesignationControleurOut, LigneTransportOut, ServiceControle, TypeRepasCantineOut } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  Select,
  SkeletonCard,
  SuccessBanner,
  TextInput,
} from "../../components/ui";
import { Bus, ShieldCheck, Trash2, Utensils } from "lucide-react";
import { estRempli } from "../../utils/validation";

const SERVICE_LABEL: Record<ServiceControle, string> = {
  transport: "Transport",
  cantine: "Cantine",
  evenement: "Événement",
};

export function ServicesScolairesAdminPage() {
  const etablissement = useAdminEtab();
  const [lignes, setLignes] = useState<LigneTransportOut[]>([]);
  const [types, setTypes] = useState<TypeRepasCantineOut[]>([]);
  const [controleurs, setControleurs] = useState<DesignationControleurOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  const [nomLigne, setNomLigne] = useState("");
  const [prixLigne, setPrixLigne] = useState("");
  const [capaciteLigne, setCapaciteLigne] = useState("");
  const [enCoursLigne, setEnCoursLigne] = useState(false);

  const [nomType, setNomType] = useState("");
  const [prixType, setPrixType] = useState("");
  const [capaciteType, setCapaciteType] = useState("");
  const [enCoursType, setEnCoursType] = useState(false);

  const [utilisateurIdControleur, setUtilisateurIdControleur] = useState("");
  const [serviceControleur, setServiceControleur] = useState<ServiceControle>("transport");
  const [enCoursControleur, setEnCoursControleur] = useState(false);
  const [revocationEnCoursId, setRevocationEnCoursId] = useState<string | null>(null);

  const charger = () => {
    setChargement(true);
    Promise.all([
      listerLignesTransport(etablissement.id),
      listerTypesRepasCantine(etablissement.id),
      listerControleurs(etablissement.id),
    ])
      .then(([resLignes, resTypes, resControleurs]) => {
        setLignes(resLignes.data);
        setTypes(resTypes.data);
        setControleurs(resControleurs.data);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, [etablissement.id]);

  const soumettreLigne = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(nomLigne) || !prixLigne || !capaciteLigne) {
      setErreur("Veuillez remplir tous les champs de la ligne de transport.");
      return;
    }
    setErreur(null);
    setEnCoursLigne(true);
    try {
      await creerLigneTransport(etablissement.id, nomLigne.trim(), Number(prixLigne), Number(capaciteLigne));
      setNomLigne("");
      setPrixLigne("");
      setCapaciteLigne("");
      setSucces("Ligne de transport créée.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer cette ligne."));
    } finally {
      setEnCoursLigne(false);
    }
  };

  const soumettreType = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(nomType) || !prixType || !capaciteType) {
      setErreur("Veuillez remplir tous les champs du service de cantine.");
      return;
    }
    setErreur(null);
    setEnCoursType(true);
    try {
      await creerTypeRepasCantine(etablissement.id, nomType.trim(), Number(prixType), Number(capaciteType));
      setNomType("");
      setPrixType("");
      setCapaciteType("");
      setSucces("Service de cantine créé.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer ce service."));
    } finally {
      setEnCoursType(false);
    }
  };

  const soumettreControleur = async (e: FormEvent) => {
    e.preventDefault();
    if (!estRempli(utilisateurIdControleur)) {
      setErreur("Veuillez saisir l'identifiant de l'utilisateur à désigner.");
      return;
    }
    setErreur(null);
    setEnCoursControleur(true);
    try {
      await designerControleur(etablissement.id, utilisateurIdControleur.trim(), serviceControleur);
      setUtilisateurIdControleur("");
      setSucces("Contrôleur désigné.");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de désigner ce contrôleur. Vérifiez l'identifiant."));
    } finally {
      setEnCoursControleur(false);
    }
  };

  const revoquer = async (designationId: string) => {
    setRevocationEnCoursId(designationId);
    setErreur(null);
    try {
      await revoquerControleur(designationId);
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setRevocationEnCoursId(null);
    }
  };

  if (chargement) {
    return <div className="page-content"><SkeletonCard /></div>;
  }

  return (
    <div className="page-content">
      <PageTitle eyebrow="Admin Établissement">Transport, cantine et contrôleurs</PageTitle>
      <div className="mb-6 space-y-3">
        <ErrorBanner>{erreur}</ErrorBanner>
        <SuccessBanner>{succes}</SuccessBanner>
      </div>

      <div className="grid-2" style={{ marginBottom: "32px" }}>
        {/* Transport */}
        <div>
          <SectionHead title="Lignes de transport" />
          <Card variant="soft" style={{ marginBottom: "16px" }}>
            <form onSubmit={soumettreLigne} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Field label="Nom de la ligne" required>
                <TextInput value={nomLigne} onChange={(e) => setNomLigne(e.target.value)} placeholder="Ex. Ligne A — Centre-ville" />
              </Field>
              <div style={{ display: "flex", gap: "12px" }}>
                <Field label="Prix (FCFA)" required>
                  <TextInput type="number" min="0" value={prixLigne} onChange={(e) => setPrixLigne(e.target.value)} />
                </Field>
                <Field label="Capacité / trajet" required>
                  <TextInput type="number" min="1" value={capaciteLigne} onChange={(e) => setCapaciteLigne(e.target.value)} />
                </Field>
              </div>
              <Btn type="submit" variant="primary" size="sm" loading={enCoursLigne} leftIcon={<Bus size={14} />}>
                Ajouter la ligne
              </Btn>
            </form>
          </Card>
          {lignes.length === 0 ? (
            <EmptyState icon={<Bus size={20} />} title="Aucune ligne" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {lignes.map((l) => (
                <Card key={l.id}>
                  <p style={{ margin: 0, fontWeight: 600 }}>{l.nom}</p>
                  <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                    {l.prix.toLocaleString("fr-FR")} FCFA — capacité {l.capacite_par_trajet}/trajet
                  </p>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Cantine */}
        <div>
          <SectionHead title="Services de cantine" />
          <Card variant="soft" style={{ marginBottom: "16px" }}>
            <form onSubmit={soumettreType} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Field label="Nom du service" required>
                <TextInput value={nomType} onChange={(e) => setNomType(e.target.value)} placeholder="Ex. Déjeuner complet" />
              </Field>
              <div style={{ display: "flex", gap: "12px" }}>
                <Field label="Prix (FCFA)" required>
                  <TextInput type="number" min="0" value={prixType} onChange={(e) => setPrixType(e.target.value)} />
                </Field>
                <Field label="Capacité / jour" required>
                  <TextInput type="number" min="1" value={capaciteType} onChange={(e) => setCapaciteType(e.target.value)} />
                </Field>
              </div>
              <Btn type="submit" variant="primary" size="sm" loading={enCoursType} leftIcon={<Utensils size={14} />}>
                Ajouter le service
              </Btn>
            </form>
          </Card>
          {types.length === 0 ? (
            <EmptyState icon={<Utensils size={20} />} title="Aucun service" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {types.map((t) => (
                <Card key={t.id}>
                  <p style={{ margin: 0, fontWeight: 600 }}>{t.nom}</p>
                  <p style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                    {t.prix.toLocaleString("fr-FR")} FCFA — capacité {t.capacite_par_jour}/jour
                  </p>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Contrôleurs */}
      <div>
        <SectionHead
          title="Contrôleurs désignés"
          desc="Un contrôleur peut valider les tickets achetés (transport, cantine ou un événement précis) une fois le paiement confirmé."
        />
        <Card variant="soft" style={{ marginBottom: "16px" }}>
          <form onSubmit={soumettreControleur} style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "flex-end" }}>
            <div style={{ flex: 1, minWidth: "220px" }}>
              <Field label="Identifiant utilisateur" required helper="ID interne du compte à désigner comme contrôleur.">
                <TextInput value={utilisateurIdControleur} onChange={(e) => setUtilisateurIdControleur(e.target.value)} placeholder="ID utilisateur" />
              </Field>
            </div>
            <div style={{ minWidth: "160px" }}>
              <Field label="Service">
                <Select value={serviceControleur} onChange={(e: any) => setServiceControleur(e.target.value as ServiceControle)}>
                  <option value="transport">Transport</option>
                  <option value="cantine">Cantine</option>
                </Select>
              </Field>
            </div>
            <Btn type="submit" variant="primary" size="sm" loading={enCoursControleur} leftIcon={<ShieldCheck size={14} />}>
              Désigner
            </Btn>
          </form>
        </Card>

        {controleurs.length === 0 ? (
          <EmptyState icon={<ShieldCheck size={20} />} title="Aucun contrôleur désigné" />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {controleurs.map((c) => (
              <Card key={c.id}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                  <div>
                    <p style={{ margin: 0, fontFamily: "var(--font-mono)", fontSize: "var(--text-sm)" }}>{c.utilisateur_id}</p>
                    <Badge tone="info">{SERVICE_LABEL[c.service]}</Badge>
                  </div>
                  <Btn variant="ghost" size="sm" loading={revocationEnCoursId === c.id} onClick={() => revoquer(c.id)} leftIcon={<Trash2 size={14} />}>
                    Révoquer
                  </Btn>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
