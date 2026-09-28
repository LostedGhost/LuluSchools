import { lazy, Suspense, useEffect, useState } from "react";
import { Captions, Headphones, Play, Video, Volume2 } from "lucide-react";
import { Btn } from "../ui";
import { messageErreur } from "../../api/client";
import { obtenirLienFichierCours, obtenirSousTitres } from "../../api/pedagogie";
import { lireTexte, useEtatLecture, arreterLecture } from "../../accessibilite/lecteurVocal";
import type { CoursOut } from "../../types/api";

const MarkdownIA = lazy(() => import("../el_professor/MarkdownIA"));

/* ═══════════════════════════════════════════════════════════════
   Lot 7.3 — lecture d'un cours audio/vidéo dans la page (et non plus dans un onglet),
   avec sous-titres et transcription ; Lot 7.5 — rien n'est téléchargé tant que l'élève
   n'a pas appuyé sur « Lire » (preload="none"), la transcription suffit hors connexion.
   ═══════════════════════════════════════════════════════════════ */

export function LecteurCours({ cours }: { cours: CoursOut }) {
  const [url, setUrl] = useState<string | null>(null);
  const [pistes, setPistes] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const video = cours.format === "video";

  // Libère l'URL locale des sous-titres en quittant la page.
  useEffect(() => () => {
    if (pistes) URL.revokeObjectURL(pistes);
  }, [pistes]);

  const charger = async () => {
    setChargement(true);
    setErreur(null);
    try {
      const [lien, vtt] = await Promise.all([
        obtenirLienFichierCours(cours.id),
        video && cours.a_des_sous_titres ? obtenirSousTitres(cours.id) : Promise.resolve(null),
      ]);
      if (vtt) setPistes(URL.createObjectURL(new Blob([vtt], { type: "text/vtt" })));
      setUrl(lien.data.url);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de charger l'enregistrement. La transcription reste disponible ci-dessous."));
    } finally {
      setChargement(false);
    }
  };

  const Icone = video ? Video : Headphones;
  return (
    <div>
      {url ? (
        video ? (
          <video
            src={url}
            controls
            autoPlay
            preload="none"
            style={{ width: "100%", borderRadius: "var(--radius-md)", background: "#000" }}
          >
            {pistes && <track kind="captions" src={pistes} srcLang="fr" label="Français" default />}
          </video>
        ) : (
          <audio src={url} controls autoPlay preload="none" style={{ width: "100%" }} />
        )
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
          <div
            style={{
              width: "48px", height: "48px", borderRadius: "var(--radius-md)", background: "var(--primary-tint)",
              color: "var(--primary-deep)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
            aria-hidden="true"
          >
            <Icone size={22} />
          </div>
          <div style={{ flex: 1, minWidth: "160px" }}>
            <p style={{ color: "var(--ink)", fontWeight: 600, margin: 0 }}>{video ? "Vidéo du cours" : "Enregistrement audio"}</p>
            <p style={{ color: "var(--ink-soft)", fontSize: "var(--text-sm)", margin: "2px 0 0" }}>
              {video && cours.a_des_sous_titres ? "Sous-titres disponibles. " : ""}
              Ne se télécharge que si vous appuyez sur « Lire ».
            </p>
          </div>
          <Btn variant="primary" onClick={charger} loading={chargement} leftIcon={<Play size={16} aria-hidden="true" />}>
            Lire {video ? "la vidéo" : "l'audio"}
          </Btn>
        </div>
      )}
      {erreur && <p role="alert" style={{ color: "var(--action-deep)", fontSize: "var(--text-sm)", marginTop: "8px" }}>{erreur}</p>}
    </div>
  );
}

/** Transcription lisible et écoutable (voix de synthèse), pour tous. */
export function TranscriptionCours({ texte, titre = "Transcription" }: { texte: string; titre?: string }) {
  const etat = useEtatLecture();
  return (
    <section aria-labelledby="titre-transcription" style={{ marginTop: "var(--space-5)" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
        <h3 id="titre-transcription" style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "var(--text-lg)", margin: 0 }}>
          <Captions size={18} aria-hidden="true" /> {titre}
        </h3>
        {etat === "arret" ? (
          <Btn variant="ghost" size="sm" onClick={() => void lireTexte(texte).catch(() => {})} leftIcon={<Volume2 size={14} aria-hidden="true" />}>
            Écouter
          </Btn>
        ) : (
          <Btn variant="ghost" size="sm" onClick={arreterLecture}>
            Arrêter la lecture
          </Btn>
        )}
      </div>
      <div style={{ color: "var(--ink)", lineHeight: 1.7 }}>
        <Suspense fallback={<p style={{ whiteSpace: "pre-wrap" }}>{texte}</p>}>
          <MarkdownIA texte={texte} />
        </Suspense>
      </div>
    </section>
  );
}
