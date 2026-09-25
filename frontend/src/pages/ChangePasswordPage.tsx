import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Lock } from "lucide-react";
import { changerMotDePasse } from "../api/auth";
import { messageErreur } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, ErrorBanner, Field, SuccessBanner, TextInput } from "../components/ui";

function computePasswordStrength(pwd: string): {
  percent: number;
  label: string;
  color: string;
} {
  if (!pwd) return { percent: 0, label: "", color: "var(--border)" };
  let score = 0;
  if (pwd.length >= 8) score += 1;
  if (pwd.length >= 12) score += 1;
  if (/[A-Z]/.test(pwd)) score += 1;
  if (/[0-9]/.test(pwd)) score += 1;
  if (/[^A-Za-z0-9]/.test(pwd)) score += 1;

  if (score <= 1) return { percent: 20, label: "Très faible", color: "var(--action)" };
  if (score === 2) return { percent: 40, label: "Faible", color: "var(--action-deep)" };
  if (score === 3) return { percent: 65, label: "Moyen", color: "var(--reward-deep)" };
  if (score === 4) return { percent: 85, label: "Fort", color: "var(--primary)" };
  return { percent: 100, label: "Excellent", color: "var(--primary-deep)" };
}

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { utilisateur, rafraichirUtilisateur, seDeconnecter } = useAuth();
  const [ancien, setAncien] = useState("");
  const [nouveau, setNouveau] = useState("");
  const [showAncien, setShowAncien] = useState(false);
  const [showNouveau, setShowNouveau] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const strength = computePasswordStrength(nouveau);

  const soumettre = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setSucces(null);
    setEnCours(true);
    try {
      await changerMotDePasse(ancien, nouveau);
      await rafraichirUtilisateur();
      setSucces("Mot de passe modifié avec succès ! Redirection en cours...");
      setTimeout(() => {
        navigate("/", { replace: true });
      }, 700);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de changer le mot de passe."));
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
      {/* Fond décoratif en gradient radial */}
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
          opacity: 0.6,
          pointerEvents: "none",
        }}
      />

      {/* Carte centrée */}
      <div
        className="card anim-float-in"
        style={{ width: "100%", maxWidth: "440px", position: "relative", zIndex: 1 }}
      >
        {/* En-tête avec médaillon cadenas */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "50%",
              background: "var(--reward-tint)",
              color: "var(--reward-deep)",
              boxShadow: "var(--shadow-sm)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
            }}
            aria-hidden
          >
            <Lock size={28} />
          </div>
          <h1
            className="text-title"
            style={{ margin: "0 0 6px", color: "var(--ink)" }}
          >
            Nouveau mot de passe
          </h1>
          <p
            style={{
              color: "var(--ink-faint)",
              fontSize: "var(--text-sm)",
              margin: 0,
            }}
          >
            Sécurisez l'accès à votre compte Lulu·Schools
          </p>
        </div>

        {utilisateur?.mot_de_passe_temporaire && (
          <div
            className="chip chip-pending mb-5 w-full justify-start text-xs"
            style={{
              borderRadius: "var(--radius-md)",
              padding: "10px 14px",
              lineHeight: 1.4,
              whiteSpace: "normal",
            }}
          >
            <span className="chip-dot" />
            Votre mot de passe est temporaire. Vous devez le changer avant de pouvoir continuer sur la plateforme.
          </div>
        )}

        <form onSubmit={soumettre} noValidate>
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            <Field label="Mot de passe actuel (temporaire)" required>
              <div style={{ position: "relative" }}>
                <TextInput
                  id="ancien-password"
                  type={showAncien ? "text" : "password"}
                  value={ancien}
                  onChange={(e) => setAncien(e.target.value)}
                  required
                  autoFocus
                  autoComplete="current-password"
                  placeholder="••••••••"
                  style={{ paddingRight: "48px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowAncien((v) => !v)}
                  aria-label={showAncien ? "Masquer le mot de passe actuel" : "Afficher le mot de passe actuel"}
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
                  {showAncien ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </Field>

            <Field
              label="Nouveau mot de passe"
              helper="8+ caractères, au moins 1 majuscule et 1 chiffre"
              required
            >
              <div style={{ position: "relative" }}>
                <TextInput
                  id="nouveau-password"
                  type={showNouveau ? "text" : "password"}
                  value={nouveau}
                  onChange={(e) => setNouveau(e.target.value)}
                  required
                  autoComplete="new-password"
                  placeholder="Ex: SuperPasse123!"
                  style={{ paddingRight: "48px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowNouveau((v) => !v)}
                  aria-label={showNouveau ? "Masquer le nouveau mot de passe" : "Afficher le nouveau mot de passe"}
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
                  {showNouveau ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              {/* Indicateur de force du mot de passe */}
              {nouveau && (
                <div style={{ marginTop: "8px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "4px",
                      fontSize: "var(--text-xs)",
                    }}
                  >
                    <span style={{ color: "var(--ink-faint)" }}>Sécurité :</span>
                    <span style={{ fontWeight: 700, color: strength.color }}>
                      {strength.label}
                    </span>
                  </div>
                  <div className="progress-bar" style={{ height: "6px" }}>
                    <div
                      className="progress-fill"
                      style={{
                        width: `${strength.percent}%`,
                        backgroundColor: strength.color,
                        transition: "width 0.3s ease, background-color 0.3s ease",
                      }}
                    />
                  </div>
                </div>
              )}
            </Field>

            {erreur && <ErrorBanner>{erreur}</ErrorBanner>}
            {succes && <SuccessBanner>{succes}</SuccessBanner>}

            <Btn
              type="submit"
              variant="primary"
              size="lg"
              loading={enCours}
              leftIcon={<Lock size={18} />}
              className="w-full"
              style={{ width: "100%", marginTop: "4px" }}
            >
              {enCours ? "Mise à jour en cours…" : "Changer le mot de passe"}
            </Btn>
          </div>
        </form>

        {/* Lien de retour */}
        <hr className="divider-dashed" />
        <div style={{ textAlign: "center" }}>
          <Link
            to="/connexion"
            onClick={() => seDeconnecter()}
            style={{
              color: "var(--ink-faint)",
              fontSize: "var(--text-sm)",
              textDecoration: "none",
              fontWeight: 600,
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            ← Retour à la connexion
          </Link>
        </div>
      </div>
    </div>
  );
}
