import uuid
from stu_back.deps import get_current_user, require_teacher
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from stu_back.database import get_db
from stu_back.models import Exam,Questions, User
from stu_back.schemas import (
    ExamCreate,
    ExamResponse,
    LoginRequest,
    QuestionCreate,
    QuestionResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from stu_back.security import create_access_token, hash_password, verify_password

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


@app.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token)

@app.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    data: ExamCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    exam = Exam(teacher_id=teacher.id, title=data.title, topic=data.topic)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam

@app.post(
    "/exams/{exam_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_question(
    exam_id: uuid.UUID,
    data: QuestionCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="This is not your exam")

    question = Question(exam_id=exam.id, question_text=data.question_text)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question