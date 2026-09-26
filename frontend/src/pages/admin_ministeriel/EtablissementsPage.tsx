import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  actionGroupeeEtablissements,
  creerEtablissement,
  listerEtablissements,
  mettreAJourLocalisation,
  modifierDescriptionEtablissement,
} from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, TypeEtablissement } from "../../types/api";
import {
  Badge,
  Btn,
  Card,
  ErrorBanner,
  Field,
  PageTitle,
  SectionHead,
  Select,
  SuccessBanner,
  TextArea,
  TextInput,
} from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { LocationPicker } from "../../components/LocationPicker";
import { PhotosEtablissementManager } from "../../components/PhotosEtablissementManager";
import { Ban, Building2, CheckCircle2, ChevronDown, ChevronUp, MapPin } from "lucide-react";
import { lienGoogleMaps } from "../../utils/geo";
import { estRempli, estEmailValide } from "../../utils/validation";

const TYPE_LABEL: Record<TypeEtablissement, string> = { EP: "Primaire", ES: "Secondaire", UP: "Supérieur" };

export function EtablissementsPage() {
  const [etablissements, setEtablissements] = useState<EtablissementOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [nom, setNom] = useState("");
  const [type, setType] = useState<TypeEtablissement>("EP");
  const [statut, setStatut] = useState<"public" | "prive">("public");
  const [adminNom, setAdminNom] = useState("");
  const [adminPrenom, setAdminPrenom] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [champErreurs, setChampErreurs] = useState<{ nom?: string; adminNom?: string; adminPrenom?: string; adminEmail?: string; localisation?: string }>({});

  // Table + recherche/filtre (UC-25)
  const [recherche, setRecherche] = useState("");
  const [filtreType, setFiltreType] = useState<"" | TypeEtablissement>("");
  const [filtreActif, setFiltreActif] = useState<"" | "actif" | "suspendu">("");
  const [selection, setSelection] = useState<Set<string>>(new Set());
  const [enCoursActionGroupee, setEnCoursActionGroupee] = useState(false);
  const [motifActionGroupee, setMotifActionGroupee] = useState("");

  // Fiche détaillée (UC-23/24/40) : ouverte en cliquant une ligne
  const [ficheOuverteId, setFicheOuverteId] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [enregistrementDescription, setEnregistrementDescription] = useState(false);
  const [editionLocalisationId, setEditionLocalisationId] = useState<string | null>(null);
  const [latModif, setLatModif] = useState("");
  const [lngModif, setLngModif] = useState("");
  const [enCoursModif, setEnCoursModif] = useState(false);

  const charger = () => {
    setChargement(true);
    listerEtablissements()
      .then((res) => setEtablissements(res.data))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(charger, []);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);

    const erreurs: typeof champErreurs = {};
    if (!estRempli(nom)) erreurs.nom = "Nom de l'établissement requis.";
    if (!estRempli(adminNom)) erreurs.adminNom = "Nom de l'administrateur requis.";
    if (!estRempli(adminPrenom)) erreurs.adminPrenom = "Prénom de l'administrateur requis.";
    if (!estEmailValide(adminEmail)) erreurs.adminEmail = "Adresse e-mail invalide.";
    const lat = Number(latitude);
    const lng = Number(longitude);
    if (!estRempli(latitude) || !estRempli(longitude) || Number.isNaN(lat) || Number.isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      erreurs.localisation = "Coordonnées requises (utilisez le bouton de géolocalisation ou saisissez-les manuellement).";
    }
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await creerEtablissement({
        nom,
        type,
        statut,
        admin: { nom: adminNom, prenom: adminPrenom, email: adminEmail },
        latitude: lat,
        longitude: lng,
      });
      setSucces(`Établissement créé. Identifiants temporaires envoyés à ${adminEmail}.`);
      setNom("");
      setAdminNom("");
      setAdminPrenom("");
      setAdminEmail("");
      setLatitude("");
      setLongitude("");
      setShowForm(false);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer l'établissement."));
    } finally {
      setEnCours(false);
    }
  };

  const ouvrirFiche = (etablissement: EtablissementOut) => {
    if (ficheOuverteId === etablissement.id) {
      setFicheOuverteId(null);
      return;
    }
    setFicheOuverteId(etablissement.id);
    setDescription(etablissement.description ?? "");
    setEditionLocalisationId(null);
  };

  const enregistrerDescription = async (etablissementId: string) => {
    setEnregistrementDescription(true);
    setErreur(null);
    try {
      await modifierDescriptionEtablissement(etablissementId, description || null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer la description."));
    } finally {
      setEnregistrementDescription(false);
    }
  };

  const ouvrirEditionLocalisation = (etablissement: EtablissementOut) => {
    setEditionLocalisationId(etablissement.id);
    setLatModif(etablissement.latitude?.toString() ?? "");
    setLngModif(etablissement.longitude?.toString() ?? "");
  };

  const enregistrerLocalisation = async (etablissementId: string) => {
    const lat = Number(latModif);
    const lng = Number(lngModif);
    if (Number.isNaN(lat) || Number.isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      setErreur("Coordonnées invalides.");
      return;
    }
    setEnCoursModif(true);
    setErreur(null);
    try {
      await mettreAJourLocalisation(etablissementId, lat, lng);
      setEditionLocalisationId(null);
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de mettre à jour la localisation."));
    } finally {
      setEnCoursModif(false);
    }
  };

  const appliquerActionGroupee = async (action: "suspendre" | "reactiver") => {
    if (!estRempli(motifActionGroupee)) {
      setErreur("Un motif est requis pour cette action groupée.");
      return;
    }
    setEnCoursActionGroupee(true);
    setErreur(null);
    try {
      await actionGroupeeEtablissements(Array.from(selection), action, motifActionGroupee);
      setSelection(new Set());
      setMotifActionGroupee("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'appliquer cette action groupée."));
    } finally {
      setEnCoursActionGroupee(false);
    }
  };

  const etablissementsFiltres = useMemo(() => {
    return etablissements.filter((e) => {
      if (recherche && !`${e.nom} ${e.code_etablissement}`.toLowerCase().includes(recherche.toLowerCase())) return false;
      if (filtreType && e.type !== filtreType) return false;
      if (filtreActif === "actif" && !e.actif) return false;
      if (filtreActif === "suspendu" && e.actif) return false;
      return true;
    });
  }, [etablissements, recherche, filtreType, filtreActif]);

  const colonnes: DataTableColumn<EtablissementOut>[] = [
    {
      key: "nom",
      header: "Établissement",
      render: (e) => (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Building2 size={16} style={{ color: "var(--primary-deep)", flexShrink: 0 }} />
          <span style={{ fontWeight: 600 }}>{e.nom}</span>
          {!e.actif && <Badge tone="error">Suspendu</Badge>}
        </div>
      ),
    },
    { key: "code", header: "Code", render: (e) => <span className="monospace text-sm">{e.code_etablissement}</span> },
    { key: "type", header: "Type", render: (e) => <Badge tone="info">{TYPE_LABEL[e.type]}</Badge> },
    { key: "statut", header: "Statut", render: (e) => (e.statut === "public" ? "Public" : "Privé") },
    {
      key: "localisation",
      header: "Localisation",
      render: (e) =>
        e.latitude !== null && e.longitude !== null ? (
          <a
            href={lienGoogleMaps(e.latitude, e.longitude)}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(ev) => ev.stopPropagation()}
            style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--primary-deep)" }}
          >
            <MapPin size={14} /> Voir
          </a>
        ) : (
          <span style={{ color: "var(--ink-faint)" }}>Non renseignée</span>
        ),
    },
    {
      key: "fiche",
      header: "",
      render: (e) => (ficheOuverteId === e.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />),
      width: "32px",
    },
  ];

  return (
    <div className="page-content">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
        <PageTitle eyebrow="Espace ministériel">Établissements</PageTitle>
        <Btn variant="primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Fermer" : "+ Créer un établissement"}
        </Btn>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && (
        <div className="mb-4">
          <SuccessBanner>{succes}</SuccessBanner>
        </div>
      )}

      {showForm && (
        <Card className="mb-8 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
          <SectionHead title="Créer un établissement" desc="Provisionne aussi le premier compte A+, avec mot de passe temporaire envoyé par e-mail." />
          <form onSubmit={soumettre} noValidate className="space-y-4" style={{ marginTop: "var(--space-4)" }}>
            <div className="grid-3">
              <Field label="Nom" error={champErreurs.nom}>
                <TextInput value={nom} onChange={(e) => setNom(e.target.value)} />
              </Field>
              <Field label="Type">
                <Select value={type} onChange={(e) => setType(e.target.value as TypeEtablissement)}>
                  <option value="EP">Primaire (EP)</option>
                  <option value="ES">Secondaire (ES)</option>
                  <option value="UP">Universitaire (UP)</option>
                </Select>
              </Field>
              <Field label="Statut">
                <Select value={statut} onChange={(e) => setStatut(e.target.value as "public" | "prive")}>
                  <option value="public">Public</option>
                  <option value="prive">Privé</option>
                </Select>
              </Field>
            </div>
            <p className="text-eyebrow">Administrateur de l'établissement</p>
            <div className="grid-3">
              <Field label="Nom" error={champErreurs.adminNom}>
                <TextInput value={adminNom} onChange={(e) => setAdminNom(e.target.value)} />
              </Field>
              <Field label="Prénom" error={champErreurs.adminPrenom}>
                <TextInput value={adminPrenom} onChange={(e) => setAdminPrenom(e.target.value)} />
              </Field>
              <Field label="E-mail" error={champErreurs.adminEmail}>
                <TextInput type="email" value={adminEmail} onChange={(e) => setAdminEmail(e.target.value)} />
              </Field>
            </div>
            <p className="text-eyebrow">Localisation</p>
            <div className="grid-2">
              <LocationPicker
                latitude={latitude}
                longitude={longitude}
                onChange={(lat, lng) => { setLatitude(lat); setLongitude(lng); }}
              />
            </div>
            {champErreurs.localisation && (
              <p className="text-sm" style={{ color: "var(--action-deep)", margin: 0 }}>{champErreurs.localisation}</p>
            )}
            <Btn type="submit" variant="primary" loading={enCours}>
              Créer l'établissement
            </Btn>
          </form>
        </Card>
      )}

      <SectionHead title="Établissements du réseau" desc="Cliquez une ligne pour voir la fiche complète (photos, description, localisation)." />

      <DataTable
        columns={colonnes}
        rows={etablissementsFiltres}
        rowKey={(e) => e.id}
        loading={chargement}
        emptyTitle="Aucun établissement"
        emptyDesc="Créez le premier établissement du réseau ci-dessus."
        searchValue={recherche}
        onSearchChange={setRecherche}
        searchPlaceholder="Rechercher par nom ou code..."
        filters={
          <>
            <Select value={filtreType} onChange={(e) => setFiltreType(e.target.value as "" | TypeEtablissement)} style={{ width: "160px" }}>
              <option value="">Tous les types</option>
              <option value="EP">Primaire</option>
              <option value="ES">Secondaire</option>
              <option value="UP">Supérieur</option>
            </Select>
            <Select value={filtreActif} onChange={(e) => setFiltreActif(e.target.value as "" | "actif" | "suspendu")} style={{ width: "160px" }}>
              <option value="">Tous statuts</option>
              <option value="actif">Actifs</option>
              <option value="suspendu">Suspendus</option>
            </Select>
          </>
        }
        selectable
        selectedIds={selection}
        onSelectionChange={setSelection}
        onRowClick={ouvrirFiche}
        bulkActions={[
          {
            label: "Suspendre",
            icon: <Ban size={14} />,
            variant: "action",
            loading: enCoursActionGroupee,
            onClick: () => appliquerActionGroupee("suspendre"),
          },
          {
            label: "Réactiver",
            icon: <CheckCircle2 size={14} />,
            variant: "outline",
            loading: enCoursActionGroupee,
            onClick: () => appliquerActionGroupee("reactiver"),
          },
        ]}
      />

      {selection.size > 0 && (
        <div style={{ marginTop: "10px" }}>
          <Field label="Motif de l'action groupée (obligatoire)" helper="Journalisé dans le journal d'audit ministériel.">
            <TextInput value={motifActionGroupee} onChange={(e) => setMotifActionGroupee(e.target.value)} placeholder="Ex. Contrôle administratif en cours" />
          </Field>
        </div>
      )}

      {ficheOuverteId && (
        <Card className="mt-6 anim-slide-up" style={{ borderColor: "var(--primary)", borderWidth: "2px" }}>
          {(() => {
            const etablissement = etablissements.find((e) => e.id === ficheOuverteId);
            if (!etablissement) return null;
            return (
              <>
                <SectionHead title={etablissement.nom} desc="Fiche complète : description, photos et localisation." />

                <Field label="Description">
                  <TextArea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Présentation de l'établissement (affichée sur l'annuaire public)."
                    rows={4}
                  />
                </Field>
                <div style={{ marginTop: "8px" }}>
                  <Btn size="sm" variant="primary" loading={enregistrementDescription} onClick={() => enregistrerDescription(etablissement.id)}>
                    Enregistrer la description
                  </Btn>
                </div>

                <div style={{ marginTop: "var(--space-4)", paddingTop: "var(--space-4)", borderTop: "1px dashed var(--border)" }}>
                  {editionLocalisationId === etablissement.id ? (
                    <>
                      <LocationPicker latitude={latModif} longitude={lngModif} onChange={(lat, lng) => { setLatModif(lat); setLngModif(lng); }} />
                      <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                        <Btn size="sm" variant="primary" loading={enCoursModif} onClick={() => enregistrerLocalisation(etablissement.id)}>Enregistrer</Btn>
                        <Btn size="sm" variant="ghost" onClick={() => setEditionLocalisationId(null)}>Annuler</Btn>
                      </div>
                    </>
                  ) : (
                    <Btn size="sm" variant="outline" onClick={() => ouvrirEditionLocalisation(etablissement)}>Modifier la localisation</Btn>
                  )}
                </div>

                <PhotosEtablissementManager etablissementId={etablissement.id} />
              </>
            );
          })()}
        </Card>
      )}
    </div>
  );
}
