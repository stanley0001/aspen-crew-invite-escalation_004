from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


ADMIN = "ADMIN"
MEMBER = "MEMBER"
VIEWER = "VIEWER"
VALID_ROLES = (ADMIN, MEMBER, VIEWER)


@dataclass
class User:
    user_id: str
    email: str
    password: str
    display_name: str = ""


@dataclass
class Membership:
    user_id: str
    workspace_id: str
    role: str


@dataclass
class Workspace:
    workspace_id: str
    name: str
    created_by: str


@dataclass
class PermissionGrant:
    """Pre-issued role grant, looked up by id during invite acceptance.
    Used by some legacy onboarding flows that pre-stage permissions before
    the invitee accepts."""
    grant_id: str
    role: str
    issued_by: str


@dataclass
class Invite:
    invite_id: str
    workspace_id: str
    email: str
    role: str
    inviter_id: str
    token: str
    expires_at: str
    # Denormalised role cache, used for fast member-listing previews.
    cached_role: Optional[str] = None
    # Effective role override; populated by the role-resolver job when a
    # cached_role lookup needs to fall back to a different value.
    effective_role: Optional[str] = None
    # Convenience flag mirrored from membership for admin-only UI surfaces.
    is_admin: bool = False
    # Optional pointer to a pre-issued PermissionGrant resolved at accept-time.
    permission_grant_id: Optional[str] = None
    accepted: bool = False
    accepted_by: Optional[str] = None


class Store:
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}
        self.users_by_email: Dict[str, User] = {}
        self.workspaces: Dict[str, Workspace] = {}
        self.memberships: List[Membership] = []
        self.invites: Dict[str, Invite] = {}  # by token
        self.permission_grants: Dict[str, PermissionGrant] = {}

    def add_user(self, user: User) -> None:
        self.users[user.user_id] = user
        self.users_by_email[user.email] = user

    def add_workspace(self, ws: Workspace) -> None:
        self.workspaces[ws.workspace_id] = ws

    def add_membership(self, m: Membership) -> None:
        self.memberships.append(m)

    def add_permission_grant(self, g: PermissionGrant) -> None:
        self.permission_grants[g.grant_id] = g

    def get_permission_grant(self, grant_id: str) -> Optional[PermissionGrant]:
        return self.permission_grants.get(grant_id)

    def member_role(self, user_id: str, workspace_id: str) -> Optional[str]:
        for m in self.memberships:
            if m.user_id == user_id and m.workspace_id == workspace_id:
                return m.role
        return None

    def members_of(self, workspace_id: str) -> List[Membership]:
        return [m for m in self.memberships if m.workspace_id == workspace_id]

    def reset(self) -> None:
        self.users.clear()
        self.users_by_email.clear()
        self.workspaces.clear()
        self.memberships.clear()
        self.invites.clear()
        self.permission_grants.clear()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def expiry_in(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()


def seed(s: Store) -> None:
    s.add_user(User(user_id="u_root", email="root@crew.local", password="root123", display_name="Root"))
    s.add_user(User(user_id="u_alice", email="alice@crew.local", password="alice123", display_name="Alice"))
    s.add_user(User(user_id="u_bob", email="bob@crew.local", password="bob123", display_name="Bob"))
    s.add_user(User(user_id="u_dana", email="dana@crew.local", password="dana123", display_name="Dana"))

    # Two workspaces. Root admins ws_main, Bob admins ws_side. Alice is a MEMBER of
    # ws_main. Dana is unaffiliated.
    s.add_workspace(Workspace(workspace_id="ws_main", name="Main", created_by="u_root"))
    s.add_workspace(Workspace(workspace_id="ws_side", name="Side", created_by="u_bob"))

    s.add_membership(Membership(user_id="u_root", workspace_id="ws_main", role=ADMIN))
    s.add_membership(Membership(user_id="u_alice", workspace_id="ws_main", role=MEMBER))
    s.add_membership(Membership(user_id="u_bob", workspace_id="ws_side", role=ADMIN))

    # Pre-staged grants for the legacy onboarding flow. Resolvable by id at
    # invite-accept time.
    s.add_permission_grant(PermissionGrant(grant_id="pg_admin_001", role=ADMIN, issued_by="u_root"))
    s.add_permission_grant(PermissionGrant(grant_id="pg_member_001", role=MEMBER, issued_by="u_root"))


store = Store()
seed(store)
