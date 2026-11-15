from fastapi import Depends, FastAPI
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from stu_back.database import get_db
from stu_back.models import User

app = FastAPI(title="AI Viva Examiner")


@app.get("/hello")
def say_hello():
    return {"message": "Hello, student!"}


@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    user_count = db.scalar(select(func.count()).select_from(User))
    return {"database": "connected", "users": user_count}