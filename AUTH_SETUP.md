# Authentication System Setup

## Overview
A modular authentication system has been added with login/signup screens. Only students with valid roll numbers (format: `22071A` + 4 digits, e.g., `22071A3259`) can register. Age must be 18+. All existing case processing logic remains unchanged.

## What Was Added

### Backend (`backend/auth.py`)
- **`/api/auth/signup`** - POST endpoint for student registration
- **`/api/auth/login`** - POST endpoint for student login
- **Local JSON storage** - Users saved in `backend/users.json` (auto-created)
- **Validation**:
  - Roll number format: `22071A\d{4}` (regex validated)
  - Age: Must be 18 or above
  - Duplicate check: Roll number must be unique
- **Password storage**: Plain text (for local use; use bcrypt in production)

### Frontend (`frontend/src/components/Auth.jsx`)
- Modular Auth component with login/signup forms
- Client-side validation before sending to backend
- Toggle between login and signup screens
- Form fields: Name, Age, Roll Number, Password, Confirm Password

### Frontend Styling (`frontend/src/styles/Auth.css`)
- Full-screen auth page with gradient background
- Responsive design
- Smooth animations
- Matches existing legal theme

### Main App Update (`frontend/src/App.js`)
- Conditional rendering: Show Auth if user not logged in
- User state management
- Logout functionality
- Header displays logged-in user info
- All existing logic preserved (no changes to case processing)

### Backend Server Integration (`backend/server.py`)
- Auth router included in main FastAPI app
- No changes to existing endpoints

## How It Works

### User Registration Flow
1. User clicks "Sign up" on login page
2. Fills form: Name, Age (18+), Roll Number (22071A####), Password
3. Frontend validates locally
4. Backend validates roll number format and age
5. Saves to `backend/users.json`
6. User can now login

### User Login Flow
1. User enters Roll Number and Password
2. Backend checks `backend/users.json`
3. On success, returns user info
4. Frontend stores user state
5. Main app page is now accessible
6. User info shown in header with Logout button

### Local Storage
- **File**: `backend/users.json` (auto-created on first signup)
- **Format**: JSON object with roll_number as keys
- **Structure**:
```json
{
  "22071A3259": {
    "name": "John Doe",
    "age": 20,
    "roll_number": "22071A3259",
    "password": "password123",
    "created_at": "2026-03-15T..."
  }
}
```

## Testing

### Backend Test
```powershell
# Signup
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/signup" -Method POST -Body '{"name":"John","age":20,"roll_number":"22071A3259","password":"pass123"}' -ContentType "application/json"

# Login
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" -Method POST -Body '{"roll_number":"22071A3259","password":"pass123"}' -ContentType "application/json"
```

### Frontend
1. Run backend and frontend
2. See Auth login page
3. Click "Sign up"
4. Try invalid roll number (e.g., `12345`) - should fail
5. Try age < 18 - should fail
6. Valid signup with `22071A3259`, age 20 - should succeed
7. Login with created credentials
8. Should see main case analysis page
9. User name and roll number shown in header
10. Click Logout - back to login page

## No Changes to Existing Logic
✅ All case upload, process, simulate, audit, PDF generation logic untouched
✅ All existing API endpoints work as before
✅ Frontend UI/UX for case processing unchanged
✅ Database connections, LLM calls, orchestration untouched

## Files Changed/Added
```
backend/
  ├── auth.py (NEW) - Authentication logic
  └── server.py (MODIFIED) - Added auth router

frontend/src/
  ├── components/
  │   └── Auth.jsx (NEW) - Auth component
  ├── styles/
  │   └── Auth.css (NEW) - Auth styling
  └── App.js (MODIFIED) - Added auth check and user state

backend/users.json (AUTO-CREATED) - Local user database
```

## Future Improvements (Optional)
- Hash passwords with bcrypt
- Add JWT tokens for session management
- Use SQLite instead of JSON for better scalability
- Add email verification
- Add password reset functionality
- Rate limiting on login attempts
