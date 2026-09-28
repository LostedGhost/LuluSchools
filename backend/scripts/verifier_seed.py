"""Verification d'un jeu de donnees (seed) : relit la base et controle les invariants
metier que les routeurs garantissent. Lance automatiquement a la fin de seed_mega.py ;
utilisable seul :  cd backend && python scripts/verifier_seed.py

Chaque regle compte ses violations et en montre quelques exemples. Code de sortie 0 si
tout est coherent, 2 sinon.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: F401,E402
from app.core.database import SessionLocal  # noqa: E402
from app.modules.actes.models import DemandeActeAcademique, StatutDemandeActe, TypeActeAcademique  # noqa: E402
from app.modules.billetterie.models import BilletEvenement, Evenement, StatutBillet, StatutEvenement  # noqa: E402
from app.modules.coffre_fort.models import ModuleDepenseCoffreFort, PlafondFamilial, ValidationParentale  # noqa: E402
from app.modules.controle_acces.models import DesignationControleur  # noqa: E402
from app.modules.cours_direct.models import ConsentementCameraLive, ParticipationLive, SessionLive, StatutSessionLive  # noqa: E402
from app.modules.etablissements.models import AdminEtablissement, AffectationEnseignant, Classe, Etablissement, TypeEtablissement  # noqa: E402
from app.modules.evaluations import periodes  # noqa: E402
from app.modules.evaluations.models import (  # noqa: E402
    Bulletin, Devoir, NatureEvaluation, QuestionDevoir, ReferentielCoefficient, Soumission, StatutReferentiel, StatutSoumission,
)
from app.modules.identite.models import RoleUtilisateur, Utilisateur  # noqa: E402
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription  # noqa: E402
from app.modules.marketplace.models import AnnonceMarketplace, StatutAnnonce, StatutTransactionMarketplace, TransactionMarketplace  # noqa: E402
from app.modules.messagerie.models import Conversation, Message, ParticipantConversation, SignalementMessage, TypeConversation  # noqa: E402
from app.modules.micro_jobs.models import MissionMicroJob, OffreMicroJob, StatutMissionMicroJob, StatutOffreMicroJob  # noqa: E402
from app.modules.pedagogie.models import (  # noqa: E402
    AlerteElProfessor, Cours, FormatCours, MessageElProfessorFamille, OrigineAlerteElProfessor, Quiz,
    SessionElProfessorEnseignant, SessionElProfessorFamille, SessionElProfessorTuteur, TentativeQuiz,
)
from app.modules.recrutement.models import (  # noqa: E402
    Candidature, Contestation, Contrat, Poste, StatutCandidature, StatutContestation, StatutContrat, StatutPoste,
    StatutVerificationCasier, VerificationCasierJudiciaire,
)
from app.modules.services_scolaires.models import LigneTransport, StatutTicket, TicketCantine, TicketTransport, TypeRepasCantine  # noqa: E402

PLACEHOLDER = "00000000-0000-0000-0000-000000000000"


def _utc(moment: datetime | None) -> datetime | None:
    if moment is None:
        return None
    # Toujours ramene en UTC : la connexion PostgreSQL peut renvoyer l'heure locale du serveur.
    return moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _age(naissance: date, reference: date) -> int:
    return reference.year - naissance.year - ((reference.month, reference.day) < (naissance.month, naissance.day))


class Controle:
    def __init__(self) -> None:
        self.resultats: list[tuple[str, int, list]] = []

    def regle(self, libelle: str, violations: list) -> None:
        self.resultats.append((libelle, len(violations), violations[:3]))


def verifier() -> bool:
    db = SessionLocal()
    c = Controle()
    maintenant = datetime.now(timezone.utc)
    aujourdhui = maintenant.date()
    try:
        tout = lambda modele: db.query(modele).all()  # noqa: E731
        users = {u.id: u for u in tout(Utilisateur)}
        etabs = {e.id: e for e in tout(Etablissement)}
        classes = {k.id: k for k in tout(Classe)}
        eleves = {e.id: e for e in tout(Eleve)}
        eleve_par_user = {e.utilisateur_id: e for e in eleves.values() if e.utilisateur_id}
        inscriptions = tout(Inscription)
        validees = [i for i in inscriptions if i.statut == StatutInscription.VALIDEE]
        classe_de_eleve = {i.eleve_id: i.classe_id for i in validees}
        etab_de_user_eleve = {eleves[i.eleve_id].utilisateur_id: classes[i.classe_id].etablissement_id for i in validees if eleves[i.eleve_id].utilisateur_id}
        admins = {a.utilisateur_id: a.etablissement_id for a in tout(AdminEtablissement)}
        contrats = tout(Contrat)
        signes = {(k.enseignant_id, k.etablissement_id) for k in contrats if k.statut == StatutContrat.SIGNE}
        affectations = tout(AffectationEnseignant)
        affecte = {(a.enseignant_id, a.classe_id) for a in affectations}
        candidatures = {k.id: k for k in tout(Candidature)}
        casiers = {v.candidature_id: v for v in tout(VerificationCasierJudiciaire)}
        postes = {p.id: p for p in tout(Poste)}

        # ─── Etablissements ───
        uac = [e for e in etabs.values() if e.nom == "Université d'Abomey-Calavi"]
        c.regle("L'Université d'Abomey-Calavi existe, active, avec classes, enseignants et étudiants",
                [] if uac and uac[0].actif and any(k.etablissement_id == uac[0].id for k in classes.values())
                and any(e == uac[0].id for _, e in signes) and any(v == uac[0].id for v in etab_de_user_eleve.values())
                else ["UAC absente ou incomplète"])
        c.regle("Chaque établissement a un A+", [e.nom for e in etabs.values() if e.id not in admins.values()])

        # ─── Recrutement ───
        c.regle("Un contrat exige un casier vérifié CONFORME",
                [k.id for k in contrats if casiers.get(k.candidature_id) is None or casiers[k.candidature_id].statut != StatutVerificationCasier.CONFORME])
        contrats_par_candidature = defaultdict(list)
        for k in contrats:
            contrats_par_candidature[k.candidature_id].append(k)
        c.regle("Candidature RETENUE ⇔ contrat", [k.id for k in candidatures.values() if (k.statut == StatutCandidature.RETENUE) != bool(contrats_par_candidature[k.id])])
        retenues_par_poste = Counter(k.poste_id for k in candidatures.values() if k.statut == StatutCandidature.RETENUE)
        c.regle("Poste POURVU : exactement une candidature retenue ; poste OUVERT : aucune",
                [p.id for p in postes.values() if retenues_par_poste[p.id] != (1 if p.statut == StatutPoste.POURVU else 0)])
        c.regle("Casier jugé : document purgé ; casier expiré : document purgé",
                [v.id for v in casiers.values() if v.contenu_chiffre is not None and (
                    v.statut != StatutVerificationCasier.EN_ATTENTE or _utc(v.date_suppression_prevue) < maintenant)])
        c.regle("Candidature rejetée : date de rejet renseignée",
                [k.id for k in candidatures.values() if k.statut == StatutCandidature.REJETEE and k.rejetee_le is None])
        c.regle("Contestation en attente/acceptée : candidature réexaminée (EN_EVALUATION) ; rejetée : REJETEE",
                [x.id for x in tout(Contestation) if (candidatures[x.candidature_id].statut == StatutCandidature.EN_EVALUATION)
                 != (x.statut != StatutContestation.REJETEE)])
        c.regle("Affectation : enseignant sous contrat SIGNÉ avec l'établissement de la classe",
                [a.id for a in affectations if (a.enseignant_id, classes[a.classe_id].etablissement_id) not in signes])
        pp = Counter(a.classe_id for a in affectations if a.est_professeur_principal)
        classes_peuplees = {i.classe_id for i in validees}
        c.regle("Chaque classe peuplée a exactement un professeur principal", [k for k in classes_peuplees if pp[k] != 1])

        # ─── Inscriptions ───
        valides_par_classe = Counter(i.classe_id for i in validees)
        c.regle("Inscriptions validées ≤ capacité de la classe", [k for k, n in valides_par_classe.items() if n > classes[k].capacite])
        c.regle("Compte élève ⇔ inscription validée, identifiant = matricule",
                [e.id for e in eleves.values() if bool(e.utilisateur_id) != (e.id in classe_de_eleve)
                 or (e.utilisateur_id and users[e.utilisateur_id].login_id != e.matricule)])
        violations = []
        for i in inscriptions:
            e = eleves[i.eleve_id]
            mineur = _age(e.date_naissance, _utc(i.created_at).date()) < 16
            if i.statut == StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL and (not mineur or i.consentement_parental_horodatage):
                violations.append(i.id)
            if i.statut in (StatutInscription.SOUMISE, StatutInscription.VALIDEE) and mineur != bool(i.consentement_parental_horodatage):
                violations.append(i.id)
        c.regle("Consentement parental horodaté pour les moins de 16 ans uniquement (Art. 446)", violations)
        c.regle("L'élève porte le nom de famille de son tuteur", [e.id for e in eleves.values() if users[e.tuteur_id].nom != e.nom])

        # ─── Pédagogie / évaluations ───
        cours = tout(Cours)
        c.regle("Cours publié par un enseignant affecté à la classe", [x.id for x in cours if (x.enseignant_id, x.classe_id) not in affecte])
        c.regle("Cours PDF : fichier + texte extrait ; cours texte : contenu",
                [x.id for x in cours if (x.format == FormatCours.PDF and not (x.lulufiles_file_id and x.texte_extrait))
                 or (x.format == FormatCours.TEXTE and not x.contenu_texte)])
        devoirs = {d.id: d for d in tout(Devoir)}
        c.regle("Devoir donné par un enseignant affecté à la classe", [d.id for d in devoirs.values() if (d.enseignant_id, d.classe_id) not in affecte])
        points = defaultdict(float)
        for q in tout(QuestionDevoir):
            points[q.devoir_id] += q.points_max
        soumissions = tout(Soumission)
        c.regle("Copie déposée avant l'échéance, par un élève de la classe",
                [s.id for s in soumissions if _utc(s.created_at) > _utc(devoirs[s.devoir_id].date_limite)
                 or classe_de_eleve.get(s.eleve_id) != devoirs[s.devoir_id].classe_id])
        c.regle("Copie corrigée : note entre 0 et le total des points ; jamais bloquée « en correction »",
                [s.id for s in soumissions if s.statut == StatutSoumission.EN_CORRECTION
                 or (s.statut == StatutSoumission.CORRIGEE and not (0 <= (s.note or -1) <= points[s.devoir_id]))])
        coefficients = {(r.niveau, r.matiere): r.coefficient for r in tout(ReferentielCoefficient) if r.statut == StatutReferentiel.VALIDE}
        soumission_de = {(s.devoir_id, s.eleve_id): s for s in soumissions}
        ecarts = []
        for b in tout(Bulletin):
            classe = classes[b.classe_id]
            notes = []
            type_etab = etabs[classe.etablissement_id].type
            for d in devoirs.values():
                if d.classe_id != b.classe_id or d.nature != NatureEvaluation.SOMMATIVE:
                    continue
                if periodes.periode_de(d.date_limite, type_etab, classe.annee_academique).code != b.periode:
                    continue
                s = soumission_de.get((d.id, b.eleve_id))
                coef = coefficients.get((classe.niveau, d.matiere), 1.0)
                if s is None:
                    if _utc(d.date_limite) < maintenant:
                        notes.append((0.0, coef))
                elif s.statut == StatutSoumission.CORRIGEE:
                    notes.append((s.note / (points[d.id] or 1.0) * 100, coef))
            attendu = sum(n * k for n, k in notes) / sum(k for _, k in notes) if notes else None
            if attendu is None or abs(attendu - b.moyenne_generale) > 0.01:
                ecarts.append(b.id)
        c.regle("Moyenne du bulletin = calcul de l'application (sur 100, pondérée)", ecarts)
        quiz_classe = {q.id: next(x.classe_id for x in cours if x.id == q.cours_id) for q in tout(Quiz)} if cours else {}
        c.regle("Tentative de quiz par un élève de la classe du cours",
                [t.id for t in tout(TentativeQuiz) if classe_de_eleve.get(t.eleve_id) != quiz_classe.get(t.quiz_id)])

        # ─── El Professor ───
        classes_enseignant = defaultdict(set)
        for a in affectations:
            classes_enseignant[a.enseignant_id].add(a.classe_id)
        c.regle("El Professor enseignant : élève d'une de ses classes",
                [s.id for s in tout(SessionElProfessorEnseignant) if s.eleve_utilisateur_id
                 and classe_de_eleve.get(eleve_par_user[s.eleve_utilisateur_id].id) not in classes_enseignant[s.enseignant_id]])
        c.regle("El Professor tuteur/famille : l'élève est l'enfant du tuteur",
                [s.id for s in tout(SessionElProfessorTuteur) + tout(SessionElProfessorFamille)
                 if eleve_par_user[s.eleve_utilisateur_id].tuteur_id != s.tuteur_id])
        non_rejointes = {s.id for s in tout(SessionElProfessorFamille) if s.rejointe_le is None}
        c.regle("Fil familial : aucun message avant que l'enfant ne l'ait rejoint",
                [m.id for m in tout(MessageElProfessorFamille) if m.session_id in non_rejointes])
        c.regle("Alerte El Professor : établissement de l'élève concerné",
                [a.id for a in tout(AlerteElProfessor) if a.eleve_utilisateur_id and etab_de_user_eleve.get(a.eleve_utilisateur_id) != a.etablissement_id])

        # ─── Messagerie ───
        participants = defaultdict(set)
        for p in tout(ParticipantConversation):
            participants[p.conversation_id].add(p.utilisateur_id)
        conversations = {x.id: x for x in tout(Conversation)}
        staff = {RoleUtilisateur.ENSEIGNANT, RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL}
        violations = []
        for conv_id, membres in participants.items():
            a, b = (users[m] for m in membres)
            roles = {a.role, b.role}
            if RoleUtilisateur.ELEVE in roles and roles & staff:
                violations.append(conv_id)
            elif a.role == b.role == RoleUtilisateur.ELEVE and etab_de_user_eleve.get(a.id) != etab_de_user_eleve.get(b.id):
                violations.append(conv_id)
            elif roles == {RoleUtilisateur.ELEVE, RoleUtilisateur.TUTEUR}:
                enfant, parent = (a, b) if a.role == RoleUtilisateur.ELEVE else (b, a)
                if eleve_par_user[enfant.id].tuteur_id != parent.id:
                    violations.append(conv_id)
        c.regle("Messages privés conformes (pas de personnel ↔ élève, élèves du même établissement, tuteur ↔ son enfant)", violations)
        messages = {m.id: m for m in tout(Message)}
        membres_classe = defaultdict(set)
        for i in validees:
            if eleves[i.eleve_id].utilisateur_id:
                membres_classe[i.classe_id].add(eleves[i.eleve_id].utilisateur_id)
        for a in affectations:
            membres_classe[a.classe_id].add(a.enseignant_id)
        c.regle("Auteur de message membre de la conversation",
                [m.id for m in messages.values() if m.auteur_id not in (
                    participants[m.conversation_id] if conversations[m.conversation_id].type == TypeConversation.DM
                    else membres_classe[conversations[m.conversation_id].classe_id])])
        c.regle("Signalement par un autre membre que l'auteur", [s.id for s in tout(SignalementMessage) if messages[s.message_id].auteur_id == s.signale_par_id])

        # ─── Cours en direct ───
        sessions = {s.id: s for s in tout(SessionLive)}
        c.regle("Session terminée dans le passé, planifiée dans le futur, jamais « en cours » figée",
                [s.id for s in sessions.values() if s.statut == StatutSessionLive.EN_COURS
                 or (s.statut == StatutSessionLive.TERMINEE) != (_utc(s.date_heure) < maintenant)])
        consentis = {k.eleve_utilisateur_id for k in tout(ConsentementCameraLive)}
        c.regle("Participant inscrit dans la classe ; caméra seulement avec consentement",
                [p.id for p in tout(ParticipationLive) if (p.camera_autorisee and p.eleve_utilisateur_id not in consentis)
                 or classe_de_eleve.get(eleve_par_user[p.eleve_utilisateur_id].id) != sessions[p.session_id].classe_id])

        # ─── Services, billetterie, actes ───
        lignes = {x.id: x.etablissement_id for x in tout(LigneTransport)}
        repas = {x.id: x.etablissement_id for x in tout(TypeRepasCantine)}
        violations, vus = [], set()
        for t, service, etab_id, jour in [(t, t.ligne_id, lignes[t.ligne_id], t.date_trajet) for t in tout(TicketTransport)] + \
                                         [(t, t.type_repas_id, repas[t.type_repas_id], t.date_service) for t in tout(TicketCantine)]:
            cle = (t.utilisateur_id, service, jour)
            if t.statut in (StatutTicket.ACHETE, StatutTicket.VALIDE):
                if cle in vus:
                    violations.append(t.id)
                vus.add(cle)
            if t.statut == StatutTicket.VALIDE and (not t.paiement_confirme or jour > aujourdhui):
                violations.append(t.id)
            if etab_de_user_eleve.get(t.utilisateur_id) != etab_id:
                violations.append(t.id)
        c.regle("Tickets : un par personne/jour/service, validé seulement payé et le jour même ou avant, élève de l'établissement", violations)
        evenements = {e.id: e for e in tout(Evenement)}
        billets = tout(BilletEvenement)
        doublons = Counter((b.evenement_id, b.utilisateur_id) for b in billets)
        c.regle("Billets : un par personne, validé seulement payé et à la date de l'événement, remboursés si annulé",
                [b.id for b in billets if doublons[(b.evenement_id, b.utilisateur_id)] > 1
                 or (b.statut == StatutBillet.VALIDE and (not b.paiement_confirme or _utc(evenements[b.evenement_id].date_heure) > maintenant))
                 or (evenements[b.evenement_id].statut == StatutEvenement.ANNULE and b.statut != StatutBillet.REMBOURSE)])
        c.regle("Contrôleur : enseignant sous contrat ou A+ de l'établissement",
                [d.id for d in tout(DesignationControleur) if (d.utilisateur_id, d.etablissement_id) not in signes and admins.get(d.utilisateur_id) != d.etablissement_id])
        types_acte = {t.id: t for t in tout(TypeActeAcademique)}
        violations = []
        for d in tout(DemandeActeAcademique):
            t = types_acte.get(d.type_acte_id)
            payant = t is not None and t.prix > 0
            if d.statut == StatutDemandeActe.SOUMISE and (not payant or d.paiement_confirme):
                violations.append(d.id)
            if d.statut != StatutDemandeActe.SOUMISE and not d.paiement_confirme:
                violations.append(d.id)
            if bool(d.document_final_lulufiles_id) and not (d.statut == StatutDemandeActe.ACCEPTEE and t is not None):
                violations.append(d.id)
            if t is not None and t.etablissement_id != classes[classe_de_eleve[d.eleve_id]].etablissement_id:
                violations.append(d.id)
        c.regle("Actes : payés avant traitement, document final pour un acte accepté, type de l'établissement de l'élève", violations)
        c.regle("Actes à modèle (attestation, relevé) : livrés automatiquement dès le paiement",
                [d.id for d in tout(DemandeActeAcademique) if types_acte.get(d.type_acte_id) is not None
                 and types_acte[d.type_acte_id].modele_document and d.paiement_confirme and d.statut != StatutDemandeActe.ACCEPTEE])

        # ─── Économie étudiante ───
        etudiants = {u for u, e in etab_de_user_eleve.items() if etabs[e].type == TypeEtablissement.UP}
        offres = {o.id: o for o in tout(OffreMicroJob)}
        missions = tout(MissionMicroJob)
        missions_par_offre = Counter(m.offre_id for m in missions)
        violations = [o.id for o in offres.values() if (o.statut in (StatutOffreMicroJob.OUVERTE, StatutOffreMicroJob.FERMEE)) != o.paiement_confirme
                      or (o.statut == StatutOffreMicroJob.FERMEE) != (missions_par_offre[o.id] == 1)]
        for m in missions:
            if m.prestataire_id not in etudiants or m.prestataire_id == offres[m.offre_id].client_id:
                violations.append(m.id)
            if m.statut == StatutMissionMicroJob.PAYEE and not (users[m.prestataire_id].telephone and m.reference_paiement_prestataire):
                violations.append(m.id)
            if m.statut == StatutMissionMicroJob.TERMINEE_DECLAREE and _utc(m.date_limite_validation) <= maintenant:
                violations.append(m.id)
        c.regle("Micro-jobs : prestataire étudiant ≠ client, paiement avant ouverture, reversement avec numéro, pas d'échéance dépassée", violations)
        annonces = {a.id: a for a in tout(AnnonceMarketplace)}
        transactions = tout(TransactionMarketplace)
        violations = []
        en_cours = {StatutTransactionMarketplace.EN_ATTENTE_PAIEMENT, StatutTransactionMarketplace.PAIEMENT_CONFIRME,
                    StatutTransactionMarketplace.REMISE_DECLAREE, StatutTransactionMarketplace.CONTESTEE, StatutTransactionMarketplace.CONFIRMEE}
        for t in transactions:
            a = annonces[t.annonce_id]
            for u in (a.vendeur_id, t.acheteur_id):
                if etab_de_user_eleve.get(u) != a.etablissement_id or _age(eleve_par_user[u].date_naissance, aujourdhui) < 16:
                    violations.append(t.id)
            attendu = StatutAnnonce.RESERVEE if t.statut in en_cours else StatutAnnonce.VENDUE if t.statut == StatutTransactionMarketplace.FINALISEE else StatutAnnonce.DISPONIBLE
            if a.statut != attendu or a.vendeur_id == t.acheteur_id:
                violations.append(t.id)
            if t.statut == StatutTransactionMarketplace.FINALISEE and not (t.reference_paiement_vendeur and users[a.vendeur_id].telephone):
                violations.append(t.id)
            if t.statut == StatutTransactionMarketplace.REMISE_DECLAREE and _utc(t.date_limite_confirmation) <= maintenant:
                violations.append(t.id)
        c.regle("Marketplace : étudiants ≥ 16 ans du même établissement, statut d'annonce cohérent, reversement avec numéro", violations)
        plafonds = {p.eleve_utilisateur_id: p for p in tout(PlafondFamilial)}
        references = {ModuleDepenseCoffreFort.MICRO_JOB: set(offres), ModuleDepenseCoffreFort.MARKETPLACE: {t.id for t in transactions},
                      ModuleDepenseCoffreFort.ACTE: {d.id for d in tout(DemandeActeAcademique)}}
        c.regle("Validation parentale : dépense réelle, au-dessus du seuil fixé par la famille",
                [v.id for v in tout(ValidationParentale) if v.reference_id not in references[v.module]
                 or v.eleve_utilisateur_id not in plafonds or v.montant <= (plafonds[v.eleve_utilisateur_id].seuil_validation or 0)])

        rembourses = [(TicketTransport, StatutTicket.REMBOURSE), (TicketCantine, StatutTicket.REMBOURSE),
                      (BilletEvenement, StatutBillet.REMBOURSE), (TransactionMarketplace, StatutTransactionMarketplace.REMBOURSEE),
                      (MissionMicroJob, StatutMissionMicroJob.REMBOURSEE)]
        c.regle("Remboursements passés effectués (aucun faux « à rembourser à la main »)",
                [r.id for modele, statut in rembourses for r in tout(modele) if r.statut == statut and r.paiement_confirme and not r.remboursement_effectue])

        # ─── Fichiers et dates ───
        colonnes = [(Cours, "lulufiles_file_id"), (Devoir, "sujet_lulufiles_file_id"), (Soumission, "copie_image_lulufiles_file_id"),
                    (DemandeActeAcademique, "document_final_lulufiles_id"), (Contrat, "signature_image_lulufiles_id")]
        c.regle("Aucun identifiant de fichier fictif", [f"{m.__tablename__}.{col}" for m, col in colonnes
                                                        if db.query(m).filter(getattr(m, col) == PLACEHOLDER).count()])
        futurs = []
        for modele in (Message, Soumission, Inscription, TentativeQuiz, Candidature, DemandeActeAcademique):
            futurs += [f"{modele.__tablename__}:{x.id}" for x in db.query(modele).all() if _utc(x.created_at) > maintenant + timedelta(minutes=1)]
        c.regle("Aucune date de création dans le futur", futurs)
    finally:
        db.close()

    print("VÉRIFICATION DE COHÉRENCE")
    ok = True
    for libelle, n, exemples in c.resultats:
        print(f"  {'OK ' if n == 0 else 'ÉCHEC'} {libelle}" + ("" if n == 0 else f" — {n} violation(s), ex. {exemples}"))
        ok = ok and n == 0
    print(f"{len(c.resultats)} règles contrôlées : {'tout est cohérent.' if ok else 'INCOHÉRENCES DÉTECTÉES.'}\n")
    return ok


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    raise SystemExit(0 if verifier() else 2)
