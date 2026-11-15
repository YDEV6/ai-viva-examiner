import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from stu_back.database import get_db
from stu_back.models import User
from stu_back.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    error = HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error

    user = db.get(User, user_id)
    if user is None:
        raise error
    return user

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can do this")
    return current_user

def require_student(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can do this")
return current_user