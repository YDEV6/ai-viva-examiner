import uuid
from stu_back.deps import get_current_user, require_student, require_teacher
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from stu_back.database import get_db
from stu_back.models import Answer, Exam,Question, User, VivaSession
from stu_back.schemas import (
    AnswerCreate,
    AnswerResponse,
    ExamCreate,
    ExamResponse,
    LoginRequest,
    QuestionCreate,
    QuestionResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
    VivaSessionResponse,
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


@app.get("/exams", response_model=list[ExamResponse])
def list_exams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Exam).order_by(Exam.created_at.desc())
    if current_user.role == "teacher":
        query = query.where(Exam.teacher_id == current_user.id)
    return db.scalars(query).all()


@app.get("/exams/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@app.get("/exams/{exam_id}/questions", response_model=list[QuestionResponse])
def list_questions(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="This is not your exam")

    query = (
        select(Question)
        .where(Question.exam_id == exam.id)
        .order_by(Question.created_at)
    )
    return db.scalars(query).all()


@app.post(
    "/exams/{exam_id}/sessions",
    response_model=VivaSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_session(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: User = Depends(require_student),
):
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    question_count = db.scalar(
        select(func.count()).select_from(Question).where(Question.exam_id == exam.id)
    )
    if question_count == 0:
        raise HTTPException(status_code=400, detail="This exam has no questions yet")

    session = VivaSession(student_id=student.id, exam_id=exam.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@app.post(
    "/sessions/{session_id}/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_answer(
    session_id: uuid.UUID,
    data: AnswerCreate,
    db: Session = Depends(get_db),
    student: User = Depends(require_student),
):
    session = db.get(VivaSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.student_id != student.id:
        raise HTTPException(status_code=403, detail="This is not your session")
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="This viva is already finished")

    question = db.get(Question, data.question_id)
    if question is None or question.exam_id != session.exam_id:
        raise HTTPException(
            status_code=400, detail="This question is not part of this exam"
        )

    already_answered = db.scalar(
        select(Answer).where(
            Answer.session_id == session.id,
            Answer.question_id == question.id,
        )
    )
    if already_answered:
        raise HTTPException(status_code=409, detail="Question already answered")

    answer = Answer(
        session_id=session.id,
        question_id=question.id,
        answer_text=data.answer_text,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


@app.get("/sessions/{session_id}/next-question", response_model=QuestionResponse | None)
def get_next_question(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: User = Depends(require_student),
):
    session = db.get(VivaSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.student_id != student.id:
        raise HTTPException(status_code=403, detail="This is not your session")
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="This viva is already finished")

    answered_ids = select(Answer.question_id).where(Answer.session_id == session.id)
    query = (
        select(Question)
        .where(Question.exam_id == session.exam_id, Question.id.not_in(answered_ids))
        .order_by(Question.created_at)
        .limit(1)
    )
    return db.scalar(query)