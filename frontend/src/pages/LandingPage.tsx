import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { FloatingXPBadge, ProgressCard3D, XPBar } from "../components/gamification";
import { Tilt3D } from "../components/Tilt3D";
import { vitrinePublique, type VitrinePublique } from "../api/etablissements";
import {
  ChevronRight,
  Zap,
  Brain,
  Shield,
  Users,
  Trophy,
  FileCheck,
  BookOpen,
  Flame,
  Building2,
  Briefcase,
  Landmark,
  GraduationCap,
  School,
} from "lucide-react";

const TYPE_LABEL: Record<string, string> = {
  EP: "Primaire",
  ES: "Secondaire",
  UP: "Supérieur",
};

const TYPE_ICON: Record<string, ReactNode> = {
  EP: <School size={22} />,
  ES: <Building2 size={22} />,
  UP: <GraduationCap size={22} />,
};

/* ═══════════════════════════════════════════════════════════════
   Landing Page — LuluSchools
   ═══════════════════════════════════════════════════════════════ */

const STATS = [
  { value: "12", label: "établissements pilotes" },
  { value: "3", label: "dép. couverts" },
  { value: "+90%", label: "devoirs corrigés < 1 min" },
];

const FEATURES = [
  {
    icon: <Brain size={28} />,
    tone: "magic",
    title: "Correction IA en temps réel",
    desc: "Les devoirs et quiz sont corrigés par intelligence artificielle en moins d'une minute. L'enseignant reste maître de la révision finale.",
  },
  {
    icon: <Trophy size={28} />,
    tone: "reward",
    title: "Parcours gamifié",
    desc: "XP, niveaux, médailles, séries de jours — chaque effort est récompensé. Les élèves progressent comme dans un jeu, mais avec de vrais apprentissages.",
  },
  {
    icon: <FileCheck size={28} />,
    tone: "primary",
    title: "Inscription simplifiée",
    desc: "Du formulaire d'inscription jusqu'au matricule officiel : tout est dématérialisé, traçable et conforme à la loi béninoise n° 2017-20.",
  },
  {
    icon: <Users size={28} />,
    tone: "info",
    title: "5 rôles, 1 plateforme",
    desc: "Tuteur, Élève, Enseignant, Directeur, Ministère — chaque acteur du système éducatif a son espace dédié.",
  },
  {
    icon: <Zap size={28} />,
    tone: "action",
    title: "Recrutement transparent",
    desc: "Les candidatures enseignant sont notées objectivement par l'IA. Chaque décision est contestable, traçable, et auditable.",
  },
  {
    icon: <Shield size={28} />,
    tone: "primary",
    title: "Conforme & sécurisé",
    desc: "Consentement parental, signature électronique, protection des données des mineurs (Art. 446) — rien n'est laissé au hasard.",
  },
];

const ROLE_CARDS = [
  {
    role: "tuteur",
    icon: <Users size={32} />,
    bg: "var(--info-tint)",
    border: "var(--info-deep)",
    label: "Je suis Tuteur",
    desc: "Inscrivez vos enfants, suivez leur progression et donnez votre consentement.",
    to: "/inscription-tuteur",
  },
  {
    role: "enseignant",
    icon: <BookOpen size={32} />,
    bg: "var(--primary-tint)",
    border: "var(--primary-deep)",
    label: "Je suis Enseignant",
    desc: "Postulez à des postes, signez vos contrats, publiez vos cours et devoirs.",
    to: "/inscription-enseignant",
  },
];

const DEMO_MEDALS = [
  { id: "m1", label: "Champion", variant: "gold" as const },
  { id: "m2", label: "Réussite", variant: "green" as const },
  { id: "m3", label: "À débloquer", variant: "locked" as const },
];

