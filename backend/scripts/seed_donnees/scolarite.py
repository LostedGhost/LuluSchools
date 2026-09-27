"""Familles et inscriptions (UC-02/03) selon inscriptions/router.py :

- l'enfant porte le nom de famille de son tuteur ; une famille peut avoir plusieurs enfants,
  eventuellement dans des etablissements differents (primaire + lycee...) ;
- l'age correspond au niveau de la classe ;
- moins de 16 ans (Art. 446) : l'inscription attend le consentement du tuteur
  (EN_ATTENTE_CONSENTEMENT_PARENTAL), puis SOUMISE avec son horodatage ;
- 16 ans et plus : SOUMISE directement, sans horodatage de consentement ;
- a la validation par l'A+ (dans la limite de la capacite) : matricule + compte eleve.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.modules.cours_direct.models import ConsentementCameraLive
from app.modules.etablissements.models import Classe, Etablissement, TypeEtablissement
from app.modules.identite.models import RoleUtilisateur
from app.modules.inscriptions.models import Eleve, Inscription, Nationalite, StatutInscription

from .contexte import Contexte, EleveInscrit, Famille, age_au, new_id

AGE_MAJORITE_NUMERIQUE = 16  # inscriptions/router.py

AGE_PAR_NIVEAU = {
    "Maternelle 1": 4, "Maternelle 2": 5, "CI": 6, "CP": 7, "CE1": 8, "CE2": 9, "CM1": 10, "CM2": 11,
    "6ème": 12, "5ème": 13, "4ème": 14, "3ème": 15, "2nde": 16, "1ère": 17, "Terminale": 18,
    "1ère année de lycée technique": 16, "2ème année de lycée technique": 17, "3ème année de lycée technique": 18,
    "1ère année de Licence": 19, "2ème année de Licence": 20, "3ème année de Licence": 21,
    "1ère année de Master": 22, "2ème année de Master": 23,
}
MOTIFS_REJET = [
    "Dossier incomplet : acte de naissance manquant.",
    "Classe complète au moment du traitement du dossier.",
    "Pièces fournies illisibles : merci de déposer un nouveau dossier.",
]


def _date_naissance(ctx: Contexte, niveau: str) -> date:
    # Age au 31 decembre de l'annee de rentree, avec un an d'avance/retard occasionnel.
    reference = date(ctx.rentree.year, 12, 31)
    age = AGE_PAR_NIVEAU[niveau] + ctx.rng.choice([0, 0, 0, 1, 1, -1] if AGE_PAR_NIVEAU[niveau] > 6 else [0, 0, 1])
    return date(reference.year - age, ctx.rng.randint(1, 12), ctx.rng.randint(1, 28))


def _famille(ctx: Contexte, etab: Etablissement) -> Famille:
    """30 % de fratries : un tuteur existant inscrit un autre enfant."""
    if ctx.familles and ctx.rng.random() < 0.3:
        famille = ctx.rng.choice(ctx.familles)
        if len(famille.enfants) < 4:
            return famille
    nom = ctx.nom_famille()
    famille = Famille(tuteur=ctx.tuteur(nom), nom=nom)
    ctx.familles.append(famille)
    return famille


def inscrire_classe(ctx: Contexte, etab: Etablissement, classe: Classe) -> None:
    n = ctx.rng.randint(*ctx.cfg.eleves_par_classe)
    valides = 0
    for _ in range(n):
        famille = _famille(ctx, etab)
        naissance = _date_naissance(ctx, classe.niveau)
        genre = ctx.rng.choice("MF")
        eleve = Eleve(
            id=new_id(), nom=famille.nom, prenom=ctx.prenom(genre), date_naissance=naissance,
            nationalite=Nationalite.NATIONALE if ctx.rng.random() < 0.92 else Nationalite.ETRANGERE,
            tuteur_id=famille.tuteur.id,
        )
        famille.enfants.append(eleve)
        ctx.ajouter(eleve)

        tirage = ctx.rng.random()
        if valides < classe.capacite and tirage < 0.86:
            issue = "validee"
        elif tirage < 0.96:
            issue = "en_attente"
        else:
            issue = "rejetee"
        # Dossiers valides/rejetes deposes avant la rentree ; dossiers en attente, recents.
        if issue == "en_attente":
            depot = ctx.instant(ctx.maintenant - timedelta(days=12), ctx.maintenant - timedelta(hours=2))
        else:
            depot = ctx.instant(ctx.rentree - timedelta(days=75), ctx.rentree - timedelta(days=5))
        mineur = age_au(naissance, depot.date()) < AGE_MAJORITE_NUMERIQUE  # age a la date du depot
        if issue == "validee":
            statut = StatutInscription.VALIDEE
        elif issue == "rejetee":
            statut = StatutInscription.REJETEE
        elif mineur and ctx.rng.random() < 0.6:
            statut = StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL
        else:
            statut = StatutInscription.SOUMISE

        # Consentement horodate : uniquement pour un mineur, et seulement une fois donne.
        consentement = None
        if mineur and statut != StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL:
            consentement = depot + timedelta(minutes=ctx.rng.randint(1, 60))
        inscription = Inscription(
            id=new_id(), eleve_id=eleve.id, classe_id=classe.id, statut=statut,
            consentement_parental_horodatage=consentement,
            motif_rejet=ctx.rng.choice(MOTIFS_REJET) if statut == StatutInscription.REJETEE else None,
            created_at=depot,
        )
        ctx.ajouter(inscription)

        if statut == StatutInscription.VALIDEE:
            valides += 1
            matricule = ctx.matricule(etab.type, eleve.nationalite)
            eleve.matricule = matricule
            etudiant = etab.type == TypeEtablissement.UP
            # Numero Mobile Money : la plupart des etudiants l'ont renseigne (reversements
            # micro-jobs/marketplace) ; jamais pour un eleve du primaire/secondaire.
            compte = ctx.utilisateur(
                RoleUtilisateur.ELEVE, eleve.nom, eleve.prenom, login_id=matricule, email=False,
                telephone=etudiant and ctx.rng.random() < 0.85, cree_le=depot + timedelta(days=ctx.rng.randint(2, 20)),
            )
            eleve.utilisateur_id = compte.id
            inscrit = EleveInscrit(
                eleve=eleve, utilisateur=compte, classe=classe, etablissement=etab,
                niveau_scolaire=min(0.98, max(0.15, ctx.rng.gauss(0.62, 0.17))),
            )
            ctx.inscrits_par_classe[classe.id].append(inscrit)
            ctx.inscrits_par_etab[etab.id].append(inscrit)

            # Consentement camera pour les cours en direct : donne par le tuteur, pour une
            # partie des enfants (UC-16).
            if ctx.rng.random() < 0.55:
                ctx.ajouter(ConsentementCameraLive(
                    id=new_id(), eleve_utilisateur_id=compte.id, tuteur_id=famille.tuteur.id,
                    date_consentement=compte.created_at + timedelta(days=ctx.rng.randint(1, 10)),
                ))
                inscrit.camera = True
