import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { messageErreur } from "../api/client";
import { Btn, ErrorBanner, Field, TextInput } from "../components/ui";
import { Eye, EyeOff } from "lucide-react";

export function LoginPage() {
  const { seConnecter } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [showPwd, setShowPwd] = useState(false);
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
    <div
      style={{
        minHeight: "100dvh",
        background: "var(--bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Fond décoratif */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse 80% 60% at 50% -10%, var(--primary-tint) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        aria-hidden
        style={{
          position: "absolute",
          bottom: "-60px",
          right: "-60px",
          width: "300px",
          height: "300px",
          borderRadius: "50%",
          background: "var(--reward-tint)",
          filter: "blur(60px)",
          opacity: ".6",
          pointerEvents: "none",
        }}
      />

      {/* Card connexion */}
      <div
        className="card anim-float-in"
        style={{ width: "100%", maxWidth: "440px", position: "relative", zIndex: 1 }}
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "60px",
              height: "60px",
              borderRadius: "50%",
              background: "var(--primary)",
              boxShadow: "var(--shadow-sm)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "20px",
              color: "var(--on-primary)",
              margin: "0 auto 16px",
            }}
          >
            LS
          </div>
          <h1
            className="text-title"
            style={{ margin: "0 0 6px", color: "var(--ink)" }}
          >
            Connexion
          </h1>
          <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)", margin: 0 }}>
            Lulu·Schools · Plateforme éducative nationale
          </p>
        </div>

        <form onSubmit={soumettre} noValidate>
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <Field label="E-mail ou matricule" required>
              <TextInput
                id="login-identifiant"
                type="text"
                value={identifiant}
                onChange={(e) => setIdentifiant(e.target.value)}
                required
                autoFocus
                autoComplete="username"
                placeholder="votre@email.com ou 710000126"
              />
            </Field>

            <Field label="Mot de passe" required>
              <div style={{ position: "relative" }}>
                <TextInput
                  id="login-password"
                  type={showPwd ? "text" : "password"}
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  style={{ paddingRight: "48px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  aria-label={showPwd ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  style={{
                    position: "absolute",
                    right: "14px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--ink-faint)",
                    display: "flex",
                    alignItems: "center",
                    padding: "4px",
                  }}
                >
                  {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </Field>

            {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

            <Btn
              type="submit"
              variant="primary"
              size="lg"
              loading={enCours}
              className="w-full"
              style={{ width: "100%" }}
            >
              {enCours ? "Connexion…" : "Se connecter"}
            </Btn>
          </div>
        </form>

        {/* Footer links */}
        <hr className="divider-dashed" />
        <p style={{ textAlign: "center", fontSize: "var(--text-sm)", color: "var(--ink-faint)", margin: 0 }}>
          Pas encore de compte ?{" "}
          <Link
            to="/inscription-tuteur"
            style={{ color: "var(--primary)", fontWeight: 700, textDecoration: "none" }}
          >
            Tuteur
          </Link>
          {" · "}
          <Link
            to="/inscription-enseignant"
            style={{ color: "var(--magic)", fontWeight: 700, textDecoration: "none" }}
          >
            Enseignant
          </Link>
        </p>
        <p style={{ textAlign: "center", marginTop: "10px" }}>
          <Link
            to="/"
            style={{ color: "var(--ink-faint)", fontSize: "var(--text-xs)", textDecoration: "none" }}
          >
            ← Retour à l'accueil
          </Link>
        </p>
      </div>
    </div>
  );
}
