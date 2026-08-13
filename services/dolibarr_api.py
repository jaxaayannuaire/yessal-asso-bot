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
        self.headers = {
            'DOLAPIKEY': self.api_key,
            'Accept': 'application/json'
        }

    def ping(self):
        """Teste la connexion à l'API Dolibarr"""
        if not self.api_url or not self.api_key:
            return False, "❌ URL ou Clé API manquante."
        try:
            url = f"{self.api_url}/status"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                version = data.get('dolibarr_version', 'Inconnue')
                return True, f"✅ Connexion réussie ! (Version : {version})"
            else:
                return False, f"⚠️ Erreur ({response.status_code}) : {response.text}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau Dolibarr : {e}")
            return False, f"❌ Impossible de joindre le serveur : {e}"

    def get_contacts(self, limit=100):
        """Récupère les contacts récents depuis Dolibarr."""
        if not self.api_url or not self.api_key:
            return False, "Configuration API manquante."
        try:
            url = f"{self.api_url}/contacts?limit={limit}&sortfield=t.rowid&sortorder=DESC"
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                return True, []
            else:
                logger.error(f"Erreur API Contacts ({response.status_code}): {response.text}")
                return False, f"Erreur API: {response.status_code}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur requête get_contacts : {e}")
            return False, "Erreur de connexion au serveur."

    def get_members(self, limit=100):
        """Récupère la liste des adhérents (membres) depuis Dolibarr"""
        try:
            url = f"{self.api_url}/members?limit={limit}&sortfield=t.rowid&sortorder=DESC"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code in [404, 501]:
                url_alt = f"{self.api_url}/index.php/members?limit={limit}&sortfield=t.rowid&sortorder=DESC"
                response_alt = requests.get(url_alt, headers=self.headers, timeout=10)
                if response_alt.status_code == 200:
                    return True, response_alt.json()
                
            logger.error(f"Erreur API Dolibarr (members): {response.status_code} - {response.text}")
            return False, f"Erreur HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Exception lors de l'appel get_members : {e}")
            return False, str(e)

    def get_memberships(self, limit=100):
        """Récupère la liste des adhésions depuis Dolibarr"""
        try:
            url = f"{self.api_url}/index.php/subscriptions?limit={limit}&sortfield=t.rowid&sortorder=DESC"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code in [404, 501]:
                url_alt = f"{self.api_url}/index.php/members/subscriptions?limit={limit}"
                response_alt = requests.get(url_alt, headers=self.headers, timeout=10)
                if response_alt.status_code == 200:
                    return True, response_alt.json()
                    
            logger.error(f"Erreur API Dolibarr (subscriptions): {response.status_code} - {response.text}")
            return False, f"Erreur HTTP {response.status_code}"
        except Exception as e:
            logger.error(f"Exception lors de l'appel get_memberships : {e}")
            return False, str(e)
