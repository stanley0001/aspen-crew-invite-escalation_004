import secrets
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException

from crew.auth import current_user, require_workspace_role
from crew.models import ADMIN, MEMBER, VALID_ROLES, VIEWER, Invite, expiry_in, store
from crew.schemas import InviteView, MemberView, WorkspaceView


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=List[WorkspaceView])
def list_my_workspaces(caller=Depends(current_user)) -> List[WorkspaceView]:
    mine = {m.workspace_id for m in store.memberships if m.user_id == caller.user_id}
    return [WorkspaceView(workspace_id=w.workspace_id, name=w.name)
            for w in store.workspaces.values() if w.workspace_id in mine]


@router.get("/{workspace_id}/members", response_model=List[MemberView])
def list_members(workspace_id: str, caller=Depends(current_user)) -> List[MemberView]:
    require_workspace_role(caller, workspace_id, (ADMIN, MEMBER, VIEWER))
    out: List[MemberView] = []
    for m in store.members_of(workspace_id):
        u = store.users.get(m.user_id)
        if u is None:
            continue
        out.append(MemberView(user_id=u.user_id, email=u.email, role=m.role))
    return out


@router.post("/{workspace_id}/invites", response_model=InviteView, status_code=201)
def create_invite(
    workspace_id: str,
    payload: Dict[str, Any] = Body(...),
    caller=Depends(current_user),
) -> InviteView:
    caller_role = require_workspace_role(caller, workspace_id, (ADMIN, MEMBER))

    email = payload.get("email")
    role = payload.get("role")
    if not isinstance(email, str) or not email:
        raise HTTPException(status_code=422, detail="email required")
    if role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail="invalid role")
    # MEMBERs can invite peers and viewers; only ADMINs can promote to ADMIN
    if caller_role == MEMBER and role == ADMIN:
        raise HTTPException(status_code=403, detail="only admins may invite admins")

    token = secrets.token_urlsafe(20)
    invite = Invite(
        invite_id=f"inv_{secrets.token_hex(4)}",
        workspace_id=workspace_id,
        email=email,
        role=role,
        inviter_id=caller.user_id,
        token=token,
        expires_at=expiry_in(7),
    )
    for key, value in payload.items():
        if hasattr(invite, key):
            setattr(invite, key, value)
    store.invites[token] = invite
    return InviteView(
        invite_id=invite.invite_id,
        workspace_id=invite.workspace_id,
        email=invite.email,
        role=invite.role,
        token=invite.token,
        expires_at=invite.expires_at,
        accepted=invite.accepted,
    )


@router.get("/{workspace_id}/invites", response_model=List[InviteView])
def list_invites(workspace_id: str, caller=Depends(current_user)) -> List[InviteView]:
    require_workspace_role(caller, workspace_id, (ADMIN,))
    return [
        InviteView(
            invite_id=inv.invite_id,
            workspace_id=inv.workspace_id,
            email=inv.email,
            role=inv.role,
            token=inv.token,
            expires_at=inv.expires_at,
            accepted=inv.accepted,
        )
        for inv in store.invites.values()
        if inv.workspace_id == workspace_id
    ]