export function LandingPage() {
  const [vitrine, setVitrine] = useState<VitrinePublique | null>(null);
  const [vitrineErreur, setVitrineErreur] = useState(false);

  useEffect(() => {
    vitrinePublique()
      .then((res) => setVitrine(res.data))
      .catch(() => setVitrineErreur(true));
  }, []);

  return (
    <div style={{ background: "var(--bg)", color: "var(--ink)", minHeight: "100dvh" }}>
      {/* ── Topbar ── */}
      <header
        className="card-glass"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 40,
          borderRadius: 0,
          borderLeft: "none",
          borderRight: "none",
          borderTop: "none",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "0 24px",
            height: "68px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "50%",
                background: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "var(--font-brand)",
                fontSize: "17px",
                color: "var(--on-primary)",
              }}
            >
              LS
            </div>
            <span
              style={{
                fontFamily: "var(--font-brand)",
                fontSize: "var(--text-2xl)",
                color: "var(--ink)",
              }}
            >
              Lulu<span style={{ color: "var(--primary)" }}>·</span>Schools
            </span>
          </div>

          {/* Nav pill */}
          <nav
            style={{
              display: "flex",
              gap: "6px",
              background: "var(--surface-2)",
              borderRadius: "var(--radius-pill)",
              padding: "5px",
            }}
          >
            {[
              { label: "Fonctionnalités", href: "#features" },
              { label: "Rôles", href: "#roles" },
            ].map((item) => (
              <a
                key={item.href}
                href={item.href}
                style={{
                  padding: "8px 16px",
                  borderRadius: "var(--radius-pill)",
                  fontSize: "var(--text-sm)",
                  fontWeight: 600,
                  textDecoration: "none",
                  color: "var(--ink-soft)",
                  transition: "background var(--dur-fast) ease, color var(--dur-fast) ease",
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLElement).style.background = "var(--surface-2)";
                  (e.target as HTMLElement).style.color = "var(--ink)";
                }}
                onMouseLeave={(e) => {
                  (e.target as HTMLElement).style.background = "transparent";
                  (e.target as HTMLElement).style.color = "var(--ink-soft)";
                }}
              >
                {item.label}
              </a>
            ))}
          </nav>

          {/* CTA nav */}
          <Link to="/connexion" className="btn btn-primary btn-sm">
            Se connecter
          </Link>
        </div>
      </header>

      {/* ── Hero ── */}
      <section style={{ position: "relative", overflow: "hidden" }}>
        <div className="dot-grid-bg" style={{ position: "absolute", inset: 0, opacity: 0.5, maskImage: "radial-gradient(ellipse 70% 60% at 50% 20%, black 0%, transparent 75%)" }} aria-hidden="true" />
        <div className="hero-glow" style={{ width: "480px", height: "480px", top: "-160px", left: "-120px", background: "color-mix(in srgb, var(--primary) 22%, transparent)" }} aria-hidden="true" />
        <div className="hero-glow" style={{ width: "360px", height: "360px", top: "60px", right: "-100px", background: "color-mix(in srgb, var(--reward) 18%, transparent)" }} aria-hidden="true" />
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px", position: "relative", zIndex: 1 }}>
        <div className="landing-hero">
          {/* Texte */}
          <div className="anim-float-in">
            <p className="text-eyebrow" style={{ marginBottom: "16px" }}>
              Plateforme nationale de l'éducation · République du Bénin
            </p>
            <h1
              className="text-display"
              style={{ margin: "0 0 20px", color: "var(--ink)" }}
            >
              L'école qui suit{" "}
              <span className="text-gradient">chaque élève,</span>
              <br />
              du premier badge
              <br />
              <span className="text-gradient">au diplôme.</span>
            </h1>
            <p
              style={{
                fontSize: "var(--text-lg)",
                color: "var(--ink-soft)",
                maxWidth: "46ch",
                lineHeight: 1.65,
                margin: "0 0 32px",
              }}
            >
              Inscriptions, devoirs corrigés par IA, quiz adaptatifs, bulletins,
              recrutement des enseignants&nbsp;: un seul compte, du CP à la licence.
            </p>
            <div style={{ display: "flex", gap: "14px", flexWrap: "wrap", marginBottom: "32px" }}>
              <Link to="/inscription-tuteur" className="btn btn-primary btn-lg">
                Créer un compte tuteur
              </Link>
              <a href="#features" className="btn btn-outline btn-lg">
                Découvrir <ChevronRight size={16} />
              </a>
            </div>

            {/* Stats */}
            <div className="hero-stat-row">
              {STATS.map((s, i) => (
                <div
                  key={s.label}
                  className="hero-stat anim-float-in"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <b>{s.value}</b>
                  <span>{s.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Visuel 3D hero — bascule réactive au curseur */}
          <Tilt3D className="hero-stage" maxTilt={5} glare style={{ boxShadow: "none" }}>
            {/* Carte de fond */}
            <ProgressCard3D
              name="Kofi A."
              classe="CM2"
              niveau="EP01"
              xpCurrent={400}
              xpMax={1000}
              level={3}
              offset
            />
            {/* Carte principale */}
            <ProgressCard3D
              name="Aisha D."
              matricule="710000126"
              classe="CE1"
              niveau="EP01"
              xpCurrent={680}
              xpMax={1000}
              level={4}
              streakDays={12}
              medals={DEMO_MEDALS}
              tiltStyle={{ transform: "translateZ(30px)" }}
            />
            {/* Badge XP flottant */}
            <div
              style={{
                position: "absolute",
                right: "10px",
                top: "-18px",
                zIndex: 3,
                width: "92px",
                height: "92px",
                transform: "translateZ(50px)",
              }}
            >
              <FloatingXPBadge amount={50} />
            </div>
          </Tilt3D>
        </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section
        id="features"
        style={{
          background: "var(--surface-2)",
          borderTop: "2px dashed var(--border)",
          borderBottom: "2px dashed var(--border)",
          padding: "80px 0",
        }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px" }}>
          <div style={{ textAlign: "center", marginBottom: "56px" }}>
            <p className="text-eyebrow" style={{ marginBottom: "12px", display: "block" }}>
              Ce que LuluSchools change
            </p>
            <h2
              className="text-headline"
              style={{ margin: "0 0 12px", color: "var(--ink)" }}
            >
              Une plateforme. Tout le système.
            </h2>
            <p style={{ color: "var(--ink-soft)", maxWidth: "52ch", margin: "0 auto", fontSize: "var(--text-lg)" }}>
              De la maternelle au supérieur, public ou privé. Pensée pour donner envie de progresser.
            </p>
          </div>

          <div className="grid-3">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className="card card-hover anim-float-in"
                style={{ animationDelay: `${i * 60}ms` }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "var(--radius-md)",
                    background: `var(--${f.tone}-tint)`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: `var(--${f.tone}-deep, var(--${f.tone}))`,
                    marginBottom: "16px",
                  }}
                >
                  {f.icon}
                </div>
                <h3
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "var(--text-lg)",
                    fontWeight: 600,
                    margin: "0 0 8px",
                    color: "var(--ink)",
                  }}
                >
                  {f.title}
                </h3>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: 0, lineHeight: 1.65 }}>
                  {f.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Vitrine : établissements & opportunités ── */}
      <section id="vitrine" style={{ maxWidth: "1200px", margin: "0 auto", padding: "80px 24px" }}>
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <p className="text-eyebrow" style={{ marginBottom: "12px", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
            <Landmark size={14} aria-hidden="true" /> Ouvert en ce moment
          </p>
          <h2 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
            Des établissements vous ouvrent leurs portes
          </h2>
          <p style={{ color: "var(--ink-soft)", maxWidth: "56ch", margin: "0 auto", fontSize: "var(--text-lg)" }}>
            Campagnes d'inscription et postes d'enseignant ouverts, directement depuis les établissements partenaires de la plateforme.
          </p>
        </div>

        {!vitrine && !vitrineErreur && (
          <div className="grid-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="vitrine-card">
                <div className="skeleton" style={{ height: "44px", width: "44px", borderRadius: "var(--radius-md)", marginBottom: "16px" }} />
                <div className="skeleton" style={{ height: "18px", width: "70%", marginBottom: "10px" }} />
                <div className="skeleton" style={{ height: "14px", width: "50%" }} />
              </div>
            ))}
          </div>
        )}

        {(vitrineErreur || (vitrine && vitrine.etablissements.length === 0)) && (
          <div className="card-soft" style={{ textAlign: "center", padding: "48px 24px" }}>
            <Building2 size={28} style={{ color: "var(--ink-faint)", marginBottom: "12px" }} aria-hidden="true" />
            <p style={{ color: "var(--ink-soft)", margin: 0 }}>
              Les premiers établissements rejoignent la plateforme — revenez bientôt pour découvrir les campagnes d'inscription et les postes ouverts.
            </p>
          </div>
        )}

        {vitrine && vitrine.etablissements.length > 0 && (
          <>
            <div className="grid-3">
              {vitrine.etablissements.slice(0, 6).map((e, i) => (
                <Tilt3D key={e.id} maxTilt={4} style={{ animationDelay: `${i * 70}ms` }} className="anim-rise-in">
                  <div className="vitrine-card">
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                      <div
                        style={{
                          width: "44px",
                          height: "44px",
                          borderRadius: "var(--radius-md)",
                          background: "var(--primary-tint)",
                          color: "var(--primary-deep)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                        aria-hidden="true"
                      >
                        {TYPE_ICON[e.type]}
                      </div>
                      <span className="chip chip-neutral" style={{ fontSize: "11px" }}>
                        {TYPE_LABEL[e.type]}
                      </span>
                    </div>
                    <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-lg)", fontWeight: 700, margin: "0 0 6px", color: "var(--ink)" }}>
                      {e.nom}
                    </h3>
                    <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: "0 0 16px" }}>
                      {e.statut === "public" ? "Établissement public" : "Établissement privé"} · {e.nb_classes} classe{e.nb_classes > 1 ? "s" : ""}
                    </p>
                    {e.nb_postes_ouverts > 0 ? (
                      <Link
                        to="/inscription-enseignant"
                        style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)", color: "var(--primary-deep)", textDecoration: "none" }}
                      >
                        <Briefcase size={14} aria-hidden="true" /> {e.nb_postes_ouverts} poste{e.nb_postes_ouverts > 1 ? "s" : ""} ouvert{e.nb_postes_ouverts > 1 ? "s" : ""}
                      </Link>
                    ) : (
                      <Link
                        to="/inscription-tuteur"
                        style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)", color: "var(--ink-soft)", textDecoration: "none" }}
                      >
                        Inscriptions ouvertes <ChevronRight size={14} aria-hidden="true" />
                      </Link>
                    )}
                  </div>
                </Tilt3D>
              ))}
            </div>

            {vitrine.postes_ouverts.length > 0 && (
              <div style={{ marginTop: "56px" }}>
                <h3
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "var(--text-xl)",
                    fontWeight: 700,
                    color: "var(--ink)",
                    margin: "0 0 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <Briefcase size={20} style={{ color: "var(--primary-deep)" }} aria-hidden="true" />
                  Postes d'enseignant ouverts en ce moment
                </h3>
                <div className="grid-3">
                  {vitrine.postes_ouverts.slice(0, 6).map((p, i) => (
                    <Link
                      key={p.id}
                      to="/inscription-enseignant"
                      className="vitrine-card anim-rise-in"
                      style={{ display: "block", textDecoration: "none", color: "inherit", animationDelay: `${i * 70}ms` }}
                    >
                      <p className="text-eyebrow" style={{ marginBottom: "8px", display: "block" }}>
                        {TYPE_LABEL[p.etablissement_type]}
                      </p>
                      <h4 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-base)", fontWeight: 700, margin: "0 0 6px", color: "var(--ink)" }}>
                        {p.titre}
                      </h4>
                      <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: "0 0 14px" }}>
                        {p.etablissement_nom}
                      </p>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)", color: "var(--primary-deep)" }}>
                        Postuler <ChevronRight size={14} aria-hidden="true" />
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </section>

      {/* ── XP Demo strip ── */}
      <section style={{ maxWidth: "1200px", margin: "0 auto", padding: "80px 24px" }}>
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding: "48px",
            boxShadow: "var(--shadow-xl)",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px", alignItems: "center" }}>
            <div>
              <p className="text-eyebrow" style={{ marginBottom: "12px", display: "block" }}>
                Gamification — pour de vrai
              </p>
              <h2 className="text-headline" style={{ margin: "0 0 16px", color: "var(--ink)" }}>
                Chaque effort devient un point d'XP.
              </h2>
              <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-base)", lineHeight: 1.7, margin: "0 0 24px" }}>
                Les élèves gagnent de l'expérience à chaque quiz réussi, devoir rendu, cours consulté.
                Les médailles et les niveaux rendent la progression visible et motivante.
              </p>
              <Link to="/inscription-tuteur" className="btn btn-primary">
                Inscrire mon enfant gratuitement <ChevronRight size={16} />
              </Link>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {[
                { name: "Aisha D.", level: 4, current: 680, max: 1000, streak: 12 },
                { name: "Kofi A.", level: 3, current: 820, max: 1000, streak: 5 },
                { name: "Fatou M.", level: 2, current: 340, max: 600, streak: 2 },
              ].map((s, i) => (
                <div
                  key={s.name}
                  className="anim-float-in"
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-lg)",
                    padding: "20px",
                    boxShadow: "var(--shadow-sm)",
                    animationDelay: `${i * 80}ms`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                    <div style={{ fontFamily: "var(--font-display)", fontWeight: 600 }}>
                      {s.name}
                    </div>
                    {s.streak > 0 && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "var(--text-sm)", fontWeight: 700, color: "var(--reward-deep)" }}>
                        <Flame size={14} aria-hidden="true" /> {s.streak}j
                      </span>
                    )}
                  </div>
                  <XPBar current={s.current} max={s.max} level={s.level} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Rôles ── */}
      <section
        id="roles"
        style={{
          background: "var(--surface-2)",
          borderTop: "2px dashed var(--border)",
          padding: "80px 0",
        }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 24px" }}>
          <div style={{ textAlign: "center", marginBottom: "48px" }}>
            <p className="text-eyebrow" style={{ marginBottom: "12px", display: "block" }}>Commencer</p>
            <h2 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
              Quel est votre rôle ?
            </h2>
          </div>
          <div className="grid-2" style={{ maxWidth: "720px", margin: "0 auto" }}>
            {ROLE_CARDS.map((rc, i) => (
              <Link
                key={rc.role}
                to={rc.to}
                className="anim-pop-in card-hover"
                style={{
                  display: "block",
                  background: "var(--surface)",
                  border: `1px solid var(--border)`,
                  borderRadius: "var(--radius-xl)",
                  padding: "32px",
                  boxShadow: "var(--shadow-sm)",
                  textDecoration: "none",
                  color: "var(--ink)",
                  transition: "transform var(--dur-normal) var(--ease-spring), box-shadow var(--dur-normal) var(--ease-spring), border-color var(--dur-normal) ease",
                  animationDelay: `${i * 80}ms`,
                }}
              >
                <div
                  style={{
                    width: "56px",
                    height: "56px",
                    borderRadius: "var(--radius-md)",
                    background: rc.bg,
                    color: rc.border,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "18px",
                  }}
                  aria-hidden="true"
                >
                  {rc.icon}
                </div>
                <h3 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-2xl)", fontWeight: 700, margin: "0 0 8px" }}>
                  {rc.label}
                </h3>
                <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: "0 0 20px", lineHeight: 1.65 }}>
                  {rc.desc}
                </p>
                <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 700, fontSize: "var(--text-sm)" }}>
                  S'inscrire maintenant <ChevronRight size={14} />
                </span>
              </Link>
            ))}
          </div>
          <p style={{ textAlign: "center", marginTop: "32px", fontSize: "var(--text-sm)", color: "var(--ink-faint)" }}>
            Déjà un compte ?{" "}
            <Link to="/connexion" style={{ color: "var(--primary)", fontWeight: 700, textDecoration: "none" }}>
              Se connecter →
            </Link>
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        style={{
          borderTop: "2px solid var(--border-strong)",
          padding: "32px 24px",
          textAlign: "center",
          color: "var(--ink-faint)",
          fontSize: "var(--text-sm)",
          fontFamily: "var(--font-mono)",
        }}
      >
        LuluSchools · Plateforme éducative nationale · République du Bénin · {new Date().getFullYear()}
      </footer>
    </div>
  );
}
