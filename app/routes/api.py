from datetime import date, time
from secrets import token_urlsafe
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import make_public_code, require_admin, require_staff
from ..database import get_db
from ..models import Event, LiveQuestion, Participant, ParticipantAnswer, PreparedQuestion, QuestionVote, User
from ..schemas import (
    AnswerCreate,
    CommentPatch,
    EventCreate,
    EventPatch,
    LiveQuestionCreate,
    ParticipantCreate,
    PinPatch,
    PreparedQuestionCreate,
    PreparedQuestionPatch,
    StatusPatch,
)

router = APIRouter(prefix="/api")

QUESTION_STATUSES = {"moderation", "approved", "rejected", "discussion", "answered"}
EVENT_STATUSES = {"draft", "active", "finished"}


def question_to_dict(question: LiveQuestion) -> dict:
    participant = question.participant
    name = "Анонимно" if participant.is_anonymous else participant.name
    return {
        "id": question.id,
        "event_id": question.event_id,
        "participant_id": question.participant_id,
        "participant_name": name,
        "text": question.text,
        "status": question.status,
        "is_pinned": question.is_pinned,
        "votes_count": question.votes_count,
        "moderator_comment": question.moderator_comment,
        "created_at": question.created_at.isoformat(),
    }


def prepared_to_dict(question: PreparedQuestion) -> dict:
    return {
        "id": question.id,
        "event_id": question.event_id,
        "text": question.text,
        "description": question.description,
        "order_index": question.order_index,
        "is_active": question.is_active,
    }


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_time(value: Optional[str]) -> Optional[time]:
    return time.fromisoformat(value) if value else None


