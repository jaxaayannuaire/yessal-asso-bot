import logging

from core.permissions import (
    ROLE_ADMIN,
    ROLE_BUREAU,
    ROLE_MEMBRE,
    ROLE_PRESIDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TRESORIER,
    ROLE_USER,
    ensure_schema,
    get_effective_role,
    get_roles_for_dolibarr_user,
    has_permission,
)

logger = logging.getLogger(__name__)

BOARD_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_PRESIDENT, ROLE_BUREAU, ROLE_TRESORIER, ROLE_ADMIN})


class AuthManager:
    """Contrôle d'accès basé sur le lien Telegram ↔ utilisateur Dolibarr.

    Les groupes/roles sont synchronisés depuis Dolibarr. La colonne role de
    bot_users reste une compatibilité de migration et un mécanisme bootstrap.
    """

    def _get_user_row(self, telegram_id):
        from core.db import DatabaseManager
        db = DatabaseManager()
        try:
            ensure_schema(db)
            return db.connect().execute(
                """
                SELECT telegram_id, username, role, dolibarr_contact_id,
                       is_active, dolibarr_user_id
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

    def get_user(self, telegram_id):
        row = self._get_user_row(telegram_id)
        if not row:
            return None
        telegram, username, legacy_role, contact_id, active, dolibarr_user_id = row
        if not active:
            return (telegram, username, ROLE_USER, contact_id, active, dolibarr_user_id)

        role = ROLE_USER
        if legacy_role == ROLE_SUPER_ADMIN:
            # Bootstrap de sécurité : le Super Admin historique reste utilisable
            # pour effectuer le premier lien Telegram ↔ Dolibarr.
            role = ROLE_SUPER_ADMIN

        if dolibarr_user_id:
            from core.db import DatabaseManager
            db = DatabaseManager()
            try:
                ensure_schema(db)
                roles = get_roles_for_dolibarr_user(db, dolibarr_user_id)
                if roles:
                    role = get_effective_role(roles)
            finally:
                db.close()
        return (telegram, username, role, contact_id, active, dolibarr_user_id)

    def get_roles(self, telegram_id) -> set[str]:
        row = self._get_user_row(telegram_id)
        if not row or not row[4]:
            return set()

        legacy_role = row[2] or ROLE_USER
        # Un utilisateur Telegram non lié à un utilisateur Dolibarr ne peut
        # pas hériter des rôles métier historiques. Seul le Super Admin
        # bootstrap est conservé pour permettre le premier appairage.
        roles = {ROLE_SUPER_ADMIN} if legacy_role == ROLE_SUPER_ADMIN else {ROLE_USER}

        if row[5]:
            from core.db import DatabaseManager
            db = DatabaseManager()
            try:
                ensure_schema(db)
                synced_roles = get_roles_for_dolibarr_user(db, row[5])
                roles = synced_roles or {ROLE_USER}
            finally:
                db.close()
        return roles

    def has_role(self, telegram_id, allowed_roles):
        roles = self.get_roles(telegram_id)
        return bool(roles.intersection(set(allowed_roles)))

    def has_permission(self, telegram_id, permission):
        return has_permission(self.get_roles(telegram_id), permission)

    def is_board_member(self, telegram_id):
        return bool(self.get_roles(telegram_id).intersection(BOARD_ROLES))

    def is_super_admin(self, telegram_id):
        return self.has_role(telegram_id, {ROLE_SUPER_ADMIN})

    def effective_role(self, telegram_id):
        return get_effective_role(self.get_roles(telegram_id))
