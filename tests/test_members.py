import unittest
from datetime import datetime, timedelta, timezone

from modules.members import build_members_overview, format_members_overview


class MembersOverviewTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
        self.types = [
            {"id": "1", "label": "Membre Actif"},
            {"id": "2", "label": "Membre d'Honneur"},
            {"id": "3", "label": "Membre Sympathisant"},
            {"id": "4", "label": "Membre Bienfaiteur"},
        ]

    def test_totals_active_and_new_30_days(self):
        members = [
            {"id": "1", "statut": "1", "typeid": "1", "date_creation": self.now.timestamp()},
            {"id": "2", "statut": "1", "typeid": "1", "date_creation": (self.now - timedelta(days=40)).timestamp()},
            {"id": "3", "statut": "0", "typeid": "2", "date_creation": (self.now - timedelta(days=5)).timestamp()},
        ]
        stats = build_members_overview(members, self.types, now=self.now)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["active"], 2)
        self.assertEqual(stats["inactive"], 1)
        self.assertEqual(stats["new_30_days"], 2)

    def test_counts_by_type_include_zero(self):
        members = [
            {"id": "1", "statut": "1", "typeid": "1", "date_creation": self.now.timestamp()},
            {"id": "2", "statut": "1", "typeid": "1", "date_creation": self.now.timestamp()},
            {"id": "3", "statut": "1", "typeid": "4", "date_creation": self.now.timestamp()},
        ]
        stats = build_members_overview(members, self.types, now=self.now)
        self.assertEqual(
            [(x["label"], x["count"]) for x in stats["by_type"]],
            [
                ("Membre Actif", 2),
                ("Membre d'Honneur", 0),
                ("Membre Sympathisant", 0),
                ("Membre Bienfaiteur", 1),
            ],
        )

    def test_older_than_30_days_not_new(self):
        members = [{
            "id": "1",
            "statut": "1",
            "typeid": "1",
            "date_creation": (self.now - timedelta(days=31)).timestamp(),
        }]
        stats = build_members_overview(members, self.types, now=self.now)
        self.assertEqual(stats["new_30_days"], 0)

    def test_empty_members(self):
        stats = build_members_overview([], self.types, now=self.now)
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["active"], 0)
        self.assertEqual(stats["inactive"], 0)
        self.assertEqual(stats["new_30_days"], 0)
        self.assertEqual(stats["by_type"][0]["count"], 0)

    def test_format_contains_expected_values(self):
        text = format_members_overview({
            "total": 13,
            "active": 10,
            "inactive": 3,
            "new_30_days": 4,
            "by_type": [
                {"id": "1", "label": "Membre Actif", "count": 10},
                {"id": "4", "label": "Membre Bienfaiteur", "count": 2},
            ],
        })
        self.assertIn("Total : 13", text)
        self.assertIn("Nouveaux (30 jours) : 4", text)
        self.assertIn("Membre Actif : 10", text)
        self.assertIn("Membre Bienfaiteur : 2", text)


if __name__ == "__main__":
    unittest.main()
