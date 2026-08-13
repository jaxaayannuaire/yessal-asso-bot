import logging

from core.db import DatabaseManager

logger = logging.getLogger(__name__)

ROLE_SUPER_ADMIN = "super_admin"
ROLE_PRESIDENT = "president"
ROLE_TRESORIER = "tresorier"
ROLE_USER = "user"

BOARD_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_PRESIDENT, ROLE_TRESORIER})


class AuthManager:
    """Centralise les contrôles d'accès basés sur les utilisateurs Telegram."""

    def get_user(self, telegram_id):
        db = DatabaseManager()
        try:
            conn = db.connect()
            return conn.execute(
                """
                SELECT telegram_id, username, role, dolibarr_contact_id, is_active
                FROM bot_users
                WHERE telegram_id = ?
                """,
                [str(telegram_id)],
            ).fetchone()
        except Exception:
            logger.exception("Erreur lors de la récupération de l'utilisateur Telegram %s", telegram_id)
            return None
        finally:
            db.close()

    def has_role(self, telegram_id, allowed_roles):
        user = self.get_user(telegram_id)
        if not user or not user[4]:
            return False
        return user[2] in set(allowed_roles)

    def is_board_member(self, telegram_id):
        return self.has_role(telegram_id, BOARD_ROLES)
