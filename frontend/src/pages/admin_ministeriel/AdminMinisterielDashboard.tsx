import { Link } from "react-router-dom";
import { Card, PageTitle } from "../../components/ui";

export function AdminMinisterielDashboard() {
  return (
    <div>
      <PageTitle>Administration ministerielle</PageTitle>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link to="/admin-ministeriel/etablissements">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Etablissements</p>
            <p className="text-sm text-slate-500">Creer un etablissement et son administrateur</p>
          </Card>
        </Link>
        <Link to="/admin-ministeriel/referentiels">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Referentiels de coefficients</p>
            <p className="text-sm text-slate-500">Gouvernance des ponderations de bulletin</p>
          </Card>
        </Link>
      </div>
    </div>
  );
}
