from pydantic import BaseModel
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, CurrentUser
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse
from app.services.group_host_agent import ensure_user_group_host_agent

router = APIRouter(prefix="/api/v1/user", tags=["auth"])
_db = Annotated[Session, Depends(get_db)]


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: _db) -> LoginResponse:
    user = db.query(User).filter(User.username == body.userName).first()
    if user is None or user.password != body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    ensure_user_group_host_agent(db, str(user.id))
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

    next_user_id = (db.query(User).count() or 0) + 1
    new_user = User(id=next_user_id, username=body.userName, password=body.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    ensure_user_group_host_agent(db, str(new_user.id))
    return {"code": 0, "msg": "注册成功", "data": None}


class UserUpdateRequest(BaseModel):
    avatar: str | None = None


@router.post("/update")
def update_user(body: UserUpdateRequest, current_user: CurrentUser, db: _db):
    user = db.get(User, current_user.id)
    if user is None:
        return {"code": 404, "msg": "用户不存在", "data": None}
    if body.avatar is not None:
        user.avatar = body.avatar
    db.commit()
    return {"code": 0, "msg": "更新成功", "data": None}
