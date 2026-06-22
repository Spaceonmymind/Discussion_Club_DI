from typing import Optional

from pydantic import BaseModel, EmailStr


class ParticipantCreate(BaseModel):
    name: Optional[str] = None
    is_anonymous: bool = False


class AnswerCreate(BaseModel):
    participant_id: int
    answer_text: str


class LiveQuestionCreate(BaseModel):
    participant_id: int
    text: str


class PreparedQuestionCreate(BaseModel):
    text: str
    description: Optional[str] = ""
    order_index: int = 0
    is_active: bool = True


class PreparedQuestionPatch(BaseModel):
    text: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None


class StatusPatch(BaseModel):
    status: str


class PinPatch(BaseModel):
    is_pinned: bool


class CommentPatch(BaseModel):
    moderator_comment: str


class EventCreate(BaseModel):
    title: str
    description: str = ""
    date: str
    start_time: str
    end_time: Optional[str] = None
    location: str = ""
    status: str = "draft"
    public_code: Optional[str] = None


class EventPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    public_code: Optional[str] = None


class ModeratorCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
