import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GuideDemarrage } from "../../components/GuideDemarrage";
import { useEleveProfil } from "../../eleve/EleveProfileContext";
import { listerDevoirs, maSoumission, obtenirBulletin, periodesDeLaClasse, type PeriodeOut } from "../../api/evaluations";
import { obtenirMonPasseport } from "../../api/passeport";
import type { BadgeOut, DevoirOut } from "../../types/api";
import { Badge, Card, EmptyState, SectionHead, Skeleton } from "../../components/ui";
import { ValidationsEnAttenteBanner } from "../../components/coffre_fort/ValidationsEnAttenteBanner";
import {
  Award, BookOpen, Bot, Bus, CircleCheck, ClipboardCheck, ClipboardList, FileText, Handshake, MessageCircle, Radio,
  ShoppingBag, Ticket, Trophy,
} from "lucide-react";

/* Tableau de bord élève : uniquement des données réelles — devoirs à rendre, moyenne de la
   période en cours, badges du passeport de compétences — et les raccourcis utiles. */

function echeance(dateLimite: string): { texte: string; urgent: boolean } {
  const ms = new Date(dateLimite).getTime() - Date.now();
  const heures = Math.round(ms / 3_600_000);
  if (heures < 24) return { texte: heures <= 1 ? "dans moins d'une heure" : `dans ${heures} h`, urgent: true };
  const jours = Math.round(heures / 24);
  return { texte: jours === 1 ? "demain" : `dans ${jours} jours`, urgent: jours <= 2 };
}

