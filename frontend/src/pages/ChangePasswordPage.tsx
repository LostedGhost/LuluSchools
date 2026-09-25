import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { changerMotDePasse } from "../api/auth";
import { messageErreur } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../components/ui";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { utilisateur, rafraichirUtilisateur } = useAuth();
  const [ancien, setAncien] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await changerMotDePasse(ancien, nouveau);
      await rafraichirUtilisateur();
      navigate("/", { replace: true });
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de changer le mot de passe."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="mx-auto mt-16 max-w-md">
      <Card>
        <PageTitle>Changement de mot de passe requis</PageTitle>
        {utilisateur?.mot_de_passe_temporaire && (
          <p className="mb-4 text-sm text-amber-700">
            Votre mot de passe est temporaire. Vous devez le changer avant de continuer.
          </p>
        )}
        <form onSubmit={soumettre} className="space-y-4">
          <Field label="Mot de passe actuel (temporaire)">
            <TextInput type="password" value={ancien} onChange={(e) => setAncien(e.target.value)} required />
          </Field>
          <Field label="Nouveau mot de passe (8+ caracteres, 1 majuscule, 1 chiffre)">
            <TextInput type="password" value={nouveau} onChange={(e) => setNouveau(e.target.value)} required />
          </Field>
          <ErrorBanner>{erreur}</ErrorBanner>
          <PrimaryButton type="submit" disabled={enCours} className="w-full">
            {enCours ? "Enregistrement..." : "Changer le mot de passe"}
          </PrimaryButton>
        </form>
      </Card>
    </div>
  );
}
