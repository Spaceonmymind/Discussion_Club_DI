from datetime import date, time
from secrets import token_hex

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import Event, PreparedQuestion, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE = "dc_user_id"


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
            title="Дискуссионный клуб",
            description="Открытая встреча для вопросов, выступлений и совместного поиска решений.",
            date=date(2026, 7, 15),
            start_time=time(10, 0),
            end_time=time(12, 0),
            location="г. Москва, ул. Б. Татарская, д. 11А",
            status="active",
            public_code="club-15july",
            created_by=admin.id,
        )
        db.add(event)
        db.flush()
        questions = [
            "Какие ключевые проблемы вы видите в теме выступления?",
            "Какие решения кажутся наиболее реалистичными?",
            "Какие риски необходимо учитывать?",
            "Какие вопросы стоит вынести на общую дискуссию?",
        ]
        for index, text in enumerate(questions, start=1):
            db.add(PreparedQuestion(event_id=event.id, text=text, order_index=index, is_active=True))
    db.commit()


def make_public_code() -> str:
    return token_hex(4)
