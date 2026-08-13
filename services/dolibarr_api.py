import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class DolibarrClient:
    def __init__(self):
        self.api_url = os.getenv('DOLIBARR_API_URL')
        self.api_key = os.getenv('DOLIBARR_API_KEY')
        self.headers = {'DOLAPIKEY': self.api_key, 'Accept': 'application/json'}

    def ping(self):
        if not self.api_url or not self.api_key:
            return False, "❌ URL ou Clé API manquante."
        try:
            response = requests.get(f"{self.api_url}/status", headers=self.headers, timeout=10)
            if response.status_code == 200:
                return True, f"✅ Connexion réussie ! (Version : {response.json().get('dolibarr_version', 'Inconnue')})"
            return False, f"⚠️ Erreur ({response.status_code})"
        except Exception as e:
            return False, f"❌ Erreur réseau : {e}"

    def get_contacts(self, limit=100):
        try:
            response = requests.get(f"{self.api_url}/contacts?limit={limit}", headers=self.headers, timeout=15)
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                return True, []
            return False, f"Erreur API: {response.status_code}"
        except Exception as e:
            return False, str(e)

    def get_members(self, limit=100):
        try:
            response = requests.get(f"{self.api_url}/members?limit={limit}", headers=self.headers, timeout=10)
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code in [404, 501]:
                res_alt = requests.get(f"{self.api_url}/index.php/members?limit={limit}", headers=self.headers, timeout=10)
                if res_alt.status_code == 200:
                    return True, res_alt.json()
            return False, f"Erreur HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def get_memberships(self, limit=100):
        endpoints = [
            f"{self.api_url}/subscriptions?limit={limit}",
            f"{self.api_url}/index.php/subscriptions?limit={limit}",
            f"{self.api_url}/members/subscriptions?limit={limit}"
        ]
        for url in endpoints:
            try:
                res = requests.get(url, headers=self.headers, timeout=10)
                if res.status_code == 200:
                    return True, res.json()
                elif res.status_code == 404:
                    return True, []
            except Exception:
                continue
        return False, "Erreur HTTP 501 (Module subscriptions non disponible)"

    def get_contributions(self, limit=100):
        endpoints = [
            f"{self.api_url}/subscriptions?limit={limit}",
            f"{self.api_url}/index.php/subscriptions?limit={limit}",
            f"{self.api_url}/donations?limit={limit}"
        ]
        all_data = []
        for url in endpoints:
            try:
                res = requests.get(url, headers=self.headers, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        all_data.extend(data)
                        break
            except Exception:
                continue
        return True, all_data

    def get_memberships(self, limit=100):
        """Récupère la liste des adhésions depuis Dolibarr"""
        try:
            url = f"{self.api_url}/subscriptions?limit={limit}&sortfield=t.rowid&sortorder=DESC"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code in [404, 501]:
                url_alt = f"{self.api_url}/index.php/subscriptions?limit={limit}&sortfield=t.rowid&sortorder=DESC"
                response_alt = requests.get(url_alt, headers=self.headers, timeout=10)
                if response_alt.status_code == 200:
                    return True, response_alt.json()
            return False, f"Erreur HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Erreur get_memberships : {e}")
            return False, str(e)

    def get_contributions(self, limit=100):
        """Récupère la liste des cotisations (paiements membres) depuis Dolibarr"""
        try:
            # Note: selon la version de Dolibarr, l'endpoint des cotisations de membres est souvent /stages ou /subscriptions/payments ou géré via les paiements factures.
            # On utilise ici l'endpoint standard des cotisations d'adhérents s'il existe, ou des paiements.
            url = f"{self.api_url}/subscriptions?limit={limit}" # (Adaptable selon les modules actifs)
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return True, response.json()
            return False, f"Erreur HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Erreur get_contributions : {e}")
            return False, str(e)