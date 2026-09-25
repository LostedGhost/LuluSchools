import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  creerCompteEnseignant,
  creerCompteTuteur,
  verifierOtpEnseignant,
  verifierOtpTuteur,
} from "../api/auth";
import { messageErreur } from "../api/client";
import { Btn, ErrorBanner, Field, TextInput } from "../components/ui";
import { CheckCircle, Mail, Users, BookOpen } from "lucide-react";

/* ── Stepper ── */
function StepDot({
  step,
  current,
  label,
}: {
  step: number;
  current: number;
  label: string;
}) {
  const done = current > step;
  const active = current === step;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
      <div
        style={{
          width: "36px",
          height: "36px",
          borderRadius: "50%",
          border: active || done ? "none" : "1.5px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: done
            ? "var(--primary)"
            : active
            ? "var(--primary-tint)"
            : "var(--surface-2)",
          color: done ? "var(--on-primary)" : active ? "var(--primary-deep)" : "var(--ink-faint)",
          fontFamily: "var(--font-display)",
          fontWeight: 700,
          fontSize: "15px",
          boxShadow: active ? "var(--shadow-xs)" : "none",
          transition: "all var(--dur-normal) ease",
        }}
      >
        {done ? <CheckCircle size={18} /> : step}
      </div>
      <span
        style={{
          fontSize: "10px",
          fontFamily: "var(--font-mono)",
          color: active ? "var(--primary-deep)" : "var(--ink-faint)",
          textTransform: "uppercase",
          letterSpacing: ".06em",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </span>
    </div>
  );
}

function Stepper({ step }: { step: number }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        gap: "0",
        marginBottom: "32px",
      }}
    >
      <StepDot step={1} current={step} label="Informations" />
      <div
        style={{
          flex: 1,
          height: "2px",
          background: step > 1 ? "var(--primary)" : "var(--border)",
          marginTop: "18px",
          maxWidth: "80px",
          transition: "background var(--dur-slow) ease",
        }}
      />
      <StepDot step={2} current={step} label="Vérification" />
      <div
        style={{
          flex: 1,
          height: "2px",
          background: step > 2 ? "var(--primary)" : "var(--border)",
          marginTop: "18px",
          maxWidth: "80px",
          transition: "background var(--dur-slow) ease",
        }}
      />
      <StepDot step={3} current={step} label="Terminé" />
    </div>
  );
}

