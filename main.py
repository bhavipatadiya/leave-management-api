from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, validator
from datetime import date, datetime, timedelta
from typing import List, Optional
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
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leave.db")


app = FastAPI()

logging.basicConfig(level=logging.INFO)


engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"])


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)



class UserCreate(BaseModel):
    username: str
    password: str
    role: str


class LeaveRequest(BaseModel):
    employee_name: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str

    @validator("end_date")
    def validate_dates(cls, v, values):
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("End date must be >= start date")
        return v


class LeaveResponse(BaseModel):
    id: int
    employee_name: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def create_token(data: dict):
    data["exp"] = datetime.utcnow() + timedelta(hours=2)
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")



def log_action(message: str):
    logging.info(message)



@app.get("/")
def root():
    return {"message": "API is running"}


@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = hash_password(user.password)

    new_user = User(
        username=user.username,
        password=hashed,
        role=user.role
    )

    db.add(new_user)
    db.commit()

    return {"message": "User created successfully"}


@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({
        "username": db_user.username,
        "role": db_user.role
    })

    return {"token": token}


@app.post("/leaves/", response_model=LeaveResponse)
def apply_leave(
    leave: LeaveRequest,
    db: Session = Depends(get_db),
    token: str = Query(...)
):
    user = get_current_user(token)

    if user["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only employees can apply")

    new_leave = Leave(**leave.dict())

    db.add(new_leave)
    db.commit()
    db.refresh(new_leave)

    logging.info(f"Leave applied by {leave.employee_name}")

    return new_leave


@app.get("/leaves/", response_model=List[LeaveResponse])
def get_leaves(
    db: Session = Depends(get_db),
    token: str = Query(...),
    page: int = 1,
    limit: int = 100,
    status: Optional[str] = None,
    employee_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
):
    user = get_current_user(token)

    if user["role"] not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Leave)

    if status:
        query = query.filter(Leave.status == status)

    if employee_name:
        query = query.filter(Leave.employee_name == employee_name)

    if start_date:
        query = query.filter(Leave.start_date >= start_date)

    if end_date:
        query = query.filter(Leave.end_date <= end_date)

    skip = (page - 1) * limit
    leaves = query.offset(skip).limit(limit).all()

    return leaves


@app.put("/leaves/{leave_id}")
def update_leave_status(
    leave_id: int,
    action: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: str = Query(...)
):
    user = get_current_user(token)

    if user["role"] != "manager":
        raise HTTPException(status_code=403, detail="Only managers allowed")

    leave = db.query(Leave).filter(Leave.id == leave_id).first()

    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    leave.status = "approved" if action == "approve" else "rejected"
    leave.updated_at = datetime.utcnow()

    db.commit()

    background_tasks.add_task(
        log_action,
        f"Leave {leave.id} updated to {leave.status}"
    )

    return {"message": f"Leave {leave.status} updated successfully"}

@app.get("/health")
def health():
    return {"status": "running"}