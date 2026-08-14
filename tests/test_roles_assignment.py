from modules.roles import (
    MANAGED_ROLES,
    ROLE_COMMANDS,
    _numeric_id,
    _role_assignment_usage,
)
from core.permissions import (
    ROLE_ADMIN,
    ROLE_BUREAU,
    ROLE_MEMBRE,
    ROLE_PRESIDENT,
    ROLE_TRESORIER,
)


class DummyContext:
    def __init__(self, args):
        self.args = args


def test_role_commands_cover_business_roles():
    assert ROLE_PRESIDENT in ROLE_COMMANDS
    assert ROLE_BUREAU in ROLE_COMMANDS
    assert ROLE_TRESORIER in ROLE_COMMANDS
    assert ROLE_ADMIN in ROLE_COMMANDS
    assert ROLE_MEMBRE in ROLE_COMMANDS


def test_numeric_dolibarr_id_only():
    assert _numeric_id(DummyContext(["7"])) == "7"
    assert _numeric_id(DummyContext(["007"])) == "007"
    assert _numeric_id(DummyContext(["webmaster"])) is None
    assert _numeric_id(DummyContext(["7", "extra"])) is None
    assert _numeric_id(DummyContext([])) is None


def test_role_assignment_usage_uses_dolibarr_id():
    usage = _role_assignment_usage(ROLE_TRESORIER)
    assert usage.startswith("Usage : /nommer_tresorier")
    assert "<ID_DOLIBARR>" in usage


def test_managed_roles_are_defined():
    assert ROLE_PRESIDENT in MANAGED_ROLES
    assert ROLE_BUREAU in MANAGED_ROLES
    assert ROLE_TRESORIER in MANAGED_ROLES
    assert ROLE_ADMIN in MANAGED_ROLES
    assert ROLE_MEMBRE in MANAGED_ROLES
