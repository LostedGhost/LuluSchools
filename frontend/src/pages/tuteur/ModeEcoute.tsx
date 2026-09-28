import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpenCheck,
  CalendarCheck,
  ChevronRight,
  GraduationCap,
  HandHelping,
  Handshake,
  LayoutGrid,
  MessageCircle,
  NotebookPen,
  UserPlus,
  Volume2,
  Wallet,
} from "lucide-react";
import { obtenirEcouteTuteur, type EcouteTuteurOut, type TuileEcoute } from "../../api/ecoute";
import { donnerConsentementParental } from "../../api/inscriptions";
import { messageErreur } from "../../api/client";
import { ErrorBanner, Skeleton } from "../../components/ui";
import { lireTexte } from "../../accessibilite/lecteurVocal";
import { useAccessibilite } from "../../accessibilite/AccessibiliteContext";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.4 — mode Écoute : l'accueil du parent pour qui lire est difficile.
   Une grande image par sujet ; la toucher la fait parler (phrase préparée par le
   serveur, sans IA). Le petit bouton flèche ouvre l'écran détaillé.
   ═══════════════════════════════════════════════════════════════ */

const PICTOGRAMMES: Record<string, ReactNode> = {
  bulletin: <GraduationCap size={40} aria-hidden="true" />,
  presences: <CalendarCheck size={40} aria-hidden="true" />,
  devoirs: <NotebookPen size={40} aria-hidden="true" />,
  paiements: <Wallet size={40} aria-hidden="true" />,
  accord: <Handshake size={40} aria-hidden="true" />,
  messages: <MessageCircle size={40} aria-hidden="true" />,
  inscrire: <UserPlus size={40} aria-hidden="true" />,
  aide: <HandHelping size={40} aria-hidden="true" />,
  apprendre: <BookOpenCheck size={40} aria-hidden="true" />,
};

const AIDE =
  "Chaque grande image parle quand vous la touchez. L'image du chapeau, c'est le bulletin. Le calendrier, ce sont les présences. " +
  "Le cahier, ce sont les devoirs. Le porte-monnaie, ce sont les dépenses. Un point rouge veut dire que quelque chose vous attend. " +
  "La petite flèche ouvre la page détaillée. La bulle sert à envoyer un message vocal au professeur.";

interface IndexAudio {
  langues: Record<string, { nom: string; cles: string[] }>;
}

let indexAudio: Promise<IndexAudio | null> | null = null;
function chargerIndexAudio(): Promise<IndexAudio | null> {
  indexAudio ??= fetch("/audio/ecoute/index.json")
    .then((r) => (r.ok ? (r.json() as Promise<IndexAudio>) : null))
    .catch(() => null);
  return indexAudio;
}

/** Joue le libellé enregistré dans la langue choisie s'il existe, puis la phrase en français. */
async function parler(cle: string, phrase: string, langue: string) {
  const index = await chargerIndexAudio();
  if (langue !== "fr" && index?.langues[langue]?.cles.includes(cle)) {
    await new Promise<void>((fin) => {
      const audio = new Audio(`/audio/ecoute/${langue}/${cle}.mp3`);
      audio.onended = () => fin();
      audio.onerror = () => fin();
      audio.play().catch(() => fin());
    });
  }
  await lireTexte(phrase).catch(() => {});
}

