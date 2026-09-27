import io
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db, get_session_factory
from app.core.rate_limit import limiteur
from app.core.email import EmailDeliveryError, get_email_client
from app.core.files import get_files_client
from app.core.llm import (
    CorrectionError,
    DigestFamilleError,
    DocumentScoringError,
    ElProfessorError,
    QuizGenerationError,
    ResumeSessionLiveError,
    get_llm_client,
)
from app.core.security import create_access_token, decode_token, hash_password
from app.main import app
from app.modules.identite.models import RoleUtilisateur, Utilisateur


@pytest.fixture(autouse=True)
def _limitation_debit_desactivee():
    """Les fixtures ouvrent des dizaines de sessions depuis la meme IP de test : la
    limitation de debit est desactivee par defaut et reactivee explicitement par les
    tests qui la verifient (fixture `limitation_debit`)."""
    settings.rate_limit_enabled = False
    limiteur.reinitialiser()
    yield
    settings.rate_limit_enabled = False
    limiteur.reinitialiser()


@pytest.fixture()
def limitation_debit():
    settings.rate_limit_enabled = True
    limiteur.reinitialiser()
    yield


# Optionnel : rejouer toute la suite sur un vrai PostgreSQL (base dediee, videe a chaque
# test). SQLite masque certaines erreurs propres a Postgres (ex. DISTINCT sur colonne json).
_URL_TEST_POSTGRES = os.environ.get("LULU_TEST_DATABASE_URL")


@pytest.fixture()
def db_session():
    if _URL_TEST_POSTGRES:
        engine = create_engine(_URL_TEST_POSTGRES)
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class FakeEmailClient:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.should_fail = False

    def send_otp_email(self, to_email: str, to_name: str, code: str) -> None:
        if self.should_fail:
            raise EmailDeliveryError("echec simule")
        self.sent.append({"to_email": to_email, "to_name": to_name, "code": code})

    def send_temporary_credentials_email(
        self, to_email: str, to_name: str, login_id: str, mot_de_passe: str
    ) -> None:
        if self.should_fail:
            raise EmailDeliveryError("echec simule")
        self.sent.append(
            {
                "to_email": to_email,
                "to_name": to_name,
                "login_id": login_id,
                "mot_de_passe": mot_de_passe,
            }
        )

    def send_notification_email(self, to_email: str, to_name: str, subject: str, message: str) -> None:
        if self.should_fail:
            raise EmailDeliveryError("echec simule")
        self.sent.append({"to_email": to_email, "to_name": to_name, "subject": subject, "message": message})

    def send_password_reset_email(self, to_email: str, to_name: str, login_id: str, code: str) -> None:
        if self.should_fail:
            raise EmailDeliveryError("echec simule")
        self.sent.append({"to_email": to_email, "to_name": to_name, "reset_login_id": login_id, "reset_code": code})


@pytest.fixture()
def fake_email_client() -> FakeEmailClient:
    return FakeEmailClient()


class FakeFilesClient:
    def __init__(self) -> None:
        self.uploaded: list[dict] = []

    def upload(self, content: bytes, filename: str, content_type: str) -> str:
        file_id = str(uuid.uuid4())
        self.uploaded.append({"file_id": file_id, "filename": filename, "content_type": content_type})
        return file_id

    def get_signed_link(self, file_id: str, disposition: str = "attachment") -> str:
        return f"https://lulufiles-api.onrender.com/files/{file_id}/content?signed=1"


@pytest.fixture()
def fake_files_client() -> FakeFilesClient:
    return FakeFilesClient()


