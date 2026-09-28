import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowLeft, BookOpen, CalendarCheck, ClipboardList, Eye, FileDown, FileSignature, ScanLine, Sparkles, UserPlus,
} from "lucide-react";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { messageErreur } from "../../api/client";
import { listerClasses } from "../../api/etablissements";
import {
  consentementSurPapier, consentementsEnAttente, contexteClasse, enregistrerAppel, enregistrerCours,
  enregistrerInscriptionGuichet, enregistrerNotes, historiqueSaisies, lienPhoto, lireDocument,
  type ConsentementEnAttente, type ContexteClasse, type DocumentPapierOut, type InscriptionGuichetOut, type LectureOut,
  type TypeLecture,
} from "../../api/saisie_papier";
import { useConfirmation } from "../../components/Modale";
import { CopiesPapier, LIBELLES_CONFIANCE, TONS_CONFIANCE } from "../../components/saisie_papier/CopiesPapier";
import { PrisePhotos } from "../../components/saisie_papier/PrisePhotos";
import {
  Badge, Btn, Card, EmptyState, ErrorBanner, Field, PageTitle, SectionHead, Select, SkeletonCard, SuccessBanner, TextArea, TextInput,
} from "../../components/ui";
import type { ClasseOut } from "../../types/api";
import { ouvrirBlobPdf } from "../../utils/telechargerBlob";

/* Saisie papier (A+) : pour les enseignants, élèves et parents sans smartphone, l'administration
   photographie leurs documents papier. L'IA lit, vous vérifiez chaque valeur, puis vous validez ;
   la photo est conservée comme preuve (historique en bas de page). */

type Flux = "notes" | "appel" | "copies" | "cours" | "inscription" | "consentement";

const FLUX: { cle: Flux; titre: string; pour: string; desc: string; icone: ReactNode }[] = [
  { cle: "notes", titre: "Feuille de notes", pour: "Enseignant", desc: "Les notes d'une évaluation faite sur papier, pour toute la classe.", icone: <ClipboardList size={22} /> },
  { cle: "appel", titre: "Feuille d'appel", pour: "Enseignant", desc: "Les absences et retards relevés sur la feuille d'appel.", icone: <CalendarCheck size={22} /> },
  { cle: "copies", titre: "Copies d'élèves", pour: "Élèves", desc: "Les copies papier d'un devoir : chaque copie est attribuée puis corrigée.", icone: <ScanLine size={22} /> },
  { cle: "cours", titre: "Cours écrit", pour: "Enseignant", desc: "Un cours manuscrit ou imprimé, publié en texte pour la classe.", icone: <BookOpen size={22} /> },
  { cle: "inscription", titre: "Inscription au guichet", pour: "Parent", desc: "La fiche d'inscription remplie à l'accueil ; identifiants imprimés pour la famille.", icone: <UserPlus size={22} /> },
  { cle: "consentement", titre: "Consentement parental", pour: "Parent", desc: "Le formulaire de consentement signé pour un élève de moins de 16 ans.", icone: <FileSignature size={22} /> },
];

const LIBELLES_TYPE: Record<string, string> = {
  feuille_notes: "Feuille de notes", feuille_appel: "Feuille d'appel", cours: "Cours écrit", fiche_inscription: "Fiche d'inscription",
  copie: "Copie d'élève", contrat_signe: "Contrat signé", consentement: "Consentement parental",
};

const aujourdhui = () => new Date().toISOString().slice(0, 10);
const texte = (v: unknown) => (typeof v === "string" ? v : "");

function libelleClasse(c: ClasseOut) {
  return c.niveau + (c.filiere ? ` — ${c.filiere}` : "");
}

async function voirPhoto(documentId: string, index = 0) {
  const res = await lienPhoto(documentId, index);
  window.open(res.data.url, "_blank", "noopener,noreferrer");
}

