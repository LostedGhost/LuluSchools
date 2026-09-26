import { useEffect, useState } from "react";
import { listerUtilisateursSupervision, reactiverCompte, suspendreCompte } from "../../api/admin";
import { messageErreur } from "../../api/client";
import type { AdminUtilisateurOut } from "../../types/api";
import { Badge, Btn, Card, ErrorBanner, Field, PageTitle, Select, SuccessBanner, TextInput } from "../../components/ui";
import { DataTable, type DataTableColumn } from "../../components/DataTable";
import { Ban, CheckCircle2, UserCog } from "lucide-react";
import { estRempli } from "../../utils/validation";

const PAGE_SIZE = 15;

const LABEL_ROLE: Record<string, string> = {
  tuteur: "Tuteur",
  eleve: "Élève",
  enseignant: "Enseignant",
  admin_etablissement: "Admin établissement (A+)",
  admin_ministeriel: "Admin ministériel (A++)",
};

export function UtilisateursPage() {
  const [utilisateurs, setUtilisateurs] = useState<AdminUtilisateurOut[]>([]);
  const [total, setTotal] = useState(0);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  const [recherche, setRecherche] = useState("");
  const [filtreRole, setFiltreRole] = useState("");
  const [filtreActif, setFiltreActif] = useState<"" | "true" | "false">("");
  const [page, setPage] = useState(0);

  const [cibleAction, setCibleAction] = useState<{ utilisateur: AdminUtilisateurOut; action: "suspendre" | "reactiver" } | null>(null);
  const [motif, setMotif] = useState("");
  const [enCoursAction, setEnCoursAction] = useState(false);

  const charger = () => {
    setChargement(true);
    listerUtilisateursSupervision({
      q: recherche || undefined,
      role: filtreRole || undefined,
      actif: filtreActif === "" ? undefined : filtreActif === "true",
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((res) => {
        setUtilisateurs(res.data.items);
        setTotal(res.data.total);
      })
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  };

  useEffect(() => {
    const t = setTimeout(charger, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recherche, filtreRole, filtreActif, page]);

  const confirmerAction = async () => {
    if (!cibleAction) return;
    if (cibleAction.action === "suspendre" && !estRempli(motif)) {
      setErreur("Un motif est requis pour suspendre un compte.");
      return;
    }
    setEnCoursAction(true);
    setErreur(null);
    try {
      if (cibleAction.action === "suspendre") {
        await suspendreCompte(cibleAction.utilisateur.id, motif.trim());
        setSucces(`Compte de ${cibleAction.utilisateur.prenom} ${cibleAction.utilisateur.nom} suspendu.`);
      } else {
        await reactiverCompte(cibleAction.utilisateur.id, motif.trim() || undefined);
        setSucces(`Compte de ${cibleAction.utilisateur.prenom} ${cibleAction.utilisateur.nom} réactivé.`);
      }
      setCibleAction(null);
      setMotif("");
      charger();
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'appliquer cette action."));
    } finally {
      setEnCoursAction(false);
    }
  };

  const colonnes: DataTableColumn<AdminUtilisateurOut>[] = [
    {
      key: "nom",
      header: "Utilisateur",
      render: (u) => (
        <div>
          <div style={{ fontWeight: 600 }}>{u.prenom} {u.nom}</div>
          <div className="text-sm" style={{ color: "var(--ink-soft)" }}>{u.email ?? u.login_id}</div>
        </div>
      ),
    },
    { key: "role", header: "Rôle", render: (u) => <Badge tone="info">{LABEL_ROLE[u.role] ?? u.role}</Badge> },
    {
      key: "statut",
      header: "Statut",
      render: (u) => (u.actif ? <Badge tone="success">Actif</Badge> : <Badge tone="error">Suspendu</Badge>),
    },
    {
      key: "actions",
      header: "",
      render: (u) =>
        u.actif ? (
          <Btn size="sm" variant="action" leftIcon={<Ban size={14} />} onClick={() => { setCibleAction({ utilisateur: u, action: "suspendre" }); setMotif(""); }}>
            Suspendre
          </Btn>
        ) : (
          <Btn size="sm" variant="outline" leftIcon={<CheckCircle2 size={14} />} onClick={() => { setCibleAction({ utilisateur: u, action: "reactiver" }); setMotif(""); }}>
            Réactiver
          </Btn>
        ),
    },
  ];

  return (
    <div className="page-content">
      <PageTitle eyebrow="Espace ministériel">Utilisateurs</PageTitle>
      <ErrorBanner>{erreur}</ErrorBanner>
      {succes && <div className="mb-4"><SuccessBanner>{succes}</SuccessBanner></div>}

      <DataTable
        columns={colonnes}
        rows={utilisateurs}
        rowKey={(u) => u.id}
        loading={chargement}
        emptyTitle="Aucun utilisateur trouvé"
        searchValue={recherche}
        onSearchChange={(v) => { setPage(0); setRecherche(v); }}
        searchPlaceholder="Rechercher par nom, e-mail ou matricule..."
        filters={
          <>
            <Select value={filtreRole} onChange={(e) => { setPage(0); setFiltreRole(e.target.value); }} style={{ width: "220px" }}>
              <option value="">Tous les rôles</option>
              {Object.entries(LABEL_ROLE).map(([valeur, label]) => (
                <option key={valeur} value={valeur}>{label}</option>
              ))}
            </Select>
            <Select value={filtreActif} onChange={(e) => { setPage(0); setFiltreActif(e.target.value as "" | "true" | "false"); }} style={{ width: "160px" }}>
              <option value="">Tous statuts</option>
              <option value="true">Actifs</option>
              <option value="false">Suspendus</option>
            </Select>
          </>
        }
        page={page}
        pageSize={PAGE_SIZE}
        total={total}
        onPageChange={setPage}
      />

      {cibleAction && (
        <Card className="mt-4 anim-slide-up" style={{ borderColor: "var(--action-deep)", borderWidth: "2px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
            <UserCog size={20} style={{ color: "var(--action-deep)" }} />
            <strong>
              {cibleAction.action === "suspendre" ? "Suspendre" : "Réactiver"} le compte de {cibleAction.utilisateur.prenom} {cibleAction.utilisateur.nom}
            </strong>
          </div>
          <Field label="Motif" required={cibleAction.action === "suspendre"} helper="Journalisé dans le journal d'audit ministériel.">
            <TextInput value={motif} onChange={(e) => setMotif(e.target.value)} placeholder="Ex. Signalement en cours d'instruction" />
          </Field>
          <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
            <Btn variant={cibleAction.action === "suspendre" ? "action" : "primary"} loading={enCoursAction} onClick={confirmerAction}>
              Confirmer
            </Btn>
            <Btn variant="ghost" onClick={() => setCibleAction(null)}>Annuler</Btn>
          </div>
        </Card>
      )}
    </div>
  );
}
