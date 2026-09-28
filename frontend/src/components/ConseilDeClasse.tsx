import { useEffect, useState } from "react";
import { FileDown, Gavel } from "lucide-react";
import { messageErreur, codeErreur } from "../api/client";
import { obtenirBulletin, periodesDeLaClasse, telechargerBulletinPdf, validerPassage, type PeriodeOut } from "../api/evaluations";
import type { BulletinOut, EleveClasseOut } from "../types/api";
import { libelle } from "../utils/libelles";
import { ouvrirBlobPdf } from "../utils/telechargerBlob";
import { useConfirmation } from "./Modale";
import { Badge, Btn, ErrorBanner, Select, Skeleton, SuccessBanner } from "./ui";

/* Conseil de classe (professeur principal) : moyenne de chaque élève pour la période,
   décision de passage (fige le bulletin ; « admis » délivre automatiquement le certificat
   de réussite demandé par l'élève) et bulletin PDF. La décision reste humaine (Art. 401). */

export const DECISIONS = ["admis", "admis_annee_validee", "redouble", "reoriente"] as const;

type Ligne = { bulletin: BulletinOut | null; chargement: boolean };

export function ConseilDeClasse({ classeId, eleves }: { classeId: string; eleves: EleveClasseOut[] }) {
  const demanderConfirmation = useConfirmation();
  const [periodes, setPeriodes] = useState<PeriodeOut[]>([]);
  const [periode, setPeriode] = useState<string>("");
  const [lignes, setLignes] = useState<Record<string, Ligne>>({});
  const [choix, setChoix] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [succes, setSucces] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);
  const comptes = eleves.filter((e) => e.utilisateur_id);

  useEffect(() => {
    periodesDeLaClasse(classeId)
      .then((res) => {
        setPeriodes(res.data);
        setPeriode((res.data.find((p) => p.courante) ?? res.data[0])?.code ?? "");
      })
      .catch((err) => setErreur(messageErreur(err)));
  }, [classeId]);

  useEffect(() => {
    if (!periode) return;
    setLignes(Object.fromEntries(comptes.map((e) => [e.utilisateur_id!, { bulletin: null, chargement: true }])));
    comptes.forEach((e) => {
      obtenirBulletin(e.utilisateur_id!, classeId, periode)
        .then((res) => setLignes((l) => ({ ...l, [e.utilisateur_id!]: { bulletin: res.data, chargement: false } })))
        .catch((err) => {
          if (codeErreur(err) !== "aucun_devoir_evalue") setErreur(messageErreur(err));
          setLignes((l) => ({ ...l, [e.utilisateur_id!]: { bulletin: null, chargement: false } }));
        });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classeId, periode]);

  const enregistrer = async (eleve: EleveClasseOut, bulletin: BulletinOut) => {
    const decision = choix[eleve.utilisateur_id!];
    if (!decision) return;
    const ok = await demanderConfirmation({
      titre: `${libelle(decision)} : ${eleve.prenom} ${eleve.nom} ?`,
      message: "La décision est définitive : le bulletin de la période est figé et la famille la voit immédiatement."
        + (decision.startsWith("admis") ? " Si l'élève a demandé un certificat de réussite, il lui est délivré automatiquement." : ""),
      action: "Enregistrer la décision",
    });
    if (!ok) return;
    setEnCours(eleve.utilisateur_id);
    setErreur(null);
    try {
      const res = await validerPassage(bulletin.id, decision);
      setLignes((l) => ({ ...l, [eleve.utilisateur_id!]: { bulletin: res.data, chargement: false } }));
      setSucces(`Décision enregistrée pour ${eleve.prenom} ${eleve.nom}.`);
    } catch (err) {
      setErreur(messageErreur(err));
    } finally {
      setEnCours(null);
    }
  };

  const pdf = async (eleve: EleveClasseOut) => {
    setEnCours(`pdf-${eleve.utilisateur_id}`);
    try {
      const res = await telechargerBulletinPdf(eleve.utilisateur_id!, classeId, periode);
      ouvrirBlobPdf(res.data, `bulletin-${periode}-${eleve.matricule ?? eleve.nom}.pdf`);
    } catch (err) {
      setErreur(messageErreur(err, "Impossible de générer ce bulletin."));
    } finally {
      setEnCours(null);
    }
  };

  return (
    <section aria-label="Conseil de classe" style={{ marginBottom: "16px", padding: "14px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
      <div className="flex flex-wrap items-center justify-between gap-3" style={{ marginBottom: "10px" }}>
        <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px", fontSize: "var(--text-lg)" }}>
          <Gavel size={18} aria-hidden="true" /> Conseil de classe
        </h3>
        <Select aria-label="Période" value={periode} onChange={(e) => setPeriode(e.target.value)} style={{ maxWidth: "200px" }}>
          {periodes.map((p) => <option key={p.code} value={p.code}>{p.libelle}</option>)}
        </Select>
      </div>
      <ErrorBanner>{erreur}</ErrorBanner>
      <SuccessBanner>{succes}</SuccessBanner>
      {comptes.length === 0 && <p className="text-sm" style={{ color: "var(--ink-soft)" }}>Aucun élève avec un compte actif dans cette classe.</p>}
      <div style={{ display: "flex", flexDirection: "column" }}>
        {comptes.map((eleve) => {
          const ligne = lignes[eleve.utilisateur_id!];
          const bulletin = ligne?.bulletin;
          return (
            <div key={eleve.eleve_id} className="flex flex-wrap items-center gap-3" style={{ padding: "10px 0", borderTop: "1px solid var(--border)" }}>
              <span style={{ flex: "1 1 180px", minWidth: 0, fontWeight: 600 }}>{eleve.prenom} {eleve.nom}</span>
              <span style={{ flex: "0 0 110px" }} className="text-sm">
                {!ligne || ligne.chargement ? <Skeleton height="14px" width="70px" /> : bulletin ? `${bulletin.moyenne_generale.toFixed(1)} / 100` : <span style={{ color: "var(--ink-faint)" }}>pas de note</span>}
              </span>
              {bulletin?.valide_par_conseil ? (
                <Badge tone={bulletin.decision_passage?.startsWith("admis") ? "success" : "pending"}>{libelle(bulletin.decision_passage)}</Badge>
              ) : bulletin ? (
                <span className="flex flex-wrap items-center gap-2">
                  <Select aria-label={`Décision pour ${eleve.prenom} ${eleve.nom}`} value={choix[eleve.utilisateur_id!] ?? ""}
                    onChange={(e) => setChoix((c) => ({ ...c, [eleve.utilisateur_id!]: e.target.value }))} style={{ maxWidth: "220px" }}>
                    <option value="">Décision…</option>
                    {DECISIONS.map((d) => <option key={d} value={d}>{libelle(d)}</option>)}
                  </Select>
                  <Btn size="sm" disabled={!choix[eleve.utilisateur_id!]} loading={enCours === eleve.utilisateur_id} onClick={() => enregistrer(eleve, bulletin)}>
                    Enregistrer
                  </Btn>
                </span>
              ) : null}
              {bulletin && (
                <Btn size="sm" variant="ghost" leftIcon={<FileDown size={14} />} loading={enCours === `pdf-${eleve.utilisateur_id}`} onClick={() => pdf(eleve)}
                  aria-label={`Bulletin PDF de ${eleve.prenom} ${eleve.nom}`}>
                  PDF
                </Btn>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
