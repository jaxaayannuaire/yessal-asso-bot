import logging
import os
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Accès local DuckDB.

    DuckDB reste un miroir/cache technique : les données métier de référence
    sont celles de Dolibarr.
    """

    def __init__(self):
        self.db_path = os.getenv("DUCKDB_PATH", "./data/yessal_asso.duckdb")
        self.conn = None

    def connect(self):
        if self.conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = duckdb.connect(self.db_path)
        return self.conn

    def init_db(self):
        conn = self.connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_users (
                    telegram_id VARCHAR PRIMARY KEY,
                    username VARCHAR,
                    role VARCHAR DEFAULT 'user',
                    dolibarr_contact_id VARCHAR,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_contacts (
                    id VARCHAR PRIMARY KEY,
                    firstname VARCHAR,
                    lastname VARCHAR,
                    phone VARCHAR,
                    email VARCHAR,
                    status VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
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
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_memberships (
                    id VARCHAR PRIMARY KEY,
                    member_id VARCHAR,
                    date_subscription VARCHAR,
                    date_start VARCHAR,
                    date_end VARCHAR,
                    amount DECIMAL(18, 2),
                    status VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_contributions (
                    id VARCHAR PRIMARY KEY,
                    ref VARCHAR,
                    member_id VARCHAR,
                    amount DECIMAL(18, 2),
                    date_payment VARCHAR,
                    type VARCHAR,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Migration additive : les anciennes installations peuvent avoir
            # les colonnes date_c/note ou manquer les nouvelles colonnes.
            self._ensure_columns(
                "cache_memberships",
                {
                    "member_id": "VARCHAR",
                    "date_subscription": "VARCHAR",
                    "date_start": "VARCHAR",
                    "date_end": "VARCHAR",
                    "amount": "DECIMAL(18, 2)",
                    "status": "VARCHAR",
                    "last_sync": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            )
            self._ensure_columns(
                "cache_contributions",
                {
                    "ref": "VARCHAR",
                    "member_id": "VARCHAR",
                    "amount": "DECIMAL(18, 2)",
                    "date_payment": "VARCHAR",
                    "type": "VARCHAR",
                    "last_sync": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            )
            logger.info("Base DuckDB initialisée : %s", self.db_path)
            return True, "✅ Base de données initialisée."
        except Exception as exc:
            logger.exception("Erreur DuckDB lors de l'initialisation")
            return False, f"❌ Erreur DuckDB : {exc}"

    def _ensure_columns(self, table, columns):
        existing = {
            row[0].lower()
            for row in self.connect().execute(f"DESCRIBE {table}").fetchall()
        }
        for name, definition in columns.items():
            if name.lower() not in existing:
                self.connect().execute(
                    f"ALTER TABLE {table} ADD COLUMN {name} {definition}"
                )
                logger.info("Colonne ajoutée à %s : %s", table, name)

    def sync_contacts(self, contacts_data):
        return self._replace_rows(
            "cache_contacts",
            contacts_data,
            "contacts",
            lambda c: (
                str(c.get("id", "")),
                c.get("firstname", "") or "",
                c.get("lastname", "") or "",
                c.get("phone_mobile", "") or c.get("phone_pro", "") or "",
                c.get("email", "") or "",
                str(c.get("statut", "1")),
            ),
            "INSERT INTO cache_contacts (id, firstname, lastname, phone, email, status) VALUES (?, ?, ?, ?, ?, ?)",
        )

    def search_contacts(self, query):
        term = f"%{str(query).lower()}%"
        return self.connect().execute(
            """
            SELECT id, firstname, lastname, phone
            FROM cache_contacts
            WHERE LOWER(firstname) LIKE ?
               OR LOWER(lastname) LIKE ?
               OR phone LIKE ?
            LIMIT 10
            """,
            [term, term, term],
        ).fetchall()

    def sync_members(self, members_data):
        return self._replace_rows(
            "cache_members",
            members_data,
            "adhérents",
            lambda m: (
                str(m.get("id", "")),
                m.get("morphy", "mor") or "mor",
                m.get("lastname", "") or m.get("societe", "") or "",
                m.get("firstname", "") or "",
                m.get("email", "") or "",
                m.get("phone", "") or m.get("phone_mobile", "") or "",
                str(m.get("statut", "")),
                str(m.get("date_fin", "")),
            ),
            "INSERT INTO cache_members (id, morphy, lastname, firstname, email, phone, status, date_fin) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        )

    def search_members(self, query):
        term = f"%{str(query).lower()}%"
        return self.connect().execute(
            """
            SELECT id, firstname, lastname, phone, status, date_fin
            FROM cache_members
            WHERE LOWER(firstname) LIKE ?
               OR LOWER(lastname) LIKE ?
               OR phone LIKE ?
            LIMIT 10
            """,
            [term, term, term],
        ).fetchall()

    def sync_memberships(self, memberships_data):
        rows = []
        for item in memberships_data:
            rows.append(
                (
                    str(item.get("id", "")),
                    str(item.get("fk_member", "")),
                    str(item.get("dateh", "") or item.get("date_creation", "")),
                    str(item.get("date_start", "")),
                    str(item.get("date_end", "")),
                    float(item.get("amount", 0.0) or 0.0),
                    str(item.get("statut", "")),
                )
            )
        return self._replace_prepared(
            "cache_memberships",
            rows,
            "adhésions",
            "INSERT INTO cache_memberships (id, member_id, date_subscription, date_start, date_end, amount, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        )

    def sync_contributions(self, contributions_data):
        rows = []
        for item in contributions_data:
            contribution_id = str(item.get("id", ""))
            ref = str(item.get("ref", "") or item.get("rowid", ""))
            member_id = str(item.get("fk_member", "") or item.get("fk_soc", ""))
            amount = float(item.get("amount", 0.0) or item.get("total_ttc", 0.0) or 0.0)
            date_payment = str(item.get("datec", "") or item.get("datep", ""))
            contribution_type = str(item.get("type", "cotisation"))
            rows.append((contribution_id, ref, member_id, amount, date_payment, contribution_type))
        return self._replace_prepared(
            "cache_contributions",
            rows,
            "cotisations",
            "INSERT INTO cache_contributions (id, ref, member_id, amount, date_payment, type) VALUES (?, ?, ?, ?, ?, ?)",
        )

    def get_dashboard_stats(self):
        try:
            conn = self.connect()
            contacts = conn.execute("SELECT COUNT(*) FROM cache_contacts").fetchone()[0]
            members, active = conn.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status='1' THEN 1 ELSE 0 END) FROM cache_members"
            ).fetchone()
            total = conn.execute("SELECT SUM(amount) FROM cache_contributions").fetchone()[0]
            return True, {
                "total_contacts": contacts,
                "total_members": members or 0,
                "active_members": int(active or 0),
                "total_contributions": float(total or 0.0),
            }
        except Exception:
            logger.exception("Erreur get_dashboard_stats")
            return False, {}

    def get_weekly_report_data(self):
        try:
            conn = self.connect()
            count, amount = conn.execute(
                "SELECT COUNT(*), SUM(amount) FROM cache_contributions"
            ).fetchone()
            members, active = conn.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status='1' THEN 1 ELSE 0 END) FROM cache_members"
            ).fetchone()
            return True, {
                "total_cotisations_count": count or 0,
                "total_cotisations_amount": float(amount or 0.0),
                "total_members": members or 0,
                "active_members": int(active or 0),
            }
        except Exception:
            logger.exception("Erreur get_weekly_report_data")
            return False, {}

    def _replace_rows(self, table, data, label, mapper, sql):
        try:
            rows = [mapper(item) for item in (data or [])]
            return self._replace_prepared(table, rows, label, sql)
        except Exception as exc:
            logger.exception("Erreur préparation sync %s", label)
            return False, f"❌ Erreur sync : {exc}"

    def _replace_prepared(self, table, rows, label, sql):
        conn = self.connect()
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(f"DELETE FROM {table}")
            if rows:
                conn.executemany(sql, rows)
            conn.execute("COMMIT")
            return True, f"✅ {len(rows)} {label} synchronisés en local."
        except Exception as exc:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            logger.exception("Erreur sync %s", label)
            return False, f"❌ Erreur sync : {exc}"

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None
