import { Link } from "react-router-dom";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import { Card, PageTitle } from "../../components/ui";

export function EleveDashboard() {
  const profil = useEleveProfil();

  if (!profil.classe_id) {
    return (
      <div>
        <PageTitle>Bienvenue {profil.prenom}</PageTitle>
        <Card>
          <p className="text-slate-600">
            Aucune inscription validee pour l'instant. Votre tuteur doit soumettre et faire valider une
            inscription avant que vous puissiez acceder a vos cours.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageTitle>Bienvenue {profil.prenom}</PageTitle>
      <Card className="mb-6">
        <p className="text-sm text-slate-500">Matricule</p>
        <p className="mb-2 font-medium text-slate-900">{profil.matricule}</p>
        <p className="text-sm text-slate-500">Classe actuelle</p>
        <p className="font-medium text-slate-900">{profil.niveau}</p>
      </Card>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Link to="/eleve/cours">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Cours</p>
            <p className="text-sm text-slate-500">Consulter les cours et quiz</p>
          </Card>
        </Link>
        <Link to="/eleve/devoirs">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Devoirs</p>
            <p className="text-sm text-slate-500">Soumettre et suivre mes devoirs</p>
          </Card>
        </Link>
        <Link to="/eleve/bulletin">
          <Card className="text-center hover:border-indigo-300 hover:shadow-md">
            <p className="text-lg font-medium text-indigo-700">Bulletin</p>
            <p className="text-sm text-slate-500">Voir ma moyenne</p>
          </Card>
        </Link>
      </div>
    </div>
  );
}
