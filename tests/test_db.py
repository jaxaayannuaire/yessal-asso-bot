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


if __name__ == "__main__":
    unittest.main()
