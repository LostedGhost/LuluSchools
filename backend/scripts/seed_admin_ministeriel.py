"""Cree le tout premier compte administrateur ministeriel (A++).

Ce role n'a pas d'inscription via l'API (aucune route publique n'expose la
creation d'un compte A++, par choix de securite - voir docs/adr/). A executer
une seule fois au deploiement initial, directement sur le serveur avec acces
a la base de production.

Usage : python scripts/seed_admin_ministeriel.py "Nom" "Prenom" "email@exemple.bj"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.core.security import generate_temporary_password, hash_password
from app.modules.identite.models import RoleUtilisateur, Utilisateur


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)

    nom, prenom, email = sys.argv[1], sys.argv[2], sys.argv[3].lower()
    mot_de_passe = generate_temporary_password()

    db = SessionLocal()
    try:
        if db.query(Utilisateur).filter(Utilisateur.login_id == email).first() is not None:
            print(f"Un compte existe deja pour {email}.")
            raise SystemExit(1)

        utilisateur = Utilisateur(
            nom=nom,
            prenom=prenom,
            login_id=email,
            email=email,
            mot_de_passe_hash=hash_password(mot_de_passe),
            mot_de_passe_temporaire=True,
            role=RoleUtilisateur.ADMIN_MINISTERIEL,
            email_verifie=True,
        )
        db.add(utilisateur)
        db.commit()
    finally:
        db.close()

    print(f"Compte A++ cree pour {email}.")
    print(f"Mot de passe temporaire (a communiquer de maniere securisee) : {mot_de_passe}")
    print("Ce mot de passe devra etre change a la premiere connexion.")


if __name__ == "__main__":
    main()
