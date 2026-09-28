"""Recrutement (UC-04 a UC-06) selon le vrai workflow :

poste OUVERT -> candidatures (documents notes par l'IA ; un document sous le seuil rejette
automatiquement) -> verdict de l'A+ sur le casier (CONFORME obligatoire) -> contrat (une
seule candidature par poste : le poste passe POURVU, la candidature RETENUE) -> signature
de l'enseignant (trace dessine). Chaque enseignant affecte a une classe a donc un contrat
SIGNE avec l'etablissement, et chaque etablissement garde des postes OUVERTS dont les
candidatures attendent l'A+ (casier a examiner, contestation, notation a revoir).
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta

from app.core.crypto import chiffrer_bytes
from app.modules.etablissements.models import AffectationEnseignant, Etablissement, TypeEtablissement
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

from .contexte import Affectation, Contexte, new_id
from .taxonomie import MOTIFS_CONTESTATION_RECRUTEMENT

CASIER_DEMO = b"%PDF-1.4\n% Extrait de casier judiciaire (bulletin n. 3) - document de demonstration LuluSchools.\n"
RETENTION_CASIER = timedelta(days=30)  # recrutement/router.py::CASIER_JUDICIAIRE_RETENTION_JOURS
CRITERES = (("cv", 0.4, 50.0), ("diplome", 0.6, 55.0))


def _titre_et_matiere(type_etab: TypeEtablissement, matiere: str | None, niveau: str) -> tuple[str, str | None]:
    if type_etab == TypeEtablissement.EP:
        return f"Instituteur / Institutrice — {niveau}", None
    if type_etab == TypeEtablissement.ES:
        return f"Professeur de {matiere}", matiere
    if type_etab == TypeEtablissement.CA:
        return f"Alphabétiseur / Alphabétiseuse — {matiere}", matiere
    return f"Enseignant-chercheur en {matiere}", matiere


def _poste(ctx: Contexte, etab: Etablissement, titre: str, matiere: str | None, ouvert_le: datetime) -> Poste:
    minimum = float(ctx.rng.choice([90000, 110000, 130000, 160000] if etab.type != TypeEtablissement.UP else [250000, 300000, 350000]))
    poste = Poste(
        id=new_id(), etablissement_id=etab.id, titre=titre, matiere=matiere,
        description=f"{etab.nom} recrute : {titre.lower()}. Poste à pourvoir pour l'année {ctx.annee}.",
        remuneration_min=minimum, remuneration_max=minimum + 40000 if ctx.rng.random() < 0.6 else None,
        statut=StatutPoste.OUVERT, created_at=ouvert_le,
    )
    ctx.ajouter(poste)
    for type_document, coefficient, seuil in CRITERES:
        ctx.ajouter(CritereDocumentPoste(
            id=new_id(), poste_id=poste.id, type_document=type_document, coefficient=coefficient, seuil_minimal=seuil
        ))
    return poste


def _candidature(
    ctx: Contexte, poste: Poste, enseignant, depose_le: datetime, *, notes: dict[str, float | None]
) -> Candidature:
    """`notes` : note IA par type de document, None = echec de notation (revision manuelle).
    Statut et score calcules comme recrutement/router.py::_reevaluer_candidature."""
    candidature = Candidature(
        id=new_id(), poste_id=poste.id, enseignant_id=enseignant.id,
        statut=StatutCandidature.EN_EVALUATION, created_at=depose_le,
    )
    for i, (type_document, _, _) in enumerate(CRITERES):
        note = notes[type_document]
        ctx.ajouter(DocumentCandidature(
            id=new_id(), candidature_id=candidature.id, type_document=type_document,
            lulufiles_file_id=ctx.fichiers.piece_candidature(type_document, ctx.sequence("piece") + i),
            note_ia=round(note, 1) if note is not None else None,
            statut=StatutDocument.NOTE if note is not None else StatutDocument.ECHEC_NOTATION,
        ))
    if all(n is not None for n in notes.values()):
        poids = sum(c for _, c, _ in CRITERES)
        candidature.score = round(sum(notes[t] * c for t, c, _ in CRITERES) / poids, 1)
        if any(notes[t] < seuil for t, _, seuil in CRITERES):
            candidature.statut = StatutCandidature.REJETEE
            candidature.rejetee_le = depose_le + timedelta(minutes=ctx.rng.randint(2, 30))
    ctx.ajouter(candidature)
    return candidature


def _casier(ctx: Contexte, candidature: Candidature, admin, verdict: StatutVerificationCasier) -> None:
    depose_le = candidature.created_at
    verification = VerificationCasierJudiciaire(
        id=new_id(), candidature_id=candidature.id, nom_fichier="casier-judiciaire.pdf", statut=verdict,
        date_suppression_prevue=depose_le + RETENTION_CASIER,
    )
    if verdict == StatutVerificationCasier.EN_ATTENTE:
        # Contenu conserve jusqu'a l'echeance de retention (Art. 395), puis purge au demarrage
        # du service. Chiffre avec la cle de la base cible - sinon, pas de document du tout.
        encore_conserve = depose_le + RETENTION_CASIER > ctx.maintenant
        if encore_conserve and ctx.casier_chiffrable:
            verification.contenu_chiffre = chiffrer_bytes(CASIER_DEMO)
    else:
        # Verdict rendu : le contenu est purge immediatement, seul le statut reste.
        verification.verifie_par_utilisateur_id = admin.id
        verification.date_verification = depose_le + timedelta(days=ctx.rng.randint(1, 6))
        if verdict == StatutVerificationCasier.NON_CONFORME and candidature.statut == StatutCandidature.EN_EVALUATION:
            candidature.statut = StatutCandidature.REJETEE
            candidature.rejetee_le = verification.date_verification
    ctx.ajouter(verification)


def _contrat(ctx: Contexte, candidature: Candidature, poste: Poste, etab: Etablissement, cree_le: datetime,
             date_fin: date, signe: bool) -> Contrat:
    contrat = Contrat(
        id=new_id(), candidature_id=candidature.id, enseignant_id=candidature.enseignant_id, etablissement_id=etab.id,
        syllabus=f"Enseignement : {poste.titre}. Volume horaire et programme conformes au référentiel national.",
        date_fin=date_fin, statut=StatutContrat.SIGNE if signe else StatutContrat.EN_ATTENTE_SIGNATURE,
        created_at=cree_le,
    )
    if signe:
        horodatage = cree_le + timedelta(hours=ctx.rng.randint(2, 72))
        contrat.signature_horodatage = horodatage
        contrat.signature_hash_document = hashlib.sha256(f"{contrat.id}{contrat.syllabus}{date_fin}".encode()).hexdigest()
        contrat.signature_image_lulufiles_id = ctx.fichiers.signature(ctx.sequence("signature"))
    candidature.statut = StatutCandidature.RETENUE
    poste.statut = StatutPoste.POURVU
    ctx.ajouter(contrat)
    return contrat


def _notes_retenues(ctx: Contexte) -> dict[str, float]:
    return {"cv": ctx.rng.uniform(62, 96), "diplome": ctx.rng.uniform(64, 97)}


def _notes_quelconques(ctx: Contexte) -> dict[str, float | None]:
    return {t: (None if ctx.rng.random() < 0.08 else ctx.rng.uniform(35, 92)) for t, _, _ in CRITERES}


def _recruter(ctx: Contexte, etab: Etablissement, matiere: str | None, niveau: str) -> None:
    """Un poste pourvu : un gagnant sous contrat, et 0 a 2 autres candidats."""
    admin = ctx.admin_par_etab[etab.id]
    titre, matiere_poste = _titre_et_matiere(etab.type, matiere, niveau)
    reconduit = ctx.rng.random() < 0.3  # deja en poste l'an dernier, contrat reconduit
    ouvert_le = ctx.rentree - timedelta(days=ctx.rng.randint(45, 110) + (365 if reconduit else 0))
    poste = _poste(ctx, etab, titre, matiere_poste, ouvert_le)

    gagnant = ctx.enseignant(ouvert_le - timedelta(days=ctx.rng.randint(1, 20)))
    candidature = _candidature(ctx, poste, gagnant, ouvert_le + timedelta(days=ctx.rng.randint(1, 10)), notes=_notes_retenues(ctx))
    _casier(ctx, candidature, admin, StatutVerificationCasier.CONFORME)

    for _ in range(ctx.rng.randint(0, 2)):
        autre = ctx.enseignant(ouvert_le - timedelta(days=ctx.rng.randint(1, 30)))
        c = _candidature(ctx, poste, autre, ouvert_le + timedelta(days=ctx.rng.randint(1, 14)), notes=_notes_quelconques(ctx))
        verdict = ctx.rng.choice([StatutVerificationCasier.CONFORME, StatutVerificationCasier.EN_ATTENTE])
        _casier(ctx, c, admin, verdict)

    contrat_le = candidature.created_at + timedelta(days=ctx.rng.randint(8, 20))
    premiere_annee = int(ctx.annee.split("-")[0])
    if reconduit:
        # Contrat de l'an dernier (echu fin juin), reconduit par l'A+ et accepte.
        ancien = _contrat(ctx, candidature, poste, etab, contrat_le, date(premiere_annee, 6, 30), signe=True)
        nouveau = Contrat(
            id=new_id(), candidature_id=candidature.id, enseignant_id=gagnant.id, etablissement_id=etab.id,
            syllabus=ancien.syllabus, date_fin=ctx.fin_annee.replace(day=30, month=6),
            statut=StatutContrat.SIGNE,
            # Proposee dans les 30 jours precedant l'echeance (RECONDUCTION_FENETRE_JOURS).
            created_at=datetime.combine(ancien.date_fin, datetime.min.time(), ctx.maintenant.tzinfo) - timedelta(days=ctx.rng.randint(5, 25)),
        )
        nouveau.signature_horodatage = nouveau.created_at + timedelta(days=ctx.rng.randint(1, 4))
        nouveau.signature_hash_document = hashlib.sha256(f"{nouveau.id}{nouveau.syllabus}".encode()).hexdigest()
        nouveau.signature_image_lulufiles_id = ancien.signature_image_lulufiles_id
        ctx.ajouter(nouveau)
        ctx.ajouter(PropositionReconduction(
            id=new_id(), contrat_precedent_id=ancien.id, nouveau_contrat_id=nouveau.id,
            statut=StatutProposition.ACCEPTEE, created_at=nouveau.created_at,
        ))
        signe = True
    else:
        signe = ctx.rng.random() < 0.95
        _contrat(ctx, candidature, poste, etab, contrat_le, ctx.fin_annee.replace(day=30, month=6), signe=signe)

    if signe:
        ctx.enseignants_par_etab[etab.id].append(gagnant)
        ctx.matiere_enseignant[gagnant.id] = matiere


def _poste_ouvert(ctx: Contexte, etab: Etablissement, matiere: str | None, niveau: str) -> None:
    """Poste en cours de recrutement : de quoi exercer tous les ecrans de l'A+."""
    admin = ctx.admin_par_etab[etab.id]
    titre, matiere_poste = _titre_et_matiere(etab.type, matiere, niveau)
    ouvert_le = ctx.maintenant - timedelta(days=ctx.rng.randint(10, 24))
    poste = _poste(ctx, etab, titre, matiere_poste, ouvert_le)
    for i in range(ctx.rng.randint(2, 4)):
        candidat = ctx.enseignant(ouvert_le - timedelta(days=ctx.rng.randint(1, 60)))
        depose = ctx.instant(ouvert_le, ctx.maintenant - timedelta(days=1))
        if i == 0:
            notes = _notes_retenues(ctx)  # dossier complet, casier a examiner par l'A+
        elif i == 1:
            notes = {"cv": ctx.rng.uniform(30, 45), "diplome": ctx.rng.uniform(60, 90)}  # rejet automatique
        else:
            notes = _notes_quelconques(ctx)
        c = _candidature(ctx, poste, candidat, depose, notes=notes)
        _casier(ctx, c, admin, StatutVerificationCasier.EN_ATTENTE)
        if c.statut == StatutCandidature.REJETEE and ctx.rng.random() < 0.6:
            # Contestation dans le delai (5 jours ouvres) : la candidature repasse EN_EVALUATION
            # tant que l'A+ n'a pas tranche (recrutement/router.py::contester_candidature).
            deposee = c.rejetee_le + timedelta(hours=ctx.rng.randint(3, 60))
            tranchee = ctx.rng.random() < 0.4 and deposee + timedelta(days=2) < ctx.maintenant
            decision = ctx.rng.choice([StatutContestation.ACCEPTEE, StatutContestation.REJETEE]) if tranchee else StatutContestation.EN_ATTENTE
            ctx.ajouter(Contestation(
                id=new_id(), candidature_id=c.id, motif=ctx.rng.choice(MOTIFS_CONTESTATION_RECRUTEMENT),
                statut=decision, created_at=deposee,
                motif_decision=("Notes confirmées après relecture du document." if decision == StatutContestation.REJETEE
                                else "Document relu : la candidature est réexaminée." if decision == StatutContestation.ACCEPTEE else None),
                decided_at=deposee + timedelta(days=2) if tranchee else None,
            ))
            c.statut = StatutCandidature.REJETEE if decision == StatutContestation.REJETEE else StatutCandidature.EN_EVALUATION


