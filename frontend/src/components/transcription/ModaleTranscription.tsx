import { useState } from "react";
import { Sparkles } from "lucide-react";
import { Modale } from "../Modale";
import { Btn, ErrorBanner } from "../ui";
import { messageErreur } from "../../api/client";
import { enregistrerTranscription, obtenirSousTitres, proposerMiseEnFormeTranscription } from "../../api/pedagogie";
import type { CoursOut } from "../../types/api";
import { ChampSousTitres, ChampTranscription } from "./ChampTranscription";

/**
 * Lot 7.3 — compléter ou corriger la transcription d'un cours déjà publié. L'IA peut
 * PROPOSER une mise en forme : l'enseignant la relit, puis choisit de l'utiliser.
 */
export function ModaleTranscription({
  cours,
  onFermer,
  onEnregistre,
}: {
  cours: CoursOut;
  onFermer: () => void;
  onEnregistre: (cours: CoursOut) => void;
}) {
  const [texte, setTexte] = useState(cours.transcription ?? "");
  const [fichierVtt, setFichierVtt] = useState<File | null>(null);
  const [proposition, setProposition] = useState<string | null>(null);
  const [miseEnForme, setMiseEnForme] = useState(false);
  const [enregistrement, setEnregistrement] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const video = cours.format === "video";

  const proposer = async () => {
    setMiseEnForme(true);
    setErreur(null);
    try {
      const res = await proposerMiseEnFormeTranscription(cours.id, texte);
      setProposition(res.data.transcription);
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setMiseEnForme(false);
    }
  };

  const enregistrer = async () => {
    if (texte.trim().length < 20) {
      setErreur("La transcription doit contenir au moins quelques phrases.");
      return;
    }
    setEnregistrement(true);
    setErreur(null);
    try {
      // Sans nouveau fichier, les sous-titres déjà enregistrés sont conservés.
      let vtt: string | null = null;
      if (fichierVtt) vtt = await fichierVtt.text();
      else if (video && cours.a_des_sous_titres) vtt = await obtenirSousTitres(cours.id);
      const res = await enregistrerTranscription(cours.id, texte.trim(), vtt);
      onEnregistre(res.data);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible d'enregistrer la transcription."));
    } finally {
      setEnregistrement(false);
    }
  };

  return (
    <Modale
      ouvert
      titre={`Transcription — ${cours.titre}`}
      onFermer={onFermer}
      largeur={680}
      pied={
        <>
          <Btn variant="ghost" onClick={onFermer}>Annuler</Btn>
          <Btn variant="primary" onClick={enregistrer} loading={enregistrement}>Enregistrer</Btn>
        </>
      }
    >
      <ErrorBanner>{erreur}</ErrorBanner>
      <ChampTranscription valeur={texte} onChange={setTexte} />
      <div style={{ marginTop: "12px" }}>
        <Btn
          variant="magic"
          size="sm"
          onClick={proposer}
          loading={miseEnForme}
          disabled={texte.trim().length < 20}
          leftIcon={<Sparkles size={14} aria-hidden="true" />}
        >
          Proposer une mise en forme (IA)
        </Btn>
      </div>
      {proposition && (
        <div style={{ marginTop: "12px", padding: "12px", borderRadius: "var(--radius-md)", background: "var(--magic-tint)" }}>
          <p style={{ fontWeight: 700, margin: "0 0 6px" }}>Proposition de l'IA — à relire avant de l'utiliser</p>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", margin: 0, maxHeight: "240px", overflow: "auto" }}>{proposition}</pre>
          <div style={{ display: "flex", gap: "8px", marginTop: "10px", flexWrap: "wrap" }}>
            <Btn
              size="sm"
              variant="primary"
              onClick={() => {
                setTexte(proposition);
                setProposition(null);
              }}
            >
              Utiliser cette version
            </Btn>
            <Btn size="sm" variant="ghost" onClick={() => setProposition(null)}>Ignorer</Btn>
          </div>
        </div>
      )}
      {video && (
        <div style={{ marginTop: "12px" }}>
          <ChampSousTitres onChange={setFichierVtt} />
          {cours.a_des_sous_titres && !fichierVtt && (
            <p style={{ fontSize: "var(--text-sm)", color: "var(--ink-soft)", margin: "4px 0 0" }}>
              Des sous-titres sont déjà enregistrés ; choisissez un fichier seulement pour les remplacer.
            </p>
          )}
        </div>
      )}
    </Modale>
  );
}
