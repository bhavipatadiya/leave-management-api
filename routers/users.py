from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, schemas, auth, deps

router = APIRouter()

@router.post("/signup")
def signup(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    hashed = auth.hash_password(user.password)

    new_user = models.User(
        username=user.username,
        password=hashed,
        role=user.role
    )

    db.add(new_user)
    db.commit()
    return {"message": "User created"}

@router.post("/login")
def login(user: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()

    if not db_user or not auth.verify_password(user.password, db_user.password):
        return {"error": "Invalid credentials"}

    token = auth.create_token({"username": db_user.username, "role": db_user.role})
    return {"token": token}