from datetime import date, time
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..database import get_db
from ..models import Event, LiveQuestion, Participant, ParticipantAnswer, PreparedQuestion, QuestionVote, User

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_time(value: Optional[str]) -> Optional[time]:
    return time.fromisoformat(value) if value else None


@router.get("", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    events = db.query(Event).order_by(Event.date.desc()).all()
    moderators = db.query(User).filter(User.role == "moderator").order_by(User.created_at.desc()).all()
    stats = {}
    for event in events:
        stats[event.id] = {
            "participants": len(event.participants),
            "live_questions": len(event.live_questions),
            "answers": db.query(ParticipantAnswer).filter(ParticipantAnswer.event_id == event.id).count(),
            "impulse_opt_ins": impulse_opt_ins(db, event.id),
        }
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {"request": request, "user": user, "events": events, "moderators": moderators, "stats": stats},
    )


def impulse_opt_ins(db: Session, event_id: int) -> list[str]:
    impulse_question_ids = [
        question.id
        for question in db.query(PreparedQuestion)
        .filter(PreparedQuestion.event_id == event_id)
        .all()
        if 'пилоте агента "импульс"' in question.text.casefold()
    ]
    if not impulse_question_ids:
        return []

    rows = (
        db.query(Participant.email, Participant.name, ParticipantAnswer.answer_text)
        .join(ParticipantAnswer, ParticipantAnswer.participant_id == Participant.id)
        .filter(
            ParticipantAnswer.event_id == event_id,
            ParticipantAnswer.prepared_question_id.in_(impulse_question_ids),
        )
        .all()
    )
    return sorted(
        {
            email or name or "Участник"
            for email, name, answer_text in rows
            if answer_text.strip().casefold() == "да"
        }
    )


@router.post("/events")
def create_event_form(
    title: str = Form(...),
    description: str = Form(default=""),
    event_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(default=""),
    location: str = Form(default=""),
    status: str = Form(default="draft"),
    public_code: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    from ..auth import make_public_code

    event = Event(
        title=title,
        description=description,
        date=parse_date(event_date),
        start_time=parse_time(start_time),
        end_time=parse_time(end_time),
        location=location,
        status=status,
        public_code=public_code.strip() or make_public_code(),
        created_by=user.id,
    )
    db.add(event)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/events/{event_id}/delete")
def delete_event_form(event_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/events/{event_id}/clear-data")
def clear_event_data_form(event_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    live_question_ids = db.query(LiveQuestion.id).filter(LiveQuestion.event_id == event_id).subquery()
    db.query(QuestionVote).filter(QuestionVote.live_question_id.in_(live_question_ids)).delete(synchronize_session=False)
    db.query(ParticipantAnswer).filter(ParticipantAnswer.event_id == event_id).delete(synchronize_session=False)
    db.query(LiveQuestion).filter(LiveQuestion.event_id == event_id).delete(synchronize_session=False)
    db.query(Participant).filter(Participant.event_id == event_id).delete(synchronize_session=False)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/events/{event_id}/edit")
def edit_event_form(
    event_id: int,
    title: str = Form(...),
    description: str = Form(default=""),
    event_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(default=""),
    location: str = Form(default=""),
    status: str = Form(default="draft"),
    public_code: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.title = title
    event.description = description
    event.date = parse_date(event_date)
    event.start_time = parse_time(start_time)
    event.end_time = parse_time(end_time)
    event.location = location
    event.status = status
    event.public_code = public_code
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/moderators")
def create_moderator_form(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    db.add(User(name=name, email=email, password_hash=hash_password(password), role="moderator"))
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)
