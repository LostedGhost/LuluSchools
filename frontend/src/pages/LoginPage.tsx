import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { messageErreur } from "../api/client";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../components/ui";

export function LoginPage() {
  const { seConnecter } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      const profil = await seConnecter(identifiant, motDePasse);
      const destination = (location.state as { from?: Location })?.from?.pathname;
      if (profil.mot_de_passe_temporaire) {
        navigate("/changer-mot-de-passe", { replace: true });
      } else {
        navigate(destination ?? "/", { replace: true });
      }
    } catch (err) {
      setErreur(messageErreur(err, "Identifiant ou mot de passe incorrect."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="mx-auto mt-16 max-w-md">
      <Card>
        <PageTitle>Connexion</PageTitle>
        <form onSubmit={soumettre} className="space-y-4">
          <Field label="E-mail (tuteur) ou matricule (eleve)">
            <TextInput
              value={identifiant}
              onChange={(e) => setIdentifiant(e.target.value)}
              required
              autoFocus
            />
          </Field>
          <Field label="Mot de passe">
            <TextInput
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              required
            />
          </Field>
          <ErrorBanner>{erreur}</ErrorBanner>
          <PrimaryButton type="submit" disabled={enCours} className="w-full">
            {enCours ? "Connexion..." : "Se connecter"}
          </PrimaryButton>
        </form>
        <p className="mt-4 text-center text-sm text-slate-500">
          Pas encore de compte ?{" "}
          <Link to="/inscription-tuteur" className="text-indigo-600 hover:underline">
            Tuteur
          </Link>{" "}
          ·{" "}
          <Link to="/inscription-enseignant" className="text-indigo-600 hover:underline">
            Enseignant
          </Link>
        </p>
      </Card>
    </div>
  );
}
