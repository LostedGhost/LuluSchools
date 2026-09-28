import { api } from "./client";

/* Saisie papier (« guichet papier ») : l'administration photographie les documents papier
   des personnes sans smartphone ; l'IA les lit, un humain vérifie puis valide. */

export type TypeLecture = "feuille_notes" | "feuille_appel" | "cours" | "fiche_inscription";
export type Confiance = "sur" | "probable" | "non_trouve";

export interface EleveCandidat {
  eleve_id: string;
  nom: string;
  prenom: string;
  matricule: string | null;
}

export interface LigneLue {
  nom_lu: string;
  eleve_id: string | null;
  confiance: Confiance;
  note: number | null;
  absent: boolean;
  statut: "absent" | "retard" | null;
  commentaire: string | null;
  lisible: boolean;
}

export interface LectureOut {
  document_id: string;
  type: TypeLecture;
  lecture: Record<string, unknown> | null;
  erreur_lecture: string | null;
  lignes: LigneLue[];
  eleves: EleveCandidat[];
  classe_proposee_id: string | null;
}

export interface ResultatEnregistrement {
  objet_id: string | null;
  nombre: number;
  message: string;
}

export interface ContexteClasse {
  eleves: EleveCandidat[];
  enseignants: { id: string; nom: string; prenom: string; matiere: string | null }[];
  devoirs: { id: string; titre: string; matiere: string; date_limite: string; copies: number }[];
}

export interface CopieLue {
  document_id: string;
  nom_fichier: string;
  nom_lu: string | null;
  eleve_id: string | null;
  confiance: Confiance;
}

export interface DocumentPapierOut {
  id: string;
  type: string;
  statut: "lu" | "enregistre";
  nombre_fichiers: number;
  objet_type: string | null;
  objet_id: string | null;
  saisi_par: string;
  created_at: string;
  enregistre_le: string | null;
  resume: string | null;
}

export interface ConsentementEnAttente {
  inscription_id: string;
  eleve: string;
  classe: string;
  depose_le: string;
}

const formulaire = (fichiers: File[], champs: Record<string, string | null | undefined> = {}) => {
  const f = new FormData();
  Object.entries(champs).forEach(([cle, valeur]) => valeur && f.append(cle, valeur));
  fichiers.forEach((fichier) => f.append("fichiers", fichier));
  return f;
};

const multipart = { headers: { "Content-Type": "multipart/form-data" } };

export const lireDocument = (etablissementId: string, type: TypeLecture, classeId: string | null, fichiers: File[]) =>
  api.post<LectureOut>(`/etablissements/${etablissementId}/saisie-papier/lire`, formulaire(fichiers, { type, classe_id: classeId }), multipart);

export const contexteClasse = (classeId: string) => api.get<ContexteClasse>(`/classes/${classeId}/saisie-papier/contexte`);

export const enregistrerNotes = (documentId: string, payload: {
  classe_id: string; enseignant_id: string; matiere: string; titre: string; date_evaluation: string; note_sur: number;
  nature: "sommative" | "formative"; lignes: { eleve_id: string; note: number | null; absent: boolean }[];
}) => api.post<ResultatEnregistrement>(`/saisie-papier/${documentId}/notes`, payload);

export const enregistrerAppel = (documentId: string, payload: {
  classe_id: string; date: string; matiere: string | null; lignes: { eleve_id: string; statut: "absent" | "retard"; commentaire: string | null }[];
}) => api.post<ResultatEnregistrement>(`/saisie-papier/${documentId}/appel`, payload);

export const enregistrerCours = (documentId: string, payload: {
  classe_id: string; enseignant_id: string; titre: string; chapitre: string; contenu: string;
}) => api.post<ResultatEnregistrement>(`/saisie-papier/${documentId}/cours`, payload);

export interface InscriptionGuichetOut {
  inscription_id: string;
  eleve_id: string;
  matricule: string | null;
  mot_de_passe_provisoire: string | null;
  fiche_identifiants_pdf: string | null;
}

export const enregistrerInscriptionGuichet = (documentId: string, payload: {
  classe_id: string; nom: string; prenom: string; date_naissance: string; nationalite: "nationale" | "etrangere";
  sexe: "F" | "M" | null; tuteur_nom: string; tuteur_telephone: string | null; consentement_signe: boolean;
}) => api.post<InscriptionGuichetOut>(`/saisie-papier/${documentId}/inscription`, payload);

export const lireCopies = (devoirId: string, fichiers: File[]) =>
  api.post<{ copies: CopieLue[]; eleves: EleveCandidat[] }>(`/devoirs/${devoirId}/copies-papier/lire`, formulaire(fichiers), multipart);

export const enregistrerCopies = (devoirId: string, affectations: { document_id: string; eleve_id: string }[]) =>
  api.post<ResultatEnregistrement>(`/devoirs/${devoirId}/copies-papier/enregistrer`, { affectations });

/** Une photo par page du document signé (8 au maximum). */
export const contratSigneSurPapier = (contratId: string, fichiers: File[]) =>
  api.post<ResultatEnregistrement>(`/contrats/${contratId}/signature-papier`, formulaire(fichiers), multipart);

export const consentementSurPapier = (inscriptionId: string, fichiers: File[]) =>
  api.post<ResultatEnregistrement>(`/inscriptions/${inscriptionId}/consentement-papier`, formulaire(fichiers), multipart);

export const consentementsEnAttente = (etablissementId: string) =>
  api.get<ConsentementEnAttente[]>(`/etablissements/${etablissementId}/saisie-papier/consentements-en-attente`);

export const historiqueSaisies = (etablissementId: string) =>
  api.get<DocumentPapierOut[]>(`/etablissements/${etablissementId}/saisie-papier/historique`);

export const lienPhoto = (documentId: string, index = 0) =>
  api.get<{ url: string }>(`/saisie-papier/${documentId}/fichiers/${index}/lien`);
