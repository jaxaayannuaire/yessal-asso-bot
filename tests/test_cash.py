import os
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal


class CashDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import duckdb  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("duckdb non installé dans l'environnement de test")
        cls.tmpdir = tempfile.TemporaryDirectory()
        os.environ["DUCKDB_PATH"] = str(Path(cls.tmpdir.name) / "cash.duckdb")
        from core.db import DatabaseManager
        cls.DatabaseManager = DatabaseManager

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()
        os.environ.pop("DUCKDB_PATH", None)

    def test_cash_transaction_is_idempotent_by_key(self):
        db = self.DatabaseManager()
        try:
            self.assertTrue(db.init_db()[0])
            self.assertTrue(db.create_cash_transaction(
                "tx-1", "cash:key-1", "in", "1", Decimal("5000.00"),
                "Cotisation", "LIQ", "2026-08-13", "123", "tresorier",
                "pending_confirmation",
            ))
            self.assertFalse(db.create_cash_transaction(
                "tx-2", "cash:key-1", "in", "1", Decimal("5000.00"),
                "Doublon", "LIQ", "2026-08-13", "123", "tresorier",
                "pending_confirmation",
            ))
        finally:
            db.close()

    def test_cash_transaction_status_update(self):
        db = self.DatabaseManager()
        try:
            db.init_db()
            db.create_cash_transaction(
                "tx-3", "cash:key-3", "out", "1", Decimal("12000.00"),
                "Transport", "LIQ", "2026-08-13", "123", "tresorier",
                "pending_confirmation",
            )
            self.assertTrue(db.update_cash_transaction("tx-3", status="posted", dolibarr_line_id="42"))
            tx = db.get_cash_transaction_dict("tx-3")
            self.assertEqual(tx["status"], "posted")
            self.assertEqual(tx["dolibarr_line_id"], "42")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
