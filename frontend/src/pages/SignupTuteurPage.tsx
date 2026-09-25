import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { creerCompteTuteur, verifierOtpTuteur } from "../api/auth";
import { messageErreur } from "../api/client";
import { Card, ErrorBanner, Field, PageTitle, PrimaryButton, TextInput } from "../components/ui";

export function SignupTuteurPage() {
  const navigate = useNavigate();
  const [etape, setEtape] = useState<"formulaire" | "otp">("formulaire");
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [code, setCode] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const soumettreInscription = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await creerCompteTuteur({ nom, prenom, email, mot_de_passe: motDePasse });
      setEtape("otp");
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de creer le compte."));
    } finally {
      setEnCours(false);
    }
  };

  const soumettreOtp = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await verifierOtpTuteur(email, code);
      navigate("/connexion", { replace: true });
    } catch (err) {
      setErreur(messageErreur(err, "Code invalide."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div className="mx-auto mt-16 max-w-md">
      <Card>
        {etape === "formulaire" ? (
          <>
            <PageTitle>Creer un compte tuteur</PageTitle>
            <form onSubmit={soumettreInscription} className="space-y-4">
              <Field label="Nom">
                <TextInput value={nom} onChange={(e) => setNom(e.target.value)} required />
              </Field>
              <Field label="Prenom">
                <TextInput value={prenom} onChange={(e) => setPrenom(e.target.value)} required />
              </Field>
              <Field label="E-mail">
                <TextInput type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </Field>
              <Field label="Mot de passe (8+ caracteres, 1 majuscule, 1 chiffre)">
                <TextInput
                  type="password"
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                  required
                />
              </Field>
              <ErrorBanner>{erreur}</ErrorBanner>
              <PrimaryButton type="submit" disabled={enCours} className="w-full">
                {enCours ? "Creation..." : "Creer mon compte"}
              </PrimaryButton>
            </form>
          </>
        ) : (
          <>
            <PageTitle>Verification de l'e-mail</PageTitle>
            <p className="mb-4 text-sm text-slate-600">
              Un code a 6 chiffres a ete envoye a <strong>{email}</strong>. Il est valable 10 minutes.
            </p>
            <form onSubmit={soumettreOtp} className="space-y-4">
              <Field label="Code de verification">
                <TextInput
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                  autoFocus
                  maxLength={6}
                />
              </Field>
              <ErrorBanner>{erreur}</ErrorBanner>
              <PrimaryButton type="submit" disabled={enCours} className="w-full">
                {enCours ? "Verification..." : "Verifier"}
              </PrimaryButton>
            </form>
          </>
        )}
      </Card>
    </div>
  );
}
