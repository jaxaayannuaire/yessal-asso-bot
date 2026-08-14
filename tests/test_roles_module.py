from modules.roles import refresh_command_menu


def test_roles_module_exports_refresh_command_menu():
    assert callable(refresh_command_menu)
