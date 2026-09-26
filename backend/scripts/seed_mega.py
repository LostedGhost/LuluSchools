"""Mega seed de developpement : peuple TOUTES les tables de l'application avec un
volume de donnees "grandeur nature" representatif du systeme educatif beninois
(~10 etablissements par type, niveaux/filieres/matieres reels, et un jeu de donnees
complet pour les 18 UC implementes, Phase 1 + Phase 2/3).

ATTENTION : ce script REINITIALISE ENTIEREMENT le schema (DROP + CREATE de toutes les
tables de l'application, via Base.metadata) avant de le repeupler. Il est reserve a un
environnement de developpement local (verifie via ENVIRONMENT dans .env) et exige une
confirmation explicite.

Usage :
    cd backend
    python scripts/seed_mega.py --yes
    python scripts/seed_mega.py --yes --scale 0.3   # jeu de donnees reduit (tests rapides)
    python scripts/seed_mega.py --yes --seed 7       # autre tirage aleatoire reproductible

Tous les comptes crees partagent le mot de passe "Password1!" (mot de passe permanent,
pas de changement force a la premiere connexion - ce script court-circuite deliberement
le flux OTP/mot de passe temporaire pour rester utilisable immediatement). Un recapitulatif
(identifiants de connexion type par role) est imprime a la fin de l'execution.
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: F401  # enregistre tous les modeles sur Base.metadata

from app.core.config import settings
from app.core.crypto import chiffrer_bytes
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password

from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique
from app.modules.billetterie.models import BilletEvenement, Evenement, StatutBillet, StatutEvenement
from app.modules.controle_acces.models import DesignationControleur, ServiceControle
from app.modules.cours_direct.models import (
    ConsentementCameraLive,
    ParticipationLive,
    SessionLive,
    StatutSessionLive,
)
from app.modules.etablissements.models import (
    AdminEtablissement,
    Classe,
    Etablissement,
    PolitiqueDepassement,
    StatutEtablissement,
    TypeEtablissement,
)
from app.modules.evaluations.models import (
    BaremeDevoir,
    Bulletin,
    Devoir,
    QuestionDevoir,
    ReferentielCoefficient,
    ReponseSoumission,
    Soumission,
    StatutReferentiel,
    StatutSoumission,
)
from app.modules.identite.models import Enseignant, RoleUtilisateur, Tuteur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, Nationalite, StatutInscription
from app.modules.marketplace.models import (
    AnnonceMarketplace,
    CategorieAnnonce,
    ContestationMarketplace,
    EtatArticle,
    PhotoAnnonceMarketplace,
    SignalementAnnonceMarketplace,
    StatutAnnonce,
    StatutContestationMarketplace,
    StatutTransactionMarketplace,
    TransactionMarketplace,
)
from app.modules.messagerie.models import (
    Conversation,
    Message,
    ParticipantConversation,
    SignalementMessage,
    TypeConversation,
)
from app.modules.micro_jobs.models import (
    ContestationMicroJob,
    MissionMicroJob,
    OffreMicroJob,
    StatutContestationMicroJob,
    StatutMissionMicroJob,
    StatutOffreMicroJob,
)
from app.modules.pedagogie.models import (
    Cours,
    FormatCours,
    MessageElProfessor,
    QuestionQuiz,
    Quiz,
    RoleMessageElProfessor,
    SessionElProfessor,
    TentativeQuiz,
)
from app.modules.recrutement.models import (
    Candidature,
    Contestation,
    Contrat,
    CritereDocumentPoste,
    DocumentCandidature,
    Poste,
    PropositionReconduction,
    StatutCandidature,
    StatutContestation,
    StatutContrat,
    StatutDocument,
    StatutPoste,
    StatutProposition,
    StatutVerificationCasier,
    VerificationCasierJudiciaire,
)
from app.modules.services_scolaires.models import (
    LigneTransport,
    StatutTicket,
    TicketCantine,
    TicketTransport,
    TypeRepasCantine,
)
from app.modules.visites_virtuelles.models import TypeVisiteVirtuelle, VisiteVirtuelle

# ═══════════════════════════════════════════════════════════════════════════
# Configuration (ajustable via --scale)
# ═══════════════════════════════════════════════════════════════════════════

MOT_DE_PASSE_COMMUN = "Password1!"
DOMAINE_SEED = "seed.luluschools.test"


class Config:
    def __init__(self, scale: float) -> None:
        self.n_ep = max(1, round(10 * scale))
        self.n_es = max(1, round(10 * scale))
        self.n_up = max(1, round(10 * scale))
        self.eleves_par_classe = (max(3, round(8 * scale)), max(4, round(16 * scale)))
        self.postes_par_etab = (1, max(1, round(2 * scale)))
        self.candidatures_par_poste = (2, max(2, round(3 * scale)))
        self.cours_par_classe = max(1, round(2 * scale))
        self.devoirs_par_classe = max(1, round(2 * scale))
        self.sessions_live_par_classe = max(1, round(2 * scale))
        self.lignes_transport_par_etab = max(1, round(2 * scale))
        self.types_cantine_par_etab = max(1, round(2 * scale))
        self.tickets_par_service = max(2, round(8 * scale))
        self.evenements_par_etab = max(1, round(2 * scale))
        self.billets_par_evenement = max(2, round(10 * scale))
        self.n_offres_micro_job = max(4, round(40 * scale))
        self.types_actes_par_etab = max(1, round(3 * scale))
        self.demandes_actes_ratio = 0.2
        self.annonces_marketplace_par_etab = max(2, round(6 * scale))


# ═══════════════════════════════════════════════════════════════════════════
# Taxonomie du systeme educatif beninois (niveaux / filieres / matieres)
# ═══════════════════════════════════════════════════════════════════════════

NIVEAUX_MATERNEL_PRIMAIRE = [
    "Maternelle 1", "Maternelle 2",
    "CI", "CP", "CE1", "CE2", "CM1", "CM2",
]

MATIERES_PRIMAIRE = {
    "Maternelle 1": ["Éveil", "Graphisme", "Langage", "Activités Manuelles"],
    "Maternelle 2": ["Éveil", "Graphisme", "Langage", "Activités Manuelles", "Pré-lecture"],
    "CI": ["Français", "Mathématiques", "Activités d'Éveil", "Éducation Civique et Morale"],
    "CP": ["Français", "Mathématiques", "Activités d'Éveil", "Éducation Civique et Morale"],
    "CE1": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS"],
    "CE2": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS"],
    "CM1": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS", "Anglais"],
    "CM2": ["Français", "Mathématiques", "Sciences d'Observation", "Histoire-Géographie", "Éducation Civique et Morale", "EPS", "Anglais"],
}

NIVEAUX_SECONDAIRE_TRONC_COMMUN = ["6ème", "5ème", "4ème", "3ème"]
MATIERES_TRONC_COMMUN = [
    "Français", "Mathématiques", "Anglais", "Histoire-Géographie",
    "Sciences de la Vie et de la Terre (SVT)", "Physique-Chimie",
    "Éducation Civique et Morale", "EPS",
]

# Séries générales (2nde/1ère/Terminale), nomenclature béninoise historique.
SERIES_GENERALES = {
    "A1": "Lettres-Langues",
    "A2": "Lettres-Philosophie",
    "B": "Sciences Économiques et Sociales",
    "C": "Mathématiques et Sciences Physiques",
    "D": "Mathématiques et Sciences de la Vie et de la Terre",
}
MATIERES_GENERAL_COMMUN = ["Français", "Anglais", "Philosophie", "EPS", "Histoire-Géographie"]
MATIERES_PAR_SERIE_GENERALE = {
    "A1": ["Littérature", "Latin/Espagnol", "Philosophie Approfondie"],
    "A2": ["Littérature", "Philosophie Approfondie", "Histoire-Géographie Approfondie"],
    "B": ["Sciences Économiques", "Mathématiques", "Comptabilité"],
    "C": ["Mathématiques", "Physique-Chimie", "Sciences de l'Ingénieur"],
    "D": ["Mathématiques", "SVT", "Physique-Chimie"],
}

# Séries techniques (nomenclature F = industrielle, G = administrative/gestion).
SERIES_TECHNIQUES = {
    "F2": "Électrotechnique",
    "F3": "Génie Civil",
    "F4": "Mécanique Générale",
    "G1": "Secrétariat / Bureautique",
    "G2": "Comptabilité-Gestion",
    "G3": "Techniques Commerciales",
}
NIVEAUX_TECHNIQUE_2ND_CYCLE = [
    "1ère année de lycée technique", "2ème année de lycée technique", "3ème année de lycée technique",
]
MATIERES_TECHNIQUE_COMMUN = ["Français", "Mathématiques", "Anglais", "Technologie Générale"]
MATIERES_PAR_SERIE_TECHNIQUE = {
    "F2": ["Électrotechnique", "Électronique", "Schémas Électriques"],
    "F3": ["Résistance des Matériaux", "Topographie", "Dessin du Bâtiment"],
    "F4": ["Mécanique Générale", "Usinage", "Dessin Industriel"],
    "G1": ["Bureautique", "Techniques de Secrétariat", "Correspondance Administrative"],
    "G2": ["Comptabilité Générale", "Mathématiques Financières", "Droit des Affaires"],
    "G3": ["Techniques Commerciales", "Économie d'Entreprise", "Marketing"],
}

NIVEAUX_UNIVERSITE = [
    "1ère année de Licence", "2ème année de Licence", "3ème année de Licence",
    "1ère année de Master", "2ème année de Master",
]

FILIERES_UNIVERSITE_PUBLIC = {
    "Droit et Sciences Politiques": ["Droit Civil", "Droit Constitutionnel", "Droit Pénal", "Procédure Civile", "Finances Publiques"],
    "Sciences Économiques et de Gestion": ["Microéconomie", "Macroéconomie", "Comptabilité Générale", "Statistiques", "Gestion Financière"],
    "Lettres Modernes": ["Littérature Française", "Linguistique", "Stylistique", "Littérature Africaine"],
    "Histoire et Archéologie": ["Histoire Contemporaine", "Archéologie Préhistorique", "Historiographie"],
    "Sciences Agronomiques": ["Agronomie Générale", "Zootechnie", "Pédologie", "Phytotechnie"],
    "Génie Civil": ["Résistance des Matériaux", "Béton Armé", "Topographie", "Hydraulique"],
    "Génie Électrique": ["Électrotechnique", "Automatisme", "Électronique de Puissance"],
    "Informatique et Télécommunications": ["Algorithmique", "Bases de Données", "Réseaux", "Systèmes d'Exploitation"],
    "Médecine": ["Anatomie", "Physiologie", "Biochimie", "Sémiologie"],
    "Sciences de la Vie et de la Terre": ["Botanique", "Zoologie", "Géologie", "Écologie"],
}
FILIERES_UNIVERSITE_PRIVE = {
    "Gestion des Entreprises": ["Management", "Comptabilité Générale", "Droit des Affaires", "Fiscalité"],
    "Informatique de Gestion": ["Algorithmique", "Bases de Données", "Génie Logiciel", "Réseaux"],
    "Marketing et Communication": ["Marketing Stratégique", "Communication d'Entreprise", "Étude de Marché"],
    "Banque et Finance": ["Analyse Financière", "Techniques Bancaires", "Marchés Financiers"],
    "Logistique et Transport": ["Gestion de la Chaîne Logistique", "Transport International", "Droit des Transports"],
    "Ressources Humaines": ["Gestion des Ressources Humaines", "Droit du Travail", "Psychologie du Travail"],
}

NOMS_ETABLISSEMENTS_EP = [
    "École Primaire Publique d'Akpakpa", "École Primaire Publique de Godomey",
    "École Primaire Publique de Sèmè-Kpodji", "École Primaire Publique de Parakou Centre",
    "École Primaire La Colombe", "Complexe Scolaire Les Flamboyants",
    "École Primaire Sainte-Rita", "Groupe Scolaire Excellence",
    "École Primaire Publique d'Abomey", "École Primaire Les Petits Génies",
]
NOMS_ETABLISSEMENTS_ES_GENERAL = [
    "Collège d'Enseignement Général de Cotonou", "Lycée Béhanzin",
    "Lycée Coulibaly", "Lycée Notre-Dame de Lourdes",
    "Collège Sainte-Jeanne d'Arc", "Lycée Mathieu Bouké",
    "CEG Godomey", "Lycée Toffa 1er",
]
NOMS_ETABLISSEMENTS_ES_TECHNIQUE = [
    "Lycée Technique Coulibaly", "Collège d'Enseignement Technique de Porto-Novo",
    "Lycée Professionnel Adjaha", "Institut Technique Saint-Joseph",
]
NOMS_ETABLISSEMENTS_UP_PUBLIC = [
    "Université Nationale des Sciences, Technologies, Ingénierie et Mathématiques",
    "Université d'Abomey-Calavi — Faculté Pilote", "Université de Parakou",
    "Institut National Supérieur de Technologie Industrielle",
]
NOMS_ETABLISSEMENTS_UP_PRIVE = [
    "Institut Supérieur de Management de Cotonou", "École Supérieure de Gestion et d'Informatique",
    "Institut Africain d'Informatique", "Haute École de Commerce du Bénin",
    "Institut Polytechnique Universitaire de Cotonou", "École Supérieure de Comptabilité et de Finance",
]

NOMS_FAMILLE = [
    "Dossou", "Adjovi", "Houngbo", "Kone", "Traore", "Agbo", "Zinsou", "Aissi", "Sossou", "Akakpo",
    "Gbaguidi", "Toko", "Amoussou", "Codjo", "Kpogbe", "Adande", "Hounkpe", "Dahoue", "Sagbo", "Koudjo",
    "Aholou", "Djossou", "Glele", "Assogba", "Tossou", "Hounsou", "Ahoyo", "Sonon", "Bokossa", "Idrissou",
    "Yacoubou", "Alassane", "Hounkonnou", "Chabi", "Gomina", "Sacca", "Baba", "Salifou", "Orou", "Tamou",
]
PRENOMS_MASCULINS = [
    "Kossi", "Moussa", "Kofi", "Eric", "Blaise", "Josue", "Firmin", "Wilfried", "Armel", "Bio",
    "Sena", "Comlan", "Judicael", "Romuald", "Cyrille", "Parfait", "Ulrich", "Landry", "Fabrice", "Ignace",
    "Herve", "Aristide", "Modeste", "Elisee", "Fortune", "Gildas", "Marcellin", "Severin", "Donatien", "Cedric",
]
PRENOMS_FEMININS = [
    "Awa", "Fatou", "Aisha", "Chantal", "Grace", "Clarisse", "Odette", "Prisca", "Nadege", "Bernice",
    "Solange", "Edwige", "Rosine", "Carole", "Huguette", "Estelle", "Divine", "Rafiatou", "Bintou", "Judith",
    "Reine", "Sidonie", "Colette", "Perpetue", "Viviane", "Berthine", "Sandrine", "Beatrice", "Aicha", "Latifa",
]

MOTIFS_CONTESTATION_RECRUTEMENT = [
    "Le document diplome a ete mal note par l'IA, la copie transmise etait pourtant lisible.",
    "Je conteste le score attribue a mon CV, mon experience n'a pas ete prise en compte.",
    "Erreur manifeste dans la notation automatique de mes pieces justificatives.",
]
MOTIFS_CONTESTATION_MICRO_JOB = [
    "Le travail livre ne correspond pas a ce qui avait ete convenu.",
    "La mission n'a pas ete terminee dans les delais annonces.",
    "Qualite du service tres en dessous de la description de l'offre.",
]

TITRES_OFFRES_MICRO_JOB = [
    "Cours particulier de mathematiques niveau college",
    "Soutien scolaire en francais pour eleve de CM2",
    "Preparation au baccalaureat serie D",
    "Cours d'anglais conversationnel",
    "Aide aux devoirs niveau primaire",
    "Initiation a l'informatique pour debutants",
    "Cours de comptabilite pour etudiants en gestion",
    "Repetition en physique-chimie niveau lycee",
    "Accompagnement redaction de memoire",
    "Cours de code et algorithmique pour lyceens",
    "Soutien en philosophie pour terminale",
    "Preparation aux concours d'entree en universite",
]

TITRES_EVENEMENTS = [
    "Kermesse de fin d'annee", "Journee culturelle de l'etablissement",
    "Remise des diplomes", "Spectacle de fin de trimestre",
    "Tournoi sportif inter-classes", "Soiree de gala des anciens eleves",
    "Journee portes ouvertes", "Concert de la chorale scolaire",
]


def rng_choice_weighted(rng: random.Random, options: list, weights: list):
    return rng.choices(options, weights=weights, k=1)[0]


def new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def add(db, obj):
    """Remplace `db.add` partout dans ce script : aucun de ces modeles n'utilise
    `relationship()` pour ses cles etrangeres (juste des colonnes id brutes), donc
    l'ordre d'insertion automatique de SQLAlchemy (qui se base sur le graphe de
    dependances des relations ORM, pas seulement sur les contraintes de cle
    etrangere de la table) ne peut pas etre deduit sans aide. Un flush immediat
    apres chaque ajout transforme chaque ligne en une ligne reelle de la
    transaction en cours avant que la ligne suivante ne puisse la referencer -
    verifie par un cas reproductible minimal (Etablissement + TypeActeAcademique
    sans flush intermediaire => ForeignKeyViolation)."""
    db.add(obj)
    db.flush()
    return obj


# ═══════════════════════════════════════════════════════════════════════════
# Contexte d'execution : compteurs, RNG, mot de passe partage
# ═══════════════════════════════════════════════════════════════════════════

class Contexte:
    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)
        self.compteur_personne = 0
        self.mot_de_passe_hash = hash_password(MOT_DE_PASSE_COMMUN)
        self.tuteurs: list[Utilisateur] = []
        self.eleves_par_etablissement: dict[str, list[Eleve]] = {}
        self.enseignants_signes_par_etablissement: dict[str, list[Utilisateur]] = {}
        self.tous_enseignants_signes: list[Utilisateur] = []
        self.contrats_signes: list[Contrat] = []
        self.admins_etablissement: list[Utilisateur] = []
        self.admin_par_etablissement: dict[str, Utilisateur] = {}
        self.admin_ministeriel: Utilisateur | None = None
        self.classes: list[Classe] = []
        self.classes_par_etablissement: dict[str, list[Classe]] = {}
        self.matieres_par_classe: dict[str, list[str]] = {}
        self.conversation_groupe_par_classe: dict[str, str] = {}
        self.cours_texte_par_classe: dict[str, list[Cours]] = {}
        self.referentiels_valides: dict[tuple[str, str], ReferentielCoefficient] = {}
        self.consentements_camera_donnes: set[str] = set()
        self.compteurs = {}
        self.sequences: dict[str, int] = {}

    def next_seq(self, cle: str) -> int:
        self.sequences[cle] = self.sequences.get(cle, 0) + 1
        return self.sequences[cle]

    def personne(self, genre: str | None = None) -> tuple[str, str, str]:
        """Retourne (nom, prenom, email_unique) pour un nouveau compte de test."""
        self.compteur_personne += 1
        if genre == "F":
            prenom = self.rng.choice(PRENOMS_FEMININS)
        elif genre == "M":
            prenom = self.rng.choice(PRENOMS_MASCULINS)
        else:
            prenom = self.rng.choice(PRENOMS_FEMININS + PRENOMS_MASCULINS)
        nom = self.rng.choice(NOMS_FAMILLE)
        email = f"{prenom.lower()}.{nom.lower()}.{self.compteur_personne}@{DOMAINE_SEED}"
        return nom, prenom, email

    def compter(self, table: str, n: int = 1) -> None:
        self.compteurs[table] = self.compteurs.get(table, 0) + n


def creer_utilisateur(
    db, ctx: Contexte, *, role: RoleUtilisateur, nom: str, prenom: str, login_id: str, email: str | None
) -> Utilisateur:
    u = Utilisateur(
        id=new_id(),
        nom=nom,
        prenom=prenom,
        login_id=login_id,
        email=email,
        mot_de_passe_hash=ctx.mot_de_passe_hash,
        mot_de_passe_temporaire=False,
        role=role,
        email_verifie=True,
    )
    add(db, u)
    ctx.compter("utilisateurs")
    return u


def creer_tuteur(db, ctx: Contexte) -> Utilisateur:
    nom, prenom, email = ctx.personne()
    u = creer_utilisateur(db, ctx, role=RoleUtilisateur.TUTEUR, nom=nom, prenom=prenom, login_id=email, email=email)
    add(db, Tuteur(utilisateur_id=u.id))
    ctx.compter("tuteurs")
    ctx.tuteurs.append(u)
    return u


def creer_enseignant_utilisateur(db, ctx: Contexte) -> Utilisateur:
    genre = ctx.rng.choice(["M", "F"])
    nom, prenom, email = ctx.personne(genre)
    u = creer_utilisateur(db, ctx, role=RoleUtilisateur.ENSEIGNANT, nom=nom, prenom=prenom, login_id=email, email=email)
    add(db, Enseignant(utilisateur_id=u.id))
    ctx.compter("enseignants")
    return u


# ═══════════════════════════════════════════════════════════════════════════
# Générateurs de code établissement / matricule élève (logique identique aux
# fonctions internes des routeurs reels, mais en memoire : au moment du seed rien
# n'est encore flush en base, une requete COUNT(*) comme celle des routeurs ne
# verrait donc pas les lignes deja ajoutees dans la meme transaction).
# ═══════════════════════════════════════════════════════════════════════════

_PREFIXES_CYCLE_MATRICULE = {TypeEtablissement.EP: "7", TypeEtablissement.ES: "8", TypeEtablissement.UP: ""}


def attribuer_code_etablissement(ctx: Contexte, type_etablissement: TypeEtablissement) -> str:
    n = ctx.next_seq(f"code_{type_etablissement.value}")
    return f"{type_etablissement.value}{n:02d}"


def attribuer_matricule(ctx: Contexte, type_etablissement: TypeEtablissement, nationalite: Nationalite) -> str:
    chiffre_nationalite = "1" if nationalite == Nationalite.NATIONALE else "2"
    annee_suffixe = f"{date.today().year % 100:02d}"
    prefixe_cycle = _PREFIXES_CYCLE_MATRICULE[type_etablissement]
    cle = f"{prefixe_cycle}{chiffre_nationalite}{annee_suffixe}"
    n = ctx.next_seq(f"matricule_{cle}")
    return f"{prefixe_cycle}{chiffre_nationalite}{n:05d}{annee_suffixe}"


# ═══════════════════════════════════════════════════════════════════════════
# Établissements et classes
# ═══════════════════════════════════════════════════════════════════════════

def _creer_classe(db, ctx: Contexte, etablissement: Etablissement, niveau: str, matieres: list[str], capacite: int) -> Classe:
    classe = Classe(
        id=new_id(),
        etablissement_id=etablissement.id,
        niveau=niveau,
        capacite=capacite,
        politique_depassement=ctx.rng.choice(list(PolitiqueDepassement)),
    )
    add(db, classe)
    ctx.compter("classes")
    conversation_id = new_id()
    add(db, Conversation(id=conversation_id, type=TypeConversation.GROUPE_CLASSE, classe_id=classe.id))
    ctx.compter("conversations")
    ctx.conversation_groupe_par_classe[classe.id] = conversation_id
    ctx.classes.append(classe)
    ctx.classes_par_etablissement.setdefault(etablissement.id, []).append(classe)
    ctx.matieres_par_classe[classe.id] = matieres
    return classe


def _capacite_pour(ctx: Contexte, cfg: Config) -> int:
    return ctx.rng.randint(*cfg.eleves_par_classe) + ctx.rng.randint(2, 8)


# ═══════════════════════════════════════════════════════════════════════════
# Géolocalisation : devine une position plausible a partir du NOM de chaque
# etablissement genere ci-dessous (les noms referencent deja de vraies
# villes/quartiers beninois - Cotonou, Porto-Novo, Abomey-Calavi, Abomey,
# Parakou, Godomey, Seme-Kpodji, Akpakpa - ou de vraies institutions connues
# comme l'UNSTIM d'Abomey ou l'INSTI de Lokossa), avec un petit ecart
# deterministe par etablissement pour eviter que plusieurs etablissements
# d'une meme ville se superposent exactement sur la carte. Logique identique
# a scripts/update_localisations.py (qui reste utile pour geolocaliser une
# base deja peuplee AVANT ce changement, ou pour un rejeu --overwrite).
# ═══════════════════════════════════════════════════════════════════════════

INSTITUTIONS_CONNUES: dict[str, tuple[float, float]] = {
    "mathieu bouké": (9.3372, 2.6303),  # Lycee Mathieu Bouke - Parakou
    "toffa 1er": (6.4969, 2.6289),  # Lycee Toffa 1er - Porto-Novo
    "technologie industrielle": (6.6389, 1.7167),  # INSTI - Lokossa
    "ingénierie et mathématiques": (7.1825, 1.9911),  # UNSTIM - Abomey
}

VILLES_BENIN: dict[str, tuple[float, float]] = {
    "abomey-calavi": (6.4025, 2.3389),
    "porto-novo": (6.4969, 2.6289),
    "seme-kpodji": (6.3661, 2.6156),
    "godomey": (6.3958, 2.3336),
    "akpakpa": (6.3644, 2.4453),
    "parakou": (9.3372, 2.6303),
    "abomey": (7.1825, 1.9911),
    "cotonou": (6.3703, 2.3912),
}


def _normaliser(texte: str) -> str:
    remplacements = {"é": "e", "è": "e", "ê": "e", "ô": "o", "à": "a", "î": "i", "’": "-", "'": "-"}
    resultat = texte.lower()
    for accentue, simple in remplacements.items():
        resultat = resultat.replace(accentue, simple)
    return resultat


def _jitter(etablissement_id: str, amplitude: float = 0.015) -> tuple[float, float]:
    """Petit ecart deterministe (~± amplitude degres, de l'ordre du km) pour ne pas
    empiler plusieurs etablissements d'une meme ville exactement au meme point."""
    digest = hashlib.sha256(etablissement_id.encode()).hexdigest()
    dx = (int(digest[:8], 16) / 0xFFFFFFFF - 0.5) * 2 * amplitude
    dy = (int(digest[8:16], 16) / 0xFFFFFFFF - 0.5) * 2 * amplitude
    return dx, dy


def deviner_coordonnees(nom: str, etablissement_id: str) -> tuple[float, float]:
    nom_normalise = _normaliser(nom)

    base: tuple[float, float] | None = None
    for fragment, coords in INSTITUTIONS_CONNUES.items():
        if _normaliser(fragment) in nom_normalise:
            base = coords
            break
    if base is None:
        for ville, coords in VILLES_BENIN.items():
            if ville in nom_normalise:
                base = coords
                break
    if base is None:
        base = VILLES_BENIN["cotonou"]  # capitale economique : repli par defaut raisonnable

    dx, dy = _jitter(etablissement_id)
    return round(base[0] + dx, 6), round(base[1] + dy, 6)


def creer_etablissement_primaire(db, ctx: Contexte, cfg: Config, nom: str) -> Etablissement:
    etab_id = new_id()
    latitude, longitude = deviner_coordonnees(nom, etab_id)
    etab = Etablissement(
        id=etab_id, nom=nom, type=TypeEtablissement.EP,
        statut=ctx.rng.choice(list(StatutEtablissement)),
        code_etablissement=attribuer_code_etablissement(ctx, TypeEtablissement.EP),
        latitude=latitude, longitude=longitude,
    )
    add(db, etab)
    ctx.compter("etablissements")
    for niveau in NIVEAUX_MATERNEL_PRIMAIRE:
        _creer_classe(db, ctx, etab, niveau, MATIERES_PRIMAIRE[niveau], _capacite_pour(ctx, cfg))
    return etab


def creer_etablissement_secondaire(db, ctx: Contexte, cfg: Config, nom: str, technique: bool) -> Etablissement:
    etab_id = new_id()
    latitude, longitude = deviner_coordonnees(nom, etab_id)
    etab = Etablissement(
        id=etab_id, nom=nom, type=TypeEtablissement.ES,
        statut=ctx.rng.choice(list(StatutEtablissement)),
        code_etablissement=attribuer_code_etablissement(ctx, TypeEtablissement.ES),
        latitude=latitude, longitude=longitude,
    )
    add(db, etab)
    ctx.compter("etablissements")
    for niveau in NIVEAUX_SECONDAIRE_TRONC_COMMUN:
        _creer_classe(db, ctx, etab, niveau, MATIERES_TRONC_COMMUN, _capacite_pour(ctx, cfg))

    if technique:
        series_choisies = ctx.rng.sample(list(SERIES_TECHNIQUES), k=min(3, len(SERIES_TECHNIQUES)))
        for niveau_base in NIVEAUX_TECHNIQUE_2ND_CYCLE:
            for code in series_choisies:
                matieres = MATIERES_TECHNIQUE_COMMUN + MATIERES_PAR_SERIE_TECHNIQUE[code]
                _creer_classe(db, ctx, etab, f"{niveau_base} {code}", matieres, _capacite_pour(ctx, cfg))
    else:
        series_choisies = ctx.rng.sample(list(SERIES_GENERALES), k=min(3, len(SERIES_GENERALES)))
        for niveau_base in ["2nde", "1ère", "Terminale"]:
            for code in series_choisies:
                matieres = MATIERES_GENERAL_COMMUN + MATIERES_PAR_SERIE_GENERALE[code]
                _creer_classe(db, ctx, etab, f"{niveau_base} {code}", matieres, _capacite_pour(ctx, cfg))
    return etab


def creer_etablissement_universite(db, ctx: Contexte, cfg: Config, nom: str, public: bool) -> Etablissement:
    etab_id = new_id()
    latitude, longitude = deviner_coordonnees(nom, etab_id)
    etab = Etablissement(
        id=etab_id, nom=nom, type=TypeEtablissement.UP,
        statut=StatutEtablissement.PUBLIC if public else StatutEtablissement.PRIVE,
        code_etablissement=attribuer_code_etablissement(ctx, TypeEtablissement.UP),
        latitude=latitude, longitude=longitude,
    )
    add(db, etab)
    ctx.compter("etablissements")
    pool = FILIERES_UNIVERSITE_PUBLIC if public else FILIERES_UNIVERSITE_PRIVE
    filieres_choisies = ctx.rng.sample(list(pool), k=min(4, len(pool)))
    filieres_master = ctx.rng.sample(filieres_choisies, k=max(1, len(filieres_choisies) // 2))

    for filiere in filieres_choisies:
        matieres = pool[filiere]
        for niveau_base in ["1ère année de Licence", "2ème année de Licence", "3ème année de Licence"]:
            _creer_classe(db, ctx, etab, f"{niveau_base} - {filiere}", matieres, _capacite_pour(ctx, cfg))
    for filiere in filieres_master:
        matieres = pool[filiere]
        for niveau_base in ["1ère année de Master", "2ème année de Master"]:
            _creer_classe(db, ctx, etab, f"{niveau_base} - {filiere}", matieres, _capacite_pour(ctx, cfg))
    return etab


def creer_tous_les_etablissements(db, ctx: Contexte, cfg: Config) -> list[Etablissement]:
    etablissements: list[Etablissement] = []
    for i in range(cfg.n_ep):
        nom = NOMS_ETABLISSEMENTS_EP[i % len(NOMS_ETABLISSEMENTS_EP)]
        if i >= len(NOMS_ETABLISSEMENTS_EP):
            nom = f"{nom} ({i + 1})"
        etablissements.append(creer_etablissement_primaire(db, ctx, cfg, nom))

    for i in range(cfg.n_es):
        technique = i % 2 == 1
        pool = NOMS_ETABLISSEMENTS_ES_TECHNIQUE if technique else NOMS_ETABLISSEMENTS_ES_GENERAL
        idx = i // 2
        nom = pool[idx % len(pool)]
        if idx >= len(pool):
            nom = f"{nom} ({idx + 1})"
        etablissements.append(creer_etablissement_secondaire(db, ctx, cfg, nom, technique))

    for i in range(cfg.n_up):
        public = i % 2 == 0
        pool = NOMS_ETABLISSEMENTS_UP_PUBLIC if public else NOMS_ETABLISSEMENTS_UP_PRIVE
        idx = i // 2
        nom = pool[idx % len(pool)]
        if idx >= len(pool):
            nom = f"{nom} ({idx + 1})"
        etablissements.append(creer_etablissement_universite(db, ctx, cfg, nom, public))

    for etab in etablissements:
        nom_a, prenom_a, email_a = ctx.personne()
        admin = creer_utilisateur(
            db, ctx, role=RoleUtilisateur.ADMIN_ETABLISSEMENT, nom=nom_a, prenom=prenom_a, login_id=email_a, email=email_a
        )
        add(db, AdminEtablissement(utilisateur_id=admin.id, etablissement_id=etab.id))
        ctx.admins_etablissement.append(admin)
        ctx.admin_par_etablissement[etab.id] = admin

    return etablissements


# ═══════════════════════════════════════════════════════════════════════════
# Recrutement (UC-04 à UC-06) : postes, candidatures, casier judiciaire, contrats
# ═══════════════════════════════════════════════════════════════════════════

CASIER_CONTENU_SEED = b"Casier judiciaire vierge - document simule pour environnement de seed/test."


def _creer_candidature(db, ctx: Contexte, poste: Poste, etablissement: Etablissement) -> Utilisateur:
    enseignant = creer_enseignant_utilisateur(db, ctx)

    note_cv = ctx.rng.uniform(45, 100)
    note_diplome = ctx.rng.uniform(45, 100)
    echec_cv = ctx.rng.random() < 0.08
    echec_diplome = ctx.rng.random() < 0.08
    score_moyen = None
    if not echec_cv and not echec_diplome:
        score_moyen = round((note_cv + note_diplome) / 2, 1)

    if score_moyen is not None and score_moyen >= 65:
        statut_candidature = StatutCandidature.RETENUE
    elif echec_cv or echec_diplome or (score_moyen is not None and score_moyen < 50):
        statut_candidature = StatutCandidature.REJETEE
    else:
        statut_candidature = ctx.rng.choice([StatutCandidature.EN_EVALUATION, StatutCandidature.REJETEE])

    candidature = Candidature(
        id=new_id(), poste_id=poste.id, enseignant_id=enseignant.id,
        statut=statut_candidature, score=score_moyen,
    )
    add(db, candidature)
    ctx.compter("candidatures")

    add(db, DocumentCandidature(
        id=new_id(), candidature_id=candidature.id, type_document="cv",
        note_ia=None if echec_cv else round(note_cv, 1),
        statut=StatutDocument.ECHEC_NOTATION if echec_cv else StatutDocument.NOTE,
    ))
    add(db, DocumentCandidature(
        id=new_id(), candidature_id=candidature.id, type_document="diplome",
        note_ia=None if echec_diplome else round(note_diplome, 1),
        statut=StatutDocument.ECHEC_NOTATION if echec_diplome else StatutDocument.NOTE,
    ))
    ctx.compter("documents_candidature", 2)

    statut_casier = rng_choice_weighted(
        ctx.rng,
        [StatutVerificationCasier.CONFORME, StatutVerificationCasier.EN_ATTENTE, StatutVerificationCasier.NON_CONFORME],
        [0.8, 0.15, 0.05],
    )
    add(db, VerificationCasierJudiciaire(
        id=new_id(), candidature_id=candidature.id,
        contenu_chiffre=chiffrer_bytes(CASIER_CONTENU_SEED),
        nom_fichier="casier_judiciaire_seed.pdf",
        statut=statut_casier,
        date_verification=_utcnow() if statut_casier != StatutVerificationCasier.EN_ATTENTE else None,
    ))
    ctx.compter("verifications_casier_judiciaire")

    if statut_candidature == StatutCandidature.REJETEE and ctx.rng.random() < 0.35:
        decidee = ctx.rng.random() < 0.5
        statut_contestation = ctx.rng.choice([StatutContestation.ACCEPTEE, StatutContestation.REJETEE]) if decidee else StatutContestation.EN_ATTENTE
        add(db, Contestation(
            id=new_id(), candidature_id=candidature.id,
            motif=ctx.rng.choice(MOTIFS_CONTESTATION_RECRUTEMENT),
            statut=statut_contestation,
            motif_decision="Apres reexamen manuel des pieces, la decision initiale est maintenue/revisee." if decidee else None,
            decided_at=_utcnow() if decidee else None,
        ))
        ctx.compter("contestations")

    if statut_candidature == StatutCandidature.RETENUE:
        signe = ctx.rng.random() < 0.75
        contrat = Contrat(
            id=new_id(), candidature_id=candidature.id, enseignant_id=enseignant.id,
            etablissement_id=etablissement.id,
            syllabus=f"Programme pedagogique standard - {poste.titre}.",
            date_fin=date.today() + timedelta(days=ctx.rng.randint(180, 720)),
            statut=StatutContrat.SIGNE if signe else StatutContrat.EN_ATTENTE_SIGNATURE,
            signature_horodatage=_utcnow() if signe else None,
            signature_hash_document=uuid.uuid4().hex if signe else None,
            signature_image_lulufiles_id=None,
        )
        add(db, contrat)
        ctx.compter("contrats")
        if signe:
            ctx.enseignants_signes_par_etablissement.setdefault(etablissement.id, []).append(enseignant)
            ctx.tous_enseignants_signes.append(enseignant)
            ctx.contrats_signes.append(contrat)

    return enseignant


def creer_recrutement_pour_etablissement(db, ctx: Contexte, cfg: Config, etablissement: Etablissement) -> None:
    n_postes = ctx.rng.randint(*cfg.postes_par_etab)
    titres_postes = ["Professeur Titulaire", "Professeur Vacataire", "Enseignant Contractuel", "Chargé de Cours"]
    for _ in range(n_postes):
        poste = Poste(
            id=new_id(), etablissement_id=etablissement.id,
            titre=ctx.rng.choice(titres_postes),
            statut=StatutPoste.OUVERT,
        )
        add(db, poste)
        ctx.compter("postes")
        add(db, CritereDocumentPoste(id=new_id(), poste_id=poste.id, type_document="cv", coefficient=0.5, seuil_minimal=50))
        add(db, CritereDocumentPoste(id=new_id(), poste_id=poste.id, type_document="diplome", coefficient=0.5, seuil_minimal=50))
        ctx.compter("criteres_document_poste", 2)

        n_candidatures = ctx.rng.randint(*cfg.candidatures_par_poste)
        for _ in range(n_candidatures):
            _creer_candidature(db, ctx, poste, etablissement)

    if not ctx.enseignants_signes_par_etablissement.get(etablissement.id):
        # Garantie : chaque etablissement a besoin d'au moins un enseignant sous contrat
        # signe pour porter les cours/devoirs/sessions live de ses classes.
        poste_garantie = Poste(
            id=new_id(), etablissement_id=etablissement.id, titre="Professeur Titulaire", statut=StatutPoste.OUVERT
        )
        add(db, poste_garantie)
        ctx.compter("postes")
        add(db, CritereDocumentPoste(id=new_id(), poste_id=poste_garantie.id, type_document="cv", coefficient=1.0, seuil_minimal=0))
        ctx.compter("criteres_document_poste")

        enseignant = creer_enseignant_utilisateur(db, ctx)
        candidature = Candidature(
            id=new_id(), poste_id=poste_garantie.id, enseignant_id=enseignant.id,
            statut=StatutCandidature.RETENUE, score=95.0,
        )
        add(db, candidature)
        ctx.compter("candidatures")
        add(db, DocumentCandidature(
            id=new_id(), candidature_id=candidature.id, type_document="cv", note_ia=95.0, statut=StatutDocument.NOTE
        ))
        ctx.compter("documents_candidature")
        add(db, VerificationCasierJudiciaire(
            id=new_id(), candidature_id=candidature.id,
            contenu_chiffre=chiffrer_bytes(CASIER_CONTENU_SEED),
            nom_fichier="casier_judiciaire_seed.pdf",
            statut=StatutVerificationCasier.CONFORME, date_verification=_utcnow(),
        ))
        ctx.compter("verifications_casier_judiciaire")
        contrat = Contrat(
            id=new_id(), candidature_id=candidature.id, enseignant_id=enseignant.id,
            etablissement_id=etablissement.id, syllabus="Programme pedagogique standard.",
            date_fin=date.today() + timedelta(days=365), statut=StatutContrat.SIGNE,
            signature_horodatage=_utcnow(), signature_hash_document=uuid.uuid4().hex,
        )
        add(db, contrat)
        ctx.compter("contrats")
        ctx.enseignants_signes_par_etablissement.setdefault(etablissement.id, []).append(enseignant)
        ctx.tous_enseignants_signes.append(enseignant)
        ctx.contrats_signes.append(contrat)


# ═══════════════════════════════════════════════════════════════════════════
# Inscriptions (UC-02/UC-03) : élèves, tuteurs, comptes générés à la validation
# ═══════════════════════════════════════════════════════════════════════════

MOTIFS_REJET_INSCRIPTION = [
    "Dossier incomplet : pieces d'etat civil manquantes.",
    "Classe complete au moment du traitement du dossier.",
    "Justificatif de domicile non conforme.",
]


def _age_plausible(ctx: Contexte, niveau: str, type_etab: TypeEtablissement) -> date:
    if type_etab == TypeEtablissement.EP:
        age = ctx.rng.randint(4, 12)
    elif type_etab == TypeEtablissement.ES:
        est_second_cycle = any(k in niveau for k in ["2nde", "1ère", "Terminale", "lycée technique"])
        age = ctx.rng.randint(15, 19) if est_second_cycle else ctx.rng.randint(11, 16)
    else:
        age = ctx.rng.randint(18, 29)
    naissance = date.today() - timedelta(days=age * 365 + ctx.rng.randint(0, 364))
    return naissance


def creer_inscriptions_pour_classe(db, ctx: Contexte, cfg: Config, classe: Classe, etablissement: Etablissement) -> list[Eleve]:
    n_eleves = ctx.rng.randint(*cfg.eleves_par_classe)
    est_adulte = etablissement.type == TypeEtablissement.UP
    eleves_de_la_classe: list[Eleve] = []

    for _ in range(n_eleves):
        if ctx.tuteurs and ctx.rng.random() < 0.3:
            tuteur = ctx.rng.choice(ctx.tuteurs)
        else:
            tuteur = creer_tuteur(db, ctx)

        genre = ctx.rng.choice(["M", "F"])
        nom = ctx.rng.choice(NOMS_FAMILLE)
        prenom = ctx.rng.choice(PRENOMS_FEMININS if genre == "F" else PRENOMS_MASCULINS)
        nationalite = Nationalite.NATIONALE if ctx.rng.random() < 0.9 else Nationalite.ETRANGERE

        if est_adulte:
            statut = rng_choice_weighted(
                ctx.rng, [StatutInscription.VALIDEE, StatutInscription.SOUMISE, StatutInscription.REJETEE], [0.7, 0.2, 0.1]
            )
        else:
            statut = rng_choice_weighted(
                ctx.rng,
                [StatutInscription.VALIDEE, StatutInscription.SOUMISE, StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL, StatutInscription.REJETEE],
                [0.65, 0.15, 0.12, 0.08],
            )

        eleve = Eleve(
            id=new_id(), nom=nom, prenom=prenom,
            date_naissance=_age_plausible(ctx, classe.niveau, etablissement.type),
            nationalite=nationalite, tuteur_id=tuteur.id,
        )
        add(db, eleve)
        ctx.compter("eleves")

        horodatage = None
        motif_rejet = None
        if statut in (StatutInscription.SOUMISE, StatutInscription.VALIDEE) and not est_adulte:
            horodatage = _utcnow() - timedelta(days=ctx.rng.randint(1, 200))
        if statut == StatutInscription.REJETEE:
            motif_rejet = ctx.rng.choice(MOTIFS_REJET_INSCRIPTION)

        inscription = Inscription(
            id=new_id(), eleve_id=eleve.id, classe_id=classe.id, statut=statut,
            consentement_parental_horodatage=horodatage, motif_rejet=motif_rejet,
        )
        add(db, inscription)
        ctx.compter("inscriptions")

        if statut == StatutInscription.VALIDEE:
            matricule = attribuer_matricule(ctx, etablissement.type, nationalite)
            utilisateur_eleve = creer_utilisateur(
                db, ctx, role=RoleUtilisateur.ELEVE, nom=nom, prenom=prenom, login_id=matricule, email=None
            )
            eleve.matricule = matricule
            eleve.utilisateur_id = utilisateur_eleve.id

        eleves_de_la_classe.append(eleve)
        ctx.eleves_par_etablissement.setdefault(etablissement.id, []).append(eleve)

    return eleves_de_la_classe


# ═══════════════════════════════════════════════════════════════════════════
# Pédagogie (UC-06/UC-07/UC-14) : cours, quiz IA, assistant El Professor
# ═══════════════════════════════════════════════════════════════════════════

CONTENU_TEXTE_TEMPLATE = (
    "Ce cours introduit les notions fondamentales de {matiere}. Il couvre les definitions "
    "cles, des exemples resolus pas a pas, et se termine par une synthese des points a "
    "retenir avant l'evaluation. Les eleves sont invites a consulter El Professor pour "
    "toute question complementaire sur ce chapitre."
)
LULUFILES_ID_PLACEHOLDER = "00000000-0000-0000-0000-000000000000"


def creer_pedagogie_pour_classe(
    db, ctx: Contexte, cfg: Config, classe: Classe, enseignant: Utilisateur, eleves_avec_compte: list[Eleve]
) -> None:
    matieres = ctx.matieres_par_classe[classe.id]

    for i in range(cfg.cours_par_classe):
        matiere = ctx.rng.choice(matieres)
        format_cours = rng_choice_weighted(
            ctx.rng, [FormatCours.TEXTE, FormatCours.PDF, FormatCours.VIDEO, FormatCours.AUDIO], [0.7, 0.15, 0.1, 0.05]
        )
        cours = Cours(
            id=new_id(), classe_id=classe.id, enseignant_id=enseignant.id,
            titre=f"{matiere} — Séance {i + 1}", chapitre=matiere, format=format_cours,
            contenu_texte=CONTENU_TEXTE_TEMPLATE.format(matiere=matiere) if format_cours == FormatCours.TEXTE else None,
            lulufiles_file_id=None if format_cours == FormatCours.TEXTE else LULUFILES_ID_PLACEHOLDER,
        )
        add(db, cours)
        ctx.compter("cours")

        if format_cours != FormatCours.TEXTE or ctx.rng.random() >= 0.7:
            continue

        quiz = Quiz(id=new_id(), cours_id=cours.id, seuil_reussite=80.0)
        add(db, quiz)
        ctx.compter("quiz")
        questions_ids = []
        for q in range(5):
            question = QuestionQuiz(
                id=new_id(), quiz_id=quiz.id, ordre=q + 1,
                enonce=f"Question {q + 1} sur {matiere} (chapitre {i + 1})",
                choix=["Proposition A", "Proposition B", "Proposition C", "Proposition D"],
                reponse_correcte_index=ctx.rng.randint(0, 3),
            )
            add(db, question)
            questions_ids.append(question.reponse_correcte_index)
        ctx.compter("questions_quiz", 5)

        candidats = ctx.rng.sample(eleves_avec_compte, k=min(len(eleves_avec_compte), max(1, len(eleves_avec_compte) // 2)))
        for eleve in candidats:
            reponses = [
                idx if ctx.rng.random() < 0.65 else (idx + 1) % 4
                for idx in questions_ids
            ]
            score = round(100 * sum(1 for r, c in zip(reponses, questions_ids) if r == c) / len(questions_ids), 1)
            add(db, TentativeQuiz(
                id=new_id(), quiz_id=quiz.id, eleve_id=eleve.id, reponses=reponses,
                score=score, reussie=score >= 80.0,
            ))
            ctx.compter("tentatives_quiz")

        if eleves_avec_compte and ctx.rng.random() < 0.3:
            eleve = ctx.rng.choice(eleves_avec_compte)
            session_ep = SessionElProfessor(id=new_id(), eleve_utilisateur_id=eleve.utilisateur_id, cours_id=cours.id)
            add(db, session_ep)
            ctx.compter("sessions_el_professor")
            questions_el_prof = [
                "Peux-tu m'expliquer ce chapitre autrement ?",
                "Quel est le point le plus important a retenir ?",
                "As-tu un exemple concret pour illustrer ce cours ?",
            ]
            for question_texte in ctx.rng.sample(questions_el_prof, k=ctx.rng.randint(1, 2)):
                add(db, MessageElProfessor(
                    id=new_id(), session_id=session_ep.id, role=RoleMessageElProfessor.ELEVE, contenu=question_texte,
                ))
                add(db, MessageElProfessor(
                    id=new_id(), session_id=session_ep.id, role=RoleMessageElProfessor.ASSISTANT,
                    contenu=f"Bonne question ! Concernant {matiere}, l'essentiel est de bien maitriser les bases avant d'aller plus loin. N'hesite pas si tu as besoin d'un autre exemple.",
                ))
                ctx.compter("messages_el_professor", 2)


# ═══════════════════════════════════════════════════════════════════════════
# Évaluations (UC-08/UC-09) : devoirs, soumissions, référentiels, bulletins
# ═══════════════════════════════════════════════════════════════════════════

REPONSES_TYPES = [
    "Voici ma reponse detaillee a la question posee, avec les elements demandes.",
    "D'apres le cours, la reponse est la suivante, avec justification.",
    "Je pense que la reponse correcte est celle-ci, en me basant sur mes notes.",
]


def creer_evaluations_pour_classe(
    db, ctx: Contexte, cfg: Config, classe: Classe, etablissement: Etablissement, enseignant: Utilisateur,
    eleves_avec_compte: list[Eleve],
) -> None:
    matieres = ctx.matieres_par_classe[classe.id]

    for i in range(cfg.devoirs_par_classe):
        matiere = ctx.rng.choice(matieres)
        est_passe = ctx.rng.random() < 0.6
        date_limite = _utcnow() + timedelta(days=ctx.rng.randint(-45, -1) if est_passe else ctx.rng.randint(3, 30))
        devoir = Devoir(
            id=new_id(), classe_id=classe.id, enseignant_id=enseignant.id,
            titre=f"Devoir de {matiere} n°{i + 1}", matiere=matiere, date_limite=date_limite,
            bareme=ctx.rng.choice(list(BaremeDevoir)),
        )
        add(db, devoir)
        ctx.compter("devoirs")

        points_par_question = [8.0, 6.0, 6.0]
        questions = []
        for q, points in enumerate(points_par_question):
            question = QuestionDevoir(
                id=new_id(), devoir_id=devoir.id, ordre=q + 1,
                enonce=f"Question {q + 1} du devoir de {matiere}.",
                bareme_reponse=f"Reponse attendue couvrant les points cles du chapitre {matiere}.",
                points_max=points,
            )
            add(db, question)
            questions.append(question)
        ctx.compter("questions_devoir", len(questions))

        niveau_matiere = (classe.niveau, matiere)
        if niveau_matiere not in ctx.referentiels_valides:
            referentiel = ReferentielCoefficient(
                id=new_id(), niveau=classe.niveau, matiere=matiere,
                coefficient=round(ctx.rng.uniform(1.0, 4.0), 1), statut=StatutReferentiel.VALIDE,
            )
            add(db, referentiel)
            ctx.compter("referentiels_coefficients")
            ctx.referentiels_valides[niveau_matiere] = referentiel

        if not est_passe:
            continue

        candidats = ctx.rng.sample(eleves_avec_compte, k=min(len(eleves_avec_compte), max(1, round(len(eleves_avec_compte) * 0.75))))
        for eleve in candidats:
            statut_soumission = rng_choice_weighted(
                ctx.rng, [StatutSoumission.CORRIGEE, StatutSoumission.ECHEC_CORRECTION, StatutSoumission.EN_CORRECTION], [0.75, 0.15, 0.10]
            )
            soumission = Soumission(id=new_id(), devoir_id=devoir.id, eleve_id=eleve.id, statut=statut_soumission, note=None)
            add(db, soumission)
            ctx.compter("soumissions")

            total = 0.0
            for question in questions:
                points_obtenus = round(ctx.rng.uniform(0, question.points_max), 1) if statut_soumission == StatutSoumission.CORRIGEE else None
                if points_obtenus is not None:
                    total += points_obtenus
                add(db, ReponseSoumission(
                    id=new_id(), soumission_id=soumission.id, question_id=question.id,
                    texte_reponse=ctx.rng.choice(REPONSES_TYPES),
                    points_obtenus=points_obtenus,
                    commentaire_ia="Reponse globalement satisfaisante, quelques imprecisions." if points_obtenus is not None else None,
                ))
                ctx.compter("reponses_soumission")
            if statut_soumission == StatutSoumission.CORRIGEE:
                soumission.note = round(total, 1)

    for eleve in eleves_avec_compte:
        add(db, Bulletin(
            id=new_id(), eleve_id=eleve.id, classe_id=classe.id, periode="trimestre1",
            moyenne_generale=round(ctx.rng.uniform(8, 18), 2),
            decision_passage=None, valide_par_conseil=False,
        ))
        ctx.compter("bulletins")
        if ctx.rng.random() < 0.5:
            add(db, Bulletin(
                id=new_id(), eleve_id=eleve.id, classe_id=classe.id, periode="trimestre2",
                moyenne_generale=round(ctx.rng.uniform(8, 18), 2),
                decision_passage=None, valide_par_conseil=False,
            ))
            ctx.compter("bulletins")


# ═══════════════════════════════════════════════════════════════════════════
# Actes académiques (UC-10)
# ═══════════════════════════════════════════════════════════════════════════

CATALOGUE_ACTES = [
    ("Attestation de scolarité", 0, "Aucune piece requise."),
    ("Relevé de notes", 1000, "Photocopie de la carte d'eleve."),
    ("Certificat de réussite", 1500, "Photocopie de la carte d'eleve, photo d'identite."),
    ("Diplôme", 5000, "Photocopie piece d'identite, quittance de scolarite."),
    ("Duplicata de diplôme", 7500, "Declaration de perte, photocopie piece d'identite."),
]
MOTIFS_REJET_ACTE = [
    "Piece jointe illisible, veuillez soumettre une nouvelle demande.",
    "Dossier academique incomplet pour la periode demandee.",
]


def creer_actes_pour_etablissement(db, ctx: Contexte, cfg: Config, etablissement: Etablissement) -> None:
    catalogue = ctx.rng.sample(CATALOGUE_ACTES, k=min(cfg.types_actes_par_etab, len(CATALOGUE_ACTES)))
    types_crees = []
    for nom, prix, pieces in catalogue:
        type_acte = TypeActeAcademique(
            id=new_id(), etablissement_id=etablissement.id, nom=nom, prix=float(prix), pieces_requises=pieces,
        )
        add(db, type_acte)
        ctx.compter("types_acte_academique")
        types_crees.append(type_acte)

    eleves_de_l_etab = [e for e in ctx.eleves_par_etablissement.get(etablissement.id, []) if e.utilisateur_id]
    n_demandes = max(0, round(len(eleves_de_l_etab) * cfg.demandes_actes_ratio))
    for eleve in ctx.rng.sample(eleves_de_l_etab, k=min(n_demandes, len(eleves_de_l_etab))):
        est_reclamation = ctx.rng.random() < 0.2
        statut = rng_choice_weighted(
            ctx.rng,
            [StatutDemandeActe.SOUMISE, StatutDemandeActe.EN_TRAITEMENT, StatutDemandeActe.ACCEPTEE, StatutDemandeActe.REJETEE],
            [0.25, 0.15, 0.45, 0.15],
        )
        type_acte = None if est_reclamation else ctx.rng.choice(types_crees)
        paiement_confirme = (not est_reclamation and type_acte.prix == 0) or (
            statut in (StatutDemandeActe.EN_TRAITEMENT, StatutDemandeActe.ACCEPTEE) and ctx.rng.random() < 0.9
        )
        add(db, DemandeActeAcademique(
            id=new_id(), eleve_id=eleve.id,
            type_acte_id=type_acte.id if type_acte else None,
            est_reclamation=est_reclamation,
            reference_evaluation=f"DEV-{ctx.rng.randint(1000, 9999)}" if est_reclamation else None,
            motif="Je conteste la note attribuee a ce devoir, ma reponse etait complete." if est_reclamation else None,
            statut=statut, paiement_confirme=paiement_confirme,
            kkiapay_transaction_id=f"seed-tx-{new_id()}" if paiement_confirme else None,
            motif_rejet=ctx.rng.choice(MOTIFS_REJET_ACTE) if statut == StatutDemandeActe.REJETEE else None,
        ))
        ctx.compter("demandes_acte_academique")


# ═══════════════════════════════════════════════════════════════════════════
# Messagerie (UC-13) : groupe classe, DM tuteur↔enfant, signalements
# ═══════════════════════════════════════════════════════════════════════════

MESSAGES_GROUPE_CLASSE = [
    "Bonjour a tous, n'oubliez pas le devoir pour la semaine prochaine.",
    "Est-ce que quelqu'un peut me rappeler la date de l'evaluation ?",
    "Merci pour le cours d'aujourd'hui, tres clair !",
    "Je serai absent(e) demain, quelqu'un peut me passer les notes ?",
    "Rappel : reunion de parents d'eleves vendredi a 17h.",
    "Bon courage a tous pour les revisions !",
]
MESSAGES_DM = [
    "Bonjour, comment se passe ta journee a l'ecole ?",
    "N'oublie pas d'apporter ton materiel de sport demain.",
    "Tes resultats du dernier devoir sont excellents, bravo !",
    "As-tu besoin d'aide pour tes devoirs ce soir ?",
    "Je viendrai te chercher un peu plus tard aujourd'hui.",
]


def creer_messagerie_groupe_classe(
    db, ctx: Contexte, classe: Classe, etablissement: Etablissement, enseignant: Utilisateur, eleves_avec_compte: list[Eleve]
) -> None:
    conversation_id = ctx.conversation_groupe_par_classe[classe.id]
    auteurs_possibles = [enseignant.id] + [e.utilisateur_id for e in eleves_avec_compte]
    if not auteurs_possibles:
        return

    messages_crees = []
    for _ in range(ctx.rng.randint(3, 8)):
        message = Message(
            id=new_id(), conversation_id=conversation_id, auteur_id=ctx.rng.choice(auteurs_possibles),
            contenu=ctx.rng.choice(MESSAGES_GROUPE_CLASSE),
            created_at=_utcnow() - timedelta(days=ctx.rng.randint(0, 60), hours=ctx.rng.randint(0, 23)),
        )
        add(db, message)
        messages_crees.append(message)
    ctx.compter("messages", len(messages_crees))

    if messages_crees and ctx.rng.random() < 0.15:
        message_signale = ctx.rng.choice(messages_crees)
        traite = ctx.rng.random() < 0.6
        admin = ctx.admin_par_etablissement.get(etablissement.id)
        add(db, SignalementMessage(
            id=new_id(), message_id=message_signale.id,
            signale_par_id=ctx.rng.choice(auteurs_possibles),
            traite=traite,
            decision="Message examine, avertissement donne a l'eleve concerne." if traite else None,
            traite_par_id=admin.id if traite and admin else None,
        ))
        ctx.compter("signalements_message")


def creer_dm_tuteur_enfant(db, ctx: Contexte, eleve: Eleve, tuteur_utilisateur_id: str) -> None:
    if ctx.rng.random() >= 0.6:
        return
    conversation_id = new_id()
    add(db, Conversation(id=conversation_id, type=TypeConversation.DM, classe_id=None))
    ctx.compter("conversations")
    add(db, ParticipantConversation(conversation_id=conversation_id, utilisateur_id=tuteur_utilisateur_id))
    add(db, ParticipantConversation(conversation_id=conversation_id, utilisateur_id=eleve.utilisateur_id))
    ctx.compter("participants_conversation", 2)

    participants = [tuteur_utilisateur_id, eleve.utilisateur_id]
    n_messages = ctx.rng.randint(2, 6)
    for i in range(n_messages):
        add(db, Message(
            id=new_id(), conversation_id=conversation_id, auteur_id=participants[i % 2],
            contenu=ctx.rng.choice(MESSAGES_DM),
            created_at=_utcnow() - timedelta(days=ctx.rng.randint(0, 60), hours=ctx.rng.randint(0, 23)),
        ))
    ctx.compter("messages", n_messages)


# ═══════════════════════════════════════════════════════════════════════════
# Cours en direct (UC-16) : sessions live, consentement caméra, participations
# ═══════════════════════════════════════════════════════════════════════════

def creer_consentements_camera(db, ctx: Contexte, eleves_avec_compte: list[Eleve]) -> None:
    for eleve in eleves_avec_compte:
        if ctx.rng.random() < 0.5:
            add(db, ConsentementCameraLive(id=new_id(), eleve_utilisateur_id=eleve.utilisateur_id, tuteur_id=eleve.tuteur_id))
            ctx.compter("consentements_camera_live")
            ctx.consentements_camera_donnes.add(eleve.utilisateur_id)


def creer_sessions_live_pour_classe(
    db, ctx: Contexte, cfg: Config, classe: Classe, enseignant: Utilisateur, eleves_avec_compte: list[Eleve]
) -> None:
    for _ in range(cfg.sessions_live_par_classe):
        statut = rng_choice_weighted(
            ctx.rng, [StatutSessionLive.PLANIFIEE, StatutSessionLive.EN_COURS, StatutSessionLive.TERMINEE], [0.3, 0.1, 0.6]
        )
        if statut == StatutSessionLive.TERMINEE:
            date_heure = _utcnow() - timedelta(days=ctx.rng.randint(1, 60))
        elif statut == StatutSessionLive.EN_COURS:
            date_heure = _utcnow() - timedelta(minutes=ctx.rng.randint(5, 40))
        else:
            date_heure = _utcnow() + timedelta(days=ctx.rng.randint(1, 30))

        session_live = SessionLive(id=new_id(), classe_id=classe.id, enseignant_id=enseignant.id, date_heure=date_heure, statut=statut)
        add(db, session_live)
        ctx.compter("sessions_live")

        if statut != StatutSessionLive.PLANIFIEE and eleves_avec_compte:
            participants = ctx.rng.sample(
                eleves_avec_compte, k=min(len(eleves_avec_compte), max(1, round(len(eleves_avec_compte) * 0.5)))
            )
            for eleve in participants:
                add(db, ParticipationLive(
                    id=new_id(), session_id=session_live.id, eleve_utilisateur_id=eleve.utilisateur_id,
                    camera_autorisee=eleve.utilisateur_id in ctx.consentements_camera_donnes,
                ))
                ctx.compter("participations_live")


# ═══════════════════════════════════════════════════════════════════════════
# Transport & cantine (UC-11/UC-12) + contrôleurs (UC-11/12/17)
# ═══════════════════════════════════════════════════════════════════════════

NOMS_LIGNES_TRANSPORT = [
    "Ligne A - Centre-ville", "Ligne B - Zone périphérique", "Ligne C - Quartier résidentiel", "Ligne D - Axe principal",
]
NOMS_REPAS_CANTINE = ["Petit-déjeuner", "Déjeuner complet", "Goûter", "Menu végétarien"]


def creer_services_scolaires_pour_etablissement(db, ctx: Contexte, cfg: Config, etablissement: Etablissement) -> None:
    eleves = [e for e in ctx.eleves_par_etablissement.get(etablissement.id, []) if e.utilisateur_id]
    if not eleves:
        return

    lignes = []
    for nom in ctx.rng.sample(NOMS_LIGNES_TRANSPORT, k=min(cfg.lignes_transport_par_etab, len(NOMS_LIGNES_TRANSPORT))):
        ligne = LigneTransport(
            id=new_id(), etablissement_id=etablissement.id, nom=nom,
            prix=float(ctx.rng.choice([500, 750, 1000, 1500])), capacite_par_trajet=ctx.rng.randint(20, 50),
        )
        add(db, ligne)
        ctx.compter("lignes_transport")
        lignes.append(ligne)

    types_repas = []
    for nom in ctx.rng.sample(NOMS_REPAS_CANTINE, k=min(cfg.types_cantine_par_etab, len(NOMS_REPAS_CANTINE))):
        type_repas = TypeRepasCantine(
            id=new_id(), etablissement_id=etablissement.id, nom=nom,
            prix=float(ctx.rng.choice([300, 500, 750])), capacite_par_jour=ctx.rng.randint(30, 100),
        )
        add(db, type_repas)
        ctx.compter("types_repas_cantine")
        types_repas.append(type_repas)

    for ligne in lignes:
        for _ in range(cfg.tickets_par_service):
            eleve = ctx.rng.choice(eleves)
            statut = rng_choice_weighted(ctx.rng, [StatutTicket.ACHETE, StatutTicket.VALIDE, StatutTicket.REMBOURSE], [0.5, 0.4, 0.1])
            paiement_confirme = statut != StatutTicket.ACHETE or ctx.rng.random() < 0.5
            add(db, TicketTransport(
                id=new_id(), ligne_id=ligne.id, utilisateur_id=eleve.utilisateur_id,
                date_trajet=date.today() + timedelta(days=ctx.rng.randint(-30, 30)),
                statut=statut, prix_paye=ligne.prix, paiement_confirme=paiement_confirme,
                kkiapay_transaction_id=f"seed-tx-{new_id()}" if paiement_confirme else None,
            ))
            ctx.compter("tickets_transport")

    for type_repas in types_repas:
        for _ in range(cfg.tickets_par_service):
            eleve = ctx.rng.choice(eleves)
            statut = rng_choice_weighted(ctx.rng, [StatutTicket.ACHETE, StatutTicket.VALIDE, StatutTicket.REMBOURSE], [0.5, 0.4, 0.1])
            paiement_confirme = statut != StatutTicket.ACHETE or ctx.rng.random() < 0.5
            add(db, TicketCantine(
                id=new_id(), type_repas_id=type_repas.id, utilisateur_id=eleve.utilisateur_id,
                date_service=date.today() + timedelta(days=ctx.rng.randint(-30, 30)),
                statut=statut, prix_paye=type_repas.prix, paiement_confirme=paiement_confirme,
                kkiapay_transaction_id=f"seed-tx-{new_id()}" if paiement_confirme else None,
            ))
            ctx.compter("tickets_cantine")

    enseignants_locaux = ctx.enseignants_signes_par_etablissement.get(etablissement.id, [])
    admin = ctx.admin_par_etablissement.get(etablissement.id)
    controleur = ctx.rng.choice(enseignants_locaux) if enseignants_locaux else admin
    if controleur:
        add(db, DesignationControleur(id=new_id(), etablissement_id=etablissement.id, utilisateur_id=controleur.id, service=ServiceControle.TRANSPORT))
        add(db, DesignationControleur(id=new_id(), etablissement_id=etablissement.id, utilisateur_id=controleur.id, service=ServiceControle.CANTINE))
        ctx.compter("designations_controleur", 2)


# ═══════════════════════════════════════════════════════════════════════════
# Billetterie (UC-17)
# ═══════════════════════════════════════════════════════════════════════════

def creer_billetterie_pour_etablissement(db, ctx: Contexte, cfg: Config, etablissement: Etablissement) -> None:
    eleves_locaux = [e for e in ctx.eleves_par_etablissement.get(etablissement.id, []) if e.utilisateur_id]
    enseignants_locaux = ctx.enseignants_signes_par_etablissement.get(etablissement.id, [])
    admin = ctx.admin_par_etablissement.get(etablissement.id)

    pool_utilisateurs = list({
        *(e.utilisateur_id for e in eleves_locaux),
        *(e.tuteur_id for e in eleves_locaux),
        *(ens.id for ens in enseignants_locaux),
        *([admin.id] if admin else []),
    })
    if not pool_utilisateurs:
        return

    for _ in range(cfg.evenements_par_etab):
        titre = ctx.rng.choice(TITRES_EVENEMENTS)
        statut_evenement = StatutEvenement.ANNULE if ctx.rng.random() < 0.1 else StatutEvenement.OUVERT
        prix = float(ctx.rng.choice([0, 500, 1000, 2000]))
        parrain_id = ctx.rng.choice(enseignants_locaux).id if enseignants_locaux and ctx.rng.random() < 0.5 else None

        evenement = Evenement(
            id=new_id(), etablissement_id=etablissement.id, titre=titre,
            description=f"{titre}, organisé par l'établissement et ouvert à toute la communauté scolaire.",
            lieu="Cour principale de l'établissement",
            date_heure=_utcnow() + timedelta(days=ctx.rng.randint(-10, 60)),
            capacite_max=ctx.rng.randint(50, 300), prix_billet=prix, statut=statut_evenement,
            parrain_utilisateur_id=parrain_id,
        )
        add(db, evenement)
        ctx.compter("evenements")

        acheteurs = ctx.rng.sample(pool_utilisateurs, k=min(len(pool_utilisateurs), cfg.billets_par_evenement))
        for utilisateur_id in acheteurs:
            if statut_evenement == StatutEvenement.ANNULE:
                statut_billet = StatutBillet.REMBOURSE
            else:
                statut_billet = rng_choice_weighted(ctx.rng, [StatutBillet.ACHETE, StatutBillet.VALIDE], [0.5, 0.5])
            paiement_confirme = prix == 0 or statut_billet == StatutBillet.VALIDE or ctx.rng.random() < 0.6
            add(db, BilletEvenement(
                id=new_id(), evenement_id=evenement.id, utilisateur_id=utilisateur_id,
                statut=statut_billet, prix_paye=prix, paiement_confirme=paiement_confirme,
                kkiapay_transaction_id=f"seed-tx-{new_id()}" if paiement_confirme and prix > 0 else None,
            ))
            ctx.compter("billets_evenement")

        if enseignants_locaux and statut_evenement == StatutEvenement.OUVERT:
            add(db, DesignationControleur(
                id=new_id(), etablissement_id=etablissement.id, utilisateur_id=ctx.rng.choice(enseignants_locaux).id,
                service=ServiceControle.EVENEMENT, evenement_id=evenement.id,
            ))
            ctx.compter("designations_controleur")


# ═══════════════════════════════════════════════════════════════════════════
# Visites virtuelles (UC-19) : table backend peuplée même si le frontend
# affiche volontairement un simple "Bientôt disponible" pour cette fonctionnalité.
# ═══════════════════════════════════════════════════════════════════════════

def creer_visite_virtuelle(db, ctx: Contexte, etablissement: Etablissement) -> None:
    add(db, VisiteVirtuelle(
        id=new_id(), etablissement_id=etablissement.id, type=ctx.rng.choice(list(TypeVisiteVirtuelle)),
        lien_externe=f"https://visites.luluschools.test/{etablissement.code_etablissement.lower()}",
        attestation_autorisation=ctx.rng.random() < 0.9,
    ))
    ctx.compter("visites_virtuelles")


# ═══════════════════════════════════════════════════════════════════════════
# Micro-jobs (UC-18) : place de marché communautaire, séquestre, arbitrage
# ═══════════════════════════════════════════════════════════════════════════

def creer_micro_jobs(db, ctx: Contexte, cfg: Config) -> None:
    pool = list(ctx.tous_enseignants_signes) + list(ctx.tuteurs) + list(ctx.admins_etablissement)
    if ctx.admin_ministeriel:
        pool.append(ctx.admin_ministeriel)
    if len(pool) < 2:
        return

    offres = []
    for _ in range(cfg.n_offres_micro_job):
        client = ctx.rng.choice(pool)
        offre = OffreMicroJob(
            id=new_id(), client_id=client.id, titre=ctx.rng.choice(TITRES_OFFRES_MICRO_JOB),
            description="Service proposé par un membre de la communauté LuluSchools, disponible immédiatement.",
            prix=float(ctx.rng.choice([2000, 3500, 5000, 7500, 10000])), statut=StatutOffreMicroJob.OUVERTE,
            paiement_confirme=True, kkiapay_transaction_id=f"seed-tx-{new_id()}",
        )
        add(db, offre)
        ctx.compter("offres_micro_job")
        offres.append((offre, client))

    for offre, client in offres:
        if ctx.rng.random() >= 0.65:
            continue
        candidats_prestataire = [u for u in pool if u.id != client.id]
        if not candidats_prestataire:
            continue
        prestataire = ctx.rng.choice(candidats_prestataire)
        offre.statut = StatutOffreMicroJob.FERMEE

        statut_mission = rng_choice_weighted(
            ctx.rng,
            [
                StatutMissionMicroJob.EN_COURS, StatutMissionMicroJob.TERMINEE_DECLAREE, StatutMissionMicroJob.VALIDEE,
                StatutMissionMicroJob.CONTESTEE, StatutMissionMicroJob.REMBOURSEE, StatutMissionMicroJob.PAYEE,
            ],
            [0.15, 0.15, 0.25, 0.15, 0.1, 0.2],
        )
        date_declaration_fin = None
        date_limite_validation = None
        reference_paiement = None
        if statut_mission != StatutMissionMicroJob.EN_COURS:
            date_declaration_fin = _utcnow() - timedelta(days=ctx.rng.randint(1, 20))
            date_limite_validation = date_declaration_fin + timedelta(days=5)
        if statut_mission == StatutMissionMicroJob.PAYEE:
            reference_paiement = f"MOMO-{ctx.rng.randint(100000, 999999)}"

        mission = MissionMicroJob(
            id=new_id(), offre_id=offre.id, prestataire_id=prestataire.id, statut=statut_mission,
            prix_paye=offre.prix, paiement_confirme=True,
            kkiapay_transaction_id=offre.kkiapay_transaction_id,
            date_declaration_fin=date_declaration_fin, date_limite_validation=date_limite_validation,
            reference_paiement_prestataire=reference_paiement,
        )
        add(db, mission)
        ctx.compter("missions_micro_job")

        if statut_mission == StatutMissionMicroJob.CONTESTEE:
            if ctx.rng.random() < 0.3:
                mission.statut = StatutMissionMicroJob.VALIDEE
                add(db, ContestationMicroJob(
                    id=new_id(), mission_id=mission.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MICRO_JOB),
                    statut=StatutContestationMicroJob.REJETEE,
                    decision_motif="Contestation jugee non fondee apres examen, la mission est validee.",
                    decision_par_id=ctx.admin_ministeriel.id if ctx.admin_ministeriel else None,
                ))
            else:
                add(db, ContestationMicroJob(
                    id=new_id(), mission_id=mission.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MICRO_JOB),
                    statut=StatutContestationMicroJob.EN_ATTENTE,
                ))
            ctx.compter("contestations_micro_job")
        elif statut_mission == StatutMissionMicroJob.REMBOURSEE:
            add(db, ContestationMicroJob(
                id=new_id(), mission_id=mission.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MICRO_JOB),
                statut=StatutContestationMicroJob.ACCEPTEE,
                decision_motif="Contestation jugee fondee, le client est rembourse.",
                decision_par_id=ctx.admin_ministeriel.id if ctx.admin_ministeriel else None,
            ))
            ctx.compter("contestations_micro_job")


# ═══════════════════════════════════════════════════════════════════════════
# Marketplace étudiante (UC-20/21/22) : annonces, photos, signalements, séquestre
# ═══════════════════════════════════════════════════════════════════════════

# Seuil identique a AGE_MAJORITE_NUMERIQUE (app/modules/inscriptions/router.py, Art. 446) :
# duplique ici plutot que d'importer un module de router dans un script de seed, qui ne
# depend sinon que de modules `models` purs.
AGE_MINIMUM_MARKETPLACE = 16


def _age_plausible_est_majeur_numerique(date_naissance: date) -> bool:
    aujourd_hui = date.today()
    age = aujourd_hui.year - date_naissance.year
    if (aujourd_hui.month, aujourd_hui.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age >= AGE_MINIMUM_MARKETPLACE

TITRES_ANNONCES_MARKETPLACE: dict[CategorieAnnonce, list[str]] = {
    CategorieAnnonce.FOURNITURES_SCOLAIRES: [
        "Lot de cahiers 100 pages", "Trousse complète avec compas", "Sac à dos scolaire", "Ramette de feuilles simples",
    ],
    CategorieAnnonce.MANUELS_LIVRES: [
        "Manuel de Mathématiques Terminale D", "Livre de Français 3ème", "Manuel de Physique-Chimie", "Dictionnaire Larousse",
    ],
    CategorieAnnonce.VETEMENTS_UNIFORMES: [
        "Uniforme complet taille M", "Blouse d'EPS", "Chaussures de sport pointure 42", "Blazer d'établissement",
    ],
    CategorieAnnonce.ELECTRONIQUE: [
        "Calculatrice scientifique Casio", "Clé USB 32 Go", "Écouteurs filaires", "Chargeur de téléphone",
    ],
    CategorieAnnonce.AUTRE: [
        "Vélo d'occasion", "Ballon de football", "Montre étudiante", "Cadenas de casier",
    ],
}
MOTIFS_SIGNALEMENT_ANNONCE = [
    "Prix anormalement bas, doute sur l'authenticité de l'annonce.",
    "Photo ne correspond pas à la description.",
    "Annonce en double publiée par erreur.",
]
MOTIFS_CONTESTATION_MARKETPLACE = [
    "L'article reçu ne correspond pas du tout à la description de l'annonce.",
    "L'article reçu est dans un état bien pire qu'annoncé.",
    "Remise jamais effectuée malgré la déclaration du vendeur.",
]

# Statuts non terminaux d'une transaction : l'annonce liée doit rester "reservee",
# jamais "disponible" - coherent avec le router (voir _STATUTS_TRANSACTION_EN_COURS
# dans app/modules/marketplace/router.py, ici etendu a CONFIRMEE qui attend encore
# le reversement au vendeur avant de devenir VENDUE).
_STATUTS_TRANSACTION_RESERVE_ANNONCE = (
    StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT,
    StatutTransactionMarketplace.PAIEMENT_CONFIRME,
    StatutTransactionMarketplace.REMISE_DECLAREE,
    StatutTransactionMarketplace.CONTESTEE,
    StatutTransactionMarketplace.CONFIRMEE,
)


def creer_marketplace_pour_etablissement(db, ctx: Contexte, cfg: Config, etablissement: Etablissement) -> None:
    eleves_eligibles = [
        e
        for e in ctx.eleves_par_etablissement.get(etablissement.id, [])
        if e.utilisateur_id and _age_plausible_est_majeur_numerique(e.date_naissance)
    ]
    if len(eleves_eligibles) < 2:
        return
    admin = ctx.admin_par_etablissement.get(etablissement.id)

    annonces_avec_vendeur = []
    for _ in range(cfg.annonces_marketplace_par_etab):
        categorie = ctx.rng.choice(list(CategorieAnnonce))
        vendeur = ctx.rng.choice(eleves_eligibles)
        titre = ctx.rng.choice(TITRES_ANNONCES_MARKETPLACE[categorie])

        annonce = AnnonceMarketplace(
            id=new_id(), etablissement_id=etablissement.id, vendeur_id=vendeur.utilisateur_id,
            titre=titre,
            description=f"{titre}, proposé par un élève de l'établissement, remise en main propre uniquement.",
            categorie=categorie, etat=ctx.rng.choice(list(EtatArticle)),
            prix=float(ctx.rng.choice([500, 1000, 1500, 2500, 5000, 7500, 10000, 15000])),
            statut=StatutAnnonce.DISPONIBLE,
        )
        add(db, annonce)
        ctx.compter("annonces_marketplace")
        add(db, PhotoAnnonceMarketplace(id=new_id(), annonce_id=annonce.id, lulufiles_file_id=LULUFILES_ID_PLACEHOLDER, ordre=0))
        ctx.compter("photos_annonce_marketplace")
        annonces_avec_vendeur.append((annonce, vendeur))

        if ctx.rng.random() < 0.15:
            candidats_signaleur = [e for e in eleves_eligibles if e.utilisateur_id != vendeur.utilisateur_id]
            signaleur = ctx.rng.choice(candidats_signaleur) if candidats_signaleur else vendeur
            traite = ctx.rng.random() < 0.6
            add(db, SignalementAnnonceMarketplace(
                id=new_id(), annonce_id=annonce.id, signale_par_id=signaleur.utilisateur_id,
                traite=traite,
                decision="Annonce examinée, conforme aux règles de la plateforme." if traite else None,
                traite_par_id=admin.id if traite and admin else None,
            ))
            ctx.compter("signalements_annonce_marketplace")

    for annonce, vendeur in annonces_avec_vendeur:
        if ctx.rng.random() >= 0.6:
            continue
        candidats_acheteur = [e for e in eleves_eligibles if e.utilisateur_id != vendeur.utilisateur_id]
        if not candidats_acheteur:
            continue
        acheteur = ctx.rng.choice(candidats_acheteur)

        statut_transaction = rng_choice_weighted(
            ctx.rng,
            [
                StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT, StatutTransactionMarketplace.PAIEMENT_CONFIRME,
                StatutTransactionMarketplace.REMISE_DECLAREE, StatutTransactionMarketplace.CONFIRMEE,
                StatutTransactionMarketplace.CONTESTEE, StatutTransactionMarketplace.FINALISEE,
                StatutTransactionMarketplace.REMBOURSEE, StatutTransactionMarketplace.ANNULEE,
            ],
            [0.1, 0.1, 0.15, 0.15, 0.1, 0.25, 0.1, 0.05],
        )
        paiement_confirme = statut_transaction != StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT
        date_remise_declaree = None
        date_limite_confirmation = None
        reference_paiement_vendeur = None
        if statut_transaction in (
            StatutTransactionMarketplace.REMISE_DECLAREE, StatutTransactionMarketplace.CONFIRMEE,
            StatutTransactionMarketplace.CONTESTEE, StatutTransactionMarketplace.FINALISEE,
            StatutTransactionMarketplace.REMBOURSEE,
        ):
            date_remise_declaree = _utcnow() - timedelta(days=ctx.rng.randint(1, 20))
            date_limite_confirmation = date_remise_declaree + timedelta(days=5)
        if statut_transaction == StatutTransactionMarketplace.FINALISEE:
            reference_paiement_vendeur = f"MOMO-{ctx.rng.randint(100000, 999999)}"

        transaction = TransactionMarketplace(
            id=new_id(), annonce_id=annonce.id, acheteur_id=acheteur.utilisateur_id,
            statut=statut_transaction, prix_paye=annonce.prix, paiement_confirme=paiement_confirme,
            kkiapay_transaction_id=f"seed-tx-{new_id()}" if paiement_confirme else None,
            date_remise_declaree=date_remise_declaree, date_limite_confirmation=date_limite_confirmation,
            reference_paiement_vendeur=reference_paiement_vendeur,
        )
        add(db, transaction)
        ctx.compter("transactions_marketplace")

        if statut_transaction == StatutTransactionMarketplace.CONTESTEE:
            if ctx.rng.random() < 0.35:
                # Litige deja tranche par l'A+ en defaveur de l'acheteur (meme schema
                # que la contestation micro-job rejetee, UC-18) : la transaction repasse
                # CONFIRMEE, prete pour le reversement au vendeur.
                transaction.statut = StatutTransactionMarketplace.CONFIRMEE
                add(db, ContestationMarketplace(
                    id=new_id(), transaction_id=transaction.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MARKETPLACE),
                    statut=StatutContestationMarketplace.REJETEE,
                    decision_motif="Contestation jugée non fondée après examen, la transaction est confirmée.",
                    decision_par_id=admin.id if admin else None,
                ))
            else:
                add(db, ContestationMarketplace(
                    id=new_id(), transaction_id=transaction.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MARKETPLACE),
                    statut=StatutContestationMarketplace.EN_ATTENTE,
                ))
            ctx.compter("contestations_marketplace")
        elif statut_transaction == StatutTransactionMarketplace.REMBOURSEE:
            add(db, ContestationMarketplace(
                id=new_id(), transaction_id=transaction.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_MARKETPLACE),
                statut=StatutContestationMarketplace.ACCEPTEE,
                decision_motif="Contestation jugée fondée, l'acheteur est remboursé.",
                decision_par_id=admin.id if admin else None,
            ))
            ctx.compter("contestations_marketplace")

        if statut_transaction in _STATUTS_TRANSACTION_RESERVE_ANNONCE:
            annonce.statut = StatutAnnonce.RESERVEE
        elif statut_transaction == StatutTransactionMarketplace.FINALISEE:
            annonce.statut = StatutAnnonce.VENDUE
        # ANNULEE et REMBOURSEE : l'annonce redevient DISPONIBLE (deja sa valeur par
        # defaut a la creation, rien a modifier).


def creer_propositions_reconduction(db, ctx: Contexte) -> None:
    if len(ctx.contrats_signes) < 2:
        return
    for contrat in ctx.rng.sample(ctx.contrats_signes, k=min(20, len(ctx.contrats_signes))):
        statut = rng_choice_weighted(
            ctx.rng, [StatutProposition.EN_ATTENTE, StatutProposition.ACCEPTEE, StatutProposition.REFUSEE], [0.4, 0.4, 0.2]
        )
        nouveau_contrat_id = None
        if statut == StatutProposition.ACCEPTEE:
            nouveau_contrat = add(db, Contrat(
                id=new_id(), candidature_id=contrat.candidature_id, enseignant_id=contrat.enseignant_id,
                etablissement_id=contrat.etablissement_id, syllabus=contrat.syllabus,
                date_fin=contrat.date_fin + timedelta(days=365), statut=StatutContrat.SIGNE,
                signature_horodatage=_utcnow(), signature_hash_document=uuid.uuid4().hex,
            ))
            ctx.compter("contrats")
            nouveau_contrat_id = nouveau_contrat.id
        add(db, PropositionReconduction(
            id=new_id(), contrat_precedent_id=contrat.id, nouveau_contrat_id=nouveau_contrat_id, statut=statut,
        ))
        ctx.compter("propositions_reconduction")


def creer_propositions_referentiel(db, ctx: Contexte, etablissements: list[Etablissement]) -> None:
    candidats = list(ctx.referentiels_valides.values())
    if not candidats:
        return
    for referentiel in ctx.rng.sample(candidats, k=min(10, len(candidats))):
        etablissement_proposant = ctx.rng.choice(etablissements)
        add(db, ReferentielCoefficient(
            id=new_id(), niveau=referentiel.niveau, matiere=referentiel.matiere,
            coefficient=max(0.5, round(referentiel.coefficient + ctx.rng.choice([-0.5, 0.5, 1.0]), 1)),
            statut=StatutReferentiel.PROPOSITION_EN_ATTENTE,
            etablissement_proposant_id=etablissement_proposant.id, propose_pour_id=referentiel.id,
        ))
        ctx.compter("referentiels_coefficients")


# ═══════════════════════════════════════════════════════════════════════════
# Orchestration
# ═══════════════════════════════════════════════════════════════════════════

def creer_admin_ministeriel(db, ctx: Contexte) -> Utilisateur:
    email = f"ministere.seed@{DOMAINE_SEED}"
    admin = creer_utilisateur(
        db, ctx, role=RoleUtilisateur.ADMIN_MINISTERIEL, nom="Ministère", prenom="Éducation", login_id=email, email=email
    )
    ctx.admin_ministeriel = admin
    return admin


def reset_schema() -> None:
    print("Réinitialisation du schéma (DROP puis CREATE de toutes les tables applicatives)...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    # drop_all/create_all recree le schema depuis les modeles SQLAlchemy actuels (comme le
    # fait deja tests/conftest.py sur SQLite), mais ne touche jamais `alembic_version`
    # (cette table n'appartient pas a Base.metadata) : sans cette etape, Alembic croirait
    # la base vierge et tenterait de rejouer TOUTES les migrations sur des tables qui
    # existent deja au prochain `alembic upgrade head`. On aligne alembic_version sur head
    # puisque le schema recree correspond exactement a l'etat vise par les migrations.
    from alembic import command
    from alembic.config import Config as AlembicConfig

    alembic_cfg = AlembicConfig(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    # purge=True : efface la table alembic_version avant de la re-timbrer, sans lire son
    # contenu actuel. Sans ce flag, `stamp` calcule un delta depuis la revision DEJA
    # enregistree jusqu'a head - si cette base a connu un historique de migrations
    # incoherent avec les fichiers presents aujourd'hui (rebase/squash anterieur au
    # seed), la resolution echoue avant meme de commencer.
    command.stamp(alembic_cfg, "head", purge=True)
    print("alembic_version aligné sur head.")


def executer_seed(cfg: Config, seed: int) -> Contexte:
    ctx = Contexte(seed)
    # expire_on_commit=False : le recapitulatif final lit des attributs (login_id,
    # matricule) sur des objets ORM apres le commit et la fermeture de la session.
    db = SessionLocal(expire_on_commit=False)
    try:
        print("Création de l'administrateur ministériel...")
        creer_admin_ministeriel(db, ctx)
        db.commit()

        n_total_etabs = cfg.n_ep + cfg.n_es + cfg.n_up
        print(f"Création de {n_total_etabs} établissements ({cfg.n_ep} EP, {cfg.n_es} ES, {cfg.n_up} UP) et de leurs classes...")
        etablissements = creer_tous_les_etablissements(db, ctx, cfg)
        print(f"  -> {len(ctx.classes)} classes créées au total.")

        for i, etablissement in enumerate(etablissements, start=1):
            classes_de_l_etab = ctx.classes_par_etablissement.get(etablissement.id, [])
            print(f"  [{i}/{len(etablissements)}] {etablissement.nom} ({etablissement.code_etablissement}) — {len(classes_de_l_etab)} classes")

            creer_recrutement_pour_etablissement(db, ctx, cfg, etablissement)
            enseignants_disponibles = ctx.enseignants_signes_par_etablissement.get(etablissement.id, [])

            for classe in classes_de_l_etab:
                eleves_de_la_classe = creer_inscriptions_pour_classe(db, ctx, cfg, classe, etablissement)
                eleves_avec_compte = [e for e in eleves_de_la_classe if e.utilisateur_id]
                enseignant = ctx.rng.choice(enseignants_disponibles)

                creer_consentements_camera(db, ctx, eleves_avec_compte)
                creer_pedagogie_pour_classe(db, ctx, cfg, classe, enseignant, eleves_avec_compte)
                creer_evaluations_pour_classe(db, ctx, cfg, classe, etablissement, enseignant, eleves_avec_compte)
                creer_messagerie_groupe_classe(db, ctx, classe, etablissement, enseignant, eleves_avec_compte)
                creer_sessions_live_pour_classe(db, ctx, cfg, classe, enseignant, eleves_avec_compte)
                for eleve in eleves_avec_compte:
                    creer_dm_tuteur_enfant(db, ctx, eleve, eleve.tuteur_id)

            creer_actes_pour_etablissement(db, ctx, cfg, etablissement)
            creer_services_scolaires_pour_etablissement(db, ctx, cfg, etablissement)
            creer_billetterie_pour_etablissement(db, ctx, cfg, etablissement)
            creer_visite_virtuelle(db, ctx, etablissement)
            creer_marketplace_pour_etablissement(db, ctx, cfg, etablissement)

            # Commit apres chaque etablissement (et non un seul commit final) : sur une
            # base distante (Render), une erreur tardive (ex. micro-jobs) ne doit pas
            # faire perdre TOUT le travail deja flush - juste ce qui suit le dernier
            # commit reussi. Deja verifie en conditions reelles : un rerun repart de
            # toute facon d'un schema vide (DROP+CREATE en tete de script), donc ces
            # commits intermediaires ne changent rien au comportement nominal, ils
            # limitent seulement la perte en cas d'echec.
            db.commit()

        print("Création des propositions de révision de référentiels...")
        creer_propositions_referentiel(db, ctx, etablissements)
        db.commit()

        print("Création des propositions de reconduction de contrats...")
        creer_propositions_reconduction(db, ctx)
        db.commit()

        print(f"Création de {cfg.n_offres_micro_job} offres de micro-jobs et de leurs missions...")
        creer_micro_jobs(db, ctx, cfg)

        print("Enregistrement en base (commit)...")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return ctx


def imprimer_recapitulatif(ctx: Contexte) -> None:
    print("\n" + "═" * 70)
    print("RÉCAPITULATIF DU SEED")
    print("═" * 70)
    largeur = max(len(k) for k in ctx.compteurs) + 2
    for table, n in sorted(ctx.compteurs.items()):
        print(f"  {table.ljust(largeur)} {n}")
    print("═" * 70)
    print(f"Mot de passe commun à TOUS les comptes créés : {MOT_DE_PASSE_COMMUN}")
    print(f"Admin ministériel (A++)   : {ctx.admin_ministeriel.login_id}")
    if ctx.admins_etablissement:
        print(f"Admin établissement (A+)  : {ctx.admins_etablissement[0].login_id}")
    if ctx.tous_enseignants_signes:
        print(f"Enseignant (contrat signé): {ctx.tous_enseignants_signes[0].login_id}")
    if ctx.tuteurs:
        print(f"Tuteur                   : {ctx.tuteurs[0].login_id}")
    premier_eleve_utilisateur = next(
        (e for etab_id in ctx.eleves_par_etablissement for e in ctx.eleves_par_etablissement[etab_id] if e.utilisateur_id),
        None,
    )
    if premier_eleve_utilisateur:
        print(f"Élève (matricule)        : {premier_eleve_utilisateur.matricule}")
    print("═" * 70 + "\n")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass  # flux deja UTF-8 ou non reconfigurable (ex. sortie redirigee sur certains OS) - sans impact sur les donnees.

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="Confirme l'exécution (réinitialise et repeuple la base).")
    parser.add_argument("--scale", type=float, default=1.0, help="Facteur d'échelle appliqué à tous les volumes (défaut 1.0).")
    parser.add_argument("--seed", type=int, default=2024, help="Graine du générateur aléatoire (reproductibilité).")
    parser.add_argument("--force", action="store_true", help="Ignore la vérification ENVIRONMENT=development.")
    args = parser.parse_args()

    # L'aperçu (cible, volumes, avertissement) s'affiche TOUJOURS avant toute
    # verification de garde-fou, y compris quand --force/--yes manquent encore :
    # sur une base distante (Render), c'est souvent le seul moment ou on peut
    # relire "Base ciblee" avant de decider de continuer.
    cfg = Config(scale=args.scale)
    n_total_etabs = cfg.n_ep + cfg.n_es + cfg.n_up

    print(f"Base ciblee : {settings.database_url}")
    print(f"Environnement : {settings.environment}")
    print(
        f"Volumes prevus (scale={args.scale}) : ~{n_total_etabs} etablissements, "
        f"~{cfg.eleves_par_classe[0]}-{cfg.eleves_par_classe[1]} eleves/classe, "
        f"~{cfg.n_offres_micro_job} offres micro-jobs."
    )
    print("\nCE SCRIPT VA SUPPRIMER PUIS RECREER TOUTES LES TABLES DE L'APPLICATION (DROP + CREATE).")
    print("Toute donnee actuellement en base sera DEFINITIVEMENT PERDUE.\n")

    if settings.environment != "development" and not args.force:
        print(
            f"ENVIRONMENT={settings.environment!r} (pas 'development') : relancez avec --force si vous etes "
            "absolument certain de la base ciblee ci-dessus."
        )
        raise SystemExit(1)

    if not args.yes:
        print("Relancez avec --yes pour confirmer l'execution.")
        raise SystemExit(1)

    reset_schema()
    ctx = executer_seed(cfg, args.seed)
    imprimer_recapitulatif(ctx)


if __name__ == "__main__":
    main()
