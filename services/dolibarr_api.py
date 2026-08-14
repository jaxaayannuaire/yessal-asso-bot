import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DolibarrClient:
    """Client REST minimal et centralisé pour Dolibarr."""

    def __init__(self):
        self.api_url = (os.getenv("DOLIBARR_API_URL") or "").rstrip("/")
        self.api_key = os.getenv("DOLIBARR_API_KEY") or ""
        self.timeout = int(os.getenv("DOLIBARR_API_TIMEOUT", "15"))
        self.headers = {"DOLAPIKEY": self.api_key, "Accept": "application/json"}

    def _get(self, path, params=None, timeout=None):
        if not self.api_url or not self.api_key:
            return False, "❌ URL ou Clé API Dolibarr manquante."
        url = f"{self.api_url}/{path.lstrip('/')}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=timeout or self.timeout)
            if response.status_code == 200:
                return True, response.json()
            if response.status_code == 404:
                return True, []
            return False, f"Erreur HTTP {response.status_code}"
        except requests.RequestException as exc:
            logger.warning("Erreur réseau Dolibarr sur %s: %s", path, exc)
            return False, f"Erreur réseau : {exc}"
        except ValueError:
            logger.error("Réponse JSON invalide Dolibarr sur %s", path)
            return False, "Réponse JSON invalide de Dolibarr."

    def _post(self, path, payload, timeout=None):
        if not self.api_url or not self.api_key:
            return False, "❌ URL ou Clé API Dolibarr manquante."
        url = f"{self.api_url}/{path.lstrip('/')}"
        try:
            response = requests.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=timeout or self.timeout,
            )
            if response.status_code in (200, 201):
                try:
                    return True, response.json()
                except ValueError:
                    return True, response.text
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            logger.warning("Dolibarr POST %s -> HTTP %s: %s", path, response.status_code, detail)
            return False, f"Erreur HTTP {response.status_code}: {detail}"
        except requests.RequestException as exc:
            logger.warning("Erreur réseau Dolibarr POST %s: %s", path, exc)
            return False, f"Erreur réseau : {exc}"

    def ping(self):
        success, data = self._get("status", timeout=10)
        if not success:
            return False, data
        version = data.get("dolibarr_version", "Inconnue") if isinstance(data, dict) else "Inconnue"
        return True, f"✅ Connexion réussie ! (Version : {version})"

    def get_contacts(self, limit=100):
        return self._get("contacts", {"limit": limit})

    def get_members(self, limit=100):
        success, data = self._get("members", {"limit": limit})
        if success and data != []:
            return success, data
        return self._get("index.php/members", {"limit": limit})

    def get_memberships(self, limit=100):
        params = {"limit": limit, "sortfield": "t.rowid", "sortorder": "DESC"}
        success, data = self._get("subscriptions", params)
        if success and data != []:
            return success, data
        return self._get("index.php/subscriptions", params)

    def get_contributions(self, limit=100):
        params = {"limit": limit}
        for endpoint in ("subscriptions", "index.php/subscriptions", "donations"):
            success, data = self._get(endpoint, params)
            if success and data:
                return True, data
            if not success and endpoint == "donations":
                return False, data
        return True, []

    def get_bank_accounts(self, limit=100):
        return self._get("bankaccounts", {"limit": limit, "sortfield": "t.rowid", "sortorder": "ASC"})

    def get_bank_account(self, account_id):
        success, data = self._get(f"bankaccounts/{int(account_id)}")
        if success and isinstance(data, dict):
            return True, data
        if success and data == []:
            return False, "Compte bancaire/caisse introuvable."
        return success, data

    def get_bank_balance(self, account_id):
        return self._get(f"bankaccounts/{int(account_id)}/balance")

    def get_bank_lines(self, account_id, sqlfilters=None):
        params = {}
        if sqlfilters:
            params["sqlfilters"] = sqlfilters
        return self._get(f"bankaccounts/{int(account_id)}/lines", params)

    def add_bank_line(self, account_id, transaction_date, payment_type, label, amount):
        try:
            date_value = int(datetime.fromisoformat(str(transaction_date)).timestamp())
        except (TypeError, ValueError, OverflowError):
            return False, "Date de transaction invalide."
        return self._post(
            f"bankaccounts/{int(account_id)}/lines",
            {"date": date_value, "type": payment_type, "label": label, "amount": float(amount)},
        )

    def get_dolibarr_users(self, limit=500):
        """Liste les utilisateurs Dolibarr accessibles par la clé API."""
        return self._get("users", {"limit": limit, "sortfield": "t.rowid", "sortorder": "ASC"})

    def get_dolibarr_user(self, user_id):
        return self._get(f"users/{int(user_id)}")

    def get_dolibarr_user_groups(self, user_id):
        """Liste les groupes d'un utilisateur Dolibarr."""
        return self._get(f"users/{int(user_id)}/groups")

    def get_dolibarr_groups(self, limit=500):
        """Liste les groupes d'utilisateurs Dolibarr."""
        return self._get("users/groups", {"limit": limit, "sortfield": "t.rowid", "sortorder": "ASC"})

    def create_dolibarr_group(self, name):
        """Crée un groupe Dolibarr si la clé API dispose des droits requis."""
        return self._post("users/groups", {"name": name})

    def add_user_to_group(self, user_id, group_id):
        """Ajoute un utilisateur à un groupe.

        Dolibarr expose cette opération en GET /users/{id}/setGroup/{group}
        dans les versions historiques de l'API Users.
        """
        return self._get(f"users/{int(user_id)}/setGroup/{int(group_id)}")

    def remove_user_from_group(self, user_id, group_id):
        """Retire un utilisateur d'un groupe sur les versions qui exposent
        POST /users/{id}/remove-group/{group}."""
        return self._post(f"users/{int(user_id)}/remove-group/{int(group_id)}", {})
