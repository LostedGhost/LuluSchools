import { useEffect, useState } from "react";
import { Download, GraduationCap, Landmark, Scale, Soup, Users, Accessibility, CalendarX, Wrench, BookOpenCheck } from "lucide-react";
import { messageErreur } from "../../api/client";
import { listerTerritoires } from "../../api/etablissements";
import { exporterIndicateursCsv, obtenirIndicateurs, type IndicateursOut } from "../../api/indicateurs";
import { useAuth } from "../../auth/AuthContext";
import { Btn, ErrorBanner, Field, KPITile, SectionHead, Select, Skeleton } from "../../components/ui";
import { ouvrirBlobPdf } from "../../utils/telechargerBlob";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.6 — indicateurs de pilotage (suivi-évaluation du PAG 2021-2026).
   Tout est recalculé depuis la base ; « masqué » = moins de 5 élèves concernés
   (protection des données des mineurs). A+ : son établissement seulement.
   ═══════════════════════════════════════════════════════════════ */

function anneesDisponibles(): string[] {
  const maintenant = new Date();
  const debut = maintenant.getMonth() >= 8 ? maintenant.getFullYear() : maintenant.getFullYear() - 1;
  return [0, 1, 2].map((i) => `${debut - i}-${debut - i + 1}`);
}