class FakeLLMClient:
    def __init__(self) -> None:
        self.scores_par_type: dict[str, float] = {}
        self.score_par_defaut = 90.0
        self.types_en_echec: set[str] = set()
        self.points_par_defaut_ratio = 1.0  # part de points_max accordee par defaut
        self.questions_en_echec_correction: set[str] = set()  # enonces qui echouent
        self.quiz_genere: list[dict] | None = None
        self.echec_generation_quiz = False
        self.reponse_el_professor = "Voici l'explication demandee."
        self.echec_el_professor = False
        self.note_copie_image_ratio = 1.0  # part de points_max_total accordee par defaut
        self.echec_correction_copie_image = False
        self.reponse_conseil_enseignant = "Voici mon conseil."
        self.echec_conseil_enseignant = False
        self.reponse_conseil_tuteur = "Voici mon conseil pour votre enfant."
        self.echec_conseil_tuteur = False
        self.reponse_resume_session_live = "Resume : la classe a revu les fractions."
        self.echec_resume_session_live = False
        self.reponse_conseil_famille = "Voici mon conseil pour vous deux."
        self.echec_conseil_famille = False
        self.reponse_digest_famille = "Cette semaine, votre enfant a bien avance."
        self.echec_digest_famille = False

    def noter_document(self, image_bytes: bytes, content_type: str, critere: str) -> float:
        for type_document in self.types_en_echec:
            if type_document in critere:
                raise DocumentScoringError("echec simule")
        for type_document, score in self.scores_par_type.items():
            if type_document in critere:
                return score
        return self.score_par_defaut

    def corriger_reponse(
        self, enonce: str, bareme_reponse: str, points_max: float, reponse_eleve: str, strict: bool
    ) -> float:
        if enonce in self.questions_en_echec_correction:
            raise CorrectionError("echec simule")
        return points_max * self.points_par_defaut_ratio

    def generer_quiz(self, contenu_cours: str, nombre_questions: int = 5) -> list[dict]:
        if self.echec_generation_quiz:
            raise QuizGenerationError("echec simule")
        if self.quiz_genere is not None:
            return self.quiz_genere
        return [
            {"enonce": f"Question {i + 1}", "choix": ["A", "B", "C", "D"], "reponse_correcte_index": 0}
            for i in range(nombre_questions)
        ]

    def repondre_question_el_professor(self, contenu_cours: str, historique: list[dict], question: str) -> str:
        if self.echec_el_professor:
            raise ElProfessorError("echec simule")
        return self.reponse_el_professor

    def corriger_copie_image(
        self, consigne_globale: str, points_max_total: float, image_bytes: bytes, content_type: str, strict: bool
    ) -> float:
        if self.echec_correction_copie_image:
            raise CorrectionError("echec simule")
        return points_max_total * self.note_copie_image_ratio

    def conseiller_enseignant(self, contexte_eleve: str | None, historique: list[dict], question: str) -> str:
        if self.echec_conseil_enseignant:
            raise ElProfessorError("echec simule")
        return self.reponse_conseil_enseignant

    def conseiller_tuteur(self, contexte_eleve: str | None, historique: list[dict], question: str) -> str:
        if self.echec_conseil_tuteur:
            raise ElProfessorError("echec simule")
        return self.reponse_conseil_tuteur

    def resumer_session_live(self, messages_chat: list[str], contenu_tableau: str) -> str:
        if self.echec_resume_session_live:
            raise ResumeSessionLiveError("echec simule")
        return self.reponse_resume_session_live

    def conseiller_famille(
        self, contexte_eleve: str | None, historique: list[dict], question: str, qui_parle: str
    ) -> str:
        if self.echec_conseil_famille:
            raise ElProfessorError("echec simule")
        return self.reponse_conseil_famille

    def generer_digest_famille(self, eleve_nom: str, sources: list[str]) -> str:
        if self.echec_digest_famille:
            raise DigestFamilleError("echec simule")
        return self.reponse_digest_famille


