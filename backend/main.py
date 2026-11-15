import os
import sys
import random

# Ensure project root is in sys.path so imports work from any working directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
for p in [PROJECT_ROOT, CURRENT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from backend.database import init_db, fetch_one, execute_write
from backend.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.models import RegisterRequest, LoginRequest, TokenResponse, UserSummary
from backend.routers import books, loans, features, admin

app = FastAPI(
    title="Smart Library Management System API",
    description="Full-stack DBMS College Project featuring 3NF normalization, ACID transactions, SQL triggers, views, and role-based access control.",
    version="1.0.0"
)

# Enable CORS for HTML/JS frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Include Feature Routers
app.include_router(books.router)
app.include_router(loans.router)
app.include_router(features.router)
app.include_router(admin.router)

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register(req: RegisterRequest):
    """
    Registers a new student account.
    Auto-generates a unique university Library Card Number (e.g., LIB-STU-108).
    """
    email_clean = req.email.strip().lower()
    existing = fetch_one("SELECT user_id FROM users WHERE email = %s", (email_clean,))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email address already exists.")

    # Generate unique library card number
    count_res = fetch_one("SELECT COUNT(*) AS total FROM users")
    next_num = (count_res["total"] if count_res else 0) + 101
    library_card_no = f"LIB-STU-{next_num}"
    
    # Ensure card number is completely unique
    while fetch_one("SELECT user_id FROM users WHERE library_card_no = %s", (library_card_no,)):
        next_num += random.randint(1, 9)
        library_card_no = f"LIB-STU-{next_num}"

    pw_hash = hash_password(req.password)
    user_role = req.role if req.role in ("admin", "member") else "member"

    user_id = execute_write(
        """
        INSERT INTO users (library_card_no, full_name, email, password_hash, phone, role, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'active')
        """,
        (library_card_no, req.full_name.strip(), email_clean, pw_hash, req.phone, user_role)
    )

    user_summary = UserSummary(
        user_id=user_id,
        library_card_no=library_card_no,
        full_name=req.full_name.strip(),
        email=email_clean,
        role=user_role,
        status="active",
        phone=req.phone
    )

    token = create_access_token({"sub": str(user_id), "role": user_role, "email": email_clean})
    return TokenResponse(access_token=token, token_type="bearer", user=user_summary)

@app.post("/api/auth/login", response_model=TokenResponse, tags=["Authentication"])
def login(req: LoginRequest):
    """
    Authenticates patron or administrator credentials and returns a signed JWT token.
    """
    email_clean = req.email.strip().lower()
    user = fetch_one(
        "SELECT user_id, library_card_no, full_name, email, password_hash, phone, role, status FROM users WHERE email = %s",
        (email_clean,)
    )

    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password combination."
        )

    if user["status"] == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your library account is suspended. Please visit the library desk."
        )

    token = create_access_token({"sub": str(user["user_id"]), "role": user["role"], "email": user["email"]})

    user_summary = UserSummary(
        user_id=user["user_id"],
        library_card_no=user["library_card_no"],
        full_name=user["full_name"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
        phone=user["phone"]
    )

    return TokenResponse(access_token=token, token_type="bearer", user=user_summary)

@app.get("/api/auth/me", response_model=UserSummary, tags=["Authentication"])
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Returns the authenticated patron's profile and active role."""
    return UserSummary(**current_user)

# ============================================================================
# STATIC FRONTEND SERVING
# ============================================================================
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

if os.path.isdir(frontend_dir):
    # Mount css and js static folders
    if os.path.isdir(os.path.join(frontend_dir, "css")):
        app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
    if os.path.isdir(os.path.join(frontend_dir, "js")):
        app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")

    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/login", include_in_schema=False)
    @app.get("/login.html", include_in_schema=False)
    def serve_login():
        return FileResponse(os.path.join(frontend_dir, "login.html"))

    @app.get("/dashboard", include_in_schema=False)
    @app.get("/dashboard.html", include_in_schema=False)
    def serve_dashboard():
        return FileResponse(os.path.join(frontend_dir, "dashboard.html"))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

