# Leave Management API 

# Project Overview
This is a Leave Management System built using FastAPI.  
It allows employees to apply for leave and managers to approve or reject requests.

# Tech Stack
- FastAPI
- Uvicorn
- SQLite
- SQLAlchemy
- Pydantic
- JWT Authentication
- HTML, CSS, JavaScript
  
# Features
- User Signup & Login
- JWT Authentication
- Secure Password Hashing (SHA256 + PBKDF2)
- Apply Leave
- Approve / Reject Leave
- Dynamic Toggle (Approve ↔ Reject)
- Filter Leaves
- Pagination
- Logging
- Health Check Endpoint

# Live API
https://leave-management-api-6kqm.onrender.com/docs

# Live Web App
https://leave-management-api-1-zwhz.onrender.com

# GitHub Repository
https://github.com/bhavipatadiya/leave-management-api

# Run Locally
```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
