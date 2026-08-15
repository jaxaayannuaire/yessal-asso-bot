import os
import tempfile
import unittest
from pathlib import Path


class DatabaseManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import duckdb  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("duckdb non installé dans l'environnement de test")

        cls.tmpdir = tempfile.TemporaryDirectory()
        os.environ["DUCKDB_PATH"] = str(Path(cls.tmpdir.name) / "test.duckdb")

        from core.db import DatabaseManager
        cls.DatabaseManager = DatabaseManager

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()
        os.environ.pop("DUCKDB_PATH", None)

    def test_init_db_is_idempotent(self):
        db = self.DatabaseManager()
        try:
            self.assertTrue(db.init_db()[0])
            self.assertTrue(db.init_db()[0])
        finally:
            db.close()

    def test_sync_contacts_replaces_cache(self):
        db = self.DatabaseManager()
        try:
            db.init_db()
            ok, _ = db.sync_contacts([{"id": 1, "firstname": "A", "lastname": "B"}])
            self.assertTrue(ok)
            self.assertEqual(db.search_contacts("A")[0][0], "1")
            ok, _ = db.sync_contacts([])
            self.assertTrue(ok)
            self.assertEqual(db.search_contacts("A"), [])
        finally:
            db.close()

    def test_sync_members_replaces_cache_with_same_ids(self):
        db = self.DatabaseManager()
        try:
            db.init_db()

            members = [
                {
                    "id": "1",
                    "firstname": "SERIGNE KHADIM",
                    "lastname": "LO",
                    "morphy": "phy",
                    "email": "",
                    "phone": "775323208",
                    "statut": "1",
                    "date_fin": "",
                },
                {
                    "id": "2",
                    "firstname": "TEST",
                    "lastname": "MEMBRE",
                    "morphy": "phy",
                    "email": "",
                    "phone": "770000000",
                    "statut": "1",
                    "date_fin": "",
                },
            ]

            # Première synchronisation.
            ok, message = db.sync_members(members)
            self.assertTrue(ok, message)

            count = db.connect().execute(
                "SELECT COUNT(*) FROM cache_members"
            ).fetchone()[0]
            self.assertEqual(count, 2)

            # Deuxième synchronisation avec exactement les mêmes IDs.
            ok, message = db.sync_members(members)
            self.assertTrue(ok, message)

            count = db.connect().execute(
                "SELECT COUNT(*) FROM cache_members"
            ).fetchone()[0]
            self.assertEqual(count, 2)

            # Vérifie qu'il n'y a aucun doublon.
            rows = db.connect().execute(
                "SELECT id FROM cache_members ORDER BY id"
            ).fetchall()

            self.assertEqual(
                [row[0] for row in rows],
                ["1", "2"],
            )

        finally:
            db.close()


    def test_sync_members_replaces_old_members(self):
        db = self.DatabaseManager()
        try:
            db.init_db()

            first = [
                {
                    "id": "1",
                    "firstname": "ANCIEN",
                    "lastname": "MEMBRE",
                    "morphy": "phy",
                    "email": "",
                    "phone": "",
                    "statut": "1",
                    "date_fin": "",
                },
                {
                    "id": "2",
                    "firstname": "A",
                    "lastname": "SUPPRIMER",
                    "morphy": "phy",
                    "email": "",
                    "phone": "",
                    "statut": "1",
                    "date_fin": "",
                },
            ]

            second = [
                {
                    "id": "1",
                    "firstname": "MEMBRE",
                    "lastname": "MODIFIE",
                    "morphy": "phy",
                    "email": "",
                    "phone": "",
                    "statut": "1",
                    "date_fin": "",
                },
                {
                    "id": "3",
                    "firstname": "NOUVEAU",
                    "lastname": "MEMBRE",
                    "morphy": "phy",
                    "email": "",
                    "phone": "",
                    "statut": "1",
                    "date_fin": "",
                },
            ]

            ok, message = db.sync_members(first)
            self.assertTrue(ok, message)

            ok, message = db.sync_members(second)
            self.assertTrue(ok, message)

            rows = db.connect().execute(
                """
                SELECT id, firstname, lastname
                FROM cache_members
                ORDER BY id
                """
            ).fetchall()

            self.assertEqual(
                rows,
                [
                    ("1", "MEMBRE", "MODIFIE"),
                    ("3", "NOUVEAU", "MEMBRE"),
                ],
            )

        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