const nombre = (v: number | null | undefined) => (v === null || v === undefined ? "masqué" : v.toLocaleString("fr-FR"));
const pourcent = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${v.toLocaleString("fr-FR")} %`);

const ALIGNEMENT_PAG: { orientation: string; indicateurs: string }[] = [
  { orientation: "Restructuration du système éducatif — qualité des formations", indicateurs: "Taux de réussite, élèves par enseignant sous contrat" },
  { orientation: "Enseignement et formation techniques et professionnels (EFTP)", indicateurs: "Part des élèves en classes techniques et professionnelles, stages, compétences métier" },
  { orientation: "Alphabétisation et éducation des adultes", indicateurs: "Adultes inscrits en centre d'alphabétisation" },
  { orientation: "Amélioration des conditions d'études — cantines scolaires", indicateurs: "Élèves bénéficiaires de la cantine, repas servis" },
  { orientation: "Égalité filles-garçons (ODD 4)", indicateurs: "Indice de parité des effectifs, réussite des filles et des garçons" },
  { orientation: "Inclusion — handicap, alphabétisation", indicateurs: "Cours oraux transcrits, comptes en mode Écoute, messages vocaux" },
  { orientation: "Bonne gouvernance et redevabilité", indicateurs: "Chiffres recalculés depuis la base, export tableur, journal d'audit" },
];

export function IndicateursPage() {
  const { utilisateur } = useAuth();
  const national = utilisateur?.role === "admin_ministeriel";
  const [annee, setAnnee] = useState(anneesDisponibles()[0]);
  const [departement, setDepartement] = useState("");
  const [departements, setDepartements] = useState<string[]>([]);
  const [donnees, setDonnees] = useState<IndicateursOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [export_, setExport] = useState(false);

  useEffect(() => {
    if (national) listerTerritoires().then((t) => setDepartements(Object.keys(t))).catch(() => {});
  }, [national]);

  useEffect(() => {
    setDonnees(null);
    setErreur(null);
    obtenirIndicateurs({ annee_academique: annee, departement: departement || undefined })
      .then((res) => setDonnees(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  }, [annee, departement]);

  const exporter = async () => {
    setExport(true);
    try {
      const blob = await exporterIndicateursCsv({ annee_academique: annee, departement: departement || undefined });
      ouvrirBlobPdf(blob, `indicateurs-luluschools-${annee}.csv`);
    } catch (err) {
      setErreur(messageErreur(err, "Export impossible pour le moment."));
    } finally {
      setExport(false);
    }
  };

  const maxEleves = Math.max(1, ...(donnees?.par_departement ?? []).map((l) => l.eleves ?? 0));

  return (
    <div className="page-content">
      <SectionHead
        eyebrow={national ? "SUIVI-ÉVALUATION NATIONAL" : "MON ÉTABLISSEMENT"}
        title="Indicateurs de pilotage"
        desc="Chiffres recalculés à chaque consultation depuis les données de la plateforme. Toute case portant sur moins de 5 élèves est masquée."
      />
      <div className="indicateurs-filtres">
        <Field label="Année scolaire">
          <Select value={annee} onChange={(e) => setAnnee(e.target.value)}>
            {anneesDisponibles().map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </Select>
        </Field>
        {national && (
          <Field label="Département">
            <Select value={departement} onChange={(e) => setDepartement(e.target.value)}>
              <option value="">Tout le Bénin</option>
              {departements.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </Select>
          </Field>
        )}
        <Btn variant="outline" onClick={exporter} loading={export_} leftIcon={<Download size={16} aria-hidden="true" />}>
          Exporter (tableur)
        </Btn>
      </div>

      <ErrorBanner>{erreur}</ErrorBanner>
      {!donnees ? (
        !erreur && <Skeleton height="240px" />
      ) : (
        <>
          <p className="text-eyebrow" style={{ margin: "var(--space-4) 0" }}>
            Périmètre : {donnees.perimetre} · {donnees.annee_academique}
          </p>
          <div className="grid-4">
            <KPITile
              label="Élèves inscrits"
              value={donnees.eleves.total.toLocaleString("fr-FR")}
              icon={<Users size={24} />}
              accent="primary"
              sub={`${nombre(donnees.eleves.filles)} filles · ${nombre(donnees.eleves.garcons)} garçons`}
            />
            <KPITile
              label="Indice de parité F/G"
              value={donnees.eleves.indice_parite?.toLocaleString("fr-FR") ?? "—"}
              icon={<Scale size={24} />}
              accent="magic"
              sub="1 = autant de filles que de garçons"
            />
            <KPITile
              label="Taux de réussite"
              value={pourcent(donnees.reussite.taux_reussite)}
              icon={<GraduationCap size={24} />}
              accent="reward"
              sub={`Filles ${pourcent(donnees.reussite.taux_reussite_filles)} · Garçons ${pourcent(donnees.reussite.taux_reussite_garcons)}`}
            />
            <KPITile
              label="Établissements"
              value={donnees.etablissements.total}
              icon={<Landmark size={24} />}
              accent="primary"
              sub={`${donnees.etablissements.publics} publics · ${donnees.etablissements.prives} privés`}
            />
            <KPITile
              label="Élèves par enseignant"
              value={donnees.enseignants.eleves_par_enseignant?.toLocaleString("fr-FR") ?? "—"}
              icon={<Users size={24} />}
              accent="magic"
              sub={`${donnees.enseignants.sous_contrat} enseignants sous contrat`}
            />
            <KPITile
              label="Absences par élève"
              value={donnees.assiduite.absences_par_eleve?.toLocaleString("fr-FR") ?? "—"}
              icon={<CalendarX size={24} />}
              accent="action"
              sub={`${donnees.assiduite.absences} absences · ${donnees.assiduite.retards} retards`}
            />
            <KPITile
              label="Cantine scolaire"
              value={nombre(donnees.cantine.eleves_beneficiaires)}
              icon={<Soup size={24} />}
              accent="reward"
              sub={`élèves bénéficiaires · ${donnees.cantine.repas} repas`}
            />
            <KPITile
              label="Élèves en EFTP"
              value={pourcent(donnees.eftp?.part)}
              icon={<Wrench size={24} />}
              accent="reward"
              sub={`${nombre(donnees.eftp?.eleves)} élèves en classes techniques ou professionnelles`}
            />
            <KPITile
              label="Adultes en alphabétisation"
              value={(donnees.inclusion.apprenants_alphabetisation ?? 0).toLocaleString("fr-FR")}
              icon={<BookOpenCheck size={24} />}
              accent="magic"
              sub={`${donnees.etablissements.par_type.CA ?? 0} centre(s) d'alphabétisation`}
            />
            <KPITile
              label="Cours oraux transcrits"
              value={pourcent(donnees.inclusion.taux_transcription)}
              icon={<Accessibility size={24} />}
              accent="primary"
              sub={`${donnees.inclusion.cours_oraux_transcrits} sur ${donnees.inclusion.cours_oraux} · ${donnees.inclusion.comptes_mode_ecoute} comptes en mode Écoute`}
            />
          </div>

          {donnees.etablissements.sans_territoire > 0 && (
            <p style={{ marginTop: "var(--space-4)", color: "var(--ink-soft)" }}>
              {donnees.etablissements.sans_territoire} établissement(s) sans département ni commune : ils comptent dans le total
              national mais dans aucune ligne ci-dessous.
            </p>
          )}

          {donnees.par_departement && (
            <section style={{ marginTop: "var(--space-8)" }} aria-labelledby="titre-departements">
              <h2 id="titre-departements" className="text-title">Par département</h2>
              <div className="table-defilante" tabIndex={0} role="region" aria-labelledby="titre-departements">
                <table className="indicateurs-table">
                  <caption className="sr-only">Effectifs, parité et réussite par département</caption>
                  <thead>
                    <tr>
                      <th scope="col">Département</th>
                      <th scope="col">Établissements</th>
                      <th scope="col" style={{ minWidth: "200px" }}>Élèves</th>
                      <th scope="col">Filles</th>
                      <th scope="col">Garçons</th>
                      <th scope="col">Parité F/G</th>
                      <th scope="col">Réussite</th>
                    </tr>
                  </thead>
                  <tbody>
                    {donnees.par_departement.map((l) => (
                      <tr key={l.departement}>
                        <th scope="row">{l.departement}</th>
                        <td>{l.etablissements}</td>
                        <td>
                          <div className="indicateur-barre" title={`${l.departement} : ${nombre(l.eleves)} élèves`}>
                            <span
                              className="indicateur-barre-remplie"
                              style={{ width: `${((l.eleves ?? 0) / maxEleves) * 100}%` }}
                              aria-hidden="true"
                            />
                            <span className="indicateur-barre-valeur">{nombre(l.eleves)}</span>
                          </div>
                        </td>
                        <td>{nombre(l.filles)}</td>
                        <td>{nombre(l.garcons)}</td>
                        <td>{l.indice_parite?.toLocaleString("fr-FR") ?? "—"}</td>
                        <td>{pourcent(l.taux_reussite)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <section style={{ marginTop: "var(--space-8)" }} aria-labelledby="titre-pag">
            <h2 id="titre-pag" className="text-title">Alignement avec le PAG 2021-2026 (axe 5 : Éducation)</h2>
            <div className="table-defilante" tabIndex={0} role="region" aria-labelledby="titre-pag">
              <table className="indicateurs-table">
                <thead>
                  <tr>
                    <th scope="col">Orientation du PAG</th>
                    <th scope="col">Indicateurs suivis ici</th>
                  </tr>
                </thead>
                <tbody>
                  {ALIGNEMENT_PAG.map((a) => (
                    <tr key={a.orientation}>
                      <th scope="row">{a.orientation}</th>
                      <td>{a.indicateurs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
