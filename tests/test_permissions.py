from core.permissions import (
    ROLE_BUREAU,
    ROLE_PRESIDENT,
    ROLE_SUPER_ADMIN,
    ROLE_TRESORIER,
    get_effective_role,
    has_permission,
    is_valid_dolibarr_user_id,
    role_from_group_name,
)


def test_business_groups_map_to_roles():
    assert role_from_group_name("YESSAL_TRESORIER") == ROLE_TRESORIER
    assert role_from_group_name("YESSAL_BUREAU") == ROLE_BUREAU
    assert role_from_group_name("YESSAL_PRESIDENT") == ROLE_PRESIDENT


def test_technical_group_is_not_a_role():
    assert role_from_group_name("Yessal Asso Bot") is None


def test_role_priority():
    assert get_effective_role({ROLE_BUREAU, ROLE_TRESORIER}) == ROLE_TRESORIER
    assert get_effective_role({ROLE_PRESIDENT, ROLE_TRESORIER}) == ROLE_PRESIDENT


def test_super_admin():
    assert has_permission({ROLE_SUPER_ADMIN}, "caisse.approve")
    assert has_permission({ROLE_SUPER_ADMIN}, "roles.manage")


def test_dolibarr_id_only():
    assert is_valid_dolibarr_user_id("7")
    assert not is_valid_dolibarr_user_id("webmaster")
