import duckdb
import os
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = os.getenv('DUCKDB_PATH', './data/yessal_asso.duckdb')
        self.conn = None

    def connect(self):
        """Établit la connexion à DuckDB"""
        if not self.conn:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = duckdb.connect(self.db_path)
        return self.conn

    def init_db(self):
        """Initialise les tables de base pour le MVP"""
        conn = self.connect()
        try:
            # 1. Table pour l'authentification et les rôles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_users (
                    telegram_id VARCHAR PRIMARY KEY,
                    username VARCHAR,
                    role VARCHAR DEFAULT 'user',
                    dolibarr_contact_id VARCHAR,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 2. Table de cache pour les contacts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_contacts (
                    id VARCHAR PRIMARY KEY,
                    firstname VARCHAR,
                    lastname VARCHAR,
                    phone VARCHAR,
                    email VARCHAR,
                    status VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Table de cache pour les adhérents (membres)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_members (
                    id VARCHAR PRIMARY KEY,
                    morphy VARCHAR,
                    lastname VARCHAR,
                    firstname VARCHAR,
                    email VARCHAR,
                    phone VARCHAR,
                    status VARCHAR,
                    date_fin VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Table de cache pour les adhésions (memberships)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_memberships (
                    id VARCHAR PRIMARY KEY,
                    member_id VARCHAR,
                    date_subscription VARCHAR,
                    date_start VARCHAR,
                    date_end VARCHAR,
                    amount DECIMAL,
                    status VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Table de cache pour les cotisations (contributions)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_contributions (
                    id VARCHAR PRIMARY KEY,
                    ref VARCHAR,
                    member_id VARCHAR,
                    amount DECIMAL,
                    date_payment VARCHAR,
                    type VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            return True, "✅ Base de données DuckDB initialisée avec succès (incluant les cotisations)."
        except Exception as e:
            logger.error(f"Erreur d'initialisation DuckDB : {e}")
            return False, f"❌ Erreur DuckDB : {e}"
            
    def sync_contacts(self, contacts_data):
        conn = self.connect()
        try:
            conn.execute("DELETE FROM cache_contacts")
            for c in contacts_data:
                c_id = str(c.get('id', ''))
                firstname = c.get('firstname', '') or ''
                lastname = c.get('lastname', '') or ''
                phone = c.get('phone_mobile', '') or c.get('phone_pro', '') or ''
                email = c.get('email', '') or ''
                status = str(c.get('statut', '1'))

                conn.execute("""
                    INSERT INTO cache_contacts (id, firstname, lastname, phone, email, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [c_id, firstname, lastname, phone, email, status])
            return True, f"✅ {len(contacts_data)} contacts synchronisés en local."
        except Exception as e:
            logger.error(f"Erreur sync_contacts : {e}")
            return False, f"❌ Erreur de synchronisation locale : {e}"

    def search_contacts(self, query):
        conn = self.connect()
        try:
            search_term = f"%{query.lower()}%"
            result = conn.execute("""
                SELECT id, firstname, lastname, phone
                FROM cache_contacts
                WHERE LOWER(firstname) LIKE ? OR LOWER(lastname) LIKE ? OR phone LIKE ?
                LIMIT 10
            """, [search_term, search_term, search_term]).fetchall()
            return result
        except Exception as e:
            logger.error(f"Erreur search_contacts : {e}")
            return []

    def sync_members(self, members_data):
        conn = self.connect()
        try:
            conn.execute("DELETE FROM cache_members")
            for m in members_data:
                m_id = str(m.get('id', ''))
                morphy = m.get('morphy', 'mor') or 'mor'
                lastname = m.get('lastname', '') or m.get('societe', '') or ''
                firstname = m.get('firstname', '') or ''
                email = m.get('email', '') or ''
                phone = m.get('phone', '') or m.get('phone_mobile', '') or ''
                status = str(m.get('statut', ''))
                date_fin = str(m.get('date_fin', ''))

                conn.execute("""
                    INSERT INTO cache_members (id, morphy, lastname, firstname, email, phone, status, date_fin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [m_id, morphy, lastname, firstname, email, phone, status, date_fin])
            return True, f"✅ {len(members_data)} adhérents synchronisés en local."
        except Exception as e:
            logger.error(f"Erreur sync_members : {e}")
            return False, f"❌ Erreur de synchronisation locale des adhérents : {e}"

    def search_members(self, query):
        conn = self.connect()
        try:
            search_term = f"%{query.lower()}%"
            result = conn.execute("""
                SELECT id, firstname, lastname, phone, status, date_fin
                FROM cache_members
                WHERE LOWER(firstname) LIKE ? OR LOWER(lastname) LIKE ? OR phone LIKE ?
                LIMIT 10
            """, [search_term, search_term, search_term]).fetchall()
            return result
        except Exception as e:
            logger.error(f"Erreur search_members : {e}")
            return []

    def sync_memberships(self, memberships_data):
        conn = self.connect()
        try:
            conn.execute("DELETE FROM cache_memberships")
            for sub in memberships_data:
                sub_id = str(sub.get('id', ''))
                member_id = str(sub.get('fk_member', ''))
                date_sub = str(sub.get('dateh', ''))
                date_start = str(sub.get('date_start', ''))
                date_end = str(sub.get('date_end', ''))
                amount = float(sub.get('amount', 0.0) or 0.0)
                status = str(sub.get('statut', ''))

                conn.execute("""
                    INSERT INTO cache_memberships (id, member_id, date_subscription, date_start, date_end, amount, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [sub_id, member_id, date_sub, date_start, date_end, amount, status])
            return True, f"✅ {len(memberships_data)} adhésions synchronisées en local."
        except Exception as e:
            logger.error(f"Erreur sync_memberships : {e}")
            return False, f"❌ Erreur de synchronisation locale des adhésions : {e}"

    def sync_contributions(self, contributions_data):
        """Met à jour le cache local des cotisations depuis Dolibarr"""
        conn = self.connect()
        try:
            conn.execute("DELETE FROM cache_contributions")
            for contrib in contributions_data:
                c_id = str(contrib.get('id', ''))
                ref = str(contrib.get('ref', '')) or str(contrib.get('rowid', ''))
                member_id = str(contrib.get('fk_member', '')) or str(contrib.get('fk_soc', ''))
                amount = float(contrib.get('amount', 0.0) or contrib.get('total_ttc', 0.0) or 0.0)
                date_payment = str(contrib.get('datec', '')) or str(contrib.get('datep', ''))
                c_type = str(contrib.get('type', 'cotisation'))

                conn.execute("""
                    INSERT INTO cache_contributions (id, ref, member_id, amount, date_payment, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [c_id, ref, member_id, amount, date_payment, c_type])
                
            return True, f"✅ {len(contributions_data)} cotisations synchronisées en local."
        except Exception as e:
            logger.error(f"Erreur sync_contributions : {e}")
            return False, f"❌ Erreur de synchronisation locale des cotisations : {e}"

    def get_dashboard_stats(self):
        """Récupère les statistiques globales pour le dashboard"""
        conn = self.connect()
        try:
            stats = {}
            res = conn.execute("SELECT COUNT(*) FROM cache_contacts").fetchone()
            stats['total_contacts'] = res[0] if res else 0
            
            res = conn.execute("SELECT COUNT(*), SUM(CASE WHEN status='1' THEN 1 ELSE 0 END) FROM cache_members").fetchone()
            stats['total_members'] = res[0] if res else 0
            stats['active_members'] = int(res[1]) if res and res[1] else 0
            
            res = conn.execute("SELECT SUM(amount) FROM cache_contributions").fetchone()
            stats['total_contributions'] = float(res[0]) if res and res[0] else 0.0
            
            return True, stats
        except Exception as e:
            logger.error(f"Erreur get_dashboard_stats : {e}")
            return False, {}
    
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
