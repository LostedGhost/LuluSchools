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
export type PolitiqueDepassement = "ordre_arrivee" | "notes_concours" | "tirage_sort";

export interface EtablissementOut {
  id: string;
  nom: string;
  type: TypeEtablissement;
  statut: StatutEtablissement;
  code_etablissement: string;
  latitude: number | null;
  longitude: number | null;
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
  eleve_utilisateur_id: string | null;
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

export type FormatCours = "texte" | "pdf" | "audio" | "video";

export interface CoursOut {
  id: string;
  classe_id: string;
  titre: string;
  chapitre: string;
  format: FormatCours;
  contenu_texte: string | null;
  lulufiles_file_id: string | null;
}

export interface LienFichierOut {
  url: string;
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

export type StatutPoste = "ouvert" | "pourvu" | "non_pourvu";

export interface CritereDocument {
  type_document: string;
  coefficient: number;
  seuil_minimal: number;
}

export interface PosteOut {
  id: string;
  etablissement_id: string;
  titre: string;
  statut: StatutPoste;
  criteres: CritereDocument[];
}

export type StatutDocumentCandidature = "en_attente" | "note" | "echec_notation";

export interface DocumentCandidatureOut {
  id: string;
  type_document: string;
  note_ia: number | null;
  statut: StatutDocumentCandidature;
  lulufiles_file_id: string | null;
}

export type StatutCandidature = "en_evaluation" | "retenue" | "rejetee";

export interface CandidatureOut {
  id: string;
  poste_id: string;
  statut: StatutCandidature;
  score: number | null;
  enseignant_nom: string;
  enseignant_prenom: string;
  documents: DocumentCandidatureOut[];
}

export type StatutContestation = "en_attente" | "acceptee" | "rejetee";

export interface ContestationOut {
  id: string;
  candidature_id: string;
  motif: string;
  statut: StatutContestation;
  motif_decision: string | null;
}

export type StatutContrat = "en_attente_signature" | "signe";

export interface ContratOut {
  id: string;
  candidature_id: string;
  etablissement_id: string;
  syllabus: string;
  date_fin: string;
  statut: StatutContrat;
  signature_horodatage: string | null;
  signature_image_lulufiles_id: string | null;
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
  eleve_nom: string;
  eleve_prenom: string;
  eleve_matricule: string | null;
  type_acte_id: string | null;
  est_reclamation: boolean;
  statut: StatutDemandeActe;
  paiement_confirme: boolean;
  motif_rejet: string | null;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 2/3 — UC-11/12 : tickets transport et cantine
   ═══════════════════════════════════════════════════════════════ */

export type StatutTicket = "achete" | "valide" | "expire" | "rembourse";
export type ServiceControle = "transport" | "cantine" | "evenement";

export interface LigneTransportOut {
  id: string;
  etablissement_id: string;
  nom: string;
  prix: number;
  capacite_par_trajet: number;
}

export interface TicketTransportOut {
  id: string;
  ligne_id: string;
  utilisateur_id: string;
  date_trajet: string;
  statut: StatutTicket;
  prix_paye: number;
  paiement_confirme: boolean;
}

export interface TypeRepasCantineOut {
  id: string;
  etablissement_id: string;
  nom: string;
  prix: number;
  capacite_par_jour: number;
}

export interface TicketCantineOut {
  id: string;
  type_repas_id: string;
  utilisateur_id: string;
  date_service: string;
  statut: StatutTicket;
  prix_paye: number;
  paiement_confirme: boolean;
}

export interface DesignationControleurOut {
  id: string;
  etablissement_id: string;
  utilisateur_id: string;
  service: ServiceControle;
  evenement_id: string | null;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 2/3 — UC-17 : billetterie d'événements
   ═══════════════════════════════════════════════════════════════ */

export type StatutEvenement = "ouvert" | "annule";
export type StatutBillet = "achete" | "valide" | "expire" | "rembourse";

export interface EvenementOut {
  id: string;
  etablissement_id: string;
  titre: string;
  description: string;
  lieu: string;
  date_heure: string;
  capacite_max: number;
  prix_billet: number;
  statut: StatutEvenement;
  parrain_utilisateur_id: string | null;
}

export interface BilletEvenementOut {
  id: string;
  evenement_id: string;
  utilisateur_id: string;
  statut: StatutBillet;
  prix_paye: number;
  paiement_confirme: boolean;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 2/3 — UC-13 : messagerie
   ═══════════════════════════════════════════════════════════════ */

export type TypeConversation = "dm" | "groupe_classe";

export interface ConversationOut {
  id: string;
  type: TypeConversation;
  classe_id: string | null;
  classe_niveau: string | null;
  autre_participant_id: string | null;
  autre_participant_nom: string | null;
  autre_participant_prenom: string | null;
  created_at: string;
}

export interface MessageOut {
  id: string;
  conversation_id: string;
  auteur_id: string;
  auteur_nom: string | null;
  auteur_prenom: string | null;
  contenu: string;
  created_at: string;
}

export interface SignalementOut {
  id: string;
  message_id: string;
  signale_par_id: string;
  traite: boolean;
  decision: string | null;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 2/3 — UC-14 : assistant El Professor
   ═══════════════════════════════════════════════════════════════ */

export type RoleMessageElProfessor = "eleve" | "assistant";

export interface MessageElProfessorOut {
  id: string;
  session_id: string;
  role: RoleMessageElProfessor;
  contenu: string;
  created_at: string;
}

export interface SessionElProfessorOut {
  id: string;
  eleve_utilisateur_id: string;
  cours_id: string;
  messages: MessageElProfessorOut[];
}

/* ═══════════════════════════════════════════════════════════════
   Phase 2/3 — UC-16 : cours en direct
   ═══════════════════════════════════════════════════════════════ */

export type StatutSessionLive = "planifiee" | "en_cours" | "terminee";

export interface SessionLiveOut {
  id: string;
  classe_id: string;
  enseignant_id: string;
  date_heure: string;
  statut: StatutSessionLive;
}

export interface SessionLiveDemarreeOut extends SessionLiveOut {
  token_connexion: string;
}

export interface ConsentementCameraLiveOut {
  id: string;
  eleve_utilisateur_id: string;
  date_consentement: string;
}

export interface ParticipationLiveOut {
  id: string;
  session_id: string;
  eleve_utilisateur_id: string;
  camera_autorisee: boolean;
  token_connexion: string;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 2/3 — UC-18 : micro-jobs et séquestre
   ═══════════════════════════════════════════════════════════════ */

export type StatutOffreMicroJob = "en_attente_paiement" | "ouverte" | "fermee" | "annulee";
export type StatutMissionMicroJob =
  | "en_cours"
  | "terminee_declaree"
  | "validee"
  | "contestee"
  | "remboursee"
  | "payee";
export type StatutContestationMicroJob = "en_attente" | "acceptee" | "rejetee";

export interface OffreMicroJobOut {
  id: string;
  client_id: string;
  titre: string;
  description: string;
  prix: number;
  statut: StatutOffreMicroJob;
  paiement_confirme: boolean;
}

export interface MissionMicroJobOut {
  id: string;
  offre_id: string;
  prestataire_id: string;
  statut: StatutMissionMicroJob;
  prix_paye: number;
  paiement_confirme: boolean;
  date_declaration_fin: string | null;
  date_limite_validation: string | null;
  reference_paiement_prestataire: string | null;
}

export interface ContestationMicroJobOut {
  id: string;
  mission_id: string;
  motif: string;
  statut: StatutContestationMicroJob;
  decision_motif: string | null;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 4 — UC-20/21/22 : marketplace étudiante
   ═══════════════════════════════════════════════════════════════ */

export type CategorieAnnonce =
  | "fournitures_scolaires"
  | "manuels_livres"
  | "vetements_uniformes"
  | "electronique"
  | "autre";
export type EtatArticle = "neuf" | "tres_bon_etat" | "bon_etat" | "use";
export type StatutAnnonce = "disponible" | "reservee" | "vendue" | "retiree";
export type StatutTransactionMarketplace =
  | "en_attente_paiement"
  | "paiement_confirme"
  | "remise_declaree"
  | "confirmee"
  | "contestee"
  | "finalisee"
  | "remboursee"
  | "annulee";
export type StatutContestationMarketplace = "en_attente" | "acceptee" | "rejetee";

export interface AnnonceMarketplaceOut {
  id: string;
  etablissement_id: string;
  vendeur_id: string;
  titre: string;
  description: string;
  categorie: CategorieAnnonce;
  etat: EtatArticle;
  prix: number;
  statut: StatutAnnonce;
}

export interface PhotoAnnonceLienOut {
  id: string;
  url: string;
  ordre: number;
}

export interface AnnonceMarketplaceDetailOut extends AnnonceMarketplaceOut {
  photos: PhotoAnnonceLienOut[];
}

export interface AnnoncesMarketplacePage {
  items: AnnonceMarketplaceOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface SignalementAnnonceOut {
  id: string;
  annonce_id: string;
  signale_par_id: string;
  traite: boolean;
  decision: string | null;
}

export interface TransactionMarketplaceOut {
  id: string;
  annonce_id: string;
  acheteur_id: string;
  statut: StatutTransactionMarketplace;
  prix_paye: number;
  paiement_confirme: boolean;
  date_remise_declaree: string | null;
  date_limite_confirmation: string | null;
  reference_paiement_vendeur: string | null;
}

export interface ContestationMarketplaceOut {
  id: string;
  transaction_id: string;
  motif: string;
  statut: StatutContestationMarketplace;
  decision_motif: string | null;
}
