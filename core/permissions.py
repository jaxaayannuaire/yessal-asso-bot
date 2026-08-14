import logging
import re
from typing import Iterable


logger = logging.getLogger(__name__)

ROLE_SUPER_ADMIN = "super_admin"
ROLE_PRESIDENT = "president"
ROLE_BUREAU = "bureau"
ROLE_TRESORIER = "tresorier"
ROLE_ADMIN = "admin"
ROLE_MEMBRE = "membre"
ROLE_USER = "user"

ROLE_PRIORITY = {
    ROLE_SUPER_ADMIN: 100,
    ROLE_PRESIDENT: 90,
    ROLE_TRESORIER: 80,
    ROLE_BUREAU: 70,
    ROLE_ADMIN: 60,
    ROLE_MEMBRE: 50,
    ROLE_USER: 0,
}

GROUP_ROLE_ALIASES = {
    "SUPER_ADMIN": ROLE_SUPER_ADMIN,
    "SUPER ADMIN": ROLE_SUPER_ADMIN,
    "PRESIDENT": ROLE_PRESIDENT,
    "PRÉSIDENT": ROLE_PRESIDENT,
    "BUREAU": ROLE_BUREAU,
    "MEMBRE DU BUREAU": ROLE_BUREAU,
    "TRESORIER": ROLE_TRESORIER,
    "TRÉSORIER": ROLE_TRESORIER,
    "ADMIN": ROLE_ADMIN,
    "ADMINISTRATEUR": ROLE_ADMIN,
    "MEMBRE": ROLE_MEMBRE,
}

ROLE_GROUP_NAMES = {
    ROLE_SUPER_ADMIN: "SUPER_ADMIN",
    ROLE_PRESIDENT: "PRESIDENT",
    ROLE_BUREAU: "BUREAU",
    ROLE_TRESORIER: "TRESORIER",
    ROLE_ADMIN: "ADMIN",
    ROLE_MEMBRE: "MEMBRE",
}

ROLE_PERMISSIONS = {
    ROLE_SUPER_ADMIN: {"*", "roles.manage"},
    ROLE_PRESIDENT: {"caisse.view", "caisse.create", "caisse.approve", "reports.view", "members.view", "roles.view"},
    ROLE_TRESORIER: {"caisse.view", "caisse.create", "reports.view", "members.view"},
    ROLE_BUREAU: {"caisse.view", "reports.view", "members.view", "roles.view"},
    ROLE_ADMIN: {"reports.view", "members.view", "roles.view"},
    ROLE_MEMBRE: {"members.self", "contributions.self"},
    ROLE_USER: {"members.self", "contributions.self"},
}


def normalize_group_name(name: str) -> str:
    value = str(name or "").strip().upper()
    value = re.sub(r"\s+", " ", value)
    return value


def role_from_group_name(name: str) -> str | None:
    return GROUP_ROLE_ALIASES.get(normalize_group_name(name))


