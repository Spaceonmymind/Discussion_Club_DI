from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .auth import SESSION_COOKIE, init_db, verify_password
from .database import get_db
from .models import User
from .routes import admin, api, moderator, public

app = FastAPI(title="Discussion Club")
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(moderator.router)
app.include_router(api.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный email или пароль"}, status_code=401)
    target = "/admin" if user.role == "admin" else "/moderator/events/1"
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(SESSION_COOKIE, str(user.id), httponly=True, samesite="lax")
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
