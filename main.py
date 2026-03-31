from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from datetime import date, datetime, timedelta
from jose import jwt
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os


SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'leave.db')}"


app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

static_path = os.path.join(BASE_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String) 
    role = Column(String)

class Leave(Base):
    __tablename__ = "leaves"
    id = Column(Integer, primary_key=True)
    employee_name = Column(String)
    leave_type = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return {"username": "unknown", "role": "employee"}


@app.get("/", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login-page", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/employee", response_class=HTMLResponse)
def employee_page(request: Request, token: str):
    return templates.TemplateResponse("employee.html", {"request": request, "token": token})

@app.get("/manager", response_class=HTMLResponse)
def manager_page(request: Request, token: str):
    return templates.TemplateResponse("manager.html", {"request": request, "token": token})

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, token: str):
    return templates.TemplateResponse("admin.html", {"request": request, "token": token})


@app.post("/signup")
def signup(username: str = Form(...), password: str = Form(...), role: str = Form(...), db: Session = next(get_db())):
    if db.query(User).filter(User.username == username).first():
        return {"message": "User already exists"}
    user = User(username=username, password=password, role=role)
    db.add(user)
    db.commit()
    return RedirectResponse("/login-page", status_code=303)


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):

    token = create_token({"username": username, "role": "employee"}) 
    return RedirectResponse(f"/employee?token={token}", status_code=303)

@app.post("/apply-leave")
def apply_leave(employee_name: str = Form(...), leave_type: str = Form(...),
                start_date: date = Form(...), end_date: date = Form(...),
                reason: str = Form(...), token: str = Form(...),
                db: Session = next(get_db())):
    user = get_current_user(token)
    leave = Leave(employee_name=employee_name, leave_type=leave_type,
                  start_date=start_date, end_date=end_date, reason=reason)
    db.add(leave)
    db.commit()
    return {"message": "Leave applied successfully"}


@app.get("/leaves/")
def get_leaves(token: str, db: Session = next(get_db())):
    user = get_current_user(token)
    return db.query(Leave).all()


@app.get("/health")
def health():
    return {"status": "running"}