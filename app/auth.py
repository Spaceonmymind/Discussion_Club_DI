from datetime import date, time
from secrets import token_hex

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Event, LiveQuestion, Participant, ParticipantAnswer, PreparedQuestion, QuestionVote, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE = "dc_user_id"

DIGEST_QUESTIONS = [
    "Какие темы дайджеста наиболее интересны лично Вам?",
    "Какая тема за II квартал 2026 года, на Ваш взгляд, сильнее всего повлияет на индустрию в ближайший год?",
    "Была полезной для Вас сегодняшняя дайджест-сессия?",
    "Хотели бы Вы, чтобы такие дайджест-сессии проводились регулярно?",
    "Какие новые темы и спикеров Вы бы хотели видеть на следующей дайджест-сессии?",
    "Что бы Вы добавили или изменили в формате?",
    'Хочу принять участие в пилоте агента "Импульс"',
]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.cookies.get(SESSION_COOKIE)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def require_staff(user: User = Depends(current_user)) -> User:
    if user.role not in {"admin", "moderator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff role required")
    return user


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()


def seed_data(db: Session) -> None:
    admin = db.query(User).filter(User.email == "admin@club.ru").first()
    if not admin:
        admin = User(
            name="Администратор",
            email="admin@club.ru",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        db.add(admin)
        db.flush()

    moderator = db.query(User).filter(User.email == "moderator@club.ru").first()
    if not moderator:
        moderator = User(
            name="Модератор",
            email="moderator@club.ru",
            password_hash=hash_password("moderator123"),
            role="moderator",
        )
        db.add(moderator)

    event = db.query(Event).filter(Event.public_code == "club-15july").first()
    if not event:
        event = Event(
            title="Пульс финтех-инноваций",
            description="Дайджест-сессия о трендах, кейсах и практических выводах для команды.",
            date=date(2026, 8, 14),
            start_time=time(11, 0),
            end_time=time(12, 0),
            location="г. Москва, ул. Б. Татарская, д. 11А",
            status="active",
            public_code="club-15july",
            created_by=admin.id,
        )
        db.add(event)
        db.flush()
        for index, text in enumerate(DIGEST_QUESTIONS, start=1):
            db.add(PreparedQuestion(event_id=event.id, text=text, order_index=index, is_active=True))
    else:
        event.title = "Пульс финтех-инноваций"
        event.description = "Дайджест-сессия о трендах, кейсах и практических выводах для команды."
        event.date = date(2026, 8, 14)
        event.start_time = time(11, 0)
        event.location = "г. Москва, ул. Б. Татарская, д. 11А"
        current_questions = [
            question.text
            for question in db.query(PreparedQuestion)
            .filter(PreparedQuestion.event_id == event.id)
            .order_by(PreparedQuestion.order_index, PreparedQuestion.id)
            .all()
        ]
        if current_questions != DIGEST_QUESTIONS:
            reset_event_data(db, event.id)
            for index, text in enumerate(DIGEST_QUESTIONS, start=1):
                db.add(PreparedQuestion(event_id=event.id, text=text, order_index=index, is_active=True))
    db.commit()


def reset_event_data(db: Session, event_id: int) -> None:
    live_question_ids = [id_ for (id_,) in db.query(LiveQuestion.id).filter(LiveQuestion.event_id == event_id).all()]
    if live_question_ids:
        db.query(QuestionVote).filter(QuestionVote.live_question_id.in_(live_question_ids)).delete(synchronize_session=False)
    db.query(ParticipantAnswer).filter(ParticipantAnswer.event_id == event_id).delete(synchronize_session=False)
    db.query(LiveQuestion).filter(LiveQuestion.event_id == event_id).delete(synchronize_session=False)
    db.query(Participant).filter(Participant.event_id == event_id).delete(synchronize_session=False)
    db.query(PreparedQuestion).filter(PreparedQuestion.event_id == event_id).delete(synchronize_session=False)


def ensure_schema() -> None:
    inspector = inspect(engine)
    participant_columns = {column["name"] for column in inspector.get_columns("participants")}
    with engine.begin() as connection:
        if "email" not in participant_columns:
            connection.execute(text("ALTER TABLE participants ADD COLUMN email VARCHAR(255)"))
        connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS uq_participant_event_email ON participants (event_id, email)")
        )


def make_public_code() -> str:
    return token_hex(4)
