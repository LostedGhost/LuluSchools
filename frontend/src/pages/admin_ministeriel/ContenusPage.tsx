import { useEffect, useState } from "react";
import {
  demasquerCours,
  demasquerDevoir,
  listerCoursSupervision,
  listerDevoirsSupervision,
  masquerCours,
  masquerDevoir,
} from "../../api/admin";
import { messageErreur } from "../../api/client";
import type { AdminCoursOut, AdminDevoirOut } from "../../types/api";
import { Badge, Btn, Card, ErrorBanner, Field, PageTitle, SectionHead, Select, SuccessBanner, TextInput } from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { EyeOff, Eye } from "lucide-react";
import { estRempli } from "../../utils/validation";

const PAGE_SIZE = 15;

type CibleMasquage =
  | { type: "cours"; contenu: AdminCoursOut }
  | { type: "devoir"; contenu: AdminDevoirOut };

export function ContenusPage() {
  const [cours, setCours] = useState<AdminCoursOut[]>([]);
  const [totalCours, setTotalCours] = useState(0);
  const [chargementCours, setChargementCours] = useState(true);
  const [pageCours, setPageCours] = useState(0);
  const [filtreMasqueCours, setFiltreMasqueCours] = useState<"" | "true" | "false">("");

  const [devoirs, setDevoirs] = useState<AdminDevoirOut[]>([]);
  const [totalDevoirs, setTotalDevoirs] = useState(0);
  const [chargementDevoirs, setChargementDevoirs] = useState(true);
  const [pageDevoirs, setPageDevoirs] = useState(0);
  const [filtreMasqueDevoirs, setFiltreMasqueDevoirs] = useState<"" | "true" | "false">("");

  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [cibleMasquage, setCibleMasquage] = useState<CibleMasquage | null>(null);
  const [motif, setMotif] = useState("");
  const [enCoursAction, setEnCoursAction] = useState(false);

  const chargerCours = () => {
    setChargementCours(true);
    listerCoursSupervision({ masque: filtreMasqueCours === "" ? undefined : filtreMasqueCours === "true", limit: PAGE_SIZE, offset: pageCours * PAGE_SIZE })
      .then((res) => { setCours(res.data.items); setTotalCours(res.data.total); })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargementCours(false));
  };

  const chargerDevoirs = () => {
    setChargementDevoirs(true);
    listerDevoirsSupervision({ masque: filtreMasqueDevoirs === "" ? undefined : filtreMasqueDevoirs === "true", limit: PAGE_SIZE, offset: pageDevoirs * PAGE_SIZE })
      .then((res) => { setDevoirs(res.data.items); setTotalDevoirs(res.data.total); })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargementDevoirs(false));
  };

  useEffect(chargerCours, [filtreMasqueCours, pageCours]);
  useEffect(chargerDevoirs, [filtreMasqueDevoirs, pageDevoirs]);

  const ouvrirDemasquage = async (cible: CibleMasquage) => {
    setErreur(null);
    setEnCoursAction(true);
    try {
      if (cible.type === "cours") await demasquerCours(cible.contenu.id);
      else await demasquerDevoir(cible.contenu.id);
      setSucces("Contenu démasqué.");
      chargerCours();
      chargerDevoirs();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCoursAction(false);
    }
  };

  const confirmerMasquage = async () => {
    if (!cibleMasquage) return;
    if (!estRempli(motif)) {
      setErreur("Un motif est requis pour masquer un contenu.");
      return;
    }
    setEnCoursAction(true);
    setErreur(null);
    try {
      if (cibleMasquage.type === "cours") await masquerCours(cibleMasquage.contenu.id, motif.trim());
      else await masquerDevoir(cibleMasquage.contenu.id, motif.trim());
      setSucces("Contenu masqué — il n'est plus visible par les élèves.");
      setCibleMasquage(null);
      setMotif("");
      chargerCours();
      chargerDevoirs();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de masquer ce contenu."));
    } finally {
      setEnCoursAction(false);
    }
  };

  const colonnesCours: DataTableColumn<AdminCoursOut>[] = [
    { key: "titre", header: "Cours", render: (c) => <span style={{ fontWeight: 600 }}>{c.titre}</span> },
    { key: "etablissement", header: "Établissement", render: (c) => c.etablissement_nom },
    { key: "enseignant", header: "Enseignant", render: (c) => `${c.enseignant_prenom} ${c.enseignant_nom}` },
    { key: "statut", header: "Statut", render: (c) => (c.masque ? <Badge tone="error">Masqué</Badge> : <Badge tone="success">Visible</Badge>) },
    {
      key: "actions",
      header: "",
      render: (c) =>
        c.masque ? (
          <Btn size="sm" variant="outline" leftIcon={<Eye size={14} />} loading={enCoursAction} onClick={() => ouvrirDemasquage({ type: "cours", contenu: c })}>
            Démasquer
          </Btn>
        ) : (
          <Btn size="sm" variant="action" leftIcon={<EyeOff size={14} />} onClick={() => { setCibleMasquage({ type: "cours", contenu: c }); setMotif(""); }}>
            Masquer
          </Btn>
        ),
    },
  ];

  const colonnesDevoirs: DataTableColumn<AdminDevoirOut>[] = [
    { key: "titre", header: "Devoir", render: (d) => <span style={{ fontWeight: 600 }}>{d.titre}</span> },
    { key: "matiere", header: "Matière", render: (d) => d.matiere },
    { key: "etablissement", header: "Établissement", render: (d) => d.etablissement_nom },
    { key: "enseignant", header: "Enseignant", render: (d) => `${d.enseignant_prenom} ${d.enseignant_nom}` },
    { key: "statut", header: "Statut", render: (d) => (d.masque ? <Badge tone="error">Masqué</Badge> : <Badge tone="success">Visible</Badge>) },
    {
      key: "actions",
      header: "",
      render: (d) =>
        d.masque ? (
          <Btn size="sm" variant="outline" leftIcon={<Eye size={14} />} loading={enCoursAction} onClick={() => ouvrirDemasquage({ type: "devoir", contenu: d })}>
            Démasquer
          </Btn>
        ) : (
          <Btn size="sm" variant="action" leftIcon={<EyeOff size={14} />} onClick={() => { setCibleMasquage({ type: "devoir", contenu: d }); setMotif(""); }}>
            Masquer
          </Btn>
        ),
    },
  ];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace ministériel">Supervision des contenus pédagogiques</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && <div className="mb-4"><SuccessBanner>{succes}</SuccessBanner></div>}

      {cibleMasquage && (
        <Card className="mb-6 anim-slide-up" style={{ borderColor: "var(--action-deep)", borderWidth: "2px" }}>
          <strong>Masquer « {cibleMasquage.contenu.titre} »</strong>
          <Field label="Motif" required helper="Journalisé dans le journal d'audit ministériel. Le contenu reste visible à l'enseignant, plus aux élèves.">
            <TextInput value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Ex. Contenu signalé comme inapproprié" />
          </Field>
          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
            <Btn variant="action" loading={enCoursAction} onClick={confirmerMasquage}>Confirmer le masquage</Btn>
            <Btn variant="ghost" onClick={() => setCibleMasquage(null)}>Annuler</Btn>
          </div>
        </Card>
      )}

      <SectionHead title="Cours" desc="Tous établissements confondus." />
      <DataTable
        columns={colonnesCours}
        rows={cours}
        rowKey={(c) => c.id}
        loading={chargementCours}
        emptyTitle="Aucun cours"
        filters={
          <Select value={filtreMasqueCours} onChange={(e) => { setPageCours(0); setFiltreMasqueCours(e.target.value as "" | "true" | "false"); }} style={{ width: "160px" }}>
            <option value="">Tous statuts</option>
            <option value="false">Visibles</option>
            <option value="true">Masqués</option>
          </Select>
        }
        page={pageCours}
        pageSize={PAGE_SIZE}
        total={totalCours}
        onPageChange={setPageCours}
      />

      <div style={{ marginTop: "var(--space-8)" }}>
        <SectionHead title="Devoirs" desc="Tous établissements confondus." />
        <DataTable
          columns={colonnesDevoirs}
          rows={devoirs}
          rowKey={(d) => d.id}
          loading={chargementDevoirs}
          emptyTitle="Aucun devoir"
          filters={
            <Select value={filtreMasqueDevoirs} onChange={(e) => { setPageDevoirs(0); setFiltreMasqueDevoirs(e.target.value as "" | "true" | "false"); }} style={{ width: "160px" }}>
              <option value="">Tous statuts</option>
              <option value="false">Visibles</option>
              <option value="true">Masqués</option>
            </Select>
          }
          page={pageDevoirs}
          pageSize={PAGE_SIZE}
          total={totalDevoirs}
          onPageChange={setPageDevoirs}
        />
      </div>
    </div>
  );
}
