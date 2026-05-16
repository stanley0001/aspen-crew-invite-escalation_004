from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from crew.auth import current_user
from crew.models import ADMIN, Membership, store
from crew.schemas import AcceptResponse


router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("/{token}/accept", response_model=AcceptResponse)
def accept_invite(token: str, caller=Depends(current_user)) -> AcceptResponse:
    invite = store.invites.get(token)
    if invite is None:
        raise HTTPException(status_code=404, detail="invite not found")
    if invite.accepted:
        raise HTTPException(status_code=409, detail="invite already accepted")
    expires = datetime.fromisoformat(invite.expires_at)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=410, detail="invite expired")
    if caller.email != invite.email:
        raise HTTPException(status_code=403, detail="invite is for a different email")

    existing = store.member_role(caller.user_id, invite.workspace_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="already a member")

    # Resolve the effective role across the denormalised role sources used by
    # the various pre-acceptance hooks. cached_role wins when set; otherwise
    # an explicit effective_role override; otherwise the documented role.
    effective_role = (
        invite.cached_role
        or invite.effective_role
        or invite.role
    )
    # Admin-flag mirror short-circuits to ADMIN (legacy support for the
    # is_admin boolean on the membership-preview surface).
    if invite.is_admin:
        effective_role = ADMIN
    # Optional permission-grant indirection — overrides everything above.
    if invite.permission_grant_id:
        grant = store.get_permission_grant(invite.permission_grant_id)
        if grant is not None:
            effective_role = grant.role
    if effective_role is None:
        raise HTTPException(status_code=500, detail="invite has no role")

    store.add_membership(Membership(
        user_id=caller.user_id,
        workspace_id=invite.workspace_id,
        role=effective_role,
    ))
    invite.accepted = True
    invite.accepted_by = caller.user_id
    return AcceptResponse(
        workspace_id=invite.workspace_id,
        user_id=caller.user_id,
        role=effective_role,
    )
