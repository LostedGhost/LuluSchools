import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { demanderReinitialisation, reinitialiserMotDePasse } from "../api/auth";
import { messageErreur } from "../api/client";
import { Btn, ErrorBanner, Field, TextInput } from "../components/ui";
import { KeyRound } from "lucide-react";
import { erreurMotDePasse, estRempli } from "../utils/validation";

export function MotDePasseOubliePage() {
  const navigate = useNavigate();
  const [etape, setEtape] = useState<1 | 2>(1);
  const [identifiant, setIdentifiant] = useState("");
  const [code, setCode] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [info, setInfo] = useState<string | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);
  const [champErreurs, setChampErreurs] = useState<{ identifiant?: string; code?: string; nouveau?: string }>({});

  const demanderCode = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    if (!estRempli(identifiant)) {
      setChampErreurs({ identifiant: "E-mail ou matricule requis." });
      return;
    }
    setChampErreurs({});
    setEnCours(true);
    try {
      const { data } = await demanderReinitialisation(identifiant.trim());
      setInfo(data.message);
      setEtape(2);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'envoyer le code pour le moment."));
    } finally {
      setEnCours(false);
    }
  };

  const confirmer = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    const erreurs: typeof champErreurs = {};
    if (code.length !== 6) erreurs.code = "Le code doit contenir exactement 6 chiffres.";
    const erreurMdp = erreurMotDePasse(nouveau);
    if (erreurMdp) erreurs.nouveau = erreurMdp;
    setChampErreurs(erreurs);
    if (Object.keys(erreurs).length > 0) return;

    setEnCours(true);
    try {
      await reinitialiserMotDePasse(identifiant.trim(), code, nouveau);
      navigate("/connexion", { replace: true, state: { message: "Mot de passe réinitialisé : vous pouvez vous connecter." } });
    } catch (err) {
      setErreur(messageErreur(err, "Code invalide ou expiré."));
    } finally {
      setEnCours(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100dvh",
        background: "var(--bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <div className="card anim-float-in" style={{ width: "100%", maxWidth: "440px" }}>
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <KeyRound size={36} style={{ color: "var(--primary-deep)", margin: "0 auto 12px", display: "block" }} />
          <h1 className="text-title" style={{ margin: "0 0 6px", color: "var(--ink)" }}>
            Mot de passe oublié
          </h1>
          <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)", margin: 0 }}>
            {etape === 1
              ? "Saisissez votre e-mail, ou votre matricule si vous êtes élève."
              : "Saisissez le code reçu par e-mail et choisissez un nouveau mot de passe."}
          </p>
        </div>

        {etape === 1 && (
          <form onSubmit={demanderCode} noValidate>
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <Field label="E-mail ou matricule" required error={champErreurs.identifiant}>
                <TextInput
                  value={identifiant}
                  onChange={(e) => setIdentifiant(e.target.value)}
                  autoFocus
                  autoComplete="username"
                  placeholder="votre@email.com ou 710000126"
                />
              </Field>
              {erreur && <ErrorBanner>{erreur}</ErrorBanner>}
              <Btn type="submit" variant="primary" size="lg" loading={enCours} style={{ width: "100%" }}>
                Recevoir un code
              </Btn>
            </div>
          </form>
        )}

        {etape === 2 && (
          <form onSubmit={confirmer} noValidate>
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {info && (
                <p role="status" style={{ margin: 0, fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>
                  {info}
                </p>
              )}
              <Field label="Code à 6 chiffres" required error={champErreurs.code}>
                <TextInput
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  autoFocus
                  maxLength={6}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123456"
                  style={{ fontFamily: "var(--font-mono)", textAlign: "center", letterSpacing: "0.3em" }}
                />
              </Field>
              <Field label="Nouveau mot de passe" required error={champErreurs.nouveau}>
                <TextInput
                  type="password"
                  value={nouveau}
                  onChange={(e) => setNouveau(e.target.value)}
                  autoComplete="new-password"
                  maxLength={128}
                />
              </Field>
              {erreur && <ErrorBanner>{erreur}</ErrorBanner>}
              <Btn type="submit" variant="primary" size="lg" loading={enCours} style={{ width: "100%" }}>
                Réinitialiser le mot de passe
              </Btn>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEtape(1)} style={{ width: "100%" }}>
                Renvoyer un code
              </button>
            </div>
          </form>
        )}

        <hr className="divider-dashed" />
        <p style={{ textAlign: "center", margin: 0 }}>
          <Link to="/connexion" style={{ color: "var(--primary-deep)", fontSize: "var(--text-sm)", textDecoration: "none" }}>
            ← Retour à la connexion
          </Link>
        </p>
      </div>
    </div>
  );
}