export function EleveDashboard() {
  const profil = useEleveProfil();
  const [aRendre, setARendre] = useState<DevoirOut[] | null>(null);
  const [periode, setPeriode] = useState<PeriodeOut | null>(null);
  const [moyenne, setMoyenne] = useState<number | null | undefined>(undefined);
  const [badges, setBadges] = useState<BadgeOut[]>([]);

  useEffect(() => {
    if (!profil.classe_id) return;
    const classeId = profil.classe_id;
    listerDevoirs(classeId)
      .then(async (res) => {
        const ouverts = res.data
          .filter((d) => new Date(d.date_limite).getTime() > Date.now())
          .sort((a, b) => a.date_limite.localeCompare(b.date_limite));
        const rendus = await Promise.all(ouverts.map((d) => maSoumission(d.id).then(() => true).catch(() => false)));
        setARendre(ouverts.filter((_, i) => !rendus[i]));
      })
      .catch(() => setARendre([]));
    periodesDeLaClasse(classeId)
      .then(async (res) => {
        const courante = res.data.find((p) => p.courante) ?? res.data[0] ?? null;
        setPeriode(courante);
        if (!courante) return setMoyenne(null);
        try {
          setMoyenne((await obtenirBulletin(profil.id, classeId, courante.code)).data.moyenne_generale);
        } catch {
          setMoyenne(null);
        }
      })
      .catch(() => setMoyenne(null));
    obtenirMonPasseport()
      .then((res) => setBadges(res.data.badges))
      .catch(() => setBadges([]));
  }, [profil.classe_id, profil.id]);

  /* ── État : pas encore inscrit ── */
  if (!profil.classe_id) {
    return (
      <div className="page-content">
        <div style={{ marginBottom: "8px" }}>
          <h1 className="text-headline" style={{ color: "var(--ink)", margin: 0 }}>
            Bienvenue, {profil.prenom}
          </h1>
        </div>
        <div className="card" style={{ marginTop: "24px", maxWidth: "480px" }}>
          <EmptyState
            icon={<ClipboardCheck size={24} />}
            title="Inscription en attente"
            desc="Aucune inscription validée pour l'instant. Votre tuteur doit soumettre et faire valider une inscription avant que vous puissiez accéder à vos cours."
          />
        </div>
      </div>
    );
  }

  const raccourcis = [
    { to: "/eleve/cours", icon: <BookOpen size={22} />, tone: "info", title: "Cours", desc: "Lire les cours et faire des quiz" },
    { to: "/eleve/el-professor", icon: <Bot size={22} />, tone: "magic", title: "El Professor", desc: "Comprendre un cours, réviser" },
    { to: "/eleve/actes", icon: <FileText size={22} />, tone: "magic", title: "Actes académiques", desc: "Attestations, relevés, réclamations" },
    { to: "/eleve/cours-direct", icon: <Radio size={22} />, tone: "primary", title: "Cours en direct", desc: "Rejoindre une séance de ma classe" },
    { to: "/eleve/services", icon: <Bus size={22} />, tone: "action", title: "Transport & cantine", desc: "Réserver mes tickets" },
    { to: "/billetterie", icon: <Ticket size={22} />, tone: "reward", title: "Billetterie", desc: "Événements de mon établissement" },
    ...(profil.est_etudiant
      ? [
          { to: "/micro-jobs", icon: <Handshake size={22} />, tone: "action", title: "Micro-jobs", desc: "Proposer ou demander un service" },
          { to: "/eleve/marketplace", icon: <ShoppingBag size={22} />, tone: "reward", title: "Marketplace", desc: "Acheter et vendre entre étudiants" },
        ]
      : []),
    { to: "/messagerie", icon: <MessageCircle size={22} />, tone: "info", title: "Messagerie", desc: "Groupe de classe et messages" },
    { to: "/eleve/passeport", icon: <Award size={22} />, tone: "reward", title: "Passeport de compétences", desc: "Moyennes par matière, badges, export" },
  ];

  return (
    <div className="page-content">
      <GuideDemarrage />
      <div style={{ marginBottom: "24px" }}>
        <p className="text-eyebrow" style={{ marginBottom: "6px" }}>Tableau de bord élève</p>
        <h1 className="text-headline" style={{ color: "var(--ink)", margin: "0 0 8px" }}>Bonjour, {profil.prenom}</h1>
        <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-sm)", margin: 0 }}>
          {profil.niveau}
          {profil.matricule && <span className="monospace"> · matricule {profil.matricule}</span>}
        </p>
      </div>

      <ValidationsEnAttenteBanner />

      <div className="grid-2" style={{ marginBottom: "32px" }}>
        {/* ── À rendre ── */}
        <Card>
          <div className="flex items-center justify-between gap-2" style={{ marginBottom: "10px" }}>
            <h2 className="text-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <ClipboardList size={20} aria-hidden="true" /> À rendre
            </h2>
            <Link to="/eleve/devoirs" className="text-sm" style={{ color: "var(--primary-deep)", fontWeight: 600 }}>Tous les devoirs</Link>
          </div>
          {aRendre === null ? (
            <Skeleton height="60px" />
          ) : aRendre.length === 0 ? (
            <p className="text-sm" style={{ display: "flex", alignItems: "center", gap: "8px", margin: 0, color: "var(--ink-soft)" }}>
              <CircleCheck size={18} aria-hidden="true" style={{ color: "var(--primary-deep)" }} /> Rien à rendre pour le moment.
            </p>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {aRendre.slice(0, 4).map((d) => {
                const e = echeance(d.date_limite);
                return (
                  <li key={d.id} style={{ borderTop: "1px solid var(--border)" }}>
                    <Link to={`/eleve/devoirs/${d.id}`} className="flex items-center justify-between gap-3" style={{ padding: "10px 0", textDecoration: "none", color: "var(--ink)" }}>
                      <span style={{ minWidth: 0 }}>
                        <span style={{ display: "block", fontWeight: 600 }}>{d.titre}</span>
                        <span className="text-sm" style={{ color: "var(--ink-soft)" }}>{d.matiere}</span>
                      </span>
                      <Badge tone={e.urgent ? "error" : "pending"}>{e.texte}</Badge>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* ── Moyenne de la période ── */}
        <Card>
          <div className="flex items-center justify-between gap-2" style={{ marginBottom: "10px" }}>
            <h2 className="text-title" style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <Trophy size={20} aria-hidden="true" /> {periode ? periode.libelle.charAt(0).toUpperCase() + periode.libelle.slice(1) : "Bulletin"}
            </h2>
            <Link to="/eleve/bulletin" className="text-sm" style={{ color: "var(--primary-deep)", fontWeight: 600 }}>Voir le bulletin</Link>
          </div>
          {moyenne === undefined ? (
            <Skeleton height="60px" />
          ) : moyenne === null ? (
            <p className="text-sm" style={{ margin: 0, color: "var(--ink-soft)" }}>
              Pas encore de moyenne : elle apparaîtra dès la première copie corrigée de la période.
            </p>
          ) : (
            <p style={{ margin: 0, fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "var(--text-4xl)", color: moyenne >= 50 ? "var(--primary-deep)" : "var(--action-deep)", lineHeight: 1.1 }}>
              {Math.round(moyenne * 10) / 10}
              <span style={{ fontSize: "var(--text-lg)", color: "var(--ink-faint)", fontWeight: 600 }}> / 100</span>
            </p>
          )}
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-2" style={{ marginTop: "12px" }}>
              {badges.map((b) => <Badge key={b.id} tone="success">{b.label}</Badge>)}
            </div>
          )}
        </Card>
      </div>

      {/* ── Raccourcis ── */}
      <SectionHead eyebrow="Navigation rapide" title="Accéder à vos activités" />
      <div className="grid-2">
        {raccourcis.map((item) => (
          <Link key={item.to} to={item.to} style={{ textDecoration: "none" }}>
            <div className="card card-hover" style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              <div
                aria-hidden="true"
                style={{
                  width: "44px", height: "44px", borderRadius: "var(--radius-md)", background: `var(--${item.tone}-tint)`,
                  display: "flex", alignItems: "center", justifyContent: "center", color: `var(--${item.tone}-deep, var(--${item.tone}))`, flexShrink: 0,
                }}
              >
                {item.icon}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "var(--text-lg)", color: "var(--ink)" }}>{item.title}</div>
                <div style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)" }}>{item.desc}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
