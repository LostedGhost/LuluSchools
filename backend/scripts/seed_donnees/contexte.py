"""Etat partage du seed : configuration, horloge, tirage aleatoire, insertion groupee."""

from __future__ import annotations

import random
import unicodedata
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

from app.core.database import Base
from app.core.security import hash_password
from app.modules.etablissements.models import Classe, Etablissement, TypeEtablissement, annee_academique_courante
from app.modules.identite.models import Enseignant, RoleUtilisateur, Tuteur, Utilisateur
from app.modules.inscriptions.models import Eleve, Nationalite

from .fichiers import Fichiers
from .taxonomie import NOMS_FAMILLE, PRENOMS_FEMININS, PRENOMS_MASCULINS, telephone_benin

MOT_DE_PASSE_COMMUN = "Password1!"
DOMAINE = "seed.luluschools.example"  # domaine reserve (RFC 2606) : aucun e-mail reel n'est adresse


class Config:
    """--scale agit sur le NOMBRE d'etablissements et d'eleves ; la structure de chaque
    etablissement (classes par niveau, un enseignant pour ~2 classes...) reste realiste."""

    def __init__(self, scale: float) -> None:
        self.scale = scale
        self.n_ep = max(1, round(10 * scale))
        self.n_es = max(1, round(10 * scale))
        # UAC toujours presente, en plus des autres universites.
        self.n_up_autres = max(0, round(10 * scale) - 1)
        self.eleves_par_classe = (max(3, round(10 * scale)), max(5, round(22 * scale)))
        self.cours_par_classe = max(1, round(3 * scale))
        self.devoirs_par_classe = max(2, round(3 * scale))
        self.sessions_live_par_classe = max(1, round(2 * scale))
        self.evenements_par_etab = max(1, round(2 * scale))
        self.n_offres_micro_job = max(6, round(60 * scale))
        self.annonces_par_universite = max(4, round(12 * scale))


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Affectation:
    enseignant: Utilisateur
    matiere: str | None
    principal: bool


@dataclass
class EleveInscrit:
    eleve: Eleve
    utilisateur: Utilisateur
    classe: Classe
    etablissement: Etablissement
    niveau_scolaire: float  # 0-1 : aptitude stable, pour des notes/quiz/vie scolaire coherents entre eux
    camera: bool = False  # consentement camera donne par le tuteur (cours en direct)


@dataclass
class Famille:
    tuteur: Utilisateur
    nom: str
    enfants: list[Eleve] = field(default_factory=list)


