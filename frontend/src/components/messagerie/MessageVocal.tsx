import { useEffect, useRef, useState } from "react";
import { Mic, Pause, Play, Square } from "lucide-react";
import { api, messageErreur } from "../../api/client";

/* ═══════════════════════════════════════════════════════════════
   Lot 7.4 — messages vocaux : parler au lieu d'écrire (parents non alphabétisés).
   Enregistrement léger (Opus ~24 kbit/s, 2 min au plus ≈ 360 Ko sur un forfait mobile).
   ═══════════════════════════════════════════════════════════════ */

const DUREE_MAX_S = 120;

function typeAudioSupporte(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm", "audio/mp4"].find((t) =>
    MediaRecorder.isTypeSupported(t),
  );
}

function formaterDuree(secondes: number): string {
  return `${Math.floor(secondes / 60)}:${String(secondes % 60).padStart(2, "0")}`;
}

export function BoutonMessageVocal({
  onEnregistre,
  desactive,
}: {
  onEnregistre: (audio: Blob, dureeSecondes: number) => void;
  desactive?: boolean;
}) {
  const [enregistrement, setEnregistrement] = useState(false);
  const [secondes, setSecondes] = useState(0);
  const [erreur, setErreur] = useState<string | null>(null);
  const enregistreur = useRef<MediaRecorder | null>(null);
  const minuterie = useRef<number | undefined>(undefined);
  const typeAudio = typeAudioSupporte();

  useEffect(
    () => () => {
      window.clearInterval(minuterie.current);
      enregistreur.current?.stream.getTracks().forEach((piste) => piste.stop());
    },
    [],
  );

  if (!typeAudio || !navigator.mediaDevices?.getUserMedia) return null;

  const arreter = () => enregistreur.current?.state === "recording" && enregistreur.current.stop();

  const demarrer = async () => {
    setErreur(null);
    try {
      const flux = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(flux, { mimeType: typeAudio, audioBitsPerSecond: 24000 });
      const morceaux: Blob[] = [];
      const debut = Date.now();
      recorder.ondataavailable = (e) => e.data.size > 0 && morceaux.push(e.data);
      recorder.onstop = () => {
        window.clearInterval(minuterie.current);
        flux.getTracks().forEach((piste) => piste.stop());
        setEnregistrement(false);
        const duree = Math.max(1, Math.min(DUREE_MAX_S, Math.round((Date.now() - debut) / 1000)));
        if (morceaux.length) onEnregistre(new Blob(morceaux, { type: typeAudio.split(";")[0] }), duree);
      };
      enregistreur.current = recorder;
      recorder.start();
      setSecondes(0);
      setEnregistrement(true);
      minuterie.current = window.setInterval(() => {
        setSecondes((s) => {
          if (s + 1 >= DUREE_MAX_S) recorder.stop();
          return s + 1;
        });
      }, 1000);
    } catch {
      setErreur("Micro inaccessible : autorisez le micro dans votre navigateur.");
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
      {enregistrement ? (
        <button type="button" className="btn btn-action" onClick={arreter} aria-label="Arrêter et envoyer le message vocal" style={{ minHeight: "44px", gap: "6px" }}>
          <Square size={16} aria-hidden="true" />
          <span aria-live="polite">{formaterDuree(secondes)}</span>
        </button>
      ) : (
        <button
          type="button"
          className="btn btn-ghost"
          onClick={demarrer}
          disabled={desactive}
          aria-label="Enregistrer un message vocal"
          title="Message vocal"
          style={{ minHeight: "44px" }}
        >
          <Mic size={18} aria-hidden="true" />
        </button>
      )}
      {erreur && <span role="alert" style={{ fontSize: "var(--text-xs)", color: "var(--action-deep)" }}>{erreur}</span>}
    </div>
  );
}

/** Lecture d'un message vocal : le lien signé n'est demandé qu'au premier appui. */
export function LecteurMessageVocal({ messageId, duree }: { messageId: string; duree: number | null }) {
  const [audio, setAudio] = useState<HTMLAudioElement | null>(null);
  const [lecture, setLecture] = useState(false);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => () => audio?.pause(), [audio]);

  const basculer = async () => {
    if (audio) {
      if (lecture) audio.pause();
      else void audio.play();
      return;
    }
    setChargement(true);
    try {
      const { data } = await api.get<{ url: string }>(`/messages/${messageId}/audio`);
      const element = new Audio(data.url);
      element.onplay = () => setLecture(true);
      element.onpause = () => setLecture(false);
      element.onended = () => setLecture(false);
      setAudio(element);
      await element.play();
    } catch (err) {
      setErreur(messageErreur(err, "Message vocal indisponible."));
    } finally {
      setChargement(false);
    }
  };

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
      <button
        type="button"
        onClick={basculer}
        disabled={chargement}
        className="btn btn-sm"
        style={{ background: "var(--surface)", color: "var(--ink)", minHeight: "40px" }}
        aria-label={lecture ? "Mettre en pause le message vocal" : "Écouter le message vocal"}
      >
        {lecture ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
      </button>
      <span>Message vocal{duree ? ` · ${formaterDuree(duree)}` : ""}</span>
      {erreur && <span role="alert" style={{ fontSize: "var(--text-xs)" }}>{erreur}</span>}
    </span>
  );
}
