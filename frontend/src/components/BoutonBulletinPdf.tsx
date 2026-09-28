import { useState } from "react";
import { FileDown } from "lucide-react";
import { codeErreur, messageErreur } from "../api/client";
import { periodesDeLaClasse, telechargerBulletinPdf } from "../api/evaluations";
import { ouvrirBlobPdf } from "../utils/telechargerBlob";
import { Btn } from "./ui";

/** Bulletin PDF de la période en cours (parent : un bouton par enfant inscrit). */
export function BoutonBulletinPdf({ eleveUtilisateurId, classeId, prenom, onErreur }: {
  eleveUtilisateurId: string;
  classeId: string;
  prenom: string;
  onErreur: (message: string | null) => void;
}) {
  const [enCours, setEnCours] = useState(false);
  const telecharger = async () => {
    setEnCours(true);
    onErreur(null);
    try {
      const periodes = (await periodesDeLaClasse(classeId)).data;
      const periode = periodes.find((p) => p.courante) ?? periodes[0];
      const res = await telechargerBulletinPdf(eleveUtilisateurId, classeId, periode.code);
      ouvrirBlobPdf(res.data, `bulletin-${prenom}-${periode.code}.pdf`);
    } catch (err) {
      onErreur(
        codeErreur(err) === "aucun_devoir_evalue"
          ? `Pas encore de bulletin pour ${prenom} : aucun devoir de la période n'a été corrigé.`
          : messageErreur(err, "Impossible de générer le bulletin pour le moment."),
      );
    } finally {
      setEnCours(false);
    }
  };
  return (
    <Btn variant="outline" size="sm" loading={enCours} onClick={telecharger} leftIcon={<FileDown size={14} />}>
      Bulletin de {prenom} (PDF)
    </Btn>
  );
}
