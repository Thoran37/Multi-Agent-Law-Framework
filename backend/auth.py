import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
from datetime import datetime

# Auth router
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# Local JSON file for user storage
USERS_FILE = Path(__file__).parent / "users.json"

def load_users():
    """Load users from JSON file."""
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Save users to JSON file."""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)

def validate_roll_number(roll_number: str) -> bool:
    """Validate roll number format: 22071A followed by 4 digits."""
    pattern = r"^22071A\d{4}$"
    return bool(re.match(pattern, roll_number))

# Request/Response Models
class SignupRequest(BaseModel):
    name: str
    age: int
    roll_number: str
    password: str

class LoginRequest(BaseModel):
    roll_number: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: dict = None

# Routes
@auth_router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    """Register a new student."""
    
    # Validate age
    if req.age < 18:
        raise HTTPException(status_code=400, detail="Age must be 18 or above")
    
    # Validate roll number
    if not validate_roll_number(req.roll_number):
        raise HTTPException(status_code=400, detail="Invalid roll number format. Must be 22071A followed by 4 digits (e.g., 22071A3259)")
    
    # Check if roll number already exists
    users = load_users()
    if req.roll_number in users:
        raise HTTPException(status_code=400, detail="Roll number already registered")
    
    # Save user (in production, hash the password!)
    users[req.roll_number] = {
        "name": req.name,
        "age": req.age,
        "roll_number": req.roll_number,
        "password": req.password,  # TODO: hash this with bcrypt in production
        "created_at": datetime.now().isoformat()
    }
    save_users(users)
    
    return AuthResponse(
        success=True,
        message="Signup successful! Please login.",
        user={"roll_number": req.roll_number, "name": req.name}
    )

@auth_router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Login a student."""
    
    # Validate roll number format
    if not validate_roll_number(req.roll_number):
        raise HTTPException(status_code=400, detail="Invalid roll number format")
    
    # Check if user exists and password matches
    users = load_users()
    if req.roll_number not in users:
        raise HTTPException(status_code=401, detail="Invalid roll number or password")
    
    user = users[req.roll_number]
    if user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid roll number or password")
    
    return AuthResponse(
        success=True,
        message="Login successful!",
        user={
            "roll_number": user["roll_number"],
            "name": user["name"],
            "age": user["age"]
        }
    )
