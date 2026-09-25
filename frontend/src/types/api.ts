export type Role =
  | "admin_ministeriel"
  | "admin_etablissement"
  | "enseignant"
  | "eleve"
  | "tuteur";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  doit_changer_mot_de_passe: boolean;
}

export interface MeOut {
  id: string;
  nom: string;
  prenom: string;
  login_id: string;
  email: string | null;
  role: Role;
  email_verifie: boolean;
  mot_de_passe_temporaire: boolean;
}

export interface TuteurOut {
  id: string;
  nom: string;
  prenom: string;
  email: string;
  email_verifie: boolean;
}

export type TypeEtablissement = "EP" | "ES" | "UP";
export type StatutEtablissement = "public" | "prive";
export type PolitiqueDepassement = "ordre_arrivee" | "notes_concours" | "tirage_au_sort";

export interface EtablissementOut {
  id: string;
  nom: string;
  type: TypeEtablissement;
  statut: StatutEtablissement;
  code_etablissement: string;
}

export interface ClasseOut {
  id: string;
  etablissement_id: string;
  niveau: string;
  capacite: number;
  politique_depassement: PolitiqueDepassement;
}

export type Nationalite = "nationale" | "etrangere";
export type StatutInscription =
  | "en_attente_consentement_parental"
  | "soumise"
  | "validee"
  | "rejetee";

export interface InscriptionOut {
  id: string;
  eleve_id: string;
  classe_id: string;
  statut: StatutInscription;
  consentement_parental_horodatage: string | null;
  motif_rejet: string | null;
}

export interface InscriptionAvecEleveOut extends InscriptionOut {
  eleve_nom: string;
  eleve_prenom: string;
  eleve_matricule: string | null;
}

export interface EleveMeOut {
  id: string;
  nom: string;
  prenom: string;
  matricule: string | null;
  nationalite: Nationalite;
  classe_id: string | null;
  niveau: string | null;
  etablissement_id: string | null;
}

export type FormatCours = "texte" | "pdf" | "audio";

export interface CoursOut {
  id: string;
  classe_id: string;
  titre: string;
  chapitre: string;
  format: FormatCours;
  lulufiles_file_id: string | null;
}

export interface QuestionQuizPubliqueOut {
  id: string;
  ordre: number;
  enonce: string;
  choix: string[];
}

export interface QuizOut {
  id: string;
  cours_id: string;
  seuil_reussite: number;
  questions: QuestionQuizPubliqueOut[];
}

export interface TentativeQuizOut {
  id: string;
  score: number;
  reussie: boolean;
}

export type BaremeDevoir = "rigide" | "flexible";

export interface QuestionDevoirOut {
  id: string;
  ordre: number;
  enonce: string;
  points_max: number;
}

export interface DevoirOut {
  id: string;
  classe_id: string;
  titre: string;
  matiere: string;
  date_limite: string;
  bareme: BaremeDevoir;
  questions: QuestionDevoirOut[];
}

export type StatutSoumission = "en_correction" | "corrigee" | "echec_correction";

export interface ReponseOut {
  question_id: string;
  texte_reponse: string;
  points_obtenus: number | null;
}

export interface SoumissionOut {
  id: string;
  devoir_id: string;
  note: number | null;
  statut: StatutSoumission;
  reponses: ReponseOut[];
}

export interface BulletinOut {
  id: string;
  eleve_id: string;
  classe_id: string;
  periode: string;
  moyenne_generale: number;
  decision_passage: string | null;
  valide_par_conseil: boolean;
}

export interface TypeActeOut {
  id: string;
  etablissement_id: string;
  nom: string;
  prix: number;
  pieces_requises: string;
  condition_eligibilite: string | null;
}

export type StatutDemandeActe = "soumise" | "en_traitement" | "acceptee" | "rejetee";

export interface DemandeActeOut {
  id: string;
  eleve_id: string;
  type_acte_id: string | null;
  est_reclamation: boolean;
  statut: StatutDemandeActe;
  paiement_confirme: boolean;
  motif_rejet: string | null;
}
