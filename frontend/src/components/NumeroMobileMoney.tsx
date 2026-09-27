import { useState } from "react";
import { mettreAJourTelephone } from "../api/auth";
import { messageErreur } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, ErrorBanner, Field, TextInput } from "./ui";
import { Smartphone } from "lucide-react";

/** Numero sur lequel l'administration reverse les gains (micro-jobs, ventes marketplace). */
export function NumeroMobileMoney({ contexte }: { contexte: string }) {
  const { utilisateur, rafraichirUtilisateur } = useAuth();
  const [edition, setEdition] = useState(false);
  const [valeur, setValeur] = useState(utilisateur?.telephone ?? "");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  if (!utilisateur) return null;
  const manquant = !utilisateur.telephone;

  const enregistrer = async () => {
    setErreur(null);
    setEnCours(true);
    try {
      await mettreAJourTelephone(valeur.trim());
      await rafraichirUtilisateur();
      setEdition(false);
    } catch (err) {
      setErreur(messageErreur(err, "Numéro invalide."));
    } finally {
      setEnCours(false);
    }
  };

  if (!manquant && !edition) {
    return (
      <p style={{ margin: "0 0 16px", fontSize: "var(--text-sm)", color: "var(--ink-soft)", display: "flex", gap: 8, alignItems: "center" }}>
        <Smartphone size={14} aria-hidden /> Numéro Mobile Money : <strong>{utilisateur.telephone}</strong>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setEdition(true)}>Modifier</button>
      </p>
    );
  }

  return (
    <Card className="mb-4" style={manquant ? { border: "1px solid var(--reward-deep)" } : undefined}>
      <p style={{ margin: "0 0 12px", fontSize: "var(--text-sm)" }}>
        {manquant
          ? `Renseignez votre numéro Mobile Money : sans lui, l'administration ne peut pas vous reverser ${contexte}.`
          : "Modifier votre numéro Mobile Money."}
      </p>
      <div style={{ display: "flex", gap: 8, alignItems: "flex-end", flexWrap: "wrap" }}>
        <Field label="Numéro Mobile Money">
          <TextInput value={valeur} onChange={(e) => setValeur(e.target.value)} inputMode="tel" placeholder="+229 01 97 00 00 00" maxLength={30} />
        </Field>
        <Btn variant="primary" size="sm" loading={enCours} onClick={enregistrer}>Enregistrer</Btn>
        {!manquant && <Btn variant="ghost" size="sm" onClick={() => setEdition(false)}>Annuler</Btn>}
      </div>
      {erreur && <ErrorBanner>{erreur}</ErrorBanner>}
    </Card>
  );
}
