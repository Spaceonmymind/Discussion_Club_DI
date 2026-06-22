from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Event, Participant

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.status == "active").order_by(Event.date.desc()).first()
    if event:
        return RedirectResponse(url=f"/event/{event.public_code}", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@router.get("/event/{public_code}", response_class=HTMLResponse)
def public_event(public_code: str, request: Request, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.public_code == public_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return templates.TemplateResponse("public_event.html", {"request": request, "event": event})


@router.post("/event/{public_code}/join")
def join_event(
    public_code: str,
    name: str = Form(default=""),
    is_anonymous: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.public_code == public_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    from secrets import token_urlsafe

    participant = Participant(
        event_id=event.id,
        name=None if is_anonymous else (name.strip() or "Участник"),
        is_anonymous=is_anonymous,
        session_token=token_urlsafe(32),
    )
    db.add(participant)
    db.commit()
    response = RedirectResponse(url=f"/event/{public_code}/discussion", status_code=303)
    response.set_cookie("dc_participant_id", str(participant.id), httponly=True, samesite="lax")
    response.set_cookie("dc_participant_token", participant.session_token, httponly=True, samesite="lax")
    return response


@router.get("/event/{public_code}/discussion", response_class=HTMLResponse)
def discussion(public_code: str, request: Request, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.public_code == public_code).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    participant_id = request.cookies.get("dc_participant_id")
    token = request.cookies.get("dc_participant_token")
    participant = None
    if participant_id and token:
        participant = db.get(Participant, int(participant_id))
        if participant and participant.session_token != token:
            participant = None
    if not participant:
        return RedirectResponse(url=f"/event/{public_code}", status_code=303)
    return templates.TemplateResponse(
        "discussion.html",
        {"request": request, "event": event, "participant": participant},
    )
