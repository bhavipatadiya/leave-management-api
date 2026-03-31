from fastapi import FastAPI, HTTPException, Query, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from datetime import date, datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import logging
import os
from dotenv import load_dotenv


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'leave.db')}"


app = FastAPI()
logging.basicConfig(level=logging.INFO)


templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


static_path = os.path.join(BASE_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


pwd_context = CryptContext(schemes=["pbkdf2_sha256"])



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



def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")



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
def signup(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=username,
        password=hash_password(password),
        role=role
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/login-page", status_code=303)


@app.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid login")

    token = create_token({"username": user.username, "role": user.role})

    redirect_map = {
        "employee": f"/employee?token={token}",
        "manager": f"/manager?token={token}",
        "admin": f"/admin?token={token}"
    }

    return RedirectResponse(redirect_map.get(user.role, "/login-page"), status_code=303)



@app.post("/apply-leave")
def apply_leave(
    employee_name: str = Form(...),
    leave_type: str = Form(...),
    start_date: date = Form(...),
    end_date: date = Form(...),
    reason: str = Form(...),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(token)

    if user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only employees allowed")

    leave = Leave(
        employee_name=employee_name,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason
    )
    db.add(leave)
    db.commit()
    return {"message": "Leave applied successfully"}



@app.get("/leaves/")
def get_leaves(token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user(token)
    if user["role"] not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(Leave).all()



@app.post("/update/{leave_id}")
def update_leave(
    leave_id: int,
    action: str = Form(...),
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(token)
    if user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Only manager allowed")

    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    leave.status = "approved" if action == "approve" else "rejected"
    db.commit()
    return {"message": f"Leave {leave.status}"}



@app.get("/health")
def health():
    return {"status": "running"}