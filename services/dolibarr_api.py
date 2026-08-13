import logging
import os

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
        self.headers = {
            "DOLAPIKEY": self.api_key,
            "Accept": "application/json",
        }

    def _get(self, path, params=None, timeout=None):
        if not self.api_url or not self.api_key:
            return False, "❌ URL ou Clé API Dolibarr manquante."
        url = f"{self.api_url}/{path.lstrip('/')}"
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=timeout or self.timeout,
            )
            if response.status_code == 200:
                return True, response.json()
            if response.status_code == 404:
                return True, []
            return False, f"Erreur HTTP {response.status_code}"
        except requests.RequestException as exc:
            logger.warning("Erreur réseau Dolibarr sur %s: %s", path, exc)
            return False, f"Erreur réseau : {exc}"
        except ValueError as exc:
            logger.error("Réponse JSON invalide Dolibarr sur %s: %s", path, exc)
            return False, "Réponse JSON invalide de Dolibarr."

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
        """Récupère les cotisations selon les endpoints disponibles.

        La correspondance exacte avec les paiements Dolibarr sera consolidée
        avant la Phase 17/18. Cette méthode reste compatible avec le MVP.
        """
        params = {"limit": limit}
        for endpoint in ("subscriptions", "index.php/subscriptions", "donations"):
            success, data = self._get(endpoint, params)
            if success and data:
                return True, data
            if not success and endpoint == "donations":
                return False, data
        return True, []
