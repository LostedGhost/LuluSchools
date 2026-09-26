import { useEffect, useState } from "react";
import { mesInscriptions } from "../api/inscriptions";
import { messageErreur } from "../api/client";
import type { InscriptionAvecEleveOut } from "../types/api";

/** UC-30 à UC-38 : la plupart des pages tuteur du volet "mon enfant" ont besoin de la
 * même liste (inscriptions validées, avec eleve_id/eleve_utilisateur_id/classe_id) -
 * mutualisé ici plutôt que ré-implémenté page par page. */
export function useMesEnfants() {
  const [enfants, setEnfants] = useState<InscriptionAvecEleveOut[]>([]);
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    mesInscriptions()
      .then((res) => setEnfants(res.data.filter((i) => i.statut === "validee" && i.eleve_utilisateur_id)))
      .catch((err) => setErreur(messageErreur(err)))
      .finally(() => setChargement(false));
  }, []);

  return { enfants, chargement, erreur };
}
