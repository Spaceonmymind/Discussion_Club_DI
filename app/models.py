from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)

    events = relationship("Event", back_populates="creator")


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=True)
    location = Column(String(255), default="")
    status = Column(String(20), default="draft", nullable=False)
    public_code = Column(String(32), unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    creator = relationship("User", back_populates="events")
    prepared_questions = relationship("PreparedQuestion", cascade="all, delete-orphan", back_populates="event")
    participants = relationship("Participant", cascade="all, delete-orphan", back_populates="event")
    live_questions = relationship("LiveQuestion", cascade="all, delete-orphan", back_populates="event")


class PreparedQuestion(Base, TimestampMixin):
    __tablename__ = "prepared_questions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    text = Column(Text, nullable=False)
    description = Column(Text, default="")
    order_index = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    event = relationship("Event", back_populates="prepared_questions")
    answers = relationship("ParticipantAnswer", cascade="all, delete-orphan", back_populates="prepared_question")


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String(120), nullable=True)
    is_anonymous = Column(Boolean, default=False)
    session_token = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="participants")
    answers = relationship("ParticipantAnswer", cascade="all, delete-orphan", back_populates="participant")
    live_questions = relationship("LiveQuestion", cascade="all, delete-orphan", back_populates="participant")
    votes = relationship("QuestionVote", cascade="all, delete-orphan", back_populates="participant")


class ParticipantAnswer(Base):
    __tablename__ = "participant_answers"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    prepared_question_id = Column(Integer, ForeignKey("prepared_questions.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    prepared_question = relationship("PreparedQuestion", back_populates="answers")
    participant = relationship("Participant", back_populates="answers")


class LiveQuestion(Base, TimestampMixin):
    __tablename__ = "live_questions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), default="moderation", nullable=False)
    is_pinned = Column(Boolean, default=False)
    votes_count = Column(Integer, default=0)
    moderator_comment = Column(Text, default="")

    event = relationship("Event", back_populates="live_questions")
    participant = relationship("Participant", back_populates="live_questions")
    votes = relationship("QuestionVote", cascade="all, delete-orphan", back_populates="live_question")


class QuestionVote(Base):
    __tablename__ = "question_votes"
    __table_args__ = (UniqueConstraint("live_question_id", "participant_id", name="uq_question_vote"),)

    id = Column(Integer, primary_key=True, index=True)
    live_question_id = Column(Integer, ForeignKey("live_questions.id"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    live_question = relationship("LiveQuestion", back_populates="votes")
    participant = relationship("Participant", back_populates="votes")
