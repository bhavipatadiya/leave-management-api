from pydantic import BaseModel, validator
from datetime import date, datetime

class UserCreate(BaseModel):
    username: str
    password: str
    role: str


class LeaveCreate(BaseModel):
    employee_name: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str

    @validator("end_date")
    def validate_dates(cls, v, values):
        if v < values["start_date"]:
            raise ValueError("End date must be >= start date")
        return v

class LeaveResponse(BaseModel):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True