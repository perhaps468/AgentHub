from pydantic import BaseModel


class LoginRequest(BaseModel):
    userName: str
    password: str


class LoginResponseData(BaseModel):
    userId: int
    userName: str
    email: str
    avatar: str | None
    type: str
    token: str


class LoginResponse(BaseModel):
    code: int
    msg: str
    data: LoginResponseData | None = None
