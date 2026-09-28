/* Libellés français des valeurs techniques renvoyées par l'API (statuts, rôles, catégories).
   Règle d'ergonomie : aucune valeur brute (« en_attente », « terminee_declaree ») ne doit
   apparaître à l'écran — passer par libelle(). Une valeur inconnue est rendue lisible
   (underscores remplacés, majuscule initiale) plutôt qu'affichée telle quelle. */

const LIBELLES: Record<string, string> = {
  // Rôles
  admin_etablissement: "Administration de l'établissement",
  admin_ministeriel: "Ministère",
  eleve: "Élève",
  enseignant: "Enseignant",
  tuteur: "Parent / tuteur",
  famille: "Famille",
  assistant: "El Professor",

  // Statuts génériques
  en_attente: "En attente",
  en_cours: "En cours",
  acceptee: "Acceptée",
  accordee: "Accordée",
  approuvee: "Approuvée",
  refusee: "Refusée",
  rejetee: "Rejetée",
  annulee: "Annulée",
  annule: "Annulé",
  ouvert: "Ouvert",
  ouverte: "Ouverte",
  fermee: "Fermée",
  terminee: "Terminée",
  planifiee: "Planifiée",
  soumise: "Soumise",
  validee: "Validée",
  valide: "Valide",
  expire: "Expiré",
  achete: "Acheté",
  rembourse: "Remboursé",
  remboursee: "Remboursée",
  contestee: "Contestée",
  confirmee: "Confirmée",
  finalisee: "Finalisée",
  payee: "Payée",

  // Inscriptions
  en_attente_consentement_parental: "Attend le consentement parental",
  notes_concours: "Sur concours (notes)",
  ordre_arrivee: "Ordre d'arrivée",
  tirage_sort: "Tirage au sort",

  // Recrutement
  en_evaluation: "En évaluation",
  retenue: "Retenue",
  en_attente_signature: "À signer",
  signe: "Signé",
  echec_notation: "Notation IA en échec",
  note: "Noté",
  non_pourvu: "Non pourvu",
  pourvu: "Pourvu",
  conforme: "Conforme",
  non_conforme: "Non conforme",

  // Actes
  en_traitement: "En traitement",

  // Évaluations
  corrigee: "Corrigée",
  en_correction: "En correction",
  echec_correction: "Correction à reprendre",
  formative: "Formative",
  sommative: "Sommative",
  rigide: "Barème strict",
  flexible: "Barème souple",
  proposition_en_attente: "Proposition en attente",
  remplace: "Remplacé",

  // Marketplace
  disponible: "Disponible",
  reservee: "Réservée",
  retiree: "Retirée",
  vendue: "Vendue",
  en_attente_paiement: "En attente de paiement",
  paiement_confirme: "Paiement confirmé",
  remise_declaree: "Remise déclarée",
  electronique: "Électronique",
  fournitures_scolaires: "Fournitures scolaires",
  manuels_livres: "Manuels et livres",
  vetements_uniformes: "Vêtements et uniformes",
  autre: "Autre",
  neuf: "Neuf",
  tres_bon_etat: "Très bon état",
  bon_etat: "Bon état",
  use: "Usé",

  // Micro-jobs
  terminee_declaree: "Fin déclarée",

  // Vie scolaire
  absence: "Absence",
  retard: "Retard",
  incident: "Incident",
  appreciation: "Appréciation",
  felicitation: "Félicitations",

  // Services
  cantine: "Cantine",
  transport: "Transport",
  evenement: "Événement",
  acte: "Acte administratif",
  marketplace: "Marketplace",
  micro_job: "Micro-job",

  // Cours
  texte: "Texte",
  pdf: "PDF",
  video: "Vidéo",
  audio: "Audio",

  // Établissements
  public: "Public",
  prive: "Privé",
  EP: "Enseignement primaire",
  ES: "Enseignement secondaire",
  UP: "Université",
  CA: "Centre d'alphabétisation",

  // Périodes d'évaluation
  trimestre1: "1er trimestre",
  trimestre2: "2e trimestre",
  trimestre3: "3e trimestre",
  semestre1: "1er semestre",
  semestre2: "2e semestre",

  // Décisions du conseil de classe
  admis: "Admis(e) en classe supérieure",
  admis_annee_validee: "Année validée",
  redouble: "Autorisé(e) à redoubler",
  reoriente: "Réorienté(e)",
  passage: "Admis(e) en classe supérieure",
  passage_classe_superieure: "Admis(e) en classe supérieure",

  // Actes générés automatiquement
  attestation_scolarite: "Attestation de scolarité",
  releve_notes: "Relevé de notes",
  certificat_reussite: "Certificat de réussite",

  // Coffre-fort
  pretee: "Prêtée",

  // Types de documents de candidature courants
  diplome: "Diplôme",
  cv: "CV",
  casier_judiciaire: "Casier judiciaire",
  lettre_motivation: "Lettre de motivation",
  piece_identite: "Pièce d'identité",
};

export function libelle(valeur: string | null | undefined): string {
  if (valeur === null || valeur === undefined || valeur === "") return "—";
  const connu = LIBELLES[valeur];
  if (connu) return connu;
  const lisible = valeur.replace(/_/g, " ");
  return lisible.charAt(0).toUpperCase() + lisible.slice(1);
}
