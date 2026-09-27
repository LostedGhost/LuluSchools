"""Etablissements, classes, administrateurs, rentrees, referentiels de coefficients."""

from __future__ import annotations

import hashlib
from datetime import timedelta

from app.modules.etablissements.models import (
    AdminEtablissement,
    Classe,
    Etablissement,
    PolitiqueDepassement,
    RentreeScolaire,
    StatutEtablissement,
    StatutRentree,
    TypeEtablissement,
)
from app.modules.evaluations.models import ReferentielCoefficient, StatutReferentiel
from app.modules.identite.models import RoleUtilisateur
from app.modules.messagerie.models import Conversation, TypeConversation
from app.modules.visites_virtuelles.models import TypeVisiteVirtuelle, VisiteVirtuelle

from .contexte import DOMAINE, Contexte, new_id
from .taxonomie import (
    FILIERES_UAC,
    FILIERES_UAC_AVEC_MASTER,
    FILIERES_UNIVERSITE_PRIVE,
    FILIERES_UNIVERSITE_PUBLIC,
    MATIERES_GENERAL_COMMUN,
    MATIERES_PAR_SERIE_GENERALE,
    MATIERES_PAR_SERIE_TECHNIQUE,
    MATIERES_PRIMAIRE,
    MATIERES_TECHNIQUE_COMMUN,
    MATIERES_TRONC_COMMUN,
    NIVEAUX_MATERNEL_PRIMAIRE,
    NIVEAUX_SECONDAIRE_TRONC_COMMUN,
    NIVEAUX_TECHNIQUE_2ND_CYCLE,
    NOMS_ETABLISSEMENTS_EP,
    NOMS_ETABLISSEMENTS_ES_GENERAL,
    NOMS_ETABLISSEMENTS_ES_TECHNIQUE,
    NOMS_ETABLISSEMENTS_UP_PRIVE,
    NOMS_ETABLISSEMENTS_UP_PUBLIC,
    SERIES_GENERALES,
    SERIES_TECHNIQUES,
    UAC_COORDONNEES,
    UAC_DESCRIPTION,
    UAC_NOM,
)

VILLES = {
    "abomey-calavi": (6.4485, 2.3557), "porto-novo": (6.4969, 2.6289), "seme-kpodji": (6.3661, 2.6156),
    "godomey": (6.3958, 2.3336), "akpakpa": (6.3644, 2.4453), "parakou": (9.3372, 2.6303),
    "abomey": (7.1825, 1.9911), "lokossa": (6.6389, 1.7167), "cotonou": (6.3703, 2.3912),
}
INSTITUTIONS = {
    "mathieu bouke": VILLES["parakou"], "toffa 1er": VILLES["porto-novo"], "behanzin": VILLES["porto-novo"],
    "technologie industrielle": VILLES["lokossa"], "ingenierie et mathematiques": VILLES["abomey"],
    "universite de parakou": VILLES["parakou"],
}


def _simple(texte: str) -> str:
    for a, b in {"é": "e", "è": "e", "ê": "e", "ô": "o", "à": "a", "î": "i", "'": " ", "’": " ", "-": "-"}.items():
        texte = texte.replace(a, b)
    return texte.lower()


def _coordonnees(nom: str, etab_id: str) -> tuple[float, float]:
    simple = _simple(nom)
    base = next((c for cle, c in INSTITUTIONS.items() if cle in simple), None)
    base = base or next((c for ville, c in VILLES.items() if ville in simple), VILLES["cotonou"])
    empreinte = hashlib.sha256(etab_id.encode()).hexdigest()
    dx = (int(empreinte[:8], 16) / 0xFFFFFFFF - 0.5) * 0.03
    dy = (int(empreinte[8:16], 16) / 0xFFFFFFFF - 0.5) * 0.03
    return round(base[0] + dx, 6), round(base[1] + dy, 6)


# Coefficient d'une matiere (referentiel national) : matieres dominantes de la serie
# plus lourdes, EPS/activites legeres - ordre de grandeur des baremes beninois.
def _coefficient(niveau: str, filiere: str | None, matiere: str) -> float:
    if matiere in ("EPS", "Activités Manuelles", "Éveil", "Graphisme"):
        return 1.0
    dominantes = {
        "Mathématiques et Sciences Physiques": ("Mathématiques", "Physique-Chimie"),
        "Mathématiques et Sciences de la Vie et de la Terre": ("Mathématiques", "SVT"),
        "Lettres-Langues": ("Littérature", "Français", "Latin/Espagnol"),
        "Lettres-Philosophie": ("Philosophie Approfondie", "Littérature", "Philosophie"),
        "Sciences Économiques et Sociales": ("Sciences Économiques", "Mathématiques"),
    }.get(filiere or "", ())
    if matiere in dominantes:
        return 5.0
    if matiere in ("Mathématiques", "Français"):
        return 3.0
    return 2.0


