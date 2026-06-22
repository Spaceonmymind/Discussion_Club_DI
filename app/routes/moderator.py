from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..auth import require_staff
from ..database import get_db
from ..models import Event, LiveQuestion, ParticipantAnswer, PreparedQuestion, User

router = APIRouter(prefix="/moderator")
templates = Jinja2Templates(directory="app/templates")


@router.get("/events/{event_id}", response_class=HTMLResponse)
def moderator_dashboard(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    prepared = db.query(PreparedQuestion).filter(PreparedQuestion.event_id == event.id).order_by(PreparedQuestion.order_index).all()
    return templates.TemplateResponse(
        "moderator_dashboard.html",
        {"request": request, "event": event, "prepared_questions": prepared, "user": user},
    )


@router.post("/events/{event_id}/prepared-questions")
def create_prepared_form(
    event_id: int,
    text: str = Form(...),
    description: str = Form(default=""),
    order_index: int = Form(default=0),
    is_active: bool = Form(default=True),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    db.add(PreparedQuestion(event_id=event_id, text=text, description=description, order_index=order_index, is_active=is_active))
    db.commit()
    return RedirectResponse(url=f"/moderator/events/{event_id}", status_code=303)


@router.post("/prepared-questions/{question_id}/delete")
def delete_prepared_form(question_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    question = db.get(PreparedQuestion, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    event_id = question.event_id
    db.delete(question)
    db.commit()
    return RedirectResponse(url=f"/moderator/events/{event_id}", status_code=303)


@router.get("/events/{event_id}/export")
def export_event_questions(event_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    def rows():
        yield "type,status,votes,pinned,participant,text,answer_or_comment\n"
        for question in db.query(LiveQuestion).filter(LiveQuestion.event_id == event_id).order_by(LiveQuestion.created_at).all():
            name = "Анонимно" if question.participant.is_anonymous else question.participant.name
            yield f'live,{question.status},{question.votes_count},{question.is_pinned},"{name}","{question.text}","{question.moderator_comment or ""}"\n'
        for answer in db.query(ParticipantAnswer).filter(ParticipantAnswer.event_id == event_id).order_by(ParticipantAnswer.created_at).all():
            name = "Анонимно" if answer.participant.is_anonymous else answer.participant.name
            yield f'prepared-answer,,,, "{name}","{answer.prepared_question.text}","{answer.answer_text}"\n'

    filename = f"event-{event_id}-questions.csv"
    return StreamingResponse(rows(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})
