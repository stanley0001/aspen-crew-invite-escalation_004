from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str
    email: str


class WorkspaceView(BaseModel):
    workspace_id: str
    name: str


class MemberView(BaseModel):
    user_id: str
    email: str
    role: str


class InviteCreate(BaseModel):
    """What an admin is supposed to send to POST /workspaces/{id}/invites.
    Lifecycle / denormalised fields (cached_role, accepted, accepted_by) are
    deliberately excluded — those are server-managed.
    """
    email: str
    role: str


class InviteView(BaseModel):
    invite_id: str
    workspace_id: str
    email: str
    role: str
    token: str
    expires_at: str
    accepted: bool


class AcceptResponse(BaseModel):
    workspace_id: str
    user_id: str
    role: str
