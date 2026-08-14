from services.dolibarr_api import DolibarrClient


def test_group_crud_paths(monkeypatch):
    client = DolibarrClient()
    calls = []

    def fake_request(method, path, payload=None, params=None, timeout=None):
        calls.append((method, path, payload))
        return True, {"success": True}

    monkeypatch.setattr(client, "_request", fake_request)
    assert client.get_dolibarr_groups()[0]
    assert client.create_dolibarr_group("YESSAL_TEST")[0]
    assert client.update_dolibarr_group(2, {"name": "YESSAL_TEST_2"})[0]
    assert client.delete_dolibarr_group(2)[0]
    assert calls == [
        ("GET", "users/groups", None),
        ("POST", "users/groups", {"name": "YESSAL_TEST"}),
        ("PUT", "users/groups/2", {"name": "YESSAL_TEST_2"}),
        ("DELETE", "users/groups/2", None),
    ]


def test_group_capabilities_dolibarr_23(monkeypatch):
    client = DolibarrClient()
    monkeypatch.setattr(client, "get_version", lambda refresh=False: (True, "23.0.3"))
    ok, capabilities = client.get_api_capabilities()
    assert ok
    assert capabilities["groups.create"]
    assert capabilities["groups.update"]
    assert capabilities["groups.delete"]
    assert capabilities["user_groups.add"]
    assert capabilities["user_groups.remove"]


def test_group_capabilities_dolibarr_22(monkeypatch):
    client = DolibarrClient()
    monkeypatch.setattr(client, "get_version", lambda refresh=False: (True, "22.0.4"))
    ok, capabilities = client.get_api_capabilities()
    assert ok
    assert capabilities["groups.list"]
    assert not capabilities["groups.create"]
    assert not capabilities["groups.update"]
    assert not capabilities["groups.delete"]


def test_nested_status_version(monkeypatch):
    client = DolibarrClient()
    monkeypatch.setattr(
        client,
        "_get",
        lambda path, params=None, timeout=None: (
            True, {"success": {"dolibarr_version": "23.0.3"}}
        ),
    )
    ok, version = client.get_version(refresh=True)
    assert ok
    assert version == "23.0.3"
