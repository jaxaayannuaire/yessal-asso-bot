from services.sync_service import SyncService


class FakeClient:
    def get_contacts(self): return True, [{"id": 1}, {"id": 2}]
    def get_members(self): return True, [{"id": 1}]
    def get_memberships(self): return True, []
    def get_contributions(self): return True, [{"id": 1}]


class FakeDb:
    def __init__(self): self.saved = []
    def close(self): pass
    def sync_contacts(self, rows): self.saved.append(("contacts", rows)); return True, "ok"
    def sync_members(self, rows): self.saved.append(("members", rows)); return True, "ok"
    def sync_memberships(self, rows): self.saved.append(("memberships", rows)); return True, "ok"
    def sync_contributions(self, rows): self.saved.append(("contributions", rows)); return True, "ok"
    def get_dashboard_stats(self): return True, {"total_contacts": 2}


def test_full_sync_uses_all_components():
    db = FakeDb()
    results = SyncService(FakeClient(), db).sync_full()
    assert [r.component for r in results] == ["contacts", "members", "memberships", "contributions"]
    assert all(r.success for r in results)
    assert [name for name, _ in db.saved] == ["contacts", "members", "memberships", "contributions"]


def test_profile_contacts_members_only():
    db = FakeDb()
    results = SyncService(FakeClient(), db).sync_profile("contacts_members")
    assert [r.component for r in results] == ["contacts", "members"]


def test_invalid_profile_rejected():
    try:
        SyncService(FakeClient(), FakeDb()).sync_profile("unknown")
    except ValueError as exc:
        assert "inconnu" in str(exc)
    else:
        raise AssertionError("ValueError attendu")
