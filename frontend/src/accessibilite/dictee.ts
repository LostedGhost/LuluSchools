import { useEffect, useMemo, useRef, useState } from "react";

/* Dictée vocale partagée (Lot 7) : API Web Speech du navigateur — FreeLLM ne transcrit
   pas l'audio (vérifié dans son code source : seule /v1/audio/speech existe). Même
   mécanique que la dictée d'El Professor. */

interface ReconnaissanceVocale {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
}
type ConstructeurReconnaissance = new () => ReconnaissanceVocale;

function constructeurReconnaissance(): ConstructeurReconnaissance | null {
  const w = window as unknown as {
    SpeechRecognition?: ConstructeurReconnaissance;
    webkitSpeechRecognition?: ConstructeurReconnaissance;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/**
 * Dicte du texte à la suite de `valeur` : `onChange` reçoit le texte complet à chaque
 * phrase reconnue. `disponible` est faux sur les navigateurs sans reconnaissance vocale.
 */
export function useDictee(valeur: string, onChange: (texte: string) => void) {
  const [active, setActive] = useState(false);
  const reconnaissanceRef = useRef<ReconnaissanceVocale | null>(null);
  const disponible = useMemo(() => constructeurReconnaissance() !== null, []);

  useEffect(() => () => reconnaissanceRef.current?.stop(), []);

  const basculer = () => {
    if (active) {
      reconnaissanceRef.current?.stop();
      return;
    }
    const Constructeur = constructeurReconnaissance();
    if (!Constructeur) return;
    const reconnaissance = new Constructeur();
    reconnaissance.lang = "fr-FR";
    reconnaissance.interimResults = false;
    reconnaissance.continuous = true;
    const base = valeur.trim();
    let dicte = "";
    reconnaissance.onresult = (evenement) => {
      for (let i = evenement.resultIndex; i < evenement.results.length; i++) {
        if (evenement.results[i].isFinal) dicte += `${evenement.results[i][0].transcript} `;
      }
      onChange(`${base}${base ? " " : ""}${dicte.trim()}`);
    };
    reconnaissance.onend = () => setActive(false);
    reconnaissance.onerror = () => setActive(false);
    reconnaissanceRef.current = reconnaissance;
    reconnaissance.start();
    setActive(true);
  };

  return { disponible, active, basculer };
}