def _referentiel(ctx: Contexte, niveau: str, filiere: str | None, matiere: str) -> None:
    if (niveau, matiere) in ctx.coefficients:
        return
    coefficient = _coefficient(niveau, filiere, matiere)
    ctx.coefficients[(niveau, matiere)] = coefficient
    referentiel = ctx.ajouter(ReferentielCoefficient(
        id=new_id(), niveau=niveau, matiere=matiere, coefficient=coefficient, statut=StatutReferentiel.VALIDE,
        created_at=ctx.debut_activite - timedelta(days=200),
    ))
    ctx.referentiel_ids[(niveau, matiere)] = referentiel.id


def _classe(ctx: Contexte, etab: Etablissement, niveau: str, matieres: list[str], filiere: str | None = None) -> Classe:
    capacite = ctx.rng.randint(ctx.cfg.eleves_par_classe[1] + 2, ctx.cfg.eleves_par_classe[1] + 12)
    classe = Classe(
        id=new_id(), etablissement_id=etab.id, niveau=niveau, filiere=filiere, annee_academique=ctx.annee,
        capacite=capacite, politique_depassement=ctx.rng.choice(list(PolitiqueDepassement)),
        created_at=ctx.rentree - timedelta(days=ctx.rng.randint(40, 90)),
    )
    # UC-44/59 : une partie des classes est reconduite de l'annee precedente (classe source
    # jamais peuplee cette annee, comme en production apres la rentree).
    if ctx.rng.random() < 0.3:
        debut, fin = ctx.annee.split("-")
        source = Classe(
            id=new_id(), etablissement_id=etab.id, niveau=niveau, filiere=filiere,
            annee_academique=f"{int(debut) - 1}-{int(fin) - 1}", capacite=capacite,
            politique_depassement=classe.politique_depassement, created_at=classe.created_at - timedelta(days=365),
        )
        ctx.ajouter(source)
        classe.reconduite_depuis_id = source.id
    ctx.ajouter(classe)
    groupe = ctx.ajouter(Conversation(id=new_id(), type=TypeConversation.GROUPE_CLASSE, classe_id=classe.id, created_at=classe.created_at))
    ctx.groupe_par_classe[classe.id] = groupe.id
    ctx.classes_par_etab[etab.id].append(classe)
    ctx.matieres_par_classe[classe.id] = matieres
    for matiere in matieres:
        _referentiel(ctx, niveau, filiere, matiere)
    return classe


def _etablissement(ctx: Contexte, nom: str, type_etab: TypeEtablissement, statut: StatutEtablissement) -> Etablissement:
    etab_id = new_id()
    latitude, longitude = UAC_COORDONNEES if nom == UAC_NOM else _coordonnees(nom, etab_id)
    code = f"{type_etab.value}{ctx.sequence('code:' + type_etab.value):02d}"
    etab = Etablissement(
        id=etab_id, nom=nom, type=type_etab, statut=statut, code_etablissement=code,
        latitude=latitude, longitude=longitude, actif=True,
        description=UAC_DESCRIPTION if nom == UAC_NOM else (
            f"{nom} est un établissement {'public' if statut == StatutEtablissement.PUBLIC else 'privé'} "
            "reconnu par le ministère, qui accueille les élèves de son secteur."
        ),
        created_at=ctx.debut_activite - timedelta(days=ctx.rng.randint(400, 900)),
    )
    ctx.ajouter(etab)
    ctx.etablissements.append(etab)

    # Admin A+ : identifiant previsible (admin.<code>@...) pour retrouver chaque etablissement.
    admin = ctx.utilisateur(
        RoleUtilisateur.ADMIN_ETABLISSEMENT, ctx.nom_famille(), ctx.prenom(ctx.rng.choice("MF")),
        login_id=f"admin.{code.lower()}@{DOMAINE}", email=f"admin.{code.lower()}@{DOMAINE}",
    )
    ctx.ajouter(AdminEtablissement(utilisateur_id=admin.id, etablissement_id=etab.id))
    ctx.admin_par_etab[etab.id] = admin

    ctx.ajouter(RentreeScolaire(
        id=new_id(), etablissement_id=etab.id, annee_academique=ctx.annee, statut=StatutRentree.OUVERTE,
        created_at=ctx.rentree - timedelta(days=30),
    ))
    debut, fin = ctx.annee.split("-")
    ctx.ajouter(RentreeScolaire(
        id=new_id(), etablissement_id=etab.id, annee_academique=f"{int(debut) - 1}-{int(fin) - 1}",
        statut=StatutRentree.FERMEE, created_at=ctx.rentree - timedelta(days=395),
    ))
    if ctx.rng.random() < 0.5:
        ctx.ajouter(VisiteVirtuelle(
            id=new_id(), etablissement_id=etab.id, type=ctx.rng.choice(list(TypeVisiteVirtuelle)),
            lien_externe=f"https://visites.luluschools.example/{code.lower()}", attestation_autorisation=True,
        ))
    return etab


