import { lazy, Suspense, useEffect, useState, type MouseEvent } from "react";
import { Link } from "react-router-dom";
import { FloatingXPBadge, ProgressCard3D, XPBar } from "../components/gamification";
import { Tilt3D } from "../components/Tilt3D";
import { DiplomaCard, FloatingMedal } from "../components/FloatingObjects3D";
import { useDonneesReduites } from "../accessibilite/AccessibiliteContext";
import { vitrinePublique, type VitrinePublique } from "../api/etablissements";
import { PHOTO_HERO_CLASSE } from "../utils/photosParDefaut";
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
  Landmark,
  MessageCircle,
  Radio,
  Sparkles,
  Bus,
  Ticket,
  Handshake,
  Box,
  Wallet,
  Radar,
  Bot,
  Award,
  ShoppingBag,
} from "lucide-react";

// Chargé à la demande : Three.js pèse à lui seul plus que tout le reste de
// l'interface, il ne doit jamais alourdir le bundle des pages internes.
const StarfieldScene = lazy(() =>
  import("../components/StarfieldScene").then((m) => ({ default: m.StarfieldScene })),
);

const TYPE_LABEL: Record<string, string> = {
  EP: "Primaire",
  ES: "Secondaire",
  UP: "Supérieur",
  CA: "Alphabétisation",
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

const NOUVEAUTES = [
  {
    icon: <MessageCircle size={26} />,
    tone: "info",
    title: "Messagerie interne",
    desc: "Groupe de classe et messages privés, avec modération intégrée pour l'établissement.",
    bientot: false,
  },
  {
    icon: <Radio size={26} />,
    tone: "primary",
    title: "Cours en direct",
    desc: "Sessions live avec tableau collaboratif « craie et chiffon » : traits à main levée, texte, plusieurs élèves autorisés à écrire en même temps, sans jamais s'écraser.",
    bientot: false,
  },
  {
    icon: <Sparkles size={26} />,
    tone: "magic",
    title: "El Professor",
    desc: "Un assistant pédagogique IA present sur chaque cours pour l'élève, mais aussi pour l'enseignant, le tuteur, et même en fil partagé parent-enfant — avec un garde-fou de sécurité qui alerte l'établissement en cas de besoin.",
    bientot: false,
  },
  {
    icon: <ShoppingBag size={26} />,
    tone: "reward",
    title: "Marketplace étudiante",
    desc: "Les élèves de 16 ans et plus revendent fournitures et manuels entre eux, paiement sécurisé par séquestre — le tuteur garde un droit de regard en lecture seule.",
    bientot: false,
  },
  {
    icon: <Bus size={26} />,
    tone: "action",
    title: "Transport & cantine",
    desc: "Achat de tickets, contrôle d'accès par un agent désigné, remboursement jusqu'à la veille 18h.",
    bientot: false,
  },
  {
    icon: <Ticket size={26} />,
    tone: "reward",
    title: "Billetterie d'événements",
    desc: "Kermesses, spectacles et cérémonies : réservez et payez votre billet en ligne.",
    bientot: false,
  },
  {
    icon: <Handshake size={26} />,
    tone: "primary",
    title: "Micro-jobs communautaires",
    desc: "Enseignants, tuteurs et établissements s'échangent des services ponctuels, paiement sécurisé par séquestre.",
    bientot: false,
  },
  {
    icon: <Box size={26} />,
    tone: "info",
    title: "Visites virtuelles 3D",
    desc: "Explorez un établissement en 3D avant d'y inscrire votre enfant.",
    bientot: true,
  },
];

const INNOVATIONS_FAMILLE = [
  {
    icon: <Wallet size={26} />,
    tone: "action",
    title: "Coffre-fort familial",
    desc: "Le tuteur fixe, s'il le souhaite, un plafond de dépense hebdomadaire ou un seuil de validation sur les achats de son enfant (marketplace, micro-jobs, actes). Jamais de blocage silencieux : l'enfant voit toujours pourquoi une dépense attend son feu vert.",
  },
  {
    icon: <Radar size={26} />,
    tone: "info",
    title: "Radar familial",
    desc: "Un résumé hebdomadaire généré par IA à partir de la vie scolaire, des devoirs corrigés et des sessions suivies de son enfant — chaque phrase cite sa source, jamais une affirmation en l'air.",
  },
  {
    icon: <Bot size={26} />,
    tone: "magic",
    title: "El Professor Famille",
    desc: "Un fil de discussion à trois : le tuteur invite son enfant, tous deux posent leurs questions à l'IA dans la même conversation. Un signal de danger remonte toujours directement à l'établissement — jamais seulement au tuteur.",
  },
  {
    icon: <Award size={26} />,
    tone: "reward",
    title: "Passeport de compétences",
    desc: "Quiz réussis, cours suivis, moyennes par matière : un récapitulatif automatique de tout ce que l'élève a déjà accompli, exportable en PDF pour une candidature ou un dossier d'orientation.",
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
  // Lot 7.5 : la scène Three.js (~120 Ko compressés + GPU) n'est jamais chargée en
  // mode données réduites — le fond en points et les halos suffisent.
  const donneesReduites = useDonneesReduites();

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
        <div className="landing-topbar">
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <img
              src="/logo.png"
              alt="LuluSchools"
              width={40}
              height={40}
              style={{ width: "40px", height: "40px", objectFit: "contain" }}
            />
            <span
              style={{
                fontFamily: "var(--font-brand)",
                fontSize: "var(--text-2xl)",
                color: "var(--ink)",
              }}
            >
              Lulu<span style={{ color: "var(--primary-deep)" }}>·</span>Schools
            </span>
          </div>

          {/* Nav pill */}
          <nav className="landing-nav" aria-label="Navigation du site">
            {[
              { label: "Notre mission", href: "#features" },
              { label: "Établissements", href: "/etablissements" },
              { label: "Cartes", href: "/cartes" },
            ].map((item) => {
              const navItemStyle = {
                padding: "8px 16px",
                borderRadius: "var(--radius-pill)",
                fontSize: "var(--text-sm)",
                fontWeight: 600,
                textDecoration: "none",
                color: "var(--ink-soft)",
                transition: "background var(--dur-fast) ease, color var(--dur-fast) ease",
              };
              const hoverHandlers = {
                onMouseEnter: (e: MouseEvent<HTMLElement>) => {
                  (e.target as HTMLElement).style.background = "var(--surface-2)";
                  (e.target as HTMLElement).style.color = "var(--ink)";
                },
                onMouseLeave: (e: MouseEvent<HTMLElement>) => {
                  (e.target as HTMLElement).style.background = "transparent";
                  (e.target as HTMLElement).style.color = "var(--ink-soft)";
                },
              };
              return item.href.startsWith("#") ? (
                <a key={item.href} href={item.href} style={navItemStyle} {...hoverHandlers}>
                  {item.label}
                </a>
              ) : (
                <Link key={item.href} to={item.href} style={navItemStyle} {...hoverHandlers}>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* CTA nav */}
          <Link to="/connexion" className="btn btn-primary btn-sm">
            Se connecter
          </Link>
        </div>
      </header>

      {/* ── Hero ── */}
      <section style={{ position: "relative", overflow: "hidden" }}>
        {!donneesReduites && (
          <Suspense fallback={null}>
            <StarfieldScene />
          </Suspense>
        )}
        <div className="dot-grid-bg" style={{ position: "absolute", inset: 0, opacity: 0.35, maskImage: "radial-gradient(ellipse 70% 60% at 50% 20%, black 0%, transparent 75%)" }} aria-hidden="true" />
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
            {/* Objets 3D décoratifs — diplôme et médaille flottants */}
            <div className="obj-scene" style={{ left: "-46px", top: "-30px", zIndex: 2 }}>
              <DiplomaCard style={{ transform: "translateZ(20px)" }} />
            </div>
            <div className="obj-scene" style={{ left: "-24px", bottom: "-18px", zIndex: 4 }}>
              <FloatingMedal style={{ transform: "translateZ(40px)" }} />
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

      {/* ── Teaser établissements : renvoie vers l'annuaire dédié, jamais la liste
           complète ici — la plateforme a vocation nationale, le nombre
           d'établissements ne doit jamais être supposé petit. ── */}
      <section style={{ maxWidth: "1200px", margin: "0 auto", padding: "64px 24px" }}>
        <Link
          to="/etablissements"
          className="card-hover"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "20px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            padding: "32px 40px",
            boxShadow: "var(--shadow-md)",
            textDecoration: "none",
            color: "inherit",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
            <div
              style={{
                width: "52px",
                height: "52px",
                borderRadius: "var(--radius-md)",
                background: "var(--primary-tint)",
                color: "var(--primary-deep)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              <Landmark size={26} />
            </div>
            <div>
              <p className="text-eyebrow" style={{ marginBottom: "6px", display: "block" }}>Annuaire national</p>
              <h2 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)", fontWeight: 700, margin: "0 0 4px", color: "var(--ink)" }}>
                {vitrine ? `${vitrine.totaux.etablissements} établissement${vitrine.totaux.etablissements > 1 ? "s" : ""} partenaire${vitrine.totaux.etablissements > 1 ? "s" : ""}` : "Découvrez les établissements partenaires"}
              </h2>
              <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: 0 }}>
                {vitrine && vitrine.totaux.postes_ouverts > 0
                  ? `${vitrine.totaux.postes_ouverts} poste${vitrine.totaux.postes_ouverts > 1 ? "s" : ""} d'enseignant ouvert${vitrine.totaux.postes_ouverts > 1 ? "s" : ""} en ce moment · campagnes d'inscription actives`
                  : "Campagnes d'inscription et recrutement des enseignants, établissement par établissement"}
              </p>
            </div>
          </div>
          <span
            className="btn btn-primary"
            style={{ flexShrink: 0, display: "inline-flex", alignItems: "center", gap: "6px" }}
          >
            Voir l'annuaire <ChevronRight size={16} />
          </span>
        </Link>
        {!vitrineErreur && vitrine && vitrine.etablissements.length > 0 && (
          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "18px" }}>
            {vitrine.etablissements.map((e) => (
              <Link
                key={e.id}
                to="/etablissements"
                className="chip chip-neutral"
                style={{ textDecoration: "none" }}
              >
                {e.nom} · {TYPE_LABEL[e.type]}
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* ── Nouveautés Phase 2/3 ── */}
      <section
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
              Au-delà de la classe
            </p>
            <h2 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
              La vie scolaire, toute entière.
            </h2>
            <p style={{ color: "var(--ink-soft)", maxWidth: "52ch", margin: "0 auto", fontSize: "var(--text-lg)" }}>
              Communication, transport, cantine, événements et bien plus — tout ce qui entoure l'école, au même endroit.
            </p>
          </div>

          <div className="grid-3">
            {NOUVEAUTES.map((f, i) => (
              <div
                key={f.title}
                className="card card-hover anim-float-in"
                style={{ animationDelay: `${i * 60}ms`, position: "relative", opacity: f.bientot ? 0.85 : 1 }}
              >
                {f.bientot && (
                  <span
                    className="chip chip-pending"
                    style={{ position: "absolute", top: "16px", right: "16px" }}
                  >
                    Bientôt disponible
                  </span>
                )}
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

      {/* ── Innovations famille (Élève/Tuteur) ── */}
      <section style={{ maxWidth: "1200px", margin: "0 auto", padding: "80px 24px" }}>
        <div style={{ textAlign: "center", marginBottom: "56px" }}>
          <p className="text-eyebrow" style={{ marginBottom: "12px", display: "block" }}>
            Pensé pour la famille
          </p>
          <h2 className="text-headline" style={{ margin: "0 0 12px", color: "var(--ink)" }}>
            Le tuteur, jamais tenu à l'écart.
          </h2>
          <p style={{ color: "var(--ink-soft)", maxWidth: "56ch", margin: "0 auto", fontSize: "var(--text-lg)" }}>
            Quatre fonctionnalités pensées pour que le tuteur reste présent au quotidien, sans jamais réduire l'autonomie de son enfant.
          </p>
        </div>

        <div className="grid-2">
          {INNOVATIONS_FAMILLE.map((f, i) => (
            <div
              key={f.title}
              className="card card-hover anim-float-in"
              style={{ display: "flex", gap: "18px", animationDelay: `${i * 60}ms` }}
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
                  flexShrink: 0,
                }}
              >
                {f.icon}
              </div>
              <div>
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
            </div>
          ))}
        </div>
      </section>

      {/* ── XP Demo strip ── */}
      <section style={{ maxWidth: "1200px", margin: "0 auto", padding: "80px 24px" }}>
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-xl)",
            boxShadow: "var(--shadow-xl)",
          }}
          className="landing-xp-demo"
        >
          <div className="landing-xp-grille">
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

      {/* ── Bande photo : vraie vie de classe (photo libre de droits, Pexels) ── */}
      <section
        style={{
          position: "relative",
          minHeight: "340px",
          display: "flex",
          alignItems: "center",
          // Lot 7.5 : photo décorative non téléchargée en mode données réduites.
          backgroundImage: donneesReduites
            ? "linear-gradient(90deg, #0B4F30 0%, #0F7A45 100%)"
            : `linear-gradient(90deg, rgba(11,18,14,0.82) 0%, rgba(11,18,14,0.45) 55%, rgba(11,18,14,0.15) 100%), url(${PHOTO_HERO_CLASSE})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "48px 24px", width: "100%" }}>
          <p className="text-eyebrow" style={{ color: "rgba(255,255,255,0.75)", marginBottom: "12px" }}>
            Sur le terrain
          </p>
          <h2 className="text-headline" style={{ margin: "0 0 16px", color: "#fff", maxWidth: "36ch" }}>
            La vraie vie d'une classe, chaque jour.
          </h2>
          <p style={{ color: "rgba(255,255,255,0.85)", maxWidth: "48ch", fontSize: "var(--text-lg)", margin: 0 }}>
            Derrière chaque tableau de bord, des élèves, des enseignants et des établissements bien réels — du primaire au supérieur.
          </p>
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
            <Link to="/connexion" style={{ color: "var(--primary-deep)", fontWeight: 700, textDecoration: "none" }}>
              Se connecter →
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
