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
  est_etudiant: boolean;
  telephone: string | null;
  /** Lot 7.2 : réglages d'accessibilité synchronisés sur le compte (null = défaut). */
  preferences_accessibilite?: import("../api/accessibilite").PreferencesAccessibilite | null;
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
  description: string | null;
  actif: boolean;
  /** Admission automatique des inscriptions (classes à l'ordre d'arrivée). */
  admission_automatique?: boolean;
  /** Lot 7.6 : rattachement territorial (12 départements, 77 communes). */
  departement?: string | null;
  commune?: string | null;
}

export interface ClasseOut {
  id: string;
  etablissement_id: string;
  niveau: string;
  filiere: string | null;
  annee_academique: string;
  reconduite_depuis_id: string | null;
  capacite: number;
  politique_depassement: PolitiqueDepassement;
}

export interface AffectationEnseignantOut {
  id: string;
  enseignant_id: string;
  classe_id: string;
  est_professeur_principal: boolean;
}

/* UC-24 : vue enrichie d'une classe pour l'enseignant qui la consulte */
export interface SalleEnseignantOut {
  id: string;
  etablissement_id: string;
  etablissement_nom: string;
  niveau: string;
  capacite: number;
  effectif: number;
  annee_academique: string;
  est_professeur_principal: boolean;
}

export interface EleveClasseOut {
  eleve_id: string;
  utilisateur_id: string | null;
  nom: string;
  prenom: string;
  matricule: string | null;
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
  est_etudiant: boolean;
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
  /** Lot 7.3 : obligatoire pour un cours audio ou vidéo (élèves sourds ou malentendants). */
  transcription?: string | null;
  a_des_sous_titres?: boolean;
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
export type NatureEvaluation = "formative" | "sommative";

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
  nature: NatureEvaluation;
  sujet_lulufiles_file_id: string | null;
  questions: QuestionDevoirOut[];
}