def _primaire(ctx: Contexte, nom: str) -> None:
    etab = _etablissement(ctx, nom, TypeEtablissement.EP, ctx.rng.choice(list(StatutEtablissement)))
    for niveau in NIVEAUX_MATERNEL_PRIMAIRE:
        _classe(ctx, etab, niveau, MATIERES_PRIMAIRE[niveau])


def _secondaire(ctx: Contexte, nom: str, technique: bool) -> None:
    etab = _etablissement(ctx, nom, TypeEtablissement.ES, ctx.rng.choice(list(StatutEtablissement)))
    for niveau in NIVEAUX_SECONDAIRE_TRONC_COMMUN:
        _classe(ctx, etab, niveau, MATIERES_TRONC_COMMUN)
    if technique:
        for code in ctx.rng.sample(list(SERIES_TECHNIQUES), k=2):
            for niveau in NIVEAUX_TECHNIQUE_2ND_CYCLE:
                _classe(ctx, etab, niveau, MATIERES_TECHNIQUE_COMMUN + MATIERES_PAR_SERIE_TECHNIQUE[code], SERIES_TECHNIQUES[code])
    else:
        for code in ctx.rng.sample(list(SERIES_GENERALES), k=3):
            for niveau in ("2nde", "1ère", "Terminale"):
                _classe(ctx, etab, niveau, MATIERES_GENERAL_COMMUN + MATIERES_PAR_SERIE_GENERALE[code], SERIES_GENERALES[code])


def _universite(ctx: Contexte, nom: str, filieres: dict[str, list[str]], avec_master: list[str], public: bool) -> Etablissement:
    etab = _etablissement(ctx, nom, TypeEtablissement.UP, StatutEtablissement.PUBLIC if public else StatutEtablissement.PRIVE)
    for filiere, matieres in filieres.items():
        for niveau in ("1ère année de Licence", "2ème année de Licence", "3ème année de Licence"):
            _classe(ctx, etab, niveau, matieres, filiere)
        if filiere in avec_master:
            for niveau in ("1ère année de Master", "2ème année de Master"):
                _classe(ctx, etab, niveau, matieres, filiere)
    return etab


def _nom_unique(pool: list[str], i: int) -> str:
    nom = pool[i % len(pool)]
    return nom if i < len(pool) else f"{nom} ({i // len(pool) + 1})"


def creer_etablissements(ctx: Contexte) -> None:
    cfg = ctx.cfg
    # L'Universite d'Abomey-Calavi en premier : toujours presente, code UP01.
    ctx.uac = _universite(ctx, UAC_NOM, FILIERES_UAC, FILIERES_UAC_AVEC_MASTER, public=True)

    for i in range(cfg.n_ep):
        _primaire(ctx, _nom_unique(NOMS_ETABLISSEMENTS_EP, i))
    for i in range(cfg.n_es):
        technique = i % 2 == 1
        pool = NOMS_ETABLISSEMENTS_ES_TECHNIQUE if technique else NOMS_ETABLISSEMENTS_ES_GENERAL
        _secondaire(ctx, _nom_unique(pool, i // 2), technique)
    for i in range(cfg.n_up_autres):
        public = i % 2 == 0
        pool = NOMS_ETABLISSEMENTS_UP_PUBLIC if public else NOMS_ETABLISSEMENTS_UP_PRIVE
        filieres_pool = FILIERES_UNIVERSITE_PUBLIC if public else FILIERES_UNIVERSITE_PRIVE
        choisies = ctx.rng.sample(list(filieres_pool), k=3)
        _universite(
            ctx, _nom_unique(pool, i // 2), {f: filieres_pool[f] for f in choisies}, choisies[:1], public
        )