def ensure_schema(db) -> None:
    conn = db.connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_users (
            telegram_id VARCHAR PRIMARY KEY,
            username VARCHAR,
            role VARCHAR DEFAULT 'user',
            dolibarr_contact_id VARCHAR,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    existing = {row[0].lower() for row in conn.execute("DESCRIBE bot_users").fetchall()}
    if "dolibarr_user_id" not in existing:
        conn.execute("ALTER TABLE bot_users ADD COLUMN dolibarr_user_id VARCHAR")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dolibarr_users (
            id VARCHAR PRIMARY KEY,
            login VARCHAR,
            firstname VARCHAR,
            lastname VARCHAR,
            email VARCHAR,
            active BOOLEAN DEFAULT true,
            last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dolibarr_groups (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            ref VARCHAR,
            last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dolibarr_user_groups (
            dolibarr_user_id VARCHAR NOT NULL,
            dolibarr_group_id VARCHAR NOT NULL,
            role VARCHAR,
            last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (dolibarr_user_id, dolibarr_group_id)
        )
        """
    )


def _first(data: dict, *keys, default=None):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return default


def sync_from_dolibarr(client, db) -> tuple[bool, str]:
    ensure_schema(db)
    ok_users, users = client.get_dolibarr_users()
    if not ok_users:
        return False, f"Impossible de synchroniser les utilisateurs Dolibarr : {users}"
    ok_groups, groups = client.get_dolibarr_groups()
    if not ok_groups:
        return False, f"Impossible de synchroniser les groupes Dolibarr : {groups}"

    conn = db.connect()
    conn.execute("DELETE FROM dolibarr_user_groups")
    conn.execute("DELETE FROM dolibarr_users")
    conn.execute("DELETE FROM dolibarr_groups")

    group_roles = {}
    for group in groups or []:
        gid = str(_first(group, "id", "rowid"))
        name = str(_first(group, "name", "nom", "label", default=""))
        ref = str(_first(group, "ref", default=""))
        if gid and gid != "None":
            group_roles[gid] = role_from_group_name(name)
            conn.execute("INSERT INTO dolibarr_groups VALUES (?, ?, ?, CURRENT_TIMESTAMP)", [gid, name, ref])

    synced_users = 0
    linked_memberships = 0
    for user in users or []:
        uid = str(_first(user, "id", "rowid"))
        if not uid or uid == "None":
            continue
        login = str(_first(user, "login", default=""))
        firstname = str(_first(user, "firstname", default=""))
        lastname = str(_first(user, "lastname", default=""))
        email = str(_first(user, "email", default=""))
        active_value = _first(user, "statut", "status", "active", default=1)
        active = bool(int(active_value)) if str(active_value).isdigit() else bool(active_value)
        conn.execute("INSERT INTO dolibarr_users VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", [uid, login, firstname, lastname, email, active])
        synced_users += 1

        ok_memberships, memberships = client.get_dolibarr_user_groups(uid)
        if not ok_memberships:
            logger.warning("Impossible de lire les groupes de l'utilisateur Dolibarr %s: %s", uid, memberships)
            continue
        for group in memberships or []:
            gid = str(_first(group, "id", "rowid"))
            if not gid or gid == "None":
                continue
            role = group_roles.get(gid) or role_from_group_name(_first(group, "name", "nom", "label", default=""))
            conn.execute(
                "INSERT OR REPLACE INTO dolibarr_user_groups VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                [uid, gid, role],
            )
            linked_memberships += 1

    return True, f"✅ Synchronisation des rôles terminée : {synced_users} utilisateurs, {len(group_roles)} groupes, {linked_memberships} appartenances."


def get_roles_for_dolibarr_user(db, dolibarr_user_id: str) -> set[str]:
    ensure_schema(db)
    rows = db.connect().execute(
        "SELECT role FROM dolibarr_user_groups WHERE dolibarr_user_id = ? AND role IS NOT NULL",
        [str(dolibarr_user_id)],
    ).fetchall()
    return {row[0] for row in rows if row[0]}


def get_effective_role(roles: Iterable[str]) -> str:
    values = set(roles)
    if not values:
        return ROLE_USER
    return max(values, key=lambda role: ROLE_PRIORITY.get(role, -1))


def has_permission(roles: Iterable[str], permission: str) -> bool:
    for role in roles:
        permissions = ROLE_PERMISSIONS.get(role, set())
        if "*" in permissions or permission in permissions:
            return True
    return False


def find_dolibarr_user(db, target: str):
    ensure_schema(db)
    value = str(target).strip()
    return db.connect().execute(
        """
        SELECT id, login, firstname, lastname, email, active
        FROM dolibarr_users
        WHERE id = ? OR lower(login) = lower(?)
        LIMIT 1
        """,
        [value, value],
    ).fetchone()


def find_group_by_role(db, role: str):
    ensure_schema(db)
    name = ROLE_GROUP_NAMES.get(role)
    if not name:
        return None
    return db.connect().execute(
        """
        SELECT id, name, ref
        FROM dolibarr_groups
        WHERE upper(trim(name)) = upper(?) OR upper(trim(ref)) = upper(?)
        LIMIT 1
        """,
        [name, name],
    ).fetchone()
