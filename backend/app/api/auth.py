from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/v1/user", tags=["auth"])
_db = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: _db) -> LoginResponse:
    user = db.query(User).filter(User.username == body.userName).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if user.password != body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(user_id=user.id, username=user.username)
    return LoginResponse(
        code=0,
        msg="",
        data={
            "userId": user.id,
            "userName": user.username,
            "email": "",
            "avatar": user.avatar,
            "type": "user",
            "token": token,
        },
    )


@router.post("/register")
def register(body: LoginRequest, db: _db):
    existing = db.query(User).filter(User.username == body.userName).first()
    if existing is not None:
        return {"code": 409, "msg": "用户名已存在", "data": None}
    new_user = User(username=body.userName, password=body.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"code": 0, "msg": "注册成功", "data": None}
