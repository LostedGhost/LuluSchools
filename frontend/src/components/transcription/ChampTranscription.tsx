import { Mic, MicOff } from "lucide-react";
import { Field, TextArea } from "../ui";
import { useDictee } from "../../accessibilite/dictee";

/**
 * Lot 7.3 — saisie de la transcription d'un cours audio/vidéo : texte libre, collé ou
 * dicté (reconnaissance vocale du navigateur, pratique en réécoutant son propre cours).
 */
export function ChampTranscription({
  valeur,
  onChange,
  requis = true,
}: {
  valeur: string;
  onChange: (texte: string) => void;
  requis?: boolean;
}) {
  const dictee = useDictee(valeur, onChange);
  return (
    <div>
      <Field
        label="Transcription du cours"
        required={requis}
        helper="Ce qui est dit dans l'enregistrement, par écrit : les élèves sourds ou malentendants suivent le cours grâce à elle, et l'IA s'en sert pour les quiz et El Professor."
      >
        <TextArea
          rows={6}
          value={valeur}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Tapez, collez ou dictez ce qui est dit dans l'enregistrement…"
        />
      </Field>
      {dictee.disponible && (
        <button
          type="button"
          className={`btn btn-sm ${dictee.active ? "btn-action" : "btn-ghost"}`}
          onClick={dictee.basculer}
          style={{ marginTop: "8px", gap: "6px" }}
          aria-pressed={dictee.active}
        >
          {dictee.active ? <MicOff size={14} aria-hidden="true" /> : <Mic size={14} aria-hidden="true" />}
          {dictee.active ? "Arrêter la dictée" : "Dicter la transcription"}
        </button>
      )}
    </div>
  );
}

/** Fichier de sous-titres WebVTT facultatif (vidéo uniquement). */
export function ChampSousTitres({ onChange }: { onChange: (fichier: File | null) => void }) {
  return (
    <Field
      label="Sous-titres (facultatif)"
      helper="Fichier .vtt (WebVTT) : les sous-titres s'affichent sous la vidéo, synchronisés avec la voix."
    >
      <input
        type="file"
        accept=".vtt,text/vtt"
        className="field-input"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
    </Field>
  );
}
