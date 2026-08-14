from core.permissions import (
    ROLE_BUREAU,
    ROLE_PRESIDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TRESORIER,
    get_effective_role,
    has_permission,
    role_from_group_name,
)


def test_group_name_mapping():
    assert role_from_group_name("Trésorier") == ROLE_TRESORIER
    assert role_from_group_name("Membre du Bureau") == ROLE_BUREAU
    assert role_from_group_name("PRESIDENT") == ROLE_PRESIDENT


def test_effective_role_priority():
    assert get_effective_role({ROLE_BUREAU, ROLE_TRESORIER}) == ROLE_TRESORIER
    assert get_effective_role({ROLE_PRESIDENT, ROLE_TRESORIER}) == ROLE_PRESIDENT


def test_super_admin_has_everything():
    assert has_permission({ROLE_SUPER_ADMIN}, "caisse.approve")
    assert has_permission({ROLE_SUPER_ADMIN}, "roles.manage")
