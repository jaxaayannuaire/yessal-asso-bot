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
            return False, f"❌ Impossible de joindre le serveur : {e}"

    def get_contacts(self, limit=100):
        try:
            url = f"{self.api_url}/contacts?limit={limit}&sortfield=t.rowid&sortorder=DESC"
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 404:
                return True, []
            return False, f"Erreur API: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, "Erreur de connexion au serveur."

    def get_members(self, limit=100):
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
            return False, f"Erreur HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)

    def get_memberships(self, limit=100):
        endpoints = [
            f"{self.api_url}/subscriptions?limit={limit}&sortfield=t.rowid&sortorder=DESC",
            f"{self.api_url}/index.php/subscriptions?limit={limit}&sortfield=t.rowid&sortorder=DESC",
            f"{self.api_url}/members/subscriptions?limit={limit}",
            f"{self.api_url}/index.php/members/subscriptions?limit={limit}",
            f"{self.api_url}/adherent/subscriptions?limit={limit}"
        ]
        for url in endpoints:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    return True, response.json()
                elif response.status_code == 404:
                    return True, []
            except Exception as e:
                continue
        return False, "Erreur HTTP 501 (Module subscriptions non disponible sur l'API REST Dolibarr)"

    def get_contributions(self, limit=100):
        """
        Dans Dolibarr, les 'cotisations' associatives sont souvent soit :
        1. Les paiements d'adhésions (/subscriptions)
        2. Les dons (/donations)
        3. Des factures spécifiques avec un tag (/invoices)
        On va tenter de récupérer les paiements d'adhésions en priorité car c'est le standard Dolibarr.
        """
        endpoints = [
            # Priorité 1 : Les adhésions validées (qui incluent souvent le montant payé)
            f"{self.api_url}/subscriptions?limit={limit}&sortfield=t.rowid&sortorder=DESC",
            f"{self.api_url}/index.php/subscriptions?limit={limit}",
            f"{self.api_url}/members/subscriptions?limit={limit}",
            # Priorité 2 : Les dons si c'est géré comme ça
            f"{self.api_url}/donations?limit={limit}&sortfield=t.rowid&sortorder=DESC"
        ]
        
        all_contributions = []
        
        for url in endpoints:
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        all_contributions.extend(data)
                        break # On a trouvé des données, on s'arrête là
            except Exception as e:
                logger.debug(f"Tentative endpoint cotisations {url} échouée: {e}")
                continue
                
        # Retourner la liste même si elle est vide, cela signifie que la requête a marché mais pas de data
        return True, all_contributions