export function SaisiePapierPage() {
  const etablissement = useAdminEtab();
  const [flux, setFlux] = useState<Flux | null>(null);
  const [classes, setClasses] = useState<ClasseOut[]>([]);
  const [historique, setHistorique] = useState<DocumentPapierOut[] | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  useEffect(() => {
    listerClasses(etablissement.id).then((res) => {
      const annee = res.data.map((c) => c.annee_academique).sort().at(-1);
      setClasses(res.data.filter((c) => c.annee_academique === annee).sort((a, b) => libelleClasse(a).localeCompare(libelleClasse(b))));
    }).catch(() => setClasses([]));
  }, [etablissement.id]);

  const chargerHistorique = () => {
    historiqueSaisies(etablissement.id).then((res) => setHistorique(res.data)).catch(() => setHistorique([]));
  };
  useEffect(chargerHistorique, [etablissement.id]);

  const terminer = (message: string) => {
    setSucces(message);
    setFlux(null);
    chargerHistorique();
  };

  const actif = FLUX.find((f) => f.cle === flux);
  return (
    <div className="page-content">
      <PageTitle eyebrow={etablissement.nom}>Saisie papier</PageTitle>
      <p className="text-sm" style={{ color: "var(--ink-soft)", marginTop: "-12px", marginBottom: "20px", maxWidth: "760px" }}>
        Pour les enseignants, élèves et parents qui n'ont pas de smartphone : photographiez leur document papier. L'IA le lit,
        vous vérifiez et corrigez chaque valeur, puis vous validez. La photo est conservée comme preuve.
      </p>
      <SuccessBanner>{succes}</SuccessBanner>

      {actif ? (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-2" style={{ marginBottom: "14px" }}>
            <h2 className="text-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>{actif.icone} {actif.titre}</h2>
            <Btn variant="ghost" size="sm" leftIcon={<ArrowLeft size={14} />} onClick={() => setFlux(null)}>Autre document</Btn>
          </div>
          {flux === "notes" && <FeuilleNotes classes={classes} etablissementId={etablissement.id} onTermine={terminer} />}
          {flux === "appel" && <FeuilleAppel classes={classes} etablissementId={etablissement.id} onTermine={terminer} />}
          {flux === "copies" && <CopiesEleves classes={classes} onTermine={() => { chargerHistorique(); }} />}
          {flux === "cours" && <CoursEcrit classes={classes} etablissementId={etablissement.id} onTermine={terminer} />}
          {flux === "inscription" && <InscriptionGuichet classes={classes} etablissementId={etablissement.id} onTermine={chargerHistorique} />}
          {flux === "consentement" && <Consentements etablissementId={etablissement.id} onTermine={chargerHistorique} />}
        </Card>
      ) : (
        <div className="grid-3">
          {FLUX.map((f) => (
            <button key={f.cle} type="button" className="card card-hover" onClick={() => { setSucces(null); setFlux(f.cle); }}
              style={{ textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit" }}>
              <span style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", color: "var(--primary-deep)" }}>
                {f.icone} <Badge tone="neutral" dot={false}>{f.pour} sans smartphone</Badge>
              </span>
              <strong style={{ display: "block", margin: "10px 0 4px", fontSize: "var(--text-lg)", color: "var(--ink)" }}>{f.titre}</strong>
              <span className="text-sm" style={{ color: "var(--ink-soft)" }}>{f.desc}</span>
            </button>
          ))}
        </div>
      )}

      <div style={{ marginTop: "32px" }}>
        <SectionHead title="Historique des saisies" desc="Chaque document enregistré, avec sa photo d'origine." />
        {historique === null ? <SkeletonCard /> : historique.length === 0 ? (
          <EmptyState icon={<ScanLine size={22} />} title="Aucune saisie pour l'instant" />
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {historique.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-3" style={{ padding: "10px 0", borderTop: "1px solid var(--border)" }}>
                <span style={{ flex: "1 1 220px", minWidth: 0 }}>
                  <strong>{LIBELLES_TYPE[d.type] ?? d.type}</strong>
                  {d.resume && <span style={{ color: "var(--ink-soft)" }}> — {d.resume}</span>}
                  <span className="text-sm" style={{ display: "block", color: "var(--ink-faint)" }}>
                    {new Date(d.enregistre_le ?? d.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })} · {d.saisi_par}
                  </span>
                </span>
                <Badge tone={d.statut === "enregistre" ? "success" : "pending"}>{d.statut === "enregistre" ? "Enregistré" : "Lu, non validé"}</Badge>
                <Btn variant="ghost" size="sm" leftIcon={<Eye size={14} />} onClick={() => voirPhoto(d.id)}>Photo</Btn>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/* ─── Briques communes ─────────────────────────────────────────────────── */

function ChoixClasse({ classes, valeur, onChange }: { classes: ClasseOut[]; valeur: string; onChange: (id: string) => void }) {
  return (
    <Field label="Classe" required>
      <Select value={valeur} onChange={(e) => onChange(e.target.value)}>
        <option value="">Choisir la classe…</option>
        {classes.map((c) => <option key={c.id} value={c.id}>{libelleClasse(c)}</option>)}
      </Select>
    </Field>
  );
}

function EtapeLecture({ fichiers, setFichiers, enCours, onLire, pret, aide, max }: {
  fichiers: File[]; setFichiers: (f: File[]) => void; enCours: boolean; onLire: () => void; pret: boolean; aide?: string; max?: number;
}) {
  return (
    <div className="space-y-3">
      <PrisePhotos fichiers={fichiers} onChange={setFichiers} aide={aide} max={max} />
      <Btn leftIcon={<Sparkles size={16} />} loading={enCours} disabled={!pret || fichiers.length === 0} onClick={onLire}>
        {enCours ? "L'IA lit le document… (20 à 60 secondes)" : "Lire le document"}
      </Btn>
    </div>
  );
}

function BandeauLecture({ lecture }: { lecture: LectureOut }) {
  return lecture.erreur_lecture ? (
    <ErrorBanner>{lecture.erreur_lecture}</ErrorBanner>
  ) : (
    <p className="text-sm" style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", color: "var(--ink-soft)", margin: 0 }}>
      <Sparkles size={15} aria-hidden="true" /> Lu par l'IA : vérifiez chaque valeur avant de valider.
      <Btn variant="ghost" size="sm" leftIcon={<Eye size={14} />} onClick={() => voirPhoto(lecture.document_id)}>Revoir la photo</Btn>
    </p>
  );
}

function useLecture(etablissementId: string, type: TypeLecture) {
  const [fichiers, setFichiers] = useState<File[]>([]);
  const [lecture, setLecture] = useState<LectureOut | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const lire = async (classeId: string | null) => {
    setEnCours(true);
    setErreur(null);
    try {
      setLecture((await lireDocument(etablissementId, type, classeId, fichiers)).data);
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  };
  return { fichiers, setFichiers, lecture, setLecture, enCours, setEnCours, erreur, setErreur, lire };
}

/* ─── Feuille de notes ─────────────────────────────────────────────────── */

type Saisie = { note: string; absent: boolean };

function FeuilleNotes({ classes, etablissementId, onTermine }: { classes: ClasseOut[]; etablissementId: string; onTermine: (m: string) => void }) {
  const demanderConfirmation = useConfirmation();
  const l = useLecture(etablissementId, "feuille_notes");
  const [classeId, setClasseId] = useState("");
  const [contexte, setContexte] = useState<ContexteClasse | null>(null);
  const [enseignantId, setEnseignantId] = useState("");
  const [matiere, setMatiere] = useState("");
  const [titre, setTitre] = useState("");
  const [date, setDate] = useState(aujourdhui());
  const [noteSur, setNoteSur] = useState("20");
  const [nature, setNature] = useState<"sommative" | "formative">("sommative");
  const [saisies, setSaisies] = useState<Record<string, Saisie>>({});

  const lire = async () => {
    const [ctx] = await Promise.all([contexteClasse(classeId).then((r) => r.data).catch(() => null), l.lire(classeId)]);
    setContexte(ctx);
  };

  useEffect(() => {
    const lu = l.lecture;
    if (!lu) return;
    const d = lu.lecture ?? {};
    setMatiere(texte(d.matiere));
    setTitre(texte(d.titre) || "Évaluation sur papier");
    if (texte(d.date)) setDate(texte(d.date));
    if (typeof d.note_sur === "number") setNoteSur(String(d.note_sur));
    setSaisies(Object.fromEntries(lu.lignes.filter((x) => x.eleve_id).map((x) => [x.eleve_id!, { note: x.note != null ? String(x.note) : "", absent: x.absent }])));
  }, [l.lecture]);

  useEffect(() => {
    if (!contexte) return;
    // « Physique » sur la feuille, « Physique-Chimie » au contrat : correspondance partielle acceptée.
    const norme = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
    const lue = norme(matiere);
    const parMatiere = lue ? contexte.enseignants.find((e) => e.matiere && (norme(e.matiere).includes(lue) || lue.includes(norme(e.matiere)))) : undefined;
    setEnseignantId((parMatiere ?? (contexte.enseignants.length === 1 ? contexte.enseignants[0] : undefined))?.id ?? "");
  }, [contexte]); // eslint-disable-line react-hooks/exhaustive-deps

  const eleves = l.lecture?.eleves ?? [];
  const nonReconnues = (l.lecture?.lignes ?? []).filter((x) => !x.eleve_id);
  const sur = Number(noteSur.replace(",", "."));
  const valeur = (id: string) => saisies[id] ?? { note: "", absent: false };
  const maj = (id: string, v: Partial<Saisie>) => setSaisies((s) => ({ ...s, [id]: { ...valeur(id), ...v } }));
  const lignes = eleves.map((e) => ({ e, s: valeur(e.eleve_id) }));
  const horsBareme = lignes.filter(({ s }) => s.note && (Number(s.note.replace(",", ".")) > sur || Number.isNaN(Number(s.note.replace(",", ".")))));
  const sansNote = lignes.filter(({ s }) => !s.absent && !s.note);
  const valide = classeId && enseignantId && matiere.trim() && titre.trim() && sur > 0 && horsBareme.length === 0 && lignes.some(({ s }) => s.absent || s.note);

  const enregistrer = async () => {
    const ok = await demanderConfirmation({
      titre: `Enregistrer les notes de « ${titre} » ?`,
      message: (
        <>
          {lignes.length - sansNote.length} élève(s) saisi(s), notes sur {sur}.
          {sansNote.length > 0 && <> <strong>{sansNote.length} élève(s) sans note</strong> ne seront pas enregistrés : ils compteront 0 comme un absent.</>}
          {" "}Les notes apparaissent aussitôt dans les bulletins et pour les familles.
        </>
      ),
      action: "Enregistrer les notes",
    });
    if (!ok) return;
    l.setEnCours(true);
    l.setErreur(null);
    try {
      const res = await enregistrerNotes(l.lecture!.document_id, {
        classe_id: classeId, enseignant_id: enseignantId, matiere: matiere.trim(), titre: titre.trim(), date_evaluation: date,
        note_sur: sur, nature,
        lignes: lignes.filter(({ s }) => s.absent || s.note).map(({ e, s }) => ({
          eleve_id: e.eleve_id, absent: s.absent, note: s.absent ? null : Number(s.note.replace(",", ".")),
        })),
      });
      onTermine(res.data.message);
    } catch (err) {
      l.setErreur(messageErreur(err));
    } finally {
      l.setEnCours(false);
    }
  };

  if (!l.lecture) {
    return (
      <div className="space-y-3">
        <ErrorBanner>{l.erreur}</ErrorBanner>
        <ChoixClasse classes={classes} valeur={classeId} onChange={setClasseId} />
        <EtapeLecture fichiers={l.fichiers} setFichiers={l.setFichiers} enCours={l.enCours} onLire={lire} pret={!!classeId} />
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <BandeauLecture lecture={l.lecture} />
      <ErrorBanner>{l.erreur}</ErrorBanner>
      <div className="grid-3">
        <Field label="Enseignant" required>
          <Select value={enseignantId} onChange={(e) => setEnseignantId(e.target.value)}>
            <option value="">Choisir…</option>
            {contexte?.enseignants.map((e) => <option key={e.id} value={e.id}>{e.prenom} {e.nom}{e.matiere ? ` (${e.matiere})` : ""}</option>)}
          </Select>
        </Field>
        <Field label="Matière" required><TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} /></Field>
        <Field label="Intitulé de l'évaluation" required><TextInput value={titre} onChange={(e) => setTitre(e.target.value)} /></Field>
        <Field label="Date de l'évaluation" required><TextInput type="date" max={aujourdhui()} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <Field label="Noté sur" required><TextInput inputMode="decimal" value={noteSur} onChange={(e) => setNoteSur(e.target.value)} /></Field>
        <Field label="Nature" helper="Une évaluation formative ne compte pas dans le bulletin.">
          <Select value={nature} onChange={(e) => setNature(e.target.value as typeof nature)}>
            <option value="sommative">Sommative (compte dans le bulletin)</option>
            <option value="formative">Formative</option>
          </Select>
        </Field>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--text-sm)" }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--ink-soft)" }}>
              <th style={{ padding: "8px" }}>Élève</th><th style={{ padding: "8px" }}>Lu sur la feuille</th>
              <th style={{ padding: "8px", width: "110px" }}>Note / {sur || "?"}</th><th style={{ padding: "8px" }}>Absent</th>
            </tr>
          </thead>
          <tbody>
            {lignes.map(({ e, s }) => {
              const lu = l.lecture!.lignes.find((x) => x.eleve_id === e.eleve_id);
              const hors = horsBareme.some((h) => h.e.eleve_id === e.eleve_id);
              return (
                <tr key={e.eleve_id} style={{ borderTop: "1px solid var(--border)", background: !s.absent && !s.note ? "var(--reward-tint)" : undefined }}>
                  <td style={{ padding: "8px", fontWeight: 600 }}>{e.nom} {e.prenom}</td>
                  <td style={{ padding: "8px" }}>
                    {lu ? <>{lu.nom_lu} <Badge tone={TONS_CONFIANCE[lu.confiance]}>{LIBELLES_CONFIANCE[lu.confiance]}</Badge>{!lu.lisible && <Badge tone="pending">peu lisible</Badge>}</>
                      : <span style={{ color: "var(--ink-faint)" }}>non trouvé</span>}
                  </td>
                  <td style={{ padding: "8px" }}>
                    <TextInput aria-label={`Note de ${e.prenom} ${e.nom}`} inputMode="decimal" value={s.note} disabled={s.absent}
                      onChange={(ev) => maj(e.eleve_id, { note: ev.target.value })} aria-invalid={hors || undefined}
                      style={{ width: "90px", borderColor: hors ? "var(--action)" : undefined }} />
                  </td>
                  <td style={{ padding: "8px" }}>
                    <input type="checkbox" aria-label={`${e.prenom} ${e.nom} absent`} checked={s.absent} onChange={(ev) => maj(e.eleve_id, { absent: ev.target.checked })} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {nonReconnues.length > 0 && (
        <div style={{ padding: "12px", borderRadius: "var(--radius-md)", background: "var(--surface-2)" }}>
          <strong>Lignes lues mais non reconnues ({nonReconnues.length})</strong>
          <p className="text-sm" style={{ margin: "4px 0 8px", color: "var(--ink-soft)" }}>Attribuez-les à un élève si besoin : la note est reportée sur sa ligne.</p>
          {nonReconnues.map((x, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2" style={{ padding: "4px 0" }}>
              <span style={{ flex: "1 1 160px" }}>{x.nom_lu} — {x.absent ? "absent" : x.note ?? "?"}</span>
              <Select aria-label={`Attribuer la ligne ${x.nom_lu}`} value="" style={{ maxWidth: "240px" }}
                onChange={(ev) => ev.target.value && maj(ev.target.value, { note: x.note != null ? String(x.note) : "", absent: x.absent })}>
                <option value="">Attribuer à…</option>
                {eleves.map((e) => <option key={e.eleve_id} value={e.eleve_id}>{e.nom} {e.prenom}</option>)}
              </Select>
            </div>
          ))}
        </div>
      )}

      {horsBareme.length > 0 && <ErrorBanner>{horsBareme.length} note(s) invalide(s) ou au-dessus de {sur}.</ErrorBanner>}
      <Btn loading={l.enCours} disabled={!valide} onClick={enregistrer}>Enregistrer les notes</Btn>
    </div>
  );
}

/* ─── Feuille d'appel ──────────────────────────────────────────────────── */

type StatutAppel = "present" | "absent" | "retard";

function FeuilleAppel({ classes, etablissementId, onTermine }: { classes: ClasseOut[]; etablissementId: string; onTermine: (m: string) => void }) {
  const demanderConfirmation = useConfirmation();
  const l = useLecture(etablissementId, "feuille_appel");
  const [classeId, setClasseId] = useState("");
  const [date, setDate] = useState(aujourdhui());
  const [matiere, setMatiere] = useState("");
  const [statuts, setStatuts] = useState<Record<string, { statut: StatutAppel; commentaire: string }>>({});

  useEffect(() => {
    const lu = l.lecture;
    if (!lu) return;
    if (texte(lu.lecture?.date)) setDate(texte(lu.lecture?.date));
    setMatiere(texte(lu.lecture?.matiere));
    setStatuts(Object.fromEntries(lu.lignes.filter((x) => x.eleve_id && x.statut).map((x) => [x.eleve_id!, { statut: x.statut!, commentaire: x.commentaire ?? "" }])));
  }, [l.lecture]);

  const eleves = l.lecture?.eleves ?? [];
  const releves = eleves.filter((e) => statuts[e.eleve_id] && statuts[e.eleve_id].statut !== "present");
  const nonReconnues = (l.lecture?.lignes ?? []).filter((x) => !x.eleve_id);

  const enregistrer = async () => {
    const ok = await demanderConfirmation({
      titre: `Enregistrer l'appel du ${new Date(date).toLocaleDateString("fr-FR")} ?`,
      message: `${releves.length} absence(s) ou retard(s) iront dans la vie scolaire des élèves ; les familles les verront.`,
      action: "Enregistrer l'appel",
    });
    if (!ok) return;
    l.setEnCours(true);
    try {
      const res = await enregistrerAppel(l.lecture!.document_id, {
        classe_id: classeId, date, matiere: matiere.trim() || null,
        lignes: releves.map((e) => ({ eleve_id: e.eleve_id, statut: statuts[e.eleve_id].statut as "absent" | "retard", commentaire: statuts[e.eleve_id].commentaire.trim() || null })),
      });
      onTermine(res.data.message);
    } catch (err) {
      l.setErreur(messageErreur(err));
    } finally {
      l.setEnCours(false);
    }
  };

  if (!l.lecture) {
    return (
      <div className="space-y-3">
        <ErrorBanner>{l.erreur}</ErrorBanner>
        <ChoixClasse classes={classes} valeur={classeId} onChange={setClasseId} />
        <EtapeLecture fichiers={l.fichiers} setFichiers={l.setFichiers} enCours={l.enCours} onLire={() => l.lire(classeId)} pret={!!classeId} />
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <BandeauLecture lecture={l.lecture} />
      <ErrorBanner>{l.erreur}</ErrorBanner>
      <div className="grid-2">
        <Field label="Date de l'appel" required><TextInput type="date" max={aujourdhui()} value={date} onChange={(e) => setDate(e.target.value)} /></Field>
        <Field label="Matière (facultatif)" helper="Vide : appel de la journée."><TextInput value={matiere} onChange={(e) => setMatiere(e.target.value)} /></Field>
      </div>
      <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
        {eleves.map((e) => {
          const s = statuts[e.eleve_id] ?? { statut: "present" as StatutAppel, commentaire: "" };
          return (
            <li key={e.eleve_id} className="flex flex-wrap items-center gap-2" style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
              <span style={{ flex: "1 1 180px", fontWeight: 600 }}>{e.nom} {e.prenom}</span>
              <Select aria-label={`Présence de ${e.prenom} ${e.nom}`} value={s.statut} style={{ maxWidth: "150px" }}
                onChange={(ev) => setStatuts((x) => ({ ...x, [e.eleve_id]: { ...s, statut: ev.target.value as StatutAppel } }))}>
                <option value="present">Présent</option><option value="absent">Absent</option><option value="retard">En retard</option>
              </Select>
              {s.statut !== "present" && (
                <TextInput aria-label={`Commentaire pour ${e.prenom} ${e.nom}`} placeholder="Commentaire (heure d'arrivée…)" value={s.commentaire}
                  onChange={(ev) => setStatuts((x) => ({ ...x, [e.eleve_id]: { ...s, commentaire: ev.target.value } }))} style={{ flex: "1 1 200px" }} />
              )}
            </li>
          );
        })}
      </ul>
      {nonReconnues.length > 0 && (
        <p className="text-sm" style={{ color: "var(--ink-soft)" }}>
          Lus mais non reconnus : {nonReconnues.map((x) => `${x.nom_lu} (${x.statut ?? "?"})`).join(", ")}. Reportez-les à la main si besoin.
        </p>
      )}
      <Btn loading={l.enCours} disabled={!date} onClick={enregistrer}>Enregistrer l'appel ({releves.length})</Btn>
    </div>
  );
}

/* ─── Copies d'élèves ──────────────────────────────────────────────────── */

function CopiesEleves({ classes, onTermine }: { classes: ClasseOut[]; onTermine: () => void }) {
  const [classeId, setClasseId] = useState("");
  const [contexte, setContexte] = useState<ContexteClasse | null>(null);
  const [devoirId, setDevoirId] = useState("");
  useEffect(() => {
    setContexte(null);
    setDevoirId("");
    if (classeId) contexteClasse(classeId).then((r) => setContexte(r.data)).catch(() => setContexte(null));
  }, [classeId]);
  return (
    <div className="space-y-3">
      <ChoixClasse classes={classes} valeur={classeId} onChange={setClasseId} />
      {contexte && (
        contexte.devoirs.length === 0 ? (
          <EmptyState title="Aucun devoir pour cette classe" desc="Les copies se rattachent à un devoir créé par l'enseignant sur la plateforme ; pour une évaluation entièrement sur papier, utilisez « Feuille de notes »." />
        ) : (
          <Field label="Devoir" required>
            <Select value={devoirId} onChange={(e) => setDevoirId(e.target.value)}>
              <option value="">Choisir le devoir…</option>
              {contexte.devoirs.map((d) => (
                <option key={d.id} value={d.id}>{d.titre} — {d.matiere} ({new Date(d.date_limite).toLocaleDateString("fr-FR")}, {d.copies} copie(s))</option>
              ))}
            </Select>
          </Field>
        )
      )}
      {devoirId && <CopiesPapier key={devoirId} devoirId={devoirId} onTermine={onTermine} />}
    </div>
  );
}

/* ─── Cours écrit ──────────────────────────────────────────────────────── */

function CoursEcrit({ classes, etablissementId, onTermine }: { classes: ClasseOut[]; etablissementId: string; onTermine: (m: string) => void }) {
  const demanderConfirmation = useConfirmation();
  const l = useLecture(etablissementId, "cours");
  const [classeId, setClasseId] = useState("");
  const [contexte, setContexte] = useState<ContexteClasse | null>(null);
  const [enseignantId, setEnseignantId] = useState("");
  const [titre, setTitre] = useState("");
  const [chapitre, setChapitre] = useState("");
  const [contenu, setContenu] = useState("");

  useEffect(() => {
    setContexte(null);
    setEnseignantId("");
    if (classeId) contexteClasse(classeId).then((r) => setContexte(r.data)).catch(() => setContexte(null));
  }, [classeId]);
  useEffect(() => {
    const d = l.lecture?.lecture;
    if (!d) return;
    setTitre(texte(d.titre));
    setChapitre(texte(d.chapitre));
    setContenu(texte(d.contenu));
  }, [l.lecture]);

  const enregistrer = async () => {
    if (!(await demanderConfirmation({ titre: `Publier « ${titre} » ?`, message: "Le cours est publié au nom de l'enseignant et visible des élèves de la classe.", action: "Publier" }))) return;
    l.setEnCours(true);
    try {
      onTermine((await enregistrerCours(l.lecture!.document_id, { classe_id: classeId, enseignant_id: enseignantId, titre: titre.trim(), chapitre: chapitre.trim(), contenu })).data.message);
    } catch (err) {
      l.setErreur(messageErreur(err));
    } finally {
      l.setEnCours(false);
    }
  };

  return (
    <div className="space-y-3">
      <ErrorBanner>{l.erreur}</ErrorBanner>
      <div className="grid-2">
        <ChoixClasse classes={classes} valeur={classeId} onChange={setClasseId} />
        <Field label="Enseignant" required>
          <Select value={enseignantId} onChange={(e) => setEnseignantId(e.target.value)} disabled={!contexte}>
            <option value="">Choisir…</option>
            {contexte?.enseignants.map((e) => <option key={e.id} value={e.id}>{e.prenom} {e.nom}{e.matiere ? ` (${e.matiere})` : ""}</option>)}
          </Select>
        </Field>
      </div>
      {!l.lecture ? (
        <EtapeLecture fichiers={l.fichiers} setFichiers={l.setFichiers} enCours={l.enCours} onLire={() => l.lire(null)} pret
          aide="Une photo par page du cours, dans l'ordre." />
      ) : (
        <>
          <BandeauLecture lecture={l.lecture} />
          <div className="grid-2">
            <Field label="Titre" required><TextInput value={titre} onChange={(e) => setTitre(e.target.value)} /></Field>
            <Field label="Chapitre" required><TextInput value={chapitre} onChange={(e) => setChapitre(e.target.value)} /></Field>
          </div>
          <Field label="Contenu du cours" required helper="Transcription de l'IA (Markdown) : relisez-la ; [illisible] signale un passage à compléter.">
            <TextArea value={contenu} onChange={(e) => setContenu(e.target.value)} rows={16} />
          </Field>
          <Btn loading={l.enCours} disabled={!classeId || !enseignantId || !titre.trim() || !chapitre.trim() || !contenu.trim()} onClick={enregistrer}>
            Publier le cours
          </Btn>
        </>
      )}
    </div>
  );
}

/* ─── Inscription au guichet ───────────────────────────────────────────── */

function age(naissance: string) {
  if (!naissance) return null;
  const n = new Date(naissance), a = new Date();
  return a.getFullYear() - n.getFullYear() - (a < new Date(a.getFullYear(), n.getMonth(), n.getDate()) ? 1 : 0);
}

function InscriptionGuichet({ classes, etablissementId, onTermine }: { classes: ClasseOut[]; etablissementId: string; onTermine: () => void }) {
  const demanderConfirmation = useConfirmation();
  const l = useLecture(etablissementId, "fiche_inscription");
  const [f, setF] = useState({ classe_id: "", nom: "", prenom: "", date_naissance: "", nationalite: "nationale" as "nationale" | "etrangere", sexe: "" as "" | "F" | "M", tuteur_nom: "", tuteur_telephone: "", consentement_signe: false });
  const [resultat, setResultat] = useState<InscriptionGuichetOut | null>(null);
  const maj = (v: Partial<typeof f>) => setF((x) => ({ ...x, ...v }));

  useEffect(() => {
    const d = l.lecture?.lecture ?? {};
    if (!l.lecture) return;
    maj({
      classe_id: l.lecture.classe_proposee_id ?? "", nom: texte(d.eleve_nom), prenom: texte(d.eleve_prenom), date_naissance: texte(d.date_naissance),
      nationalite: d.nationalite === "etrangere" ? "etrangere" : "nationale",
      tuteur_nom: [texte(d.tuteur_prenom), texte(d.tuteur_nom)].filter(Boolean).join(" "), tuteur_telephone: texte(d.tuteur_telephone),
      consentement_signe: d.signature_parent === true,
    });
  }, [l.lecture]);

  const mineur = (age(f.date_naissance) ?? 99) < 16;
  const valide = f.classe_id && f.nom.trim() && f.prenom.trim() && f.date_naissance && f.tuteur_nom.trim() && (!mineur || f.consentement_signe);

  const enregistrer = async () => {
    if (!(await demanderConfirmation({
      titre: `Inscrire ${f.prenom} ${f.nom} ?`,
      message: "L'élève est inscrit et admis dans la classe choisie (s'il reste de la place). Ses identifiants s'affichent ensuite, à imprimer et remettre à la famille.",
      action: "Inscrire",
    }))) return;
    l.setEnCours(true);
    l.setErreur(null);
    try {
      setResultat((await enregistrerInscriptionGuichet(l.lecture!.document_id, { ...f, sexe: f.sexe || null, tuteur_telephone: f.tuteur_telephone.trim() || null })).data);
      onTermine();
    } catch (err) {
      l.setErreur(messageErreur(err));
    } finally {
      l.setEnCours(false);
    }
  };

  const imprimer = () => {
    if (!resultat?.fiche_identifiants_pdf) return;
    const octets = Uint8Array.from(atob(resultat.fiche_identifiants_pdf), (c) => c.charCodeAt(0));
    ouvrirBlobPdf(new Blob([octets], { type: "application/pdf" }), `identifiants-${resultat.matricule}.pdf`);
  };

  if (resultat) {
    return (
      <div className="space-y-3">
        <p style={{ margin: 0 }}><strong>{f.prenom} {f.nom}</strong> est inscrit(e). Remettez ces identifiants à la famille (ils ne seront plus affichés) :</p>
        <div className="monospace" style={{ padding: "12px", borderRadius: "var(--radius-md)", background: "var(--surface-2)" }}>
          Identifiant : {resultat.matricule}<br />Mot de passe provisoire : {resultat.mot_de_passe_provisoire}
        </div>
        <Btn leftIcon={<FileDown size={16} />} onClick={imprimer}>Imprimer la fiche d'identifiants</Btn>
      </div>
    );
  }
  if (!l.lecture) {
    return (
      <div className="space-y-3">
        <ErrorBanner>{l.erreur}</ErrorBanner>
        <EtapeLecture fichiers={l.fichiers} setFichiers={l.setFichiers} enCours={l.enCours} onLire={() => l.lire(null)} pret
          aide="Photographiez la fiche d'inscription remplie et signée par le parent (recto, et verso s'il est rempli)." />
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <BandeauLecture lecture={l.lecture} />
      <ErrorBanner>{l.erreur}</ErrorBanner>
      <div className="grid-2">
        <ChoixClasse classes={classes} valeur={f.classe_id} onChange={(id) => maj({ classe_id: id })} />
        <Field label="Nationalité">
          <Select value={f.nationalite} onChange={(e) => maj({ nationalite: e.target.value as typeof f.nationalite })}>
            <option value="nationale">Béninoise</option><option value="etrangere">Étrangère</option>
          </Select>
        </Field>
        <Field label="Sexe (facultatif)">
          <Select value={f.sexe} onChange={(e) => maj({ sexe: e.target.value as typeof f.sexe })}>
            <option value="">Non précisé</option>
            <option value="F">Fille</option>
            <option value="M">Garçon</option>
          </Select>
        </Field>
        <Field label="Nom de l'élève" required><TextInput value={f.nom} onChange={(e) => maj({ nom: e.target.value })} /></Field>
        <Field label="Prénom(s) de l'élève" required><TextInput value={f.prenom} onChange={(e) => maj({ prenom: e.target.value })} /></Field>
        <Field label="Date de naissance" required><TextInput type="date" max={aujourdhui()} value={f.date_naissance} onChange={(e) => maj({ date_naissance: e.target.value })} /></Field>
        <Field label="Parent ou tuteur" required><TextInput value={f.tuteur_nom} onChange={(e) => maj({ tuteur_nom: e.target.value })} /></Field>
        <Field label="Téléphone du parent"><TextInput type="tel" value={f.tuteur_telephone} onChange={(e) => maj({ tuteur_telephone: e.target.value })} /></Field>
      </div>
      <label className="flex items-start gap-2" style={{ cursor: "pointer" }}>
        <input type="checkbox" checked={f.consentement_signe} onChange={(e) => maj({ consentement_signe: e.target.checked })} style={{ marginTop: "4px" }} />
        <span>
          La fiche porte la signature du parent ou tuteur.
          {mineur && <span className="text-sm" style={{ display: "block", color: "var(--action-deep)" }}>Obligatoire : l'élève a moins de 16 ans (consentement parental).</span>}
        </span>
      </label>
      <Btn loading={l.enCours} disabled={!valide} onClick={enregistrer}>Inscrire l'élève</Btn>
    </div>
  );
}

/* ─── Consentements parentaux ──────────────────────────────────────────── */

function Consentements({ etablissementId, onTermine }: { etablissementId: string; onTermine: () => void }) {
  const [liste, setListe] = useState<ConsentementEnAttente[] | null>(null);
  const [photos, setPhotos] = useState<Record<string, File[]>>({});
  const [enCours, setEnCours] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const charger = () => consentementsEnAttente(etablissementId).then((r) => setListe(r.data)).catch((e) => setErreur(messageErreur(e)));
  useEffect(() => { void charger(); }, [etablissementId]); // eslint-disable-line react-hooks/exhaustive-deps

  const enregistrer = async (c: ConsentementEnAttente) => {
    setEnCours(c.inscription_id);
    setErreur(null);
    try {
      setSucces((await consentementSurPapier(c.inscription_id, photos[c.inscription_id])).data.message);
      await charger();
      onTermine();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(null);
    }
  };

  const vide = useMemo(() => liste !== null && liste.length === 0, [liste]);
  return (
    <div className="space-y-3">
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>
      <p className="text-sm" style={{ margin: 0, color: "var(--ink-soft)" }}>
        Inscriptions d'élèves de moins de 16 ans qui attendent le consentement du parent. Faites signer le formulaire au parent, puis photographiez-le.
      </p>
      {liste === null ? <SkeletonCard /> : vide ? <EmptyState title="Aucun consentement en attente" /> : (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {liste!.map((c) => (
            <li key={c.inscription_id} className="space-y-2" style={{ padding: "12px 0", borderTop: "1px solid var(--border)" }}>
              <div><strong>{c.eleve}</strong> — {c.classe} <span className="text-sm" style={{ color: "var(--ink-faint)" }}>demandé le {new Date(c.depose_le).toLocaleDateString("fr-FR")}</span></div>
              <PrisePhotos fichiers={photos[c.inscription_id] ?? []} onChange={(f) => setPhotos((p) => ({ ...p, [c.inscription_id]: f }))}
                aide="Une photo par page du formulaire signé par le parent." />
              <Btn size="sm" loading={enCours === c.inscription_id} disabled={!photos[c.inscription_id]?.length} onClick={() => enregistrer(c)}>
                Enregistrer le consentement
              </Btn>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