@pytest.fixture()
def fake_llm_client() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture()
def test_session_factory(db_session):
    """Sessionmaker lie au MEME moteur (StaticPool) que db_session, pour que les
    BackgroundTasks (qui ouvrent leur propre session via get_session_factory, la session
    de la requete etant deja fermee) voient les memes donnees en test."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind())


@pytest.fixture()
def client(db_session, test_session_factory, fake_email_client, fake_files_client, fake_llm_client):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_session_factory] = lambda: test_session_factory
    app.dependency_overrides[get_email_client] = lambda: fake_email_client
    app.dependency_overrides[get_files_client] = lambda: fake_files_client
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def creer_utilisateur_direct(
    db_session, *, role: RoleUtilisateur, login_id: str, nom: str = "Test", prenom: str = "Test"
) -> Utilisateur:
    """Insere un utilisateur directement en base, pour les roles sans auto-inscription
    (admin ministeriel, admin etablissement provisionne autrement que via le flux teste)."""
    utilisateur = Utilisateur(
        nom=nom,
        prenom=prenom,
        login_id=login_id,
        email=login_id,
        mot_de_passe_hash=hash_password("Password1"),
        role=role,
        email_verifie=True,
    )
    db_session.add(utilisateur)
    db_session.commit()
    db_session.refresh(utilisateur)
    return utilisateur


def token_pour(utilisateur: Utilisateur) -> str:
    return create_access_token(utilisateur.id, utilisateur.role.value)


@pytest.fixture()
def admin_ministeriel(db_session):
    return creer_utilisateur_direct(
        db_session, role=RoleUtilisateur.ADMIN_MINISTERIEL, login_id="ministere@example.com"
    )


@pytest.fixture()
def admin_ministeriel_headers(admin_ministeriel):
    return {"Authorization": f"Bearer {token_pour(admin_ministeriel)}"}


@pytest.fixture()
def etudiant_headers(client, fake_email_client, admin_ministeriel_headers):
    """UC-57/58 (lot admin etablissement, arbitrage utilisateur du 2026-09-26) : un
    ETUDIANT (eleve inscrit et valide dans un etablissement de type UP) - seul role
    autorise cote PRESTATAIRE des micro-jobs (micro_jobs/router.py::
    _exiger_prestataire_micro_job) et seul role autorise sur la marketplace
    (marketplace/router.py::_verifier_eleve_de_l_etablissement)."""
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Universite Test Fixture",
            "type": "UP",
            "statut": "public",
            "admin": {"nom": "Dossou", "prenom": "Universite", "email": "admin.universite.fixture@example.com"},
            "latitude": 6.4,
            "longitude": 2.4,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "admin.universite.fixture@example.com"
    )
    login_admin = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "admin.universite.fixture@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    admin_headers = {"Authorization": f"Bearer {login_admin['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=admin_headers,
    )

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "1ère année de Licence", "capacite": 3, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    tuteur_payload = {
        "nom": "Zannou", "prenom": "Parent", "email": "parent.etudiant.fixture@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": tuteur_payload["email"], "code": code})
    login_tuteur = client.post(
        "/api/v1/auth/login", json={"identifiant": tuteur_payload["email"], "mot_de_passe": tuteur_payload["mot_de_passe"]}
    ).json()
    tuteur_headers = {"Authorization": f"Bearer {login_tuteur['access_token']}"}

    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Etudiant", "prenom": "Test", "date_naissance": "2003-01-01", "classe_id": classe["id"],
            "consentement_parental_donne": True,
        },
        headers=tuteur_headers,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=admin_headers)
    identifiants = next(m for m in fake_email_client.sent if "login_id" in m and m["to_email"] == tuteur_payload["email"])
    login_etudiant = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]},
    ).json()
    headers = {"Authorization": f"Bearer {login_etudiant['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": identifiants["mot_de_passe"], "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=headers,
    )
    return headers


@pytest.fixture()
def classe_avec_tuteur_et_etudiant(client, fake_email_client, admin_ministeriel_headers):
    """Meme etablissement UP + etudiant que `etudiant_headers`, mais expose aussi les
    headers du tuteur (necessaire pour les tests coffre-fort : depuis l'arbitrage
    utilisateur du 2026-09-26, seul un ETUDIANT peut etre CLIENT d'un micro-job ou
    publier sur la marketplace - `classe_avec_enseignant_et_eleve`, dont l'eleve est
    EP/CE1, ne convient plus pour exercer ces deux modules de depense)."""
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Universite Test Coffre-Fort",
            "type": "UP",
            "statut": "public",
            "admin": {"nom": "Dossou", "prenom": "Universite", "email": "admin.universite.coffrefort@example.com"},
            "latitude": 6.4,
            "longitude": 2.4,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"] for m in fake_email_client.sent if m.get("to_email") == "admin.universite.coffrefort@example.com"
    )
    login_admin = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "admin.universite.coffrefort@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    admin_headers = {"Authorization": f"Bearer {login_admin['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=admin_headers,
    )

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "1ère année de Licence", "capacite": 3, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    tuteur_payload = {
        "nom": "Zannou", "prenom": "Parent", "email": "parent.coffrefort.fixture@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": tuteur_payload["email"], "code": code})
    login_tuteur = client.post(
        "/api/v1/auth/login", json={"identifiant": tuteur_payload["email"], "mot_de_passe": tuteur_payload["mot_de_passe"]}
    ).json()
    tuteur_headers = {"Authorization": f"Bearer {login_tuteur['access_token']}"}

    inscription = client.post(
        "/api/v1/inscriptions",
        json={
            "nom": "Etudiant", "prenom": "Test", "date_naissance": "2003-01-01", "classe_id": classe["id"],
            "consentement_parental_donne": True,
        },
        headers=tuteur_headers,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=admin_headers)
    identifiants = next(m for m in fake_email_client.sent if "login_id" in m and m["to_email"] == tuteur_payload["email"])
    login_eleve = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants["login_id"], "mot_de_passe": identifiants["mot_de_passe"]},
    ).json()
    eleve_headers = {"Authorization": f"Bearer {login_eleve['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": identifiants["mot_de_passe"], "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=eleve_headers,
    )
    return {"etablissement": etablissement, "classe": classe, "tuteur_headers": tuteur_headers, "eleve_headers": eleve_headers}


@pytest.fixture()
def tuteur_headers(client, fake_email_client):
    payload = {
        "nom": "Dossou",
        "prenom": "Awa",
        "email": "awa.tuteur.fixture@example.com",
        "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=payload)
    code = fake_email_client.sent[-1]["code"]
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


@pytest.fixture()
def enseignant_headers(client, fake_email_client):
    payload = {
        "nom": "Traore",
        "prenom": "Moussa",
        "email": "moussa.traore.fixture@example.com",
        "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/enseignants", json=payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == payload["email"])
    client.post("/api/v1/auth/enseignants/verify-otp", json={"email": payload["email"], "code": code})
    login = client.post(
        "/api/v1/auth/login", json={"identifiant": payload["email"], "mot_de_passe": payload["mot_de_passe"]}
    ).json()
    return {"Authorization": f"Bearer {login['access_token']}"}


@pytest.fixture()
def etablissement_avec_classe(client, fake_email_client, admin_ministeriel_headers):
    etablissement = client.post(
        "/api/v1/etablissements",
        json={
            "nom": "Ecole Primaire Test",
            "type": "EP",
            "statut": "public",
            "admin": {"nom": "Kone", "prenom": "Fatou", "email": "fatou.kone.fixture@example.com"},
            "latitude": 6.3703,
            "longitude": 2.3912,
        },
        headers=admin_ministeriel_headers,
    ).json()
    mot_de_passe_temp = next(
        m["mot_de_passe"]
        for m in fake_email_client.sent
        if m.get("to_email") == "fatou.kone.fixture@example.com"
    )
    login_admin = client.post(
        "/api/v1/auth/login",
        json={"identifiant": "fatou.kone.fixture@example.com", "mot_de_passe": mot_de_passe_temp},
    ).json()
    admin_headers = {"Authorization": f"Bearer {login_admin['access_token']}"}
    # Le mot de passe temporaire doit etre change avant toute action d'ecriture (deps.get_current_active_user).
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": mot_de_passe_temp, "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=admin_headers,
    )

    classe = client.post(
        f"/api/v1/etablissements/{etablissement['id']}/classes",
        json={"niveau": "CE1", "capacite": 1, "politique_depassement": "ordre_arrivee"},
        headers=admin_headers,
    ).json()

    return {"etablissement": etablissement, "classe": classe, "admin_headers": admin_headers}


@pytest.fixture()
def classe_avec_enseignant_et_eleve(client, fake_email_client, fake_llm_client, etablissement_avec_classe, enseignant_headers):
    """Etablissement + classe + un enseignant sous contrat signe dans cet etablissement +
    un eleve inscrit et valide dans cette classe. Sert de socle aux tests pedagogie/
    evaluations/actes, qui exigent tous un rattachement reel (pas juste un role)."""
    admin_headers = etablissement_avec_classe["admin_headers"]
    classe = etablissement_avec_classe["classe"]

    poste = client.post(
        f"/api/v1/etablissements/{etablissement_avec_classe['etablissement']['id']}/postes",
        json={"titre": "Professeur", "criteres": [{"type_document": "cv", "coefficient": 1, "seuil_minimal": 0}]},
        headers=admin_headers,
    ).json()
    fake_llm_client.score_par_defaut = 100.0
    candidature = client.post(
        f"/api/v1/postes/{poste['id']}/candidatures",
        data={"types": ["cv"]},
        files=[
            ("fichiers", ("cv.png", io.BytesIO(b"contenu"), "image/png")),
            ("casier_judiciaire", ("casier.pdf", io.BytesIO(b"casier"), "application/pdf")),
        ],
        headers=enseignant_headers,
    ).json()
    client.post(
        f"/api/v1/candidatures/{candidature['id']}/casier-judiciaire/verdict",
        json={"conforme": True},
        headers=admin_headers,
    )
    contrat = client.post(
        f"/api/v1/candidatures/{candidature['id']}/contrat",
        json={"syllabus": "Programme", "date_fin": "2027-06-30"},
        headers=admin_headers,
    ).json()
    client.post(
        f"/api/v1/contrats/{contrat['id']}/signer",
        files={"signature_image": ("signature.png", io.BytesIO(b"trace-du-canvas-en-png"), "image/png")},
        headers=enseignant_headers,
    )
    enseignant_utilisateur_id = decode_token(enseignant_headers["Authorization"].split(" ")[1])["sub"]
    client.post(
        f"/api/v1/classes/{classe['id']}/affectations",
        json={"enseignant_utilisateur_id": enseignant_utilisateur_id},
        headers=admin_headers,
    )

    tuteur_payload = {
        "nom": "Dossou", "prenom": "Awa", "email": "awa.tuteur.classe@example.com", "mot_de_passe": "Password1",
    }
    client.post("/api/v1/auth/tuteurs", json=tuteur_payload)
    code = next(m["code"] for m in reversed(fake_email_client.sent) if m.get("to_email") == tuteur_payload["email"])
    client.post("/api/v1/auth/tuteurs/verify-otp", json={"email": tuteur_payload["email"], "code": code})
    login_tuteur = client.post(
        "/api/v1/auth/login", json={"identifiant": tuteur_payload["email"], "mot_de_passe": tuteur_payload["mot_de_passe"]}
    ).json()
    tuteur_headers_local = {"Authorization": f"Bearer {login_tuteur['access_token']}"}

    inscription = client.post(
        "/api/v1/inscriptions",
        json={"nom": "Dossou", "prenom": "Aisha", "date_naissance": "2010-01-01", "classe_id": classe["id"]},
        headers=tuteur_headers_local,
    ).json()
    client.post(f"/api/v1/inscriptions/{inscription['id']}/valider", headers=admin_headers)
    identifiants_eleve = next(m for m in fake_email_client.sent if "login_id" in m and m["to_email"] == tuteur_payload["email"])
    login_eleve = client.post(
        "/api/v1/auth/login",
        json={"identifiant": identifiants_eleve["login_id"], "mot_de_passe": identifiants_eleve["mot_de_passe"]},
    ).json()
    eleve_headers = {"Authorization": f"Bearer {login_eleve['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": identifiants_eleve["mot_de_passe"], "nouveau_mot_de_passe": "NouveauMdp1"},
        headers=eleve_headers,
    )

    return {
        "etablissement": etablissement_avec_classe["etablissement"],
        "classe": classe,
        "admin_headers": admin_headers,
        "enseignant_headers": enseignant_headers,
        "eleve_headers": eleve_headers,
        "tuteur_headers": tuteur_headers_local,
    }
