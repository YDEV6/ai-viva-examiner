from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from stu_back.database import get_db
from stu_back.models import User
from stu_back.schemas import SignupRequest, UserResponse
from stu_back.security import hash_password

app = FastAPI(title="AI Viva Examiner")


@app.get("/hello")
def say_hello():
    return {"message": "Hello, student!"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    user_count = db.scalar(select(func.count()).select_from(User))
    return {"database": "connected", "users": user_count}


@app.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user         