class Contexte:
    def __init__(self, seed: int, cfg: Config, fichiers: Fichiers, casier_chiffrable: bool) -> None:
        self.rng = random.Random(seed)
        self.cfg = cfg
        self.fichiers = fichiers
        self.casier_chiffrable = casier_chiffrable
        self.mot_de_passe_hash = hash_password(MOT_DE_PASSE_COMMUN)

        # Horloge : tout le jeu de donnees est date par rapport au moment du seed. L'annee
        # scolaire a commence a la rentree (mi-septembre) ; l'activite (devoirs, sessions,
        # tickets passes) s'etale entre la rentree et maintenant, au moins sur 3 semaines.
        self.maintenant = datetime.now(timezone.utc)
        self.annee = annee_academique_courante()
        premiere_annee = int(self.annee.split("-")[0])
        self.rentree = datetime(premiere_annee, 9, 16, 7, 30, tzinfo=timezone.utc)
        self.debut_activite = min(self.rentree, self.maintenant - timedelta(days=21))
        self.fin_annee = date(premiere_annee + 1, 7, 15)

        self._tampon: dict[str, list] = defaultdict(list)
        self._tous: dict[str, list] = defaultdict(list)  # tout ce qui a ete cree, persiste ou non
        self.compteurs: dict[str, int] = defaultdict(int)
        self._sequences: dict[str, int] = defaultdict(int)
        self._n_personne = 0

        self.admin_ministeriel: Utilisateur | None = None
        self.etablissements: list[Etablissement] = []
        self.uac: Etablissement | None = None
        self.admin_par_etab: dict[str, Utilisateur] = {}
        self.classes_par_etab: dict[str, list[Classe]] = defaultdict(list)
        self.matieres_par_classe: dict[str, list[str]] = {}
        self.enseignants_par_etab: dict[str, list[Utilisateur]] = defaultdict(list)  # contrat SIGNE
        self.matiere_enseignant: dict[str, str | None] = {}
        self.affectations_par_classe: dict[str, list[Affectation]] = defaultdict(list)
        self.inscrits_par_classe: dict[str, list[EleveInscrit]] = defaultdict(list)
        self.inscrits_par_etab: dict[str, list[EleveInscrit]] = defaultdict(list)
        self.familles: list[Famille] = []
        self.tuteurs: dict[str, Utilisateur] = {}
        self.utilisateurs: dict[str, Utilisateur] = {}
        self.coefficients: dict[tuple[str, str], float] = {}
        self.referentiel_ids: dict[tuple[str, str], str] = {}
        self.groupe_par_classe: dict[str, str] = {}
        self.plafonds: dict[str, object] = {}  # eleve_utilisateur_id -> PlafondFamilial
        self.depenses: dict[str, list[tuple]] = defaultdict(list)
        self.protege: set[str] = set()  # comptes de demonstration : jamais suspendus
        self.demo: dict[str, str] = {}
        self.eleves_demo: dict[str, EleveInscrit] = {}
        self.enseignants_demo: list[tuple[Utilisateur, str]] = []

    # ─── insertion ─────────────────────────────────────────────────────────
    def ajouter(self, obj):
        """Mise en tampon ; `persister` insere ensuite table par table dans l'ordre des
        cles etrangeres (Base.metadata.sorted_tables) : une requete groupee par table au
        lieu d'un aller-retour par ligne, decisif contre une base distante (Render)."""
        self._tampon[obj.__table__.name].append(obj)
        self._tous[obj.__table__.name].append(obj)
        self.compteurs[obj.__table__.name] += 1
        return obj

    def persister(self, db) -> None:
        for table in Base.metadata.sorted_tables:
            objets = self._tampon.pop(table.name, None)
            if objets:
                db.add_all(objets)
                db.flush()
        if self._tampon:
            restes = ", ".join(self._tampon)
            raise RuntimeError(f"Tables hors metadata dans le tampon : {restes}")
        db.commit()

    def objets(self, modele) -> list:
        return self._tous[modele.__tablename__]

    # ─── temps ─────────────────────────────────────────────────────────────
    def instant(self, debut: datetime, fin: datetime) -> datetime:
        if fin <= debut:
            return debut
        return debut + timedelta(seconds=self.rng.uniform(0, (fin - debut).total_seconds()))

    def instant_scolaire(self, debut: datetime, fin: datetime) -> datetime:
        """Un instant plausible en journee (7 h - 19 h, heure du Benin = UTC+1)."""
        jour = self.instant(debut, fin)
        heure = self.rng.randint(6, 17)
        resultat = datetime.combine(jour.date(), time(heure, self.rng.randint(0, 59)), tzinfo=timezone.utc)
        return min(max(resultat, debut), fin)

    def jour(self, decalage_min: int, decalage_max: int) -> date:
        return (self.maintenant + timedelta(days=self.rng.randint(decalage_min, decalage_max))).date()

    # ─── sequences / identites ─────────────────────────────────────────────
    def sequence(self, cle: str) -> int:
        self._sequences[cle] += 1
        return self._sequences[cle]

    def prenom(self, genre: str) -> str:
        return self.rng.choice(PRENOMS_FEMININS if genre == "F" else PRENOMS_MASCULINS)

    def nom_famille(self) -> str:
        return self.rng.choice(NOMS_FAMILLE)

    def _email(self, prenom: str, nom: str) -> str:
        self._n_personne += 1
        sans_accents = unicodedata.normalize("NFKD", f"{prenom}.{nom}".lower()).encode("ascii", "ignore").decode()
        simple = "".join(c for c in sans_accents if c.isalnum() or c == ".")
        return f"{simple}.{self._n_personne}@{DOMAINE}"

    def utilisateur(
        self,
        role: RoleUtilisateur,
        nom: str,
        prenom: str,
        *,
        login_id: str | None = None,
        email: str | None | bool = True,
        telephone: bool = True,
        cree_le: datetime | None = None,
    ) -> Utilisateur:
        if email is True:
            email = self._email(prenom, nom)
        u = Utilisateur(
            id=new_id(),
            nom=nom,
            prenom=prenom,
            login_id=login_id or email,
            email=email or None,
            telephone=telephone_benin(self.sequence("telephone") * 7919) if telephone else None,
            mot_de_passe_hash=self.mot_de_passe_hash,
            mot_de_passe_temporaire=False,
            role=role,
            email_verifie=True,
            actif=True,
            created_at=cree_le or self.debut_activite - timedelta(days=self.rng.randint(30, 400)),
        )
        self.ajouter(u)
        self.utilisateurs[u.id] = u
        return u

    def tuteur(self, nom: str) -> Utilisateur:
        genre = self.rng.choice("MF")
        u = self.utilisateur(RoleUtilisateur.TUTEUR, nom, self.prenom(genre), telephone=self.rng.random() < 0.92)
        self.ajouter(Tuteur(utilisateur_id=u.id))
        self.tuteurs[u.id] = u
        return u

    def enseignant(self, cree_le: datetime) -> Utilisateur:
        genre = self.rng.choice("MF")
        u = self.utilisateur(RoleUtilisateur.ENSEIGNANT, self.nom_famille(), self.prenom(genre), cree_le=cree_le)
        self.ajouter(Enseignant(utilisateur_id=u.id))
        return u

    def matricule(self, type_etab: TypeEtablissement, nationalite: Nationalite) -> str:
        """Meme format que inscriptions/router.py::_generer_matricule (sequence par
        cycle + nationalite + annee), calcule en memoire."""
        prefixe = {TypeEtablissement.EP: "7", TypeEtablissement.ES: "8", TypeEtablissement.UP: ""}[type_etab]
        chiffre = "1" if nationalite == Nationalite.NATIONALE else "2"
        annee = f"{self.maintenant.year % 100:02d}"
        n = self.sequence(f"matricule:{prefixe}{chiffre}{annee}")
        return f"{prefixe}{chiffre}{n:05d}{annee}"

    def depense(self, eleve_utilisateur_id: str, quand: datetime, montant: float, module) -> None:
        """Depense payee d'un eleve (Coffre-fort : cumul hebdomadaire)."""
        self.depenses[eleve_utilisateur_id].append((quand, montant, module))


def age_au(date_naissance: date, reference: date) -> int:
    age = reference.year - date_naissance.year
    if (reference.month, reference.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age