def recruter_et_affecter(ctx: Contexte, etab: Etablissement) -> None:
    classes = ctx.classes_par_etab[etab.id]
    matieres_principales: list[str | None]
    if etab.type == TypeEtablissement.EP:
        # Primaire : un instituteur (polyvalent) par classe.
        besoins = [(None, c.niveau) for c in classes]
    else:
        # Secondaire/superieur : environ un enseignant pour deux classes, repartis sur les
        # matieres les plus enseignees de l'etablissement.
        frequence: dict[str, int] = {}
        for c in classes:
            for m in ctx.matieres_par_classe[c.id]:
                frequence[m] = frequence.get(m, 0) + 1
        matieres_principales = [m for m, _ in sorted(frequence.items(), key=lambda kv: -kv[1])]
        n = max(3, math.ceil(len(classes) * 0.6))
        besoins = [(matieres_principales[i % len(matieres_principales)], classes[0].niveau) for i in range(n)]

    for matiere, niveau in besoins:
        _recruter(ctx, etab, matiere, niveau)
    _poste_ouvert(ctx, etab, besoins[0][0], besoins[0][1])
    _affecter(ctx, etab)


def _affecter(ctx: Contexte, etab: Etablissement) -> None:
    """Affectations (AffectationEnseignant) : un professeur principal par classe, puis les
    enseignants de matiere dont la matiere est enseignee dans la classe."""
    enseignants = list(ctx.enseignants_par_etab[etab.id])
    if not enseignants:
        raise RuntimeError(f"Aucun enseignant sous contrat signe pour {etab.nom}")
    classes = ctx.classes_par_etab[etab.id]
    for i, classe in enumerate(classes):
        principal = enseignants[i % len(enseignants)]
        _affectation(ctx, classe.id, principal, principal=True)
        if etab.type == TypeEtablissement.EP:
            continue
        for enseignant in enseignants:
            matiere = ctx.matiere_enseignant.get(enseignant.id)
            deja = any(a.enseignant.id == enseignant.id for a in ctx.affectations_par_classe[classe.id])
            if not deja and matiere in ctx.matieres_par_classe[classe.id] and ctx.rng.random() < 0.7:
                _affectation(ctx, classe.id, enseignant, principal=False)


def _affectation(ctx: Contexte, classe_id: str, enseignant, principal: bool) -> None:
    ctx.ajouter(AffectationEnseignant(
        id=new_id(), enseignant_id=enseignant.id, classe_id=classe_id, est_professeur_principal=principal,
        created_at=ctx.rentree - timedelta(days=ctx.rng.randint(1, 10)),
    ))
    ctx.affectations_par_classe[classe_id].append(
        Affectation(enseignant=enseignant, matiere=ctx.matiere_enseignant.get(enseignant.id), principal=principal)
    )