@router.post("/events/{event_id}/participants")
def create_participant(event_id: int, payload: ParticipantCreate, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    participant = Participant(
        event_id=event_id,
        name=None if payload.is_anonymous else (payload.name or "Участник"),
        is_anonymous=payload.is_anonymous,
        session_token=token_urlsafe(32),
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return {"id": participant.id, "session_token": participant.session_token}


@router.get("/events/{event_id}/prepared-questions")
def get_prepared_questions(event_id: int, db: Session = Depends(get_db)):
    questions = (
        db.query(PreparedQuestion)
        .filter(PreparedQuestion.event_id == event_id, PreparedQuestion.is_active.is_(True))
        .order_by(PreparedQuestion.order_index, PreparedQuestion.id)
        .all()
    )
    return [prepared_to_dict(question) for question in questions]


@router.post("/prepared-questions/{question_id}/answers")
def create_answer(question_id: int, payload: AnswerCreate, db: Session = Depends(get_db)):
    question = db.get(PreparedQuestion, question_id)
    participant = db.get(Participant, payload.participant_id)
    if not question or not participant or participant.event_id != question.event_id:
        raise HTTPException(status_code=404, detail="Question or participant not found")
    answer = ParticipantAnswer(
        event_id=question.event_id,
        prepared_question_id=question.id,
        participant_id=participant.id,
        answer_text=payload.answer_text.strip(),
    )
    if not answer.answer_text:
        raise HTTPException(status_code=400, detail="Answer is empty")
    db.add(answer)
    db.commit()
    return {"ok": True, "id": answer.id}


@router.post("/events/{event_id}/live-questions")
def create_live_question(event_id: int, payload: LiveQuestionCreate, db: Session = Depends(get_db)):
    participant = db.get(Participant, payload.participant_id)
    if not participant or participant.event_id != event_id:
        raise HTTPException(status_code=404, detail="Participant not found")
    text = payload.text.strip()
    if len(text) < 3:
        raise HTTPException(status_code=400, detail="Question is too short")
    question = LiveQuestion(event_id=event_id, participant_id=participant.id, text=text, status="moderation")
    db.add(question)
    db.commit()
    db.refresh(question)
    return question_to_dict(question)


@router.get("/events/{event_id}/live-questions")
def get_live_questions(event_id: int, participant_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(LiveQuestion).filter(LiveQuestion.event_id == event_id)
    if participant_id:
        query = query.filter((LiveQuestion.status != "rejected") | (LiveQuestion.participant_id == participant_id))
    else:
        query = query.filter(LiveQuestion.status.in_(["approved", "discussion", "answered"]))
    questions = query.order_by(LiveQuestion.is_pinned.desc(), LiveQuestion.votes_count.desc(), LiveQuestion.created_at.desc()).all()
    return [question_to_dict(question) for question in questions]


@router.post("/live-questions/{question_id}/vote")
def vote_question(question_id: int, participant_id: int, db: Session = Depends(get_db)):
    question = db.get(LiveQuestion, question_id)
    participant = db.get(Participant, participant_id)
    if not question or not participant or participant.event_id != question.event_id:
        raise HTTPException(status_code=404, detail="Question or participant not found")
    vote = QuestionVote(live_question_id=question.id, participant_id=participant.id)
    db.add(vote)
    try:
        question.votes_count += 1
        db.commit()
    except IntegrityError:
        db.rollback()
    db.refresh(question)
    return {"votes_count": question.votes_count}


@router.post("/events/{event_id}/prepared-questions")
def create_prepared_question(event_id: int, payload: PreparedQuestionCreate, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    if not db.get(Event, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    question = PreparedQuestion(event_id=event_id, **payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return prepared_to_dict(question)


@router.patch("/prepared-questions/{question_id}")
def patch_prepared_question(question_id: int, payload: PreparedQuestionPatch, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    question = db.get(PreparedQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, field, value)
    db.commit()
    return prepared_to_dict(question)


@router.delete("/prepared-questions/{question_id}")
def delete_prepared_question(question_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    question = db.get(PreparedQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(question)
    db.commit()
    return {"ok": True}


@router.get("/events/{event_id}/moderation/live-questions")
def get_moderation_questions(event_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    questions = db.query(LiveQuestion).filter(LiveQuestion.event_id == event_id).order_by(
        LiveQuestion.is_pinned.desc(),
        LiveQuestion.created_at.desc(),
    ).all()
    return [question_to_dict(question) for question in questions]


@router.patch("/live-questions/{question_id}/status")
def patch_question_status(question_id: int, payload: StatusPatch, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    if payload.status not in QUESTION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    question = db.get(LiveQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    question.status = payload.status
    db.commit()
    return question_to_dict(question)


@router.patch("/live-questions/{question_id}/pin")
def patch_question_pin(question_id: int, payload: PinPatch, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    question = db.get(LiveQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    question.is_pinned = payload.is_pinned
    db.commit()
    return question_to_dict(question)


@router.patch("/live-questions/{question_id}/comment")
def patch_question_comment(question_id: int, payload: CommentPatch, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    question = db.get(LiveQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    question.moderator_comment = payload.moderator_comment
    db.commit()
    return question_to_dict(question)


@router.post("/events")
def create_event(payload: EventCreate, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if payload.status not in EVENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    event = Event(
        title=payload.title,
        description=payload.description,
        date=parse_date(payload.date),
        start_time=parse_time(payload.start_time),
        end_time=parse_time(payload.end_time),
        location=payload.location,
        status=payload.status,
        public_code=payload.public_code or make_public_code(),
        created_by=user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": event.id, "public_code": event.public_code}


@router.patch("/events/{event_id}")
def patch_event(event_id: int, payload: EventPatch, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    data = payload.model_dump(exclude_unset=True)
    if "date" in data:
        data["date"] = parse_date(data["date"])
    if "start_time" in data:
        data["start_time"] = parse_time(data["start_time"])
    if "end_time" in data:
        data["end_time"] = parse_time(data["end_time"])
    if "status" in data and data["status"] not in EVENT_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    for field, value in data.items():
        setattr(event, field, value)
    db.commit()
    return {"ok": True}


@router.delete("/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"ok": True}


@router.get("/events/{event_id}/stats")
def event_stats(event_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not db.get(Event, event_id):
        raise HTTPException(status_code=404, detail="Event not found")
    base = db.query(LiveQuestion).filter(LiveQuestion.event_id == event_id)
    top = base.order_by(LiveQuestion.votes_count.desc()).limit(5).all()
    return {
        "participants": db.query(Participant).filter(Participant.event_id == event_id).count(),
        "live_questions": base.count(),
        "moderation": base.filter(LiveQuestion.status == "moderation").count(),
        "approved": base.filter(LiveQuestion.status == "approved").count(),
        "answered": base.filter(LiveQuestion.status == "answered").count(),
        "prepared_answers": db.query(ParticipantAnswer).filter(ParticipantAnswer.event_id == event_id).count(),
        "top_questions": [question_to_dict(question) for question in top],
    }
