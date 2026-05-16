from fastapi import APIRouter, HTTPException, status

from crew import auth
from crew.schemas import LoginRequest, LoginResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login_endpoint(req: LoginRequest) -> LoginResponse:
    user = auth.login(req.email, req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    token = auth.issue_token(user)
    return LoginResponse(token=token, user_id=user.user_id, email=user.email)
