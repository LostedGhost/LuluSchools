"""Lot 7.8 — EFTP et insertion : offres de stage d'entreprises partenaires (secondaire
technique et universites), candidatures, competences metier validees par les enseignants
des classes techniques, et un type d'acte « bourse scientifique » a eligibilite verifiee."""

from __future__ import annotations

from datetime import timedelta

from app.modules.actes.models import TypeActeAcademique
from app.modules.etablissements.models import Etablissement, TypeEtablissement
from app.modules.insertion.models import (
    CandidatureStage,
    CompetenceMetier,
    NiveauCompetence,
    OffreStage,
    StatutCandidatureStage,
)

from .contexte import Contexte, new_id

ENTREPRISES = (
    ("SBEE", "Électricien de maintenance", "Entretien des postes de distribution électrique.", "Cotonou"),
    ("SONEB", "Technicien réseau d'eau", "Maintenance des réseaux et relevé des compteurs.", "Porto-Novo"),
    ("Port Autonome de Cotonou", "Agent logistique", "Suivi des conteneurs et saisie des bons de sortie.", "Cotonou"),
    ("Sèmè City", "Développeur web junior", "Participation au développement d'applications pour des start-up.", "Sèmè-Kpodji"),
    ("Ferme-école de Songhaï", "Assistant agronome", "Suivi des cultures et de l'élevage en agriculture durable.", "Porto-Novo"),
)
COMPETENCES = ("Lire un schéma technique", "Utiliser les outils de mesure", "Respecter les règles de sécurité",
               "Rédiger un compte rendu d'intervention", "Travailler en équipe sur un chantier")


def peupler(ctx: Contexte, etab: Etablissement) -> None:
    if etab.type in (TypeEtablissement.ES, TypeEtablissement.UP):
        # Bourse d'etudes pour les filieres scientifiques (PAG) : jamais tiree au hasard
        # par le seed, l'eligibilite etant verifiee a chaque demande reelle.
        ctx.ajouter(TypeActeAcademique(
            id=new_id(), etablissement_id=etab.id, nom="Demande de bourse (filières scientifiques)", prix=0.0,
            pieces_requises="Aucune : la moyenne dans les matières scientifiques est vérifiée automatiquement.",
            condition_eligibilite="Moyenne d'au moins 12/20 dans les matières scientifiques de l'année.",
            critere_automatique="bourse_scientifique", created_at=ctx.debut_activite - timedelta(days=100),
        ))

    classes = ctx.classes_par_etab[etab.id]
    techniques = [c for c in classes if c.enseignement == "technique"]
    if etab.type == TypeEtablissement.UP or techniques:
        admin = ctx.admin_par_etab[etab.id]
        inscrits = [i for i in ctx.inscrits_par_etab[etab.id] if not techniques or i.classe in techniques]
        for entreprise, intitule, description, lieu in ctx.rng.sample(ENTREPRISES, k=2):
            offre = OffreStage(
                id=new_id(), etablissement_id=etab.id, entreprise=entreprise, intitule=f"Stage — {intitule}",
                description=description, lieu=lieu, filiere=None, duree_semaines=ctx.rng.choice([4, 6, 8, 12]),
                date_limite=(ctx.maintenant + timedelta(days=ctx.rng.randint(10, 45))).date(), contact=f"stages@{entreprise.lower().split()[0]}.example",
                active=True, publie_par_id=admin.id, created_at=ctx.debut_activite + timedelta(days=ctx.rng.randint(5, 20)),
            )
            ctx.ajouter(offre)
            for inscrit in ctx.rng.sample(inscrits, k=min(3, len(inscrits))):
                ctx.ajouter(CandidatureStage(
                    id=new_id(), offre_id=offre.id, eleve_utilisateur_id=inscrit.utilisateur.id,
                    message="Je souhaite mettre en pratique ma formation dans votre entreprise.",
                    statut=ctx.rng.choice(list(StatutCandidatureStage)),
                    created_at=offre.created_at + timedelta(days=ctx.rng.randint(1, 5)),
                ))

    for classe in techniques:
        affectations = ctx.affectations_par_classe[classe.id]
        if not affectations:
            continue
        for inscrit in ctx.inscrits_par_classe[classe.id]:
            if ctx.rng.random() < 0.35:
                ctx.ajouter(CompetenceMetier(
                    id=new_id(), eleve_utilisateur_id=inscrit.utilisateur.id, intitule=ctx.rng.choice(COMPETENCES),
                    niveau=ctx.rng.choice(list(NiveauCompetence)), valide_par_id=affectations[0].enseignant.id,
                    created_at=ctx.debut_activite + timedelta(days=ctx.rng.randint(10, 40)),
                ))