export function SignupPage({ role }: { role: "tuteur" | "enseignant" }) {
  const navigate = useNavigate();
  const [etape, setEtape] = useState<1 | 2 | 3>(1);
  const [nom, setNom] = useState("");
  const [prenom, setPrenom] = useState("");
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [code, setCode] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  const creerCompte = role === "tuteur" ? creerCompteTuteur : creerCompteEnseignant;
  const verifierOtp = role === "tuteur" ? verifierOtpTuteur : verifierOtpEnseignant;

  const isTuteur = role === "tuteur";
  const accent = isTuteur ? "info" : "magic";
  const RoleIcon = isTuteur ? Users : BookOpen;
  const titre = isTuteur ? "Créer un compte tuteur" : "Créer un compte enseignant";

  const soumettreInscription = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await creerCompte({ nom, prenom, email, mot_de_passe: motDePasse });
      setEtape(2);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de créer le compte."));
    } finally {
      setEnCours(false);
    }
  };

  const soumettreOtp = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setEnCours(true);
    try {
      await verifierOtp(email, code);
      setEtape(3);
      setTimeout(() => navigate("/connexion", { replace: true }), 2000);
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
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Décor */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse 70% 50% at 50% -10%, var(--${accent}-tint) 0%, transparent 70%)`,
          pointerEvents: "none",
        }}
      />

      <div
        className="card anim-float-in"
        style={{ width: "100%", maxWidth: "480px", position: "relative", zIndex: 1 }}
      >
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "var(--radius-md)",
              background: `var(--${accent}-tint)`,
              color: `var(--${accent}-deep)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px",
            }}
            aria-hidden="true"
          >
            <RoleIcon size={28} />
          </div>
          <h1
            className="text-title"
            style={{ margin: "0 0 4px", color: "var(--ink)" }}
          >
            {titre}
          </h1>
          <p style={{ color: "var(--ink-faint)", fontSize: "var(--text-sm)", margin: 0 }}>
            Plateforme éducative nationale du Bénin
          </p>
        </div>

        {/* Stepper */}
        <Stepper step={etape} />

        {/* Étape 1 — Formulaire */}
        {etape === 1 && (
          <form onSubmit={soumettreInscription} noValidate className="anim-slide-up">
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <Field label="Prénom" required>
                  <TextInput
                    value={prenom}
                    onChange={(e) => setPrenom(e.target.value)}
                    required
                    autoFocus
                    autoComplete="given-name"
                    placeholder="Aisha"
                  />
                </Field>
                <Field label="Nom" required>
                  <TextInput
                    value={nom}
                    onChange={(e) => setNom(e.target.value)}
                    required
                    autoComplete="family-name"
                    placeholder="Dossou"
                  />
                </Field>
              </div>
              <Field label="Adresse e-mail" required>
                <TextInput
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="votre@email.com"
                />
              </Field>
              <Field
                label="Mot de passe"
                required
                helper="8+ caractères, 1 majuscule, 1 chiffre"
              >
                <TextInput
                  type="password"
                  value={motDePasse}
                  onChange={(e) => setMotDePasse(e.target.value)}
                  required
                  autoComplete="new-password"
                  placeholder="••••••••"
                  minLength={8}
                />
              </Field>

              {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

              <Btn
                type="submit"
                variant={isTuteur ? "primary" : "magic"}
                size="lg"
                loading={enCours}
                style={{ width: "100%" }}
              >
                Créer mon compte
              </Btn>
            </div>
          </form>
        )}

        {/* Étape 2 — OTP */}
        {etape === 2 && (
          <form onSubmit={soumettreOtp} noValidate className="anim-slide-up">
            <div
              style={{
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-lg)",
                padding: "20px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
                marginBottom: "20px",
              }}
            >
              <Mail size={24} style={{ color: "var(--primary)", flexShrink: 0 }} />
              <div>
                <p style={{ margin: "0 0 2px", fontWeight: 700, fontSize: "var(--text-sm)" }}>
                  Code envoyé à {email}
                </p>
                <p style={{ margin: 0, fontSize: "var(--text-xs)", color: "var(--ink-faint)" }}>
                  Valable 10 minutes · 5 tentatives max
                </p>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <Field label="Code de vérification à 6 chiffres" required>
                <TextInput
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  required
                  autoFocus
                  maxLength={6}
                  inputMode="numeric"
                  pattern="\d{6}"
                  placeholder="123456"
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--text-2xl)",
                    textAlign: "center",
                    letterSpacing: "0.3em",
                  }}
                />
              </Field>

              {erreur && <ErrorBanner>{erreur}</ErrorBanner>}

              <Btn
                type="submit"
                variant="primary"
                size="lg"
                loading={enCours}
                style={{ width: "100%" }}
              >
                Vérifier le code
              </Btn>
              <button
                type="button"
                onClick={() => setEtape(1)}
                className="btn btn-ghost btn-sm"
                style={{ width: "100%" }}
              >
                ← Modifier l'e-mail
              </button>
            </div>
          </form>
        )}

        {/* Étape 3 — Succès */}
        {etape === 3 && (
          <div className="anim-pop-in" style={{ textAlign: "center", padding: "20px 0" }}>
            <div
              style={{
                width: "72px",
                height: "72px",
                borderRadius: "50%",
                background: "var(--primary-tint)",
                color: "var(--primary-deep)",
                boxShadow: "var(--shadow-sm)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px",
              }}
            >
              <CheckCircle size={36} />
            </div>
            <h2
              className="text-title"
              style={{ color: "var(--ink)", margin: "0 0 8px" }}
            >
              Compte créé !
            </h2>
            <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-sm)", marginBottom: "20px" }}>
              Votre compte est activé. Redirection vers la connexion…
            </p>
            <Link to="/connexion" className="btn btn-primary">
              Se connecter maintenant
            </Link>
          </div>
        )}

        {/* Footer */}
        {etape === 1 && (
          <p style={{ textAlign: "center", marginTop: "20px", fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
            Déjà un compte ?{" "}
            <Link to="/connexion" style={{ color: "var(--primary)", fontWeight: 700, textDecoration: "none" }}>
              Se connecter
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
