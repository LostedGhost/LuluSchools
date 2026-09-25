import { Link } from "react-router-dom";
import { useAdminEtab } from "../../admin/AdminEtabContext";
import { Card, PageTitle } from "../../components/ui";

export function AdminEtabDashboard() {
  const etablissement = useAdminEtab();

  const liens = [
    { to: "/admin-etablissement/inscriptions", label: "Inscriptions a valider", desc: "Elèves en attente" },
    { to: "/admin-etablissement/classes", label: "Classes", desc: "Creer et consulter" },
    { to: "/admin-etablissement/postes", label: "Recrutement", desc: "Postes et candidatures" },
    { to: "/admin-etablissement/contestations", label: "Contestations", desc: "Recrutement en litige" },
    { to: "/admin-etablissement/actes", label: "Actes academiques", desc: "Catalogue et demandes" },
  ];

  return (
    <div>
      <PageTitle>{etablissement.nom}</PageTitle>
      <p className="mb-4 text-sm text-slate-500">
        {etablissement.code_etablissement} — {etablissement.type} — {etablissement.statut}
      </p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {liens.map((lien) => (
          <Link key={lien.to} to={lien.to}>
            <Card className="text-center hover:border-indigo-300 hover:shadow-md">
              <p className="text-lg font-medium text-indigo-700">{lien.label}</p>
              <p className="text-sm text-slate-500">{lien.desc}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
