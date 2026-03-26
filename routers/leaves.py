from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from .. import models, schemas, deps
from datetime import datetime

router = APIRouter()


def log_action(msg: str):
    print(f"LOG: {msg}")


@router.post("/leaves")
def create_leave(
    leave: schemas.LeaveCreate,
    db: Session = Depends(deps.get_db),
    user=Depends(deps.get_current_user)
):
    if user["role"] != "employee":
        return {"error": "Only employee allowed"}

    new_leave = models.Leave(**leave.dict())
    db.add(new_leave)
    db.commit()
    return new_leave


@router.get("/leaves")
def get_leaves(
    db: Session = Depends(deps.get_db),
    user=Depends(deps.get_current_user),
    page: int = 1,
    limit: int = 5
):
    if user["role"] not in ["admin", "manager"]:
        return {"error": "Access denied"}

    skip = (page - 1) * limit
    leaves = db.query(models.Leave).offset(skip).limit(limit).all()
    return leaves


@router.put("/leaves/{id}")
def update_leave(
    id: int,
    action: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    user=Depends(deps.get_current_user)
):
    if user["role"] != "manager":
        return {"error": "Only manager allowed"}

    leave = db.query(models.Leave).filter(models.Leave.id == id).first()

    if not leave:
        return {"error": "Not found"}

    leave.status = "approved" if action == "approve" else "rejected"
    leave.updated_at = datetime.utcnow()

    db.commit()

    background_tasks.add_task(log_action, f"Leave {leave.status}")

    return {"message": leave.status}