import { Link } from "react-router-dom";
import { Card, PageTitle } from "../../components/ui";

export function EnseignantDashboard() {
  return (
    <div>
      <PageTitle>Espace enseignant</PageTitle>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link to="/enseignant/postes">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Postes ouverts</p>
            <p className="text-sm text-slate-500">Parcourir et postuler</p>
          </Card>
        </Link>
        <Link to="/enseignant/candidatures">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Mes candidatures</p>
            <p className="text-sm text-slate-500">Suivi et contestation</p>
          </Card>
        </Link>
        <Link to="/enseignant/contrats">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Mes contrats</p>
            <p className="text-sm text-slate-500">Signature electronique</p>
          </Card>
        </Link>
        <Link to="/enseignant/cours">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Cours et devoirs</p>
            <p className="text-sm text-slate-500">Publier, generer des quiz, corriger</p>
          </Card>
        </Link>
      </div>
    </div>
  );
}
