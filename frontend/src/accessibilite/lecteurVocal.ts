import { useSyncExternalStore } from "react";
import { syntheseVocaleServeur } from "../api/accessibilite";
import { getAccessToken } from "../api/client";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.2 — lecture à voix haute, partagée par toute l'application (barre
   d'accessibilité, mode Écoute, cours). Une seule lecture à la fois.

   1. Voix du navigateur (speechSynthesis) : gratuite, instantanée, sans réseau.
   2. Repli serveur (FreeLLM) si aucune voix française n'est installée — fréquent sur
      les Android d'entrée de gamme — et seulement pour un utilisateur connecté.
   ═══════════════════════════════════════════════════════════════ */

export type EtatLecture = "arret" | "chargement" | "lecture" | "pause";

let etat: EtatLecture = "arret";
const abonnes = new Set<() => void>();
let audioCourant: HTMLAudioElement | null = null;
// Incrémenté à chaque nouvelle lecture ou arrêt : une lecture périmée s'interrompt seule.
let generation = 0;

function changerEtat(suivant: EtatLecture) {
  etat = suivant;
  abonnes.forEach((notifier) => notifier());
}

export function useEtatLecture(): EtatLecture {
  return useSyncExternalStore(
    (notifier) => {
      abonnes.add(notifier);
      return () => abonnes.delete(notifier);
    },
    () => etat,
  );
}

function synthese(): SpeechSynthesis | null {
  return typeof window !== "undefined" && "speechSynthesis" in window ? window.speechSynthesis : null;
}

/** Les voix se chargent en différé sur Chrome : attend au plus une seconde. */
function voixFrancaise(): Promise<SpeechSynthesisVoice | null> {
  const synth = synthese();
  if (!synth) return Promise.resolve(null);
  const choisir = () => {
    const voix = synth.getVoices().filter((v) => v.lang.toLowerCase().startsWith("fr"));
    return voix.find((v) => v.localService) ?? voix[0] ?? null;
  };
  const immediate = choisir();
  if (immediate || synth.getVoices().length > 0) return Promise.resolve(immediate);
  return new Promise((resoudre) => {
    const fin = () => {
      synth.removeEventListener("voiceschanged", fin);
      resoudre(choisir());
    };
    synth.addEventListener("voiceschanged", fin);
    window.setTimeout(fin, 1000);
  });
}

/** Découpe en phrases de taille raisonnable : Chrome coupe une lecture unique trop longue. */
export function decouperEnPhrases(texte: string, maximum = 220): string[] {
  const propre = texte.replace(/[ \t]+/g, " ").replace(/\n{2,}/g, "\n").trim();
  const phrases = propre.split(/(?<=[.!?;:])\s+|\n+/).map((p) => p.trim()).filter(Boolean);
  const morceaux: string[] = [];
  for (const phrase of phrases) {
    if (phrase.length <= maximum) {
      morceaux.push(phrase);
      continue;
    }
    let courant = "";
    for (const mot of phrase.split(" ")) {
      if ((courant + " " + mot).trim().length > maximum && courant) {
        morceaux.push(courant);
        courant = mot;
      } else {
        courant = (courant + " " + mot).trim();
      }
    }
    if (courant) morceaux.push(courant);
  }
  return morceaux;
}

/** Regroupe les phrases en blocs pour limiter le nombre d'appels au serveur. */
function regrouper(phrases: string[], maximum: number): string[] {
  const blocs: string[] = [];
  let courant = "";
  for (const phrase of phrases) {
    if (courant && courant.length + phrase.length + 1 > maximum) {
      blocs.push(courant);
      courant = phrase;
    } else {
      courant = courant ? `${courant} ${phrase}` : phrase;
    }
  }
  if (courant) blocs.push(courant);
  return blocs;
}

export function arreterLecture() {
  generation += 1;
  synthese()?.cancel();
  if (audioCourant) {
    audioCourant.pause();
    URL.revokeObjectURL(audioCourant.src);
    audioCourant = null;
  }
  changerEtat("arret");
}

export function mettreEnPause() {
  if (etat !== "lecture") return;
  if (audioCourant) audioCourant.pause();
  else synthese()?.pause();
  changerEtat("pause");
}

export function reprendreLecture() {
  if (etat !== "pause") return;
  if (audioCourant) void audioCourant.play();
  else synthese()?.resume();
  changerEtat("lecture");
}

function jouer(blob: Blob, maGeneration: number): Promise<void> {
  return new Promise((resoudre) => {
    if (maGeneration !== generation) return resoudre();
    const audio = new Audio(URL.createObjectURL(blob));
    audioCourant = audio;
    const terminer = () => {
      URL.revokeObjectURL(audio.src);
      if (audioCourant === audio) audioCourant = null;
      resoudre();
    };
    audio.onended = terminer;
    audio.onerror = terminer;
    changerEtat("lecture");
    audio.play().catch(terminer);
  });
}

async function lireParLeServeur(phrases: string[], maGeneration: number) {
  const blocs = regrouper(phrases, 1500);
  // Le bloc suivant se télécharge pendant que le précédent est lu.
  let suivant = syntheseVocaleServeur(blocs[0]);
  for (let i = 0; i < blocs.length; i += 1) {
    const blob = await suivant;
    if (i + 1 < blocs.length) suivant = syntheseVocaleServeur(blocs[i + 1]);
    await jouer(blob, maGeneration);
    if (maGeneration !== generation) return;
  }
}

export class AucuneVoixDisponible extends Error {}

/**
 * Lit un texte à voix haute. Rejette `AucuneVoixDisponible` si le navigateur n'a pas de
 * voix française et que la personne n'est pas connectée (pas de repli serveur possible).
 */
export async function lireTexte(texte: string): Promise<void> {
  arreterLecture();
  const maGeneration = generation;
  const phrases = decouperEnPhrases(texte);
  if (phrases.length === 0) return;
  changerEtat("chargement");
  const synth = synthese();
  const voix = await voixFrancaise();
  if (maGeneration !== generation) return;

  if (synth && voix) {
    phrases.forEach((phrase, index) => {
      const enonce = new SpeechSynthesisUtterance(phrase);
      enonce.voice = voix;
      enonce.lang = voix.lang;
      enonce.rate = 0.95;
      if (index === 0) enonce.onstart = () => maGeneration === generation && changerEtat("lecture");
      if (index === phrases.length - 1) {
        enonce.onend = () => maGeneration === generation && changerEtat("arret");
      }
      enonce.onerror = () => maGeneration === generation && changerEtat("arret");
      synth.speak(enonce);
    });
    return;
  }

  if (!getAccessToken()) {
    changerEtat("arret");
    throw new AucuneVoixDisponible("Aucune voix française sur cet appareil.");
  }
  try {
    await lireParLeServeur(phrases, maGeneration);
  } finally {
    if (maGeneration === generation) changerEtat("arret");
  }
}

/** Texte à lire pour « Écouter cette page » : la sélection si elle existe, sinon le contenu principal. */
export function texteDeLaPage(): string {
  const selection = window.getSelection()?.toString().trim() ?? "";
  if (selection.length > 3) return selection;
  const principal = document.getElementById("main-content");
  return principal?.innerText ?? "";
}