function Tuile({
  cle,
  titre,
  alerte,
  onParler,
  onOuvrir,
  action,
}: {
  cle: string;
  titre: string;
  alerte?: boolean;
  onParler: () => void;
  onOuvrir?: () => void;
  action?: ReactNode;
}) {
  return (
    <div className={`ecoute-tuile ${alerte ? "ecoute-tuile-alerte" : ""}`}>
      <button type="button" className="ecoute-tuile-principal" onClick={onParler} aria-label={`${titre} : écouter`}>
        {alerte && <span className="ecoute-point" aria-hidden="true" />}
        {PICTOGRAMMES[cle] ?? <Volume2 size={40} aria-hidden="true" />}
        <span className="ecoute-tuile-titre">{titre}</span>
        <Volume2 size={18} aria-hidden="true" className="ecoute-haut-parleur" />
      </button>
      {action}
      {onOuvrir && (
        <button type="button" className="ecoute-ouvrir" onClick={onOuvrir} aria-label={`Ouvrir : ${titre}`}>
          <ChevronRight size={22} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export function ModeEcoute() {
  const navigate = useNavigate();
  const { preferences, modifier } = useAccessibilite();
  const [donnees, setDonnees] = useState<EcouteTuteurOut | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [accordEnCours, setAccordEnCours] = useState<string | null>(null);

  const charger = () => {
    obtenirEcouteTuteur()
      .then((res) => setDonnees(res.data))
      .catch((err) => setErreur(messageErreur(err)));
  };
  useEffect(charger, []);

  const dire = (cle: string, phrase: string) => void parler(cle, phrase, preferences.langue_audio);

  const donnerAccord = async (tuile: TuileEcoute) => {
    if (!tuile.consentement_inscription_id) return;
    setAccordEnCours(tuile.consentement_inscription_id);
    try {
      await donnerConsentementParental(tuile.consentement_inscription_id);
      await lireTexte("Merci. Votre accord est enregistré.").catch(() => {});
      charger();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setAccordEnCours(null);
    }
  };

  if (!donnees) {
    return (
      <div className="page-content">
        <ErrorBanner>{erreur}</ErrorBanner>
        {!erreur && <Skeleton height="220px" />}
      </div>
    );
  }

  return (
    <div className="page-content ecoute">
      <ErrorBanner>{erreur}</ErrorBanner>
      <button type="button" className="ecoute-accueil" onClick={() => dire("accueil", donnees.accueil)}>
        <Volume2 size={36} aria-hidden="true" />
        <span>{donnees.accueil}</span>
      </button>

      {donnees.enfants.map((enfant) => (
        <section key={enfant.eleve_utilisateur_id ?? enfant.prenom} aria-label={enfant.prenom} className="ecoute-enfant">
          <h2 className="ecoute-prenom">{enfant.prenom}</h2>
          <div className="ecoute-grille">
            {enfant.tuiles.map((t) => (
              <Tuile
                key={t.cle}
                cle={t.cle}
                titre={t.titre}
                alerte={t.alerte}
                onParler={() => dire(t.cle, t.phrase)}
                onOuvrir={t.consentement_inscription_id ? undefined : () => navigate(t.lien)}
                action={
                  t.consentement_inscription_id ? (
                    <button
                      type="button"
                      className="ecoute-accord"
                      disabled={accordEnCours === t.consentement_inscription_id}
                      onClick={() => donnerAccord(t)}
                    >
                      <Handshake size={22} aria-hidden="true" /> Donner mon accord
                    </button>
                  ) : undefined
                }
              />
            ))}
          </div>
        </section>
      ))}

      <section aria-label="Autres actions" className="ecoute-enfant">
        <div className="ecoute-grille">
          <Tuile
            cle="messages"
            titre="Messages"
            onParler={() => dire("messages", "Touchez la flèche pour parler au professeur avec un message vocal.")}
            onOuvrir={() => navigate("/messagerie")}
          />
          <Tuile
            cle="inscrire"
            titre="Inscrire"
            onParler={() => dire("inscrire", "Touchez la flèche pour inscrire un enfant dans une école.")}
            onOuvrir={() => navigate("/tuteur/nouvelle-inscription")}
          />
          <Tuile
            cle="apprendre"
            titre="Apprendre à lire"
            onParler={() => dire("apprendre", "Touchez la flèche pour apprendre à lire, à écrire et à compter, avec des leçons à écouter.")}
            onOuvrir={() => navigate("/tuteur/alphabetisation")}
          />
          <Tuile cle="aide" titre="Aide" onParler={() => dire("aide", AIDE)} />
        </div>
      </section>

      <button type="button" className="btn btn-ghost" onClick={() => modifier({ mode_ecoute: false })} style={{ gap: "8px" }}>
        <LayoutGrid size={16} aria-hidden="true" /> Voir l'écran complet
      </button>
    </div>
  );
}
