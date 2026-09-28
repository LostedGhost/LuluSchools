from sqlalchemy.orm import Session

from app.modules.evaluations.models import Devoir, NatureEvaluation, Soumission, StatutSoumission
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.pedagogie.models import Cours, Quiz, TentativeQuiz


def _quiz_reussis(db: Session, eleve: Eleve) -> list[dict]:
    """UC-38.1 : une ligne par quiz reussi au moins une fois (tentatives illimitees,
    voir Quiz docstring) - on ne garde que la meilleure tentative reussie de chaque
    quiz, jamais chaque tentative individuelle."""
    tentatives = (
        db.query(TentativeQuiz)
        .filter(TentativeQuiz.eleve_id == eleve.id, TentativeQuiz.reussie.is_(True))
        .order_by(TentativeQuiz.created_at.asc())
        .all()
    )
    meilleure_par_quiz: dict[str, TentativeQuiz] = {}
    for tentative in tentatives:
        actuelle = meilleure_par_quiz.get(tentative.quiz_id)
        if actuelle is None or tentative.score > actuelle.score:
            meilleure_par_quiz[tentative.quiz_id] = tentative

    resultats = []
    for tentative in meilleure_par_quiz.values():
        quiz = db.get(Quiz, tentative.quiz_id)
        cours = db.get(Cours, quiz.cours_id) if quiz is not None else None
        resultats.append(
            {
                "quiz_id": tentative.quiz_id,
                "cours_titre": cours.titre if cours is not None else "Cours supprimé",
                "cours_chapitre": cours.chapitre if cours is not None else "",
                "score": tentative.score,
                "date": tentative.created_at,
            }
        )
    resultats.sort(key=lambda r: r["date"], reverse=True)
    return resultats


def _cours_suivis(db: Session, eleve: Eleve) -> list[dict]:
    """UC-38.1 : aucun modele de suivi/completion n'existe (voir Cours) - "suivi" veut
    dire ici "mis a disposition dans une classe ou l'eleve a ete valide", passee ou
    actuelle, pas seulement la classe courante."""
    classe_ids = [
        row[0]
        for row in db.query(Inscription.classe_id)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .distinct()
        .all()
    ]
    if not classe_ids:
        return []
    cours = db.query(Cours).filter(Cours.classe_id.in_(classe_ids)).order_by(Cours.created_at.asc()).all()
    return [{"id": c.id, "titre": c.titre, "chapitre": c.chapitre, "format": c.format.value} for c in cours]


def _moyennes_par_matiere(db: Session, eleve: Eleve) -> list[dict]:
    """UC-38.1 : moyenne simple (non ponderee par un referentiel de coefficients,
    contrairement au bulletin officiel - voir evaluations/router.py::_calculer_et_
    enregistrer_bulletin) par matiere, sur toutes les soumissions deja corrigees de
    devoirs SOMMATIFS. Volontairement plus simple que le bulletin : le passeport est un
    recapitulatif informel, pas un document officiel."""
    soumissions = (
        db.query(Soumission, Devoir)
        .join(Devoir, Devoir.id == Soumission.devoir_id)
        .filter(
            Soumission.eleve_id == eleve.id,
            Soumission.statut == StatutSoumission.CORRIGEE,
            Soumission.note.isnot(None),
            Devoir.nature == NatureEvaluation.SOMMATIVE,
        )
        .all()
    )
    notes_par_matiere: dict[str, list[float]] = {}
    for soumission, devoir in soumissions:
        points_max_devoir = sum(q.points_max for q in devoir.questions) or 1.0
        note_normalisee = (soumission.note / points_max_devoir) * 100
        notes_par_matiere.setdefault(devoir.matiere, []).append(note_normalisee)

    return [
        {"matiere": matiere, "moyenne": sum(notes) / len(notes)}
        for matiere, notes in sorted(notes_par_matiere.items())
    ]


def _badges(quiz_reussis: list[dict], moyennes: list[dict]) -> list[dict]:
    """UC-38.1 : badges derives directement des donnees deja agregees ci-dessus (jamais
    une nouvelle saisie ni un critere arbitraire non tracable) - meme esprit que les
    medailles deja affichees cote frontend (gamification.tsx), mais reellement calcules."""
    badges = []
    nb_quiz = len(quiz_reussis)
    if nb_quiz >= 1:
        badges.append({"id": "premier-quiz", "label": "Premier quiz réussi"})
    if nb_quiz >= 5:
        badges.append({"id": "cinq-quiz", "label": "5 quiz reussis"})
    if nb_quiz >= 20:
        badges.append({"id": "vingt-quiz", "label": "20 quiz reussis"})
    for moyenne in moyennes:
        if moyenne["moyenne"] >= 90:
            badges.append({"id": f"excellence-{moyenne['matiere']}", "label": f"Excellence en {moyenne['matiere']}"})
    return badges


def construire_passeport(db: Session, eleve_utilisateur_id: str) -> dict | None:
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur_id).first()
    if eleve is None:
        return None

    quiz_reussis = _quiz_reussis(db, eleve)
    cours_suivis = _cours_suivis(db, eleve)
    moyennes = _moyennes_par_matiere(db, eleve)
    badges = _badges(quiz_reussis, moyennes)

    return {
        "eleve_utilisateur_id": eleve_utilisateur_id,
        "eleve_nom": eleve.nom,
        "eleve_prenom": eleve.prenom,
        "quiz_reussis": quiz_reussis,
        "cours_suivis": cours_suivis,
        "moyennes_par_matiere": moyennes,
        "badges": badges,
    }
