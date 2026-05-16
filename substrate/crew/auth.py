import secrets
from typing import Dict, Optional

from fastapi import Header, HTTPException, status

from crew.models import User, store


_tokens: Dict[str, str] = {}  # token -> user_id


def login(email: str, password: str) -> Optional[User]:
    user = store.users_by_email.get(email)
    if user is None or user.password != password:
        return None
    return user


def issue_token(user: User) -> str:
    token = secrets.token_urlsafe(24)
    _tokens[token] = user.user_id
    return token


def resolve(token: str) -> Optional[User]:
    user_id = _tokens.get(token)
    if user_id is None:
        return None
    return store.users.get(user_id)


def current_user(authorization: Optional[str] = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    token = authorization.split(" ", 1)[1].strip()
    user = resolve(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
        )
    return user


def require_workspace_role(user: User, workspace_id: str, allowed: tuple) -> str:
    if workspace_id not in store.workspaces:
        raise HTTPException(status_code=404, detail="workspace not found")
    role = store.member_role(user.user_id, workspace_id)
    if role is None:
        raise HTTPException(status_code=403, detail="not a member of this workspace")
    if role not in allowed:
        raise HTTPException(status_code=403, detail="insufficient role")
    return role


def _clear_tokens() -> None:
    """Test-only helper for state reset between tests."""
    _tokens.clear()
