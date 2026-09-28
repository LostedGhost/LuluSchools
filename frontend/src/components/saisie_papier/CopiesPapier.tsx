import { useState } from "react";
import { Sparkles } from "lucide-react";
import { messageErreur } from "../../api/client";
import { enregistrerCopies, lireCopies, type CopieLue, type EleveCandidat } from "../../api/saisie_papier";
import { useConfirmation } from "../Modale";
import { Badge, Btn, ErrorBanner, Select, SuccessBanner } from "../ui";
import { PrisePhotos } from "./PrisePhotos";

export const TONS_CONFIANCE = { sur: "success", probable: "pending", non_trouve: "error" } as const;
export const LIBELLES_CONFIANCE = { sur: "reconnu", probable: "à vérifier", non_trouve: "non reconnu" } as const;

/** Copies papier d'un devoir (élèves sans smartphone) : une photo par copie, l'IA lit le nom
 * écrit sur chacune et propose l'élève, on confirme, puis l'IA corrige selon le barème. */
export function CopiesPapier({ devoirId, onTermine }: { devoirId: string; onTermine?: () => void }) {
  const demanderConfirmation = useConfirmation();
  const [fichiers, setFichiers] = useState<File[]>([]);
  const [copies, setCopies] = useState<CopieLue[] | null>(null);
  const [eleves, setEleves] = useState<EleveCandidat[]>([]);
  const [choix, setChoix] = useState<Record<string, string>>({});
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);

  const lire = async () => {
    setEnCours(true);
    setErreur(null);
    try {
      const res = (await lireCopies(devoirId, fichiers)).data;
      setCopies(res.copies);
      setEleves(res.eleves);
      setChoix(Object.fromEntries(res.copies.map((c) => [c.document_id, c.eleve_id ?? ""])));
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  };

  const affectations = Object.entries(choix).filter(([, eleveId]) => eleveId).map(([document_id, eleve_id]) => ({ document_id, eleve_id }));
  const doublon = new Set(affectations.map((a) => a.eleve_id)).size !== affectations.length;

  const enregistrer = async () => {
    const ok = await demanderConfirmation({
      titre: `Enregistrer ${affectations.length} copie(s) ?`,
      message: "Chaque copie devient celle de l'élève choisi et est corrigée par l'IA selon le barème du devoir. Les copies sans élève choisi sont ignorées.",
      action: "Enregistrer",
    });
    if (!ok) return;
    setEnCours(true);
    setErreur(null);
    try {
      setSucces((await enregistrerCopies(devoirId, affectations)).data.message);
      setCopies(null);
      setFichiers([]);
      onTermine?.();
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(false);
    }
  };

  const nom = (e: EleveCandidat) => `${e.nom} ${e.prenom}`;

  return (
    <div className="space-y-3">
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>
      {copies === null ? (
        <>
          <PrisePhotos fichiers={fichiers} onChange={setFichiers} max={40}
            aide="Une photo par copie (la page où figure le nom de l'élève). Jusqu'à 40 copies par envoi." />
          <Btn leftIcon={<Sparkles size={16} />} loading={enCours} disabled={fichiers.length === 0} onClick={lire}>
            {enCours ? "L'IA lit les noms sur les copies…" : "Lire les noms sur les copies"}
          </Btn>
        </>
      ) : (
        <>
          <p className="text-sm" style={{ color: "var(--ink-soft)", margin: 0 }}>
            Vérifiez l'élève de chaque copie. Seuls les élèves qui n'ont pas encore de copie pour ce devoir sont proposés.
          </p>
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {copies.map((c, i) => (
              <li key={c.document_id} className="flex flex-wrap items-center gap-3" style={{ padding: "8px 0", borderTop: "1px solid var(--border)" }}>
                <span style={{ flex: "1 1 180px", minWidth: 0 }}>
                  <strong>Copie {i + 1}</strong> <span className="text-sm" style={{ color: "var(--ink-faint)" }}>{c.nom_fichier}</span>
                  <span className="text-sm" style={{ display: "block", color: "var(--ink-soft)" }}>
                    Nom lu : {c.nom_lu ?? "—"} <Badge tone={TONS_CONFIANCE[c.confiance]}>{LIBELLES_CONFIANCE[c.confiance]}</Badge>
                  </span>
                </span>
                <Select aria-label={`Élève de la copie ${i + 1}`} value={choix[c.document_id] ?? ""}
                  onChange={(e) => setChoix((x) => ({ ...x, [c.document_id]: e.target.value }))} style={{ maxWidth: "260px" }}>
                  <option value="">Ignorer cette copie</option>
                  {eleves.map((e) => <option key={e.eleve_id} value={e.eleve_id}>{nom(e)}</option>)}
                </Select>
              </li>
            ))}
          </ul>
          {doublon && <ErrorBanner>Un même élève est choisi pour deux copies.</ErrorBanner>}
          <div className="flex flex-wrap gap-2">
            <Btn loading={enCours} disabled={affectations.length === 0 || doublon} onClick={enregistrer}>
              Enregistrer {affectations.length} copie(s)
            </Btn>
            <Btn variant="ghost" onClick={() => { setCopies(null); setFichiers([]); }}>Recommencer</Btn>
          </div>
        </>
      )}
    </div>
  );
}
