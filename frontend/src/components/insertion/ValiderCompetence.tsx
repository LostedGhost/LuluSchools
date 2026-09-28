import { useState } from "react";
import { messageErreur } from "../../api/client";
import { validerCompetenceMetier, type CompetenceMetier } from "../../api/insertion";
import { Btn, Field, Select, TextInput } from "../ui";

/** Lot 7.8 : l'enseignant valide une compétence professionnelle (passeport de compétences). */
export function ValiderCompetence({ eleveUtilisateurId }: { eleveUtilisateurId: string }) {
  const [intitule, setIntitule] = useState("");
  const [niveau, setNiveau] = useState<CompetenceMetier["niveau"]>("initie");
  const [message, setMessage] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  const valider = async () => {
    setEnvoi(true);
    setMessage(null);
    try {
      await validerCompetenceMetier(eleveUtilisateurId, intitule.trim(), niveau);
      setMessage("Compétence ajoutée au passeport de l'élève.");
      setIntitule("");
    } catch (err) {
      setMessage(messageErreur(err));
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div style={{ display: "flex", gap: "8px", alignItems: "flex-end", flexWrap: "wrap", marginTop: "10px" }}>
      <Field label="Compétence professionnelle">
        <TextInput value={intitule} onChange={(e) => setIntitule(e.target.value)} placeholder="Ex. Lire un schéma électrique" />
      </Field>
      <Field label="Niveau">
        <Select value={niveau} onChange={(e) => setNiveau(e.target.value as CompetenceMetier["niveau"])}>
          <option value="initie">Initié</option>
          <option value="confirme">Confirmé</option>
          <option value="maitrise">Maîtrisé</option>
        </Select>
      </Field>
      <Btn size="sm" variant="outline" onClick={valider} loading={envoi} disabled={intitule.trim().length < 3}>
        Valider la compétence
      </Btn>
      {message && <p role="status" style={{ width: "100%", margin: 0, fontSize: "var(--text-sm)" }}>{message}</p>}
    </div>
  );
}
