import { useEffect, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { Accessibility, Pause, Play, Square, Volume2 } from "lucide-react";
import { Modale } from "../components/Modale";
import { Btn } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import { useAccessibilite } from "./AccessibiliteContext";
import {
  AucuneVoixDisponible,
  arreterLecture,
  lireTexte,
  mettreEnPause,
  reprendreLecture,
  texteDeLaPage,
  useEtatLecture,
} from "./lecteurVocal";
import type { PreferencesAccessibilite } from "../api/accessibilite";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.2 — bouton et panneau d'accessibilité, présents sur toutes les pages.
   Raccourci clavier : Alt + A (ouvre le panneau), Alt + L (écouter la page).
   ═══════════════════════════════════════════════════════════════ */

const TAILLES: { valeur: PreferencesAccessibilite["taille"]; libelle: string; description: string }[] = [
  { valeur: "normal", libelle: "A", description: "Taille normale" },
  { valeur: "grand", libelle: "A+", description: "Texte agrandi" },
  { valeur: "tres_grand", libelle: "A++", description: "Texte très agrandi" },
];

const MODES_DONNEES: { valeur: PreferencesAccessibilite["donnees"]; libelle: string; aide: string }[] = [
  { valeur: "auto", libelle: "Automatique", aide: "Réduit dès que le réseau est lent ou que le téléphone économise les données." },
  { valeur: "reduit", libelle: "Toujours réduit", aide: "Pas d'animation 3D ni de chargement automatique des photos et vidéos." },
  { valeur: "normal", libelle: "Complet", aide: "Tout est chargé, même sur un réseau lent." },
];

async function ecouterLaPage(): Promise<string | null> {
  const texte = texteDeLaPage();
  if (!texte.trim()) return "Rien à lire sur cette page.";
  try {
    await lireTexte(texte);
    return null;
  } catch (erreur) {
    if (erreur instanceof AucuneVoixDisponible) {
      return "Aucune voix française n'est installée sur cet appareil. Connectez-vous pour utiliser la voix de LuluSchools.";
    }
    return "La lecture à voix haute est indisponible pour le moment.";
  }
}

function Interrupteur({
  libelle,
  aide,
  actif,
  onChange,
}: {
  libelle: string;
  aide: string;
  actif: boolean;
  onChange: (actif: boolean) => void;
}) {
  return (
    <label className="a11y-option">
      <input type="checkbox" role="switch" checked={actif} onChange={(e) => onChange(e.target.checked)} />
      <span>
        <span className="a11y-option-libelle">{libelle}</span>
        <span className="a11y-option-aide">{aide}</span>
      </span>
    </label>
  );
}

function ControlesLecture({ onMessage }: { onMessage: (message: string | null) => void }) {
  const etat = useEtatLecture();
  if (etat === "arret") {
    return (
      <Btn variant="primary" onClick={async () => onMessage(await ecouterLaPage())}>
        <Volume2 size={16} aria-hidden="true" /> Écouter cette page
      </Btn>
    );
  }
  return (
    <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
      {etat === "pause" ? (
        <Btn variant="primary" onClick={reprendreLecture}>
          <Play size={16} aria-hidden="true" /> Reprendre
        </Btn>
      ) : (
        <Btn variant="primary" onClick={mettreEnPause} disabled={etat === "chargement"}>
          <Pause size={16} aria-hidden="true" /> {etat === "chargement" ? "Préparation…" : "Pause"}
        </Btn>
      )}
      <Btn variant="ghost" onClick={arreterLecture}>
        <Square size={16} aria-hidden="true" /> Arrêter
      </Btn>
    </div>
  );
}

function PanneauAccessibilite({ ouvert, onFermer }: { ouvert: boolean; onFermer: () => void }) {
  const { preferences, modifier, reinitialiser, reseauLent, donneesReduites } = useAccessibilite();
  const { utilisateur } = useAuth();
  const [message, setMessage] = useState<string | null>(null);

  return (
    <Modale
      ouvert={ouvert}
      titre="Accessibilité"
      onFermer={onFermer}
      pied={
        <Btn variant="ghost" onClick={reinitialiser}>
          Revenir aux réglages d'origine
        </Btn>
      }
    >
      <section className="a11y-section" aria-labelledby="a11y-ecouter">
        <h3 id="a11y-ecouter" className="a11y-titre">Écouter</h3>
        <ControlesLecture onMessage={setMessage} />
        <p className="a11y-option-aide" role="status">
          {message ?? "Astuce : sélectionnez un passage pour n'écouter que lui. Raccourci : Alt + L."}
        </p>
      </section>

      <section className="a11y-section" aria-labelledby="a11y-taille">
        <h3 id="a11y-taille" className="a11y-titre">Taille du texte</h3>
        <div className="a11y-segments" role="group" aria-labelledby="a11y-taille">
          {TAILLES.map((t) => (
            <button
              key={t.valeur}
              type="button"
              className="a11y-segment"
              aria-pressed={preferences.taille === t.valeur}
              aria-label={t.description}
              onClick={() => modifier({ taille: t.valeur })}
            >
              {t.libelle}
            </button>
          ))}
        </div>
      </section>

      <section className="a11y-section" aria-labelledby="a11y-lisibilite">
        <h3 id="a11y-lisibilite" className="a11y-titre">Lisibilité</h3>
        <Interrupteur
          libelle="Contraste élevé"
          aide="Textes plus foncés, bordures marquées, liens soulignés."
          actif={preferences.contraste}
          onChange={(contraste) => modifier({ contraste })}
        />
        <Interrupteur
          libelle="Espacement renforcé"
          aide="Plus d'espace entre les lignes, les mots et les lettres (dyslexie)."
          actif={preferences.espacement}
          onChange={(espacement) => modifier({ espacement })}
        />
        <Interrupteur
          libelle="Réduire les animations"
          aide="Supprime les mouvements et effets de défilement."
          actif={preferences.animations_reduites}
          onChange={(animations_reduites) => modifier({ animations_reduites })}
        />
      </section>

      <section className="a11y-section" aria-labelledby="a11y-donnees">
        <h3 id="a11y-donnees" className="a11y-titre">Connexion internet</h3>
        <div role="radiogroup" aria-labelledby="a11y-donnees">
          {MODES_DONNEES.map((m) => (
            <label key={m.valeur} className="a11y-option">
              <input
                type="radio"
                name="a11y-donnees"
                checked={preferences.donnees === m.valeur}
                onChange={() => modifier({ donnees: m.valeur })}
              />
              <span>
                <span className="a11y-option-libelle">{m.libelle}</span>
                <span className="a11y-option-aide">{m.aide}</span>
              </span>
            </label>
          ))}
        </div>
        <p className="a11y-option-aide">
          {reseauLent ? "Réseau lent détecté. " : ""}
          Mode données réduites : {donneesReduites ? "activé" : "désactivé"}.
        </p>
      </section>

      {utilisateur?.role === "tuteur" && (
        <section className="a11y-section" aria-labelledby="a11y-ecoute">
          <h3 id="a11y-ecoute" className="a11y-titre">Mode Écoute</h3>
          <Interrupteur
            libelle="Accueil en images et en voix"
            aide="Grandes images qui se lisent à voix haute : pour les personnes qui ne lisent pas ou peu."
            actif={preferences.mode_ecoute}
            onChange={(mode_ecoute) => modifier({ mode_ecoute })}
          />
        </section>
      )}
    </Modale>
  );
}

/** Mini-lecteur flottant : garde la main sur la lecture une fois le panneau fermé. */
function MiniLecteur() {
  const etat = useEtatLecture();
  if (etat === "arret") return null;
  return createPortal(
    <div className="a11y-mini-lecteur" role="region" aria-label="Lecture à voix haute en cours">
      <Volume2 size={16} aria-hidden="true" />
      <span className="a11y-mini-texte">{etat === "chargement" ? "Préparation…" : etat === "pause" ? "En pause" : "Lecture…"}</span>
      {etat === "pause" ? (
        <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={reprendreLecture} aria-label="Reprendre la lecture">
          <Play size={16} />
        </button>
      ) : (
        <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={mettreEnPause} aria-label="Mettre la lecture en pause">
          <Pause size={16} />
        </button>
      )}
      <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={arreterLecture} aria-label="Arrêter la lecture">
        <Square size={16} />
      </button>
    </div>,
    document.body,
  );
}

/* Un seul panneau pour toute l'application, quel que soit le nombre de boutons affichés
   (barre latérale, en-tête mobile, bouton flottant). */
let panneauOuvert = false;
const abonnesPanneau = new Set<() => void>();
function ouvrirPanneau(ouvert: boolean) {
  panneauOuvert = ouvert;
  abonnesPanneau.forEach((notifier) => notifier());
}

/** Ouvre le panneau depuis un autre menu (ex. menu « Plus » sur téléphone). */
export function ouvrirPanneauAccessibilite() {
  ouvrirPanneau(true);
}

/** Monté une seule fois (AppLayout) : panneau, mini-lecteur et raccourcis clavier. */
export function AccessibiliteHote() {
  const ouvert = useSyncExternalStore(
    (notifier) => {
      abonnesPanneau.add(notifier);
      return () => abonnesPanneau.delete(notifier);
    },
    () => panneauOuvert,
  );

  useEffect(() => {
    const clavier = (e: KeyboardEvent) => {
      if (!e.altKey || e.ctrlKey || e.metaKey) return;
      const touche = e.key.toLowerCase();
      if (touche === "a") {
        e.preventDefault();
        ouvrirPanneau(true);
      } else if (touche === "l") {
        e.preventDefault();
        void ecouterLaPage();
      }
    };
    document.addEventListener("keydown", clavier);
    return () => document.removeEventListener("keydown", clavier);
  }, []);

  return (
    <>
      <PanneauAccessibilite ouvert={ouvert} onFermer={() => ouvrirPanneau(false)} />
      <MiniLecteur />
    </>
  );
}

/** Bouton qui ouvre le panneau : "flottant" (pages publiques) ou "icone" (en-têtes). */
export function BoutonAccessibilite({ variante = "icone" }: { variante?: "flottant" | "icone" }) {
  return (
    <button
      type="button"
      onClick={() => ouvrirPanneau(true)}
      className={variante === "flottant" ? "a11y-bouton-flottant" : "btn btn-ghost btn-icon btn-sm"}
      aria-label="Accessibilité : écouter, agrandir le texte, contraste (Alt + A)"
      title="Accessibilité (Alt + A)"
      aria-haspopup="dialog"
    >
      <Accessibility size={variante === "flottant" ? 22 : 16} />
    </button>
  );
}
