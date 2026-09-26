import { type ReactNode, useState, useEffect, createContext, useContext } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Avatar, RolePill } from "../components/Avatar";
import { Footer } from "../components/Footer";
import { XPBar } from "../components/gamification";
import {
  LayoutDashboard,
  BookOpen,
  ClipboardList,
  FileText,
  Award,
  Users,
  GraduationCap,
  Briefcase,
  ScrollText,
  Building2,
  Settings,
  LogOut,
  Sun,
  Moon,
  ChevronLeft,
  PencilRuler,
  UserCheck,
  Scale,
  MessageCircle,
  Flag,
  Radio,
  Bus,
  Ticket,
  ShieldCheck,
  CalendarDays,
  Handshake,
  Gavel,
  ShoppingBag,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════
   Dark mode context
   ═══════════════════════════════════════════════════════════════ */

const ThemeCtx = createContext<{
  dark: boolean;
  toggle: () => void;
}>({ dark: false, toggle: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("ls-theme");
    if (saved) return saved === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("ls-theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <ThemeCtx.Provider value={{ dark, toggle: () => setDark((d) => !d) }}>
      {children}
    </ThemeCtx.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeCtx);
}

/* ═══════════════════════════════════════════════════════════════
   Nav items par rôle
   ═══════════════════════════════════════════════════════════════ */

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
}

function navPourRole(role: string | undefined): NavItem[] {
  const iconSize = 18;
  if (role === "tuteur") {
    return [
      { to: "/tuteur", label: "Mes enfants", icon: <Users size={iconSize} />, end: true },
      { to: "/tuteur/nouvelle-inscription", label: "Nouvelle inscription", icon: <UserCheck size={iconSize} /> },
      { to: "/tuteur/services", label: "Transport & cantine", icon: <Bus size={iconSize} /> },
      { to: "/billetterie", label: "Billetterie", icon: <Ticket size={iconSize} /> },
      { to: "/micro-jobs", label: "Micro-jobs", icon: <Handshake size={iconSize} /> },
      { to: "/messagerie", label: "Messagerie", icon: <MessageCircle size={iconSize} /> },
    ];
  }
  if (role === "eleve") {
    return [
      { to: "/eleve", label: "Tableau de bord", icon: <LayoutDashboard size={iconSize} />, end: true },
      { to: "/eleve/cours", label: "Cours", icon: <BookOpen size={iconSize} /> },
      { to: "/eleve/devoirs", label: "Devoirs", icon: <ClipboardList size={iconSize} /> },
      { to: "/eleve/bulletin", label: "Bulletin", icon: <Award size={iconSize} /> },
      { to: "/eleve/actes", label: "Actes académiques", icon: <FileText size={iconSize} /> },
      { to: "/eleve/cours-direct", label: "Cours en direct", icon: <Radio size={iconSize} /> },
      { to: "/eleve/services", label: "Transport & cantine", icon: <Bus size={iconSize} /> },
      { to: "/billetterie", label: "Billetterie", icon: <Ticket size={iconSize} /> },
      { to: "/micro-jobs", label: "Micro-jobs", icon: <Handshake size={iconSize} /> },
      { to: "/eleve/marketplace", label: "Marketplace", icon: <ShoppingBag size={iconSize} /> },
      { to: "/messagerie", label: "Messagerie", icon: <MessageCircle size={iconSize} /> },
    ];
  }
  if (role === "enseignant") {
    return [
      { to: "/enseignant", label: "Tableau de bord", icon: <LayoutDashboard size={iconSize} />, end: true },
      { to: "/enseignant/postes", label: "Postes ouverts", icon: <Briefcase size={iconSize} /> },
      { to: "/enseignant/candidatures", label: "Mes candidatures", icon: <ScrollText size={iconSize} /> },
      { to: "/enseignant/contrats", label: "Mes contrats", icon: <FileText size={iconSize} /> },
      { to: "/enseignant/cours", label: "Mes cours", icon: <BookOpen size={iconSize} /> },
      { to: "/enseignant/devoirs", label: "Mes devoirs", icon: <PencilRuler size={iconSize} /> },
      { to: "/enseignant/cours-direct", label: "Cours en direct", icon: <Radio size={iconSize} /> },
      { to: "/billetterie", label: "Billetterie", icon: <Ticket size={iconSize} /> },
      { to: "/micro-jobs", label: "Micro-jobs", icon: <Handshake size={iconSize} /> },
      { to: "/valider-acces", label: "Valider un accès", icon: <ShieldCheck size={iconSize} /> },
      { to: "/messagerie", label: "Messagerie", icon: <MessageCircle size={iconSize} /> },
    ];
  }
  if (role === "admin_etablissement") {
    return [
      { to: "/admin-etablissement", label: "Tableau de bord", icon: <LayoutDashboard size={iconSize} />, end: true },
      { to: "/admin-etablissement/inscriptions", label: "Inscriptions", icon: <UserCheck size={iconSize} /> },
      { to: "/admin-etablissement/classes", label: "Classes", icon: <GraduationCap size={iconSize} /> },
      { to: "/admin-etablissement/postes", label: "Recrutement", icon: <Briefcase size={iconSize} /> },
      { to: "/admin-etablissement/contestations", label: "Contestations", icon: <Scale size={iconSize} /> },
      { to: "/admin-etablissement/actes", label: "Actes académiques", icon: <FileText size={iconSize} /> },
      { to: "/admin-etablissement/referentiels", label: "Référentiels", icon: <Settings size={iconSize} /> },
      { to: "/admin-etablissement/services", label: "Transport & cantine", icon: <Bus size={iconSize} /> },
      { to: "/admin-etablissement/evenements", label: "Événements", icon: <CalendarDays size={iconSize} /> },
      { to: "/micro-jobs", label: "Micro-jobs", icon: <Handshake size={iconSize} /> },
      { to: "/admin-etablissement/marketplace", label: "Marketplace", icon: <ShoppingBag size={iconSize} /> },
      { to: "/valider-acces", label: "Valider un accès", icon: <ShieldCheck size={iconSize} /> },
      { to: "/admin-etablissement/signalements", label: "Signalements", icon: <Flag size={iconSize} /> },
    ];
  }
  if (role === "admin_ministeriel") {
    return [
      { to: "/admin-ministeriel", label: "Tableau de bord", icon: <LayoutDashboard size={iconSize} />, end: true },
      { to: "/admin-ministeriel/etablissements", label: "Établissements", icon: <Building2 size={iconSize} /> },
      { to: "/admin-ministeriel/referentiels", label: "Référentiels", icon: <Settings size={iconSize} /> },
      { to: "/admin-ministeriel/micro-jobs-arbitrage", label: "Arbitrage micro-jobs", icon: <Gavel size={iconSize} /> },
    ];
  }
  return [];
}

/* ═══════════════════════════════════════════════════════════════
   Wordmark Logo
   ═══════════════════════════════════════════════════════════════ */

function Wordmark({ collapsed }: { collapsed: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
      <img
        src="/logo.png"
        alt="LuluSchools"
        width={36}
        height={36}
        style={{ width: "36px", height: "36px", objectFit: "contain", flexShrink: 0 }}
      />
      {!collapsed && (
        <span className="sidebar-wordmark">
          Lulu<span className="dot">·</span>Schools
        </span>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Sidebar Desktop
   ═══════════════════════════════════════════════════════════════ */

function DesktopSidebar({
  items,
  collapsed,
  onToggleCollapse,
}: {
  items: NavItem[];
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const { utilisateur, seDeconnecter } = useAuth();
  const { dark, toggle: toggleTheme } = useTheme();

  return (
    <aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""}`}>
      {/* Header */}
      <div className="sidebar-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <NavLink to="/" className="sidebar-logo" aria-label="LuluSchools — Accueil">
            <Wordmark collapsed={collapsed} />
          </NavLink>
          <button
            onClick={onToggleCollapse}
            className="btn btn-ghost btn-icon"
            style={{ marginLeft: "auto" }}
            aria-label={collapsed ? "Développer la navigation" : "Réduire la navigation"}
          >
            <ChevronLeft
              size={16}
              style={{
                transform: collapsed ? "rotate(180deg)" : "none",
                transition: "transform 0.3s ease",
              }}
            />
          </button>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav" aria-label="Navigation principale">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `sidebar-nav-item ${isActive ? "active" : ""}`
            }
            title={collapsed ? item.label : undefined}
            aria-label={item.label}
          >
            <span className="sidebar-nav-icon">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer — Avatar + contrôles */}
      <div className="sidebar-footer">
        {utilisateur && (
          <div style={{ marginBottom: "12px" }}>
            {!collapsed && (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <Avatar
                    role={utilisateur.role}
                    prenom={utilisateur.prenom}
                    nom={utilisateur.nom}
                    size={36}
                  />
                  <div style={{ overflow: "hidden", flex: 1 }}>
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: "var(--text-sm)",
                        color: "var(--ink)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {utilisateur.prenom} {utilisateur.nom}
                    </div>
                    <RolePill role={utilisateur.role} />
                  </div>
                </div>
                {/* Mini XP bar pour élève */}
                {utilisateur.role === "eleve" && (
                  <XPBar current={680} max={1000} level={4} />
                )}
              </>
            )}
            {collapsed && (
              <div style={{ display: "flex", justifyContent: "center" }}>
                <Avatar role={utilisateur.role} prenom={utilisateur.prenom} nom={utilisateur.nom} size={36} />
              </div>
            )}
          </div>
        )}

        {/* Dark mode + Déconnexion */}
        <div style={{ display: "flex", gap: "8px", justifyContent: collapsed ? "center" : "flex-start", flexWrap: "wrap" }}>
          <button
            onClick={toggleTheme}
            className="btn btn-ghost btn-icon btn-sm"
            aria-label={dark ? "Activer le mode clair" : "Activer le mode sombre"}
            title={dark ? "Mode clair" : "Mode sombre"}
          >
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          {utilisateur && (
            <button
              onClick={seDeconnecter}
              className="btn btn-ghost btn-sm"
              aria-label="Se déconnecter"
              title="Déconnexion"
              style={{ color: "var(--action)", gap: "6px" }}
            >
              <LogOut size={14} />
              {!collapsed && <span>Déconnexion</span>}
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Bottom Navigation Mobile
   ═══════════════════════════════════════════════════════════════ */

function BottomNav({ items }: { items: NavItem[] }) {
  const location = useLocation();
  const visibleItems = items.slice(0, 5);

  return (
    <nav className="bottom-nav" aria-label="Navigation principale">
      <div className="bottom-nav-items">
        {visibleItems.map((item) => {
          const isActive = location.pathname === item.to ||
            (!item.end && location.pathname.startsWith(item.to));
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={`bottom-nav-item ${isActive ? "active" : ""}`}
              aria-label={item.label}
              aria-current={isActive ? "page" : undefined}
            >
              <span style={{ width: "20px", height: "20px" }}>{item.icon}</span>
              <span>{item.label.split(" ")[0]}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Mobile Header
   ═══════════════════════════════════════════════════════════════ */

function MobileHeader() {
  const { dark, toggle } = useTheme();
  const { utilisateur } = useAuth();
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: "var(--z-sticky)",
        background: "var(--surface)",
        borderBottom: "2px solid var(--border-strong)",
        boxShadow: "0 2px 0 var(--border-strong)",
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <NavLink to="/" style={{ textDecoration: "none" }} aria-label="LuluSchools — Accueil">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              width: "30px",
              height: "30px",
              borderRadius: "50%",
              background: "radial-gradient(circle at 32% 28%, #A9F0C6, var(--primary) 70%)",
              border: "2px solid var(--border-strong)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "11px",
              color: "var(--on-primary)",
            }}
          >
            LS
          </div>
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontWeight: 700,
              fontSize: "var(--text-lg)",
              color: "var(--ink)",
            }}
          >
            Lulu<span style={{ color: "var(--reward)" }}>·</span>Schools
          </span>
        </div>
      </NavLink>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <button onClick={toggle} className="btn btn-ghost btn-icon btn-sm" aria-label="Basculer le thème">
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        {utilisateur && (
          <Avatar role={utilisateur.role} prenom={utilisateur.prenom} nom={utilisateur.nom} size={32} />
        )}
      </div>
    </header>
  );
}

/* ═══════════════════════════════════════════════════════════════
   AppLayout — Layout principal
   ═══════════════════════════════════════════════════════════════ */

export function AppLayout({ children }: { children: ReactNode }) {
  const { utilisateur } = useAuth();
  const items = navPourRole(utilisateur?.role);
  const [collapsed, setCollapsed] = useState(false);

  // Sur petits écrans, auto-collapse
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1200px)");
    const handler = (e: MediaQueryListEvent) => setCollapsed(e.matches);
    setCollapsed(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const isPublicPage = !utilisateur;

  if (isPublicPage) {
    /* Pages publiques : pas de sidebar, layout centré, footer global (mentions
       légales, cookies...) - pas repété sur les tableaux de bord authentifiés
       pour ne pas entrer en collision avec la barre de navigation mobile. */
    return (
      <div style={{ minHeight: "100dvh", background: "var(--bg)", display: "flex", flexDirection: "column" }}>
        <div style={{ flex: 1 }}>{children}</div>
        <Footer />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100dvh", background: "var(--bg)" }}>
      {/* Sidebar desktop (masquée < 768px via CSS) */}
      {items.length > 0 && (
        <DesktopSidebar
          items={items}
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed((c) => !c)}
        />
      )}

      {/* Header mobile */}
      <div style={{ display: "none" }} className="mobile-header-wrapper">
        <MobileHeader />
      </div>

      {/* Contenu principal */}
      <main
        className={`app-with-sidebar ${collapsed ? "sidebar-collapsed-layout" : ""}`}
        id="main-content"
        tabIndex={-1}
        aria-label="Contenu principal"
      >
        {children}
      </main>

      {/* Bottom nav mobile */}
      {items.length > 0 && <BottomNav items={items} />}
    </div>
  );
}