export interface DevoirProprietaireOut extends DevoirOut {
  bareme_document_lulufiles_file_id: string | null;
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
  copie_image_lulufiles_file_id: string | null;
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

export type TypeChampFormulaire = "texte_court" | "texte_long" | "fichier" | "choix_unique" | "choix_multiple";

export interface ChampFormulaire {
  id: string;
  label: string;
  type: TypeChampFormulaire;
  requis: boolean;
  options: string[] | null;
}

export interface PosteOut {
  id: string;
  etablissement_id: string;
  titre: string;
  description: string | null;
  matiere: string | null;
  remuneration_min: number | null;
  remuneration_max: number | null;
  schema_formulaire: ChampFormulaire[] | null;
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
  reponses_formulaire: Record<string, unknown> | null;
  enseignant_nom: string;
  enseignant_prenom: string;
  documents: DocumentCandidatureOut[];
  statut_casier_judiciaire: StatutVerificationCasier | null;
}

export type StatutVerificationCasier = "en_attente" | "conforme" | "non_conforme";

export interface VerificationCasierOut {
  candidature_id: string;
  statut: StatutVerificationCasier;
  date_verification: string | null;
  date_suppression_prevue: string | null;
  document_disponible: boolean;
}

export interface EnseignantSigneOut {
  id: string;
  nom: string;
  prenom: string;
  email: string | null;
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

export interface ContratAvecEnseignantOut extends ContratOut {
  enseignant_nom: string;
  enseignant_prenom: string;
}

export type StatutProposition = "en_attente" | "acceptee" | "refusee";

export interface PropositionReconductionOut {
  id: string;
  contrat_precedent_id: string;
  nouveau_contrat_id: string | null;
  statut: StatutProposition;
}

export interface TypeActeOut {
  id: string;
  etablissement_id: string;
  nom: string;
  prix: number;
  pieces_requises: string;
  condition_eligibilite: string | null;
  schema_formulaire: ChampFormulaire[] | null;
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
  reponses_formulaire: Record<string, unknown> | null;
  document_final_lulufiles_id: string | null;
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
  /** Lot 7.4 : message vocal (écouter via GET /messages/{id}/audio). */
  est_vocal?: boolean;
  duree_audio_s?: number | null;
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
  piece_jointe_nom?: string | null;
  piece_jointe_type?: string | null;
  created_at: string;
}

export interface SessionElProfessorOut {
  id: string;
  eleve_utilisateur_id: string;
  /** null : conversation d'aide générale, hors d'un cours précis. */
  cours_id: string | null;
  cours_titre: string | null;
  sujet: string | null;
  created_at: string;
  messages: MessageElProfessorOut[];
}

export type PersonaElProfessor = "eleve" | "enseignant" | "tuteur" | "famille";

/** Message tel que le renvoie le flux SSE, commun aux 4 personas. */
export interface MessageElProfessorChat {
  id: string;
  session_id: string;
  role: string;
  contenu: string;
  piece_jointe_nom?: string | null;
  piece_jointe_type?: string | null;
  created_at: string;
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

export interface ContestationMicroJobAEtrancherOut extends ContestationMicroJobOut {
  created_at: string;
  offre_titre: string;
  offre_prix: number;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 5 — UC-23 à UC-38 : refonte admin ministériel (supervision)
   ═══════════════════════════════════════════════════════════════ */

export interface ContestationMicroJobDetailOut {
  id: string;
  mission_id: string;
  motif: string;
  statut: StatutContestationMicroJob;
  decision_motif: string | null;
  created_at: string;
  offre_titre: string;
  prix: number;
  client_nom: string;
  client_prenom: string;
  prestataire_nom: string;
  prestataire_prenom: string;
}

export interface MissionAReverserOut {
  id: string;
  offre_titre: string;
  prix_paye: number;
  prestataire_id: string;
  prestataire_nom: string;
  prestataire_prenom: string;
  prestataire_telephone: string | null;
  date_declaration_fin: string | null;
}

export interface AdminUtilisateurOut {
  id: string;
  nom: string;
  prenom: string;
  login_id: string;
  email: string | null;
  role: string;
  actif: boolean;
  mot_de_passe_temporaire: boolean;
  created_at: string;
}

export interface AdminCoursOut {
  id: string;
  titre: string;
  chapitre: string;
  format: string;
  classe_id: string;
  etablissement_id: string;
  etablissement_nom: string;
  enseignant_id: string;
  enseignant_nom: string;
  enseignant_prenom: string;
  masque: boolean;
  created_at: string;
}

export interface AdminDevoirOut {
  id: string;
  titre: string;
  matiere: string;
  classe_id: string;
  etablissement_id: string;
  etablissement_nom: string;
  enseignant_id: string;
  enseignant_nom: string;
  enseignant_prenom: string;
  masque: boolean;
  created_at: string;
}

export interface AdminEvenementOut {
  id: string;
  etablissement_id: string;
  etablissement_nom: string;
  titre: string;
  lieu: string;
  date_heure: string;
  capacite_max: number;
  statut: "ouvert" | "annule";
}

export interface JournalAuditOut {
  id: string;
  acteur_id: string;
  action: string;
  cible_type: string;
  cible_id: string;
  motif: string | null;
  created_at: string;
}

export interface PageOut<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
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

/* ═══════════════════════════════════════════════════════════════
   Phase 6 — UC-39 à UC-58 : refonte admin établissement
   ═══════════════════════════════════════════════════════════════ */

export type StatutRentree = "ouverte" | "fermee";

export interface RentreeOut {
  id: string;
  etablissement_id: string;
  annee_academique: string;
  statut: StatutRentree;
  created_at: string;
}

export interface InscriptionVieScolaireOut {
  id: string;
  etablissement_id: string;
  etablissement_nom: string;
  classe_niveau: string;
  classe_filiere: string | null;
  annee_academique: string;
  statut: string;
  created_at: string;
}

export interface BulletinVieScolaireOut {
  id: string;
  etablissement_nom: string;
  periode: string;
  moyenne_generale: number;
  decision_passage: string | null;
}

export interface VieScolaireOut {
  eleve_id: string;
  nom: string;
  prenom: string;
  date_naissance: string;
  matricule: string | null;
  est_etudiant: boolean;
  photo_url: string | null;
  inscriptions: InscriptionVieScolaireOut[];
  bulletins: BulletinVieScolaireOut[];
}

export interface ConsoleEleveOut {
  eleve_id: string;
  nom: string;
  prenom: string;
  matricule: string | null;
  classe_id: string;
  classe_niveau: string;
  classe_filiere: string | null;
  statut_inscription: string;
}

export interface ConsoleEnseignantOut {
  utilisateur_id: string;
  nom: string;
  prenom: string;
  classe_id: string;
  classe_niveau: string;
  classe_filiere: string | null;
}

export interface ConsoleTuteurOut {
  utilisateur_id: string;
  nom: string;
  prenom: string;
  email: string | null;
  nb_enfants_dans_le_perimetre: number;
}

export interface ConsoleCoursOut {
  id: string;
  titre: string;
  chapitre: string;
  classe_id: string;
  classe_niveau: string;
  enseignant_nom: string;
  enseignant_prenom: string;
}

export interface ConsoleNoteOut {
  eleve_id: string;
  eleve_nom: string;
  eleve_prenom: string;
  classe_id: string;
  classe_niveau: string;
  periode: string;
  moyenne_generale: number;
  decision_passage: string | null;
}

export interface ContestationMarketplaceAEtrancherOut extends ContestationMarketplaceOut {
  created_at: string;
  annonce_titre: string;
  prix_paye: number;
}

export interface TransactionAReverserOut {
  id: string;
  annonce_titre: string;
  prix_paye: number;
  vendeur_nom: string;
  vendeur_prenom: string;
  vendeur_telephone: string | null;
  date_remise_declaree: string | null;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 5 — UC-23 : vie scolaire
   ═══════════════════════════════════════════════════════════════ */

export type NatureEntreeVieScolaire = "absence" | "retard" | "appreciation" | "incident" | "felicitation";

export interface EntreeVieScolaireOut {
  id: string;
  eleve_id: string;
  classe_id: string;
  auteur_id: string;
  nature: NatureEntreeVieScolaire;
  matiere: string | null;
  description: string;
  date_survenue: string;
  created_at: string;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 5 — UC-28 : recherche d'utilisateur designable (controleur)
   ═══════════════════════════════════════════════════════════════ */

export interface UtilisateurDesignableOut {
  id: string;
  nom: string;
  prenom: string;
  email: string | null;
  role: Role;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 5 — UC-27 : El Professor, volet enseignant
   ═══════════════════════════════════════════════════════════════ */

export type RoleMessageElProfessorEnseignant = "enseignant" | "assistant";

export interface MessageElProfessorEnseignantOut {
  id: string;
  session_id: string;
  role: RoleMessageElProfessorEnseignant;
  contenu: string;
  piece_jointe_nom?: string | null;
  piece_jointe_type?: string | null;
  created_at: string;
}

export interface SessionElProfessorEnseignantOut {
  id: string;
  enseignant_id: string;
  eleve_utilisateur_id: string | null;
  sujet: string | null;
  created_at: string;
  messages: MessageElProfessorEnseignantOut[];
}

export interface AlerteElProfessorOut {
  id: string;
  /** Conversation d'origine : enseignant, tuteur, famille ou élève. */
  origine: "enseignant" | "tuteur" | "famille" | "eleve";
  eleve_utilisateur_id: string | null;
  session_id: string;
  etablissement_id: string | null;
  motif: string;
  traite: boolean;
  created_at: string;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 5 — UC-25 : tableau collaboratif de session live
   ═══════════════════════════════════════════════════════════════ */

export type TypeTraitTableau = "trait_libre" | "texte" | "effacement";
export type ModePermissionEcriture = "pretee" | "accordee";
export type StatutDemandeCraie = "en_attente" | "accordee" | "refusee";

export interface DonneesTraitLibre {
  points: [number, number][];
  epaisseur?: number;
  couleur?: string;
}

export interface DonneesTraitTexte {
  x: number;
  y: number;
  texte: string;
  taille?: number;
  couleur?: string;
}

export interface PanneauTableauOut {
  id: string;
  session_id: string;
  ordre: number;
}

export interface TraitTableauOut {
  id: string;
  panneau_id: string;
  auteur_id: string;
  type: TypeTraitTableau;
  donnees: Record<string, unknown>;
  created_at: string;
}

export interface PanneauAvecTraitsOut {
  panneau: PanneauTableauOut;
  traits: TraitTableauOut[];
}

export interface PermissionEcritureOut {
  id: string;
  session_id: string;
  eleve_utilisateur_id: string;
  mode: ModePermissionEcriture;
}

export interface DemandeCraieOut {
  id: string;
  session_id: string;
  eleve_utilisateur_id: string;
  statut: StatutDemandeCraie;
}

export interface EtatTableauOut {
  panneaux: PanneauAvecTraitsOut[];
  permissions: PermissionEcritureOut[];
  demandes_en_attente: DemandeCraieOut[];
}

export interface CaptureTableauOut {
  id: string;
  session_id: string;
  panneau_id: string;
  lulufiles_file_id: string;
  created_at: string;
}

export interface MessageSessionLiveOut {
  id: string;
  session_id: string;
  auteur_id: string;
  contenu: string;
  created_at: string;
}

export type EvenementTempsReelSessionLive =
  | { type: "trait"; panneau_id: string; trait: TraitTableauOut }
  | { type: "demande_craie"; demande: DemandeCraieOut }
  | { type: "demande_craie_tranchee"; demande: DemandeCraieOut }
  | { type: "permission_accordee"; eleve_utilisateur_id: string }
  | { type: "permission_revoquee"; eleve_utilisateur_id: string }
  | { type: "message"; message: MessageSessionLiveOut }
  | { type: "webrtc_signal"; from: string; payload: unknown };

/* ═══════════════════════════════════════════════════════════════
   Phase 6 — UC-32/37 : El Professor Tuteur et El Professor Famille
   ═══════════════════════════════════════════════════════════════ */

export type RoleMessageElProfessorTuteur = "tuteur" | "assistant";

export interface MessageElProfessorTuteurOut {
  id: string;
  session_id: string;
  role: RoleMessageElProfessorTuteur;
  contenu: string;
  piece_jointe_nom?: string | null;
  piece_jointe_type?: string | null;
  created_at: string;
}

export interface SessionElProfessorTuteurOut {
  id: string;
  tuteur_id: string;
  eleve_utilisateur_id: string;
  sujet: string | null;
  created_at: string;
  messages: MessageElProfessorTuteurOut[];
}

export type RoleMessageElProfessorFamille = "tuteur" | "eleve" | "assistant";

export interface MessageElProfessorFamilleOut {
  id: string;
  session_id: string;
  role: RoleMessageElProfessorFamille;
  contenu: string;
  piece_jointe_nom?: string | null;
  piece_jointe_type?: string | null;
  created_at: string;
}

export interface SessionElProfessorFamilleOut {
  id: string;
  tuteur_id: string;
  eleve_utilisateur_id: string;
  sujet: string | null;
  created_at: string;
  rejointe_le: string | null;
  messages: MessageElProfessorFamilleOut[];
}

/* ═══════════════════════════════════════════════════════════════
   Phase 6 — UC-33 : résumé asynchrone de session live (tuteur)
   ═══════════════════════════════════════════════════════════════ */

export interface ResumeSessionLiveOut {
  id: string;
  session_id: string;
  contenu: string;
  created_at: string;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 6 — UC-35 : coffre-fort familial
   ═══════════════════════════════════════════════════════════════ */

export type ModuleDepenseCoffreFort = "micro_job" | "marketplace" | "acte";
export type StatutValidationParentale = "en_attente" | "approuvee" | "refusee";

export interface PlafondFamilialOut {
  id: string;
  eleve_utilisateur_id: string;
  plafond_hebdomadaire: number | null;
  seuil_validation: number | null;
  updated_at: string;
}

export interface ValidationParentaleOut {
  id: string;
  eleve_utilisateur_id: string;
  module: ModuleDepenseCoffreFort;
  reference_id: string;
  montant: number;
  statut: StatutValidationParentale;
  motif_refus: string | null;
  decidee_at: string | null;
  created_at: string;
}

export interface AlerteDepassementPlafondOut {
  id: string;
  eleve_utilisateur_id: string;
  module: ModuleDepenseCoffreFort;
  montant_semaine: number;
  plafond: number;
  created_at: string;
}

export interface ReleveFinancierOut {
  eleve_utilisateur_id: string;
  periode_debut: string | null;
  periode_fin: string | null;
  gains_micro_jobs: number;
  ventes_marketplace: number;
  achats_marketplace: number;
  depenses_micro_jobs: number;
  frais_actes: number;
  solde_net: number;
}

/* ═══════════════════════════════════════════════════════════════
   Phase 6 — UC-36 : radar familial (digest hebdomadaire)
   ═══════════════════════════════════════════════════════════════ */

export interface RadarFamilialOut {
  eleve_utilisateur_id: string;
  periode_debut: string;
  periode_fin: string;
  resume: string;
  sources: string[];
}

/* ═══════════════════════════════════════════════════════════════
   Phase 6 — UC-38 : passeport de compétences
   ═══════════════════════════════════════════════════════════════ */

export interface QuizReussiOut {
  quiz_id: string;
  cours_titre: string;
  cours_chapitre: string;
  score: number;
  date: string;
}

export interface CoursSuiviOut {
  id: string;
  titre: string;
  chapitre: string;
  format: string;
}

export interface MoyenneMatiereOut {
  matiere: string;
  moyenne: number;
}

export interface BadgeOut {
  id: string;
  label: string;
}

export interface PasseportOut {
  eleve_utilisateur_id: string;
  eleve_nom: string;
  eleve_prenom: string;
  quiz_reussis: QuizReussiOut[];
  cours_suivis: CoursSuiviOut[];
  moyennes_par_matiere: MoyenneMatiereOut[];
  badges: BadgeOut[];
}

export interface PasseportExportOut {
  lulufiles_file_id: string;
  lien: string;
}
