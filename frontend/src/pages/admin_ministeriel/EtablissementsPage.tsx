import { useEffect, useState, type FormEvent } from "react";
import { creerEtablissement, listerEtablissements, mettreAJourLocalisation } from "../../api/etablissements";
import { messageErreur } from "../../api/client";
import type { EtablissementOut, TypeEtablissement } from "../../types/api";
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
import { LocationPicker } from "../../components/LocationPicker";
import { Building2, MapPin } from "lucide-react";
import { lienGoogleMaps } from "../../utils/geo";
import { PHOTOS_PAR_DEFAUT } from "../../utils/photosParDefaut";
import { estRempli, estEmailValide } from "../../utils/validation";

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

      <SectionHead title="Établissements du réseau" />
      {chargement ? (
        <div className="grid-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : etablissements.length === 0 ? (
        <EmptyState photo={PHOTOS_PAR_DEFAUT.ES[0].url} title="Aucun établissement" desc="Créez le premier établissement du réseau ci-dessus." />
      ) : (
        <div className="grid-3">
          {etablissements.map((e) => (
            <Card key={e.id}>
              <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-2)" }}>
                <div style={{
                  width: "40px", height: "40px", borderRadius: "var(--radius-md)",
                  background: "var(--primary-tint)", color: "var(--primary-deep)",
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }} aria-hidden="true">
                  <Building2 size={20} />
                </div>
                <span style={{ fontWeight: 600, color: "var(--ink)" }}>{e.nom}</span>
              </div>
              <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-3)" }}>
                <Badge tone="neutral">{e.code_etablissement}</Badge>
                <Badge tone="info">{e.type}</Badge>
              </div>

              {editionLocalisationId === e.id ? (
                <div style={{ paddingTop: "var(--space-3)", borderTop: "1px dashed var(--border)" }}>
                  <LocationPicker latitude={latModif} longitude={lngModif} onChange={(lat, lng) => { setLatModif(lat); setLngModif(lng); }} />
                  <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                    <Btn size="sm" variant="primary" loading={enCoursModif} onClick={() => enregistrerLocalisation(e.id)}>Enregistrer</Btn>
                    <Btn size="sm" variant="ghost" onClick={() => setEditionLocalisationId(null)}>Annuler</Btn>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", paddingTop: "var(--space-3)", borderTop: "1px dashed var(--border)" }}>
                  {e.latitude !== null && e.longitude !== null ? (
                    <a href={lienGoogleMaps(e.latitude, e.longitude)} target="_blank" rel="noopener noreferrer" className="text-sm" style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "var(--primary-deep)" }}>
                      <MapPin size={14} /> Voir sur Google Maps
                    </a>
                  ) : (
                    <span className="text-sm" style={{ color: "var(--ink-faint)" }}>Position non renseignée</span>
                  )}
                  <Btn size="sm" variant="ghost" onClick={() => ouvrirEditionLocalisation(e)}>Modifier</Btn>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
