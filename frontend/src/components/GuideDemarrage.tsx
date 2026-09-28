import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

/* Guide de première connexion : les quatre premières choses à faire, par rôle, en tête du
   tableau de bord. Fermé une fois, il ne réapparaît plus pour cet utilisateur sur cet
   appareil (préférence locale : il n'y a rien de critique à conserver côté serveur). */

interface Etape {
  titre: string;
  detail: string;
  lien?: string;
}

const GUIDES: Record<string, { intro: string; etapes: Etape[] }> = {
  tuteur: {
    intro: "Voici comment suivre la scolarité de vos enfants.",
    etapes: [
      { titre: "Inscrire un enfant", detail: "Choisissez l'établissement et la classe ; l'école valide ensuite l'inscription.", lien: "/tuteur/nouvelle-inscription" },
      { titre: "Donner votre consentement", detail: "Obligatoire pour un enfant de moins de 16 ans : le bouton apparaît dans « Mes enfants ».", lien: "/tuteur" },
      { titre: "Suivre au quotidien", detail: "Devoirs, notes, vie scolaire et dépenses : tout est sur la fiche de chaque enfant.", lien: "/tuteur" },
      { titre: "Demander conseil", detail: "El Professor répond à vos questions sur la scolarité et l'orientation.", lien: "/tuteur/el-professor" },
    ],
  },
  eleve: {
    intro: "Voici l'essentiel pour bien démarrer.",
    etapes: [
      { titre: "Vos cours", detail: "Lisez les cours de vos enseignants et posez vos questions à El Professor.", lien: "/eleve/cours" },
      { titre: "Vos devoirs", detail: "Rendez-les avant la date limite : un devoir non rendu compte 0.", lien: "/eleve/devoirs" },
      { titre: "Votre bulletin", detail: "Votre moyenne se met à jour à chaque correction, période par période.", lien: "/eleve/bulletin" },
      { titre: "Vos documents", detail: "Demandez une attestation de scolarité ou un relevé de notes en ligne.", lien: "/eleve/actes" },
    ],
  },
  enseignant: {
    intro: "Voici comment démarrer sur LuluSchools.",
    etapes: [
      { titre: "Postuler", detail: "Consultez les postes ouverts et déposez vos pièces : elles sont notées automatiquement.", lien: "/enseignant/postes" },
      { titre: "Signer votre contrat", detail: "Une fois retenu, le contrat vous attend ici ; signez-le en ligne.", lien: "/enseignant/contrats" },
      { titre: "Publier cours et devoirs", detail: "Les copies sont corrigées par l'IA selon votre barème ; vous gardez la main.", lien: "/enseignant/devoirs" },
      { titre: "Faire cours en direct", detail: "Tableau partagé, chat et résumé de séance pour les absents.", lien: "/enseignant/cours-direct" },
    ],
  },
  admin_etablissement: {
    intro: "Voici par où commencer pour administrer votre établissement.",
    etapes: [
      { titre: "Ouvrir « À traiter »", detail: "Tout ce qui attend une décision, avec les actions groupées et l'aide de l'IA.", lien: "/admin-etablissement/a-traiter" },
      { titre: "Préparer la rentrée", detail: "Créez les classes et ouvrez les inscriptions aux familles.", lien: "/admin-etablissement/rentree" },
      { titre: "Recruter", detail: "Publiez des postes : les candidatures sont notées, il vous reste à décider.", lien: "/admin-etablissement/postes" },
      { titre: "Automatiser", detail: "Activez l'admission automatique et la livraison automatique des actes.", lien: "/admin-etablissement/a-traiter" },
    ],
  },
  admin_ministeriel: {
    intro: "Voici les principaux leviers de l'administration ministérielle.",
    etapes: [
      { titre: "Ouvrir « À traiter »", detail: "Litiges, reversements et propositions de coefficients, en un seul endroit.", lien: "/admin-ministeriel/a-traiter" },
      { titre: "Référentiels", detail: "Fixez les coefficients nationaux et validez les propositions des écoles.", lien: "/admin-ministeriel/referentiels" },
      { titre: "Établissements", detail: "Créez les établissements et leurs administrateurs.", lien: "/admin-ministeriel/etablissements" },
      { titre: "Journal d'audit", detail: "Chaque action ministérielle y est tracée.", lien: "/admin-ministeriel/journal-audit" },
    ],
  },
};

const cle = (id: string) => `lulu_guide_ferme_${id}`;

function dejaFerme(id: string): boolean {
  try {
    return localStorage.getItem(cle(id)) === "1";
  } catch {
    return false;
  }
}

export function GuideDemarrage() {
  const { utilisateur } = useAuth();
  const [ferme, setFerme] = useState(() => (utilisateur ? dejaFerme(utilisateur.id) : true));
  const guide = utilisateur ? GUIDES[utilisateur.role] : undefined;
  if (!utilisateur || !guide || ferme) return null;

  const fermer = () => {
    try {
      localStorage.setItem(cle(utilisateur.id), "1");
    } catch {
      /* stockage indisponible : le guide sera simplement proposé à nouveau */
    }
    setFerme(true);
  };

  return (
    <section className="guide-demarrage anim-slide-up" aria-labelledby="guide-demarrage-titre">
      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
        <Sparkles size={20} aria-hidden="true" style={{ color: "var(--magic-deep)", flexShrink: 0, marginTop: "2px" }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <h2 id="guide-demarrage-titre" style={{ margin: 0, fontSize: "var(--text-lg)", color: "var(--ink)" }}>
            Bienvenue, {utilisateur.prenom} !
          </h2>
          <p className="text-sm" style={{ margin: "2px 0 0", color: "var(--ink-soft)" }}>{guide.intro}</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={fermer} aria-label="Fermer le guide de démarrage">
          <X size={16} /> <span className="guide-fermer-texte">J'ai compris</span>
        </button>
      </div>
      <ol className="guide-etapes">
        {guide.etapes.map((e, i) => (
          <li key={e.titre}>
            <span className="guide-numero" aria-hidden="true">{i + 1}</span>
            <div style={{ minWidth: 0 }}>
              {e.lien ? (
                <Link to={e.lien} className="guide-lien">
                  {e.titre} <ArrowRight size={13} aria-hidden="true" />
                </Link>
              ) : (
                <strong>{e.titre}</strong>
              )}
              <p className="text-sm" style={{ margin: "2px 0 0", color: "var(--ink-soft)" }}>{e.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
