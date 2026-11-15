import uuid
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["teacher", "student"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ExamCreate(BaseModel):
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    teacher_id: uuid.UUID
    title: str
    topic: str
    created_at: datetime

class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_id: uuid.UUID
    question_text: str
    created_at: datetime

class VivaSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    exam_id: uuid.UUID
    status: str
    final_score: float | None
    created_at: datetime