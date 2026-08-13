import logging
from core.db import DatabaseManager

logger = logging.getLogger(__name__)

class AuthManager:
    def get_user(self, telegram_id):
        db = DatabaseManager()
        conn = db.connect()
        try:
            res = conn.execute("SELECT telegram_id, username, role, dolibarr_contact_id, is_active FROM bot_users WHERE telegram_id = ?", [str(telegram_id)]).fetchone()
            return res
        except Exception as e:
            return None
        finally:
            db.close()
