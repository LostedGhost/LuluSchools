"""Administration ministerielle (A++) : compte, moderation, suspensions, propositions de
referentiel, journal d'audit ; et selection des comptes de demonstration."""

from __future__ import annotations

from datetime import timedelta

from app.modules.audit.models import JournalAuditMinisteriel
from app.modules.etablissements.models import TypeEtablissement
from app.modules.evaluations.models import Devoir, ReferentielCoefficient, StatutReferentiel
from app.modules.identite.models import RoleUtilisateur
from app.modules.pedagogie.models import Cours

from .contexte import DOMAINE, Contexte, age_au, new_id


def creer_admin_ministeriel(ctx: Contexte) -> None:
    login = f"ministere@{DOMAINE}"
    ctx.admin_ministeriel = ctx.utilisateur(
        RoleUtilisateur.ADMIN_MINISTERIEL, "Ministère", "Enseignements", login_id=login, email=login,
        cree_le=ctx.debut_activite - timedelta(days=500),
    )
    ctx.protege.add(ctx.admin_ministeriel.id)


def _journal(ctx: Contexte, action: str, cible_type: str, cible_id: str, motif: str, quand) -> None:
    ctx.ajouter(JournalAuditMinisteriel(
        id=new_id(), acteur_id=ctx.admin_ministeriel.id, action=action, cible_type=cible_type, cible_id=cible_id,
        motif=motif, created_at=quand,
    ))


def moderer_contenus(ctx: Contexte, cours: list[Cours], devoirs: list[Devoir]) -> None:
    """Masquage non destructif de quelques contenus signales (jamais supprimes)."""
    for objet, cible, action in [(c, "cours", "cours.masquer") for c in cours] + [(d, "devoir", "devoir.masquer") for d in devoirs]:
        if ctx.rng.random() >= 0.02:
            continue
        quand = ctx.instant(objet.created_at, ctx.maintenant - timedelta(hours=1))
        objet.masque_par_id = ctx.admin_ministeriel.id
        objet.masque_le = quand
        _journal(ctx, action, cible, objet.id, "Contenu signalé : masqué le temps de la vérification.", quand)


def suspendre(ctx: Contexte) -> None:
    """Quelques comptes adultes suspendus (ecran de supervision A++), jamais un compte de
    demonstration ; un etablissement suspendu, jamais l'UAC ni un etablissement de demo."""
    candidats = [u for u in ctx.utilisateurs.values()
                 if u.role in (RoleUtilisateur.TUTEUR, RoleUtilisateur.ENSEIGNANT) and u.id not in ctx.protege]
    for u in ctx.rng.sample(candidats, k=min(len(candidats), max(1, round(len(candidats) * 0.01)))):
        u.actif = False
        _journal(ctx, "utilisateur.suspendre", "utilisateur", u.id, "Comportement signalé à plusieurs reprises.",
                 ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=1)))
    etablissements = [e for e in ctx.etablissements if e.id not in ctx.protege]
    if len(etablissements) > 3:
        etab = ctx.rng.choice(etablissements)
        etab.actif = False
        _journal(ctx, "etablissement.suspendre", "etablissement", etab.id,
                 "Agrément en cours de renouvellement : établissement suspendu temporairement.",
                 ctx.maintenant - timedelta(days=ctx.rng.randint(1, 10)))


def propositions_referentiel(ctx: Contexte) -> None:
    """Un A+ propose un coefficient different pour un niveau/matiere que son etablissement
    enseigne reellement ; la proposition attend la validation groupee de l'A++."""
    enseignes = [(etab, classe) for etab in ctx.etablissements for classe in ctx.classes_par_etab[etab.id]]
    for etab, classe in ctx.rng.sample(enseignes, k=min(6, len(enseignes))):
        matiere = ctx.rng.choice(ctx.matieres_par_classe[classe.id])
        actuel = ctx.coefficients[(classe.niveau, matiere)]
        ctx.ajouter(ReferentielCoefficient(
            id=new_id(), niveau=classe.niveau, matiere=matiere, coefficient=actuel + 1.0,
            statut=StatutReferentiel.PROPOSITION_EN_ATTENTE, etablissement_proposant_id=etab.id,
            propose_pour_id=ctx.referentiel_ids[(classe.niveau, matiere)],
            created_at=ctx.instant(ctx.debut_activite, ctx.maintenant - timedelta(hours=2)),
        ))


def choisir_comptes_demo(ctx: Contexte) -> None:
    """Comptes representatifs a communiquer (tous : mot de passe commun), choisis parmi ceux
    qui ont le plus de donnees, et proteges des suspensions aleatoires."""
    uac = ctx.uac
    ctx.protege.update({uac.id, ctx.admin_par_etab[uac.id].id})
    ctx.demo["A++ (ministère)"] = ctx.admin_ministeriel.login_id
    ctx.demo["A+ Université d'Abomey-Calavi"] = ctx.admin_par_etab[uac.id].login_id

    def meilleur_eleve(etab, majeur: bool = False):
        inscrits = ctx.inscrits_par_etab[etab.id]
        if majeur:  # prestataire de micro-jobs : 18 ans et plus, numero Mobile Money renseigne
            inscrits = [i for i in inscrits if i.utilisateur.telephone and age_au(i.eleve.date_naissance, ctx.maintenant.date()) >= 18] or inscrits
        return max(inscrits, key=lambda i: (i.niveau_scolaire, i.utilisateur.id)) if inscrits else None

    def enseignant_demo(etab):
        enseignant = next(a.enseignant for c in ctx.classes_par_etab[etab.id] for a in ctx.affectations_par_classe[c.id] if a.principal)
        classe_id = next(c.id for c in ctx.classes_par_etab[etab.id] for a in ctx.affectations_par_classe[c.id] if a.enseignant.id == enseignant.id)
        ctx.enseignants_demo.append((enseignant, classe_id))
        ctx.protege.add(enseignant.id)
        return enseignant

    etudiant = meilleur_eleve(uac, majeur=True)
    ctx.demo["Enseignant UAC"] = enseignant_demo(uac).login_id
    if etudiant:
        ctx.eleves_demo["uac"] = etudiant
        ctx.demo["Étudiant UAC (matricule)"] = etudiant.utilisateur.login_id
        ctx.demo["Tuteur de cet étudiant"] = ctx.tuteurs[etudiant.eleve.tuteur_id].login_id
        ctx.protege.update({etudiant.utilisateur.id, etudiant.eleve.tuteur_id})

    for type_etab, libelle, cle in ((TypeEtablissement.ES, "lycée", "lycee"), (TypeEtablissement.EP, "école primaire", "primaire")):
        etab = next((e for e in ctx.etablissements if e.type == type_etab), None)
        if etab is None:
            continue
        ctx.protege.update({etab.id, ctx.admin_par_etab[etab.id].id})
        ctx.demo[f"A+ {libelle} ({etab.nom})"] = ctx.admin_par_etab[etab.id].login_id
        eleve = meilleur_eleve(etab)
        if eleve:
            ctx.eleves_demo[cle] = eleve
            ctx.demo[f"Élève {libelle} (matricule)"] = eleve.utilisateur.login_id
            ctx.demo[f"Tuteur de cet élève ({libelle})"] = ctx.tuteurs[eleve.eleve.tuteur_id].login_id
            ctx.protege.update({eleve.utilisateur.id, eleve.eleve.tuteur_id})
        ctx.demo[f"Enseignant {libelle}"] = enseignant_demo(etab).login_id
