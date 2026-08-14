import logging
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class DolibarrClient:
    """Client REST centralisé pour Dolibarr."""

    def __init__(self):
        self.api_url = (os.getenv("DOLIBARR_API_URL") or "").rstrip("/")
        self.api_key = os.getenv("DOLIBARR_API_KEY") or ""
        self.timeout = int(os.getenv("DOLIBARR_API_TIMEOUT", "15"))
        self.headers = {"DOLAPIKEY": self.api_key, "Accept": "application/json"}
        self.version = None

    def _request(self, method, path, payload=None, params=None, timeout=None):
        if not self.api_url or not self.api_key:
            return False, "❌ URL ou Clé API Dolibarr manquante."
        url = f"{self.api_url}/{path.lstrip('/')}"
        headers = {**self.headers}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = requests.request(
                method, url, headers=headers, params=params,
                json=payload if payload is not None else None,
                timeout=timeout or self.timeout,
            )
            if 200 <= response.status_code < 300:
                if not response.content:
                    return True, None
                try:
                    return True, response.json()
                except ValueError:
                    return True, response.text
            if response.status_code == 404 and method == "GET":
                return True, []
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            logger.warning(
                "Dolibarr %s %s -> HTTP %s: %s",
                method, path, response.status_code, detail,
            )
            return False, f"Erreur HTTP {response.status_code}: {detail}"
        except requests.RequestException as exc:
            logger.warning("Erreur réseau Dolibarr %s %s: %s", method, path, exc)
            return False, f"Erreur réseau : {exc}"

    def _get(self, path, params=None, timeout=None):
        return self._request("GET", path, params=params, timeout=timeout)

    def _post(self, path, payload, timeout=None):
        return self._request("POST", path, payload=payload, timeout=timeout)

    def _put(self, path, payload, timeout=None):
        return self._request("PUT", path, payload=payload, timeout=timeout)

    def _delete(self, path, timeout=None):
        return self._request("DELETE", path, timeout=timeout)

    def get_version(self, refresh=False):
        if self.version and not refresh:
            return True, self.version
        success, data = self._get("status", timeout=10)
        if not success:
            return False, data
        version = None
        if isinstance(data, dict):
            nested = data.get("success")
            if isinstance(nested, dict):
                version = nested.get("dolibarr_version")
            version = version or data.get("dolibarr_version")
        self.version = str(version or "unknown")
        return True, self.version

    def get_api_capabilities(self):
        success, version = self.get_version()
        if not success:
            return False, version
        capabilities = {
            "groups.list": True,
            "groups.read": True,
            "groups.create": False,
            "groups.update": False,
            "groups.delete": False,
            "user_groups.add": True,
            "user_groups.remove": False,
        }
        try:
            major = int(str(version).split(".", 1)[0])
        except (TypeError, ValueError):
            major = 0
        if major >= 23:
            capabilities.update({
                "groups.create": True,
                "groups.update": True,
                "groups.delete": True,
                "user_groups.remove": True,
            })
        return True, capabilities

    def ping(self):
        success, version = self.get_version(refresh=True)
        if not success:
            return False, version
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
        return self._get("users", {"limit": limit, "sortfield": "t.rowid", "sortorder": "ASC"})

    def get_dolibarr_user(self, user_id):
        return self._get(f"users/{int(user_id)}")

    def get_dolibarr_user_groups(self, user_id):
        return self._get(f"users/{int(user_id)}/groups")

    def get_dolibarr_groups(self, limit=500):
        return self._get("users/groups", {"limit": limit, "sortfield": "t.rowid", "sortorder": "ASC"})

    def create_dolibarr_group(self, name):
        return self._post("users/groups", {"name": name})

    def update_dolibarr_group(self, group_id, payload):
        return self._put(f"users/groups/{int(group_id)}", payload)

    def delete_dolibarr_group(self, group_id):
        return self._delete(f"users/groups/{int(group_id)}")

    def add_user_to_group(self, user_id, group_id):
        return self._get(f"users/{int(user_id)}/setGroup/{int(group_id)}")

    def remove_user_from_group(self, user_id, group_id):
        return self._post(f"users/{int(user_id)}/remove-group/{int(group_id)}", {})
