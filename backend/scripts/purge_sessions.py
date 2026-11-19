"""Purge des sessions visiteurs et des messages expirés.

Usage (depuis backend/) :  python -m scripts.purge_sessions
À planifier régulièrement (ex. toutes les heures) avec le planificateur de tâches.
"""

from app.db.session import SessionLocal
from app.services.session_purge_service import purger_sessions_expirees


def main() -> None:
    with SessionLocal() as db:
        resultat = purger_sessions_expirees(db)
    print(
        f"Messages expirés supprimés : {resultat['messages_supprimes']} | "
        f"sessions marquées expirées : {resultat['marquees_expirees']} | "
        f"sessions supprimées : {resultat['supprimees']}"
    )


if __name__ == "__main__":
    main()